from datetime import datetime
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints

from app.modules.auth.schemas import Email

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
# Canadian provinces and territories, for the governing law in the terms (decision 12).
Province = Literal[
    "Alberta", "British Columbia", "Manitoba", "New Brunswick", "Newfoundland and Labrador",
    "Northwest Territories", "Nova Scotia", "Nunavut", "Ontario", "Prince Edward Island",
    "Quebec", "Saskatchewan", "Yukon",
]
SocialNetwork = Literal["linkedin", "x", "facebook", "instagram", "youtube", "tiktok", "github"]
FeatureStatus = Literal["available", "in_development", "hidden"]


class SocialLink(BaseModel):
    network: SocialNetwork
    url: AnyHttpUrl


class SiteSettingsData(BaseModel):
    """Everything an admin can change about the marketing site without a release.
    Empty values mean "not shown" (e.g. no contact email until one is set)."""

    model_config = ConfigDict(extra="forbid")

    company_description: Text = (
        "Outlogik is a digital marketing agency for SEO, social media, content and analytics, "
        "with a client portal that shows you exactly what we're doing."
    )
    tagline: Text = "Digital Marketing. Smarter. Together."
    contact_email: Email | None = None
    sales_email: Email | None = "sales@outlogik.com"
    # For billing questions (the payment and subscription policy)
    billing_email: Email | None = "billings@outlogik.com"
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    address: Text | None = "Toronto, Ontario, Canada"
    social_links: Annotated[list[SocialLink], Field(max_length=10)] = []
    # The main call to action used across the site
    consultation_cta_label: Label = "Book a free consultation"
    # SEO defaults (pages override these)
    seo_title_suffix: Annotated[str, StringConstraints(max_length=60)] = " · Outlogik"
    seo_default_description: Annotated[str, StringConstraints(max_length=200)] = (
        "Outlogik is a digital marketing agency: SEO, social media management, content "
        "marketing and analytics, with clear reporting in your own client portal."
    )

    # Legal details (decision 12, provided 2026-11-16). The privacy policy and terms are published
    # on the website only while these and the address are all set; otherwise those pages answer 404.
    legal_name: Annotated[str, StringConstraints(
        strip_whitespace=True, min_length=1, max_length=160)] | None = "Outlogik"
    province: Province | None = "Ontario"
    privacy_email: Email | None = "privacy@outlogik.com"

    # Analytics (all optional, off by default). Loaded on the website only for visitors who accept
    # analytics cookies; with none set, the site uses no tracking cookies and shows no banner.
    ga4_measurement_id: Annotated[str, StringConstraints(
        strip_whitespace=True, pattern=r"^G-[A-Z0-9]{4,16}$")] | None = None
    gtm_container_id: Annotated[str, StringConstraints(
        strip_whitespace=True, pattern=r"^GTM-[A-Z0-9]{4,12}$")] | None = None
    clarity_project_id: Annotated[str, StringConstraints(
        strip_whitespace=True, pattern=r"^[a-z0-9]{6,16}$")] | None = None

    @classmethod
    def from_stored(cls, data: dict) -> "SiteSettingsData":
        """Read stored settings, ignoring keys from older versions (new writes are strict)."""
        return cls.model_validate({k: v for k, v in (data or {}).items() if k in cls.model_fields})


class PortalFeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    summary: str
    status: FeatureStatus
    sort_order: int


FeatureName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
FeatureSummary = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class PortalFeatureUpdate(BaseModel):
    name: FeatureName | None = None
    summary: FeatureSummary | None = None
    status: FeatureStatus | None = None
    sort_order: Annotated[int, Field(ge=0, le=10_000)] | None = None


class PublicSiteOut(BaseModel):
    """What the website (and the app's sign-in page) needs."""

    settings: SiteSettingsData
    portal_features: list[PortalFeatureOut]
    # False when the app is invite-only: the sign-in page then doesn't offer "Create an account".
    signup_open: bool


class AdminSettingsOut(BaseModel):
    data: SiteSettingsData
    updated_at: datetime
