import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Page } from '../../core/api.types';
import { queryParams } from '../../core/org-api.service';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Pager, Search, Status } from '../../shared/table/table-parts';
import { OrgRow, PLATFORM_API } from './platform-api';

const PAGE_SIZE = 50;

/** /admin/platform/organizations: every business and agency, with its plan. */
@Component({
  selector: 'ol-platform-organizations',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, PageHeader, EmptyState, ErrorState, LoadingState, Pager, Search, Status],
  template: `
    <ol-page-header title="Organizations" description="Every business and agency using Outlogik." />
    <div class="ol-toolbar">
      <ol-search placeholder="Search name or address" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Account type" [value]="kind()" (change)="kind.set($any($event.target).value); page.set(1)">
        <option value="">Businesses and agencies</option>
        <option value="business">Businesses</option>
        <option value="agency">Agencies</option>
      </select>
      <select class="form-select" aria-label="Status" [value]="status()" (change)="status.set($any($event.target).value); page.set(1)">
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="suspended">Suspended</option>
      </select>
    </div>
    @if (list.error()) {
      <ol-error-state message="We couldn't load organizations." (retry)="list.reload()" />
    } @else if (list.value(); as l) {
      @if (l.total === 0) {
        <ol-empty-state icon="building" title="No organizations match" message="Try a different search or filter." />
      } @else {
        <div class="ol-table-card" [class.opacity-50]="list.isLoading()">
          <div class="table-responsive">
            <table class="table ol-table mb-0">
              <thead><tr><th>Organization</th><th>Type</th><th>Plan</th><th class="text-end">Members</th>
                <th class="text-end">Clients</th><th class="text-end">Websites</th><th>Status</th><th>Joined</th></tr></thead>
              <tbody>
                @for (o of l.items; track o.id) {
                  <tr>
                    <td><a class="row-link fw-medium" [routerLink]="['/admin', 'platform', 'organizations', o.id]">{{ o.name }}</a>
                      <span class="d-block small text-muted">{{ o.slug }}</span></td>
                    <td>{{ o.kind === 'agency' ? 'Agency' : 'Business' }}</td>
                    <td>{{ o.plan ?? '—' }}
                      @if (o.subscription_status) { <span class="d-block"><ol-status [value]="o.subscription_status" /></span> }</td>
                    <td class="text-end">{{ o.members }}</td>
                    <td class="text-end">{{ o.kind === 'agency' ? o.clients : '—' }}</td>
                    <td class="text-end">{{ o.websites }}</td>
                    <td><ol-status [value]="o.status" /></td>
                    <td class="text-nowrap text-muted">{{ o.created_at | date: 'mediumDate' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
        <ol-pager [page]="page()" [pageSize]="pageSize" [total]="l.total" (pageChange)="page.set($event)" />
      }
    } @else {
      <ol-loading-state label="Loading organizations…" />
    }
  `,
})
export class PlatformOrganizations {
  protected readonly pageSize = PAGE_SIZE;
  protected readonly q = signal('');
  protected readonly kind = signal('');
  protected readonly status = signal('');
  protected readonly page = signal(1);
  protected readonly list = httpResource<Page<OrgRow>>(() => ({
    url: `${PLATFORM_API}/organizations`,
    params: queryParams({ q: this.q(), kind: this.kind(), status: this.status(), page: this.page(), page_size: PAGE_SIZE }),
  }));
}
