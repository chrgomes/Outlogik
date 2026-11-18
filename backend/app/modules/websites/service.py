import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.core.pagination import PageParams, apply_sort, like_pattern, paginate
from app.modules.audit.service import record
from app.modules.clients.service import get_client
from app.modules.websites.models import Website
from app.modules.websites.schemas import WebsiteOut
from app.modules.websites.urls import normalize_url
from app.modules.workspaces import service as workspaces
from app.modules.workspaces.models import Workspace
from app.tenancy.context import OrgContext
from app.tenancy.scoped import get_visible, workspace_visibility

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


def get_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, *,
                workspace: Workspace | None = None, for_update: bool = False) -> Website:
    site = get_visible(db, Website, website_id, ctx,
                       visibility=workspace_visibility(Website.workspace_id, ctx),
                       label="Website", for_update=for_update)  # 404: "Website not found."
    if workspace is not None and site.workspace_id != workspace.id:
        raise NotFound(WEBSITE_NOT_FOUND)  # the same 404 as a missing website
    return site


def to_out(db: Session, site: Website) -> WebsiteOut:
    return _out(site, db.get(Workspace, site.workspace_id))


def list_websites(db: Session, ctx: OrgContext, params: PageParams, *, q: str | None,
                  client_id: uuid.UUID | None = None, workspace_id: uuid.UUID | None = None,
                  status: str | None, sort: str | None) -> tuple[list[WebsiteOut], int]:
    stmt = (select(Website, Workspace).join(Workspace, Workspace.id == Website.workspace_id)
            .where(Website.organization_id == ctx.org.id,
                   workspace_visibility(Website.workspace_id, ctx)))
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


def _ensure_unique(db: Session, ctx: OrgContext, url: str, exclude: uuid.UUID | None = None):
    stmt = select(Website.id).where(Website.organization_id == ctx.org.id, Website.url == url)
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
    url, domain = normalize_url(url)
    _ensure_unique(db, ctx, url)
    site = Website(organization_id=ctx.org.id, workspace_id=workspace.id,
                   client_id=workspace.client_id, url=url, domain=domain,
                   name=name or domain, status=status)
    db.add(site)
    db.flush()
    record(db, "website.create", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="website", target_id=site.id,
           meta={"url": url, "workspace": workspace.name,
                 "client": workspace.name if workspace.client_id else None}, ip=ip)
    _commit_unique(db)
    return _out(site, workspace)


def update_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, data: dict,
                   ip: str | None, *, workspace: Workspace | None = None) -> WebsiteOut:
    site = get_website(db, ctx, website_id, workspace=workspace, for_update=True)
    changes: dict = {}
    target = None
    if data.get("workspace_id"):
        target = workspaces.get_workspace(db, ctx, data["workspace_id"])
    elif data.get("client_id"):
        target = workspace_for_client(db, ctx, data["client_id"])
    if target is not None and target.id != site.workspace_id:
        current = db.get(Workspace, site.workspace_id)
        changes["workspace"] = {"from": current.name, "to": target.name}
        site.workspace_id, site.client_id = target.id, target.client_id
    if data.get("url"):
        url, domain = normalize_url(data["url"])
        if url != site.url:
            _ensure_unique(db, ctx, url, exclude=site.id)
            changes["url"] = {"from": site.url, "to": url}
            site.url, site.domain = url, domain
    for key in ("name", "status"):
        if data.get(key) and data[key] != getattr(site, key):
            changes[key] = {"from": getattr(site, key), "to": data[key]}
            setattr(site, key, data[key])
    if changes:
        record(db, "website.update", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
               target_type="website", target_id=site.id, meta=changes, ip=ip)
    _commit_unique(db)
    return to_out(db, site)


def delete_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, ip: str | None, *,
                   workspace: Workspace | None = None) -> None:
    site = get_website(db, ctx, website_id, workspace=workspace, for_update=True)
    record(db, "website.delete", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="website", target_id=site.id, meta={"url": site.url}, ip=ip)
    db.delete(site)
    db.commit()
