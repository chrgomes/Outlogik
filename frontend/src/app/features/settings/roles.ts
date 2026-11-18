import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { Page, Role } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { DialogService } from '../../shared/dialog/dialog';
import { Icon } from '@brand/icon/icon';
import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { Can } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { RoleEditorDialog } from './role-editor-dialog';

@Component({
  selector: 'ol-roles',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageHeader, ErrorState, LoadingState, Can, Icon],
  template: `
    <ol-page-header title="Roles" description="What each role can do. Owners can add custom roles.">
      <button *olCan="'roles.manage'" actions type="button" class="btn btn-primary" (click)="create()">
        <ol-icon name="plus-lg" /> New role
      </button>
    </ol-page-header>

    @if (roles.error()) {
      <ol-error-state message="We couldn't load roles." (retry)="roles.reload()" />
    } @else if (roles.hasValue()) {
      <div class="ol-table-card">
        <table class="table ol-table">
          <thead><tr><th>Role</th><th class="text-end">People</th><th class="text-end">Permissions</th>
            <th><span class="visually-hidden">Actions</span></th></tr></thead>
          <tbody>
            @for (r of roles.value().items; track r.id) {
              <tr>
                <td>
                  <span class="fw-medium">{{ r.name }}</span>
                  @if (r.is_system) { <span class="badge rounded-pill builtin">Built-in</span> }
                  @if (r.workspace_scope === 'assigned') {
                    <span class="badge rounded-pill builtin">Assigned workspaces only</span>
                  }
                  @if (r.description) { <span class="d-block small text-muted">{{ r.description }}</span> }
                </td>
                <td class="text-end tabular-nums">{{ r.member_count }}</td>
                <td class="text-end tabular-nums">{{ r.permissions.length }}</td>
                <td class="text-end text-nowrap">
                  @if (!r.is_system && org.can('roles.manage')) {
                    <button type="button" class="btn btn-sm btn-link" (click)="edit(r)">Edit</button>
                    <button type="button" class="btn btn-sm btn-link text-danger" (click)="remove(r)">Delete</button>
                  } @else {
                    <button type="button" class="btn btn-sm btn-link" (click)="view(r)">View</button>
                  }
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    } @else {
      <ol-loading-state label="Loading roles…" />
    }
  `,
  styles: `.builtin { margin-left: 0.375rem; background: var(--ol-surface-active); color: var(--ol-text); font-weight: 500; }`,
})
export class Roles {
  protected readonly org = inject(CurrentOrgService);
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);
  protected readonly roles = httpResource<Page<Role>>(() => ({
    url: this.api.url('roles'), params: queryParams({ page_size: 100 }),
  }));

  protected async create(): Promise<void> {
    const role = await this.dialogs.open<Role>(RoleEditorDialog, {}, true);
    if (role) {
      this.roles.reload();
      this.toast.success(`${role.name} created.`);
    }
  }

  protected async edit(role: Role): Promise<void> {
    if (await this.dialogs.open<Role>(RoleEditorDialog, { role }, true)) {
      this.roles.reload();
      this.toast.success('Role saved.');
    }
  }

  protected view(role: Role): void {
    void this.dialogs.open(RoleEditorDialog, { role, readOnly: true }, true);
  }

  protected async remove(role: Role): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: `Delete ${role.name}?`, danger: true, confirmLabel: 'Delete role',
      message: "Roles still assigned to people or open invitations can't be deleted.",
    });
    if (!ok) return;
    try {
      await this.api.deleteRole(role.id);
      this.roles.reload();
      this.toast.success(`${role.name} deleted.`);
    } catch (err) {
      const p = apiProblem(err);
      const d = p.details as { members?: number; open_invitations?: number } | null;
      this.toast.error(p.code === 'role_in_use' && d
        ? `${role.name} is still used by ${d.members} member(s) and ${d.open_invitations} open invitation(s).`
        : p.message);
    }
  }
}
