import { ChangeDetectionStrategy, Component } from '@angular/core';

/** Replaced by the real sign-in page in step 8. */
@Component({
  selector: 'ol-login-placeholder',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1 class="h4">Sign in</h1>
    <p class="text-muted mb-0">The sign-in page arrives in step 8 of Phase 1.</p>
  `,
})
export class LoginPlaceholder {}
