import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.core.pagination import PageParams, apply_sort, like_pattern, paginate
from app.modules.audit.service import record
from app.modules.clients.service import get_client
from app.modules.plans.service import check_limit
from app.modules.websites.models import Website
from app.modules.websites.schemas import WebsiteOut
from app.modules.websites.urls import normalize_url
from app.modules.workspaces import service as workspaces
from app.modules.workspaces.models import Workspace
from app.tenancy.context import OrgContext
from app.tenancy.scoped import workspace_visibility

# "client" sorts by workspace name, which is the client's name for client workspaces.
WEBSITE_SORTS = {"name": func.lower(Website.name), "domain": Website.domain,
                 "created_at": Website.created_at, "client": func.lower(Workspace.name),
                 "workspace": func.lower(Workspace.name)}
DUPLICATE = "This website is already in your organization."
WEBSITE_NOT_FOUND = "Website not found."


def _out(site: Website, ws: Workspace) -> WebsiteOut:
    return WebsiteOut(id=site.id, workspace_id=ws.id, workspace_name=ws.name,
                      client_id=ws.client_id, client_name=ws.name if ws.client_id else None,
                      name=site.name, url=site.url, domain=site.domain, status=site.status,
                      created_at=site.created_at, updated_at=site.updated_at)


def _reachable(ctx: OrgContext):
    """Websites of this organization, or in a workspace shared with it, that the caller may
    see."""
    belongs = Website.organization_id == ctx.org.id
    if ctx.linked:
        belongs = belongs | Website.workspace_id.in_(ctx.linked)
    return belongs & workspace_visibility(Website.workspace_id, ctx)


def get_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, *,
                workspace: Workspace | None = None, for_update: bool = False) -> Website:
    stmt = select(Website).where(Website.id == website_id, _reachable(ctx))
    if workspace is not None:
        stmt = stmt.where(Website.workspace_id == workspace.id)
    if for_update:
        stmt = stmt.with_for_update()
    site = db.scalar(stmt)
    if site is None:
        raise NotFound(WEBSITE_NOT_FOUND)  # the same 404 for missing and hidden websites
    return site


def _audit(db: Session, ctx: OrgContext, site: Website, action: str, meta: dict,
           ip: str | None) -> None:
    """Record the change for the website's organization. When an agency works in a business's
    shared workspace, both organizations get the entry."""
    if site.organization_id != ctx.org.id:
        meta = {**meta, "agency": ctx.org.name}
        record(db, action, actor_user_id=ctx.user.id, organization_id=ctx.org.id,
               target_type="website", target_id=site.id, meta=meta, ip=ip)
    record(db, action, actor_user_id=ctx.user.id, organization_id=site.organization_id,
           target_type="website", target_id=site.id, meta=meta, ip=ip)


def to_out(db: Session, site: Website) -> WebsiteOut:
    return _out(site, db.get(Workspace, site.workspace_id))


def list_websites(db: Session, ctx: OrgContext, params: PageParams, *, q: str | None,
                  client_id: uuid.UUID | None = None, workspace_id: uuid.UUID | None = None,
                  status: str | None, sort: str | None) -> tuple[list[WebsiteOut], int]:
    stmt = (select(Website, Workspace).join(Workspace, Workspace.id == Website.workspace_id)
            .where(_reachable(ctx)))
    if q:
        like = like_pattern(q)
        stmt = stmt.where(or_(func.lower(Website.name).like(like, escape="\\"),
                              Website.domain.like(like, escape="\\")))
    if client_id:
        stmt = stmt.where(Website.client_id == client_id)
    if workspace_id:
        stmt = stmt.where(Website.workspace_id == workspace_id)
    if status:
        stmt = stmt.where(Website.status == status)
    stmt = apply_sort(stmt, sort, WEBSITE_SORTS, "name")
    rows, total = paginate(db, stmt, params)
    return [_out(s, w) for s, w in rows], total


