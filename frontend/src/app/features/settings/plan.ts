import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { PlanService } from '../../core/plan.service';
import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';

const STATUS: Record<string, string> = {
  trialing: 'Free trial', active: 'Active', past_due: 'Payment overdue',
  cancelled: 'Cancelled', trial_ended: 'Trial ended',
};

/** The organization's plan, its limits and current usage (owners and admins). */
@Component({
  selector: 'ol-plan',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CurrencyPipe, DatePipe, PageHeader, ErrorState, LoadingState],
  template: `
    <ol-page-header title="Plan" description="Your plan, what it includes, and how much of it you're using." />

    @if (plan.subscription.error()) {
      <ol-error-state message="We couldn't load your plan." (retry)="plan.subscription.reload()" />
    } @else if (plan.current(); as s) {
      <section class="settings-card mb-4">
        <div class="d-flex flex-wrap align-items-baseline gap-2 mb-1">
          <h2 class="h4 mb-0">{{ s.plan.name }}</h2>
          <span [class]="'badge rounded-pill fw-medium ' + badge()">{{ statusLabel() }}</span>
        </div>
        <p class="text-muted mb-0">
          @if (s.billing_interval === 'annual') {
            {{ s.plan.annual_price_cents / 100 | currency: s.plan.currency : 'symbol-narrow' }} a year, paid upfront
            ({{ s.plan.annual_price_cents / 1200 | currency: s.plan.currency : 'symbol-narrow' }} a month)
          } @else {
            {{ s.plan.monthly_price_cents / 100 | currency: s.plan.currency : 'symbol-narrow' }} a month
          }
          · {{ s.plan.currency }}, plus tax
        </p>
        @if (s.status === 'trialing' && s.trial_ends_at) {
          <p class="mb-0 mt-2">Your free trial ends on <strong>{{ s.trial_ends_at | date: 'longDate' }}</strong>.</p>
        }
        @if (s.status === 'trial_ended' || s.status === 'cancelled') {
          <p class="mb-0 mt-2">Everything you've added is kept and can still be edited. Nothing new can be added until you have a plan.</p>
        }
      </section>

      <section class="settings-card mb-4">
        <h2 class="h6 mb-3">What's included</h2>
        @for (l of s.limits; track l.key) {
          <div class="limit">
            <div class="d-flex justify-content-between gap-3">
              <span>{{ l.label }}</span>
              <span class="tabular-nums" [class.text-danger]="l.limit !== null && l.used >= l.limit">
                {{ l.used }} of {{ l.limit === null ? 'unlimited' : l.limit }}
              </span>
            </div>
            @if (l.limit) {
              <div class="meter" role="progressbar" [attr.aria-label]="l.label"
                [attr.aria-valuenow]="l.used" aria-valuemin="0" [attr.aria-valuemax]="l.limit">
                <div class="meter-fill" [class.full]="l.used >= l.limit"
                  [style.width.%]="l.used >= l.limit ? 100 : (l.used / l.limit) * 100"></div>
              </div>
            }
          </div>
        }
      </section>

      <p class="text-muted small">
        To change your plan{{ s.billing_interval === 'monthly' ? ' or switch to annual billing (20% off)' : '' }}, email
        <a href="mailto:sales@outlogik.com">sales@outlogik.com</a>.
      </p>
    } @else {
      <ol-loading-state label="Loading your plan…" />
    }
  `,
  styles: `
    .settings-card { max-width: 40rem; padding: 1.5rem; border: 1px solid var(--ol-border);
      border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); }
    .badge { font-size: 0.75rem; display: inline-block; }
    .text-bg-success-subtle { background: var(--bs-success-bg-subtle); color: var(--bs-success-text-emphasis); }
    .text-bg-warning-subtle { background: var(--bs-warning-bg-subtle); color: var(--bs-warning-text-emphasis); }
    .text-bg-secondary-subtle { background: var(--ol-surface-active); color: var(--ol-text); }
    .limit + .limit { margin-top: 1rem; }
    .meter { height: 0.375rem; margin-top: 0.375rem; border-radius: 999px; overflow: hidden;
      background: var(--ol-surface-active); }
    .meter-fill { height: 100%; border-radius: inherit; background: var(--ol-accent); }
    .meter-fill.full { background: var(--bs-danger); }
  `,
})
export class Plan {
  protected readonly plan = inject(PlanService);
  protected readonly statusLabel = computed(() => STATUS[this.plan.current()?.status ?? ''] ?? '');
  protected readonly badge = computed(() => {
    const status = this.plan.current()?.status;
    if (status === 'active') return 'text-bg-success-subtle';
    if (status === 'trialing') return 'text-bg-secondary-subtle';
    return 'text-bg-warning-subtle';
  });

  constructor() {
    this.plan.subscription.reload(); // usage changes as people work
  }
}
