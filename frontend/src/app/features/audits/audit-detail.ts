import { DatePipe, DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuditDetail, IssueArea, IssueGroup } from '../../core/api.types';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { AREA_LABEL, SeverityBadge, describeDetails } from './audit-parts';

interface AuditPage {
  url: string; final_url: string; status_code: number | null; redirects: number;
  elapsed_ms: number; depth: number; title: string | null; word_count: number | null;
  error: string | null;
}

/** One audit: summary, what changed since the last one, AI search readiness, issues, pages. */
@Component({
  selector: 'ol-audit-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, DecimalPipe, RouterLink, ErrorState, LoadingState, SeverityBadge],
  template: `
    <a [routerLink]="['/o', org.slug(), 'audits']" class="back-link">← All audits</a>

    @if (audit.error()) {
      <ol-error-state message="We couldn't load this audit." (retry)="audit.reload()" />
    } @else if (audit.value(); as a) {
      <header class="mb-4">
        <h1 class="h3 mb-1">{{ a.website_name }}</h1>
        <p class="text-muted mb-0">
          {{ a.url }} · {{ (a.finished_at ?? a.created_at) | date: 'medium' }}
          · {{ a.trigger === 'scheduled' ? 'Scheduled audit' : 'Run by hand' }}
        </p>
      </header>

      @if (a.status !== 'completed') {
        <div class="alert" [class.alert-danger]="a.status === 'failed'" [class.alert-secondary]="a.status !== 'failed'" role="status">
          {{ a.status === 'failed' ? (a.error ?? "The audit didn't finish.") : 'This audit is still running. Results appear here when it finishes.' }}
        </div>
      } @else {
        <section class="summary mb-4" aria-label="Summary">
          <div class="stat"><span class="num">{{ a.pages_crawled }}</span>{{ ' ' }}<span>{{ a.pages_crawled === 1 ? 'page checked' : 'pages checked' }}</span>
            @if (a.hit_page_limit) {<small class="text-muted">Your plan's limit of {{ a.page_limit }} pages per audit was reached.</small>}</div>
          <div class="stat"><span class="num text-danger-emphasis">{{ a.errors }}</span>{{ ' ' }}<span>{{ a.errors === 1 ? 'error' : 'errors' }}</span></div>
          <div class="stat"><span class="num">{{ a.warnings }}</span>{{ ' ' }}<span>{{ a.warnings === 1 ? 'warning' : 'warnings' }}</span></div>
          <div class="stat"><span class="num">{{ a.notices }}</span>{{ ' ' }}<span>{{ a.notices === 1 ? 'notice' : 'notices' }}</span></div>
          @if (a.new_issues !== null) {
            <div class="stat"><span class="num">{{ a.new_issues }} new · {{ a.fixed_issues }} fixed</span>{{ ' ' }}<span>since the last audit</span></div>
          }
        </section>

        <section class="card-box mb-4" aria-labelledby="ai-title">
          <h2 id="ai-title" class="h6 mb-3">AI search readiness</h2>
          <div class="facts">
            <div>
              <h3 class="fact-title">AI search crawlers</h3>
              @for (c of crawlers(a.facts.ai_search_crawlers); track c.name) {
                <div class="d-flex justify-content-between gap-3"><span>{{ c.name }}</span>{{ ' ' }}
                  <span [class.text-danger]="!c.allowed">{{ c.allowed ? 'Allowed' : 'Blocked' }}</span></div>
              } @empty { <p class="text-muted mb-0">Not checked.</p> }
              <p class="small text-muted mt-2 mb-0">These read websites for AI answers and search results.</p>
            </div>
            <div>
              <h3 class="fact-title">AI training crawlers</h3>
              @for (c of crawlers(a.facts.ai_training_crawlers); track c.name) {
                <div class="d-flex justify-content-between gap-3"><span>{{ c.name }}</span>{{ ' ' }}
                  <span>{{ c.allowed ? 'Allowed' : 'Blocked' }}</span></div>
              } @empty { <p class="text-muted mb-0">Not checked.</p> }
              <p class="small text-muted mt-2 mb-0">Blocking these is your choice; it doesn't affect AI search.</p>
            </div>
            <div>
              <h3 class="fact-title">Structured data on the home page</h3>
              @if (a.facts.structured_data_types?.length) {
                <p class="mb-0">{{ a.facts.structured_data_types!.join(', ') }}</p>
              } @else { <p class="mb-0">None found.</p> }
              <h3 class="fact-title mt-3">Sitemap and robots.txt</h3>
              <p class="mb-0">Sitemap: {{ a.facts.sitemap ? 'found (' + a.facts.sitemap_urls + ' addresses)' : 'not found' }}<br>
                robots.txt: {{ a.facts.robots_txt === 200 ? 'found' : 'not found' }}</p>
            </div>
            <div>
              <h3 class="fact-title">Page speed (mobile, home page)</h3>
              @if (a.facts.pagespeed; as ps) {
                @if (!ps.connected) {
                  <p class="mb-0 text-muted">Not connected yet. Outlogik adds this once Google PageSpeed is set up.</p>
                } @else if (ps.error) {
                  <p class="mb-0 text-muted">{{ ps.error }}</p>
                } @else {
                  <p class="mb-0"><strong>{{ ps.score }}</strong> out of 100<br>
                    <span class="small text-muted">Largest content shown after {{ (ps.lcp_ms ?? 0) / 1000 | number: '1.1-1' }} s ·
                      layout shift {{ ps.cls }} · blocking {{ ps.tbt_ms | number: '1.0-0' }} ms</span></p>
                }
              } @else { <p class="mb-0 text-muted">Not checked.</p> }
            </div>
          </div>
        </section>

        <section aria-labelledby="issues-title" class="mb-4">
          <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
            <h2 id="issues-title" class="h5 mb-0">Issues</h2>
            <div class="btn-group btn-group-sm" role="group" aria-label="Show issues for">
              @for (f of filters; track f.value) {
                <button type="button" class="btn" [class.btn-dark]="area() === f.value"
                  [class.btn-outline-secondary]="area() !== f.value" [attr.aria-pressed]="area() === f.value"
                  (click)="area.set(f.value)">{{ f.label }}</button>
              }
            </div>
          </div>
          @if (issues.hasValue()) {
            @for (g of shownIssues(); track g.check) {
              <details class="issue">
                <summary>
                  <ol-severity [value]="g.severity" />
                  <span class="fw-medium flex-grow-1">{{ g.title }}</span>
                  @if (g.new) {<span class="small text-muted">{{ g.new }} new</span>}
                  <span class="tabular-nums">{{ g.count }}</span>
                </summary>
                <div class="issue-body">
                  <p class="mb-1"><strong>Why it matters.</strong> {{ g.why }}</p>
                  <p class="mb-2"><strong>How to fix it.</strong> {{ g.fix }}</p>
                  <ul class="list-unstyled mb-0">
                    @for (i of g.items; track $index) {
                      <li>
                        @if (i.url) {<a [href]="i.url" target="_blank" rel="noopener noreferrer">{{ i.url }}</a>}
                        @else {<span>The whole site</span>}
                        @if (i.is_new) {<span class="badge rounded-pill new">New</span>}
                        @if (describe(i.details); as d) {<span class="d-block small text-muted">{{ d }}</span>}
                      </li>
                    }
                  </ul>
                  @if (g.count > g.items.length) {<p class="small text-muted mt-2 mb-0">Showing {{ g.items.length }} of {{ g.count }}.</p>}
                </div>
              </details>
            } @empty {
              <p class="text-muted">No issues found here.</p>
            }
          } @else {
            <ol-loading-state label="Loading issues…" />
          }
        </section>

        @if ((fixed.value() ?? []).length) {
          <section class="mb-4" aria-labelledby="fixed-title">
            <h2 id="fixed-title" class="h5">Fixed since the last audit</h2>
            <ul class="mb-0">
              @for (f of fixed.value()!; track $index) {
                <li>{{ f.title }}@if (f.url) {: <span class="text-muted">{{ f.url }}</span>}</li>
              }
            </ul>
          </section>
        }

        <section aria-labelledby="pages-title">
          <h2 id="pages-title" class="h5">Pages checked</h2>
          @if (pages.hasValue()) {
            <div class="ol-table-card">
              <table class="table ol-table">
                <thead><tr><th>Page</th><th>Status</th><th class="text-end">Response</th><th class="text-end">Words</th></tr></thead>
                <tbody>
                  @for (p of pages.value().slice(0, pageCount()); track p.url) {
                    <tr>
                      <td><span class="d-block">{{ p.title || '(no title)' }}</span>
                        <span class="small text-muted">{{ p.url }}</span></td>
                      <td>{{ p.status_code ?? p.error }}</td>
                      <td class="text-end tabular-nums">{{ p.elapsed_ms | number }} ms</td>
                      <td class="text-end tabular-nums">{{ p.word_count ?? '–' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            @if (pages.value().length > pageCount()) {
              <button type="button" class="btn btn-link px-0" (click)="pageCount.set(pageCount() + 100)">Show more pages</button>
            }
          }
        </section>
      }
    } @else {
      <ol-loading-state label="Loading audit…" />
    }
  `,
  styles: `
    .back-link { display: inline-block; margin-bottom: 1rem; color: var(--ol-text-muted); text-decoration: none; }
    .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr)); gap: 0.75rem; }
    .stat, .card-box { border: 1px solid var(--ol-border); border-radius: var(--bs-border-radius-lg);
      background: var(--ol-surface-raised); padding: 1rem 1.25rem; }
    .stat { display: flex; flex-direction: column; gap: 0.125rem; }
    .stat .num { font-size: 1.5rem; font-weight: 600; }
    .facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr)); gap: 1.5rem; }
    .fact-title { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
      color: var(--ol-text-muted); margin-bottom: 0.5rem; }
    .issue { border: 1px solid var(--ol-border); border-radius: var(--bs-border-radius);
      background: var(--ol-surface-raised); margin-bottom: 0.5rem; }
    .issue summary { display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1rem; cursor: pointer; }
    .issue-body { padding: 0 1rem 1rem; }
    .issue-body li { padding: 0.375rem 0; border-top: 1px solid var(--ol-border); overflow-wrap: anywhere; }
    .new { margin-left: 0.5rem; background: var(--ol-surface-active); color: var(--ol-text); font-weight: 500; }
  `,
})
export class AuditDetailPage {
  protected readonly org = inject(CurrentOrgService);
  private readonly api = inject(OrgApi);
  readonly workspaceId = input.required<string>();
  readonly auditId = input.required<string>();

