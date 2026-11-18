import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.modules.auth.schemas import Email

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    kind: Literal["business", "agency"]
    created_at: datetime


class OrganizationDetailOut(OrganizationOut):
    your_role: str
    your_permissions: list[str]


class OrganizationUpdateIn(BaseModel):
    name: Name | None = None


class RoleRef(BaseModel):
    id: uuid.UUID
    name: str
    system_key: str | None


class MemberOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: RoleRef
    status: str
    joined_at: datetime
    is_you: bool


class MemberUpdateIn(BaseModel):
    role_id: uuid.UUID | None = None
    status: Literal["active", "disabled"] | None = None


class InvitationCreateIn(BaseModel):
    email: Email
    role_id: uuid.UUID
    # Required when inviting with the Client role; the invitee sees only this client.
    client_id: uuid.UUID | None = None


class InvitationOut(BaseModel):
    id: uuid.UUID
    email: str
    role: RoleRef
    client_id: uuid.UUID | None
    client_name: str | None
    invited_by: str | None
    status: Literal["pending", "expired"]
    expires_at: datetime
    created_at: datetime
