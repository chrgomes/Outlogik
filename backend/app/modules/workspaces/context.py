"""Workspace-scoped routes: /api/v1/orgs/{org_slug}/workspaces/{workspace_id}/...

`require_workspace(permission)` first runs the organization check (`require`), then loads the
workspace: one of the organization's own, or another organization's shared with it through an
access grant. A workspace the caller can't see is a 404, the same as one that doesn't exist.
Changes in a workspace shared with view-only access are refused (403).
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.workspaces.models import Workspace
from app.modules.workspaces.service import ensure_writable, get_workspace
from app.tenancy.context import OrgContext, require


@dataclass
class WorkspaceContext:
    org: OrgContext
    workspace: Workspace


def require_workspace(permission: str) -> Callable[..., WorkspaceContext]:
    org_dependency = require(permission)

    def _dependency(workspace_id: uuid.UUID = Path(), ctx: OrgContext = Depends(org_dependency),
                    db: Session = Depends(get_db)) -> WorkspaceContext:
        ws = get_workspace(db, ctx, workspace_id)
        if not permission.endswith(".read"):
            ensure_writable(ctx, ws.id)
        return WorkspaceContext(org=ctx, workspace=ws)

    _dependency.required_permission = permission  # type: ignore[attr-defined]
    return _dependency
