import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.modules.auth.schemas import Email

Access = Literal["manage", "view"]


class GrantCreateIn(BaseModel):
    # Someone at the agency. Only the account with this email can accept.
    email: Email
    access: Access = "manage"


class GrantOut(BaseModel):
    id: uuid.UUID
    email: str
    access: Access
    status: Literal["pending", "expired", "active", "revoked"]
    agency_name: str | None
    invited_by: str | None
    accepted_by: str | None
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None


class AgencyChoice(BaseModel):
    organization_id: uuid.UUID
    slug: str
    name: str


class GrantPreviewOut(BaseModel):
    business_name: str
    workspace_name: str
    access: Access
    email: str
    invited_by: str | None
    expires_at: datetime
    # The agencies the signed-in user can accept it into (owner or admin, or a role with
    # "linked_accounts.manage").
    agencies: list[AgencyChoice]


class GrantTokenIn(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=200)]


class GrantAcceptIn(GrantTokenIn):
    organization_id: uuid.UUID
