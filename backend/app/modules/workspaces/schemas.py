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
    # Set for another organization's workspace, shared through an access grant.
    linked: bool = False
    organization_name: str | None = None
    access: Literal["manage", "view"] | None = None


class WorkspaceRef(BaseModel):
    id: uuid.UUID
    kind: WorkspaceKind
    name: str


class MemberWorkspacesIn(BaseModel):
    # The complete list of workspaces this member should see (replaces the current list).
    workspace_ids: Annotated[list[uuid.UUID], Field(max_length=1000)]
