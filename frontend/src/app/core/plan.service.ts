import { httpResource } from '@angular/common/http';
import { Injectable, computed, inject } from '@angular/core';

import { Subscription } from './api.types';
import { CurrentOrgService } from './current-org.service';

const DAY = 24 * 60 * 60 * 1000;

/** The current organization's plan and usage, for people who may see it (owners, admins). */
@Injectable({ providedIn: 'root' })
export class PlanService {
  private readonly org = inject(CurrentOrgService);

  readonly subscription = httpResource<Subscription>(() => {
    const slug = this.org.slug();
    return this.org.area() === 'org' && slug && this.org.can('plan.read')
      ? `/api/v1/orgs/${slug}/subscription` : undefined;
  });
  readonly current = computed(() => (this.subscription.hasValue() ? this.subscription.value() : null));
  /** Whole days left in a trial (rounded up), or null outside a trial. */
  readonly trialDaysLeft = computed(() => {
    const s = this.current();
    if (s?.status !== 'trialing' || !s.trial_ends_at) return null;
    return Math.max(0, Math.ceil((new Date(s.trial_ends_at).getTime() - Date.now()) / DAY));
  });
}
