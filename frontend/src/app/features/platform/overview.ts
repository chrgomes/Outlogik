import { DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { Overview, PLATFORM_API } from './platform-api';

interface Tile { label: string; value: number; detail: string; link?: string[]; warn?: boolean; }

/** /admin/platform: totals across Outlogik, and whether background jobs are keeping up. */
@Component({
  selector: 'ol-platform-overview',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe, RouterLink, PageHeader, ErrorState, LoadingState],
  template: `
    <ol-page-header title="Platform overview" description="Everyone using Outlogik, their plans, and the background jobs." />
    @if (data.error()) {
      <ol-error-state message="We couldn't load the overview." (retry)="data.reload()" />
    } @else if (data.value()) {
      @for (group of groups(); track group.title) {
        <h2 class="h6 mt-4 mb-3">{{ group.title }}</h2>
        <div class="po-tiles">
          @for (t of group.tiles; track t.label) {
            @if (t.link) {
              <a class="po-tile" [class.po-warn]="t.warn" [routerLink]="t.link">
                <span class="small text-muted">{{ t.label }}</span>
                <span class="po-value">{{ t.value | number }}</span>
                <span class="small text-muted">{{ t.detail }}</span>
              </a>
            } @else {
              <div class="po-tile" [class.po-warn]="t.warn">
                <span class="small text-muted">{{ t.label }}</span>
                <span class="po-value">{{ t.value | number }}</span>
                <span class="small text-muted">{{ t.detail }}</span>
              </div>
            }
          }
        </div>
      }
      <p class="small text-muted mt-4 mb-0">Revenue isn't shown: plans are assigned by hand until billing exists (H3).</p>
    } @else {
      <ol-loading-state label="Loading the overview…" />
    }
  `,
  styles: `
    .po-tiles { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr)); }
    .po-tile { display: flex; flex-direction: column; gap: 0.2rem; padding: 1rem 1.15rem; border: 1px solid var(--ol-border);
      border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); color: inherit; text-decoration: none; }
    a.po-tile:hover { border-color: var(--ol-text-muted); }
    .po-value { font-size: 1.75rem; font-weight: 600; color: var(--ol-text-strong); line-height: 1.2; }
    .po-warn { border-color: var(--bs-warning-border-subtle); background: var(--bs-warning-bg-subtle);
      .text-muted { color: var(--bs-warning-text-emphasis) !important; } }
  `,
})
export class PlatformOverview {
  protected readonly data = httpResource<Overview>(() => `${PLATFORM_API}/overview`);

  protected readonly groups = computed(() => {
    const o = this.data.value();
    if (!o) return [];
    const orgs = ['/admin', 'platform', 'organizations'];
    const users = ['/admin', 'platform', 'users'];
    const j = o.jobs;
    const stuck = (j.oldest_queued_minutes ?? 0) >= 15;
    return [
      { title: 'Accounts', tiles: [
        { label: 'Businesses', value: o.organizations.business, detail: 'Market their own business', link: orgs },
        { label: 'Agencies', value: o.organizations.agency, detail: 'Also manage clients (counted under Usage)', link: orgs },
        { label: 'New organizations', value: o.organizations.new_30_days, detail: 'In the last 30 days', link: orgs },
        { label: 'Suspended organizations', value: o.organizations.suspended, detail: 'Members can’t use them', link: orgs, warn: o.organizations.suspended > 0 },
        { label: 'Users', value: o.users.total, detail: `${o.users.new_30_days} new in 30 days · ${o.users.unverified} email not confirmed`, link: users },
        { label: 'Suspended users', value: o.users.suspended, detail: 'Can’t sign in', link: users, warn: o.users.suspended > 0 },
      ] as Tile[] },
      { title: 'Plans', tiles: [
        { label: 'On a trial', value: o.subscriptions.trialing, detail: 'The 14-day trial' },
        { label: 'Trial ended', value: o.subscriptions.trial_ended, detail: 'Can read, not add', warn: o.subscriptions.trial_ended > 0 },
        { label: 'Active plans', value: o.subscriptions.active, detail: 'Assigned by staff' },
        { label: 'Past due or cancelled', value: o.subscriptions.past_due + o.subscriptions.cancelled, detail: `${o.subscriptions.past_due} past due · ${o.subscriptions.cancelled} cancelled` },
      ] as Tile[] },
      { title: 'Usage', tiles: [
        { label: 'Active clients', value: o.clients_active, detail: 'Across all agencies' },
        { label: 'Active websites', value: o.websites_active, detail: 'Across all organizations' },
        { label: 'Active invitation codes', value: o.signup_codes_active, detail: 'For signing up during the beta' },
      ] as Tile[] },
      { title: 'Background jobs', tiles: [
        { label: 'Waiting', value: j.queued, detail: j.oldest_queued_minutes === null ? 'Nothing waiting' : `Oldest waiting ${j.oldest_queued_minutes} min`, warn: stuck },
        { label: 'Running', value: j.running, detail: 'Audits, syncs, emails' },
        { label: 'Failed, last 24 hours', value: j.failed_24h, detail: 'Will be retried', warn: j.failed_24h > 0 },
        { label: 'Gave up, last 24 hours', value: j.dead_24h, detail: 'See: python -m app.cli jobs --status dead', warn: j.dead_24h > 0 },
      ] as Tile[] },
    ];
  });
}
