import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class Integration(UUIDPrimaryKey, Timestamps, Base):
    """A workspace's connection to an outside account (Google, for now)."""

    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider"),
        CheckConstraint("provider IN ('google')", name="provider_valid"),
        CheckConstraint("status IN ('connected', 'error')", name="status_valid"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="connected")
    # Which outside account is connected (shown to the user)
    account_email: Mapped[str | None] = mapped_column(String(320))
    scopes: Mapped[str] = mapped_column(Text, default="")
    # Encrypted (integrations/crypto.py); never returned by the API
    refresh_token_encrypted: Mapped[str] = mapped_column(Text)
    connected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    last_error: Mapped[str | None] = mapped_column(String(500))


class DataSource(UUIDPrimaryKey, Timestamps, Base):
    """One thing synced from an integration: a GA4 property or a Search Console site."""

    __tablename__ = "data_sources"
    __table_args__ = (
        UniqueConstraint("integration_id", "kind"),
        CheckConstraint("kind IN ('ga4', 'search_console')", name="kind_valid"),
        CheckConstraint("sync_status IN ('pending', 'ok', 'failed')", name="sync_status_valid"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    integration_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("integrations.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    external_id: Mapped[str] = mapped_column(String(500))  # properties/123 or a site URL
    name: Mapped[str] = mapped_column(String(300))
    sync_status: Mapped[str] = mapped_column(String(20), default="pending")
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_through: Mapped[date | None] = mapped_column(Date)  # the latest day with data
    # The first day synced: comparisons are only made with periods from this day on.
    # (Google leaves out days with no visits, so counting rows can't tell.)
    history_from: Mapped[date | None] = mapped_column(Date)
    pages_from: Mapped[date | None] = mapped_column(Date)  # GA4 visits by landing page
    last_error: Mapped[str | None] = mapped_column(String(500))


class Ga4Daily(UUIDPrimaryKey, Base):
    __tablename__ = "ga4_daily"
    __table_args__ = (UniqueConstraint("source_id", "day"),)

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_sources.id", ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    users: Mapped[int] = mapped_column(Integer, default=0)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    engaged_sessions: Mapped[int] = mapped_column(Integer, default=0)
    page_views: Mapped[int] = mapped_column(Integer, default=0)
    key_events: Mapped[float] = mapped_column(Float, default=0)


class Ga4Breakdown(UUIDPrimaryKey, Base):
    """Sessions per day by channel, or by AI tool that referred the visit."""

    __tablename__ = "ga4_breakdowns"
    __table_args__ = (
        UniqueConstraint("source_id", "day", "dimension", "value"),
        CheckConstraint("dimension IN ('channel', 'ai_source')", name="dimension_valid"),
    )

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_sources.id", ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    dimension: Mapped[str] = mapped_column(String(20))
    value: Mapped[str] = mapped_column(String(200))
    sessions: Mapped[int] = mapped_column(Integer, default=0)


class GscDaily(UUIDPrimaryKey, Base):
    __tablename__ = "gsc_daily"
    __table_args__ = (UniqueConstraint("source_id", "day"),)

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_sources.id", ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[float] = mapped_column(Float, default=0)  # average, as Google reports it


class GscQuery(UUIDPrimaryKey, Base):
    """Top search queries over the 28 days up to `period_end` (replaced at each sync)."""

    __tablename__ = "gsc_queries"

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    period_end: Mapped[date] = mapped_column(Date)
    query: Mapped[str] = mapped_column(String(500))
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[float] = mapped_column(Float, default=0)


class Ga4Page(UUIDPrimaryKey, Base):
    """Sessions per day by the page they started on (GA4's landing page)."""

    __tablename__ = "ga4_pages"
    __table_args__ = (UniqueConstraint("source_id", "day", "path"),)

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_sources.id", ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    path: Mapped[str] = mapped_column(String(1000))
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    key_events: Mapped[float] = mapped_column(Float, default=0)


class GscPage(UUIDPrimaryKey, Base):
    """Search results by page over the 28 days up to `period_end` (replaced at each sync)."""

    __tablename__ = "gsc_pages"

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    period_end: Mapped[date] = mapped_column(Date)
    page: Mapped[str] = mapped_column(String(2048))
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[float] = mapped_column(Float, default=0)


class GscQueryPage(UUIDPrimaryKey, Base):
    """Searches and the page Google showed for them, over the 28 days up to `period_end`
    (replaced at each sync). Used for "searches you almost rank for"."""

    __tablename__ = "gsc_query_pages"

    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("data_sources.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    period_end: Mapped[date] = mapped_column(Date)
    query: Mapped[str] = mapped_column(String(500))
    page: Mapped[str] = mapped_column(String(2048))
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[float] = mapped_column(Float, default=0)
