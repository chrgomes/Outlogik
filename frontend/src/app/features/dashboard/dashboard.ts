import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, ViewEncapsulation, computed, inject, signal } from '@angular/core';

import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { WorkspaceService } from '../../core/workspace.service';
import { PageHeader } from '../../shared/page-header/page-header';
import { LoadingState } from '../../shared/states/states';
import { describe, timeAgo } from './activity';
import { AgencyOverview } from './agency-overview';
import { Compare, DashboardSummary } from './dashboard.types';
import { PeriodChoice, WorkspaceDashboardView } from './workspace-dashboard';

const MAX_DAYS = 486;

/**
 * The dashboard. A business (or an agency with one workspace selected) sees that workspace's
 * dashboard; an agency with "All workspaces" sees every client side by side.
 */
@Component({
  selector: 'ol-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  // dashboard.scss styles the child views too (dash-… classes), so it isn't encapsulated.
  encapsulation: ViewEncapsulation.None,
  imports: [DatePipe, PageHeader, LoadingState, AgencyOverview, WorkspaceDashboardView],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
  protected readonly org = inject(CurrentOrgService);
  protected readonly ws = inject(WorkspaceService);
  private readonly auth = inject(AuthService);
  private readonly api = inject(OrgApi);
  protected readonly describe = describe;
  protected readonly timeAgo = timeAgo;

  /** Recent activity (people who can see the audit log). */
  protected readonly summary = httpResource<DashboardSummary>(() => this.api.url('dashboard'));

  protected readonly overview = computed(() => this.org.isAgency() && !this.ws.current());
  protected readonly ready = computed(() => this.ws.list.hasValue() || this.ws.list.error());

  // Period controls
  protected readonly choice = signal<'7' | '28' | '90' | 'custom'>('28');
  protected readonly compare = signal<Compare>('previous');
  protected readonly start = signal('');
  protected readonly end = signal('');
  protected readonly applied = signal<{ start: string; end: string } | null>(null);
  protected readonly rangeError = signal('');
  protected readonly today = new Date().toISOString().slice(0, 10);

  protected readonly period = computed<PeriodChoice>(() => {
    const custom = this.choice() === 'custom' ? this.applied() : null;
    return { days: custom ? null : Number(this.choice() === 'custom' ? 28 : this.choice()),
      start: custom?.start ?? null, end: custom?.end ?? null, compare: this.compare() };
  });
  protected readonly overviewDays = computed(() => (this.choice() === 'custom' ? 28 : Number(this.choice())));

  protected readonly greeting = computed(() => {
    const hour = new Date().getHours();
    const part = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    const first = this.auth.user()?.full_name.split(/\s+/)[0];
    return first ? `${part}, ${first}` : part;
  });
  protected readonly subtitle = computed(() => this.overview()
    ? `${this.org.membership()?.organization_name ?? ''} · all ${this.org.isAgency() ? 'clients' : 'workspaces'}`
    : this.ws.current()?.name ?? '');

  protected applyRange(): void {
    const s = this.start(), e = this.end();
    if (!s || !e) return this.rangeError.set('Choose a start and an end date.');
    if (s > e) return this.rangeError.set('The start date is after the end date.');
    if ((Date.parse(e) - Date.parse(s)) / 86_400_000 + 1 > MAX_DAYS) {
      return this.rangeError.set('Choose a period of 16 months or less.');
    }
    this.rangeError.set('');
    this.applied.set({ start: s, end: e });
  }
}
