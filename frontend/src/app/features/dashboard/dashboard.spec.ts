import { TestBed } from '@angular/core/testing';

import { ALL, CLIENT_PERMS, answer, flushPending, setupOrg } from '../../../testing/org-setup';
import { describe as sentence, timeAgo } from './activity';
import { Dashboard } from './dashboard';
import { ActivityItem, DashboardSummary } from './dashboard.types';

const item = (action: string, meta: Record<string, unknown> = {}, actor: string | null = 'Olive'): ActivityItem =>
  ({ id: action, action, actor_name: actor, target_type: null, target_id: null, meta,
    created_at: '2026-11-14T10:00:00Z' });

describe('activity sentences', () => {
  it.each([
    [item('client.create', { name: 'Bakery Ltd' }), 'Olive added client Bakery Ltd'],
    [item('client.update', { name: 'Bakery Ltd', status: 'archived' }), 'Olive archived client Bakery Ltd'],
    [item('member.update', { user_email: 'tom@x.com', role: { from: 'Team Member', to: 'Admin' } }), 'Olive made tom@x.com Admin'],
    [item('invitation.create', { email: 'jo@x.com', role: 'Client' }), 'Olive invited jo@x.com as Client'],
    [item('organization.update', { name: { from: 'A', to: 'B' } }), 'Olive renamed the organization to B'],
    [item('website.create', { url: 'https://x.com' }, null), 'Someone added website https://x.com'],
    [item('something.new'), 'Olive: something.new'],
  ])('%#', (input, expected) => expect(sentence(input)).toBe(expected));
});

describe('timeAgo', () => {
  const now = Date.parse('2026-11-14T12:00:00Z');
  it('reads naturally', () => {
    expect(timeAgo('2026-11-14T11:59:40Z', now)).toBe('just now');
    expect(timeAgo('2026-11-14T11:55:00Z', now)).toBe('5 minutes ago');
    expect(timeAgo('2026-11-14T09:00:00Z', now)).toBe('3 hours ago');
    expect(timeAgo('2026-11-13T12:00:00Z', now)).toBe('yesterday');
  });
});

describe('Dashboard', () => {
  const summary = (over: Partial<DashboardSummary> = {}): DashboardSummary => ({
    clients: { total: 3, active: 2, archived: 1 },
    websites: { total: 4, active: 3, paused: 1, archived: 0 },
    team: { members: 2, client_users: 1, pending_invitations: 0 },
    recent_activity: [item('client.create', { name: 'Bakery Ltd' })],
    ...over,
  });

  async function render(perms: string[], data: DashboardSummary, roleKey = 'owner') {
    const http = setupOrg(perms, roleKey);
    const fixture = TestBed.createComponent(Dashboard);
    fixture.detectChanges();
    await flushPending();
    answer(http, '/api/v1/orgs/acme/dashboard', data);
    await flushPending();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const tiles = [...el.querySelectorAll('.tile')].map((t) => [
      t.querySelector('.tile-label')!.textContent!.trim(),
      t.querySelector('.tile-value')!.textContent!.trim(),
      t.querySelector('.tile-detail')!.textContent!.trim(),
    ]);
    return { el, tiles };
  }

  it('shows real counts, activity and the Phase 2 placeholders', async () => {
    const { el, tiles } = await render(ALL, summary());
    expect(tiles).toEqual([
      ['Active clients', '2', '1 archived'],
      ['Active websites', '3', '1 paused'],
      ['Team members', '2', '1 client-portal user'],
      ['Pending invitations', '0', 'Links expire after 7 days'],
    ]);
    expect(el.textContent).toContain('Olive added client Bakery Ltd');
    expect(el.querySelectorAll('.not-connected').length).toBe(4);
    // Phase 2 cards never show numbers.
    expect(el.querySelector('.upcoming-grid')!.textContent).not.toMatch(/\d/);
    // Everything is done except inviting the team? Members > 1 counts as done.
    expect(el.querySelector('.checklist')).toBeNull();
  });

  it('shows a first-run checklist from real counts', async () => {
    const empty = summary({ clients: { total: 0, active: 0, archived: 0 },
      websites: { total: 0, active: 0, paused: 0, archived: 0 },
      team: { members: 1, client_users: 0, pending_invitations: 0 } });
    const { el } = await render(ALL, empty);
    const items = [...el.querySelectorAll('.checklist li')].map((li) => li.textContent!.trim());
    expect(items).toEqual(['Add your first client', 'Add a website', 'Invite your team']);
  });

  it('client-portal users get their counts only, no team or activity', async () => {
    const { el, tiles } = await render(CLIENT_PERMS,
      summary({ team: null, recent_activity: null }), 'client');
    expect(tiles.map((t) => t[0])).toEqual(['Active clients', 'Active websites']);
    expect(el.textContent).not.toContain('Recent activity');
    expect(el.querySelector('.checklist')).toBeNull();
  });
});
