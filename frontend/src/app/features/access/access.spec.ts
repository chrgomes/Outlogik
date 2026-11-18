import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { me, membership } from '../../../testing/fixtures';
import { ALL, answer, dialogProviders, flushPending, page, setupOrg } from '../../../testing/org-setup';
import { AccessGrant, Workspace } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { DialogService } from '../../shared/dialog/dialog';
import { MemberWorkspacesDialog } from '../settings/member-workspaces-dialog';
import { WebsitesList } from '../websites/websites-list';
import { AcceptAccess } from './accept-access';
import { AgencyAccess } from './agency-access';

const GRANT_PERMS = [...ALL, 'access_grants.manage', 'linked_accounts.manage'];
const confirmYes = { provide: DialogService, useValue: { confirm: async () => true, open: async () => undefined } };

function grant(over: Partial<AccessGrant>): AccessGrant {
  return {
    id: 'g1', email: 'jo@agency.example.com', access: 'manage', status: 'active',
    agency_name: 'Northline Agency', invited_by: 'Olive', accepted_by: 'Jo Agent',
    created_at: '2026-11-01T00:00:00Z', expires_at: '2026-11-15T00:00:00Z',
    accepted_at: '2026-11-02T00:00:00Z', revoked_at: null, ...over,
  };
}

function ws(over: Partial<Workspace>): Workspace {
  return {
    id: 'w-own', kind: 'own', name: 'Acme', client_id: null, client_status: null, website_count: 0,
    created_at: '2026-11-18T00:00:00Z', linked: false, organization_name: null, access: null, ...over,
  };
}

describe('Agency access (business)', () => {
  async function render(grants: AccessGrant[]) {
    const http = setupOrg(GRANT_PERMS, 'owner', [confirmYes]);
    TestBed.inject(AuthService).me.set(me([membership({ permissions: GRANT_PERMS, organization_kind: 'business' })]));
    const fixture = TestBed.createComponent(AgencyAccess);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/access-grants', grants);
    await flushPending();
    fixture.detectChanges();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  it('lists agencies with their access and who accepted', async () => {
    const { el } = await render([grant({}), grant({ id: 'g2', status: 'pending', agency_name: null,
      accepted_by: null, email: 'new@other.example.com', access: 'view' })]);
    const rows = [...el.querySelectorAll('tbody tr')].map((r) => r.textContent!.replace(/\s+/g, ' ').trim());
    expect(rows[0]).toContain('Northline Agency');
    expect(rows[0]).toContain('Accepted by Jo Agent');
    expect(rows[0]).toContain('End access');
    expect(rows[1]).toContain('Sent to new@other.example.com');
    expect(rows[1]).toContain('View only');
    expect(rows[1]).toContain('Cancel');
  });

  it('sends access to an agency', async () => {
    const { el, http, fixture } = await render([]);
    expect(el.textContent).toContain('No agencies yet');
    const input = el.querySelector('#grant-email') as HTMLInputElement;
    input.value = 'jo@agency.example.com';
    input.dispatchEvent(new Event('input'));
    (el.querySelector('#access-view') as HTMLInputElement).click();
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    const req = http.expectOne((r) => r.method === 'POST' && r.url === '/api/v1/orgs/acme/access-grants');
    expect(req.request.body).toEqual({ email: 'jo@agency.example.com', access: 'view' });
  });

  it('ends an agency’s access', async () => {
    const { el, http } = await render([grant({})]);
    (el.querySelector('tbody .btn-link') as HTMLButtonElement).click();
    await flushPending();
    const req = http.expectOne((r) => r.method === 'DELETE');
    expect(req.request.url).toBe('/api/v1/orgs/acme/access-grants/g1');
  });
});

describe('Accept agency access', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([
        { path: 'agency-access', component: AcceptAccess },
        { path: '**', children: [] },
      ])],
    });
    TestBed.inject(AuthService).me.set(me());
    return TestBed.inject(HttpTestingController);
  }

  const preview = (agencies: { organization_id: string; slug: string; name: string }[]) => ({
    business_name: 'Corner Bakery', workspace_name: 'Corner Bakery', access: 'manage',
    email: 'olive@acme.example.com', invited_by: 'Bea Baker', expires_at: '2026-12-01T00:00:00Z', agencies,
  });

  it('accepts into the chosen agency and opens its websites', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/agency-access?token=tok-1234567890');
    const req = http.expectOne('/api/v1/access-grants/preview');
    expect(req.request.body).toEqual({ token: 'tok-1234567890' });
    req.flush(preview([{ organization_id: 'o1', slug: 'one', name: 'One Agency' },
      { organization_id: 'o2', slug: 'two', name: 'Two Agency' }]));
    await flushPending();
    harness.detectChanges();
    const el = harness.routeNativeElement!;
    expect(el.textContent).toContain('Corner Bakery shared their workspace');
    const select = el.querySelector('#agency') as HTMLSelectElement;
    select.value = 'o2';
    select.dispatchEvent(new Event('change'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const accept = http.expectOne('/api/v1/access-grants/accept');
    expect(accept.request.body).toEqual({ token: 'tok-1234567890', organization_id: 'o2' });
    accept.flush([membership({ organization_id: 'o2', organization_slug: 'two' })]);
    await flushPending();
    http.expectOne('/api/v1/auth/me').flush(me([membership({ organization_id: 'o2', organization_slug: 'two' })]));
    await flushPending();
    expect(TestBed.inject(Router).url).toBe('/o/two/websites');
  });

  it('explains when the person can’t accept for any agency', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/agency-access?token=tok-1234567890');
    http.expectOne('/api/v1/access-grants/preview').flush(preview([]));
    await flushPending();
    harness.detectChanges();
    expect(harness.routeNativeElement!.textContent).toContain('owner or administrator of an agency');
    expect(harness.routeNativeElement!.querySelector('button[type=submit]')).toBeNull();
  });

  it('shows the API’s reason when the link is for someone else', async () => {
    const http = setup();
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/agency-access?token=tok-1234567890');
    http.expectOne('/api/v1/access-grants/preview').flush(
      { error: { code: 'wrong_account', message: 'This access link was sent to a different email address.', details: null } },
      { status: 403, statusText: 'Forbidden' });
    await flushPending();
    harness.detectChanges();
    expect(harness.routeNativeElement!.textContent).toContain('sent to a different email address');
  });
});

