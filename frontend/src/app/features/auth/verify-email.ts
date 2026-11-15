import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { takeLinkToken } from './link-token';

@Component({
  selector: 'ol-verify-email',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    @switch (state()) {
      @case ('working') {
        <div role="status" class="d-flex align-items-center gap-2 text-muted">
          <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
          Confirming your email…
        </div>
      }
      @case ('done') {
        <h1 class="h4 mb-2">Email confirmed</h1>
        <p class="text-muted">Thanks — your email address is confirmed.</p>
        <a routerLink="/" class="btn btn-primary w-100">
          {{ auth.me() ? 'Go to your dashboard' : 'Sign in' }}
        </a>
      }
      @case ('failed') {
        <h1 class="h4 mb-2">This link doesn't work</h1>
        <p class="text-muted">
          It may have expired or already been used. If your email isn't confirmed yet, sign in
          and use “Resend link” to get a new one.
        </p>
        <a routerLink="/" class="btn btn-outline-secondary w-100">Continue</a>
      }
    }
  `,
})
export class VerifyEmail {
  protected readonly auth = inject(AuthService);
  protected readonly state = signal<'working' | 'done' | 'failed'>('working');

  constructor() {
    const token = takeLinkToken();
    if (!token) {
      this.state.set('failed');
      return;
    }
    // Know whether someone is signed in (for the button), then confirm.
    void this.auth.ensureLoaded().catch(() => null)
      .then(() => this.auth.verifyEmail(token))
      .then(() => this.state.set('done'), () => this.state.set('failed'));
  }
}
