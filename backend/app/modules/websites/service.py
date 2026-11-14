import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflict
from app.core.pagination import PageParams, apply_sort, like_pattern, paginate
from app.modules.audit.service import record
from app.modules.clients.models import Client
from app.modules.clients.service import get_client
from app.modules.websites.models import Website
from app.modules.websites.schemas import WebsiteOut
from app.modules.websites.urls import normalize_url
from app.tenancy.context import OrgContext
from app.tenancy.scoped import client_visibility, get_visible

WEBSITE_SORTS = {"name": func.lower(Website.name), "domain": Website.domain,
                 "created_at": Website.created_at, "client": func.lower(Client.name)}
DUPLICATE = "This website is already in your organization."


def _out(site: Website, client: Client) -> WebsiteOut:
    return WebsiteOut(id=site.id, client_id=client.id, client_name=client.name, name=site.name,
                      url=site.url, domain=site.domain, status=site.status,
                      created_at=site.created_at, updated_at=site.updated_at)


def get_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, *,
                for_update: bool = False) -> Website:
    return get_visible(db, Website, website_id, ctx, client_id_column=Website.client_id,
                       label="Website", for_update=for_update)


def to_out(db: Session, site: Website) -> WebsiteOut:
    return _out(site, db.get(Client, site.client_id))


def list_websites(db: Session, ctx: OrgContext, params: PageParams, *, q: str | None,
                  client_id: uuid.UUID | None, status: str | None,
                  sort: str | None) -> tuple[list[WebsiteOut], int]:
    stmt = (select(Website, Client).join(Client, Client.id == Website.client_id)
            .where(Website.organization_id == ctx.org.id,
                   client_visibility(Website.client_id, ctx)))
    if q:
        like = like_pattern(q)
        stmt = stmt.where(or_(func.lower(Website.name).like(like, escape="\\"),
                              Website.domain.like(like, escape="\\")))
    if client_id:
        stmt = stmt.where(Website.client_id == client_id)
    if status:
        stmt = stmt.where(Website.status == status)
    stmt = apply_sort(stmt, sort, WEBSITE_SORTS, "name")
    rows, total = paginate(db, stmt, params)
    return [_out(s, c) for s, c in rows], total


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


def create_website(db: Session, ctx: OrgContext, *, client_id: uuid.UUID, url: str,
                   name: str | None, status: str, ip: str | None) -> WebsiteOut:
    client = get_client(db, ctx, client_id)
    url, domain = normalize_url(url)
    _ensure_unique(db, ctx, url)
    site = Website(organization_id=ctx.org.id, client_id=client.id, url=url, domain=domain,
                   name=name or domain, status=status)
    db.add(site)
    db.flush()
    record(db, "website.create", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="website", target_id=site.id,
           meta={"url": url, "client": client.name}, ip=ip)
    _commit_unique(db)
    return _out(site, client)


def update_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, data: dict,
                   ip: str | None) -> WebsiteOut:
    site = get_website(db, ctx, website_id, for_update=True)
    changes: dict = {}
    if data.get("client_id") and data["client_id"] != site.client_id:
        new_client = get_client(db, ctx, data["client_id"])
        changes["client"] = {"from": db.get(Client, site.client_id).name, "to": new_client.name}
        site.client_id = new_client.id
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


def delete_website(db: Session, ctx: OrgContext, website_id: uuid.UUID, ip: str | None) -> None:
    site = get_website(db, ctx, website_id, for_update=True)
    record(db, "website.delete", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="website", target_id=site.id, meta={"url": site.url}, ip=ip)
    db.delete(site)
    db.commit()
