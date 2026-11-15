import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints

from app.modules.auth.schemas import Email

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=10_000)]
ClientStatus = Literal["active", "archived"]


class ClientCreateIn(BaseModel):
    name: Name
    contact_email: Email | None = None
    notes: Notes | None = None
    status: ClientStatus = "active"


class ClientUpdateIn(BaseModel):
    name: Name | None = None
    contact_email: Email | None = None
    notes: Notes | None = None
    status: ClientStatus | None = None


class ClientOut(BaseModel):
    id: uuid.UUID
    name: str
    contact_email: str | None
    status: str
    # Internal agency notes; always null for client-portal users.
    notes: str | None
    website_count: int
    portal_user_count: int | None  # null for client-portal users
    created_at: datetime
    updated_at: datetime


class ClientUserOut(BaseModel):
    user_id: uuid.UUID
    member_id: uuid.UUID
    email: str
    full_name: str
    linked_at: datetime


class ClientUserLinkIn(BaseModel):
    member_id: uuid.UUID
