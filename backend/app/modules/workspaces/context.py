"""Workspace-scoped routes: /api/v1/orgs/{org_slug}/workspaces/{workspace_id}/...

`require_workspace(permission)` first runs the organization check (`require`), then loads the
workspace within that organization. A workspace the caller can't see is a 404, the same as one
that doesn't exist.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.service import get_workspace
from app.tenancy.context import OrgContext, require


@dataclass
class WorkspaceContext:
    org: OrgContext
    workspace: Workspace


def require_workspace(permission: str) -> Callable[..., WorkspaceContext]:
    org_dependency = require(permission)

    def _dependency(workspace_id: uuid.UUID = Path(), ctx: OrgContext = Depends(org_dependency),
                    db: Session = Depends(get_db)) -> WorkspaceContext:
        return WorkspaceContext(org=ctx, workspace=get_workspace(db, ctx, workspace_id))

    _dependency.required_permission = permission  # type: ignore[attr-defined]
    return _dependency
