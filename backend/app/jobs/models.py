import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey

JOB_STATUSES = ("queued", "running", "succeeded", "dead")


class Job(UUIDPrimaryKey, Timestamps, Base):
    """One piece of background work, and what happened to it.

    queued → running → succeeded, or back to queued for a retry, or dead once it has used all
    its attempts (kept for a person to look at and retry).
    """

    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint("status IN ('queued', 'running', 'succeeded', 'dead')",
                        name="status_valid"),
        # The same work can't be waiting or running twice.
        Index("uq_jobs_active_dedupe_key", "dedupe_key", unique=True,
              postgresql_where=text("status IN ('queued', 'running')")),
        Index("ix_jobs_status_run_after", "status", "run_after"),
    )

    kind: Mapped[str] = mapped_column(String(100))
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", server_default="queued")
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    dedupe_key: Mapped[str | None] = mapped_column(String(200))
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    run_after: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                server_default=text("now()"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
