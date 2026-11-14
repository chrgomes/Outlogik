"""Pagination and sorting shared by every list endpoint.

Lists return {"items", "total", "page", "page_size"}. Sorting takes `sort=field` or
`sort=-field` (descending) and accepts only fields the endpoint whitelists.
"""

from typing import Annotated, Any

from fastapi import Depends, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError


class PageParams(BaseModel):
    page: int = 1
    page_size: int = 25


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


Paging = Annotated[PageParams, Depends(page_params)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


def apply_sort(stmt: Select, sort: str | None, allowed: dict[str, Any], default: str) -> Select:
    key = sort or default
    desc = key.startswith("-")
    column = allowed.get(key.lstrip("-"))
    if column is None:
        raise AppError(f"Cannot sort by '{key.lstrip('-')}'.", code="invalid_sort",
                       details={"allowed": sorted(allowed)})
    return stmt.order_by(column.desc() if desc else column.asc())


def paginate(db: Session, stmt: Select, params: PageParams) -> tuple[list[Any], int]:
    """Run a select for one page. Returns (rows, total). Rows are full Result rows."""
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(
        stmt.limit(params.page_size).offset((params.page - 1) * params.page_size)
    ).all()
    return list(rows), total


def like_pattern(q: str) -> str:
    """A case-insensitive 'contains' pattern with LIKE wildcards in the input escaped."""
    escaped = q.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
