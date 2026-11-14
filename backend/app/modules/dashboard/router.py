from fastapi import APIRouter, Depends

from app.modules.auth.deps import DB
from app.modules.dashboard import service
from app.modules.dashboard.schemas import DashboardOut
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut,
            summary="Counts and recent activity for the organization's dashboard")
def dashboard(db: DB, ctx: OrgContext = Depends(require("dashboard.read"))):
    return service.summary(db, ctx)
