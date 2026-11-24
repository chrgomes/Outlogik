import { HttpClient } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { Me } from '../../core/api.types';
import { AuthService } from '../../core/auth.service';
import { DialogService } from '../../shared/dialog/dialog';
import { FieldError, PasswordInput, showError } from '../../shared/forms/forms';
import { PageHeader } from '../../shared/page-header/page-header';
import { ToastService } from '../../shared/toast/toast';

/** Your own account: name, password, signing out everywhere, and where you're a member. */
@Component({
  selector: 'ol-account',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FieldError, PasswordInput, PageHeader],
  template: `
    <ol-page-header title="Your account" description="Your name, password and where you're signed in." />

    <div class="acct">
      <section class="ol-card-block" aria-labelledby="details-h">
        <h2 id="details-h" class="h6 mb-3">Your details</h2>
        <form [formGroup]="profile" (ngSubmit)="saveName()" novalidate>
          <div class="mb-3">
            <label for="acct-name" class="form-label">Name</label>
            <input id="acct-name" class="form-control" formControlName="full_name" autocomplete="name"
              [class.is-invalid]="bad(profile.controls.full_name)" />
            <ol-field-error [control]="profile.controls.full_name" />
          </div>
          <div class="mb-3">
            <label for="acct-email" class="form-label">Email</label>
            <input id="acct-email" class="form-control" [value]="auth.user()?.email" readonly aria-describedby="acct-email-hint" />
            <div id="acct-email-hint" class="form-text">You sign in with this address. To use a different one, ask the person who invited you to invite the new address.</div>
          </div>
          <button type="submit" class="btn btn-primary" [disabled]="busy() === 'name' || profile.pristine">Save</button>
        </form>
      </section>

      <section class="ol-card-block" aria-labelledby="password-h">
        <h2 id="password-h" class="h6 mb-1">Password</h2>
        <p class="small text-muted mb-3">Changing it signs you out on your other devices, and we email you to let you know.</p>
        <form [formGroup]="password" (ngSubmit)="changePassword()" novalidate>
          <div class="mb-3">
            <label for="acct-current" class="form-label">Current password</label>
            <ol-password-input [control]="password.controls.current_password" inputId="acct-current" autocomplete="current-password" />
            <ol-field-error [control]="password.controls.current_password" />
          </div>
          <div class="mb-3">
            <label for="acct-new" class="form-label">New password</label>
            <ol-password-input [control]="password.controls.new_password" inputId="acct-new"
              autocomplete="new-password" describedBy="acct-new-hint" />
            <ol-field-error [control]="password.controls.new_password" />
            <div id="acct-new-hint" class="form-text">At least 10 characters. A short phrase works well.</div>
          </div>
          <button type="submit" class="btn btn-primary" [disabled]="busy() === 'password'">Change password</button>
        </form>
      </section>

      <section class="ol-card-block" aria-labelledby="sessions-h">
        <h2 id="sessions-h" class="h6 mb-1">Signed-in devices</h2>
        <p class="small text-muted mb-3">If you signed in on a shared or lost device, sign out everywhere. You'll need to sign in again here too.</p>
        <button type="button" class="btn btn-outline-secondary" (click)="signOutEverywhere()">Sign out everywhere</button>
      </section>

      <section class="ol-card-block" aria-labelledby="orgs-h">
        <h2 id="orgs-h" class="h6 mb-3">Where you're a member</h2>
        <ul class="list-unstyled mb-0 acct-orgs">
          @for (m of auth.memberships(); track m.organization_id) {
            <li><span class="fw-medium">{{ m.organization_name }}</span>{{ ' ' }}<span class="text-muted">· {{ m.role_name }}</span></li>
          }
        </ul>
      </section>
    </div>
  `,
  styles: `
    .acct { display: grid; gap: 1.5rem; max-width: 40rem; }
    .ol-card-block { padding: 1.25rem 1.5rem; border: 1px solid var(--ol-border); border-radius: var(--bs-border-radius-lg);
      background: var(--ol-surface-raised); }
    .acct-orgs li + li { margin-top: 0.4rem; }
  `,
})
export class AccountPage {
  protected readonly auth = inject(AuthService);
  private readonly http = inject(HttpClient);
  private readonly toast = inject(ToastService);
  private readonly dialog = inject(DialogService);
  private readonly fb = inject(NonNullableFormBuilder);

  protected readonly busy = signal<'name' | 'password' | null>(null);
  protected readonly profile = this.fb.group({
    full_name: [this.auth.user()?.full_name ?? '', [Validators.required, Validators.maxLength(200)]],
  });
  protected readonly password = this.fb.group({
    current_password: ['', Validators.required],
    new_password: ['', [Validators.required, Validators.minLength(10), Validators.maxLength(128)]],
  });

  protected bad(control: Parameters<typeof showError>[0]): boolean {
    return showError(control);
  }

  protected async saveName(): Promise<void> {
    if (this.profile.invalid) { this.profile.markAllAsTouched(); return; }
    this.busy.set('name');
    try {
      const me = await firstValueFrom(this.http.patch<Me>('/api/v1/auth/me', this.profile.getRawValue()));
      this.auth.me.set(me);
      this.profile.reset({ full_name: me.user.full_name });
      this.toast.success('Your name is saved.');
    } catch (err) {
      const problem = apiProblem(err);
      if (!applyFieldErrors(this.profile, problem.fields)) this.toast.error(problem.message);
    } finally {
      this.busy.set(null);
    }
  }

  protected async changePassword(): Promise<void> {
    if (this.password.invalid) { this.password.markAllAsTouched(); return; }
    this.busy.set('password');
    try {
      await firstValueFrom(this.http.post('/api/v1/auth/change-password', this.password.getRawValue()));
      this.password.reset();
      this.toast.success('Password changed. Your other devices were signed out.');
    } catch (err) {
      const problem = apiProblem(err);
      if (!applyFieldErrors(this.password, problem.fields)) this.toast.error(problem.message);
    } finally {
      this.busy.set(null);
    }
  }

  protected async signOutEverywhere(): Promise<void> {
    const ok = await this.dialog.confirm({
      title: 'Sign out everywhere?', confirmLabel: 'Sign out everywhere',
      message: 'You’ll be signed out on every device, including this one.',
    });
    if (ok) await this.auth.logout(true);
  }
}
