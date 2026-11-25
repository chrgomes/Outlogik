/** Shapes returned by the Outlogik API (mirrors backend schemas). */

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_super_admin: boolean;
  /** Outlogik staff role for the website admin area (super admins report 'site_admin'). */
  platform_role: 'content_editor' | 'site_admin' | 'platform_admin' | 'support_admin' | 'billing_admin' | null;
  /** What Outlogik staff may do in the platform (Super Admin) area. */
  platform_caps: string[];
  email_verified_at: string | null;
  created_at: string;
}

/** business: markets itself (one workspace, no clients). agency: also works for clients. */
export type AccountType = 'business' | 'agency';

/** A role sees every workspace, or only the ones each member is assigned to. */
export type WorkspaceScope = 'all' | 'assigned';

export interface Membership {
  organization_id: string;
  organization_slug: string;
  organization_name: string;
  organization_status: string;
  organization_kind: AccountType;
  /** 'assigned': this member sees only the workspaces they're assigned to. */
  workspace_scope: WorkspaceScope;
  role_id: string;
  role_name: string;
  /** Built-in role key ('owner', 'admin', 'member', 'client'), or null for custom roles. */
  role_key: string | null;
  permissions: string[];
}

export interface Me {
  user: User;
  memberships: Membership[];
}

export interface ApiError {
  error: { code: string; message: string; details: unknown };
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface InvitePreview {
  email: string;
  organization_name: string;
  organization_slug: string;
  role_name: string;
  client_name: string | null;
  invited_by: string | null;
  account_exists: boolean;
  expires_at: string;
}

export interface Client {
  id: string;
  name: string;
  contact_email: string | null;
  status: 'active' | 'archived';
  notes: string | null;
  website_count: number;
  portal_user_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface ClientUser {
  user_id: string;
  member_id: string;
  email: string;
  full_name: string;
  linked_at: string;
}

/**
 * Where marketing data lives: the organization's own workspace, or one per agency client.
 */
export interface Workspace {
  id: string;
  kind: 'own' | 'client';
  name: string;
  client_id: string | null;
  client_status: 'active' | 'archived' | null;
  website_count: number;
  created_at: string;
  /** Another organization's workspace, shared with this one through an access grant. */
  linked: boolean;
  organization_name: string | null;
  access: 'manage' | 'view' | null;
}

export interface WorkspaceRef {
  id: string;
  kind: 'own' | 'client';
  name: string;
}

/** A business's grant of access to an agency. */
export interface AccessGrant {
  id: string;
  email: string;
  access: 'manage' | 'view';
  status: 'pending' | 'expired' | 'active' | 'revoked';
  agency_name: string | null;
  invited_by: string | null;
  accepted_by: string | null;
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
}

export interface GrantPreview {
  business_name: string;
  workspace_name: string;
  access: 'manage' | 'view';
  email: string;
  invited_by: string | null;
  expires_at: string;
  agencies: { organization_id: string; slug: string; name: string }[];
}

export interface Subscription {
  plan: {
    key: string;
    name: string;
    account_kind: AccountType;
    currency: string;
    monthly_price_cents: number;
    annual_price_cents: number;
  };
  status: 'trialing' | 'active' | 'past_due' | 'cancelled' | 'trial_ended';
  billing_interval: 'monthly' | 'annual';
  trial_ends_at: string | null;
  current_period_end: string | null;
  /** limit null: unlimited. used null: a cap per use (pages per audit), not counted. */
  limits: { key: string; label: string; limit: number | null; used: number | null }[];
}

export interface Website {
  id: string;
  workspace_id: string;
  workspace_name: string;
  /** Null for websites in the organization's own workspace. */
  client_id: string | null;
  client_name: string | null;
  name: string;
  url: string;
  domain: string;
  status: 'active' | 'paused' | 'archived';
  audit_frequency: AuditFrequency;
  created_at: string;
  updated_at: string;
}

export type AuditFrequency = 'off' | 'weekly' | 'monthly';
export type Severity = 'error' | 'warning' | 'notice';
export type IssueArea = 'seo' | 'technical' | 'ai_search';

export interface Audit {
  id: string;
  workspace_id: string;
  website_id: string;
  website_name: string;
  url: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  trigger: 'manual' | 'scheduled';
  page_limit: number;
  pages_crawled: number;
  hit_page_limit: boolean;
  errors: number;
  warnings: number;
  notices: number;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface AuditDetail extends Audit {
  facts: AuditFacts;
  previous_audit_id: string | null;
  new_issues: number | null;
  fixed_issues: number | null;
}

export interface AuditFacts {
  https?: boolean;
  robots_txt?: number | null;
  sitemap?: boolean;
  sitemap_urls?: number;
  skipped_by_robots?: number;
  ai_search_crawlers?: Record<string, boolean>;
  ai_training_crawlers?: Record<string, boolean>;
  structured_data_types?: string[];
  pagespeed?: { connected: boolean; error?: string; score?: number | null; lcp_ms?: number | null;
    cls?: number | null; tbt_ms?: number | null };
}

export interface IssueGroup {
  check: string;
  title: string;
  severity: Severity;
  area: IssueArea;
  why: string;
  fix: string;
  count: number;
  new: number;
  items: { url: string | null; details: Record<string, unknown>; is_new: boolean }[];
}

export interface WebsiteAudits {
  website_id: string;
  website_name: string;
  url: string;
  workspace_id: string;
  workspace_name: string;
  audit_frequency: AuditFrequency;
  latest: Audit | null;
}

export interface RoleRef {
  id: string;
  name: string;
  system_key: string | null;
  workspace_scope: WorkspaceScope;
}

export interface Member {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: RoleRef;
  status: 'active' | 'disabled';
  joined_at: string;
  is_you: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: RoleRef;
  client_id: string | null;
  client_name: string | null;
  invited_by: string | null;
  status: 'pending' | 'expired';
  expires_at: string;
  created_at: string;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
  system_key: string | null;
  workspace_scope: WorkspaceScope;
  permissions: string[];
  member_count: number;
  created_at: string;
}

export interface PermissionInfo {
  code: string;
  description: string;
  group: string;
}

export interface OrganizationDetail {
  id: string;
  name: string;
  slug: string;
  status: string;
  kind: AccountType;
  created_at: string;
  your_role: string;
  your_permissions: string[];
}

// Integrations (H1-7)
export type SourceKind = 'ga4' | 'search_console';

export interface DataSource {
  id: string;
  kind: SourceKind;
  external_id: string;
  name: string;
  sync_status: 'pending' | 'ok' | 'failed';
  last_synced_at: string | null;
  synced_through: string | null;
  last_error: string | null;
}

export interface GoogleIntegration {
  configured: boolean;
  connected: boolean;
  status: 'connected' | 'error' | null;
  account_email: string | null;
  connected_at: string | null;
  last_error: string | null;
  sources: DataSource[];
}

export interface GoogleAvailable {
  ga4: { id: string; name: string; account: string }[];
  search_console: { site_url: string; permission: string }[];
}

export interface Metric {
  value: number;
  previous: number | null;
}

export interface Share {
  name: string;
  sessions: number;
  previous: number;
}

export interface AnalyticsSummary {
  days: number;
  start: string | null;
  end: string | null;
  ga4: Record<'sessions' | 'users' | 'new_users' | 'engaged_sessions' | 'page_views' | 'key_events', Metric> | null;
  search_console: Record<'clicks' | 'impressions' | 'ctr' | 'position', Metric> | null;
  series: { day: string; sessions: number | null; users: number | null; clicks: number | null; impressions: number | null }[];
  channels: Share[];
  ai_referrals: Share[];
  top_queries: { query: string; clicks: number; impressions: number; ctr: number; position: number }[];
  top_queries_through: string | null;
}

// Reports (H1-9)
export type ReportSection = 'traffic' | 'ai' | 'search' | 'audit';

export interface Report {
  id: string;
  workspace_id: string;
  workspace_name: string;
  title: string;
  sections: ReportSection[];
  period_start: string;
  period_end: string;
  compare: 'previous' | 'year' | 'none';
  compare_start: string | null;
  compare_end: string | null;
  sources: { name: string; detail: string; through: string | null }[];
  unavailable: string[];
  csv_files: { name: string; label: string }[];
  created_at: string;
  created_by: string | null;
}

export interface ReportRequest {
  title: string | null;
  sections: ReportSection[];
  days: number | null;
  start: string | null;
  end: string | null;
  compare: 'previous' | 'year' | 'none';
}
