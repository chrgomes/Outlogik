from datetime import datetime
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, StringConstraints

from app.modules.auth.schemas import Email

Text = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
SocialNetwork = Literal["linkedin", "x", "facebook", "instagram", "youtube", "tiktok", "github"]
ModuleStatus = Literal["available", "in_development", "hidden"]


class SocialLink(BaseModel):
    network: SocialNetwork
    url: AnyHttpUrl


class SiteSettingsData(BaseModel):
    """Everything an admin can change about the marketing site without a release.
    Empty values mean "not shown" (e.g. no contact email until one is set)."""

    model_config = ConfigDict(extra="forbid")

    company_description: Text = (
        "Outlogik brings client management, SEO, analytics and reporting together in one "
        "workspace for agencies and marketing teams."
    )
    tagline: Text = "Digital Marketing. Smarter. Together."
    contact_email: Email | None = None
    sales_email: Email | None = None
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=40)] | None = None
    address: Text | None = None
    social_links: Annotated[list[SocialLink], Field(max_length=10)] = []
    # Calls to action used across the site
    primary_cta_label: Label = "Get started"
    demo_cta_label: Label = "Book a demo"
    # Shown on the site while the product is in early access (decision 1 of the plan)
    early_access: bool = True
    # SEO defaults (pages override these)
    seo_title_suffix: Annotated[str, StringConstraints(max_length=60)] = " · Outlogik"
    seo_default_description: Annotated[str, StringConstraints(max_length=200)] = (
        "Outlogik brings client management, SEO, analytics and reporting together in one "
        "workspace for agencies and marketing teams."
    )


class ProductModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    summary: str
    status: ModuleStatus
    sort_order: int


ModuleName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
ModuleSummary = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class ProductModuleUpdate(BaseModel):
    name: ModuleName | None = None
    summary: ModuleSummary | None = None
    status: ModuleStatus | None = None
    sort_order: Annotated[int, Field(ge=0, le=10_000)] | None = None


class PublicSiteOut(BaseModel):
    """What the marketing site needs on every page."""

    settings: SiteSettingsData
    modules: list[ProductModuleOut]


class AdminSettingsOut(BaseModel):
    data: SiteSettingsData
    updated_at: datetime
