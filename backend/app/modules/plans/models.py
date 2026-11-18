import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey


class Plan(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "plans"
    __table_args__ = (
        CheckConstraint("account_kind IN ('business', 'agency')", name="account_kind_valid"),
    )

    key: Mapped[str] = mapped_column(String(60), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    account_kind: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3), default="CAD", server_default="CAD")
    # In cents. The annual price is the whole year, paid upfront.
    monthly_price_cents: Mapped[int] = mapped_column(Integer)
    annual_price_cents: Mapped[int] = mapped_column(Integer)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class PlanEntitlement(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "plan_entitlements"
    __table_args__ = (UniqueConstraint("plan_id", "key"),)

    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("plans.id", ondelete="CASCADE"), index=True
    )
    # One of plans/catalogue.py ENTITLEMENTS
    key: Mapped[str] = mapped_column(String(100))
    # For limits: a number, or null for unlimited
    value: Mapped[Any] = mapped_column(JSONB, nullable=True)


class Subscription(UUIDPrimaryKey, Timestamps, Base):
    """An organization's plan. One per organization; changes are in the activity log."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint("status IN ('trialing', 'active', 'past_due', 'cancelled')",
                        name="status_valid"),
        CheckConstraint("billing_interval IN ('monthly', 'annual')", name="interval_valid"),
        CheckConstraint("status <> 'trialing' OR trial_ends_at IS NOT NULL",
                        name="trial_has_end"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("organizations.id", ondelete="CASCADE"), unique=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("plans.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    billing_interval: Mapped[str] = mapped_column(String(10), default="monthly",
                                                  server_default="monthly")
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # manual: set by Outlogik staff. A payment provider comes in H3.
    source: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
