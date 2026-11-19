import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel


class ClientCounts(BaseModel):
    total: int
    active: int
    archived: int


class WebsiteCounts(BaseModel):
    total: int
    active: int
    paused: int
    archived: int


class TeamCounts(BaseModel):
    members: int            # active team members (not client-portal users)
    client_users: int       # active client-portal users
    pending_invitations: int | None  # null without members.invite


class ActivityItem(BaseModel):
    id: uuid.UUID
    action: str
    actor_name: str | None
    target_type: str | None
    target_id: str | None
    meta: dict[str, Any]
    created_at: datetime


class DashboardOut(BaseModel):
    clients: ClientCounts
    websites: WebsiteCounts
    # Null when the caller's role can't see the team (members.read) or audit log (audit.read).
    team: TeamCounts | None
    recent_activity: list[ActivityItem] | None


# --- H1-8 dashboards ------------------------------------------------------------------------

class MetricOut(BaseModel):
    value: float
    previous: float | None


class PeriodOut(BaseModel):
    start: date
    end: date
    days: int
    compare: Literal["previous", "year", "none"] = "previous"
    compare_start: date | None
    compare_end: date | None


class SetupOut(BaseModel):
    websites: int
    audited: bool
    google: Literal["connected", "error", "not_connected"]
    ga4: bool
    search_console: bool
    analytics_visible: bool
    audits_visible: bool


class SourceTotalsOut(BaseModel):
    through: date
    metrics: dict[str, MetricOut]


class SeriesPoint(BaseModel):
    day: date
    sessions: int | None = None
    previous_sessions: int | None = None
    clicks: int | None = None
    impressions: int | None = None


class ShareOut(BaseModel):
    name: str
    sessions: int
    previous: int | None


class PageOut(BaseModel):
    path: str
    sessions: int
    previous: int | None
    key_events: float


class QueryPageOut(BaseModel):
    query: str
    page: str
    clicks: int
    impressions: int
    position: float


class LowCtrOut(BaseModel):
    page: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class QueryOut(BaseModel):
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class AuditPointOut(BaseModel):
    finished_at: datetime
    errors: int
    warnings: int


class FixFirstOut(BaseModel):
    check: str
    title: str
    severity: str
    count: int


class AuditSummaryOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    website_name: str
    finished_at: datetime
    pages_crawled: int
    errors: int
    warnings: int
    notices: int
    new_issues: int | None
    fixed_issues: int | None
    history: list[AuditPointOut]
    fix_first: list[FixFirstOut]


class WorkspaceDashboardOut(BaseModel):
    workspace_id: uuid.UUID
    workspace_name: str
    period: PeriodOut
    setup: SetupOut
    changes: list[str]
    ga4: SourceTotalsOut | None
    search_console: SourceTotalsOut | None
    series: list[SeriesPoint]
    channels: list[ShareOut]
    ai_referrals: list[ShareOut]
    top_pages: list[PageOut]
    pages_from: date | None
    search_snapshot_end: date | None
    almost_ranking: list[QueryPageOut]
    low_ctr_pages: list[LowCtrOut]
    site_ctr: float | None
    top_queries: list[QueryOut]
    audit: AuditSummaryOut | None


class ReviewOut(BaseModel):
    reviewed_at: datetime
    reviewed_by: str | None


class OverviewAuditOut(BaseModel):
    errors: int
    warnings: int


class OverviewRowOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: Literal["own", "client"]
    linked: bool
    organization_name: str | None
    website: str | None
    google: Literal["connected", "error", "not_connected"]
    has_analytics: bool
    has_search_console: bool
    visits: int | None
    visits_previous: int | None
    spark: list[int]
    ai_visits: int | None
    search_clicks: int | None
    audit: OverviewAuditOut | None
    assigned_to_me: bool
    managers: list[str] | None  # None: the caller can't see the team
    review: ReviewOut | None


class AttentionOut(BaseModel):
    workspace_id: uuid.UUID
    name: str
    kind: Literal["reconnect", "visits_drop", "audit_errors", "not_connected"]
    text: str


class WeekOut(BaseModel):
    week_start: date
    sessions: int
    ai_visits: int


class OverviewTotalsOut(BaseModel):
    workspaces: int
    clients: int
    websites: int
    visits: int | None
    visits_previous: int | None
    ai_visits: int | None
    ai_visits_previous: int | None
    with_audit_errors: int | None
    google_not_connected: int | None


class OverviewPeriodOut(BaseModel):
    start: date
    end: date
    days: int
    compare_start: date
    compare_end: date


class OverviewOut(BaseModel):
    period: OverviewPeriodOut
    totals: OverviewTotalsOut
    weekly: list[WeekOut]
    attention: list[AttentionOut]
    workspaces: list[OverviewRowOut]
