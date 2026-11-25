import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';

/** /suspended/:orgSlug: Outlogik staff suspended this organization (it isn't deleted). */
@Component({
  selector: 'ol-suspended',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <h1 class="h4 mb-2">{{ name() }} is suspended</h1>
    <p class="text-muted">
      Outlogik has paused this organization, so it can't be used right now. Nothing has been
      deleted. If you think this is a mistake, contact Outlogik.
    </p>
    @if (others().length) {
      <p class="mb-2">You can still open:</p>
      <ul class="list-unstyled mb-4">
        @for (m of others(); track m.organization_slug) {
          <li><a [routerLink]="['/o', m.organization_slug]">{{ m.organization_name }}</a></li>
        }
      </ul>
    }
    <button type="button" class="btn btn-outline-secondary w-100" (click)="auth.logout()">Sign out</button>
  `,
})
export class SuspendedPage {
  readonly orgSlug = input.required<string>();
  protected readonly auth = inject(AuthService);
  protected readonly name = computed(() =>
    this.auth.memberships().find((m) => m.organization_slug === this.orgSlug())?.organization_name ?? 'This organization');
  protected readonly others = computed(() =>
    this.auth.memberships().filter((m) => m.organization_slug !== this.orgSlug() && m.organization_status !== 'suspended'));
}
