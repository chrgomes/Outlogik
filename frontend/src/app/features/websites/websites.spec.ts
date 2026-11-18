import { TestBed } from '@angular/core/testing';

import { ALL, answer, dialogProviders, flushPending, page, setupOrg } from '../../../testing/org-setup';
import { membership, me } from '../../../testing/fixtures';
import { Website, Workspace } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { WorkspaceService } from '../../core/workspace.service';
import { WebsiteFormDialog } from './website-form-dialog';
import { WebsitesList } from './websites-list';

const own: Workspace = {
  id: 'w-own', kind: 'own', name: 'Acme', client_id: null, client_status: null, website_count: 1,
  created_at: '2026-11-18T00:00:00Z', linked: false, organization_name: null, access: null,
};
const bakery: Workspace = { ...own, id: 'w-1', kind: 'client', name: 'Bakery', client_id: 'c1',
  client_status: 'active' };
const site: Website = {
  id: 's1', workspace_id: 'w-own', workspace_name: 'Acme', client_id: null, client_name: null,
  name: 'acme.example.com', url: 'https://acme.example.com', domain: 'acme.example.com',
  status: 'active', created_at: '2026-11-18T00:00:00Z', updated_at: '2026-11-18T00:00:00Z',
};

function asKind(kind: 'agency' | 'business') {
  TestBed.inject(AuthService).me.set(me([membership({ permissions: ALL, organization_kind: kind })]));
}

describe('WebsitesList', () => {
  beforeEach(() => localStorage.clear());

  async function render(kind: 'agency' | 'business', selected?: string) {
    if (selected) localStorage.setItem('ol.workspace.acme', selected);
    const http = setupOrg(ALL);
    asKind(kind);
    const fixture = TestBed.createComponent(WebsitesList);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/workspaces', kind === 'agency' ? [own, bakery] : [own]);
    await flushPending();
    fixture.detectChanges();
    await flushPending();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  it('shows an agency every workspace, with a Workspace column', async () => {
    const { fixture, http, el } = await render('agency');
    const req = http.expectOne((r) => r.url === '/api/v1/orgs/acme/websites');
    expect(req.request.params.get('sort')).toBe('workspace');
    req.flush(page([site, { ...site, id: 's2', workspace_id: 'w-1', workspace_name: 'Bakery',
      client_id: 'c1', client_name: 'Bakery' }]));
    await flushPending();
    fixture.detectChanges();
    expect([...el.querySelectorAll('th')].map((t) => t.textContent!.trim())).toContain('Workspace');
    expect(el.textContent).toContain('Your own marketing');
    expect(el.querySelector('tbody a.row-link')!.getAttribute('href')).toBe('/o/acme/clients/c1');
  });

  it("uses the selected workspace's endpoint and drops the column", async () => {
    const { fixture, http, el } = await render('agency', 'w-1');
    http.expectOne((r) => r.url === '/api/v1/orgs/acme/workspaces/w-1/websites').flush(page([]));
    await flushPending();
    fixture.detectChanges();
    expect(el.textContent).toContain("Bakery's websites.");
    expect(el.textContent).toContain("Add Bakery's websites to track them.");
  });

  it('gives a business its own websites with no workspace or client wording', async () => {
    const { fixture, http, el } = await render('business');
    http.expectOne((r) => r.url === '/api/v1/orgs/acme/websites').flush(page([site]));
    await flushPending();
    fixture.detectChanges();
    expect([...el.querySelectorAll('th')].map((t) => t.textContent!.trim())).not.toContain('Workspace');
    expect(el.textContent).not.toMatch(/client/i);
  });
});

describe('WebsiteFormDialog', () => {
  beforeEach(() => localStorage.clear());

  async function render(kind: 'agency' | 'business', data: object) {
    const http = setupOrg(ALL, 'owner', dialogProviders(data));
    asKind(kind);
    TestBed.inject(WorkspaceService);
    await flushPending();
    answer(http, '/api/v1/orgs/acme/workspaces', kind === 'agency' ? [own, bakery] : [own]);
    await flushPending();
    const fixture = TestBed.createComponent(WebsiteFormDialog);
    fixture.detectChanges();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  function fill(el: HTMLElement, selector: string, value: string) {
    const input = el.querySelector(selector) as HTMLInputElement | HTMLSelectElement;
    input.value = value;
    input.dispatchEvent(new Event(input.tagName === 'SELECT' ? 'change' : 'input'));
  }

  it('lets an agency choose the workspace and adds the site there', async () => {
    const { el, http } = await render('agency', { workspaceId: 'w-1' });
    const options = [...el.querySelectorAll('#site-workspace option')].map((o) => o.textContent!.trim());
    expect(options).toEqual(['Choose a workspace', 'Acme (your own marketing)', 'Bakery']);
    expect((el.querySelector('#site-workspace') as HTMLSelectElement).value).toBe('w-1');
    fill(el, '#site-url', 'bakery.example.com');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne('/api/v1/orgs/acme/workspaces/w-1/websites');
    expect(req.request.body).toEqual({ url: 'bakery.example.com', name: null });
  });

  it('has no workspace field for a business, which adds to its own workspace', async () => {
    const { el, http } = await render('business', {});
    expect(el.querySelector('#site-workspace')).toBeNull();
    fill(el, '#site-url', 'acme.example.com');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne('/api/v1/orgs/acme/websites');
    expect(req.request.body.client_id).toBeUndefined();
  });

  it("adds from a client's page to that client's workspace", async () => {
    const { el, http } = await render('agency', { clientId: 'c1' });
    expect(el.querySelector('#site-workspace')).toBeNull();
    fill(el, '#site-url', 'bakery.example.com');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    expect(http.expectOne('/api/v1/orgs/acme/websites').request.body.client_id).toBe('c1');
  });

  it('moves an existing site to another workspace', async () => {
    const { el, http } = await render('agency', { website: site });
    fill(el, '#site-workspace', 'w-1');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne('/api/v1/orgs/acme/websites/s1');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body.workspace_id).toBe('w-1');
  });
});
