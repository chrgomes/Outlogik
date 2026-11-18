import { ChangeDetectionStrategy, Component, effect, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { DialogService } from '../../shared/dialog/dialog';
import { FieldError, showError } from '../../shared/forms/forms';
import { PageHeader } from '../../shared/page-header/page-header';
import { ToastService } from '../../shared/toast/toast';

@Component({
  selector: 'ol-organization-settings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, PageHeader, FieldError],
  template: `
    <ol-page-header title="Organization"
      [description]="org.isAgency() ? 'Your agency’s account in Outlogik.' : 'Your business’s account in Outlogik.'" />

    <section class="settings-card">
      <form [formGroup]="form" (ngSubmit)="save()" novalidate>
        <div class="mb-3">
          <label for="org-name" class="form-label">Name</label>
          <input id="org-name" class="form-control" formControlName="name"
            [class.is-invalid]="invalid()" [readonly]="!canEdit" />
          <ol-field-error [control]="form.controls.name" />
        </div>
        <div class="mb-3">
          <label for="org-url" class="form-label">Web address</label>
          <input id="org-url" class="form-control" [value]="address()" readonly aria-describedby="url-hint" />
          <div id="url-hint" class="form-text">Stays the same when you rename the organization, so links keep working.</div>
        </div>
        <p class="text-muted small mb-0">Your role: <strong>{{ org.membership()?.role_name }}</strong></p>
        @if (canEdit) {
          <div class="d-flex justify-content-end mt-3">
            <button type="submit" class="btn btn-primary" [disabled]="busy() || form.pristine">Save changes</button>
          </div>
        }
      </form>
    </section>

    <section class="settings-card danger mt-4">
      <h2 class="h6 mb-1">Leave organization</h2>
      <p class="text-muted small mb-3">
        You'll lose access to {{ org.membership()?.organization_name }} straight away. Someone will need
        to invite you again to come back. An organization's only owner can't leave.
      </p>
      <button type="button" class="btn btn-outline-danger btn-sm" (click)="leave()">Leave organization</button>
    </section>
  `,
  styles: `
    .settings-card { max-width: 40rem; padding: 1.5rem; border: 1px solid var(--ol-border);
      border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); }
    .settings-card.danger { border-color: var(--bs-danger-border-subtle); }
  `,
})
export class OrganizationSettings {
  protected readonly org = inject(CurrentOrgService);
  private readonly auth = inject(AuthService);
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  protected readonly canEdit = this.org.can('organization.update');
  protected readonly form = inject(NonNullableFormBuilder).group({
    name: ['', [Validators.required, Validators.maxLength(200)]],
  });
  protected readonly busy = signal(false);
  protected readonly address = () => `${location.origin}/o/${this.org.slug()}`;

  constructor() {
    effect(() => {
      const name = this.org.membership()?.organization_name;
      if (name !== undefined && this.form.pristine) this.form.reset({ name });
    });
  }

  protected invalid(): boolean {
    return showError(this.form.controls.name);
  }

  protected async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    try {
      const saved = await this.api.updateOrganization(this.form.getRawValue());
      await this.auth.refresh(); // the switcher and title use the new name
      this.form.reset({ name: saved.name });
      this.toast.success('Organization renamed.');
    } catch (err) {
      const p = apiProblem(err);
      if (!applyFieldErrors(this.form, p.fields)) this.toast.error(p.message);
    } finally {
      this.busy.set(false);
    }
  }

  protected async leave(): Promise<void> {
    const name = this.org.membership()?.organization_name ?? 'this organization';
    const ok = await this.dialogs.confirm({
      title: `Leave ${name}?`, danger: true, confirmLabel: 'Leave organization',
      message: "You'll lose access straight away. Someone will need to invite you again to come back.",
    });
    if (!ok) return;
    try {
      await this.api.leave();
      await this.auth.refresh();
      this.toast.success(`You left ${name}.`);
      await this.router.navigateByUrl('/');
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    }
  }
}
