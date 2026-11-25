import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { Icon } from '@brand/icon/icon';
import { apiProblem } from '../../core/api-errors';
import { Report, ReportSection } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { ToastService } from '../../shared/toast/toast';
import { NewReportData, NewReportDialog } from './new-report-dialog';

const SECTION_LABEL: Record<ReportSection, string> = {
  traffic: 'Traffic', ai: 'AI tools', search: 'Google search', audit: 'Audit',
};

/** Saved reports: make one, download it as PDF or CSV, or delete it. */
@Component({
  selector: 'ol-reports-list',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, Icon, PageHeader, EmptyState, ErrorState, LoadingState],
  template: `
    <ol-page-header title="Reports"
      description="Reports of traffic, AI tool visits, Google search and audits for a period, to download as PDF or CSV." />

    @if (canCreate()) {
      <div class="mb-3">
        <button type="button" class="btn btn-primary" (click)="newReport()">New report</button>
      </div>
    }

    @if (reports.error()) {
      <ol-error-state message="We couldn't load reports." (retry)="reports.reload()" />
    } @else if (reports.value(); as list) {
      @if (list.length === 0) {
        <ol-empty-state icon="file-earmark-bar-graph" title="No reports yet"
          [message]="canCreate() ? 'Make a report to download the figures for a period as a PDF, or as CSV files for a spreadsheet.' : 'Reports made for you will appear here.'" />
      } @else {
        <div class="ol-table-card">
          <div class="table-responsive">
            <table class="table ol-table mb-0">
              <thead><tr><th>Report</th><th>Period</th><th>Made</th><th><span class="visually-hidden">Downloads</span></th></tr></thead>
              <tbody>
                @for (r of list; track r.id) {
                  <tr>
                    <td class="rep-title">
                      <span class="fw-medium d-block">{{ r.title }}</span>
                      @if (showWorkspace()) { <span class="small text-muted d-block">{{ r.workspace_name }}</span> }
                      <span class="small text-muted">{{ sectionNames(r) }}</span>
                      @if (r.unavailable.length) {
                        <details class="small mt-1">
                          <summary class="text-muted">{{ r.unavailable.length }} {{ r.unavailable.length === 1 ? 'note' : 'notes' }} about missing data</summary>
                          <ul class="mb-0 ps-3 mt-1">@for (u of r.unavailable; track u) { <li>{{ u }}</li> }</ul>
                        </details>
                      }
                    </td>
                    <td class="text-nowrap">{{ r.period_start | date: 'MMM d' }} – {{ r.period_end | date: 'mediumDate' }}
                      <span class="small text-muted d-block">{{ compareText(r) }}</span></td>
                    <td class="text-nowrap">{{ r.created_at | date: 'mediumDate' }}
                      @if (r.created_by) { <span class="small text-muted d-block">{{ r.created_by }}</span> }</td>
                    <td class="text-end">
                      <div class="d-inline-flex flex-wrap gap-2 justify-content-end align-items-start">
                        <a class="btn btn-sm btn-outline-secondary text-nowrap" [href]="pdfUrl(r)" download
                          [attr.aria-label]="'Download PDF of ' + r.title"><ol-icon name="download" size="0.9rem" /> PDF</a>
                        @if (r.csv_files.length) {
                          <details class="rep-csv">
                            <summary class="btn btn-sm btn-outline-secondary text-nowrap" [attr.aria-label]="'CSV files of ' + r.title">CSV</summary>
                            <ul class="rep-menu">
                              @for (f of r.csv_files; track f.name) {
                                <li><a [href]="csvUrl(r, f.name)" download>{{ f.label }}</a></li>
                              }
                            </ul>
                          </details>
                        }
                        @if (canCreate()) {
                          <button type="button" class="btn btn-sm btn-link text-danger" [disabled]="busy() === r.id"
                            [attr.aria-label]="'Delete ' + r.title" (click)="remove(r)">Delete</button>
                        }
                      </div>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      }
    } @else {
      <ol-loading-state label="Loading reports…" />
    }
  `,
  styles: `
    .rep-title { max-width: 26rem; }
    .rep-csv { position: relative; summary { list-style: none; } summary::-webkit-details-marker { display: none; } }
    .rep-menu { position: absolute; right: 0; z-index: 5; min-width: 15rem; margin: 0.25rem 0 0; padding: 0.35rem 0;
      list-style: none; text-align: left; background: var(--ol-surface-raised); border: 1px solid var(--ol-border);
      border-radius: var(--bs-border-radius); box-shadow: var(--ol-shadow);
      a { display: block; padding: 0.4rem 0.9rem; color: var(--ol-text); text-decoration: none; }
      a:hover, a:focus-visible { background: var(--ol-surface-hover); } }
  `,
})
export class ReportsList {
  protected readonly org = inject(CurrentOrgService);
  private readonly ws = inject(WorkspaceService);
  private readonly api = inject(OrgApi);
  private readonly dialog = inject(DialogService);
  private readonly toast = inject(ToastService);

  /** The selected workspace's reports; agencies with "All workspaces" see every one. */
  private readonly workspaceId = computed(() => this.ws.current()?.id ?? null);
  // Waits for the workspace list, so it asks once, for the right workspace.
  protected readonly reports = httpResource<Report[]>(() => this.ws.list.hasValue() || this.ws.list.error()
    ? { url: this.api.url('reports'), params: queryParams({ workspace_id: this.workspaceId() }) }
    : undefined);
  protected readonly showWorkspace = computed(() => this.org.isAgency() && !this.workspaceId());
  protected readonly canCreate = computed(() => this.org.can('reports.create'));
  protected readonly busy = signal<string | null>(null);

  constructor() {
    // From the agency dashboard's "Client report" button: /reports?new=<workspace id>
    const route = inject(ActivatedRoute);
    const workspace = route.snapshot.queryParamMap.get('new');
    if (workspace && this.canCreate()) {
      void inject(Router).navigate([], { relativeTo: route, queryParams: {}, replaceUrl: true });
      queueMicrotask(() => this.newReport(workspace));
    }
  }

  protected sectionNames(r: Report): string {
    return r.sections.map((s) => SECTION_LABEL[s]).join(' · ');
  }

  protected compareText(r: Report): string {
    if (r.compare === 'none' || !r.compare_start) return 'No comparison';
    const f = (d: string) => new Date(d + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    return `Compared with ${r.compare === 'year' ? 'last year' : f(r.compare_start) + ' – ' + f(r.compare_end!)}`;
  }

  protected pdfUrl(r: Report): string {
    return this.api.url(`reports/${r.id}/pdf`);
  }
  protected csvUrl(r: Report, table: string): string {
    return this.api.url(`reports/${r.id}/csv/${table}`);
  }

  protected async newReport(workspaceId?: string): Promise<void> {
    const report = await this.dialog.open<Report, NewReportData>(NewReportDialog, { workspaceId: workspaceId ?? null });
    if (report) {
      this.toast.success(`“${report.title}” is ready to download.`);
      this.reports.reload();
    }
  }

  protected async remove(r: Report): Promise<void> {
    const ok = await this.dialog.confirm({
      title: 'Delete this report?', danger: true, confirmLabel: 'Delete',
      message: `“${r.title}” will be deleted. Anyone you sent the PDF or CSV files to keeps their copy.`,
    });
    if (!ok) return;
    this.busy.set(r.id);
    try {
      await this.api.deleteReport(r.id);
      this.toast.success('Report deleted.');
      this.reports.reload();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(null);
    }
  }
}
