import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { Page } from '../../core/api.types';
import { queryParams } from '../../core/org-api.service';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Pager, Search, Status } from '../../shared/table/table-parts';
import {
  ADMIN_API, KIND_LABELS, LEAD_STATUSES, LeadCounts, LeadKind, LeadListItem, LeadStatus, SERVICE_LABELS,
} from './admin-api';

const PAGE_SIZE = 25;

/** /admin/leads: consultation requests and messages from the website. */
@Component({
  selector: 'ol-leads-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, Icon, PageHeader, EmptyState, ErrorState, LoadingState, Pager,
    Search, Status],
  template: `
    <ol-page-header title="Leads" description="Consultation requests and messages from the website.">
      <a actions class="btn btn-outline-secondary" [href]="exportUrl()" download>
        <ol-icon name="download" /> Export CSV
      </a>
    </ol-page-header>

    <div class="ol-toolbar">
      <ol-search placeholder="Search name, email or company" [value]="q()" (search)="q.set($event); page.set(1)" />
      <select class="form-select" aria-label="Status" [value]="status()"
        (change)="status.set($any($event.target).value); page.set(1)">
        <option value="">All except spam</option>
        @for (s of statuses; track s.value) {
          <option [value]="s.value">{{ s.label }}{{ counts.hasValue() ? ' (' + counts.value()[s.value] + ')' : '' }}</option>
        }
      </select>
      <select class="form-select" aria-label="Type" [value]="kind()"
        (change)="kind.set($any($event.target).value); page.set(1)">
        <option value="">All types</option>
        <option value="consultation">Consultations</option>
        <option value="contact">Messages</option>
      </select>
    </div>

    @if (leads.error()) {
      <ol-error-state message="We couldn't load the leads." (retry)="leads.reload()" />
    } @else if (leads.hasValue()) {
      @let list = leads.value();
      @if (list.total === 0) {
        @if (q() || status() || kind()) {
          <ol-empty-state icon="search" title="No matching leads" message="Try a different search or filter." />
        } @else {
          <ol-empty-state icon="inbox" title="No leads yet"
            message="Consultation requests and messages sent from the website will appear here." />
        }
      } @else {
        <div class="ol-table-card" [class.opacity-50]="leads.isLoading()">
          <table class="table ol-table table-hover">
            <thead>
              <tr><th>Received</th><th>From</th><th>Type</th><th>Services</th><th>Source</th><th>Status</th></tr>
            </thead>
            <tbody>
              @for (l of list.items; track l.id) {
                <tr [class.fw-semibold]="l.status === 'new'">
                  <td class="text-muted text-nowrap">{{ l.created_at | date: 'MMM d, h:mm a' }}</td>
                  <td>
                    <a class="row-link" [routerLink]="[l.id]">{{ l.name }}</a>
                    <small class="d-block text-muted fw-normal">{{ l.company || l.email }}</small>
                  </td>
                  <td class="fw-normal">{{ kindLabels[l.kind] }}</td>
                  <td class="text-muted fw-normal">{{ services(l) }}</td>
                  <td class="text-muted fw-normal">{{ l.utm_source || '—' }}</td>
                  <td>
                    <ol-status [value]="l.status" />
                    @if (l.note_count) {
                      <small class="text-muted fw-normal ms-1" [attr.aria-label]="l.note_count + ' notes'">· {{ l.note_count }} {{ l.note_count === 1 ? 'note' : 'notes' }}</small>
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
      <ol-loading-state label="Loading leads…" />
    }
  `,
})
export class LeadsList {
  protected readonly pageSize = PAGE_SIZE;
  protected readonly statuses = LEAD_STATUSES;
  protected readonly kindLabels = KIND_LABELS;
  protected readonly q = signal('');
  protected readonly status = signal<LeadStatus | ''>('');
  protected readonly kind = signal<LeadKind | ''>('');
  protected readonly page = signal(1);

  private readonly filters = computed(() => ({ q: this.q(), status: this.status(), kind: this.kind() }));
  protected readonly leads = httpResource<Page<LeadListItem>>(() => ({
    url: `${ADMIN_API}/leads`,
    params: queryParams({ ...this.filters(), page: this.page(), page_size: PAGE_SIZE }),
  }));
  protected readonly counts = httpResource<LeadCounts>(() => `${ADMIN_API}/leads/counts`);
  /** The CSV download uses the same filters as the list. */
  protected readonly exportUrl = computed(() => {
    const params = queryParams(this.filters()).toString();
    return `${ADMIN_API}/leads/export.csv${params ? '?' + params : ''}`;
  });

  protected services(lead: LeadListItem): string {
    if (lead.kind === 'contact') return '—';
    return lead.services.map((s) => SERVICE_LABELS[s] ?? s).join(', ');
  }
}
