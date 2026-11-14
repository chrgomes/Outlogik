import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Email = Annotated[EmailStr, AfterValidator(lambda v: v.strip().lower())]
# 10+ characters; length is the main strength factor. Max bounds hashing cost.
Password = Annotated[str, Field(min_length=10, max_length=128)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class RegisterIn(BaseModel):
    email: Email
    password: Password
    full_name: Name
    organization_name: Name


class LoginIn(BaseModel):
    email: Email
    password: Annotated[str, Field(min_length=1, max_length=128)]


class ForgotPasswordIn(BaseModel):
    email: Email


class ResetPasswordIn(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=200)]
    password: Password


class TokenIn(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=200)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_super_admin: bool
    email_verified_at: datetime | None
    created_at: datetime


class MembershipOut(BaseModel):
    organization_id: uuid.UUID
    organization_slug: str
    organization_name: str
    organization_status: str
    role_id: uuid.UUID
    role_name: str
    # Stable key of a built-in role ("owner", "admin", "member", "client"); null for custom roles.
    role_key: str | None
    permissions: list[str]


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]


class MessageOut(BaseModel):
    message: str


class AcceptInviteIn(BaseModel):
    token: Annotated[str, Field(min_length=10, max_length=200)]
    # Only needed when the invited email has no account yet.
    full_name: Name | None = None
    password: Password | None = None


class InvitePreviewOut(BaseModel):
    email: str
    organization_name: str
    organization_slug: str
    role_name: str
    client_name: str | None
    invited_by: str | None
    account_exists: bool
    expires_at: datetime
