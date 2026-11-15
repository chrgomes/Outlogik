import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { EmptyState } from '../../shared/states/states';

@Component({
  selector: 'ol-not-found',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <h1 class="h4">Page not found</h1>
    <p class="text-muted">
      This page doesn't exist, or you don't have access to it.
    </p>
    <a routerLink="/" class="btn btn-primary w-100">Go to your dashboard</a>
  `,
})
export class NotFound {}

@Component({
  selector: 'ol-no-organization',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1 class="h4">You're not in an organization</h1>
    <p class="text-muted">
      Ask an organization owner or admin to invite you, then open the link in their email.
    </p>
    <button type="button" class="btn btn-outline-secondary w-100" (click)="auth.logout()">
      Sign out
    </button>
  `,
})
export class NoOrganization {
  protected readonly auth = inject(AuthService);
}

@Component({
  selector: 'ol-no-access',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyState, RouterLink],
  template: `
    <ol-empty-state icon="shield-lock" title="You don't have access to this page"
      message="Your role doesn't include this. An owner or admin can change your role.">
      <a [routerLink]="['/o', org.slug()]" class="btn btn-outline-secondary">Back to dashboard</a>
    </ol-empty-state>
  `,
})
export class NoAccess {
  protected readonly org = inject(CurrentOrgService);
}
