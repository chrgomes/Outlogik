import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { InvitePreview } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { FieldError, PasswordInput, showError } from '../../shared/forms/forms';
import { takeLinkToken } from './link-token';

type View = 'loading' | 'invalid' | 'new-account' | 'sign-in' | 'wrong-account' | 'confirm';

@Component({
  selector: 'ol-accept-invite',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, FieldError, PasswordInput],
  template: `
    @switch (view()) {
      @case ('loading') {
        <div role="status" class="d-flex align-items-center gap-2 text-muted">
          <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
          Opening your invitation…
        </div>
      }
      @case ('invalid') {
        <h1 class="h4 mb-2">This invitation doesn't work</h1>
        <p class="text-muted">
          It may have expired, been cancelled, or already been accepted. Ask the person who
          invited you to send a new one.
        </p>
        <a routerLink="/" class="btn btn-outline-secondary w-100">Continue</a>
      }
      @default {
        @if (invite(); as inv) {
          <h1 class="h4 mb-1">Join {{ inv.organization_name }}</h1>
          <p class="text-muted mb-4">
            {{ inv.invited_by ?? 'Someone' }} invited <strong>{{ inv.email }}</strong> as
            <strong>{{ inv.role_name }}</strong>@if (inv.client_name) {, with access to
            <strong>{{ inv.client_name }}</strong>}.
          </p>
          @if (error()) {
            <div class="alert alert-danger" role="alert">{{ error() }}</div>
          }

          @switch (view()) {
            @case ('new-account') {
              <form [formGroup]="form" (ngSubmit)="accept()" (focusin)="proof.prepare()" novalidate>
                <div class="mb-3">
                  <label for="full_name" class="form-label">Your name</label>
                  <input id="full_name" class="form-control" formControlName="full_name"
                    autocomplete="name" [class.is-invalid]="invalidName()" autofocus />
                  <ol-field-error [control]="form.controls.full_name" />
                </div>
                <div class="mb-4">
                  <label for="password" class="form-label">Choose a password</label>
                  <ol-password-input [control]="form.controls.password" inputId="password"
                    autocomplete="new-password" describedBy="password-hint" />
                  <ol-field-error [control]="form.controls.password" />
                  <div id="password-hint" class="form-text">At least 10 characters.</div>
                </div>
                <button type="submit" class="btn btn-primary w-100" [disabled]="busy()">
                  @if (busy()) {<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>}
                  Create account and join
                </button>
              </form>
            }
            @case ('sign-in') {
              <p>You already have an Outlogik account. Sign in to accept.</p>
              <a routerLink="/login" [queryParams]="{ returnUrl: returnHere() }"
                class="btn btn-primary w-100">Sign in to accept</a>
            }
            @case ('wrong-account') {
              <div class="alert alert-warning" role="status">
                You're signed in as <strong>{{ auth.user()?.email }}</strong>, but this
                invitation is for <strong>{{ inv.email }}</strong>.
              </div>
              <button type="button" class="btn btn-primary w-100" (click)="switchAccount()">
                Sign out and continue
              </button>
            }
            @case ('confirm') {
              <button type="button" class="btn btn-primary w-100" (click)="accept()"
                [disabled]="busy()">
                @if (busy()) {<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>}
                Accept invitation
              </button>
            }
          }
        }
      }
    }
  `,
})
export class AcceptInvite {
  protected readonly auth = inject(AuthService);
  /** The invisible browser check; solved while the person types. */
  protected readonly proof = this.auth.proof();
  private readonly router = inject(Router);
  private readonly token = takeLinkToken();

  protected readonly invite = signal<InvitePreview | null>(null);
  private readonly failed = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly form = inject(NonNullableFormBuilder).group({
    full_name: ['', [Validators.required, Validators.maxLength(200)]],
    password: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(128)]],
  });

  protected readonly view = computed<View>(() => {
    const inv = this.invite();
    if (this.failed()) return 'invalid';
    if (!inv) return 'loading';
    const user = this.auth.user();
    if (user && user.email !== inv.email) return 'wrong-account';
    if (!inv.account_exists) return 'new-account';
    return user ? 'confirm' : 'sign-in';
  });

  constructor() {
    if (!this.token) {
      this.failed.set(true);
      return;
    }
    Promise.all([this.auth.ensureLoaded().catch(() => null), this.auth.previewInvite(this.token)])
      .then(([, inv]) => this.invite.set(inv), () => this.failed.set(true));
  }

  protected invalidName(): boolean {
    return showError(this.form.controls.full_name);
  }

  /** Where to come back to after signing in (the token is needed again). */
  protected returnHere(): string {
    return `/accept-invite?token=${encodeURIComponent(this.token ?? '')}`;
  }

  protected switchAccount(): void {
    void this.auth.logout(false, this.returnHere());
  }

  protected async accept(): Promise<void> {
    this.error.set(null);
    const isNew = this.view() === 'new-account';
    if (isNew && this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    try {
      await this.auth.acceptInvite({ token: this.token!, ...(isNew ? this.form.getRawValue() : {}) }, this.proof);
      await this.router.navigate(['/o', this.invite()!.organization_slug]);
    } catch (err) {
      const problem = apiProblem(err);
      if (problem.code === 'invalid_token') this.failed.set(true);
      else if (!applyFieldErrors(this.form, problem.fields)) this.error.set(problem.message);
    } finally {
      this.busy.set(false);
    }
  }
}
