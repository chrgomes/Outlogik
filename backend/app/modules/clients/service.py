import uuid

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.core.pagination import PageParams, apply_sort, like_pattern, paginate
from app.modules.audit.service import record
from app.modules.clients.models import Client, ClientUser
from app.modules.clients.schemas import ClientOut, ClientUserOut
from app.modules.organizations.models import OrganizationMember
from app.modules.rbac.catalogue import CLIENT
from app.modules.rbac.models import Role
from app.modules.users.models import User
from app.modules.websites.models import Website
from app.tenancy.context import OrgContext
from app.tenancy.scoped import client_visibility, get_scoped, get_visible

CLIENT_SORTS = {"name": func.lower(Client.name), "created_at": Client.created_at,
                "updated_at": Client.updated_at}


def _count_by_client(db: Session, column, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    return dict(db.execute(select(column, func.count()).where(column.in_(ids))
                           .group_by(column)).all())


def _many_out(db: Session, ctx: OrgContext, clients: list[Client]) -> list[ClientOut]:
    ids = [c.id for c in clients]
    sites = _count_by_client(db, Website.client_id, ids)
    users = {} if ctx.is_client_user else _count_by_client(db, ClientUser.client_id, ids)
    return [ClientOut(
        id=c.id, name=c.name, contact_email=c.contact_email, status=c.status,
        notes=None if ctx.is_client_user else c.notes, website_count=sites.get(c.id, 0),
        portal_user_count=None if ctx.is_client_user else users.get(c.id, 0),
        created_at=c.created_at, updated_at=c.updated_at,
    ) for c in clients]


def to_out(db: Session, ctx: OrgContext, client: Client) -> ClientOut:
    return _many_out(db, ctx, [client])[0]


def get_client(db: Session, ctx: OrgContext, client_id: uuid.UUID, *,
               for_update: bool = False) -> Client:
    return get_visible(db, Client, client_id, ctx, client_id_column=Client.id, label="Client",
                       for_update=for_update)


def list_clients(db: Session, ctx: OrgContext, params: PageParams, *, q: str | None,
                 status: str | None, sort: str | None) -> tuple[list[ClientOut], int]:
    stmt = select(Client).where(Client.organization_id == ctx.org.id,
                                client_visibility(Client.id, ctx))
    if q:
        like = like_pattern(q)
        stmt = stmt.where(or_(func.lower(Client.name).like(like, escape="\\"),
                              func.lower(Client.contact_email).like(like, escape="\\")))
    if status:
        stmt = stmt.where(Client.status == status)
    stmt = apply_sort(stmt, sort, CLIENT_SORTS, "name")
    rows, total = paginate(db, stmt, params)
    return _many_out(db, ctx, [c for (c,) in rows]), total


def create_client(db: Session, ctx: OrgContext, data: dict, ip: str | None) -> ClientOut:
    client = Client(organization_id=ctx.org.id, **data)
    db.add(client)
    db.flush()
    record(db, "client.create", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="client", target_id=client.id, meta={"name": client.name}, ip=ip)
    db.commit()
    return to_out(db, ctx, client)


def update_client(db: Session, ctx: OrgContext, client_id: uuid.UUID, data: dict,
                  ip: str | None) -> ClientOut:
    client = get_client(db, ctx, client_id, for_update=True)
    changed = sorted(k for k, v in data.items() if getattr(client, k) != v)
    for key in changed:
        setattr(client, key, data[key])
    if changed:
        meta: dict = {"name": client.name, "fields": changed}
        if "status" in changed:
            meta["status"] = data["status"]
        record(db, "client.update", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
               target_type="client", target_id=client.id, meta=meta, ip=ip)
    db.commit()
    return to_out(db, ctx, client)


def delete_client(db: Session, ctx: OrgContext, client_id: uuid.UUID, ip: str | None) -> None:
    client = get_client(db, ctx, client_id, for_update=True)
    counts = {
        "websites": _count_by_client(db, Website.client_id, [client.id]).get(client.id, 0),
        "portal_users": _count_by_client(db, ClientUser.client_id, [client.id]).get(client.id, 0),
    }
    record(db, "client.delete", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="client", target_id=client.id, meta={"name": client.name, **counts},
           ip=ip)
    db.delete(client)  # websites, portal links and client invitations cascade in the database
    db.commit()


# --- client-portal users --------------------------------------------------------------------

def list_client_users(db: Session, ctx: OrgContext, client_id: uuid.UUID) -> list[ClientUserOut]:
    client = get_client(db, ctx, client_id)
    rows = db.execute(
        select(ClientUser, User, OrganizationMember)
        .join(User, User.id == ClientUser.user_id)
        .join(OrganizationMember, (OrganizationMember.user_id == User.id)
              & (OrganizationMember.organization_id == ctx.org.id))
        .where(ClientUser.client_id == client.id)
        .order_by(func.lower(User.full_name))
    ).all()
    return [ClientUserOut(user_id=u.id, member_id=m.id, email=u.email, full_name=u.full_name,
                          linked_at=cu.created_at) for cu, u, m in rows]


def link_client_user(db: Session, ctx: OrgContext, client_id: uuid.UUID,
                     member_id: uuid.UUID, ip: str | None) -> list[ClientUserOut]:
    """Give an existing client-portal member access to one more client."""
    client = get_client(db, ctx, client_id)
    member = get_scoped(db, OrganizationMember, member_id, ctx, label="Member")
    role = db.get(Role, member.role_id)
    if role.system_key != CLIENT:
        raise Conflict("Only members with the Client role can be linked to a client. "
                       "Team members already see every client.", code="not_client_role")
    exists = db.scalar(select(ClientUser.id).where(ClientUser.client_id == client.id,
                                                   ClientUser.user_id == member.user_id))
    if not exists:
        db.add(ClientUser(organization_id=ctx.org.id, client_id=client.id,
                          user_id=member.user_id))
        user = db.get(User, member.user_id)
        record(db, "client_user.link", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
               target_type="client", target_id=client.id,
               meta={"client": client.name, "user_email": user.email}, ip=ip)
        db.commit()
    return list_client_users(db, ctx, client.id)


def unlink_client_user(db: Session, ctx: OrgContext, client_id: uuid.UUID,
                       user_id: uuid.UUID, ip: str | None) -> None:
    client = get_client(db, ctx, client_id)
    result = db.execute(delete(ClientUser).where(ClientUser.client_id == client.id,
                                                 ClientUser.user_id == user_id,
                                                 ClientUser.organization_id == ctx.org.id))
    if not result.rowcount:
        raise NotFound("This person doesn't have access to this client.")
    user = db.get(User, user_id)
    record(db, "client_user.unlink", actor_user_id=ctx.user.id, organization_id=ctx.org.id,
           target_type="client", target_id=client.id,
           meta={"client": client.name, "user_email": user.email if user else None}, ip=ip)
    db.commit()
