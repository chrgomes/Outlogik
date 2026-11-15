import { CdkMenu, CdkMenuItem, CdkMenuTrigger } from '@angular/cdk/menu';
import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { Client, Page, Website } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
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
    <ol-page-header title="Websites" description="Every client website, in one place.">
      <button *olCan="'websites.write'" actions type="button" class="btn btn-primary" (click)="add()">
        <ol-icon name="plus-lg" /> Add website
      </button>
    </ol-page-header>

    <div class="ol-toolbar">
      <ol-search placeholder="Search by name or domain" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Client" [value]="clientId()"
        (change)="clientId.set($any($event.target).value); page.set(1)">
        <option value="">All clients</option>
        @for (c of clients.value()?.items ?? []; track c.id) {
          <option [value]="c.id">{{ c.name }}</option>
        }
      </select>
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
        @if (q() || status() || clientId()) {
          <ol-empty-state icon="search" title="No matching websites" message="Try a different search or filter." />
        } @else if ((clients.value()?.total ?? 0) === 0 && org.can('clients.write')) {
          <ol-empty-state icon="globe2" title="No websites yet"
            message="Websites belong to a client, so add a client first.">
            <a class="btn btn-primary" [routerLink]="['/o', org.slug(), 'clients']">Go to clients</a>
          </ol-empty-state>
        } @else {
          <ol-empty-state icon="globe2" title="No websites yet" message="Add your clients' websites to track them.">
            <button *olCan="'websites.write'" type="button" class="btn btn-primary" (click)="add()">
              <ol-icon name="plus-lg" /> Add a website
            </button>
          </ol-empty-state>
        }
      } @else {
        <div class="ol-table-card" [class.opacity-50]="sites.isLoading()">
          <table class="table ol-table table-hover">
            <thead>
              <tr><th>Website</th><th>Client</th><th>Status</th><th>Added</th>
                <th><span class="visually-hidden">Actions</span></th></tr>
            </thead>
            <tbody>
              @for (w of list.items; track w.id) {
                <tr>
                  <td>
                    <span class="fw-medium d-block">{{ w.name }}</span>
                    <a class="small text-muted" [href]="w.url" target="_blank" rel="noopener noreferrer">{{ w.url }}</a>
                  </td>
                  <td><a class="row-link" [routerLink]="['/o', org.slug(), 'clients', w.client_id]">{{ w.client_name }}</a></td>
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
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);

  protected readonly pageSize = PAGE_SIZE;
  protected readonly q = signal('');
  protected readonly clientId = signal('');
  protected readonly status = signal('');
  protected readonly page = signal(1);
  protected readonly sites = httpResource<Page<Website>>(() => ({
    url: this.api.url('websites'),
    params: queryParams({ q: this.q(), client_id: this.clientId(), status: this.status(),
      page: this.page(), page_size: PAGE_SIZE }),
  }));
  protected readonly clients = httpResource<Page<Client>>(() => ({
    url: this.api.url('clients'), params: queryParams({ page_size: 100, sort: 'name' }),
  }));

  protected async add(): Promise<void> {
    const site = await this.dialogs.open<Website>(WebsiteFormDialog, { clientId: this.clientId() || undefined });
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
      message: `${w.url} will be removed from ${w.client_name}. This can't be undone; to keep it, set it to Archived instead.`,
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
