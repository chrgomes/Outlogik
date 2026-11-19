import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select

from app.modules.audits import service
from app.modules.audits.models import Audit
from app.modules.audits.schemas import (
    AuditDetailOut,
    AuditOut,
    AuditPageOut,
    AuditStartIn,
    FixedOut,
    IssueGroupOut,
    WebsiteAuditsOut,
)
from app.modules.auth.deps import DB
from app.modules.websites.models import Website
from app.modules.websites.service import get_website, reachable
from app.modules.workspaces.context import WorkspaceContext, require_workspace
from app.modules.workspaces.models import Workspace
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}/workspaces/{workspace_id}/audits", tags=["audits"])
overview_router = APIRouter(prefix="/orgs/{org_slug}/audits", tags=["audits"])


@overview_router.get("/websites", response_model=list[WebsiteAuditsOut],
                     summary="Every website you can see, with its latest audit")
def websites_overview(db: DB, ctx: OrgContext = Depends(require("audits.read"))):
    rows = db.execute(
        select(Website, Workspace).join(Workspace, Workspace.id == Website.workspace_id)
        .where(reachable(ctx), Website.status != "archived")
        .order_by(Workspace.name, Website.name)).all()
    out = []
    for site, ws in rows:
        latest = db.scalar(select(Audit).where(Audit.website_id == site.id)
                           .order_by(Audit.created_at.desc()).limit(1))
        out.append(WebsiteAuditsOut(website_id=site.id, website_name=site.name, url=site.url,
                                    workspace_id=ws.id, workspace_name=ws.name,
                                    audit_frequency=site.audit_frequency,
                                    latest=service._out(latest, site) if latest else None))
    return out


@router.get("", response_model=list[AuditOut], summary="Audits in this workspace, newest first")
def list_audits(db: DB, website_id: uuid.UUID | None = None,
                limit: Annotated[int, Query(ge=1, le=100)] = 30,
                w: WorkspaceContext = Depends(require_workspace("audits.read"))):
    stmt = select(Audit).where(Audit.workspace_id == w.workspace.id)
    if website_id:
        stmt = stmt.where(Audit.website_id == website_id)
    return [service.to_out(db, a) for a in db.scalars(
        stmt.order_by(Audit.created_at.desc()).limit(limit))]


@router.post("", response_model=AuditOut, status_code=status.HTTP_202_ACCEPTED,
             summary="Start an audit of one of this workspace's websites")
def start_audit(body: AuditStartIn, db: DB,
                w: WorkspaceContext = Depends(require_workspace("audits.run"))):
    site = get_website(db, w.org, body.website_id, workspace=w.workspace)
    audit = service.start(db, site, user_id=w.org.user.id, actor_org_id=w.org.org.id)
    db.refresh(audit)
    return service.to_out(db, audit)


@router.get("/{audit_id}", response_model=AuditDetailOut)
def get_audit(audit_id: uuid.UUID, db: DB,
              w: WorkspaceContext = Depends(require_workspace("audits.read"))):
    return service.detail(db, service.get(db, w.workspace, audit_id))


@router.get("/{audit_id}/issues", response_model=list[IssueGroupOut],
            summary="Issues found, grouped by check, most serious first")
def audit_issues(audit_id: uuid.UUID, db: DB,
                 w: WorkspaceContext = Depends(require_workspace("audits.read"))):
    return service.issues(db, service.get(db, w.workspace, audit_id))


@router.get("/{audit_id}/fixed", response_model=list[FixedOut],
            summary="Issues in the previous audit that are gone now")
def audit_fixed(audit_id: uuid.UUID, db: DB,
                w: WorkspaceContext = Depends(require_workspace("audits.read"))):
    return service.fixed(db, service.get(db, w.workspace, audit_id))


@router.get("/{audit_id}/pages", response_model=list[AuditPageOut])
def audit_pages(audit_id: uuid.UUID, db: DB,
                w: WorkspaceContext = Depends(require_workspace("audits.read"))):
    return service.pages(db, service.get(db, w.workspace, audit_id))
