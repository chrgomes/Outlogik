export interface ActivityItem {
  id: string;
  action: string;
  actor_name: string | null;
  target_type: string | null;
  target_id: string | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface DashboardSummary {
  clients: { total: number; active: number; archived: number };
  websites: { total: number; active: number; paused: number; archived: number };
  team: { members: number; client_users: number; pending_invitations: number | null } | null;
  recent_activity: ActivityItem[] | null;
}

// H1-8 dashboards
export interface Metric { value: number; previous: number | null; }
export interface Share { name: string; sessions: number; previous: number | null; }
export type Compare = 'previous' | 'year' | 'none';

export interface WorkspaceDashboard {
  workspace_id: string;
  workspace_name: string;
  period: { start: string; end: string; days: number; compare: Compare; compare_start: string | null; compare_end: string | null };
  setup: {
    websites: number; audited: boolean; google: 'connected' | 'error' | 'not_connected';
    ga4: boolean; search_console: boolean; analytics_visible: boolean; audits_visible: boolean;
  };
  changes: string[];
  ga4: { through: string; metrics: Record<'sessions' | 'users' | 'new_users' | 'engaged_sessions' | 'page_views' | 'key_events', Metric> } | null;
  search_console: { through: string; metrics: Record<'clicks' | 'impressions' | 'ctr' | 'position', Metric> } | null;
  series: { day: string; sessions: number | null; previous_sessions: number | null; clicks: number | null; impressions: number | null }[];
  channels: Share[];
  ai_referrals: Share[];
  top_pages: { path: string; sessions: number; previous: number | null; key_events: number }[];
  pages_from: string | null;
  search_snapshot_end: string | null;
  almost_ranking: { query: string; page: string; clicks: number; impressions: number; position: number }[];
  low_ctr_pages: { page: string; clicks: number; impressions: number; ctr: number; position: number }[];
  site_ctr: number | null;
  top_queries: { query: string; clicks: number; impressions: number; ctr: number; position: number }[];
  audit: {
    id: string; workspace_id: string; website_name: string; finished_at: string; pages_crawled: number;
    errors: number; warnings: number; notices: number; new_issues: number | null; fixed_issues: number | null;
    history: { finished_at: string; errors: number; warnings: number }[];
    fix_first: { check: string; title: string; severity: string; count: number }[];
  } | null;
}

export interface OverviewRow {
  id: string; name: string; kind: 'own' | 'client'; linked: boolean; organization_name: string | null;
  website: string | null; google: 'connected' | 'error' | 'not_connected';
  has_analytics: boolean; has_search_console: boolean;
  visits: number | null; visits_previous: number | null; spark: number[];
  ai_visits: number | null; search_clicks: number | null;
  audit: { errors: number; warnings: number } | null;
  assigned_to_me: boolean;
  managers: string[] | null;
  review: { reviewed_at: string; reviewed_by: string | null } | null;
}

export interface Overview {
  period: { start: string; end: string; days: number; compare_start: string; compare_end: string };
  totals: {
    workspaces: number; clients: number; websites: number;
    visits: number | null; visits_previous: number | null;
    ai_visits: number | null; ai_visits_previous: number | null;
    with_audit_errors: number | null; google_not_connected: number | null;
  };
  weekly: { week_start: string; sessions: number; ai_visits: number }[];
  attention: { workspace_id: string; name: string; kind: 'reconnect' | 'visits_drop' | 'audit_errors' | 'not_connected'; text: string }[];
  workspaces: OverviewRow[];
}

/** "+12% vs before", or why there's no comparison. */
export function changeText(value: number, previous: number | null, against = 'before'): string {
  if (previous === null) return 'No earlier data to compare';
  if (previous === 0) return value === 0 ? 'No change' : 'New this period';
  const pct = Math.round(((value - previous) / previous) * 100);
  return pct === 0 ? 'No change' : `${pct > 0 ? '+' : '−'}${Math.abs(pct)}% vs ${against}`;
}

/** Bootstrap text class for a change; `lowerIsBetter` for things like audit errors. */
export function changeTone(value: number, previous: number | null, lowerIsBetter = false): string {
  // Grey when there's nothing to compare, or the change rounds to 0%.
  if (previous === null || previous === value || (previous && Math.round(((value - previous) / previous) * 100) === 0)) return 'text-muted';
  return (value > previous) !== lowerIsBetter ? 'text-success' : 'text-danger';
}

/** Who a client-portal user can contact about their workspace. */
export interface Contacts {
  organization_name: string;
  contacts: { name: string; email: string; role: 'account_manager' | 'owner' }[];
}
