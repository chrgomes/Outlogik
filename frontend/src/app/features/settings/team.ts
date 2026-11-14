import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { Invitation, Member, Page } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { DialogService } from '../../shared/dialog/dialog';
import { Icon } from '../../shared/icon/icon';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Can, Pager, Search, Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { ChangeRoleDialog } from './change-role-dialog';
import { InviteDialog } from './invite-dialog';

const PAGE_SIZE = 25;

@Component({
  selector: 'ol-team',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, CdkMenuTrigger, CdkMenu, CdkMenuItem, PageHeader, EmptyState, ErrorState,
    LoadingState, Pager, Search, Status, Can, Icon],
  template: `
    <ol-page-header title="Team" description="Everyone with access to this organization, including client-portal users.">
      <button *olCan="'members.invite'" actions type="button" class="btn btn-primary" (click)="invite()">
        <ol-icon name="plus-lg" /> Invite people
      </button>
    </ol-page-header>

    <div class="ol-toolbar">
      <ol-search placeholder="Search by name or email" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Status" [value]="status()"
        (change)="status.set($any($event.target).value); page.set(1)">
        <option value="">All members</option>
        <option value="active">Active</option>
        <option value="disabled">Disabled</option>
      </select>
    </div>

    @if (members.error()) {
      <ol-error-state message="We couldn't load the team." (retry)="members.reload()" />
    } @else if (members.hasValue()) {
      @let list = members.value();
      @if (list.total === 0) {
        <ol-empty-state icon="search" title="Nobody matches" message="Try a different search." />
      } @else {
        <div class="ol-table-card" [class.opacity-50]="members.isLoading()">
          <table class="table ol-table">
            <thead><tr><th>Person</th><th>Role</th><th>Status</th><th>Joined</th>
              <th><span class="visually-hidden">Actions</span></th></tr></thead>
            <tbody>
              @for (m of list.items; track m.id) {
                <tr>
                  <td>
                    <span class="fw-medium">{{ m.full_name }}</span>
                    @if (m.is_you) { <span class="badge rounded-pill you">You</span> }
                    <span class="d-block small text-muted">{{ m.email }}</span>
                  </td>
                  <td>{{ m.role.name }}</td>
                  <td><ol-status [value]="m.status" /></td>
                  <td class="text-muted text-nowrap">{{ m.joined_at | date: 'mediumDate' }}</td>
                  <td class="text-end">
                    @if (canManage(m)) {
                      <button type="button" class="icon-action" [cdkMenuTriggerFor]="menu"
                        [attr.aria-label]="'Actions for ' + m.full_name">
                        <ol-icon name="three-dots" />
                      </button>
                      <ng-template #menu>
                        <div class="ol-menu" cdkMenu>
                          @if (org.can('members.update')) {
                            <button type="button" class="ol-menu-item" cdkMenuItem (cdkMenuItemTriggered)="changeRole(m)">Change role…</button>
                            <button type="button" class="ol-menu-item" cdkMenuItem (cdkMenuItemTriggered)="toggleStatus(m)">
                              {{ m.status === 'active' ? 'Disable access' : 'Restore access' }}
                            </button>
                          }
                          @if (org.can('members.remove')) {
                            <div class="ol-menu-divider" role="separator"></div>
                            <button type="button" class="ol-menu-item text-danger" cdkMenuItem (cdkMenuItemTriggered)="remove(m)">Remove from organization…</button>
                          }
                        </div>
                      </ng-template>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <ol-pager [page]="page()" [pageSize]="pageSize" [total]="list.total" (pageChange)="page.set($event)" />
      }
    } @else {
      <ol-loading-state label="Loading team…" />
    }

    @if (org.can('members.invite')) {
      <section class="ol-section">
        <header><h2>Invitations</h2></header>
        @if (invites.hasValue()) {
          @if (invites.value().total === 0) {
            <p class="text-muted mb-0">No open invitations.</p>
          } @else {
            <div class="ol-table-card">
              <table class="table ol-table">
                <thead><tr><th>Email</th><th>Role</th><th>Status</th><th>Expires</th>
                  <th><span class="visually-hidden">Actions</span></th></tr></thead>
                <tbody>
                  @for (i of invites.value().items; track i.id) {
                    <tr>
                      <td>
                        <span class="fw-medium">{{ i.email }}</span>
                        <span class="d-block small text-muted">Invited by {{ i.invited_by ?? 'someone' }}</span>
                      </td>
                      <td>{{ i.role.name }}@if (i.client_name) {<span class="d-block small text-muted">{{ i.client_name }}</span>}</td>
                      <td><ol-status [value]="i.status" /></td>
                      <td class="text-muted text-nowrap">{{ i.expires_at | date: 'mediumDate' }}</td>
                      <td class="text-end text-nowrap">
                        <button type="button" class="btn btn-sm btn-link" (click)="resend(i)">Resend</button>
                        <button type="button" class="btn btn-sm btn-link text-danger" (click)="revoke(i)">Cancel</button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        } @else if (invites.error()) {
          <ol-error-state message="We couldn't load invitations." (retry)="invites.reload()" />
        } @else {
          <ol-loading-state />
        }
      </section>
    }
  `,
  styles: `.you { margin-left: 0.375rem; background: var(--ol-surface-active); color: var(--ol-text); font-weight: 500; }`,
})
export class Team {
  protected readonly org = inject(CurrentOrgService);
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected readonly pageSize = PAGE_SIZE;
  protected readonly q = signal('');
  protected readonly status = signal('');
  protected readonly page = signal(1);
  protected readonly members = httpResource<Page<Member>>(() => ({
    url: this.api.url('members'),
    params: queryParams({ q: this.q(), status: this.status(), page: this.page(), page_size: PAGE_SIZE }),
  }));
  protected readonly invites = httpResource<Page<Invitation>>(() =>
    this.org.can('members.invite')
      ? { url: this.api.url('invitations'), params: queryParams({ page_size: 100 }) }
      : undefined);

