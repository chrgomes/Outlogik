import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

RoleName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


class PermissionOut(BaseModel):
    code: str
    description: str
    group: str


class RoleOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    system_key: str | None
    permissions: list[str]
    member_count: int
    created_at: datetime


class RoleCreateIn(BaseModel):
    name: RoleName
    description: Description | None = None
    permissions: Annotated[list[str], Field(max_length=100)]


class RoleUpdateIn(BaseModel):
    name: RoleName | None = None
    description: Description | None = None
    # Replaces the role's whole permission set when given.
    permissions: Annotated[list[str], Field(max_length=100)] | None = None
