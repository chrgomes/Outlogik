import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]


class Overview(BaseModel):
    users: dict[str, int]  # total, active, suspended, unverified, new_30_days
    organizations: dict[str, int]  # business, agency, suspended, new_30_days
    subscriptions: dict[str, int]  # trialing, trial_ended, active, past_due, cancelled
    clients_active: int
    websites_active: int
    signup_codes_active: int
    jobs: dict[str, int | None]  # queued, running, failed_24h, dead_24h, oldest_queued_minutes


class OrgRow(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    kind: Literal["business", "agency"]
    status: str
    plan: str | None
    subscription_status: str | None
    trial_ends_at: datetime | None
    members: int
    clients: int
    websites: int
    created_at: datetime


class MemberRow(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    role: str
    status: str
    user_active: bool


class LimitRow(BaseModel):
    key: str
    label: str
    limit: int | None
    used: int | None


class AdminAction(BaseModel):
    action: str
    actor: str | None
    meta: dict
    created_at: datetime


class OrgDetail(OrgRow):
    suspended_reason: str | None
    signup_code: str | None
    billing_interval: str | None
    limits: list[LimitRow]
    members_list: list[MemberRow]
    history: list[AdminAction]


class UserRow(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    active: bool
    verified: bool
    staff_role: str | None
    super_admin: bool
    organizations: int
    last_login_at: datetime | None
    created_at: datetime


class MembershipRow(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    organization_status: str
    role: str
    status: str


class UserDetail(UserRow):
    suspended_reason: str | None
    memberships: list[MembershipRow]
    history: list[AdminAction]


class PlanIn(BaseModel):
    plan: Annotated[str, Field(min_length=1, max_length=60)]
    status: Literal["trialing", "active", "past_due", "cancelled"] = "active"
    interval: Literal["monthly", "annual"] = "monthly"
    trial_days: int | None = Field(default=None, ge=1, le=90)


class SuspendIn(BaseModel):
    reason: Reason


class SignupCodeIn(BaseModel):
    label: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=200)]
    account_type: Literal["business", "agency"] | None = None
    max_uses: int | None = Field(default=None, ge=1, le=10000)
    expires_in_days: int | None = Field(default=None, ge=1, le=365)


class SignupCodeOut(BaseModel):
    id: uuid.UUID
    label: str
    hint: str
    account_type: Literal["business", "agency"] | None
    max_uses: int | None
    uses: int
    expires_at: datetime | None
    revoked_at: datetime | None
    status: Literal["active", "used_up", "expired", "revoked"]
    created_at: datetime
    created_by: str | None


class SignupCodeCreated(SignupCodeOut):
    code: str  # shown once


class PlanOption(BaseModel):
    key: str
    name: str
    account_kind: str
