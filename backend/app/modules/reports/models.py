import uuid
from datetime import date
from typing import Any

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class Report(UUIDPrimaryKey, Timestamps, Base):
    """A saved report: the numbers as they were when it was made, with its period, sources and
    anything that wasn't available (spec §10). PDFs and CSVs are drawn from `data`, so a report
    sent to a client last month still says exactly what it said then.

    Belongs to the organization that made it (an agency's report on a business's shared
    workspace is the agency's)."""

    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("compare IN ('previous', 'year', 'none')", name="compare_valid"),
        Index("ix_reports_org_created", "organization_id", "created_at"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"))
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(200))
    sections: Mapped[list[str]] = mapped_column(JSONB)  # traffic, ai, search, audit
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    compare: Mapped[str] = mapped_column(String(10))
    # Everything the PDF and CSVs show: sources, unavailable metrics, figures, tables
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
