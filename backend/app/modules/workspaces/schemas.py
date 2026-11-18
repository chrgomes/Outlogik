import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

WorkspaceKind = Literal["own", "client"]


class WorkspaceOut(BaseModel):
    id: uuid.UUID
    kind: WorkspaceKind
    name: str
    # Set for client workspaces only
    client_id: uuid.UUID | None
    client_status: str | None
    website_count: int
    created_at: datetime


class WorkspaceRef(BaseModel):
    id: uuid.UUID
    kind: WorkspaceKind
    name: str


class MemberWorkspacesIn(BaseModel):
    # The complete list of workspaces this member should see (replaces the current list).
    workspace_ids: Annotated[list[uuid.UUID], Field(max_length=1000)]
