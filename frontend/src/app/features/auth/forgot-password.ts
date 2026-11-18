import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';
import { FieldError, showError } from '../../shared/forms/forms';

@Component({
  selector: 'ol-forgot-password',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, FieldError],
  template: `
    @if (sentTo(); as email) {
      <h1 class="h4 mb-2">Check your email</h1>
      <p class="text-muted">
        If there's an Outlogik account for <strong>{{ email }}</strong>, we've sent a link to
        reset its password. The link works for one hour.
      </p>
      <p class="text-muted small">Nothing arrived? Check your spam folder, or try again in a few minutes.</p>
      <a routerLink="/login" class="btn btn-outline-secondary w-100">Back to sign in</a>
    } @else {
      <h1 class="h4 mb-1">Reset your password</h1>
      <p class="text-muted mb-4">Enter your email and we'll send you a link to choose a new password.</p>
      @if (error()) {
        <div class="alert alert-danger" role="alert">{{ error() }}</div>
      }
      <form [formGroup]="form" (ngSubmit)="submit()" (focusin)="proof.prepare()" novalidate>
        <div class="mb-4">
          <label for="email" class="form-label">Email</label>
          <input id="email" type="email" class="form-control" formControlName="email"
            autocomplete="email" [class.is-invalid]="invalid()" autofocus />
          <ol-field-error [control]="form.controls.email" />
        </div>
        <button type="submit" class="btn btn-primary w-100" [disabled]="busy()">
          @if (busy()) {<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>}
          Send reset link
        </button>
      </form>
      <p class="text-center small mt-4 mb-0"><a routerLink="/login">Back to sign in</a></p>
    }
  `,
})
export class ForgotPassword {
  private readonly auth = inject(AuthService);
  /** The invisible browser check; solved while the person types. */
  protected readonly proof = this.auth.proof();
  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly sentTo = signal<string | null>(null);

  protected invalid(): boolean {
    return showError(this.form.controls.email);
  }

  protected async submit(): Promise<void> {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    try {
      const { email } = this.form.getRawValue();
      await this.auth.forgotPassword(email, this.proof);
      this.sentTo.set(email);
    } catch (err) {
      this.error.set(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
