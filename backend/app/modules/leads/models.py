import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, Timestamps, UUIDPrimaryKey, utcnow

LEAD_KINDS = ("consultation", "contact")
LEAD_STATUSES = ("new", "contacted", "qualified", "closed", "spam")
SUBSCRIBER_STATUSES = ("pending", "confirmed", "unsubscribed")


class Lead(UUIDPrimaryKey, Timestamps, Base):
    """A consultation request or contact message from the public website.

    `details` holds the form-specific answers (services, budget, topic, preferred contact time);
    `attribution` holds where the visitor came from (UTM tags, referrer, landing page, the page
    the form was on). Spam caught by the honeypot or timing checks is kept with status "spam"
    so staff can review false positives; it never triggers notifications.
    """

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint("kind IN ('consultation', 'contact')", name="kind_valid"),
        CheckConstraint(
            "status IN ('new', 'contacted', 'qualified', 'closed', 'spam')", name="status_valid"
        ),
        Index("ix_leads_status_created_at", "status", "created_at"),
    )

    kind: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="new")
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(320), index=True)
    company: Mapped[str | None] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(300))
    phone: Mapped[str | None] = mapped_column(String(40))
    message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    attribution: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    spam_reason: Mapped[str | None] = mapped_column(String(40))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))


class NewsletterSubscriber(UUIDPrimaryKey, Timestamps, Base):
    """A newsletter subscriber, with the consent record CASL requires: the exact wording shown,
    when consent was given and confirmed (double opt-in), and when they unsubscribed."""

    __tablename__ = "newsletter_subscribers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'unsubscribed')", name="status_valid"
        ),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    consent_text: Mapped[str] = mapped_column(Text)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Hashes only; the tokens themselves exist only in the emails.
    confirm_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    confirm_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unsubscribe_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    attribution: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    ip: Mapped[str | None] = mapped_column(String(64))



class LeadNote(UUIDPrimaryKey, Base):
    """A note on a lead: a staff note (calls made, what was agreed) or one the website adds.
    Deleted with the lead."""

    __tablename__ = "lead_notes"
    __table_args__ = (CheckConstraint("source IN ('staff', 'website')", name="source_valid"),)

    lead_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    author_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    body: Mapped[str] = mapped_column(Text)
    # "staff" for notes written in the admin area; "website" for notes the system adds (for
    # example when the same person sends the same form again).
    source: Mapped[str] = mapped_column(String(20), default="staff", server_default="staff")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=utcnow
    )
