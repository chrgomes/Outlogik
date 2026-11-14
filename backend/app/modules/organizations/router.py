import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.pagination import Page, Paging
from app.core.request import client_ip
from app.modules.audit.service import record
from app.modules.auth.deps import DB, CurrentUser
from app.modules.auth.schemas import MembershipOut
from app.modules.auth.service import memberships_for
from app.modules.organizations import invitations, members
from app.modules.organizations.schemas import (
    InvitationCreateIn,
    InvitationOut,
    MemberOut,
    MemberUpdateIn,
    OrganizationDetailOut,
    OrganizationUpdateIn,
)
from app.tenancy.context import OrgContext, get_org_context, require

router = APIRouter(tags=["organizations"])
org = APIRouter(prefix="/orgs/{org_slug}")

Sort = Annotated[str | None, Query(max_length=40, description="Field name; prefix - for desc")]


@router.get("/organizations", response_model=list[MembershipOut],
            summary="Organizations you belong to")
def my_organizations(user: CurrentUser, db: DB) -> list[dict]:
    return memberships_for(db, user)


def _detail(ctx: OrgContext) -> OrganizationDetailOut:
    return OrganizationDetailOut(
        id=ctx.org.id, name=ctx.org.name, slug=ctx.org.slug, status=ctx.org.status,
        created_at=ctx.org.created_at, your_role=ctx.role.name,
        your_permissions=sorted(ctx.permissions),
    )


@org.get("", response_model=OrganizationDetailOut)
def get_organization(ctx: OrgContext = Depends(require("organization.read"))):
    return _detail(ctx)


@org.patch("", response_model=OrganizationDetailOut)
def update_organization(body: OrganizationUpdateIn, request: Request, db: DB,
                        ctx: OrgContext = Depends(require("organization.update"))):
    if body.name is not None and body.name != ctx.org.name:
        record(db, "organization.update", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
               target_type="organization", target_id=ctx.org.id,
               meta={"name": {"from": ctx.org.name, "to": body.name}}, ip=client_ip(request))
        ctx.org.name = body.name
        db.add(ctx.org)
        db.commit()
    return _detail(ctx)


# --- members --------------------------------------------------------------------------------

@org.get("/members", response_model=Page[MemberOut])
def list_members(db: DB, paging: Paging, sort: Sort = None,
                 q: Annotated[str | None, Query(max_length=100)] = None,
                 status_: Annotated[Literal["active", "disabled"] | None,
                                    Query(alias="status")] = None,
                 role_id: uuid.UUID | None = None,
                 ctx: OrgContext = Depends(require("members.read"))):
    items, total = members.list_members(db, ctx, paging, q=q, status=status_, role_id=role_id,
                                        sort=sort)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@org.patch("/members/{member_id}", response_model=MemberOut)
def update_member(member_id: uuid.UUID, body: MemberUpdateIn, request: Request, db: DB,
                  ctx: OrgContext = Depends(require("members.update"))):
    return members.update_member(db, ctx, member_id, role_id=body.role_id, status=body.status,
                                 ip=client_ip(request))


@org.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(member_id: uuid.UUID, request: Request, db: DB,
                  ctx: OrgContext = Depends(require("members.remove"))) -> Response:
    members.remove_member(db, ctx, member_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@org.post("/leave", status_code=status.HTTP_204_NO_CONTENT,
          summary="Leave the organization yourself")
def leave(request: Request, db: DB, ctx: OrgContext = Depends(get_org_context)) -> Response:
    members.leave(db, ctx, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- invitations ----------------------------------------------------------------------------

@org.get("/invitations", response_model=Page[InvitationOut],
         summary="Open invitations (pending or expired, not yet accepted or cancelled)")
def list_invitations(db: DB, paging: Paging, sort: Sort = None,
                     ctx: OrgContext = Depends(require("members.invite"))):
    items, total = invitations.list_invitations(db, ctx, paging, sort)
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@org.post("/invitations", response_model=InvitationOut, status_code=status.HTTP_201_CREATED)
def create_invitation(body: InvitationCreateIn, request: Request, db: DB,
                      ctx: OrgContext = Depends(require("members.invite"))):
    return invitations.create_invitation(db, ctx, email=body.email, role_id=body.role_id,
                                         client_id=body.client_id, ip=client_ip(request))


@org.post("/invitations/{invitation_id}/resend", response_model=InvitationOut,
          summary="Send a fresh link (the old one stops working)")
def resend_invitation(invitation_id: uuid.UUID, request: Request, db: DB,
                      ctx: OrgContext = Depends(require("members.invite"))):
    return invitations.resend_invitation(db, ctx, invitation_id, client_ip(request))


@org.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(invitation_id: uuid.UUID, request: Request, db: DB,
                      ctx: OrgContext = Depends(require("members.invite"))) -> Response:
    invitations.revoke_invitation(db, ctx, invitation_id, client_ip(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


router.include_router(org)
