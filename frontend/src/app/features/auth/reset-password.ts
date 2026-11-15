import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import {
  AbstractControl,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';
import { FieldError, PasswordInput } from '../../shared/forms/forms';
import { takeLinkToken } from './link-token';

function matchPassword(control: AbstractControl): ValidationErrors | null {
  const parent = control.parent;
  return parent && control.value !== parent.get('password')?.value ? { mismatch: true } : null;
}

@Component({
  selector: 'ol-reset-password',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, FieldError, PasswordInput],
  template: `
    @if (!token || linkInvalid()) {
      <h1 class="h4 mb-2">This link doesn't work</h1>
      <p class="text-muted">
        Password reset links work once and expire after an hour. Request a new one and use the
        most recent email.
      </p>
      <a routerLink="/forgot-password" class="btn btn-primary w-100">Request a new link</a>
    } @else {
      <h1 class="h4 mb-1">Choose a new password</h1>
      <p class="text-muted mb-4">You'll be signed out on all your devices.</p>
      @if (error()) {
        <div class="alert alert-danger" role="alert">{{ error() }}</div>
      }
      <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
        <div class="mb-3">
          <label for="password" class="form-label">New password</label>
          <ol-password-input [control]="form.controls.password" inputId="password"
            autocomplete="new-password" describedBy="password-hint" />
          <ol-field-error [control]="form.controls.password" />
          <div id="password-hint" class="form-text">At least 10 characters.</div>
        </div>
        <div class="mb-4">
          <label for="confirm" class="form-label">Repeat new password</label>
          <ol-password-input [control]="form.controls.confirm" inputId="confirm"
            autocomplete="new-password" />
          <ol-field-error [control]="form.controls.confirm" />
        </div>
        <button type="submit" class="btn btn-primary w-100" [disabled]="busy()">
          @if (busy()) {<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>}
          Change password
        </button>
      </form>
    }
  `,
})
export class ResetPassword {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  protected readonly token = takeLinkToken();
  protected readonly form = inject(NonNullableFormBuilder).group({
    password: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(128)]],
    confirm: ['', [Validators.required, matchPassword]],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly linkInvalid = signal(false);

  constructor() {
    this.form.controls.password.valueChanges.subscribe(() =>
      this.form.controls.confirm.updateValueAndValidity({ emitEvent: false }),
    );
  }

  protected async submit(): Promise<void> {
    this.error.set(null);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    try {
      await this.auth.resetPassword(this.token!, this.form.getRawValue().password);
      this.auth.clear();
      await this.router.navigate(['/login'], { queryParams: { reset: 1 } });
    } catch (err) {
      const problem = apiProblem(err);
      if (problem.code === 'invalid_token') this.linkInvalid.set(true);
      else if (!applyFieldErrors(this.form, problem.fields)) this.error.set(problem.message);
    } finally {
      this.busy.set(false);
    }
  }
}
