from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.auth.schemas import Email

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
    empty), and how long the form was open before it was sent."""

    nickname: Annotated[str, StringConstraints(max_length=200)] = ""
    elapsed_ms: int = Field(default=0, ge=0)


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
