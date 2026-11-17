import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.auth.schemas import Email
from app.modules.leads.challenge import Solution

# Kept in step with the website (projects/marketing/src/app/config/forms.ts).
SERVICE_CHOICES = Literal[
    "seo", "social-media-management", "website-analytics-reporting", "content-marketing",
    "not-sure",
]
BUDGET_CHOICES = Literal["under-1k", "1k-2.5k", "2.5k-5k", "5k-plus", "not-sure"]
CONTACT_TOPICS = Literal["general", "existing-client", "partnerships", "press"]

Text = Annotated[str, StringConstraints(strip_whitespace=True)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=160)]


def _blank_to_none(value: str | None) -> str | None:
    return value or None


class Attribution(BaseModel):
    """Where the visitor came from, collected by the website without cookies (first page of the
    visit, its referrer and UTM tags) plus the page the form was on. Everything is optional."""

    model_config = ConfigDict(extra="ignore")

    page: Annotated[str, StringConstraints(max_length=300)] | None = None
    landing_page: Annotated[str, StringConstraints(max_length=500)] | None = None
    referrer: Annotated[str, StringConstraints(max_length=500)] | None = None
    utm_source: Annotated[str, StringConstraints(max_length=120)] | None = None
    utm_medium: Annotated[str, StringConstraints(max_length=120)] | None = None
    utm_campaign: Annotated[str, StringConstraints(max_length=120)] | None = None
    utm_term: Annotated[str, StringConstraints(max_length=120)] | None = None
    utm_content: Annotated[str, StringConstraints(max_length=120)] | None = None


class SpamChecks(BaseModel):
    """Invisible checks sent with every form: a honeypot field people never see (so leave
    empty), how long the form was open before it was sent, and the browser's proof of work."""

    nickname: Annotated[str, StringConstraints(max_length=200)] = ""
    elapsed_ms: int = Field(default=0, ge=0)
    pow: Solution | None = None


class ConsultationIn(SpamChecks):
    model_config = ConfigDict(extra="forbid")

    name: Name
    email: Email
    company: Short | None = None
    website: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)] | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    services: list[SERVICE_CHOICES] = Field(min_length=1, max_length=5)
    budget: BUDGET_CHOICES | None = None
    message: Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)] | None = None
    preferred_contact: Short | None = None
    attribution: Attribution = Attribution()


class ContactIn(SpamChecks):
    model_config = ConfigDict(extra="forbid")

    name: Name
    email: Email
    company: Short | None = None
    topic: CONTACT_TOPICS = "general"
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]
    attribution: Attribution = Attribution()


class NewsletterIn(SpamChecks):
    model_config = ConfigDict(extra="forbid")

    email: Email
    consent: Literal[True]
    attribution: Attribution = Attribution()


class TokenIn(BaseModel):
    token: Annotated[str, StringConstraints(min_length=10, max_length=200)]


class Received(BaseModel):
    received: bool = True


# --- admin ------------------------------------------------------------------------------------

LeadStatus = Literal["new", "contacted", "qualified", "closed", "spam"]
LeadKind = Literal["consultation", "contact"]


class LeadListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: LeadKind
    status: LeadStatus
    name: str
    email: str
    company: str | None
    services: list[str] = []
    utm_source: str | None = None
    note_count: int = 0
    created_at: datetime


class LeadNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    body: str
    author_name: str | None
    source: Literal["staff", "website"] = "staff"
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: LeadKind
    status: LeadStatus
    name: str
    email: str
    company: str | None
    website: str | None
    phone: str | None
    message: str | None
    details: dict
    attribution: dict
    spam_reason: str | None
    # Why it was marked as spam, in words (app.modules.leads.spam.REASONS)
    spam_reason_text: str | None = None
    created_at: datetime
    updated_at: datetime
    notes: list[LeadNoteOut]


class LeadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: LeadStatus


class LeadNoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=5000)]


class LeadCounts(BaseModel):
    """Leads per status, for the inbox's filters (spam is counted separately)."""

    new: int = 0
    contacted: int = 0
    qualified: int = 0
    closed: int = 0
    spam: int = 0


SubscriberStatus = Literal["pending", "confirmed", "unsubscribed"]


class SubscriberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    status: SubscriberStatus
    consent_at: datetime
    confirmed_at: datetime | None
    unsubscribed_at: datetime | None
    source_page: str | None = None


class LeadSource(BaseModel):
    """Leads from one source: a campaign (utm_source), a referring site, or "Direct"."""

    source: str
    consultations: int = 0
    messages: int = 0
    newsletter: int = 0
