import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { AuditFrequency, WebsiteAudits } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { ToastService } from '../../shared/toast/toast';
import { IssueCounts } from './audit-parts';

/** Every website with its latest audit: run one, choose a schedule, open the results. */
@Component({
  selector: 'ol-audits-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, PageHeader, EmptyState, ErrorState, LoadingState, IssueCounts],
  template: `
    <ol-page-header title="Audits"
      description="A check of each website's pages for technical, SEO and AI search problems, with how to fix them." />

    @if (sites.error()) {
      <ol-error-state message="We couldn't load audits." (retry)="sites.reload()" />
    } @else if (sites.hasValue()) {
      @if (rows().length === 0) {
        <ol-empty-state icon="heart-pulse" title="No websites to audit"
          message="Add a website first. Audits check its pages and list what to fix." />
      } @else {
        <div class="ol-table-card">
          <table class="table ol-table">
            <thead><tr><th>Website</th><th>Latest audit</th><th>Issues</th><th>Schedule</th>
              <th><span class="visually-hidden">Actions</span></th></tr></thead>
            <tbody>
              @for (s of rows(); track s.website_id) {
                <tr>
                  <td>
                    <span class="fw-medium d-block">{{ s.website_name }}</span>
                    <span class="small text-muted">{{ s.url }}</span>
                    @if (showWorkspace()) {<span class="small text-muted d-block">{{ s.workspace_name }}</span>}
                  </td>
                  <td class="text-nowrap">
                    @if (s.latest; as a) {
                      @switch (a.status) {
                        @case ('queued') { <span class="text-muted">Waiting to start…</span> }
                        @case ('running') { <span class="text-muted">Running…</span> }
                        @case ('failed') { <span class="text-danger">Didn't finish</span> }
                        @default {
                          <a class="row-link" [routerLink]="['/o', org.slug(), 'audits', a.workspace_id, a.id]">
                            {{ a.finished_at | date: 'mediumDate' }}</a>
                          <span class="small text-muted d-block">{{ a.pages_crawled }} pages</span>
                        }
                      }
                    } @else {
                      <span class="text-muted">Never</span>
                    }
                  </td>
                  <td>
                    @if (s.latest?.status === 'completed') {
                      <ol-issue-counts [errors]="s.latest!.errors" [warnings]="s.latest!.warnings" [notices]="s.latest!.notices" />
                    }
                  </td>
                  <td>
                    @if (canRun(s)) {
                      <select class="form-select form-select-sm" [attr.aria-label]="'Schedule for ' + s.website_name"
                        [value]="s.audit_frequency" (change)="schedule(s, $any($event.target).value)">
                        <option value="off">Only when I run it</option>
                        <option value="weekly">Weekly</option>
                        <option value="monthly">Monthly</option>
                      </select>
                    } @else {
                      <span class="text-muted">{{ frequencyLabel[s.audit_frequency] }}</span>
                    }
                  </td>
                  <td class="text-end">
                    @if (canRun(s)) {
                      <button type="button" class="btn btn-sm btn-outline-secondary text-nowrap"
                        [disabled]="busy() === s.website_id || isActive(s)" (click)="run(s)">
                        {{ isActive(s) ? 'Running…' : 'Run audit' }}
                      </button>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    } @else {
      <ol-loading-state label="Loading audits…" />
    }
  `,
  styles: `.form-select-sm { min-width: 11rem; }`,
})
export class AuditsList {
  protected readonly org = inject(CurrentOrgService);
  private readonly ws = inject(WorkspaceService);
  private readonly api = inject(OrgApi);
  private readonly toast = inject(ToastService);

  protected readonly frequencyLabel: Record<AuditFrequency, string> = {
    off: 'Not scheduled', weekly: 'Weekly', monthly: 'Monthly',
  };
  protected readonly sites = httpResource<WebsiteAudits[]>(() => this.api.url('audits/websites'));
  /** Agencies see the selected workspace's websites (or all). */
  protected readonly rows = computed(() => {
    const all = this.sites.value() ?? [];
    const current = this.org.isAgency() ? this.ws.current() : null;
    return current ? all.filter((s) => s.workspace_id === current.id) : all;
  });
  protected readonly showWorkspace = computed(() => this.org.isAgency() && !this.ws.current());
  protected readonly busy = signal<string | null>(null);
  private readonly viewOnly = computed(
    () => new Set(this.ws.linked().filter((w) => w.access === 'view').map((w) => w.id)));

  constructor() {
    // While an audit runs, check every few seconds.
    const timer = setInterval(() => {
      if ((this.sites.value() ?? []).some((s) => this.isActive(s))) this.sites.reload();
    }, 4000);
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
  }

  protected isActive(s: WebsiteAudits): boolean {
    return s.latest?.status === 'queued' || s.latest?.status === 'running';
  }

  protected canRun(s: WebsiteAudits): boolean {
    return this.org.can('audits.run') && !this.viewOnly().has(s.workspace_id);
  }

  protected async run(s: WebsiteAudits): Promise<void> {
    this.busy.set(s.website_id);
    try {
      await this.api.startAudit(s.workspace_id, s.website_id);
      this.toast.success(`Audit of ${s.website_name} started. It usually takes a few minutes.`);
      this.sites.reload();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(null);
    }
  }

  protected async schedule(s: WebsiteAudits, frequency: AuditFrequency): Promise<void> {
    try {
      await this.api.setAuditFrequency(s.website_id, frequency);
      this.toast.success(frequency === 'off' ? `${s.website_name} won't be audited automatically.`
        : `${s.website_name} will be audited ${frequency === 'weekly' ? 'every week' : 'every month'}.`);
      this.sites.reload();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    }
  }
}
