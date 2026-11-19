import uuid
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.core.models import utcnow
from app.modules.auth.deps import DB
from app.modules.dashboard import service
from app.modules.dashboard.analytics import MAX_DAYS, workspace_dashboard
from app.modules.dashboard.models import WorkspaceReview
from app.modules.dashboard.overview import overview
from app.modules.dashboard.schemas import (
    DashboardOut,
    OverviewOut,
    ReviewOut,
    WorkspaceDashboardOut,
)
from app.modules.workspaces.context import WorkspaceContext, require_workspace
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
    return overview(db, ctx, days)


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
