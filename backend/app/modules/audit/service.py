import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog


def record(
    db: Session,
    action: str,
    *,
    actor_user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | str | None = None,
    meta: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Add an audit entry to the current transaction. The caller commits."""
    entry = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        meta=meta or {},
        ip=ip,
    )
    db.add(entry)
    return entry
