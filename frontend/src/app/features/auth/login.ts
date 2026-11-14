import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { apiProblem, safeReturnUrl } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';
import { FieldError, PasswordInput, showError } from '../../shared/forms/forms';

@Component({
  selector: 'ol-login',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, FieldError, PasswordInput],
  template: `
    <h1 class="h4 mb-1">Sign in</h1>
    <p class="text-muted mb-4">Welcome back to Outlogik.</p>

    @if (reason() === 'expired') {
      <div class="alert alert-info" role="status">Your session has ended. Please sign in again.</div>
    }
    @if (reset()) {
      <div class="alert alert-success" role="status">Your password has been changed. Sign in with the new one.</div>
    }
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }

    <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
      <div class="mb-3">
        <label for="email" class="form-label">Email</label>
        <input id="email" type="email" class="form-control" formControlName="email"
          autocomplete="username" [class.is-invalid]="invalid('email')" autofocus />
        <ol-field-error [control]="form.controls.email" />
      </div>
      <div class="mb-4">
        <div class="d-flex justify-content-between align-items-baseline">
          <label for="password" class="form-label">Password</label>
          <a routerLink="/forgot-password" class="small">Forgot password?</a>
        </div>
        <ol-password-input [control]="form.controls.password" inputId="password" />
        <ol-field-error [control]="form.controls.password" />
      </div>
      <button type="submit" class="btn btn-primary w-100" [disabled]="busy()">
        @if (busy()) {<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>}
        Sign in
      </button>
    </form>

    <p class="text-center text-muted small mt-4 mb-0">
      New to Outlogik? <a routerLink="/register">Create an account</a>
    </p>
  `,
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  readonly returnUrl = input<string>();
  readonly reason = input<string>();
  readonly reset = input<string>();
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected invalid(name: 'email' | 'password'): boolean {
    return showError(this.form.controls[name]);
  }

  protected async submit(): Promise<void> {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    try {
      const { email, password } = this.form.getRawValue();
      await this.auth.login(email, password);
      await this.router.navigateByUrl(safeReturnUrl(this.returnUrl()));
    } catch (err) {
      this.error.set(apiProblem(err).message);
      this.form.controls.password.reset();
    } finally {
      this.busy.set(false);
    }
  }
}
