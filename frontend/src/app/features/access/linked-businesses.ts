import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { Workspace } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { ToastService } from '../../shared/toast/toast';

/** An agency's view of the businesses that shared their workspace with it. */
@Component({
  selector: 'ol-linked-businesses',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PageHeader, EmptyState, ErrorState, LoadingState],
  template: `
    <ol-page-header title="Linked businesses"
      description="Businesses on Outlogik that gave your agency access to their workspace. Their data stays theirs." />

    @if (ws.list.error()) {
      <ol-error-state message="We couldn't load linked businesses." (retry)="ws.list.reload()" />
    } @else if (ws.list.hasValue()) {
      @if (ws.linked().length === 0) {
        <ol-empty-state icon="link-45deg" title="No linked businesses"
          message="When a business gives your agency access, you'll get an email to accept it. It then shows here and in the workspace switcher." />
      } @else {
        <div class="ol-table-card">
          <table class="table ol-table">
            <thead><tr><th>Business</th><th>Access</th><th class="text-end">Websites</th>
              <th><span class="visually-hidden">Actions</span></th></tr></thead>
            <tbody>
              @for (w of ws.linked(); track w.id) {
                <tr>
                  <td class="fw-medium">{{ w.organization_name }}</td>
                  <td>{{ w.access === 'manage' ? 'Can make changes' : 'View only' }}</td>
                  <td class="text-end tabular-nums">{{ w.website_count }}</td>
                  <td class="text-end">
                    @if (org.can('linked_accounts.manage')) {
                      <button type="button" class="btn btn-sm btn-link text-danger" (click)="disconnect(w)">Disconnect</button>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    } @else {
      <ol-loading-state label="Loading linked businesses…" />
    }
  `,
})
export class LinkedBusinesses {
  protected readonly org = inject(CurrentOrgService);
  protected readonly ws = inject(WorkspaceService);
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected async disconnect(w: Workspace): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: `Disconnect from ${w.organization_name}?`, danger: true, confirmLabel: 'Disconnect',
      message: `Your agency will lose access to ${w.organization_name}'s workspace. To work on it again, they'll need to send new access.`,
    });
    if (!ok) return;
    try {
      await this.api.disconnectWorkspace(w.id);
      if (this.ws.current()?.id === w.id) this.ws.select(null);
      this.toast.success(`Disconnected from ${w.organization_name}.`);
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    }
  }
}
