import { DatePipe, DecimalPipe, PercentPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { apiProblem } from '../../core/api-errors';
import { AnalyticsSummary, GoogleAvailable, GoogleIntegration, Metric, SourceKind } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { DialogService } from '../../shared/dialog/dialog';
import { PageHeader } from '../../shared/page-header/page-header';
import { EmptyState, ErrorState, LoadingState } from '../../shared/states/states';
import { ToastService } from '../../shared/toast/toast';

const SIGN_IN_ERRORS: Record<string, string> = {
  oauth_state_invalid: 'That Google sign-in expired or was started by someone else. Start again.',
  oauth_scopes_missing: 'Outlogik needs read access to both Analytics and Search Console. Connect again and leave both boxes ticked.',
  oauth_no_refresh_token: "Google didn't grant lasting access. Try connecting again.",
};

const KIND_LABEL: Record<SourceKind, string> = { ga4: 'Google Analytics', search_console: 'Search Console' };

/** A workspace's Google connection (Analytics and Search Console) and the last 28 days of results. */
@Component({
  selector: 'ol-integrations',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, DecimalPipe, PercentPipe, PageHeader, EmptyState, ErrorState, LoadingState],
  template: `
    <ol-page-header title="Integrations"
      description="Connect Google Analytics and Search Console to see traffic, visits from AI tools and search results." />

    @if (!workspaceId()) {
      <ol-empty-state icon="plug" title="Choose a workspace"
        message="Integrations belong to one workspace. Choose your own workspace or a client's in the top bar." />
    } @else if (google.error()) {
      <ol-error-state message="We couldn't load this workspace's integrations." (retry)="google.reload()" />
    } @else if (google.hasValue()) {
      @let g = google.value()!;
      <section class="card mb-4" aria-labelledby="google-heading">
        <div class="card-body">
          <div class="d-flex flex-wrap gap-3 align-items-start justify-content-between">
            <div>
              <h2 id="google-heading" class="h5 mb-1">Google Analytics and Search Console</h2>
              @if (!g.connected) {
                <p class="text-muted mb-0">Read-only access: Outlogik can see reports, never change your Google settings.</p>
              } @else {
                <p class="mb-0">
                  Connected as <span class="fw-medium">{{ g.account_email }}</span>
                  <span class="text-muted">{{ ' ' }}since {{ g.connected_at | date: 'mediumDate' }}</span>
                </p>
              }
            </div>
            @if (canManage()) {
              <div class="d-flex gap-2">
                @if (!g.connected) {
                  @if (g.configured) {
                    <button type="button" class="btn btn-primary" [disabled]="busy()" (click)="connect()">Connect Google</button>
                  }
                } @else {
                  @if (g.status === 'error') {
                    <button type="button" class="btn btn-primary" [disabled]="busy()" (click)="connect()">Reconnect Google</button>
                  } @else if (g.sources.length) {
                    <button type="button" class="btn btn-outline-secondary" [disabled]="busy() || syncing()" (click)="sync()">
                      {{ syncing() ? 'Syncing…' : 'Sync now' }}</button>
                  }
                  <button type="button" class="btn btn-outline-danger" [disabled]="busy()" (click)="disconnect()">Disconnect</button>
                }
              </div>
            }
          </div>

          @if (!g.configured && !g.connected) {
            <div class="alert alert-info mt-3 mb-0" role="status">
              Google isn't set up on this Outlogik server yet, so it can't be connected. Outlogik's team is working on it.
            </div>
          }
          @if (g.status === 'error' && g.last_error) {
            <div class="alert alert-warning mt-3 mb-0" role="alert">{{ g.last_error }}</div>
          }
          @if (readOnly() && !g.connected) {
            <p class="text-muted small mt-3 mb-0">This workspace is shared with view-only access, so you can't connect it.</p>
          }

          @if (g.connected) {
            @if (g.sources.length) {
              <ul class="list-unstyled mt-3 mb-0 sources">
                @for (s of g.sources; track s.id) {
                  <li>
                    <span class="fw-medium">{{ kindLabel[s.kind] }}:</span>{{ ' ' }}{{ s.name }}
                    <span class="small d-block" [class.text-danger]="s.sync_status === 'failed'" [class.text-muted]="s.sync_status !== 'failed'">
                      @switch (s.sync_status) {
                        @case ('pending') { Waiting for the first sync… }
                        @case ('failed') { Last sync failed{{ s.last_error ? ': ' + s.last_error : '' }} }
                        @default {
                          Synced {{ s.last_synced_at | date: 'medium' }}@if (s.synced_through) {, data through {{ s.synced_through | date: 'mediumDate' }}}
                        }
                      }
                    </span>
                  </li>
                }
              </ul>
            }
            @if (canManage() && g.status === 'connected') {
              @if (choosing() || !g.sources.length) {
                <form class="mt-3 border-top pt-3" (submit)="$event.preventDefault(); save()">
                  @if (available.error()) {
                    <div class="alert alert-warning" role="alert">{{ availableError() }}</div>
                  } @else if (available.hasValue()) {
                    @let a = available.value()!;
                    <div class="row g-3">
                      <div class="col-md-6">
                        <label class="form-label" for="ga4">Analytics property</label>
                        <select id="ga4" class="form-select" [value]="ga4()" (change)="ga4.set($any($event.target).value)">
                          <option value="">Don't sync Analytics</option>
                          @for (p of a.ga4; track p.id) { <option [value]="p.id">{{ p.name }} ({{ p.account }})</option> }
                        </select>
                        @if (!a.ga4.length) { <div class="form-text">This Google account can't see any Analytics properties.</div> }
                      </div>
                      <div class="col-md-6">
                        <label class="form-label" for="gsc">Search Console site</label>
                        <select id="gsc" class="form-select" [value]="gsc()" (change)="gsc.set($any($event.target).value)">
                          <option value="">Don't sync Search Console</option>
                          @for (s of a.search_console; track s.site_url) { <option [value]="s.site_url">{{ s.site_url }}</option> }
                        </select>
                        @if (!a.search_console.length) { <div class="form-text">This Google account has no verified Search Console sites.</div> }
                      </div>
                    </div>
                    <div class="mt-3 d-flex gap-2">
                      <button type="submit" class="btn btn-primary" [disabled]="busy()">Save and sync</button>
                      @if (g.sources.length) {
                        <button type="button" class="btn btn-link" (click)="choosing.set(false)">Cancel</button>
                      }
                    </div>
                    <p class="form-text mb-0">The first sync copies the last 16 months. After that, Outlogik syncs every night.</p>
                  } @else {
                    <ol-loading-state label="Loading your Google properties…" />
                  }
                </form>
              } @else {
                <button type="button" class="btn btn-link px-0 mt-2" (click)="choose()">Change what's synced</button>
              }
            }
          }
        </div>
      </section>

      @if (summary.hasValue() && (summary.value()!.ga4 || summary.value()!.search_console)) {
        @let s = summary.value()!;
        <h2 class="h5">Last {{ s.days }} days</h2>
        <p class="text-muted small">Compared with the {{ s.days }} days before. Only data synced from Google is shown.</p>
        <div class="kpis mb-4">
          @if (s.ga4; as a) {
            @for (k of ga4Kpis; track k.key) {
              <div class="card kpi"><div class="card-body">
                <div class="small text-muted">{{ k.label }}</div>
                <div class="h4 mb-0">{{ a[k.key].value | number: '1.0-0' }}</div>
                <div class="small" [class]="tone(a[k.key])">{{ change(a[k.key]) }}</div>
              </div></div>
            }
          }
          @if (s.search_console; as c) {
            <div class="card kpi"><div class="card-body">
              <div class="small text-muted">Search clicks</div>
              <div class="h4 mb-0">{{ c.clicks.value | number: '1.0-0' }}</div>
              <div class="small" [class]="tone(c.clicks)">{{ change(c.clicks) }}</div>
            </div></div>
            <div class="card kpi"><div class="card-body">
              <div class="small text-muted">Search impressions</div>
              <div class="h4 mb-0">{{ c.impressions.value | number: '1.0-0' }}</div>
              <div class="small" [class]="tone(c.impressions)">{{ change(c.impressions) }}</div>
            </div></div>
            <div class="card kpi"><div class="card-body">
              <div class="small text-muted">Average position</div>
              <div class="h4 mb-0">{{ c.position.value | number: '1.1-1' }}</div>
              <div class="small text-muted">Click rate {{ c.ctr.value | percent: '1.1-1' }}</div>
            </div></div>
          }
        </div>

        <div class="row g-4">
          @if (s.ga4) {
            <div class="col-lg-6">
              <section class="ol-table-card" aria-labelledby="ai-heading">
                <h3 id="ai-heading" class="h6 p-3 mb-0">Visits from AI tools</h3>
                @if (s.ai_referrals.length) {
                  <table class="table ol-table mb-0">
                    <thead><tr><th>Source</th><th class="text-end">Sessions</th><th class="text-end">Before</th></tr></thead>
                    <tbody>
                      @for (r of s.ai_referrals; track r.name) {
                        <tr><td>{{ r.name }}</td><td class="text-end">{{ r.sessions | number }}</td><td class="text-end text-muted">{{ r.previous | number }}</td></tr>
                      }
                    </tbody>
                  </table>
                } @else {
                  <p class="px-3 text-muted">No visits from ChatGPT, Perplexity, Gemini, Copilot or Claude in this period.</p>
                }
                <p class="small text-muted px-3 pb-3 mb-0">Visits where Google Analytics recorded an AI assistant as the referring site.
                  Some AI tools don't pass this on, so the real number can be higher.</p>
              </section>
            </div>
            <div class="col-lg-6">
              <section class="ol-table-card" aria-labelledby="channels-heading">
                <h3 id="channels-heading" class="h6 p-3 mb-0">Where visits came from</h3>
                <table class="table ol-table mb-0">
                  <thead><tr><th>Channel</th><th class="text-end">Sessions</th><th class="text-end">Before</th></tr></thead>
                  <tbody>
                    @for (r of s.channels; track r.name) {
                      <tr><td>{{ r.name }}</td><td class="text-end">{{ r.sessions | number }}</td><td class="text-end text-muted">{{ r.previous | number }}</td></tr>
                    }
                  </tbody>
                </table>
              </section>
            </div>
          }
          @if (s.top_queries.length) {
            <div class="col-12">
              <section class="ol-table-card" aria-labelledby="queries-heading">
                <h3 id="queries-heading" class="h6 p-3 mb-0">Top Google searches
                  <span class="small text-muted fw-normal">· 28 days to {{ s.top_queries_through | date: 'mediumDate' }}</span></h3>
                <table class="table ol-table mb-0">
                  <thead><tr><th>Search</th><th class="text-end">Clicks</th><th class="text-end">Impressions</th>
                    <th class="text-end">Click rate</th><th class="text-end">Position</th></tr></thead>
                  <tbody>
                    @for (q of s.top_queries; track q.query) {
                      <tr><td>{{ q.query }}</td><td class="text-end">{{ q.clicks | number }}</td>
                        <td class="text-end">{{ q.impressions | number }}</td><td class="text-end">{{ q.ctr | percent: '1.1-1' }}</td>
                        <td class="text-end">{{ q.position | number: '1.1-1' }}</td></tr>
                    }
                  </tbody>
                </table>
              </section>
            </div>
          }
        </div>
      }
    } @else {
      <ol-loading-state label="Loading integrations…" />
    }
  `,
  styles: `
    .kpis { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fill, minmax(8rem, 1fr)); }
    .sources li + li { margin-top: .5rem; }
  `,
})
export class IntegrationsPage {
  protected readonly org = inject(CurrentOrgService);
  private readonly ws = inject(WorkspaceService);
  private readonly api = inject(OrgApi);
  private readonly toast = inject(ToastService);
  private readonly dialog = inject(DialogService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  protected readonly kindLabel = KIND_LABEL;
  protected readonly ga4Kpis = [
    { key: 'sessions', label: 'Sessions' }, { key: 'users', label: 'Visitors' },
    { key: 'key_events', label: 'Key events' },
  ] as const;

  protected readonly workspaceId = computed(() => this.ws.current()?.id ?? null);
  protected readonly readOnly = this.ws.readOnly;
  protected readonly canManage = computed(() => this.org.can('integrations.manage') && !this.readOnly());
  private base(): string | undefined {
    const id = this.workspaceId();
    return id ? this.api.url(`workspaces/${id}`) : undefined;
  }

  protected readonly google = httpResource<GoogleIntegration>(() => {
    const b = this.base();
    return b ? `${b}/integrations/google` : undefined;
  });
  protected readonly summary = httpResource<AnalyticsSummary>(() => {
    const b = this.base();
    return b && this.org.can('analytics.read') && this.google.value()?.connected ? `${b}/analytics/summary` : undefined;
  });
  protected readonly choosing = signal(false);
  private readonly wantsChoices = computed(() => {
    const g = this.google.value();
    return !!g?.connected && g.status === 'connected' && this.canManage() && (this.choosing() || !g.sources.length);
  });
  protected readonly available = httpResource<GoogleAvailable>(() => {
    const b = this.base();
    return b && this.wantsChoices() ? `${b}/integrations/google/available` : undefined;
  });
  protected readonly availableError = computed(() =>
    this.available.error() ? apiProblem(this.available.error()).message : '');
  protected readonly ga4 = signal('');
  protected readonly gsc = signal('');
  protected readonly busy = signal(false);
  protected readonly syncing = computed(() => (this.google.value()?.sources ?? []).some((s) => s.sync_status === 'pending'));

  constructor() {
    this.handleReturnFromGoogle();
    // While a sync is waiting or running, check every few seconds.
    const timer = setInterval(() => {
      if (this.syncing()) { this.google.reload(); this.summary.reload(); }
    }, 4000);
    inject(DestroyRef).onDestroy(() => clearInterval(timer));
    // Preselect what's synced now when the choices open.
    effect(() => {
      const sources = this.google.value()?.sources ?? [];
      this.ga4.set(sources.find((s) => s.kind === 'ga4')?.external_id ?? '');
      this.gsc.set(sources.find((s) => s.kind === 'search_console')?.external_id ?? '');
    });
  }

  private handleReturnFromGoogle(): void {
    const q = this.route.snapshot.queryParamMap;
    const workspace = q.get('workspace');
    if (workspace) this.ws.select(workspace);
    if (q.get('google') === 'connected') this.toast.success('Google is connected. Now choose what to sync.');
    const error = q.get('google_error');
    if (error) this.toast.error(SIGN_IN_ERRORS[error] ?? 'Google couldn’t be connected. Try again.');
    if (workspace || q.get('google') || error) {
      void this.router.navigate([], { relativeTo: this.route, queryParams: {}, replaceUrl: true });
    }
  }

  protected change(m: Metric): string {
    if (m.previous === null) return 'No earlier data to compare';
    if (m.previous === 0) return m.value === 0 ? 'No change' : 'New this period';
    const pct = Math.round(((m.value - m.previous) / m.previous) * 100);
    return pct === 0 ? 'No change' : `${pct > 0 ? '+' : '−'}${Math.abs(pct)}% vs before`;
  }

  protected tone(m: Metric): string {
    if (m.previous === null || m.previous === m.value) return 'text-muted';
    return m.value > m.previous ? 'text-success' : 'text-danger';
  }

  protected choose(): void {
    this.choosing.set(true);
  }

  protected async connect(): Promise<void> {
    const id = this.workspaceId();
    if (!id) return;
    this.busy.set(true);
    try {
      const { url } = await this.api.connectGoogle(id);
      window.location.assign(url);
    } catch (err) {
      this.toast.error(apiProblem(err).message);
      this.busy.set(false);
    }
  }

  protected async save(): Promise<void> {
    const id = this.workspaceId();
    if (!id) return;
    this.busy.set(true);
    try {
      const result = await this.api.chooseGoogleSources(id, {
        ga4_property: this.ga4() || null, search_console_site: this.gsc() || null });
      this.google.set(result);
      this.choosing.set(false);
      this.summary.reload();
      this.toast.success(result.sources.length ? 'Saved. Syncing from Google…' : 'Saved. Nothing is synced now.');
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }

  protected async sync(): Promise<void> {
    const id = this.workspaceId();
    if (!id) return;
    this.busy.set(true);
    try {
      this.google.set(await this.api.syncGoogle(id));
      this.summary.reload();
      this.toast.success('Syncing from Google…');
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }

  protected async disconnect(): Promise<void> {
    const id = this.workspaceId();
    if (!id) return;
    const ok = await this.dialog.confirm({
      title: 'Disconnect Google?', danger: true, confirmLabel: 'Disconnect',
      message: 'Outlogik’s access is removed at Google, and the traffic and search history synced into this workspace is deleted. You can connect again later.',
    });
    if (!ok) return;
    this.busy.set(true);
    try {
      await this.api.disconnectGoogle(id);
      this.google.reload();
      this.toast.success('Google is disconnected.');
    } catch (err) {
      this.toast.error(apiProblem(err).message);
    } finally {
      this.busy.set(false);
    }
  }
}
