import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { me, membership } from '../../../testing/fixtures';
import { answer, dialogProviders, flushPending, setupOrg } from '../../../testing/org-setup';
import { Workspace } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { staffGuard } from '../../core/guards';
import { WorkspaceService } from '../../core/workspace.service';
import { DialogService } from '../../shared/dialog/dialog';
import { Dashboard } from '../dashboard/dashboard';
import { AccountPage } from './account';

const BASE = '/api/v1/orgs/acme';
const PORTAL = ['organization.read', 'dashboard.read', 'clients.read', 'websites.read', 'audits.read',
  'analytics.read', 'reports.read'];
const ws = (over: Partial<Workspace> = {}): Workspace => ({
  id: 'w1', kind: 'client', name: 'Alpha Dental', client_id: 'c1', client_status: 'active', website_count: 1,
  created_at: '2026-11-01T00:00:00Z', linked: false, organization_name: null, access: null, ...over,
});
const text = (el: HTMLElement) => el.textContent!.replace(/\s+/g, ' ');

function asClient(http: HttpTestingController) {
  TestBed.inject(AuthService).me.set(me([membership({ role_key: 'client', role_name: 'Client Viewer',
    workspace_scope: 'assigned', organization_name: 'Northline', permissions: PORTAL })]));
  return http;
}

describe('Client portal', () => {
  beforeEach(() => localStorage.clear());

  it('always has one of the client’s own workspaces selected, never "All"', async () => {
    const http = asClient(setupOrg(PORTAL, 'client'));
    const service = TestBed.inject(WorkspaceService);
    TestBed.tick();
    answer(http, `${BASE}/workspaces`, [ws(), ws({ id: 'w2', name: 'Alpha Clinic' })]);
    await flushPending();
    expect(service.current()?.id).toBe('w1');
    expect(service.canSeeAll()).toBe(false);
    service.select(null);
    expect(service.current()?.id).toBe('w1');
    service.select('w2');
    expect(service.current()?.id).toBe('w2');
  });

  it('shows the client their own dashboard and their account manager', async () => {
    const http = asClient(setupOrg(PORTAL, 'client'));
    const fixture = TestBed.createComponent(Dashboard);
    fixture.detectChanges();
    await flushPending();
    answer(http, `${BASE}/workspaces`, [ws()]);
    http.match(`${BASE}/dashboard`).forEach((r) => r.flush({ clients: { total: 1, active: 1, archived: 0 },
      websites: { total: 1, active: 1, paused: 0, archived: 0 }, team: null, recent_activity: null }));
    await flushPending();
    fixture.detectChanges();
    await flushPending();
    http.expectNone(`${BASE}/dashboard/overview`);
    answer(http, `${BASE}/workspaces/w1/contacts`, { organization_name: 'Northline', contacts: [
      { name: 'Sam Kumar', email: 'sam@northline.example.com', role: 'account_manager' }] });
    http.expectOne((r) => r.url === `${BASE}/workspaces/w1/dashboard`).flush({
      workspace_id: 'w1', workspace_name: 'Alpha Dental',
      period: { start: '2026-10-27', end: '2026-11-23', days: 28, compare: 'previous', compare_start: null, compare_end: null },
      setup: { websites: 1, audited: false, google: 'not_connected', ga4: false, search_console: false,
        analytics_visible: true, audits_visible: true },
      changes: [], ga4: null, search_console: null, series: [], channels: [], ai_referrals: [], top_pages: [],
      pages_from: null, search_snapshot_end: null, almost_ranking: [], low_ctr_pages: [], site_ctr: null,
      top_queries: [], audit: null });
    await flushPending();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const t = text(el);
    expect(t).toContain('Your account manager');
    expect(el.querySelector('a[href="mailto:sam@northline.example.com"]')).not.toBeNull();
    expect(t).toContain('Appears when Northline connects Google Analytics.');
    expect(t).toContain('No audit yet. Northline will run the first one.');
    expect(t).not.toContain('Integrations');
    expect(t).not.toContain('Get your dashboard started');
  });

  it('sends client users away from agency pages', async () => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(),
      provideRouter([{ path: 'o/:orgSlug/clients', canActivate: [staffGuard], children: [] },
        { path: 'o/:orgSlug/dashboard', children: [] }])] });
    TestBed.inject(AuthService).me.set(me([membership({ role_key: 'client', permissions: PORTAL })]));
    TestBed.inject(CurrentOrgService).slug.set('acme');
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/o/acme/clients');
    expect(TestBed.inject(Router).url).toBe('/o/acme/dashboard');
  });
});

describe('Your account', () => {
  async function render() {
    const http = setupOrg(['dashboard.read'], 'owner', [...dialogProviders(null),
      { provide: DialogService, useValue: { confirm: async () => true } }]);
    TestBed.inject(AuthService).me.set(me([membership({}), membership({ organization_id: 'o2', organization_name: 'Second Co', role_name: 'Client Viewer' })]));
    const fixture = TestBed.createComponent(AccountPage);
    fixture.detectChanges();
    await flushPending();
    return { http, fixture, el: fixture.nativeElement as HTMLElement };
  }
  const type = (el: HTMLElement, id: string, value: string) => {
    const input = el.querySelector(id) as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  };

  it('changes your name', async () => {
    const { el, http, fixture } = await render();
    expect(text(el)).toContain('Second Co · Client Viewer');
    type(el, '#acct-name', 'Olive Baker');
    fixture.detectChanges();
    el.querySelectorAll('form')[0].dispatchEvent(new Event('submit'));
    const req = http.expectOne('/api/v1/auth/me');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ full_name: 'Olive Baker' });
  });

  it('changes your password, and shows a wrong current password on its field', async () => {
    const { el, http, fixture } = await render();
    type(el, '#acct-current', 'old-password');
    type(el, '#acct-new', 'short');
    el.querySelectorAll('form')[1].dispatchEvent(new Event('submit'));
    http.expectNone('/api/v1/auth/change-password');
    type(el, '#acct-new', 'A-new-long-password');
    el.querySelectorAll('form')[1].dispatchEvent(new Event('submit'));
    const req = http.expectOne('/api/v1/auth/change-password');
    expect(req.request.body).toEqual({ current_password: 'old-password', new_password: 'A-new-long-password' });
    req.flush({ error: { code: 'wrong_password', message: 'That isn’t your current password.',
      details: [{ field: 'current_password', message: 'That isn’t your current password.' }] } },
    { status: 400, statusText: 'Bad Request' });
    await flushPending();
    fixture.detectChanges();
    expect(text(el)).toContain('That isn’t your current password.');
  });

  it('signs out everywhere after confirming', async () => {
    const { el, http } = await render();
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Sign out everywhere'))!.click();
    await flushPending();
    expect(http.expectOne('/api/v1/auth/logout-all').request.method).toBe('POST');
  });
});