  /** Hide actions that can't succeed: your own row, or an owner when you aren't one. */
  protected canManage(m: Member): boolean {
    if (m.is_you || !(this.org.can('members.update') || this.org.can('members.remove'))) return false;
    return m.role.system_key !== 'owner' || this.org.isOwner();
  }

  protected async invite(): Promise<void> {
    const inv = await this.dialogs.open<Invitation>(InviteDialog);
    if (inv) {
      this.invites.reload();
      this.toast.success(`Invitation sent to ${inv.email}.`);
    }
  }

  protected async changeRole(m: Member): Promise<void> {
    const updated = await this.dialogs.open<Member>(ChangeRoleDialog, m);
    if (updated) {
      this.members.reload();
      this.toast.success(`${m.full_name} is now ${updated.role.name}.`);
    }
  }

  protected async toggleStatus(m: Member): Promise<void> {
    const disabling = m.status === 'active';
    if (disabling) {
      const ok = await this.dialogs.confirm({
        title: `Disable ${m.full_name}'s access?`, danger: true, confirmLabel: 'Disable access',
        message: "They'll lose access to this organization straight away. You can restore it later.",
      });
      if (!ok) return;
    }
    await this.act(async () => {
      await this.api.updateMember(m.id, { status: disabling ? 'disabled' : 'active' });
      this.members.reload();
      this.toast.success(disabling ? 'Access disabled.' : 'Access restored.');
    });
  }

  protected async remove(m: Member): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: `Remove ${m.full_name}?`, danger: true, confirmLabel: 'Remove',
      message: "They'll lose access to this organization and any client portals in it. Their account itself isn't deleted.",
    });
    if (!ok) return;
    await this.act(async () => {
      await this.api.removeMember(m.id);
      this.members.reload();
      this.toast.success(`${m.full_name} removed.`);
    });
  }

  protected async resend(i: Invitation): Promise<void> {
    await this.act(async () => {
      await this.api.resendInvitation(i.id);
      this.invites.reload();
      this.toast.success(`New link sent to ${i.email}.`);
    });
  }

  protected async revoke(i: Invitation): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: 'Cancel this invitation?', confirmLabel: 'Cancel invitation', danger: true,
      message: `The link sent to ${i.email} will stop working.`,
    });
    if (!ok) return;
    await this.act(async () => {
      await this.api.revokeInvitation(i.id);
      this.invites.reload();
      this.toast.success('Invitation cancelled.');
    });
  }

  private async act(action: () => Promise<void>): Promise<void> {
    try {
      await action();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    }
  }
}