describe('Choosing a member’s workspaces', () => {
  const member = (key: string) => ({
    id: 'm1', user_id: 'u1', email: 'am@acme.example.com', full_name: 'Avery Manager',
    role: { id: 'r1', name: key === 'client' ? 'Client Viewer' : 'Account Manager', system_key: key,
      workspace_scope: 'assigned' as const },
    status: 'active' as const, joined_at: '2026-11-01T00:00:00Z', is_you: false,
  });
  const list = [ws({}), ws({ id: 'w1', kind: 'client', name: 'Bakery', client_id: 'c1', client_status: 'active' }),
    ws({ id: 'w9', name: 'Corner Shop', linked: true, organization_name: 'Corner Shop', access: 'manage' })];

  async function render(key: string, assigned: string[]) {
    const http = setupOrg(ALL, 'owner', dialogProviders(member(key)));
    const fixture = TestBed.createComponent(MemberWorkspacesDialog);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/workspaces', list);
    answer(http, '/api/v1/orgs/acme/members/m1/workspaces', list.filter((w) => assigned.includes(w.id))
      .map(({ id, kind, name }) => ({ id, kind, name })));
    await flushPending();
    fixture.detectChanges();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  it('shows every workspace, ticks the assigned ones, and saves the new list', async () => {
    const { el, http } = await render('account_manager', ['w1']);
    const labels = [...el.querySelectorAll('.form-check-label')].map((l) => l.textContent!.replace(/\s+/g, ' ').trim());
    expect(labels).toEqual(['Acme', 'Bakery', 'Corner Shop · shared by Corner Shop']);
    expect((el.querySelector('#ws-w1') as HTMLInputElement).checked).toBe(true);
    (el.querySelector('#ws-w9') as HTMLInputElement).click();
    (el.querySelector('.btn-primary') as HTMLButtonElement).click();
    const req = http.expectOne('/api/v1/orgs/acme/members/m1/workspaces');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body.workspace_ids.sort()).toEqual(['w1', 'w9']);
  });

  it('offers Client Viewers only client workspaces', async () => {
    const { el } = await render('client', []);
    expect([...el.querySelectorAll('.form-check-label')].map((l) => l.textContent!.trim())).toEqual(['Bakery']);
  });
});

describe('Websites in a view-only linked workspace', () => {
  it('hides changes and explains why', async () => {
    localStorage.setItem('ol.workspace.acme', 'w9');
    const http = setupOrg(ALL);
    const fixture = TestBed.createComponent(WebsitesList);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/workspaces', [ws({}),
      ws({ id: 'w9', name: 'Corner Shop', linked: true, organization_name: 'Corner Shop', access: 'view' })]);
    await flushPending();
    fixture.detectChanges();
    await flushPending();
    http.expectOne((r) => r.url === '/api/v1/orgs/acme/workspaces/w9/websites').flush(page([{
      id: 's1', workspace_id: 'w9', workspace_name: 'Corner Shop', client_id: null, client_name: null,
      name: 'cornershop.example.com', url: 'https://cornershop.example.com', domain: 'cornershop.example.com',
      status: 'active', created_at: '2026-11-18T00:00:00Z', updated_at: '2026-11-18T00:00:00Z' }]));
    await flushPending();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('view-only access');
    expect(el.textContent).not.toContain('Add website');
    expect(el.querySelector('tbody .icon-action')).toBeNull();
    localStorage.clear();
  });
});
