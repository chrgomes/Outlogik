import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, utcnow

MODULE_STATUSES = ("available", "in_development", "hidden")


class SiteSettings(Base):
    """Marketing website settings. A single row (id = 1); `data` is validated by
    `site.schemas.SiteSettingsData` on every write."""

    __tablename__ = "site_settings"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow, onupdate=utcnow
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )


class ProductModule(Timestamps, Base):
    """A product capability shown on the marketing site, with its honest status (spec §20)."""

    __tablename__ = "product_modules"
    __table_args__ = (
        CheckConstraint("status IN ('available', 'in_development', 'hidden')",
                        name="status_valid"),
    )

    slug: Mapped[str] = mapped_column(String(60), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    summary: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="in_development")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
