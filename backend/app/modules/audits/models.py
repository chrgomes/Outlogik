import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class Audit(UUIDPrimaryKey, Timestamps, Base):
    """One run of the website audit."""

    __tablename__ = "audits"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'completed', 'failed')",
                        name="status_valid"),
        CheckConstraint("trigger IN ('manual', 'scheduled')", name="trigger_valid"),
        Index("ix_audits_website_created", "website_id", "created_at"),
    )

    # The organization that owns the website (a business's, when an agency runs it)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    website_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("websites.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default="queued")
    trigger: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    url: Mapped[str] = mapped_column(String(2048))
    page_limit: Mapped[int] = mapped_column(Integer)
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    errors: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    warnings: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    notices: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    hit_page_limit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # Site-level findings: robots.txt, sitemap, AI crawlers, structured data, page speed…
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditPage(UUIDPrimaryKey, Base):
    __tablename__ = "audit_pages"

    audit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("audits.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(String(2048))
    final_url: Mapped[str] = mapped_column(String(2048))
    status_code: Mapped[int | None] = mapped_column(Integer)
    redirects: Mapped[int] = mapped_column(Integer, default=0)
    elapsed_ms: Mapped[int] = mapped_column(Integer, default=0)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str | None] = mapped_column(String(500))
    word_count: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String(300))


class AuditIssue(UUIDPrimaryKey, Base):
    __tablename__ = "audit_issues"
    __table_args__ = (
        CheckConstraint("severity IN ('error', 'warning', 'notice')", name="severity_valid"),
        Index("ix_audit_issues_audit_check", "audit_id", "check_key"),
    )

    audit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("audits.id", ondelete="CASCADE"))
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    # One of audits/checks.py CHECKS
    check_key: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(10))
    area: Mapped[str] = mapped_column(String(20))
    url: Mapped[str | None] = mapped_column(String(2048))  # None: the whole site
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class UsageRecord(UUIDPrimaryKey, Timestamps, Base):
    """Metered use per organization and month (for example, audits run), for monthly limits."""

    __tablename__ = "usage_records"
    __table_args__ = (UniqueConstraint("organization_id", "metric", "period"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(60))
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM, UTC
    count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
