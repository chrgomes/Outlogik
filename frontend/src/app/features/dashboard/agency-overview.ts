import { DatePipe, DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { ToastService } from '../../shared/toast/toast';
import { Chart, ChartColors, ChartOptions } from './chart';
import { Overview, OverviewRow, changeText, changeTone } from './dashboard.types';

type Sort = 'drop' | 'gain' | 'ai' | 'errors' | 'name';
type Filter = 'all' | 'attention' | 'errors' | 'not_connected' | 'mine';

const change = (r: OverviewRow) =>
  r.visits !== null && r.visits_previous ? (r.visits - r.visits_previous) / r.visits_previous : null;

/** Every workspace side by side: what needs attention, totals, and a sortable client table. */
@Component({
  selector: 'ol-agency-overview',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, DecimalPipe, RouterLink, Chart, EmptyState, ErrorState, LoadingState],
  template: `
    @if (data.error()) {
      <ol-error-state message="We couldn't load the dashboard." (retry)="data.reload()" />
    } @else if (data.value(); as o) {
      @if (o.workspaces.length === 0) {
        <ol-empty-state icon="briefcase" title="No clients yet"
          message="Add a client to see their websites, traffic and audits here, side by side." />
      } @else {
        <div class="dash-kpis mb-4">
          @for (k of kpis(); track k.label) {
            <div class="dash-card">
              <div class="small text-muted">{{ k.label }}</div>
              <div class="dash-kpi-value">{{ k.value }}</div>
              <div class="small" [class]="k.tone">{{ k.note }}</div>
            </div>
          }
        </div>

        <div class="dash-row mb-4">
          <section class="dash-card" aria-labelledby="attn-h">
            <h2 id="attn-h" class="h6 mb-3">Needs attention</h2>
            @if (o.attention.length) {
              <ul class="dash-list">
                @for (a of o.attention; track a.workspace_id + a.kind) {
                  <li>
                    <span class="d-flex gap-2"><span class="dash-dot mt-2" [class]="'dash-dot-' + a.kind" aria-hidden="true"></span>
                      <span><strong class="d-block">{{ a.name }}</strong><span class="small text-muted">{{ a.text }}</span></span></span>
                    @switch (a.kind) {
                      @case ('reconnect') {
                        <a class="small fw-semibold text-nowrap" [routerLink]="['/o', org.slug(), 'integrations']" [queryParams]="{ workspace: a.workspace_id }">Reconnect</a>
                      }
                      @case ('not_connected') {
                        @if (org.can('integrations.manage')) {
                          <a class="small fw-semibold text-nowrap" [routerLink]="['/o', org.slug(), 'integrations']" [queryParams]="{ workspace: a.workspace_id }">Connect</a>
                        }
                      }
                      @case ('audit_errors') {
                        <button type="button" class="btn btn-link btn-sm p-0 fw-semibold text-nowrap" (click)="open(a.workspace_id, 'audits')">See audit</button>
                      }
                      @default {
                        <button type="button" class="btn btn-link btn-sm p-0 fw-semibold text-nowrap" (click)="open(a.workspace_id)">View</button>
                      }
                    }
                  </li>
                }
              </ul>
            } @else {
              <p class="dash-empty">Nothing needs attention right now.</p>
            }
          </section>

          <section class="dash-card dash-wide" aria-labelledby="trend-h">
            <div class="dash-head">
              <h2 id="trend-h" class="h6 mb-0">Visits across all clients, by week</h2>
              @if (o.weekly.length) {
                <span class="small text-muted"><span class="dash-key"></span>All visits
                  <span class="dash-key dash-key-search ms-3"></span>From AI tools</span>
              }
            </div>
            @if (o.weekly.length) {
              <ol-chart [options]="weeklyChart()" [label]="weeklyLabel()" height="230px" />
            } @else {
              <p class="dash-empty">Appears when Google Analytics is connected for at least one client.</p>
            }
          </section>
        </div>

        <section class="ol-table-card" aria-labelledby="clients-h">
          <div class="dash-head p-3 pb-2 align-items-end">
            <div>
              <h2 id="clients-h" class="h6 mb-0">Clients</h2>
              <span class="small text-muted">{{ o.period.start | date: 'MMM d' }} to {{ o.period.end | date: 'mediumDate' }}, compared with the {{ o.period.days }} days before</span>
            </div>
            <div class="d-flex flex-wrap gap-2">
              <div>
                <label class="form-label small text-muted mb-1" for="sort">Sort by</label>
                <select id="sort" class="form-select form-select-sm" [value]="sort()" (change)="sort.set($any($event.target).value)">
                  <option value="drop">Biggest drop in visits</option>
                  <option value="gain">Biggest gain in visits</option>
                  <option value="ai">Most visits from AI tools</option>
                  <option value="errors">Most audit errors</option>
                  <option value="name">Name</option>
                </select>
              </div>
              <div>
                <label class="form-label small text-muted mb-1" for="filter">Show</label>
                <select id="filter" class="form-select form-select-sm" [value]="filter()" (change)="filter.set($any($event.target).value)">
                  <option value="all">All clients</option>
                  <option value="attention">Needs attention</option>
                  <option value="errors">Audit errors</option>
                  <option value="not_connected">Google not connected</option>
                  @if (hasMine()) { <option value="mine">My clients</option> }
                </select>
              </div>
            </div>
          </div>
          <div class="table-responsive">
            <table class="table ol-table mb-0 dash-clients">
              <thead><tr><th>Client</th><th>Visits</th><th class="text-end">From AI tools</th><th class="text-end">Search clicks</th>
                <th>Audit</th><th>Google</th>@if (showTeam()) { <th>Account manager</th> }
                @if (canReport()) { <th><span class="visually-hidden">Report</span></th> }</tr></thead>
              <tbody>
                @for (r of rows(); track r.id) {
                  <tr>
                    <td><button type="button" class="btn btn-link p-0 fw-semibold text-start" (click)="open(r.id)">{{ r.name }}</button>
                      <span class="d-block small text-muted dash-break">{{ r.linked ? 'Shared by ' + r.organization_name : siteOf(r) }}</span></td>
                    <td>
                      @if (r.visits !== null) {
                        <span class="d-flex align-items-center gap-2">
                          <svg viewBox="0 0 100 30" preserveAspectRatio="none" class="dash-spark" aria-hidden="true"><polyline [attr.points]="spark(r.spark)" /></svg>
                          <span><strong>{{ r.visits | number }}</strong>
                            <span class="d-block small" [class]="tone(r)">{{ changeOf(r) }}</span></span>
                        </span>
                      } @else {
                        <span class="text-muted">No Analytics</span>
                      }
                    </td>
                    <td class="text-end">{{ r.ai_visits === null ? '—' : (r.ai_visits | number) }}</td>
                    <td class="text-end">{{ r.search_clicks === null ? '—' : (r.search_clicks | number) }}</td>
                    <td>
                      @if (r.audit; as a) {
                        <span class="badge rounded-pill" [class]="a.errors ? 'dash-sev-error' : a.warnings ? 'dash-sev-warning' : 'dash-sev-ok'">
                          {{ a.errors ? a.errors + (a.errors === 1 ? ' error' : ' errors') : a.warnings ? a.warnings + (a.warnings === 1 ? ' warning' : ' warnings') : 'No errors' }}</span>
                      } @else {
                        <span class="text-muted small">Not audited yet</span>
                      }
                    </td>
                    <td class="small" [class.text-danger]="r.google === 'error'" [class.text-muted]="r.google === 'not_connected'">
                      {{ r.google === 'connected' ? 'Connected' : r.google === 'error' ? 'Reconnect needed' : 'Not connected' }}</td>
                    @if (showTeam()) {
                      <td class="small">
                        {{ r.managers?.length ? r.managers!.join(', ') : '—' }}
                        <span class="d-block text-muted">{{ r.review ? 'Reviewed ' + (r.review.reviewed_at | date: 'MMM d') : 'Not reviewed yet' }}</span>
                        @if (org.can('workspaces.review')) {
                          <button type="button" class="btn btn-link btn-sm p-0" [disabled]="busy() === r.id" (click)="review(r)">Mark reviewed</button>
                        }
                      </td>
                    }
                    @if (canReport()) {
                      <td class="text-end"><a class="btn btn-sm btn-outline-secondary text-nowrap"
                        [routerLink]="['/o', org.slug(), 'reports']" [queryParams]="{ new: r.id }"
                        [attr.aria-label]="'Client report for ' + r.name">Client report</a></td>
                    }
                  </tr>
                } @empty {
                  <tr><td [attr.colspan]="6 + (showTeam() ? 1 : 0) + (canReport() ? 1 : 0)" class="text-muted">No clients match.</td></tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }
    } @else {
      <ol-loading-state label="Loading dashboard…" />
    }
  `,
})
export class AgencyOverview {
  readonly days = input(28);

