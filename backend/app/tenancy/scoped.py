"""Query helpers that always filter tenant-owned rows by the active organization."""

import uuid
from typing import Any

from sqlalchemy import Select, select
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
