"""Workspaces hold an organization's marketing data: one "own" workspace per organization and
one "client" workspace per agency client. They're created and renamed with the organization
or client they belong to, so there's no separate API for creating them."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import case, false, func, select, true
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.modules.clients.models import Client
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.websites.models import Website
from app.modules.workspaces.models import Workspace, WorkspaceAssignment
from app.modules.workspaces.schemas import WorkspaceOut

if TYPE_CHECKING:  # tenancy.context imports auth, which creates organizations through here
    from app.tenancy.context import OrgContext

WORKSPACE_NOT_FOUND = "Workspace not found."


def create_own_workspace(db: Session, org: Organization) -> Workspace:
    ws = Workspace(organization_id=org.id, kind="own", name=org.name)
    db.add(ws)
    db.flush()
    return ws


def create_client_workspace(db: Session, client: Client) -> Workspace:
    ws = Workspace(organization_id=client.organization_id, kind="client", name=client.name,
                   client_id=client.id)
    db.add(ws)
    db.flush()
    return ws


def own_workspace(db: Session, org_id: uuid.UUID) -> Workspace:
    return db.scalars(select(Workspace).where(Workspace.organization_id == org_id,
                                              Workspace.kind == "own")).one()


def client_workspace(db: Session, client_id: uuid.UUID) -> Workspace:
    return db.scalars(select(Workspace).where(Workspace.client_id == client_id)).one()


def rename_for(db: Session, *, org: Organization | None = None,
               client: Client | None = None) -> None:
    """Keep a workspace's name in step with its organization or client."""
    ws = own_workspace(db, org.id) if org else client_workspace(db, client.id)
    ws.name = (org or client).name


def visibility(ctx: OrgContext):
    """WHERE clause: the workspaces the caller may see. Roles that see every workspace see
    them all; others (Account Manager, Client Viewer, …) only the ones they're assigned."""
    if ctx.workspace_ids is None:
        return true()
    return Workspace.id.in_(ctx.workspace_ids) if ctx.workspace_ids else false()


def get_workspace(db: Session, ctx: OrgContext, workspace_id: uuid.UUID) -> Workspace:
    ws = db.scalar(select(Workspace).where(Workspace.id == workspace_id,
                                           Workspace.organization_id == ctx.org.id,
                                           visibility(ctx)))
    if ws is None:
        raise NotFound(WORKSPACE_NOT_FOUND)
    return ws


def _many_out(db: Session, rows: list[tuple[Workspace, str | None]]) -> list[WorkspaceOut]:
    ids = [ws.id for ws, _ in rows]
    counts = dict(db.execute(select(Website.workspace_id, func.count())
                             .where(Website.workspace_id.in_(ids))
                             .group_by(Website.workspace_id)).all()) if ids else {}
    return [WorkspaceOut(id=ws.id, kind=ws.kind, name=ws.name, client_id=ws.client_id,
                         client_status=status, website_count=counts.get(ws.id, 0),
                         created_at=ws.created_at) for ws, status in rows]


def list_workspaces(db: Session, ctx: OrgContext) -> list[WorkspaceOut]:
    """The own workspace first, then client workspaces by name."""
    stmt = (select(Workspace, Client.status).outerjoin(Client, Client.id == Workspace.client_id)
            .where(Workspace.organization_id == ctx.org.id, visibility(ctx))
            .order_by(case((Workspace.kind == "own", 0), else_=1), func.lower(Workspace.name)))
    return _many_out(db, [tuple(r) for r in db.execute(stmt).all()])


def to_out(db: Session, ws: Workspace) -> WorkspaceOut:
    status = db.scalar(select(Client.status).where(Client.id == ws.client_id)) \
        if ws.client_id else None
    return _many_out(db, [(ws, status)])[0]


# --- assignments ----------------------------------------------------------------------------

def assign(db: Session, member: OrganizationMember, ws: Workspace) -> bool:
    """Give a member access to a workspace. False if they already had it."""
    exists = db.scalar(select(WorkspaceAssignment.id).where(
        WorkspaceAssignment.member_id == member.id, WorkspaceAssignment.workspace_id == ws.id))
    if exists:
        return False
    db.add(WorkspaceAssignment(organization_id=member.organization_id, member_id=member.id,
                               workspace_id=ws.id))
    db.flush()
    return True


def unassign(db: Session, member_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
    row = db.scalar(select(WorkspaceAssignment).where(
        WorkspaceAssignment.member_id == member_id,
        WorkspaceAssignment.workspace_id == workspace_id))
    if row is None:
        return False
    db.delete(row)
    db.flush()
    return True


def assigned_workspace_ids(db: Session, member_id: uuid.UUID) -> set[uuid.UUID]:
    return set(db.scalars(select(WorkspaceAssignment.workspace_id)
                          .where(WorkspaceAssignment.member_id == member_id)))
