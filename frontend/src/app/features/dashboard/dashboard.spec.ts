import { HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { me, membership } from '../../../testing/fixtures';
import { ALL, CLIENT_PERMS, answer, flushPending, setupOrg } from '../../../testing/org-setup';
import { Workspace } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { describe as sentence, timeAgo } from './activity';
import { Dashboard } from './dashboard';
import { ActivityItem, Overview, OverviewRow, WorkspaceDashboard } from './dashboard.types';

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

const BASE = '/api/v1/orgs/acme';
const WS = (over: Partial<Workspace> = {}): Workspace => ({
  id: 'w-own', kind: 'own', name: 'Corner Bakery', client_id: null, client_status: null, website_count: 1,
  created_at: '2026-11-01T00:00:00Z', linked: false, organization_name: null, access: null, ...over,
});
const m = (value: number, previous: number | null) => ({ value, previous });

function workspaceData(over: Partial<WorkspaceDashboard> = {}): WorkspaceDashboard {
  return {
    workspace_id: 'w-own', workspace_name: 'Corner Bakery',
    period: { start: '2026-10-22', end: '2026-11-18', days: 28, compare: 'previous', compare_start: '2026-09-24', compare_end: '2026-10-21' },
    setup: { websites: 1, audited: true, google: 'connected', ga4: true, search_console: true, analytics_visible: true, audits_visible: true },
    changes: ['Visits are up 12% (2,840), mostly from Organic Search (+210) compared with before.'],
    ga4: { through: '2026-11-18', metrics: { sessions: m(2840, 2536), users: m(2260, 2260), new_users: m(800, 700),
      engaged_sessions: m(1700, 1600), page_views: m(7000, 6500), key_events: m(112, null) } },
    search_console: { through: '2026-11-16', metrics: { clicks: m(280, 292), impressions: m(5600, 5000), ctr: m(0.05, 0.058), position: m(8, 8.2) } },
    series: [{ day: '2026-11-18', sessions: 100, previous_sessions: 90, clicks: null, impressions: null }],
    channels: [{ name: 'Organic Search', sessions: 1590, previous: 1380 }],
    ai_referrals: [{ name: 'ChatGPT', sessions: 112, previous: 80 }, { name: 'Perplexity', sessions: 56, previous: 40 }],
    top_pages: [{ path: '/menu', sessions: 640, previous: 542, key_events: 12 }],
    pages_from: null, search_snapshot_end: '2026-11-16',
    almost_ranking: [{ query: 'birthday cakes toronto', page: 'https://cornerbakery.example.com/cakes', clicks: 9, impressions: 1320, position: 8.4 }],
    low_ctr_pages: [{ page: 'https://cornerbakery.example.com/about', clicks: 4, impressions: 760, ctr: 0.005, position: 6.2 }],
    site_ctr: 0.041,
    top_queries: [{ query: 'sourdough near me', clicks: 40, impressions: 900, ctr: 0.044, position: 3.2 }],
    audit: { id: 'a1', workspace_id: 'w-own', website_name: 'cornerbakery.example.com', finished_at: '2026-11-17T10:00:00Z',
      pages_crawled: 42, errors: 2, warnings: 5, notices: 9, new_issues: 1, fixed_issues: 2,
      history: [{ finished_at: '2026-10-17T10:00:00Z', errors: 3, warnings: 6 }, { finished_at: '2026-11-17T10:00:00Z', errors: 2, warnings: 5 }],
      fix_first: [{ check: 'page_broken', title: 'Broken pages', severity: 'error', count: 2 }] },
    ...over,
  };
}

function overviewData(): Overview {
  const row = (over: Partial<OverviewRow>): OverviewRow => ({
    id: 'w1', name: 'Alpha', kind: 'client', linked: false, organization_name: null, website: 'https://alpha.example.com',
    google: 'connected', has_analytics: true, has_search_console: true, visits: 1000, visits_previous: 1000,
    spark: [1, 2, 3], ai_visits: 10, search_clicks: 50, audit: { errors: 0, warnings: 1 }, assigned_to_me: false,
    managers: ['Sam K.'], review: null, ...over });
  return {
    period: { start: '2026-10-22', end: '2026-11-18', days: 28, compare_start: '2026-09-24', compare_end: '2026-10-21' },
    totals: { workspaces: 3, clients: 2, websites: 3, visits: 1700, visits_previous: 2000, ai_visits: 15,
      ai_visits_previous: 10, with_audit_errors: 1, google_not_connected: 1 },
    weekly: [{ week_start: '2026-11-12', sessions: 400, ai_visits: 4 }],
    attention: [{ workspace_id: 'w2', name: 'Beta', kind: 'visits_drop', text: 'Visits down 30% compared with the 28 days before.' }],
    workspaces: [
      row({}),
      row({ id: 'w2', name: 'Beta', visits: 700, visits_previous: 1000, audit: { errors: 2, warnings: 0 }, assigned_to_me: true }),
      row({ id: 'w3', name: 'Gamma', google: 'not_connected', has_analytics: false, visits: null, visits_previous: null, ai_visits: null, audit: null }),
    ],
  };
}

const text = (el: HTMLElement) => el.textContent!.replace(/\s+/g, ' ');

describe('Dashboard', () => {
  async function render(kind: 'business' | 'agency', perms = [...ALL, 'analytics.read', 'audits.read', 'audits.run',
    'integrations.manage', 'workspaces.review'], workspaces = [WS()]) {
    const http = setupOrg(perms, 'owner');
    TestBed.inject(AuthService).me.set(me([membership({ permissions: perms, organization_kind: kind })]));
    const fixture = TestBed.createComponent(Dashboard);
    fixture.detectChanges();
    await flushPending();
    answer(http, `${BASE}/workspaces`, workspaces);
    http.match(`${BASE}/dashboard`).forEach((r) => r.flush({ clients: { total: 0, active: 0, archived: 0 },
      websites: { total: 1, active: 1, paused: 0, archived: 0 }, team: null, recent_activity: null }));
    await flushPending();
    fixture.detectChanges();
    return { http, fixture, el: fixture.nativeElement as HTMLElement };
  }
  const workspaceReq = (http: HttpTestingController) =>
    http.expectOne((r) => r.url === `${BASE}/workspaces/w-own/dashboard`);

  it('shows a business its workspace: what changed, figures, AI tools, search and the audit', async () => {
    const { http, fixture, el } = await render('business');
    const req = workspaceReq(http);
    expect(req.request.params.get('days')).toBe('28');
    expect(req.request.params.get('compare')).toBe('previous');
    req.flush(workspaceData());
    await flushPending();
    fixture.detectChanges();
    const t = text(el);
    expect(t).toContain('What changed');
    expect(t).toContain('Visits are up 12% (2,840)');
    expect(t).toContain('2,840');
    expect(t).toContain('+12% vs before');
    expect(t).toContain('No earlier data to compare'); // key events
    expect(t).toContain('Visits from AI tools');
    expect(t).toContain('168 visits · +40% vs before');
    expect(t).toContain('Searches you almost rank for');
    expect(t).toContain('birthday cakes toronto');
    expect(t).toContain('/about');
    expect(t).toContain('Broken pages');
    expect(t).toContain('1 fewer than the audit before');
    expect(t).not.toContain('Get your dashboard started');
    expect(el.querySelectorAll('ol-chart').length).toBe(3);
  });

  it('changes the period and the comparison', async () => {
    const { http, fixture, el } = await render('business');
    workspaceReq(http).flush(workspaceData());
    await flushPending();
    const period = el.querySelector('#dash-period') as HTMLSelectElement;
    period.value = '90';
    period.dispatchEvent(new Event('change'));
    const compare = el.querySelector('#dash-compare') as HTMLSelectElement;
    compare.value = 'year';
    compare.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    await flushPending();
    const req = workspaceReq(http);
    expect(req.request.params.get('days')).toBe('90');
    expect(req.request.params.get('compare')).toBe('year');
  });

  it('checks a custom range before asking for it', async () => {
    const { http, fixture, el } = await render('business');
    workspaceReq(http).flush(workspaceData());
    await flushPending();
    const period = el.querySelector('#dash-period') as HTMLSelectElement;
    period.value = 'custom';
    period.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    const set = (id: string, v: string) => {
      const i = el.querySelector(id) as HTMLInputElement; i.value = v; i.dispatchEvent(new Event('input'));
    };
    set('#dash-start', '2026-11-10'); set('#dash-end', '2026-11-01');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    expect(text(el)).toContain('The start date is after the end date.');
    set('#dash-end', '2026-11-15');
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    await flushPending();
    const req = workspaceReq(http);
    expect(req.request.params.get('start')).toBe('2026-11-10');
    expect(req.request.params.get('end')).toBe('2026-11-15');
    expect(req.request.params.has('days')).toBe(false);
  });

  it('starts a new business with steps instead of empty charts', async () => {
    const { http, fixture, el } = await render('business');
    workspaceReq(http).flush(workspaceData({
      setup: { websites: 1, audited: false, google: 'not_connected', ga4: false, search_console: false, analytics_visible: true, audits_visible: true },
      changes: [], ga4: null, search_console: null, series: [], channels: [], ai_referrals: [], top_pages: [],
      almost_ranking: [], low_ctr_pages: [], top_queries: [], audit: null }));
    await flushPending();
    fixture.detectChanges();
    const t = text(el);
    expect(t).toContain('Get your dashboard started');
    const steps = [...el.querySelectorAll('.dash-steps > li')].map((li) =>
      [...li.children].slice(0, 2).map((c) => c.textContent!.trim()).join(' '));
    expect(steps).toEqual(['Done 1. Add your website', 'Next 2. Run a website audit', 'Not started 3. Connect Google']);
    expect(t).toContain('Appears when Google Analytics is connected');
    expect(el.querySelectorAll('ol-chart').length).toBe(0);
  });

  it('shows an agency every client, what needs attention, and sorts and filters', async () => {
    const { http, fixture, el } = await render('agency', undefined,
      [WS({ name: 'Agency' }), WS({ id: 'w1', kind: 'client', name: 'Alpha' })]);
    const req = http.expectOne((r) => r.url === `${BASE}/dashboard/overview`);
    expect(req.request.params.get('days')).toBe('28');
    req.flush(overviewData());
    await flushPending();
    fixture.detectChanges();
    const t = text(el);
    expect(t).toContain('Needs attention');
    expect(t).toContain('Visits down 30%');
    expect(t).toContain('−15% vs before'); // all clients
    const names = () => [...el.querySelectorAll('tbody tr td:first-child button')].map((b) => b.textContent!.trim());
    expect(names()).toEqual(['Beta', 'Alpha', 'Gamma']); // biggest drop first, no data last
    const filter = el.querySelector('#filter') as HTMLSelectElement;
    filter.value = 'mine';
    filter.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(names()).toEqual(['Beta']);
    filter.value = 'not_connected';
    filter.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(names()).toEqual(['Gamma']);
    expect(el.querySelector('#dash-compare')).toBeNull();
  });

  it('offers a client report for each client', async () => {
    const { http, fixture, el } = await render('agency', [...ALL, 'analytics.read', 'reports.create'],
      [WS({ name: 'Agency' }), WS({ id: 'w1', kind: 'client', name: 'Alpha' })]);
    http.expectOne((r) => r.url === `${BASE}/dashboard/overview`).flush(overviewData());
    await flushPending();
    fixture.detectChanges();
    const links = [...el.querySelectorAll('a')].filter((a) => a.textContent!.includes('Client report'));
    expect(links.map((a) => a.getAttribute('href'))).toContain('/o/acme/reports?new=w2');
  });

  it('marks a client as reviewed', async () => {
    const { http, fixture, el } = await render('agency', undefined,
      [WS({ name: 'Agency' }), WS({ id: 'w1', kind: 'client', name: 'Alpha' })]);
    http.expectOne((r) => r.url === `${BASE}/dashboard/overview`).flush(overviewData());
    await flushPending();
    fixture.detectChanges();
    const button = [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Mark reviewed'))!;
    button.click();
    const req = http.expectOne((r) => r.method === 'PUT');
    expect(req.request.url).toMatch(/\/workspaces\/w\d\/review$/);
  });

  it('hides team details from people who can’t see the team', async () => {
    const data = overviewData();
    data.workspaces = data.workspaces.map((r) => ({ ...r, managers: null, review: null }));
    const { http, fixture, el } = await render('agency', [...CLIENT_PERMS, 'analytics.read'],
      [WS({ name: 'Agency' }), WS({ id: 'w1', kind: 'client', name: 'Alpha' })]);
    http.expectOne((r) => r.url === `${BASE}/dashboard/overview`).flush(data);
    await flushPending();
    fixture.detectChanges();
    expect(text(el)).not.toContain('Account manager');
    expect(text(el)).not.toContain('Mark reviewed');
  });
});
