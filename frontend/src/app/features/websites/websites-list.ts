import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, computed, effect, inject, signal, untracked,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { Page, Website } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { DialogService } from '../../shared/dialog/dialog';
import { Icon } from '@brand/icon/icon';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Can, Pager, Search, Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { WebsiteFormDialog } from './website-form-dialog';

const PAGE_SIZE = 25;

@Component({
  selector: 'ol-websites-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, CdkMenuTrigger, CdkMenu, CdkMenuItem, PageHeader, EmptyState,
    ErrorState, LoadingState, Pager, Search, Status, Can, Icon],
  template: `
    <ol-page-header title="Websites" [description]="description()">
      <button *olCan="'websites.write'" actions type="button" class="btn btn-primary" (click)="add()">
        <ol-icon name="plus-lg" /> Add website
      </button>
    </ol-page-header>

    <div class="ol-toolbar">
      <ol-search placeholder="Search by name or domain" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Status" [value]="status()"
        (change)="status.set($any($event.target).value); page.set(1)">
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="paused">Paused</option>
        <option value="archived">Archived</option>
      </select>
    </div>

    @if (sites.error()) {
      <ol-error-state message="We couldn't load websites." (retry)="sites.reload()" />
    } @else if (sites.hasValue()) {
      @let list = sites.value();
      @if (list.total === 0) {
        @if (q() || status()) {
          <ol-empty-state icon="search" title="No matching websites" message="Try a different search or filter." />
        } @else {
          <ol-empty-state icon="globe2" title="No websites yet" [message]="emptyMessage()">
            <button *olCan="'websites.write'" type="button" class="btn btn-primary" (click)="add()">
              <ol-icon name="plus-lg" /> Add a website
            </button>
          </ol-empty-state>
        }
      } @else {
        <div class="ol-table-card" [class.opacity-50]="sites.isLoading()">
          <table class="table ol-table table-hover">
            <thead>
              <tr><th>Website</th>@if (showWorkspace()) {<th>Workspace</th>}<th>Status</th><th>Added</th>
                <th><span class="visually-hidden">Actions</span></th></tr>
            </thead>
            <tbody>
              @for (w of list.items; track w.id) {
                <tr>
                  <td>
                    <span class="fw-medium d-block">{{ w.name }}</span>
                    <a class="small text-muted" [href]="w.url" target="_blank" rel="noopener noreferrer">{{ w.url }}</a>
                  </td>
                  @if (showWorkspace()) {
                    <td>
                      @if (w.client_id && org.can('clients.read')) {
                        <a class="row-link" [routerLink]="['/o', org.slug(), 'clients', w.client_id]">{{ w.workspace_name }}</a>
                      } @else {
                        {{ w.workspace_name }}
                        @if (!w.client_id) {<small class="d-block text-muted">Your own marketing</small>}
                      }
                    </td>
                  }
                  <td><ol-status [value]="w.status" /></td>
                  <td class="text-muted text-nowrap">{{ w.created_at | date: 'mediumDate' }}</td>
                  <td class="text-end">
                    @if (org.can('websites.write') || org.can('websites.delete')) {
                      <button type="button" class="icon-action" [cdkMenuTriggerFor]="menu"
                        [attr.aria-label]="'Actions for ' + w.name">
                        <ol-icon name="three-dots" />
                      </button>
                      <ng-template #menu>
                        <div class="ol-menu" cdkMenu>
                          @if (org.can('websites.write')) {
                            <button type="button" class="ol-menu-item" cdkMenuItem (cdkMenuItemTriggered)="edit(w)">Edit</button>
                          }
                          @if (org.can('websites.delete')) {
                            <button type="button" class="ol-menu-item text-danger" cdkMenuItem (cdkMenuItemTriggered)="remove(w)">Delete…</button>
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
      <ol-loading-state label="Loading websites…" />
    }
  `,
})
export class WebsitesList {
  protected readonly org = inject(CurrentOrgService);
  protected readonly ws = inject(WorkspaceService);
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected readonly pageSize = PAGE_SIZE;
  protected readonly q = signal('');
  protected readonly status = signal('');
  protected readonly page = signal(1);
  /** Agencies see one workspace's websites, or every workspace's (with a Workspace column). */
  private readonly workspaceId = computed(() => (this.org.isAgency() ? this.ws.current()?.id : undefined));
  protected readonly showWorkspace = computed(() => this.org.isAgency() && !this.workspaceId());
  protected readonly sites = httpResource<Page<Website>>(() => {
    const id = this.workspaceId();
    return {
      url: this.api.url(id ? `workspaces/${id}/websites` : 'websites'),
      params: queryParams({ q: this.q(), status: this.status(), page: this.page(),
        page_size: PAGE_SIZE, sort: this.showWorkspace() ? 'workspace' : null }),
    };
  });
  protected readonly description = computed(() => {
    const w = this.ws.current();
    if (!this.org.isAgency()) return 'Your websites, in one place.';
    if (!w) return 'Every website across your workspaces.';
    return w.kind === 'own' ? 'Websites for your own marketing.' : `${w.name}'s websites.`;
  });
  protected readonly emptyMessage = computed(() => {
    const w = this.ws.current();
    if (!this.org.isAgency() || w?.kind === 'own') return 'Add your websites to track them.';
    return w ? `Add ${w.name}'s websites to track them.` : 'Add your own or your clients\' websites to track them.';
  });

  constructor() {
    // A different workspace starts again on page 1.
    effect(() => {
      this.workspaceId();
      untracked(() => this.page.set(1));
    });
  }

  protected async add(): Promise<void> {
    const site = await this.dialogs.open<Website>(WebsiteFormDialog, { workspaceId: this.ws.current()?.id });
    if (site) {
      this.sites.reload();
      this.toast.success(`${site.name} added.`);
    }
  }

  protected async edit(w: Website): Promise<void> {
    if (await this.dialogs.open<Website>(WebsiteFormDialog, { website: w })) {
      this.sites.reload();
      this.toast.success('Changes saved.');
    }
  }

  protected async remove(w: Website): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: `Delete ${w.name}?`, danger: true, confirmLabel: 'Delete website',
      message: `${w.url} will be removed from ${w.workspace_name}. This can't be undone; to keep it, set it to Archived instead.`,
    });
    if (!ok) return;
    try {
      await this.api.deleteWebsite(w.id);
      this.sites.reload();
      this.toast.success(`${w.name} deleted.`);
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    }
  }
}
