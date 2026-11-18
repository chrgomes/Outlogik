import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { Icon } from '@brand/icon/icon';
import { apiProblem } from '../../core/api-errors';
import { Page } from '../../core/api.types';
import { queryParams } from '../../core/org-api.service';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Pager, Search, Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import { ADMIN_API, AdminApi, Subscriber } from './admin-api';

const PAGE_SIZE = 50;

/** /admin/newsletter: subscribers and their consent (CASL), with a CSV export. */
@Component({
  selector: 'ol-subscribers',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, Icon, PageHeader, EmptyState, ErrorState, LoadingState, Pager, Search, Status],
  template: `
    <ol-page-header title="Newsletter"
      description="People who signed up on the website. Only confirmed subscribers have agreed to receive emails.">
      <a actions class="btn btn-outline-secondary" [href]="exportUrl" download>
        <ol-icon name="download" /> Export confirmed
      </a>
    </ol-page-header>

    <div class="ol-toolbar">
      <ol-search placeholder="Search email" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Status" [value]="status()"
        (change)="status.set($any($event.target).value); page.set(1)">
        <option value="">All statuses</option>
        <option value="confirmed">Confirmed</option>
        <option value="pending">Waiting for confirmation</option>
        <option value="unsubscribed">Unsubscribed</option>
      </select>
    </div>

    @if (subs.error()) {
      <ol-error-state message="We couldn't load subscribers." (retry)="subs.reload()" />
    } @else if (subs.hasValue()) {
      @let list = subs.value();
      @if (list.total === 0) {
        @if (q() || status()) {
          <ol-empty-state icon="search" title="No matching subscribers" message="Try a different search or status." />
        } @else {
          <ol-empty-state icon="envelope" title="No subscribers yet"
            message="People who sign up in the website's footer will appear here." />
        }
      } @else {
        <div class="ol-table-card" [class.opacity-50]="subs.isLoading()">
          <table class="table ol-table">
            <thead>
              <tr><th>Email</th><th>Status</th><th>Consent given</th><th>Confirmed</th><th>Signed up on</th><th><span class="visually-hidden">Actions</span></th></tr>
            </thead>
            <tbody>
              @for (s of list.items; track s.id) {
                <tr>
                  <td>{{ s.email }}</td>
                  <td><ol-status [value]="s.status" /></td>
                  <td class="text-muted text-nowrap">{{ s.consent_at | date: 'mediumDate' }}</td>
                  <td class="text-muted text-nowrap">{{ s.confirmed_at ? (s.confirmed_at | date: 'mediumDate') : '—' }}</td>
                  <td class="text-muted">{{ s.source_page || '—' }}</td>
                  <td class="text-end">
                    <button type="button" class="icon-action" (click)="remove(s)" [attr.aria-label]="'Delete ' + s.email" title="Delete">
                      <ol-icon name="trash" />
                    </button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
        <ol-pager [page]="page()" [pageSize]="pageSize" [total]="list.total" (pageChange)="page.set($event)" />
      }
    } @else {
      <ol-loading-state label="Loading subscribers…" />
    }
    <p class="text-muted small mt-3">
      Sending newsletters isn't built into Outlogik yet. Export confirmed subscribers to your email
      service, and remove anyone who unsubscribes there.
    </p>
  `,
})
export class Subscribers {
  private readonly api = inject(AdminApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);
  protected readonly pageSize = PAGE_SIZE;
  protected readonly exportUrl = `${ADMIN_API}/newsletter/subscribers/export.csv`;
  protected readonly q = signal('');
  protected readonly status = signal('');
  protected readonly page = signal(1);
  private readonly params = computed(() =>
    queryParams({ q: this.q(), status: this.status(), page: this.page(), page_size: PAGE_SIZE }));
  protected readonly subs = httpResource<Page<Subscriber>>(() => ({
    url: `${ADMIN_API}/newsletter/subscribers`, params: this.params(),
  }));

  protected async remove(s: Subscriber): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: 'Delete this subscriber?',
      message: `${s.email} and their consent record will be deleted permanently. Use this for privacy requests; if they only want to stop receiving emails, they can unsubscribe instead.`,
      confirmLabel: 'Delete subscriber',
      danger: true,
    });
    if (!ok) return;
    try {
      await this.api.deleteSubscriber(s.id);
      this.toast.success('Subscriber deleted.');
      this.subs.reload();
    } catch (e) {
      this.toast.error(apiProblem(e).message);
    }
  }
}
