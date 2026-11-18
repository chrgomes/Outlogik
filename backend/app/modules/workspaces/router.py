from fastapi import APIRouter, Depends

from app.modules.auth.deps import DB
from app.modules.workspaces import service
from app.modules.workspaces.context import WorkspaceContext, require_workspace
from app.modules.workspaces.schemas import WorkspaceOut
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut],
            summary="Workspaces you can open: the organization's own first, then its clients' "
                    "(client-portal users see only their clients')")
def list_workspaces(db: DB, ctx: OrgContext = Depends(require("organization.read"))):
    return service.list_workspaces(db, ctx)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(db: DB, wctx: WorkspaceContext = Depends(require_workspace("organization.read"))):
    return service.to_out(db, wctx.workspace)
