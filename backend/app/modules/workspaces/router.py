import uuid

from fastapi import APIRouter, Depends, Request

from app.core.request import client_ip
from app.modules.auth.deps import DB
from app.modules.workspaces import assignments, service
from app.modules.workspaces.context import WorkspaceContext, require_workspace
from app.modules.workspaces.schemas import MemberWorkspacesIn, WorkspaceOut, WorkspaceRef
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}/workspaces", tags=["workspaces"])
members_router = APIRouter(prefix="/orgs/{org_slug}/members/{member_id}/workspaces",
                           tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut],
            summary="Workspaces you can open: the organization's own first, then its clients' "
                    "(client-portal users see only their clients')")
def list_workspaces(db: DB, ctx: OrgContext = Depends(require("organization.read"))):
    return service.list_workspaces(db, ctx)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(db: DB, wctx: WorkspaceContext = Depends(require_workspace("organization.read"))):
    return service.to_out(db, wctx.workspace)


@members_router.get("", response_model=list[WorkspaceRef],
                    summary="The workspaces a member is assigned to")
def member_workspaces(member_id: uuid.UUID, db: DB,
                      ctx: OrgContext = Depends(require("members.read"))):
    return assignments.list_member_workspaces(db, ctx, member_id)


@members_router.put("", response_model=list[WorkspaceRef],
                    summary="Choose the workspaces a member with a limited role can see")
def set_member_workspaces(member_id: uuid.UUID, body: MemberWorkspacesIn, request: Request,
                          db: DB, ctx: OrgContext = Depends(require("members.update"))):
    return assignments.set_member_workspaces(db, ctx, member_id, body.workspace_ids,
                                             client_ip(request))
