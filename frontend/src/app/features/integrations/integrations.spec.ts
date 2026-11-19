import { TestBed } from '@angular/core/testing';

import { me, membership } from '../../../testing/fixtures';
import { ALL, answer, flushPending, setupOrg } from '../../../testing/org-setup';
import { AnalyticsSummary, GoogleIntegration, Workspace } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { DialogService } from '../../shared/dialog/dialog';
import { IntegrationsPage } from './integrations';

const MANAGE = [...ALL, 'integrations.read', 'integrations.manage', 'analytics.read'];
const VIEW = [...ALL, 'integrations.read', 'analytics.read'];
const BASE = '/api/v1/orgs/acme/workspaces/w-own';
const confirmYes = { provide: DialogService, useValue: { confirm: async () => true } };

const workspace: Workspace = {
  id: 'w-own', kind: 'own', name: 'Bakery', client_id: null, client_status: null, website_count: 1,
  created_at: '2026-11-18T00:00:00Z', linked: false, organization_name: null, access: null,
};

function integration(over: Partial<GoogleIntegration> = {}): GoogleIntegration {
  return {
    configured: true, connected: true, status: 'connected', account_email: 'marketing@bakery.example.com',
    connected_at: '2026-11-19T00:00:00Z', last_error: null,
    sources: [{ id: 'd1', kind: 'ga4', external_id: 'properties/123', name: 'bakery.example.com (Bakery)',
      sync_status: 'ok', last_synced_at: '2026-11-19T05:30:00Z', synced_through: '2026-11-18', last_error: null }],
    ...over,
  };
}

const m = (value: number, previous: number | null) => ({ value, previous });
const summary: AnalyticsSummary = {
  days: 28, start: '2026-10-22', end: '2026-11-18',
  ga4: { sessions: m(2800, 2000), users: m(2240, 2240), new_users: m(840, 800),
    engaged_sessions: m(1680, 1500), page_views: m(7000, 6000), key_events: m(112, null) },
  search_console: null, series: [],
  channels: [{ name: 'Organic Search', sessions: 1960, previous: 1500 }],
  ai_referrals: [{ name: 'ChatGPT', sessions: 112, previous: 80 }],
  top_queries: [], top_queries_through: null,
};

async function render(perms: string[], google: GoogleIntegration, extra = [confirmYes]) {
  const http = setupOrg(perms, 'owner', extra);
  TestBed.inject(AuthService).me.set(me([membership({ permissions: perms, organization_kind: 'business' })]));
  const fixture = TestBed.createComponent(IntegrationsPage);
  fixture.detectChanges();
  await flushPending();
  answer(http, '/api/v1/orgs/acme/workspaces', [workspace]);
  await flushPending();
  answer(http, `${BASE}/integrations/google`, google);
  await flushPending();
  fixture.detectChanges();
  return { http, fixture, el: fixture.nativeElement as HTMLElement };
}

describe('Integrations', () => {
  it('explains when Google isn’t set up on the server', async () => {
    const { el } = await render(MANAGE, integration({ configured: false, connected: false, status: null, sources: [] }));
    expect(el.textContent).toContain("Google isn't set up on this Outlogik server yet");
    expect(el.querySelector('section button')).toBeNull();
  });

  it('starts connecting and sends the person to Google', async () => {
    const { el, http } = await render(MANAGE, integration({ connected: false, status: null, sources: [] }));
    const button = [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Connect Google'))!;
    button.click();
    const req = http.expectOne(`${BASE}/integrations/google/connect`);
    expect(req.request.method).toBe('POST');
  });

  it('shows the connection, what is synced and the 28-day summary', async () => {
    const { el, http, fixture } = await render(MANAGE, integration());
    answer(http, `${BASE}/analytics/summary`, summary);
    await flushPending();
    fixture.detectChanges();
    const text = el.textContent!.replace(/\s+/g, ' ');
    expect(text).toContain('Connected as marketing@bakery.example.com');
    expect(text).toContain('Google Analytics: bakery.example.com (Bakery)');
    expect(text).toContain('2,800');
    expect(text).toContain('+40% vs before');
    expect(text).toContain('No earlier data to compare'); // key events have no full previous period
    expect(text).toContain('Visits from AI tools');
    expect(text).toContain('ChatGPT');
    expect(text).toContain('Sync now');
  });

  it('asks to reconnect when Google withdrew access', async () => {
    const { el, http } = await render(MANAGE, integration({
      status: 'error', last_error: 'Google no longer accepts this connection. Reconnect Google to start syncing again.' }));
    answer(http, `${BASE}/analytics/summary`, { ...summary, ga4: null, ai_referrals: [], channels: [] });
    expect(el.textContent).toContain('Reconnect Google');
    expect(el.querySelector('.alert-warning')!.textContent).toContain('no longer accepts');
  });

  it('chooses what to sync from what the account can see', async () => {
    const { el, http, fixture } = await render(MANAGE, integration({ sources: [] }));
    answer(http, `${BASE}/analytics/summary`, { ...summary, ga4: null });
    answer(http, `${BASE}/integrations/google/available`, {
      ga4: [{ id: 'properties/123', name: 'bakery.example.com', account: 'Bakery' }],
      search_console: [{ site_url: 'sc-domain:bakery.example.com', permission: 'siteOwner' }] });
    await flushPending();
    fixture.detectChanges();
    const ga4 = el.querySelector('#ga4') as HTMLSelectElement;
    ga4.value = 'properties/123';
    ga4.dispatchEvent(new Event('change'));
    const gsc = el.querySelector('#gsc') as HTMLSelectElement;
    gsc.value = 'sc-domain:bakery.example.com';
    gsc.dispatchEvent(new Event('change'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne(`${BASE}/integrations/google/sources`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ ga4_property: 'properties/123', search_console_site: 'sc-domain:bakery.example.com' });
  });

  it('disconnects after confirming', async () => {
    const { el, http } = await render(MANAGE, integration());
    answer(http, `${BASE}/analytics/summary`, summary);
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Disconnect'))!.click();
    await flushPending();
    const req = http.expectOne((r) => r.method === 'DELETE');
    expect(req.request.url).toBe(`${BASE}/integrations/google`);
  });

  it('without permission to manage, only shows what is connected', async () => {
    const { el, http, fixture } = await render(VIEW, integration());
    answer(http, `${BASE}/analytics/summary`, summary);
    await flushPending();
    fixture.detectChanges();
    expect(el.textContent).toContain('Connected as');
    expect(el.textContent).not.toContain('Disconnect');
    expect(el.textContent).not.toContain('Sync now');
    expect(el.textContent).not.toContain("Change what's synced");
  });
});
