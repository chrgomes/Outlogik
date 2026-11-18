import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

Severity = Literal["error", "warning", "notice"]
Area = Literal["seo", "technical", "ai_search"]


class AuditStartIn(BaseModel):
    website_id: uuid.UUID


class AuditOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    website_id: uuid.UUID
    website_name: str
    url: str
    status: Literal["queued", "running", "completed", "failed"]
    trigger: Literal["manual", "scheduled"]
    page_limit: int
    pages_crawled: int
    hit_page_limit: bool
    errors: int
    warnings: int
    notices: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class AuditDetailOut(AuditOut):
    facts: dict[str, Any]
    previous_audit_id: uuid.UUID | None
    # Compared with the previous completed audit of the same website
    new_issues: int | None
    fixed_issues: int | None


class IssueRef(BaseModel):
    url: str | None
    details: dict[str, Any]
    is_new: bool


class IssueGroupOut(BaseModel):
    check: str
    title: str
    severity: Severity
    area: Area
    why: str
    fix: str
    count: int
    new: int
    items: list[IssueRef]  # up to 200 per check


class FixedOut(BaseModel):
    check: str
    title: str
    url: str | None


class AuditPageOut(BaseModel):
    url: str
    final_url: str
    status_code: int | None
    redirects: int
    elapsed_ms: int
    depth: int
    title: str | None
    word_count: int | None
    error: str | None


class WebsiteAuditsOut(BaseModel):
    website_id: uuid.UUID
    website_name: str
    url: str
    workspace_id: uuid.UUID
    workspace_name: str
    audit_frequency: Literal["off", "weekly", "monthly"]
    latest: AuditOut | None
