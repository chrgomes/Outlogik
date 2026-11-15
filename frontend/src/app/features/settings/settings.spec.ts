import { TestBed } from '@angular/core/testing';

import { ALL, answer, dialogProviders, flushPending, page, setupOrg } from '../../../testing/org-setup';
import { InviteDialog } from './invite-dialog';
import { RoleEditorDialog } from './role-editor-dialog';
import { Team } from './team';

const role = (id: string, name: string, key: string | null, permissions: string[] = []) => ({
  id, name, description: `${name} role`, is_system: key !== null, system_key: key, permissions,
  member_count: 1, created_at: '2026-11-01T00:00:00Z',
});
const ROLES = [role('r-o', 'Owner', 'owner'), role('r-a', 'Admin', 'admin'),
  role('r-m', 'Team Member', 'member'), role('r-c', 'Client', 'client')];
const member = (id: string, name: string, key: string, isYou = false) => ({
  id, user_id: `u-${id}`, email: `${id}@acme.example.com`, full_name: name,
  role: { id: `r-${key[0]}`, name: key, system_key: key }, status: 'active',
  joined_at: '2026-11-01T00:00:00Z', is_you: isYou,
});

describe('Team page', () => {
  async function render(roleKey: string) {
    const http = setupOrg(ALL.filter((p) => roleKey === 'owner' || p !== 'roles.manage'), roleKey);
    const fixture = TestBed.createComponent(Team);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/members', page([
      member('me', 'Me Myself', roleKey, true), member('own', 'Olive Owner', 'owner'),
      member('tm', 'Tom Member', 'member'),
    ]));
    answer(http, '/api/v1/orgs/acme/invitations', page([]));
    await flushPending();
    fixture.detectChanges();
    const rows = [...fixture.nativeElement.querySelectorAll('tbody tr')] as HTMLElement[];
    return rows.map((r) => ({ name: r.querySelector('.fw-medium')!.textContent!.trim(),
      hasActions: !!r.querySelector('button[aria-label^="Actions"]') }));
  }

  it('admins can act on members but not on owners or themselves', async () => {
    expect(await render('admin')).toEqual([
      { name: 'Me Myself', hasActions: false },
      { name: 'Olive Owner', hasActions: false },
      { name: 'Tom Member', hasActions: true },
    ]);
  });

  it('owners can act on other owners', async () => {
    const rows = await render('owner');
    expect(rows.find((r) => r.name === 'Olive Owner')!.hasActions).toBe(true);
    expect(rows.find((r) => r.name === 'Me Myself')!.hasActions).toBe(false);
  });
});

describe('Invite dialog', () => {
  async function render(roleKey: string) {
    const http = setupOrg(ALL, roleKey, dialogProviders(undefined));
    const fixture = TestBed.createComponent(InviteDialog);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/roles', page(ROLES));
    answer(http, '/api/v1/orgs/acme/clients', page([{ id: 'c1', name: 'Bakery Ltd' }]));
    await flushPending();
    fixture.detectChanges();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  const options = (el: HTMLElement, id: string) =>
    [...el.querySelectorAll(`#${id} option:not([disabled])`)].map((o) => o.textContent!.trim());

  it('only owners can invite owners', async () => {
    expect(options((await render('admin')).el, 'invite-role')).toEqual(['Admin', 'Team Member', 'Client']);
  });

  it('asks which client a client-portal user can see', async () => {
    const { fixture, el, http } = await render('owner');
    expect(el.querySelector('#invite-client')).toBeNull();
    const select = el.querySelector('#invite-role') as HTMLSelectElement;
    select.value = 'r-c';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(options(el, 'invite-client')).toEqual(['Bakery Ltd']);

    (el.querySelector('#invite-email') as HTMLInputElement).value = 'jo@bakery.example.com';
    el.querySelector('#invite-email')!.dispatchEvent(new Event('input'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    http.expectNone('/api/v1/orgs/acme/invitations');
    expect(el.textContent).toContain('This field is required.');
  });
});

describe('Role editor', () => {
  async function render(data: object) {
    const http = setupOrg(undefined, undefined, dialogProviders(data));
    const fixture = TestBed.createComponent(RoleEditorDialog);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/permissions', [
      { code: 'clients.read', description: 'View clients', group: 'Clients' },
      { code: 'clients.write', description: 'Create and edit clients', group: 'Clients' },
      { code: 'roles.read', description: 'View roles', group: 'Roles' },
    ]);
    await flushPending();
    fixture.detectChanges();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  it('shows built-in roles read-only', async () => {
    const { el } = await render({ role: role('r-m', 'Team Member', 'member', ['clients.read']) });
    expect(el.querySelector('fieldset')!.disabled).toBe(true);
    expect((el.querySelector('#perm-clients\\.read') as HTMLInputElement).checked).toBe(true);
    expect(el.textContent).not.toContain('Save changes');
  });

  it('groups permissions and requires at least one', async () => {
    const { fixture, el, http } = await render({});
    expect([...el.querySelectorAll('.perm-group-title')].map((h) => h.textContent)).toEqual(['Clients', 'Roles']);
    (el.querySelector('#role-name') as HTMLInputElement).value = 'SEO';
    el.querySelector('#role-name')!.dispatchEvent(new Event('input'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    http.expectNone('/api/v1/orgs/acme/roles');
    expect(el.textContent).toContain('Choose at least one permission.');

    (el.querySelector('#perm-clients\\.read') as HTMLInputElement).click();
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne('/api/v1/orgs/acme/roles');
    expect(req.request.body).toEqual({ name: 'SEO', description: null, permissions: ['clients.read'] });
  });
});
