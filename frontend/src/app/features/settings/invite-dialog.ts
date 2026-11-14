import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { apiProblem, applyFieldErrors } from '../../core/api-errors';
import { Client, Invitation, Page, Role } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { FieldError, showError } from '../../shared/forms/forms';

export interface InviteData {
  /** Invite a client-portal user for this client (role fixed to Client). */
  client?: { id: string; name: string };
}

/** Invite a team member or a client-portal user. Closes with the invitation. */
@Component({
  selector: 'ol-invite-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, FieldError],
  template: `
    <h2 class="h5 mb-1">{{ fixedClient ? 'Invite to the client portal' : 'Invite someone' }}</h2>
    <p class="text-muted small mb-3">
      @if (fixedClient) {
        They'll see {{ fixedClient.name }} and its websites, nothing else.
      } @else {
        We'll email them a link to join {{ org.membership()?.organization_name }}. It works for 7 days.
      }
    </p>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    <form [formGroup]="form" (ngSubmit)="send()" novalidate>
      <div class="mb-3">
        <label for="invite-email" class="form-label">Email</label>
        <input id="invite-email" type="email" class="form-control" formControlName="email"
          [class.is-invalid]="invalid('email')" autocomplete="off" />
        <ol-field-error [control]="form.controls.email" />
      </div>
      @if (!fixedClient) {
        <div class="mb-3">
          <label for="invite-role" class="form-label">Role</label>
          <select id="invite-role" class="form-select" formControlName="role_id"
            [class.is-invalid]="invalid('role_id')">
            <option value="" disabled>Choose a role</option>
            @for (r of assignable(); track r.id) {
              <option [value]="r.id">{{ r.name }}</option>
            }
          </select>
          <ol-field-error [control]="form.controls.role_id" />
          @if (selectedRole(); as role) {
            <div class="form-text">{{ role.description }}</div>
          }
        </div>
        @if (isClientRole()) {
          <div class="mb-3">
            <label for="invite-client" class="form-label">Client they can see</label>
            <select id="invite-client" class="form-select" formControlName="client_id"
              [class.is-invalid]="invalid('client_id')">
              <option value="" disabled>Choose a client</option>
              @for (c of clients.value()?.items ?? []; track c.id) {
                <option [value]="c.id">{{ c.name }}</option>
              }
            </select>
            <ol-field-error [control]="form.controls.client_id" />
          </div>
        }
      }
      <div class="ol-dialog-actions">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">Send invitation</button>
      </div>
    </form>
  `,
})
export class InviteDialog {
  protected readonly ref = inject<DialogRef<Invitation>>(DialogRef);
  protected readonly org = inject(CurrentOrgService);
  private readonly api = inject(OrgApi);
  protected readonly fixedClient = inject<InviteData | undefined>(DIALOG_DATA)?.client;

  protected readonly roles = httpResource<Page<Role>>(() => ({
    url: this.api.url('roles'), params: queryParams({ page_size: 100 }),
  }));
  protected readonly clients = httpResource<Page<Client>>(() => this.fixedClient ? undefined : {
    url: this.api.url('clients'), params: queryParams({ page_size: 100, status: 'active', sort: 'name' }),
  });
  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
    role_id: [''],
    client_id: [this.fixedClient?.id ?? ''],
  });
  private readonly roleId = toSignal(this.form.controls.role_id.valueChanges, { initialValue: '' });

  /** Owners can grant anything; others can't hand out Owner (the API also checks the rest). */
  protected readonly assignable = computed(() => (this.roles.value()?.items ?? [])
    .filter((r) => r.system_key !== 'owner' || this.org.isOwner()));
  protected readonly selectedRole = computed(() =>
    this.assignable().find((r) => r.id === this.roleId()) ?? null);
  protected readonly isClientRole = computed(() => this.selectedRole()?.system_key === 'client');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected invalid(name: 'email' | 'role_id' | 'client_id'): boolean {
    return showError(this.form.controls[name]);
  }

  protected async send(): Promise<void> {
    const v = this.form.getRawValue();
    let roleId = v.role_id;
    if (this.fixedClient) {
      roleId = this.roles.value()?.items.find((r) => r.system_key === 'client')?.id ?? '';
    } else {
      if (!roleId) this.form.controls.role_id.setErrors({ required: true });
      if (this.isClientRole() && !v.client_id) this.form.controls.client_id.setErrors({ required: true });
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    try {
      const inv = await this.api.invite({ email: v.email, role_id: roleId,
        client_id: this.fixedClient || this.isClientRole() ? v.client_id : null });
      this.ref.close(inv);
    } catch (err) {
      const p = apiProblem(err);
      if (p.code === 'already_member') this.form.controls.email.setErrors({ server: p.message });
      else if (!applyFieldErrors(this.form, p.fields)) this.error.set(p.message);
    } finally {
      this.busy.set(false);
    }
  }
}
