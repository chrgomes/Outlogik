import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Page } from '../../core/api.types';
import { queryParams } from '../../core/org-api.service';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Pager, Search, Status } from '../../shared/table/table-parts';
import { PLATFORM_API, UserRow, staffLabel } from './platform-api';

const PAGE_SIZE = 50;

/** /admin/platform/users: everyone with an Outlogik account. */
@Component({
  selector: 'ol-platform-users',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, PageHeader, EmptyState, ErrorState, LoadingState, Pager, Search, Status],
  template: `
    <ol-page-header title="Users" description="Everyone with an Outlogik account, in any organization." />
    <div class="ol-toolbar">
      <ol-search placeholder="Search name or email" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Status" [value]="status()" (change)="status.set($any($event.target).value); page.set(1)">
        <option value="">All statuses</option>
        <option value="active">Active</option>
        <option value="suspended">Suspended</option>
      </select>
    </div>
    @if (list.error()) {
      <ol-error-state message="We couldn't load users." (retry)="list.reload()" />
    } @else if (list.value(); as l) {
      @if (l.total === 0) {
        <ol-empty-state icon="people" title="No users match" message="Try a different search or status." />
      } @else {
        <div class="ol-table-card" [class.opacity-50]="list.isLoading()">
          <div class="table-responsive">
            <table class="table ol-table mb-0">
              <thead><tr><th>Name</th><th>Email</th><th class="text-end">Organizations</th><th>Last signed in</th><th>Status</th></tr></thead>
              <tbody>
                @for (u of l.items; track u.id) {
                  <tr>
                    <td><a class="row-link fw-medium" [routerLink]="['/admin', 'platform', 'users', u.id]">{{ u.name }}</a>
                      @if (staffLabel(u); as s) { <span class="d-block small text-muted">Outlogik staff · {{ s }}</span> }</td>
                    <td>{{ u.email }}@if (!u.verified) {<span class="d-block small text-muted">Email not confirmed</span>}</td>
                    <td class="text-end">{{ u.organizations }}</td>
                    <td class="text-nowrap text-muted">{{ u.last_login_at ? (u.last_login_at | date: 'mediumDate') : 'Never' }}</td>
                    <td><ol-status [value]="u.active ? 'active' : 'suspended'" /></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
        <ol-pager [page]="page()" [pageSize]="pageSize" [total]="l.total" (pageChange)="page.set($event)" />
      }
    } @else {
      <ol-loading-state label="Loading users…" />
    }
  `,
})
export class PlatformUsers {
  protected readonly pageSize = PAGE_SIZE;
  protected readonly staffLabel = staffLabel;
  protected readonly q = signal('');
  protected readonly status = signal('');
  protected readonly page = signal(1);
  protected readonly list = httpResource<Page<UserRow>>(() => ({
    url: `${PLATFORM_API}/users`,
    params: queryParams({ q: this.q(), status: this.status(), page: this.page(), page_size: PAGE_SIZE }),
  }));
}
