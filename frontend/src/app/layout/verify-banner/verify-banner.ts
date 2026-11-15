import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';

/** Shown in the app until the user confirms their email address. */
@Component({
  selector: 'ol-verify-banner',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (auth.user(); as user) {
      @if (!user.email_verified_at) {
        <div class="banner" role="status">
          <span>
            Please confirm your email address. We sent a link to <strong>{{ user.email }}</strong>.
          </span>
          @switch (state()) {
            @case ('sent') { <span class="text-muted">New link sent.</span> }
            @case ('error') { <span class="text-danger">{{ error() }}</span> }
            @default {
              <button type="button" class="btn btn-link btn-sm p-0" (click)="resend()"
                [disabled]="state() === 'sending'">Resend link</button>
            }
          }
        </div>
      }
    }
  `,
  styles: `
    .banner {
      display: flex; flex-wrap: wrap; align-items: center; gap: 0.25rem 1rem;
      padding: 0.625rem 2rem; border-bottom: 1px solid var(--ol-border);
      background: var(--ol-surface); font-size: 0.875rem;
    }
    @media (max-width: 991.98px) { .banner { padding: 0.625rem 1rem; } }
  `,
})
export class VerifyBanner {
  protected readonly auth = inject(AuthService);
  protected readonly state = signal<'idle' | 'sending' | 'sent' | 'error'>('idle');
  protected readonly error = signal('');

  protected async resend(): Promise<void> {
    this.state.set('sending');
    try {
      await this.auth.resendVerification();
      this.state.set('sent');
    } catch (err) {
      this.error.set(apiProblem(err).message);
      this.state.set('error');
    }
  }
}
