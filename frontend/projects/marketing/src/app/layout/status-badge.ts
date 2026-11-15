import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { FeatureStatus } from '../config/site';

/** Honest status label for a client-portal feature. */
@Component({
  selector: 'mk-status-badge',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (status() === 'in_development') {
      <span class="mk-badge">In development</span>
    } @else if (showAvailable()) {
      <span class="mk-badge mk-badge--available">Available</span>
    }
  `,
})
export class StatusBadge {
  readonly status = input.required<FeatureStatus>();
  readonly showAvailable = input(false);
}
