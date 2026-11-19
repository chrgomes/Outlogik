import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Url = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=2048)]
WebsiteStatus = Literal["active", "paused", "archived"]
AuditFrequency = Literal["off", "weekly", "monthly"]


class WebsiteCreateIn(BaseModel):
    # Organization-level endpoint only: the client whose workspace gets the site. Leave it out
    # for the organization's own workspace. Ignored by the workspace endpoint.
    client_id: uuid.UUID | None = None
    url: Url
    # Defaults to the domain when omitted.
    name: Name | None = None
    status: WebsiteStatus = "active"


class WebsiteUpdateIn(BaseModel):
    # Move the site to another workspace (or, the older way, to a client's workspace)
    workspace_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    url: Url | None = None
    name: Name | None = None
    status: WebsiteStatus | None = None
    audit_frequency: AuditFrequency | None = None


class WebsiteOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    workspace_name: str
    # Null for websites in the organization's own workspace
    client_id: uuid.UUID | None
    client_name: str | None
    name: str
    url: str
    domain: str
    status: str
    audit_frequency: AuditFrequency = "off"
    created_at: datetime
    updated_at: datetime
