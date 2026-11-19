import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi, queryParams } from '../../core/org-api.service';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { Chart, ChartColors, ChartOptions } from './chart';
import { Compare, Metric, WorkspaceDashboard, changeText, changeTone } from './dashboard.types';

export interface PeriodChoice {
  days: number | null;
  start: string | null;
  end: string | null;
  compare: Compare;
}

interface Kpi { label: string; value: string; note: string; tone: string; }

const shortDate = (iso: string) =>
  new Date(iso + 'T00:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

/** One workspace's dashboard: what changed, traffic, AI tools, search, pages and audits. */
@Component({
  selector: 'ol-workspace-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, DecimalPipe, PercentPipe, RouterLink, Chart, ErrorState, LoadingState],
  template: `
    @if (data.error()) {
      <ol-error-state message="We couldn't load the dashboard." (retry)="data.reload()" />
    } @else if (data.value(); as d) {
      @if (steps(); as s) {
        <section class="dash-card dash-start mb-4" aria-labelledby="start-h">
          <h2 id="start-h" class="h5 mb-1">Get your dashboard started</h2>
          <p class="text-muted mb-3">The dashboard shows only real data from your website and your Google accounts.</p>
          <ol class="dash-steps">
            @for (step of s; track step.title) {
              <li class="dash-card">
                <span class="small fw-semibold" [class.text-success]="step.done" [class.text-muted]="!step.done">
                  {{ step.done ? 'Done' : step.next ? 'Next' : 'Not started' }}</span>
                <span class="fw-semibold">{{ step.title }}</span>
                <span class="small text-muted">{{ step.text }}</span>
                @if (!step.done && step.link) {
                  <a class="btn btn-sm align-self-start mt-1" [class.btn-primary]="step.next"
                    [class.btn-outline-secondary]="!step.next" [routerLink]="step.link" [queryParams]="step.query">{{ step.action }}</a>
                }
              </li>
            }
          </ol>
        </section>
      }

      @if (d.changes.length) {
        <section class="dash-card dash-changed mb-4" aria-labelledby="changed-h">
          <h2 id="changed-h" class="h6 mb-2">What changed</h2>
          <ul class="mb-2">@for (c of d.changes; track c) { <li>{{ c }}</li> }</ul>
          <p class="small text-muted mb-0">Worked out from your synced data and audits. No guesses or forecasts.</p>
        </section>
      }

      @if (kpis().length) {
        <div class="dash-kpis mb-4">
          @for (k of kpis(); track k.label) {
            <div class="dash-card">
              <div class="small text-muted">{{ k.label }}</div>
              <div class="dash-kpi-value">{{ k.value }}</div>
              <div class="small" [class]="k.tone">{{ k.note }}</div>
            </div>
          }
        </div>
      }

      <div class="dash-row mb-4">
        <section class="dash-card dash-wide" aria-labelledby="visits-h">
          <div class="dash-head">
            <h2 id="visits-h" class="h6 mb-0">Visits per day</h2>
            @if (d.ga4 && d.period.compare !== 'none' && d.ga4.metrics.sessions.previous !== null) {
              <span class="small text-muted"><span class="dash-key"></span>This period
                <span class="dash-key dash-key-compare ms-3"></span>{{ compareLabel() }}</span>
            }
          </div>
          @if (d.ga4) {
            <ol-chart [options]="visitsChart()" [label]="'Visits per day, ' + periodLabel()" height="240px" />
          } @else {
            <p class="dash-empty">{{ analyticsMissing() }}</p>
          }
        </section>

        <section class="dash-card" aria-labelledby="ai-h">
          <h2 id="ai-h" class="h6 mb-1">Visits from AI tools</h2>
          @if (d.ga4) {
            <p class="small text-muted">{{ aiTotal() | number }} visits{{ ' ' }}·{{ ' ' }}{{ aiChange() }}</p>
            @if (d.ai_referrals.length) {
              <ul class="dash-bars">
                @for (r of d.ai_referrals; track r.name) {
                  <li><span class="d-flex justify-content-between"><span>{{ r.name }}</span><strong>{{ r.sessions | number }}</strong></span>
                    <span class="dash-bar"><span [style.width.%]="share(r.sessions, d.ai_referrals[0].sessions)"></span></span></li>
                }
              </ul>
            } @else {
              <p class="text-muted small">No visits from ChatGPT, Perplexity, Gemini, Copilot or Claude in this period.</p>
            }
            <p class="small text-muted mb-0 mt-3">Some AI tools don't pass on where a visitor came from, so the real number can be higher.</p>
          } @else {
            <p class="dash-empty">{{ analyticsMissing() }}</p>
          }
        </section>
      </div>

      <div class="dash-row mb-4">
        <section class="dash-card" aria-labelledby="search-h">
          <h2 id="search-h" class="h6 mb-1">Google search clicks</h2>
          @if (d.search_console; as sc) {
            <p class="small text-muted">{{ sc.metrics.clicks.value | number }} clicks from {{ sc.metrics.impressions.value | number }} searches
              · average position {{ sc.metrics.position.value | number: '1.1-1' }}</p>
            <ol-chart [options]="clicksChart()" [label]="'Google search clicks per day, ' + periodLabel()" height="170px" />
            <p class="small text-muted mb-0">Search Console has data through {{ sc.through | date: 'mediumDate' }}; it runs 2–3 days behind.</p>
          } @else {
            <p class="dash-empty">{{ searchMissing() }}</p>
          }
        </section>

        <section class="dash-card" aria-labelledby="channels-h">
          <h2 id="channels-h" class="h6 mb-3">Where visits came from</h2>
          @if (d.ga4) {
            <ul class="dash-bars">
              @for (c of d.channels.slice(0, 6); track c.name) {
                <li><span class="d-flex justify-content-between"><span>{{ c.name }}</span>
                  <span><strong>{{ c.sessions | number }}</strong>{{ ' ' }}<span class="text-muted">({{ c.sessions / channelTotal() | percent }})</span></span></span>
                  <span class="dash-bar"><span [style.width.%]="share(c.sessions, d.channels[0].sessions)"></span></span></li>
              }
            </ul>
          } @else {
            <p class="dash-empty">{{ analyticsMissing() }}</p>
          }
        </section>

        <section class="dash-card d-flex flex-column gap-3" aria-labelledby="audit-h">
          <div>
            <h2 id="audit-h" class="h6 mb-1">Latest website audit</h2>
            @if (d.audit; as a) {
              <p class="small text-muted mb-0">{{ a.website_name }} · {{ a.finished_at | date: 'mediumDate' }} · {{ a.pages_crawled }} pages checked</p>
            }
          </div>
          @if (d.audit; as a) {
            <div class="d-flex flex-wrap gap-2">
              <span class="badge rounded-pill dash-sev-error">{{ a.errors }} {{ a.errors === 1 ? 'error' : 'errors' }}</span>
              <span class="badge rounded-pill dash-sev-warning">{{ a.warnings }} {{ a.warnings === 1 ? 'warning' : 'warnings' }}</span>
              <span class="badge rounded-pill dash-sev-notice">{{ a.notices }} {{ a.notices === 1 ? 'notice' : 'notices' }}</span>
            </div>
            @if (a.history.length > 1) {
              <div>
                <div class="small fw-semibold">Errors and warnings, last {{ a.history.length }} audits</div>
                <ol-chart [options]="auditChart()" [label]="auditHistoryLabel()" height="110px" />
              </div>
            }
            @if (a.fix_first.length) {
              <div>
                <div class="small fw-semibold mb-1">Fix first</div>
                <ul class="dash-fix">
                  @for (f of a.fix_first; track f.check) {
                    <li><span class="dash-dot" [class]="'dash-dot-' + f.severity" aria-hidden="true"></span>
                      <span>{{ f.title }}<span class="text-muted"> ({{ f.count }})</span></span></li>
                  }
                </ul>
              </div>
            }
            <a class="fw-semibold mt-auto" [routerLink]="['/o', org.slug(), 'audits', a.workspace_id, a.id]">Open the audit</a>
          } @else {
            <p class="dash-empty">{{ d.setup.audits_visible ? 'No audit yet. An audit checks your pages for technical, SEO and AI search problems.' : 'Audits aren’t part of your role.' }}</p>
          }
        </section>
      </div>

      @if (d.top_pages.length) {
        <section class="ol-table-card mb-4" aria-labelledby="pages-h">
          <div class="dash-head p-3 pb-2"><h2 id="pages-h" class="h6 mb-0">Pages that bring the most visits</h2>
            <span class="small text-muted">The page each visit started on{{ d.pages_from ? ', from ' + (d.pages_from | date: 'mediumDate') : '' }}</span></div>
          <div class="table-responsive">
            <table class="table ol-table mb-0">
              <thead><tr><th>Page</th><th class="text-end">Visits</th><th class="text-end">Change</th><th class="text-end">Key events</th></tr></thead>
              <tbody>
                @for (p of d.top_pages; track p.path) {
                  <tr><td class="dash-break">{{ p.path }}</td><td class="text-end">{{ p.sessions | number }}</td>
                    <td class="text-end" [class]="tone(p.sessions, p.previous)">{{ pct(p.sessions, p.previous) }}</td>
                    <td class="text-end">{{ p.key_events | number: '1.0-0' }}</td></tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      }

      @if (d.search_console) {
        <div class="dash-row mb-4">
          <section class="dash-card" aria-labelledby="almost-h">
            <h2 id="almost-h" class="h6 mb-1">Searches you almost rank for</h2>
            <p class="small text-muted">Positions 8 to 20: just off, or at the bottom of, Google’s first page. Improving these pages is often the quickest win.</p>
            @if (d.almost_ranking.length) {
              <ul class="dash-list">
                @for (a of d.almost_ranking; track a.query + a.page) {
                  <li><span class="dash-break"><span class="d-block">{{ a.query }}</span>
                    <span class="small text-muted">{{ path(a.page) }} · {{ a.impressions | number }} searches</span></span>
                    <strong>#{{ a.position | number: '1.1-1' }}</strong></li>
                }
              </ul>
            } @else {
              <p class="dash-empty">No searches in positions 8 to 20 right now.</p>
            }
          </section>

          <section class="dash-card" aria-labelledby="lowctr-h">
            <h2 id="lowctr-h" class="h6 mb-1">Shown in search, rarely clicked</h2>
            <p class="small text-muted">On Google’s first page, but clicked less than half as often as your other pages{{ d.site_ctr !== null ? ' (' + (d.site_ctr | percent: '1.1-1') + ')' : '' }}. A clearer title and description usually help.</p>
            @if (d.low_ctr_pages.length) {
              <ul class="dash-list">
                @for (l of d.low_ctr_pages; track l.page) {
                  <li><span class="dash-break"><span class="d-block">{{ path(l.page) }}</span>
                    <span class="small text-muted">{{ l.impressions | number }} searches · {{ l.ctr | percent: '1.1-1' }} clicked · position {{ l.position | number: '1.1-1' }}</span></span>
                    @if (d.audit; as a) {
                      <a class="small fw-semibold text-nowrap" [routerLink]="['/o', org.slug(), 'audits', a.workspace_id, a.id]">Title advice</a>
                    }</li>
                }
              </ul>
            } @else {
              <p class="dash-empty">None of your pages stand out as rarely clicked.</p>
            }
          </section>
        </div>
        <p class="small text-muted mt-n3 mb-4">These two lists and the searches below cover the 28 days to {{ d.search_snapshot_end | date: 'mediumDate' }}, whatever period you choose.</p>
      }

      @if (d.top_queries.length) {
        <section class="ol-table-card mb-4" aria-labelledby="queries-h">
          <h2 id="queries-h" class="h6 p-3 pb-2 mb-0">Top Google searches</h2>
          <div class="table-responsive">
            <table class="table ol-table mb-0">
              <thead><tr><th>Search</th><th class="text-end">Clicks</th><th class="text-end">Impressions</th>
                <th class="text-end">Click rate</th><th class="text-end">Position</th></tr></thead>
              <tbody>
                @for (q of d.top_queries; track q.query) {
                  <tr><td class="dash-break">{{ q.query }}</td><td class="text-end">{{ q.clicks | number }}</td>
                    <td class="text-end">{{ q.impressions | number }}</td><td class="text-end">{{ q.ctr | percent: '1.1-1' }}</td>
                    <td class="text-end">{{ q.position | number: '1.1-1' }}</td></tr>
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
export class WorkspaceDashboardView {
  readonly workspaceId = input.required<string>();
  readonly period = input.required<PeriodChoice>();

  protected readonly org = inject(CurrentOrgService);
  private readonly api = inject(OrgApi);

  protected readonly data = httpResource<WorkspaceDashboard>(() => {
    const p = this.period();
    return {
      url: this.api.url(`workspaces/${this.workspaceId()}/dashboard`),
      params: queryParams({ days: p.days, start: p.start, end: p.end, compare: p.compare }),
    };
  });

  private readonly against = computed(() =>
    this.data.value()?.period.compare === 'year' ? 'last year' : 'before');
  protected readonly compareLabel = computed(() =>
    this.data.value()?.period.compare === 'year' ? 'Same period last year' : `The ${this.data.value()?.period.days} days before`);
  protected readonly periodLabel = computed(() => {
    const p = this.data.value()?.period;
    return p ? `${shortDate(p.start)} to ${shortDate(p.end)}` : '';
  });

  protected readonly steps = computed(() => {
    const d = this.data.value();
    if (!d || !this.org.can('websites.write')) return null;
    const s = d.setup;
    const google = s.google === 'connected' && (s.ga4 || s.search_console);
    if (s.websites && s.audited && google) return null;
    const base = ['/o', this.org.slug()];
    const items = [
      { title: '1. Add your website', done: s.websites > 0, text: 'The address of the website to track.',
        action: 'Add website', link: [...base, 'websites'], query: null },
      { title: '2. Run a website audit', done: s.audited, text: 'Finds technical, SEO and AI search problems. Takes a few minutes.',
        action: 'Go to Audits', link: this.org.can('audits.run') ? [...base, 'audits'] : null, query: null },
      { title: '3. Connect Google', done: google, text: 'Analytics and Search Console, read-only. Adds visits, AI tool visits and searches.',
        action: 'Go to Integrations', link: this.org.can('integrations.manage') ? [...base, 'integrations'] : null,
        query: { workspace: d.workspace_id } },
    ];
    const next = items.findIndex((i) => !i.done);
    return items.map((i, n) => ({ ...i, next: n === next }));
  });

  protected readonly aiTotal = computed(() => (this.data.value()?.ai_referrals ?? []).reduce((a, r) => a + r.sessions, 0));
  private readonly aiPrevious = computed(() => {
    // Compared only when the visits are (the same synced period).
    if (this.data.value()?.ga4?.metrics.sessions.previous == null) return null;
    return (this.data.value()?.ai_referrals ?? []).reduce((a, r) => a + (r.previous ?? 0), 0);
  });
  protected readonly aiChange = computed(() => changeText(this.aiTotal(), this.aiPrevious(), this.against()));
  protected readonly channelTotal = computed(() => (this.data.value()?.channels ?? []).reduce((a, r) => a + r.sessions, 0) || 1);

  protected readonly kpis = computed<Kpi[]>(() => {
    const d = this.data.value();
    if (!d) return [];
    const out: Kpi[] = [];
    const add = (label: string, m: Metric, digits = 0) => out.push({
      label, value: m.value.toLocaleString(undefined, { maximumFractionDigits: digits }),
      note: changeText(m.value, m.previous, this.against()), tone: changeTone(m.value, m.previous) });
    if (d.ga4) {
      add('Visits', d.ga4.metrics.sessions);
      add('Visitors', d.ga4.metrics.users);
      add('Visits from AI tools', { value: this.aiTotal(), previous: this.aiPrevious() });
    }
    if (d.search_console) add('Search clicks', d.search_console.metrics.clicks);
    if (d.ga4) add('Key events', d.ga4.metrics.key_events);
    if (d.audit) {
      const h = d.audit.history;
      const before = h.length > 1 ? h[h.length - 2].errors : null;
      out.push({ label: 'Audit errors', value: d.audit.errors.toLocaleString(),
        note: before === null ? 'First audit' : before === d.audit.errors ? 'Same as the audit before'
          : `${Math.abs(before - d.audit.errors)} ${before > d.audit.errors ? 'fewer' : 'more'} than the audit before`,
        tone: changeTone(d.audit.errors, before, true) });
    }
    return out;
  });

  protected readonly analyticsMissing = computed(() => {
    const s = this.data.value()?.setup;
    if (!s?.analytics_visible) return 'Traffic numbers aren’t part of your role.';
    if (s.google === 'error') return 'Google stopped accepting the connection. Reconnect it in Integrations.';
    return s.ga4 ? 'Waiting for the first sync from Google Analytics.' : 'Appears when Google Analytics is connected in Integrations.';
  });
  protected readonly searchMissing = computed(() => {
    const s = this.data.value()?.setup;
    if (!s?.analytics_visible) return 'Search numbers aren’t part of your role.';
    return s.search_console ? 'Waiting for the first sync from Search Console.' : 'Appears when Search Console is connected in Integrations.';
  });

  protected readonly visitsChart = computed<ChartOptions>(() => {
    const series = this.data.value()?.series ?? [];
    const days = series.map((p) => shortDate(p.day));
    const hasPrevious = series.some((p) => p.previous_sessions !== null);
    return (c: ChartColors) => ({
      grid: { left: 40, right: 24, top: 12, bottom: 28 },
      xAxis: { type: 'category', data: days, boundaryGap: false, axisLine: { lineStyle: { color: c.grid } },
        axisTick: { show: false }, axisLabel: { color: c.muted, hideOverlap: true } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: c.grid } }, axisLabel: { color: c.muted } },
      series: [
        ...(hasPrevious ? [{ name: this.compareLabel(), type: 'line', data: series.map((p) => p.previous_sessions),
          showSymbol: false, lineStyle: { color: c.compare, width: 1.5, type: 'dashed' }, itemStyle: { color: c.compare } }] : []),
        { name: 'Visits', type: 'line', data: series.map((p) => p.sessions), showSymbol: false,
          lineStyle: { color: c.primary, width: 2.5 }, itemStyle: { color: c.primary },
          areaStyle: { color: c.primary, opacity: 0.06 } },
      ],
    });
  });

  protected readonly clicksChart = computed<ChartOptions>(() => {
    const series = (this.data.value()?.series ?? []).filter((p) => p.clicks !== null);
    return (c: ChartColors) => ({
      grid: { left: 32, right: 8, top: 8, bottom: 24 },
      xAxis: { type: 'category', data: series.map((p) => shortDate(p.day)), axisLine: { lineStyle: { color: c.grid } },
        axisTick: { show: false }, axisLabel: { color: c.muted, hideOverlap: true } },
      yAxis: { type: 'value', splitLine: { lineStyle: { color: c.grid } }, axisLabel: { color: c.muted }, minInterval: 1 },
      series: [{ name: 'Clicks', type: 'bar', data: series.map((p) => p.clicks), itemStyle: { color: c.search }, barMaxWidth: 14 }],
    });
  });

  protected readonly auditChart = computed<ChartOptions>(() => {
    const h = this.data.value()?.audit?.history ?? [];
    return (c: ChartColors) => ({
      grid: { left: 24, right: 4, top: 6, bottom: 22 },
      xAxis: { type: 'category', data: h.map((a) => new Date(a.finished_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })),
        axisLine: { lineStyle: { color: c.grid } }, axisTick: { show: false }, axisLabel: { color: c.muted, hideOverlap: true } },
      yAxis: { type: 'value', minInterval: 1, splitLine: { lineStyle: { color: c.grid } }, axisLabel: { color: c.muted } },
      series: [
        { name: 'Errors', type: 'bar', data: h.map((a) => a.errors), itemStyle: { color: c.error }, barMaxWidth: 12 },
        { name: 'Warnings', type: 'bar', data: h.map((a) => a.warnings), itemStyle: { color: c.warning }, barMaxWidth: 12 },
      ],
    });
  });

  protected readonly auditHistoryLabel = computed(() => {
    const h = this.data.value()?.audit?.history ?? [];
    return 'Errors and warnings in the last audits: ' + h.map((a) => `${a.errors} errors, ${a.warnings} warnings`).join('; then ');
  });

  protected share(value: number, max: number): number {
    return max ? Math.max(2, (value / max) * 100) : 0;
  }
  protected pct(value: number, previous: number | null): string {
    return previous === null ? '—' : changeText(value, previous).replace(/ vs .*/, '');
  }
  protected tone(value: number, previous: number | null): string {
    return changeTone(value, previous);
  }
  protected path(url: string): string {
    try { const u = new URL(url); return u.pathname + u.search || '/'; } catch { return url; }
  }
}