  protected readonly org = inject(CurrentOrgService);
  private readonly ws = inject(WorkspaceService);
  private readonly api = inject(OrgApi);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);

  protected readonly data = httpResource<Overview>(() => ({
    url: this.api.url('dashboard/overview'), params: { days: this.days() } }));
  protected readonly sort = signal<Sort>('drop');
  protected readonly filter = signal<Filter>('all');
  protected readonly busy = signal<string | null>(null);

  protected readonly showTeam = computed(() => (this.data.value()?.workspaces ?? []).some((r) => r.managers !== null));
  protected readonly canReport = computed(() => this.org.can('reports.create'));
  protected readonly hasMine = computed(() => (this.data.value()?.workspaces ?? []).some((r) => r.assigned_to_me));

  protected readonly kpis = computed(() => {
    const t = this.data.value()?.totals;
    if (!t) return [];
    const out = [{ label: this.org.isAgency() ? 'Clients' : 'Workspaces', value: (this.org.isAgency() ? t.clients : t.workspaces).toLocaleString(),
      note: `${t.websites} ${t.websites === 1 ? 'website' : 'websites'}`, tone: 'text-muted' }];
    if (t.visits !== null) {
      out.push({ label: 'Visits, all clients', value: t.visits.toLocaleString(),
        note: changeText(t.visits, t.visits_previous), tone: changeTone(t.visits, t.visits_previous) });
      out.push({ label: 'Visits from AI tools', value: (t.ai_visits ?? 0).toLocaleString(),
        note: changeText(t.ai_visits ?? 0, t.ai_visits_previous), tone: changeTone(t.ai_visits ?? 0, t.ai_visits_previous) });
    }
    if (t.with_audit_errors !== null) {
      out.push({ label: 'Clients with audit errors', value: t.with_audit_errors.toLocaleString(),
        note: 'From each website’s latest audit', tone: 'text-muted' });
    }
    if (t.google_not_connected !== null) {
      out.push({ label: 'Google not connected', value: t.google_not_connected.toLocaleString(),
        note: `Of ${t.workspaces}`, tone: 'text-muted' });
    }
    return out;
  });

  protected readonly rows = computed(() => {
    const o = this.data.value();
    if (!o) return [];
    const attention = new Set(o.attention.map((a) => a.workspace_id));
    const f = this.filter();
    const list = o.workspaces.filter((r) =>
      f === 'all' || (f === 'attention' && attention.has(r.id)) || (f === 'errors' && !!r.audit?.errors)
      || (f === 'not_connected' && r.google === 'not_connected') || (f === 'mine' && r.assigned_to_me));
    const by: Record<Sort, (a: OverviewRow, b: OverviewRow) => number> = {
      // Rows without a comparison go last, whichever way.
      drop: (a, b) => (change(a) ?? Infinity) - (change(b) ?? Infinity),
      gain: (a, b) => (change(b) ?? -Infinity) - (change(a) ?? -Infinity),
      ai: (a, b) => (b.ai_visits ?? -1) - (a.ai_visits ?? -1),
      errors: (a, b) => (b.audit?.errors ?? -1) - (a.audit?.errors ?? -1),
      name: () => 0,
    };
    return [...list].sort((a, b) => by[this.sort()](a, b) || a.name.localeCompare(b.name));
  });

  protected readonly weeklyChart = computed<ChartOptions>(() => {
    const w = this.data.value()?.weekly ?? [];
    const label = (iso: string) => new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    return (c: ChartColors) => ({
      grid: { left: 48, right: 40, top: 12, bottom: 28 },
      xAxis: { type: 'category', data: w.map((x) => label(x.week_start)), axisLine: { lineStyle: { color: c.grid } },
        axisTick: { show: false }, axisLabel: { color: c.muted, hideOverlap: true } },
      yAxis: [
        { type: 'value', splitLine: { lineStyle: { color: c.grid } }, axisLabel: { color: c.muted } },
        { type: 'value', splitLine: { show: false }, axisLabel: { color: c.search } },
      ],
      series: [
        { name: 'All visits', type: 'bar', data: w.map((x) => x.sessions), itemStyle: { color: c.primary }, barMaxWidth: 22 },
        { name: 'From AI tools', type: 'line', yAxisIndex: 1, data: w.map((x) => x.ai_visits),
          lineStyle: { color: c.search, width: 2 }, itemStyle: { color: c.search }, symbolSize: 5 },
      ],
    });
  });

  protected readonly weeklyLabel = computed(() => {
    const w = this.data.value()?.weekly ?? [];
    return w.length ? `Weekly visits across all clients for the last ${w.length} weeks, from ${w[0].sessions.toLocaleString()} to ${w[w.length - 1].sessions.toLocaleString()} a week` : '';
  });

  protected changeOf(r: OverviewRow): string {
    return r.visits_previous === null ? 'No earlier data' : changeText(r.visits ?? 0, r.visits_previous).replace(/ vs .*/, '');
  }
  protected siteOf(r: OverviewRow): string {
    return r.website ? r.website.replace(/^https?:\/\//, '') : 'No website yet';
  }
  protected tone(r: OverviewRow): string {
    return changeTone(r.visits ?? 0, r.visits_previous);
  }
  protected spark(values: number[]): string {
    const max = Math.max(...values, 1);
    return values.map((v, i) => `${(i / Math.max(values.length - 1, 1)) * 100},${28 - (v / max) * 26}`).join(' ');
  }

  /** Switch to that workspace's dashboard (or another page for it). */
  protected open(id: string, page?: string): void {
    this.ws.select(id);
    if (page) void this.router.navigate(['/o', this.org.slug(), page]);
  }

  protected async review(r: OverviewRow): Promise<void> {
    this.busy.set(r.id);
    try {
      await this.api.markReviewed(r.id);
      this.toast.success(`${r.name} marked as reviewed.`);
      this.data.reload();
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(null);
    }
  }
}
