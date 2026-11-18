import uuid

from fastapi import APIRouter, Depends, Request, Response, status

from app.core.request import client_ip
from app.modules.auth.deps import DB, CurrentUser
from app.modules.auth.schemas import MembershipOut
from app.modules.auth.service import memberships_for
from app.modules.grants import service
from app.modules.grants.schemas import (
    GrantAcceptIn,
    GrantCreateIn,
    GrantOut,
    GrantPreviewOut,
    GrantTokenIn,
)
from app.tenancy.context import OrgContext, require

# A business's grants
router = APIRouter(prefix="/orgs/{org_slug}/access-grants", tags=["access grants"])
# An agency ending its access to a linked workspace
linked_router = APIRouter(prefix="/orgs/{org_slug}/workspaces/{workspace_id}/access",
                          tags=["access grants"])
# Opening and accepting a grant link (signed-in user, any organization)
open_router = APIRouter(prefix="/access-grants", tags=["access grants"])


@router.get("", response_model=list[GrantOut], summary="Agencies given access to this business")
def list_grants(db: DB, ctx: OrgContext = Depends(require("access_grants.manage"))):
    return service.list_grants(db, ctx)


@router.post("", response_model=GrantOut, status_code=status.HTTP_201_CREATED,
             summary="Send an agency access to this business's workspace")
def create_grant(body: GrantCreateIn, request: Request, db: DB,
                 ctx: OrgContext = Depends(require("access_grants.manage"))):
    return service.create_grant(db, ctx, email=body.email, access=body.access,
                                ip=client_ip(request))


@router.delete("/{grant_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Cancel a pending grant, or end an agency's access")
def revoke_grant(grant_id: uuid.UUID, request: Request, db: DB,
                 ctx: OrgContext = Depends(require("access_grants.manage"))) -> Response:
    service.revoke_grant(db, ctx, grant_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@linked_router.delete("", status_code=status.HTTP_204_NO_CONTENT,
                      summary="Disconnect from a business's shared workspace")
def disconnect(workspace_id: uuid.UUID, request: Request, db: DB,
               ctx: OrgContext = Depends(require("linked_accounts.manage"))) -> Response:
    service.disconnect(db, ctx, workspace_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@open_router.post("/preview", response_model=GrantPreviewOut,
                  summary="What an access link offers, and which agencies can accept it")
def preview(body: GrantTokenIn, user: CurrentUser, db: DB):
    # POST so the token stays out of URLs and logs.
    return service.preview(db, body.token, user)


@open_router.post("/accept", response_model=list[MembershipOut],
                  summary="Accept an access link into one of your agencies")
def accept(body: GrantAcceptIn, request: Request, user: CurrentUser, db: DB):
    service.accept(db, body.token, body.organization_id, user, client_ip(request))
    return memberships_for(db, user)
