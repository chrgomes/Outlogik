import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';
import { FieldError, PasswordInput, showError } from '../../shared/forms/forms';

@Component({
  selector: 'ol-register',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, FieldError, PasswordInput],
  template: `
    <h1 class="h4 mb-1">Create your agency account</h1>
    <p class="text-muted mb-4">You'll be the owner of a new Outlogik workspace.</p>

    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }

    <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
      <div class="mb-3">
        <label for="full_name" class="form-label">Your name</label>
        <input id="full_name" class="form-control" formControlName="full_name" autocomplete="name"
          [class.is-invalid]="invalid('full_name')" autofocus />
        <ol-field-error [control]="form.controls.full_name" />
      </div>
      <div class="mb-3">
        <label for="organization_name" class="form-label">Agency name</label>
        <input id="organization_name" class="form-control" formControlName="organization_name"
          autocomplete="organization" [class.is-invalid]="invalid('organization_name')" />
        <ol-field-error [control]="form.controls.organization_name" />
      </div>
      <div class="mb-3">
        <label for="email" class="form-label">Work email</label>
        <input id="email" type="email" class="form-control" formControlName="email"
          autocomplete="email" [class.is-invalid]="invalid('email')" />
        <ol-field-error [control]="form.controls.email" />
        @if (emailTaken()) {
          <div class="form-text">Already have an account? <a routerLink="/login">Sign in</a>.</div>
        }
      </div>
      <div class="mb-4">
        <label for="password" class="form-label">Password</label>
        <ol-password-input [control]="form.controls.password" inputId="password"
          autocomplete="new-password" describedBy="password-hint" />
        <ol-field-error [control]="form.controls.password" />
        <div id="password-hint" class="form-text">At least 10 characters. A short phrase works well.</div>
      </div>
      <button type="submit" class="btn btn-primary w-100" [disabled]="busy()">
        @if (busy()) {<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>}
        Create account
      </button>
    </form>

    <p class="text-center text-muted small mt-4 mb-0">
      Already have an account? <a routerLink="/login">Sign in</a>
    </p>
  `,
})
export class Register {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  protected readonly form = inject(NonNullableFormBuilder).group({
    full_name: ['', [Validators.required, Validators.maxLength(200)]],
    organization_name: ['', [Validators.required, Validators.maxLength(200)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(128)]],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly emailTaken = signal(false);

  protected invalid(name: keyof typeof this.form.controls): boolean {
    return showError(this.form.controls[name]);
  }

  protected async submit(): Promise<void> {
    this.error.set(null);
    this.emailTaken.set(false);
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    try {
      const me = await this.auth.register(this.form.getRawValue());
      await this.router.navigate(['/o', me.memberships[0].organization_slug]);
    } catch (err) {
      const problem = apiProblem(err);
      if (problem.code === 'email_taken') {
        this.form.controls.email.setErrors({ server: problem.message });
        this.emailTaken.set(true);
      } else if (!applyFieldErrors(this.form, problem.fields)) {
        this.error.set(problem.message);
      }
    } finally {
      this.busy.set(false);
    }
  }
}
