import { DatePipe } from '@angular/common';
import { HttpErrorResponse, httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { apiProblem } from '../../core/api-errors';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { Status } from '../../shared/table/table-parts';
import { ToastService } from '../../shared/toast/toast';
import {
  ADMIN_API, AdminApi, BUDGET_LABELS, KIND_LABELS, LEAD_STATUSES, Lead, LeadStatus, SERVICE_LABELS,
  TOPIC_LABELS,
} from './admin-api';

const SPAM_REASONS: Record<string, string> = {
  honeypot: 'A hidden field that people never see was filled in.',
  too_fast: 'The form was sent within a few seconds of opening.',
};

/** /admin/leads/:leadId: everything sent, where it came from, status and notes. */
@Component({
  selector: 'ol-lead-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, FormsModule, RouterLink, Icon, PageHeader, EmptyState, ErrorState, LoadingState, Status],
  template: `
    <a routerLink="/admin/leads" class="back-link"><ol-icon name="arrow-left" /> Leads</a>

    @if (lead.error()) {
      @if (notFound()) {
        <ol-empty-state icon="inbox" title="Lead not found" message="It may have been deleted." />
      } @else {
        <ol-error-state message="We couldn't load this lead." (retry)="lead.reload()" />
      }
    } @else if (lead.hasValue()) {
      @let l = lead.value();
      <ol-page-header [title]="l.name" [description]="kindLabels[l.kind] + ' · received ' + (l.created_at | date: 'MMM d, y, h:mm a')">
        <div actions class="d-flex align-items-center gap-2">
          <label class="visually-hidden" for="lead-status">Status</label>
          <select id="lead-status" class="form-select" [ngModel]="l.status" (ngModelChange)="setStatus(l, $event)"
            [disabled]="busy()">
            @for (s of statuses; track s.value) { <option [value]="s.value">{{ s.label }}</option> }
          </select>
          <a class="btn btn-primary text-nowrap" [href]="mailto(l)"><ol-icon name="envelope" /> Reply</a>
          <button type="button" class="icon-action" (click)="remove(l)" aria-label="Delete lead" title="Delete lead">
            <ol-icon name="trash" />
          </button>
        </div>
      </ol-page-header>

      @if (l.status === 'spam' && l.spam_reason) {
        <div class="alert alert-warning">
          <strong>Marked as spam automatically.</strong> {{ spamReasons[l.spam_reason] ?? l.spam_reason }}
          If this is a real enquiry, change its status.
        </div>
      }

      <div class="lead-grid">
        <div>
          <section class="ol-section">
            <header><h2>{{ l.kind === 'consultation' ? 'Request' : 'Message' }}</h2></header>
            <dl class="facts">
              @if (l.kind === 'consultation') {
                <dt>Services</dt><dd>{{ services(l) }}</dd>
                <dt>Budget</dt><dd>{{ l.details.budget ? budgetLabels[l.details.budget] : 'Not given' }}</dd>
                <dt>Best time</dt><dd>{{ l.details.preferred_contact || 'Not given' }}</dd>
              } @else {
                <dt>Topic</dt><dd>{{ topicLabels[l.details.topic ?? 'general'] }}</dd>
              }
            </dl>
            @if (l.message) {
              <p class="message">{{ l.message }}</p>
            } @else {
              <p class="text-muted mb-0">No message.</p>
            }
          </section>

          <section class="ol-section">
            <header><h2>Notes</h2></header>
            <form (ngSubmit)="addNote(l)" class="mb-3">
              <label for="note" class="visually-hidden">Add a note</label>
              <textarea id="note" name="note" class="form-control mb-2" rows="3" maxlength="5000"
                placeholder="Add a note: calls made, what was agreed, next steps…" [(ngModel)]="note"></textarea>
              <button type="submit" class="btn btn-outline-secondary" [disabled]="busy() || !note().trim()">Add note</button>
            </form>
            @for (n of l.notes; track n.id) {
              <article class="note">
                <p class="mb-1">{{ n.body }}</p>
                <small class="text-muted">{{ n.author_name ?? 'Former staff member' }} · {{ n.created_at | date: 'MMM d, y, h:mm a' }}</small>
              </article>
            } @empty {
              <p class="text-muted mb-0">No notes yet.</p>
            }
          </section>
        </div>

        <aside>
          <section class="ol-section">
            <header><h2>Contact</h2></header>
            <dl class="facts facts--stacked">
              <dt>Email</dt><dd><a [href]="'mailto:' + l.email">{{ l.email }}</a></dd>
              @if (l.phone) { <dt>Phone</dt><dd><a [href]="'tel:' + l.phone">{{ l.phone }}</a></dd> }
              @if (l.company) { <dt>Company</dt><dd>{{ l.company }}</dd> }
              @if (l.website) {
                <dt>Website</dt>
                <dd><a [href]="websiteUrl(l.website)" target="_blank" rel="noopener noreferrer">{{ l.website }} <ol-icon name="box-arrow-up-right" /></a></dd>
              }
            </dl>
          </section>
          <section class="ol-section">
            <header><h2>Where they came from</h2></header>
            @if (source().length) {
              <dl class="facts facts--stacked">
                @for (s of source(); track s.label) { <dt>{{ s.label }}</dt><dd class="text-break">{{ s.value }}</dd> }
              </dl>
            } @else {
              <p class="text-muted mb-0">Not recorded.</p>
            }
          </section>
          <p class="text-muted small">Status: <ol-status [value]="l.status" /> · last updated {{ l.updated_at | date: 'MMM d, h:mm a' }}</p>
        </aside>
      </div>
    } @else {
      <ol-loading-state label="Loading lead…" />
    }
  `,
  styles: `
    .lead-grid { display: grid; grid-template-columns: minmax(0, 2fr) minmax(16rem, 1fr); gap: 1.5rem; align-items: start; }
    @media (max-width: 991.98px) { .lead-grid { grid-template-columns: 1fr; } }
    .facts { display: grid; grid-template-columns: 8rem 1fr; gap: 0.5rem 1rem; margin-bottom: 1rem; }
    .facts dt { font-weight: 500; color: var(--ol-text-muted); }
    .facts dd { margin: 0; }
    .facts--stacked { grid-template-columns: 1fr; gap: 0.125rem; }
    .facts--stacked dd { margin-bottom: 0.625rem; }
    .message { white-space: pre-line; margin: 0; padding: 1rem; border-radius: var(--bs-border-radius);
      background: var(--ol-surface-hover); }
    .note { padding: 0.75rem 0; border-top: 1px solid var(--ol-border); }
    .note p { white-space: pre-line; }
    select.form-select { width: auto; }
  `,
})
export class LeadDetail {
  readonly leadId = input.required<string>();
  private readonly api = inject(AdminApi);
  private readonly dialogs = inject(DialogService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  protected readonly statuses = LEAD_STATUSES;
  protected readonly kindLabels = KIND_LABELS;
  protected readonly budgetLabels = BUDGET_LABELS;
  protected readonly topicLabels = TOPIC_LABELS;
  protected readonly spamReasons = SPAM_REASONS;
  protected readonly busy = signal(false);
  protected readonly note = signal('');

  protected readonly lead = httpResource<Lead>(() => `${ADMIN_API}/leads/${this.leadId()}`);
  protected readonly notFound = computed(
    () => (this.lead.error() as HttpErrorResponse | undefined)?.status === 404,
  );
  protected readonly source = computed(() => {
    const a = this.lead.hasValue() ? this.lead.value().attribution : {};
    const campaign = (['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content'] as const)
      .filter((k) => a[k]).map((k) => `${k.slice(4)}: ${a[k]}`).join(' · ');
    return [
      { label: 'Sent from', value: a.page },
      { label: 'First page of the visit', value: a.landing_page },
      { label: 'Referred by', value: a.referrer },
      { label: 'Campaign', value: campaign },
    ].filter((s) => s.value);
  });

  protected services(l: Lead): string {
    return (l.details.services ?? []).map((s) => SERVICE_LABELS[s] ?? s).join(', ') || '—';
  }

  protected mailto(l: Lead): string {
    const subject = l.kind === 'consultation' ? 'Your free consultation with Outlogik' : 'Re: your message to Outlogik';
    return `mailto:${l.email}?subject=${encodeURIComponent(subject)}`;
  }

  /** Websites are typed by visitors, so only http(s) links are made clickable. */
  protected websiteUrl(site: string): string {
    return /^https?:\/\//i.test(site) ? site : `https://${site}`;
  }

  protected async setStatus(l: Lead, status: LeadStatus): Promise<void> {
    this.busy.set(true);
    try {
      this.lead.set(await this.api.setLeadStatus(l.id, status));
      this.toast.success(`Marked as ${status}.`);
    } catch (e) {
      this.toast.error(apiProblem(e).message);
      this.lead.reload();
    } finally {
      this.busy.set(false);
    }
  }

  protected async addNote(l: Lead): Promise<void> {
    const body = this.note().trim();
    if (!body) return;
    this.busy.set(true);
    try {
      this.lead.set(await this.api.addNote(l.id, body));
      this.note.set('');
    } catch (e) {
      this.toast.error(apiProblem(e).message);
    } finally {
      this.busy.set(false);
    }
  }

  protected async remove(l: Lead): Promise<void> {
    const ok = await this.dialogs.confirm({
      title: 'Delete this lead?',
      message: `${l.name}'s ${l.kind === 'consultation' ? 'request' : 'message'} and its notes will be deleted permanently. Use this for privacy requests or junk; to file a lead away, set its status to Closed instead.`,
      confirmLabel: 'Delete lead',
      danger: true,
    });
    if (!ok) return;
    try {
      await this.api.deleteLead(l.id);
      this.toast.success('Lead deleted.');
      await this.router.navigate(['/admin/leads']);
    } catch (e) {
      this.toast.error(apiProblem(e).message);
    }
  }
}
