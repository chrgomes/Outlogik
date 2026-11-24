import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.errors import Forbidden
from app.core.models import utcnow
from app.modules.auth.deps import DB
from app.modules.dashboard import service
from app.modules.dashboard.analytics import MAX_DAYS, workspace_dashboard
from app.modules.dashboard.models import WorkspaceReview
from app.modules.dashboard.overview import overview
from app.modules.dashboard.schemas import (
    ContactsOut,
    DashboardOut,
    OverviewOut,
    ReviewOut,
    WorkspaceDashboardOut,
)
from app.modules.organizations.models import OrganizationMember
from app.modules.rbac.catalogue import ACCOUNT_MANAGER, OWNER
from app.modules.rbac.models import Role
from app.modules.users.models import User
from app.modules.workspaces.context import WorkspaceContext, require_workspace
from app.modules.workspaces.models import WorkspaceAssignment
from app.modules.workspaces.service import get_workspace
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut,
            summary="Counts and recent activity for the organization's dashboard")
def dashboard(db: DB, ctx: OrgContext = Depends(require("dashboard.read"))):
    return service.summary(db, ctx)


@router.get("/dashboard/overview", response_model=OverviewOut,
            summary="Every workspace side by side, and what needs attention (agencies)")
def dashboard_overview(db: DB, days: Annotated[int, Query(ge=7, le=90)] = 28,
                       ctx: OrgContext = Depends(require("dashboard.read"))):
    # The client portal shows a client their own workspace, never the agency's overview (§7).
    if ctx.is_client_user:
        raise Forbidden("The client portal shows your own dashboard.", code="client_portal")
    return overview(db, ctx, days)


@router.get("/workspaces/{workspace_id}/contacts", response_model=ContactsOut,
            summary="Who to contact about this workspace: its account managers, else the owners")
def contacts(db: DB, w: WorkspaceContext = Depends(require_workspace("dashboard.read"))):
    ctx, ws = w.org, w.workspace
    active = (OrganizationMember.organization_id == ctx.org.id) \
        & (OrganizationMember.status == "active")
    base = (select(User.full_name, User.email, Role.system_key)
            .join(OrganizationMember, OrganizationMember.user_id == User.id)
            .join(Role, Role.id == OrganizationMember.role_id).where(active))
    rows = db.execute(base.join(WorkspaceAssignment,
                                WorkspaceAssignment.member_id == OrganizationMember.id)
                      .where(WorkspaceAssignment.workspace_id == ws.id,
                             Role.system_key == ACCOUNT_MANAGER)
                      .order_by(User.full_name)).all()
    role = "account_manager"
    if not rows:
        rows = db.execute(base.where(Role.system_key == OWNER).order_by(User.full_name)).all()
        role = "owner"
    return ContactsOut(organization_name=ctx.org.name,
                       contacts=[{"name": n, "email": e, "role": role} for n, e, _ in rows])


@router.get("/workspaces/{workspace_id}/dashboard", response_model=WorkspaceDashboardOut,
            summary="One workspace's dashboard for a period, against an earlier one")
def workspace(db: DB, days: Annotated[int | None, Query(ge=1, le=MAX_DAYS)] = None,
              start: date | None = None, end: date | None = None,
              compare: Literal["previous", "year", "none"] = "previous",
              w: WorkspaceContext = Depends(require_workspace("dashboard.read"))):
    return workspace_dashboard(db, w.org, w.workspace, days=days, start=start, end=end,
                               compare=compare)


@router.put("/workspaces/{workspace_id}/review", response_model=ReviewOut,
            summary="Mark a workspace as reviewed today")
def mark_reviewed(workspace_id: uuid.UUID, db: DB,
                  ctx: OrgContext = Depends(require("workspaces.review"))):
    # The review is the caller's own record, so a view-only shared workspace can be reviewed.
    ws = get_workspace(db, ctx, workspace_id)
    review = db.scalar(select(WorkspaceReview).where(
        WorkspaceReview.organization_id == ctx.org.id, WorkspaceReview.workspace_id == ws.id))
    if review is None:
        review = WorkspaceReview(organization_id=ctx.org.id, workspace_id=ws.id)
        db.add(review)
    review.reviewed_at, review.reviewed_by_user_id = utcnow(), ctx.user.id
    db.commit()
    return ReviewOut(reviewed_at=review.reviewed_at, reviewed_by=ctx.user.full_name)
