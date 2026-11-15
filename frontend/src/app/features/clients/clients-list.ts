import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { Client, Page } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { DialogService } from '../../shared/dialog/dialog';
import { Icon } from '@brand/icon/icon';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Can, Pager, Search, Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { ClientFormDialog } from './client-form-dialog';

const PAGE_SIZE = 25;

@Component({
  selector: 'ol-clients-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, PageHeader, EmptyState, ErrorState, LoadingState, Pager, Search,
    Status, Can, Icon],
  template: `
    <ol-page-header title="Clients" [description]="org.isClientUser()
      ? 'The businesses you have access to.' : 'The businesses your agency works for.'">
      <button *olCan="'clients.write'" actions type="button" class="btn btn-primary" (click)="add()">
        <ol-icon name="plus-lg" /> Add client
      </button>
    </ol-page-header>

    <div class="ol-toolbar">
      <ol-search placeholder="Search clients" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Status" [value]="status()"
        (change)="status.set($any($event.target).value); page.set(1)">
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="archived">Archived</option>
      </select>
    </div>

    @if (clients.error()) {
      <ol-error-state message="We couldn't load your clients." (retry)="clients.reload()" />
    } @else if (clients.hasValue()) {
      @let list = clients.value();
      @if (list.total === 0) {
        @if (q() || status()) {
          <ol-empty-state icon="search" title="No matching clients" message="Try a different search or status." />
        } @else {
          <ol-empty-state icon="briefcase" title="No clients yet"
            message="Add the businesses you work for, then their websites.">
            <button *olCan="'clients.write'" type="button" class="btn btn-primary" (click)="add()">
              <ol-icon name="plus-lg" /> Add your first client
            </button>
          </ol-empty-state>
        }
      } @else {
        <div class="ol-table-card" [class.opacity-50]="clients.isLoading()">
          <table class="table ol-table table-hover">
            <thead>
              <tr><th>Name</th><th>Contact</th><th class="text-end">Websites</th><th>Status</th><th>Updated</th></tr>
            </thead>
            <tbody>
              @for (c of list.items; track c.id) {
                <tr>
                  <td><a class="row-link" [routerLink]="[c.id]">{{ c.name }}</a></td>
                  <td class="text-muted">{{ c.contact_email || '—' }}</td>
                  <td class="text-end tabular-nums">{{ c.website_count }}</td>
                  <td><ol-status [value]="c.status" /></td>
                  <td class="text-muted text-nowrap">{{ c.updated_at | date: 'mediumDate' }}</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <ol-pager [page]="page()" [pageSize]="pageSize" [total]="list.total" (pageChange)="page.set($event)" />
      }
    } @else {
      <ol-loading-state label="Loading clients…" />
    }
  `,
})
export class ClientsList {
  protected readonly org = inject(CurrentOrgService);
  private readonly api = inject(OrgApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  protected readonly pageSize = PAGE_SIZE;
  protected readonly q = signal('');
  protected readonly status = signal('');
  protected readonly page = signal(1);
  protected readonly clients = httpResource<Page<Client>>(() => ({
    url: this.api.url('clients'),
    params: queryParams({ q: this.q(), status: this.status(), page: this.page(), page_size: PAGE_SIZE }),
  }));

  protected async add(): Promise<void> {
    const created = await this.dialogs.open<Client>(ClientFormDialog);
    if (created) {
      this.toast.success(`${created.name} added.`);
      await this.router.navigate(['/o', this.org.slug(), 'clients', created.id]);
    }
  }
}
