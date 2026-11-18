import { Type } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { ALL, answer, flushPending, setupOrg } from '../../../testing/org-setup';
import { Subscription } from '../../core/api.types';
import { PlanBanner } from '../../layout/plan-banner/plan-banner';
import { Plan } from './plan';

const PERMS = [...ALL, 'plan.read'];
const DAY = 24 * 60 * 60 * 1000;

function subscription(over: Partial<Subscription> = {}): Subscription {
  return {
    plan: { key: 'agency_starter', name: 'Agency Starter', account_kind: 'agency', currency: 'CAD',
      monthly_price_cents: 7900, annual_price_cents: 75840 },
    status: 'active', billing_interval: 'monthly', trial_ends_at: null, current_period_end: null,
    limits: [
      { key: 'limits.websites', label: 'Websites (archived ones don’t count)', limit: 10, used: 3 },
      { key: 'limits.clients', label: 'Clients (archived ones don’t count)', limit: 5, used: 5 },
      { key: 'limits.team_members', label: 'Team members', limit: null, used: 2 },
    ],
    ...over,
  };
}

async function render<T>(component: Type<T>, body: Subscription, perms = PERMS) {
  const http = setupOrg(perms);
  const fixture = TestBed.createComponent(component);
  fixture.detectChanges();
  await flushPending();
  if (perms.includes('plan.read')) answer(http, '/api/v1/orgs/acme/subscription', body);
  await flushPending();
  fixture.detectChanges();
  return { http, el: fixture.nativeElement as HTMLElement };
}

describe('Plan page', () => {
  it('shows the plan, its price and usage against each limit', async () => {
    const { el } = await render(Plan, subscription());
    const text = el.textContent!.replace(/\s+/g, ' ');
    expect(text).toContain('Agency Starter');
    expect(text).toContain('Active');
    expect(text).toContain('$79.00 a month');
    expect(text).toContain('3 of 10');
    expect(text).toContain('2 of unlimited');
    // At the limit: shown in red, and the bar is full.
    const full = el.querySelectorAll('.meter-fill')[1] as HTMLElement;
    expect(full.classList).toContain('full');
    expect(el.querySelectorAll('.meter').length).toBe(2); // none for unlimited
    expect(el.querySelector('.badge')!.className).toContain('text-bg-success-subtle');
  });

  it('shows annual billing as a yearly price paid upfront', async () => {
    const { el } = await render(Plan, subscription({ billing_interval: 'annual' }));
    expect(el.textContent).toContain('$758.40 a year, paid upfront');
    expect(el.textContent).toContain('$63.20 a month');
  });

  it('says when a trial ends, and what happens after it has', async () => {
    const ends = new Date(Date.now() + 5 * DAY).toISOString();
    let { el } = await render(Plan, subscription({ status: 'trialing', trial_ends_at: ends }));
    expect(el.textContent).toContain('Free trial');
    expect(el.textContent).toContain('Your free trial ends on');
    TestBed.resetTestingModule();
    ({ el } = await render(Plan, subscription({ status: 'trial_ended' })));
    expect(el.textContent).toContain('Trial ended');
    expect(el.textContent).toContain('Nothing new can be added');
  });
});

describe('Plan banner', () => {
  it('appears in a trial’s last week', async () => {
    const soon = new Date(Date.now() + 3 * DAY - 60_000).toISOString();
    const { el } = await render(PlanBanner, subscription({ status: 'trialing', trial_ends_at: soon }));
    expect(el.textContent).toContain('Your free trial ends in 3 days.');
    expect(el.querySelector('a')!.getAttribute('href')).toBe('/o/acme/settings/plan');
  });

  it('stays out of the way earlier in a trial', async () => {
    const later = new Date(Date.now() + 12 * DAY).toISOString();
    const { el } = await render(PlanBanner, subscription({ status: 'trialing', trial_ends_at: later }));
    expect(el.querySelector('.banner')).toBeNull();
  });

  it('explains a trial that has ended', async () => {
    const { el } = await render(PlanBanner, subscription({ status: 'trial_ended' }));
    expect(el.querySelector('.banner.warn')!.textContent).toContain('Your free trial has ended');
  });

  it('isn’t shown to people who can’t see the plan', async () => {
    const { el, http } = await render(PlanBanner, subscription({ status: 'trial_ended' }), ALL);
    http.expectNone('/api/v1/orgs/acme/subscription');
    expect(el.querySelector('.banner')).toBeNull();
  });
});
