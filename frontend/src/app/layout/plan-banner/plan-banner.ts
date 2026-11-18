import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CurrentOrgService } from '../../core/current-org.service';
import { PlanService } from '../../core/plan.service';

/**
 * For owners and admins: a trial's last week, and what happens once it has ended or the
 * subscription was cancelled.
 */
@Component({
  selector: 'ol-plan-banner',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    @if (message(); as m) {
      <div class="banner" [class.warn]="m.warn" role="status">
        <span>{{ m.text }}</span>
        <a [routerLink]="['/o', org.slug(), 'settings', 'plan']">See your plan</a>
      </div>
    }
  `,
  styles: `
    .banner {
      display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem 1rem;
      padding: 0.625rem 2rem; border-bottom: 1px solid var(--ol-border);
      background: var(--ol-surface); font-size: 0.875rem;
    }
    .banner.warn { background: var(--bs-warning-bg-subtle); color: var(--bs-warning-text-emphasis); }
    .banner.warn a { color: inherit; }
    @media (max-width: 991.98px) { .banner { padding: 0.625rem 1rem; } }
  `,
})
export class PlanBanner {
  protected readonly org = inject(CurrentOrgService);
  private readonly plan = inject(PlanService);

  protected readonly message = computed(() => {
    const s = this.plan.current();
    if (!s) return null;
    if (s.status === 'trial_ended') {
      return { warn: true, text: 'Your free trial has ended. Everything is kept and you can still edit it, but nothing new can be added until you choose a plan.' };
    }
    if (s.status === 'cancelled') {
      return { warn: true, text: 'Your subscription was cancelled. Everything is kept, but nothing new can be added.' };
    }
    const days = this.plan.trialDaysLeft();
    if (days !== null && days <= 7) {
      return { warn: false, text: days <= 1 ? 'Your free trial ends today.'
        : `Your free trial ends in ${days} days.` };
    }
    return null;
  });
}
