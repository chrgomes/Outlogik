import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

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
