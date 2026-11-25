import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { me } from '../../../testing/fixtures';
import { flushPending } from '../../../testing/org-setup';
import { AuthService } from '../../core/auth.service';
import { DialogService } from '../../shared/dialog/dialog';
import { PlatformCodes } from './codes';
import { PlatformOrganization } from './organization';
import { PlatformOverview } from './overview';
import { OrgDetail, PLATFORM_API, UserDetail } from './platform-api';
import { PlatformUser } from './user';

const ALL = ['orgs.suspend', 'plans.assign', 'platform.read', 'signup_codes.manage', 'users.suspend'];
const text = (el: HTMLElement) => el.textContent!.replace(/\s+/g, ' ');

function setup(caps = ALL, dialog?: object) {
  TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
    ...(dialog ? [{ provide: DialogService, useValue: dialog }] : [])] });
  TestBed.inject(AuthService).me.set(me([], { id: 'staff-1', platform_role: 'platform_admin', platform_caps: caps }));
  return TestBed.inject(HttpTestingController);
}

function org(over: Partial<OrgDetail> = {}): OrgDetail {
  return {
    id: 'o1', name: 'Corner Bakery', slug: 'corner-bakery', kind: 'business', status: 'active',
    plan: 'Digital Professional', subscription_status: 'trialing', trial_ends_at: '2026-12-01T00:00:00Z',
    members: 1, clients: 0, websites: 1, created_at: '2026-11-17T00:00:00Z', suspended_reason: null,
    signup_code: 'Beta wave 1 (…9TWD)', billing_interval: 'monthly',
    limits: [{ key: 'limits.websites', label: 'Websites', limit: 10, used: 1 }],
    members_list: [{ user_id: 'u1', name: 'Bea Baker', email: 'bea@bakery.example.com', role: 'Owner', status: 'active', user_active: true }],
    history: [], ...over,
  };
}
const PLANS = [{ key: 'digital_starter', name: 'Digital Starter', account_kind: 'business' },
  { key: 'digital_professional', name: 'Digital Professional', account_kind: 'business' },
  { key: 'agency_starter', name: 'Agency Starter', account_kind: 'agency' }];

describe('Platform overview', () => {
  it('shows totals and flags job trouble', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(PlatformOverview);
    fixture.detectChanges();
    http.expectOne(`${PLATFORM_API}/overview`).flush({
      users: { total: 12, active: 11, suspended: 1, unverified: 3, new_30_days: 5 },
      organizations: { business: 4, agency: 2, suspended: 0, new_30_days: 3 },
      subscriptions: { trialing: 3, trial_ended: 1, active: 2, past_due: 0, cancelled: 0 },
      clients_active: 7, websites_active: 9, signup_codes_active: 2,
      jobs: { queued: 4, running: 1, failed_24h: 0, dead_24h: 1, oldest_queued_minutes: 22 } });
    await flushPending();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const tiles = [...el.querySelectorAll('.po-tile')].map((t) => [...t.children].map((c) => c.textContent!.trim()).join(' '));
    expect(tiles).toContain('Businesses 4 Market their own business');
    expect(tiles).toContain('New organizations 3 In the last 30 days');
    expect(text(el)).toContain('Oldest waiting 22 min');
    expect(text(el)).toContain('Revenue isn’t shown'.replace('’', "'"));
    expect(el.querySelectorAll('.po-warn').length).toBe(4); // suspended users, trial ended, waiting, gave up
  });
});

