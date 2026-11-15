import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ClientCounts(BaseModel):
    total: int
    active: int
    archived: int


class WebsiteCounts(BaseModel):
    total: int
    active: int
    paused: int
    archived: int


class TeamCounts(BaseModel):
    members: int            # active team members (not client-portal users)
    client_users: int       # active client-portal users
    pending_invitations: int | None  # null without members.invite


class ActivityItem(BaseModel):
    id: uuid.UUID
    action: str
    actor_name: str | None
    target_type: str | None
    target_id: str | None
    meta: dict[str, Any]
    created_at: datetime


class DashboardOut(BaseModel):
    clients: ClientCounts
    websites: WebsiteCounts
    # Null when the caller's role can't see the team (members.read) or audit log (audit.read).
    team: TeamCounts | None
    recent_activity: list[ActivityItem] | None
