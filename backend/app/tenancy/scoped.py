"""Query helpers that always filter tenant-owned rows by the active organization."""

import uuid
from typing import Any

from sqlalchemy import Select, false, select, true
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.tenancy.context import OrgContext


def scoped_select(model: Any, ctx: OrgContext, *entities: Any) -> Select:
    stmt = select(*(entities or (model,)))
    return stmt.where(model.organization_id == ctx.org.id)


def get_scoped(db: Session, model: Any, obj_id: uuid.UUID, ctx: OrgContext,
               *, label: str | None = None, for_update: bool = False) -> Any:
    """Fetch one row by id within the active organization, or raise 404."""
    stmt = select(model).where(model.id == obj_id, model.organization_id == ctx.org.id)
    if for_update:
        stmt = stmt.with_for_update()
    obj = db.scalar(stmt)
    if obj is None:
        raise NotFound(f"{label or model.__name__} not found.")
    return obj


def client_visibility(client_id_column: Any, ctx: OrgContext) -> Any:
    """A WHERE clause limiting rows to the clients the caller may see (true for team members)."""
    if ctx.client_ids is None:
        return true()
    return client_id_column.in_(ctx.client_ids) if ctx.client_ids else false()


def workspace_visibility(workspace_id_column: Any, ctx: OrgContext) -> Any:
    """A WHERE clause limiting rows to the workspaces the caller may see (true when the role
    sees every workspace)."""
    if ctx.workspace_ids is None:
        return true()
    return workspace_id_column.in_(ctx.workspace_ids) if ctx.workspace_ids else false()


def get_visible(db: Session, model: Any, obj_id: uuid.UUID, ctx: OrgContext, *,
                visibility: Any, label: str, for_update: bool = False) -> Any:
    """get_scoped(), plus a visibility clause (client_visibility or workspace_visibility).
    Hidden rows are a plain 404."""
    stmt = select(model).where(model.id == obj_id, model.organization_id == ctx.org.id,
                               visibility)
    if for_update:
        stmt = stmt.with_for_update()
    obj = db.scalar(stmt)
    if obj is None:
        raise NotFound(f"{label} not found.")
    return obj