describe('Platform organization', () => {
  async function render(caps = ALL, dialog?: object, detail = org()) {
    const http = setup(caps, dialog);
    const fixture = TestBed.createComponent(PlatformOrganization);
    (fixture.componentRef as ComponentRef<PlatformOrganization>).setInput('orgId', 'o1');
    fixture.detectChanges();
    http.expectOne(`${PLATFORM_API}/organizations/o1`).flush(detail);
    if (caps.includes('plans.assign')) http.expectOne(`${PLATFORM_API}/plans`).flush(PLANS);
    await flushPending();
    fixture.detectChanges();
    return { http, fixture, el: fixture.nativeElement as HTMLElement };
  }

  it('shows the plan, usage, members and the code used', async () => {
    const { el } = await render();
    const t = text(el);
    expect(t).toContain('Signed up with invitation code Beta wave 1 (…9TWD)');
    expect([...el.querySelectorAll('#usage-h + table td')].map((td) => td.textContent!.trim())).toEqual(['Websites', '1 of 10']);
    expect(t).toContain('bea@bakery.example.com');
    // Only plans for this kind of account
    expect([...el.querySelectorAll('#p-plan option')].map((o) => o.textContent)).toEqual(['Digital Starter', 'Digital Professional']);
  });

  it('assigns a plan, with the trial length for a trial', async () => {
    const { el, http, fixture } = await render();
    const status = el.querySelector('#p-status') as HTMLSelectElement;
    status.value = 'trialing';
    status.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    (el.querySelector('#p-days') as HTMLInputElement).value = '30';
    el.querySelector('#p-days')!.dispatchEvent(new Event('input'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne(`${PLATFORM_API}/organizations/o1/plan`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ plan: 'digital_professional', status: 'trialing', interval: 'monthly', trial_days: 30 });
  });

  it('suspends with a reason', async () => {
    const dialog = { open: vi.fn(async () => 'Unpaid invoices'), confirm: async () => true };
    const { el, http } = await render(ALL, dialog);
    [...el.querySelectorAll('button')].find((b) => b.textContent!.includes('Suspend Corner Bakery'))!.click();
    await flushPending();
    const req = http.expectOne(`${PLATFORM_API}/organizations/o1/suspend`);
    expect(req.request.body).toEqual({ reason: 'Unpaid invoices' });
  });

  it('read-only staff see no plan form or suspend button', async () => {
    const { el } = await render(['platform.read', 'users.suspend']);
    expect(el.querySelector('#p-plan')).toBeNull();
    expect(text(el)).not.toContain('Suspend Corner Bakery');
  });

  it('shows why a suspended organization is suspended', async () => {
    const { el } = await render(ALL, undefined, org({ status: 'suspended', suspended_reason: 'Unpaid invoices' }));
    expect(text(el)).toContain('Suspended. Unpaid invoices');
    expect(text(el)).toContain('Reactivate');
  });
});

describe('Platform user', () => {
  function user(over: Partial<UserDetail> = {}): UserDetail {
    return { id: 'u1', name: 'Bea Baker', email: 'bea@bakery.example.com', active: true, verified: true,
      staff_role: null, super_admin: false, organizations: 1, last_login_at: null, created_at: '2026-11-17T00:00:00Z',
      suspended_reason: null, memberships: [], history: [], ...over };
  }
  async function render(detail: UserDetail, caps = ALL) {
    const http = setup(caps);
    const fixture = TestBed.createComponent(PlatformUser);
    (fixture.componentRef as ComponentRef<PlatformUser>).setInput('userId', detail.id);
    fixture.detectChanges();
    http.expectOne(`${PLATFORM_API}/users/${detail.id}`).flush(detail);
    await flushPending();
    fixture.detectChanges();
    return text(fixture.nativeElement as HTMLElement);
  }

  it('can suspend a customer, but not yourself or other staff', async () => {
    expect(await render(user())).toContain('Suspend Bea Baker');
    TestBed.resetTestingModule();
    expect(await render(user({ id: 'staff-1', name: 'Me' }))).not.toContain('Suspend Me');
    TestBed.resetTestingModule();
    const staffMember = await render(user({ id: 'u2', name: 'Sam', staff_role: 'billing_admin' }));
    expect(staffMember).toContain('Outlogik staff · Billing admin');
    expect(staffMember).not.toContain('Suspend Sam');
  });
});

describe('Invitation codes', () => {
  it('makes a code and shows it once', async () => {
    const http = setup();
    const fixture = TestBed.createComponent(PlatformCodes);
    fixture.detectChanges();
    http.expectOne(`${PLATFORM_API}/signup-codes`).flush([]);
    await flushPending();
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    fixture.detectChanges();
    expect(text(el)).toContain('Say who the code is for');
    const label = el.querySelector('#c-label') as HTMLInputElement;
    label.value = 'Beta wave 1';
    label.dispatchEvent(new Event('input'));
    const uses = el.querySelector('#c-uses') as HTMLInputElement;
    uses.value = '20';
    uses.dispatchEvent(new Event('input'));
    el.querySelector('form')!.dispatchEvent(new Event('submit'));
    const req = http.expectOne((r) => r.method === 'POST' && r.url === `${PLATFORM_API}/signup-codes`);
    expect(req.request.body).toEqual({ label: 'Beta wave 1', account_type: null, max_uses: 20, expires_in_days: null });
    req.flush({ id: 'c1', label: 'Beta wave 1', hint: '9TWD', account_type: null, max_uses: 20, uses: 0,
      expires_at: null, revoked_at: null, status: 'active', created_at: '2026-11-25T00:00:00Z', created_by: 'Pat', code: 'K7PM-3QXR-9TWD' });
    await flushPending();
    fixture.detectChanges();
    expect(text(el)).toContain('K7PM-3QXR-9TWD');
    expect(text(el)).toContain('won’t be shown again'.replace('’', "'"));
  });
});
