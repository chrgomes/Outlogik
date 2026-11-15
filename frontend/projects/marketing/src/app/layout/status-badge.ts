import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { ModuleStatus } from '../config/site';

/** "In development" label for modules that aren't built yet. Available modules show nothing. */
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
  readonly status = input.required<ModuleStatus>();
  readonly showAvailable = input(false);
}