  private readonly base = computed(() => `workspaces/${this.workspaceId()}/audits/${this.auditId()}`);
  protected readonly audit = httpResource<AuditDetail>(() => this.api.url(this.base()));
  protected readonly issues = httpResource<IssueGroup[]>(() =>
    this.audit.value()?.status === 'completed' ? this.api.url(`${this.base()}/issues`) : undefined);
  protected readonly fixed = httpResource<{ check: string; title: string; url: string | null }[]>(() =>
    this.audit.value()?.previous_audit_id ? this.api.url(`${this.base()}/fixed`) : undefined);
  protected readonly pages = httpResource<AuditPage[]>(() =>
    this.audit.value()?.status === 'completed' ? this.api.url(`${this.base()}/pages`) : undefined);

  protected readonly filters: { value: IssueArea | 'all'; label: string }[] = [
    { value: 'all', label: 'All' }, { value: 'technical', label: AREA_LABEL['technical'] },
    { value: 'seo', label: AREA_LABEL['seo'] }, { value: 'ai_search', label: AREA_LABEL['ai_search'] },
  ];
  protected readonly area = signal<IssueArea | 'all'>('all');
  protected readonly shownIssues = computed(() => (this.issues.value() ?? [])
    .filter((g) => this.area() === 'all' || g.area === this.area()));
  protected readonly pageCount = signal(100);
  protected readonly describe = describeDetails;

  protected crawlers(map: Record<string, boolean> | undefined) {
    return Object.entries(map ?? {}).map(([name, allowed]) => ({ name, allowed }));
  }
}
