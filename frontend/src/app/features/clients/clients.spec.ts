import { TestBed } from '@angular/core/testing';

import { ALL, answer, CLIENT_PERMS, flushPending, page, setupOrg } from '../../../testing/org-setup';
import { ClientDetail } from './client-detail';
import { ClientsList } from './clients-list';

const client = {
  id: 'c1', name: 'Bakery Ltd', contact_email: 'jo@bakery.example.com', status: 'active',
  notes: 'Pays late', website_count: 1, portal_user_count: 0,
  created_at: '2026-11-01T00:00:00Z', updated_at: '2026-11-02T00:00:00Z',
};

describe('ClientsList', () => {
  async function render(perms: string[], items = [client]) {
    const http = setupOrg(perms);
    const fixture = TestBed.createComponent(ClientsList);
    fixture.detectChanges();
    await flushPending();
    const req = http.expectOne((r) => r.url === '/api/v1/orgs/acme/clients');
    expect(req.request.params.get('page')).toBe('1');
    req.flush(page(items));
    await flushPending();
    fixture.detectChanges();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  it('lists clients with a link to each', async () => {
    const { el } = await render(ALL);
    const link = el.querySelector('tbody a')!;
    expect(link.textContent).toContain('Bakery Ltd');
    expect(link.getAttribute('href')).toBe('/c1');
    expect(el.textContent).toContain('Add client');
  });

  it('hides "Add client" from roles that cannot create clients', async () => {
    const { el } = await render(CLIENT_PERMS);
    expect(el.textContent).not.toContain('Add client');
  });

  it('shows an empty state with a call to action', async () => {
    const { el } = await render(ALL, []);
    expect(el.textContent).toContain('No clients yet');
    expect(el.textContent).toContain('Add your first client');
  });

  it('searches on the server', async () => {
    const { fixture, http } = await render(ALL);
    const input = fixture.nativeElement.querySelector('input[type="search"]') as HTMLInputElement;
    input.value = 'bak';
    input.dispatchEvent(new Event('input'));
    await new Promise((r) => setTimeout(r, 300));
    await flushPending();
    const req = http.expectOne((r) => r.url === '/api/v1/orgs/acme/clients');
    expect(req.request.params.get('q')).toBe('bak');
  });
});

describe('ClientDetail', () => {
  async function render(perms: string[], roleKey: string | null) {
    const http = setupOrg(perms, roleKey);
    const fixture = TestBed.createComponent(ClientDetail);
    fixture.componentRef.setInput('clientId', 'c1');
    fixture.detectChanges();
    await flushPending();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  it('shows websites and portal access to the agency team', async () => {
    const { fixture, http, el } = await render(ALL, 'owner');
    answer(http, '/api/v1/orgs/acme/clients/c1', client);
    answer(http, '/api/v1/orgs/acme/websites', page([]));
    answer(http, '/api/v1/orgs/acme/clients/c1/users', []);
    await flushPending();
    fixture.detectChanges();
    expect(el.querySelector('h1')!.textContent).toContain('Bakery Ltd');
    expect(el.textContent).toContain('Pays late');
    expect(el.textContent).toContain('Client portal access');
  });

  it('client-portal users see no notes, management or portal section', async () => {
    const { fixture, http, el } = await render(CLIENT_PERMS, 'client');
    answer(http, '/api/v1/orgs/acme/clients/c1', { ...client, notes: null, portal_user_count: null });
    answer(http, '/api/v1/orgs/acme/websites', page([]));
    http.expectNone('/api/v1/orgs/acme/clients/c1/users');
    await flushPending();
    fixture.detectChanges();
    expect(el.textContent).not.toContain('Client portal access');
    expect(el.textContent).not.toContain('Edit');
    expect(el.textContent).not.toContain('Add website');
  });

  it('explains a missing client', async () => {
    const { fixture, http, el } = await render(ALL, 'owner');
    http.expectOne('/api/v1/orgs/acme/clients/c1').flush(null, { status: 404, statusText: 'Not Found' });
    await flushPending();
    fixture.detectChanges();
    expect(el.textContent).toContain('Client not found');
  });
});
