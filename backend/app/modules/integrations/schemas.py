import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field


class DataSourceOut(BaseModel):
    id: uuid.UUID
    kind: Literal["ga4", "search_console"]
    external_id: str
    name: str
    sync_status: Literal["pending", "ok", "failed"]
    last_synced_at: datetime | None
    synced_through: date | None
    last_error: str | None


class IntegrationOut(BaseModel):
    """A workspace's Google connection. The token itself is never returned."""

    configured: bool  # whether this Outlogik server has Google set up at all
    connected: bool
    status: Literal["connected", "error"] | None = None
    account_email: str | None = None
    connected_at: datetime | None = None
    last_error: str | None = None
    sources: list[DataSourceOut] = []


class ConnectOut(BaseModel):
    url: str


class Ga4PropertyOut(BaseModel):
    id: str
    name: str
    account: str


class SearchConsoleSiteOut(BaseModel):
    site_url: str
    permission: str


class AvailableOut(BaseModel):
    ga4: list[Ga4PropertyOut]
    search_console: list[SearchConsoleSiteOut]


class SourcesIn(BaseModel):
    ga4_property: str | None = Field(default=None, max_length=500)
    search_console_site: str | None = Field(default=None, max_length=500)


class Metric(BaseModel):
    value: float
    previous: float | None  # the same number of days just before; None without full data


class DayPoint(BaseModel):
    day: date
    sessions: int | None = None
    users: int | None = None
    clicks: int | None = None
    impressions: int | None = None


class Share(BaseModel):
    name: str
    sessions: int
    previous: int


class QueryOut(BaseModel):
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class SummaryOut(BaseModel):
    days: int
    start: date | None
    end: date | None
    ga4: dict[str, Metric] | None  # sessions, users, new_users, engaged_sessions, page_views, …
    search_console: dict[str, Metric] | None  # clicks, impressions, ctr, position
    series: list[DayPoint]
    channels: list[Share]
    ai_referrals: list[Share]
    top_queries: list[QueryOut]
    top_queries_through: date | None
