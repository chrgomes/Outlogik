import { DatePipe, DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { CurrentOrgService } from '../../core/current-org.service';
import { OrgApi } from '../../core/org-api.service';
import { Icon } from '../../shared/icon/icon';
import { IconName } from '../../shared/icon/icons';
import { PageHeader } from '../../shared/page-header/page-header';
import { ErrorState, LoadingState } from '../../shared/states/states';
import { describe, timeAgo } from './activity';
import { DashboardSummary } from './dashboard.types';

interface Tile { label: string; value: number; detail: string; link: string; }
interface Upcoming { title: string; text: string; icon: IconName; }

/** Integrations planned for Phase 2. Shown as "Not connected yet", never with numbers. */
const PHASE_2: Upcoming[] = [
  { title: 'Search performance', icon: 'search',
    text: 'Clicks, impressions and positions from Google Search Console and Bing.' },
  { title: 'Website traffic', icon: 'graph-up',
    text: 'Visitors and top pages from privacy-friendly analytics.' },
  { title: 'Site health', icon: 'heart-pulse',
    text: 'Technical SEO and performance audits for each website.' },
  { title: 'Broken links', icon: 'link-45deg',
    text: 'Links that lead nowhere, found by regular checks.' },
];

@Component({
  selector: 'ol-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, DecimalPipe, RouterLink, PageHeader, ErrorState, LoadingState, Icon],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
  protected readonly org = inject(CurrentOrgService);
  private readonly auth = inject(AuthService);
  private readonly api = inject(OrgApi);
  protected readonly upcoming = PHASE_2;
  protected readonly describe = describe;
  protected readonly timeAgo = timeAgo;

  protected readonly summary = httpResource<DashboardSummary>(() => this.api.url('dashboard'));

  protected readonly greeting = computed(() => {
    const hour = new Date().getHours();
    const part = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    const first = this.auth.user()?.full_name.split(/\s+/)[0];
    return first ? `${part}, ${first}` : part;
  });

  protected readonly tiles = computed<Tile[]>(() => {
    const s = this.summary.value();
    if (!s) return [];
    const base = ['/o', this.org.slug()].join('/');
    const tiles: Tile[] = [
      { label: 'Active clients', value: s.clients.active, link: `${base}/clients`,
        detail: s.clients.archived ? `${s.clients.archived} archived` : 'None archived' },
      { label: 'Active websites', value: s.websites.active, link: `${base}/websites`,
        detail: [s.websites.paused && `${s.websites.paused} paused`,
          s.websites.archived && `${s.websites.archived} archived`].filter(Boolean).join(' · ') || 'None paused or archived' },
    ];
    if (s.team) {
      tiles.push({ label: 'Team members', value: s.team.members, link: `${base}/settings/members`,
        detail: s.team.client_users === 1 ? '1 client-portal user' : `${s.team.client_users} client-portal users` });
      if (s.team.pending_invitations !== null) {
        tiles.push({ label: 'Pending invitations', value: s.team.pending_invitations,
          link: `${base}/settings/members`, detail: 'Links expire after 7 days' });
      }
    }
    return tiles;
  });

  /** First-run checklist from real counts; hidden once done or for roles that can't act. */
  protected readonly checklist = computed(() => {
    const s = this.summary.value();
    if (!s || !this.org.can('clients.write')) return null;
    const items = [
      { label: 'Add your first client', done: s.clients.total > 0, link: 'clients' },
      { label: 'Add a client website', done: s.websites.total > 0, link: 'websites' },
      ...(s.team && this.org.can('members.invite') ? [{
        label: 'Invite your team', link: 'settings/members',
        done: s.team.members > 1 || (s.team.pending_invitations ?? 0) > 0 }] : []),
    ];
    return items.every((i) => i.done) ? null : items;
  });
}
