import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { apiProblem } from '../../core/api-errors';
import { Member, Page, Role } from '../../core/api.types';
import { OrgApi, queryParams } from '../../core/org-api.service';

/** Change a team member's role. Closes with the updated member. */
@Component({
  selector: 'ol-change-role-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  template: `
    <h2 class="h5 mb-1">Change role</h2>
    <p class="text-muted small mb-3">For {{ member.full_name }} ({{ member.email }}). Takes effect straight away.</p>
    @if (error()) {
      <div class="alert alert-danger" role="alert">{{ error() }}</div>
    }
    <label for="role" class="form-label">Role</label>
    <select id="role" class="form-select" [ngModel]="roleId()" (ngModelChange)="roleId.set($event)">
      @for (r of options(); track r.id) {
        <option [value]="r.id">{{ r.name }}</option>
      }
    </select>
    @if (selected(); as r) {
      <div class="form-text">{{ r.description }}</div>
    }
    <div class="ol-dialog-actions">
      <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
      <button type="button" class="btn btn-primary" (click)="save()"
        [disabled]="busy() || roleId() === member.role.id">Save</button>
    </div>
  `,
})
export class ChangeRoleDialog {
  protected readonly ref = inject<DialogRef<Member>>(DialogRef);
  protected readonly member = inject<Member>(DIALOG_DATA);
  private readonly api = inject(OrgApi);
  private readonly roles = httpResource<Page<Role>>(() => ({
    url: this.api.url('roles'), params: queryParams({ page_size: 100 }),
  }));
  /** Client-portal users and team members can't be switched into each other (API rule). */
  protected readonly options = computed(() => (this.roles.value()?.items ?? []).filter(
    (r) => (r.system_key === 'client') === (this.member.role.system_key === 'client')));
  protected readonly roleId = signal(this.member.role.id);
  protected readonly selected = computed(() => this.options().find((r) => r.id === this.roleId()));
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected async save(): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    try {
      this.ref.close(await this.api.updateMember(this.member.id, { role_id: this.roleId() }));
    } catch (err) {
      this.error.set(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
