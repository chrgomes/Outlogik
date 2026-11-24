import { DIALOG_DATA, DialogRef } from '@angular/cdk/dialog';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { apiProblem } from '../../core/api-errors';
import { Report, ReportSection } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';

export interface NewReportData {
  /** Preselected workspace (from the agency dashboard's Client report button). */
  workspaceId?: string | null;
}

const SECTIONS: { key: ReportSection; label: string; hint: string; permission: string }[] = [
  { key: 'traffic', label: 'Traffic', hint: 'Visits, visitors, channels and top pages', permission: 'analytics.read' },
  { key: 'ai', label: 'Visits from AI tools', hint: 'ChatGPT, Perplexity, Gemini and others', permission: 'analytics.read' },
  { key: 'search', label: 'Google search', hint: 'Clicks, searches, positions and quick wins', permission: 'analytics.read' },
  { key: 'audit', label: 'Website audit', hint: 'Errors, warnings and how to fix them', permission: 'audits.read' },
];
const MAX_DAYS = 486;

/** Make a report: workspace, period, comparison, sections and an optional title. Closes with it. */
@Component({
  selector: 'ol-new-report-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h2 class="h5 mb-1">New report</h2>
    <p class="text-muted small mb-3">A PDF and CSV files with the figures as they are now. Saved reports don’t change when new data arrives.</p>
    @if (error()) { <div class="alert alert-danger" role="alert">{{ error() }}</div> }
    <form (submit)="$event.preventDefault(); create()" novalidate>
      <div class="mb-3">
        <label class="form-label" for="r-ws">{{ org.isAgency() ? 'Client or workspace' : 'Workspace' }}</label>
        <select id="r-ws" class="form-select" (change)="workspaceId.set($any($event.target).value)">
          <option value="" disabled [selected]="!workspaceId()">Choose one</option>
          @for (w of ws.list.value() ?? []; track w.id) {
            <!-- [selected] per option: the list arrives after the select is drawn -->
            <option [value]="w.id" [selected]="w.id === workspaceId()">{{ w.name }}{{ w.linked ? ' (shared by ' + w.organization_name + ')' : '' }}</option>
          }
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label" for="r-title">Title <span class="text-muted fw-normal">(optional)</span></label>
        <input id="r-title" class="form-control" maxlength="200" [placeholder]="defaultTitle()"
          [value]="title()" (input)="title.set($any($event.target).value)" />
      </div>
      <div class="row g-3 mb-3">
        <div class="col-sm-6">
          <label class="form-label" for="r-period">Period</label>
          <select id="r-period" class="form-select" [value]="period()" (change)="period.set($any($event.target).value)">
            <option value="7">Last 7 days</option>
            <option value="28">Last 28 days</option>
            <option value="90">Last 90 days</option>
            <option value="custom">Custom range…</option>
          </select>
        </div>
        <div class="col-sm-6">
          <label class="form-label" for="r-compare">Compare with</label>
          <select id="r-compare" class="form-select" [value]="compare()" (change)="compare.set($any($event.target).value)">
            <option value="previous">The period before</option>
            <option value="year">Same period last year</option>
            <option value="none">No comparison</option>
          </select>
        </div>
        @if (period() === 'custom') {
          <div class="col-sm-6">
            <label class="form-label" for="r-start">From</label>
            <input id="r-start" type="date" class="form-control" [max]="today" [value]="start()" (input)="start.set($any($event.target).value)" />
          </div>
          <div class="col-sm-6">
            <label class="form-label" for="r-end">To</label>
            <input id="r-end" type="date" class="form-control" [max]="today" [value]="end()" (input)="end.set($any($event.target).value)" />
          </div>
        }
      </div>
      <fieldset class="mb-3">
        <legend class="form-label fs-6">Include</legend>
        @for (s of sections; track s.key) {
          <div class="form-check">
            <input class="form-check-input" type="checkbox" [id]="'r-' + s.key" [checked]="chosen().has(s.key)"
              [disabled]="!org.can(s.permission)" (change)="toggle(s.key)" />
            <label class="form-check-label" [for]="'r-' + s.key">{{ s.label }}
              <span class="d-block small text-muted">{{ org.can(s.permission) ? s.hint : 'Not part of your role' }}</span></label>
          </div>
        }
      </fieldset>
      <div class="d-flex justify-content-end gap-2">
        <button type="button" class="btn btn-outline-secondary" (click)="ref.close()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">{{ busy() ? 'Making the report…' : 'Make report' }}</button>
      </div>
    </form>
  `,
})
export class NewReportDialog {
  protected readonly ref = inject<DialogRef<Report>>(DialogRef);
  private readonly data = inject<NewReportData | null>(DIALOG_DATA, { optional: true });
  protected readonly org = inject(CurrentOrgService);
  protected readonly ws = inject(WorkspaceService);
  private readonly api = inject(OrgApi);

  protected readonly sections = SECTIONS;
  protected readonly today = new Date().toISOString().slice(0, 10);
  protected readonly workspaceId = signal(this.data?.workspaceId ?? this.ws.current()?.id ?? '');
  protected readonly title = signal('');
  protected readonly period = signal<'7' | '28' | '90' | 'custom'>('28');
  protected readonly compare = signal<'previous' | 'year' | 'none'>('previous');
  protected readonly start = signal('');
  protected readonly end = signal('');
  protected readonly chosen = signal(new Set(SECTIONS.filter((s) => this.org.can(s.permission)).map((s) => s.key)));
  protected readonly busy = signal(false);
  protected readonly error = signal('');

  protected readonly defaultTitle = computed(() => {
    const w = (this.ws.list.value() ?? []).find((x) => x.id === this.workspaceId());
    return w ? `${w.name}: marketing report` : 'Marketing report';
  });

  protected toggle(key: ReportSection): void {
    const next = new Set(this.chosen());
    if (next.has(key)) next.delete(key); else next.add(key);
    this.chosen.set(next);
  }

  protected async create(): Promise<void> {
    this.error.set('');
    if (!this.workspaceId()) return this.error.set('Choose a workspace.');
    if (!this.chosen().size) return this.error.set('Choose at least one thing to include.');
    const custom = this.period() === 'custom';
    if (custom) {
      const s = this.start(), e = this.end();
      if (!s || !e) return this.error.set('Choose a start and an end date.');
      if (s > e) return this.error.set('The start date is after the end date.');
      if ((Date.parse(e) - Date.parse(s)) / 86_400_000 + 1 > MAX_DAYS) return this.error.set('Choose a period of 16 months or less.');
    }
    this.busy.set(true);
    try {
      const report = await this.api.createReport(this.workspaceId(), {
        title: this.title().trim() || null,
        sections: SECTIONS.map((s) => s.key).filter((k) => this.chosen().has(k)),
        days: custom ? null : Number(this.period()),
        start: custom ? this.start() : null,
        end: custom ? this.end() : null,
        compare: this.compare(),
      });
      this.ref.close(report);
    } catch (err) {
      this.error.set(apiProblem(err).message);
      this.busy.set(false);
    }
  }
}