def _ensure_unique(db: Session, org_id: uuid.UUID, url: str, exclude: uuid.UUID | None = None):
    stmt = select(Website.id).where(Website.organization_id == org_id, Website.url == url)
    if exclude:
        stmt = stmt.where(Website.id != exclude)
    if db.scalar(stmt):
        raise Conflict(DUPLICATE, code="website_exists")


def _commit_unique(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:  # a concurrent request added the same URL
        db.rollback()
        raise Conflict(DUPLICATE, code="website_exists") from None


def workspace_for_client(db: Session, ctx: OrgContext, client_id: uuid.UUID | None) -> Workspace:
    """The older, client-based way of naming a workspace: a client, or none for the own one."""
    if client_id is None:
        return workspaces.get_workspace(db, ctx, workspaces.own_workspace(db, ctx.org.id).id)
    return workspaces.client_workspace(db, get_client(db, ctx, client_id).id)


def create_website(db: Session, ctx: OrgContext, *, workspace: Workspace, url: str,
                   name: str | None, status: str, ip: str | None) -> WebsiteOut:
    workspaces.ensure_writable(ctx, workspace.id)
    if status != "archived":
        # The plan of the organization that owns the workspace (a business's, when an agency
        # adds to a shared workspace).
        check_limit(db, workspace.organization_id, "limits.websites")
    url, domain = normalize_url(url)
    _ensure_unique(db, workspace.organization_id, url)
    site = Website(organization_id=workspace.organization_id, workspace_id=workspace.id,
                   client_id=workspace.client_id, url=url, domain=domain,
                   name=name or domain, status=status)
    db.add(site)
    db.flush()
    _audit(db, ctx, site, "website.create",
           {"url": url, "workspace": workspace.name,
            "client": workspace.name if workspace.client_id else None}, ip)
    _commit_unique(db)
    return _out(site, workspace)


def update_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, data: dict,
                   ip: str | None, *, workspace: Workspace | None = None) -> WebsiteOut:
    site = get_website(db, ctx, website_id, workspace=workspace, for_update=True)
    workspaces.ensure_writable(ctx, site.workspace_id)
    changes: dict = {}
    target = None
    if data.get("workspace_id"):
        target = workspaces.get_workspace(db, ctx, data["workspace_id"])
    elif data.get("client_id"):
        target = workspace_for_client(db, ctx, data["client_id"])
    if target is not None and target.organization_id != site.organization_id:
        # Websites only move between workspaces of the organization that owns them.
        raise NotFound(workspaces.WORKSPACE_NOT_FOUND)
    if target is not None and target.id != site.workspace_id:
        current = db.get(Workspace, site.workspace_id)
        changes["workspace"] = {"from": current.name, "to": target.name}
        site.workspace_id, site.client_id = target.id, target.client_id
    if data.get("url"):
        url, domain = normalize_url(data["url"])
        if url != site.url:
            _ensure_unique(db, site.organization_id, url, exclude=site.id)
            changes["url"] = {"from": site.url, "to": url}
            site.url, site.domain = url, domain
    if data.get("status") and site.status == "archived" and data["status"] != "archived":
        check_limit(db, site.organization_id, "limits.websites")  # restoring counts again
    for key in ("name", "status"):
        if data.get(key) and data[key] != getattr(site, key):
            changes[key] = {"from": getattr(site, key), "to": data[key]}
            setattr(site, key, data[key])
    if changes:
        _audit(db, ctx, site, "website.update", changes, ip)
    _commit_unique(db)
    return to_out(db, site)


def delete_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, ip: str | None, *,
                   workspace: Workspace | None = None) -> None:
    site = get_website(db, ctx, website_id, workspace=workspace, for_update=True)
    workspaces.ensure_writable(ctx, site.workspace_id)
    _audit(db, ctx, site, "website.delete", {"url": site.url}, ip)
    db.delete(site)
    db.commit()
