import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { AccessGrant } from '../../core/api.types';
import { OrgApi } from '../../core/org-api.service';
import { DialogService } from '../../shared/dialog/dialog';
import { FieldError, showError } from '../../shared/forms/forms';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';

/** A business gives an agency access to its workspace, and sees or ends that access. */
@Component({
  selector: 'ol-agency-access',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, ReactiveFormsModule, FieldError, PageHeader, EmptyState, ErrorState,
    LoadingState, Status],
  template: `
    <ol-page-header title="Agency access"
      description="Let a marketing agency work on your websites and results, without sharing your login. You can end it at any time." />

    <section class="settings-card mb-4">
      <h2 class="h6 mb-3">Give an agency access</h2>
      @if (error()) {
        <div class="alert alert-danger" role="alert">{{ error() }}</div>
      }
      <form [formGroup]="form" (ngSubmit)="send()" novalidate>
        <div class="mb-3">
          <label for="grant-email" class="form-label">Email of someone at the agency</label>
          <input id="grant-email" type="email" class="form-control" formControlName="email"
            autocomplete="off" [class.is-invalid]="invalid()" aria-describedby="grant-email-hint" />
          <ol-field-error [control]="form.controls.email" />
          <div id="grant-email-hint" class="form-text">They accept it with their Outlogik agency account.</div>
        </div>
        <fieldset class="mb-3">
          <legend class="form-label fs-6 mb-1">What they can do</legend>
          <div class="form-check">
            <input class="form-check-input" type="radio" id="access-manage" value="manage" formControlName="access" />
            <label class="form-check-label" for="access-manage">Work on your websites and marketing</label>
          </div>
          <div class="form-check">
            <input class="form-check-input" type="radio" id="access-view" value="view" formControlName="access" />
            <label class="form-check-label" for="access-view">View only</label>
          </div>
        </fieldset>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">Send access</button>
      </form>
    </section>

    @if (grants.error()) {
      <ol-error-state message="We couldn't load agency access." (retry)="grants.reload()" />
    } @else if (grants.hasValue()) {
      @if (visible().length === 0) {
        <ol-empty-state icon="people" title="No agencies yet"
          message="When you give an agency access, it shows here, with who accepted it." />
      } @else {
        <div class="ol-table-card">
          <table class="table ol-table">
            <thead><tr><th>Agency</th><th>Access</th><th>Status</th><th>Since</th>
              <th><span class="visually-hidden">Actions</span></th></tr></thead>
            <tbody>
              @for (g of visible(); track g.id) {
                <tr>
                  <td>
                    <span class="fw-medium">{{ g.agency_name ?? g.email }}</span>
                    <span class="d-block small text-muted">
                      @if (g.accepted_by) { Accepted by {{ g.accepted_by }} } @else { Sent to {{ g.email }} }
                    </span>
                  </td>
                  <td>{{ g.access === 'manage' ? 'Can make changes' : 'View only' }}</td>
                  <td><ol-status [value]="g.status" /></td>
                  <td class="text-muted text-nowrap">{{ (g.accepted_at ?? g.created_at) | date: 'mediumDate' }}</td>
                  <td class="text-end">
                    @if (g.status === 'active' || g.status === 'pending') {
                      <button type="button" class="btn btn-sm btn-link text-danger" (click)="revoke(g)">
                        {{ g.status === 'active' ? 'End access' : 'Cancel' }}
                      </button>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    } @else {
      <ol-loading-state label="Loading agency access…" />
    }
  `,
  styles: `
    .settings-card { max-width: 40rem; padding: 1.5rem; border: 1px solid var(--ol-border);
      border-radius: var(--bs-border-radius-lg); background: var(--ol-surface-raised); }
  `,
})
export class AgencyAccess {
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected readonly grants = httpResource<AccessGrant[]>(() => this.api.url('access-grants'));
  /** Ended and expired grants stay in the history, but only recent ones are worth showing. */
  protected readonly visible = computed(() => (this.grants.value() ?? []).filter(
    (g) => g.status === 'active' || g.status === 'pending' || g.status === 'expired').concat(
    (this.grants.value() ?? []).filter((g) => g.status === 'revoked').slice(0, 5)));
  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
    access: ['manage' as 'manage' | 'view'],
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected invalid(): boolean {
    return showError(this.form.controls.email);
  }

  protected async send(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    try {
      const g = await this.api.createGrant(this.form.getRawValue());
      this.form.reset({ email: '', access: 'manage' });
      this.grants.reload();
      this.toast.success(`Access sent to ${g.email}.`);
    } catch (err) {
      const p = apiProblem(err);
      if (!applyFieldErrors(this.form, p.fields)) this.error.set(p.message);
    } finally {
      this.busy.set(false);
    }
  }

  protected async revoke(g: AccessGrant): Promise<void> {
    const active = g.status === 'active';
    const ok = await this.dialogs.confirm({
      title: active ? `End ${g.agency_name}'s access?` : 'Cancel this access link?',
      message: active
        ? `${g.agency_name} will lose access to your workspace straight away. Your websites and results stay as they are.`
        : `The link sent to ${g.email} will stop working.`,
      confirmLabel: active ? 'End access' : 'Cancel link', danger: true,
    });
    if (!ok) return;
    try {
      await this.api.revokeGrant(g.id);
      this.grants.reload();
      this.toast.success(active ? 'Access ended.' : 'Link cancelled.');
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    }
  }
}
