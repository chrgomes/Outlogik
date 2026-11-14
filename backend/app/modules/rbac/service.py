import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.rbac.catalogue import DEFAULT_ROLES, PERMISSIONS
from app.modules.rbac.models import Permission, Role, RolePermission


def sync_permissions(db: Session) -> None:
    """Make the permissions table match the catalogue. Idempotent; runs at startup."""
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for code, description in PERMISSIONS.items():
        if code in existing:
            existing[code].description = description
        else:
            db.add(Permission(code=code, description=description))
    for code, perm in existing.items():
        if code not in PERMISSIONS:
            db.delete(perm)
    db.commit()


def _permission_ids(db: Session, codes: set[str]) -> list[uuid.UUID]:
    return list(db.scalars(select(Permission.id).where(Permission.code.in_(codes))))


def create_default_roles(db: Session, organization_id: uuid.UUID) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for key, spec in DEFAULT_ROLES.items():
        role = Role(organization_id=organization_id, name=spec["name"],
                    description=spec["description"], is_system=True, system_key=key)
        db.add(role)
        db.flush()
        for pid in _permission_ids(db, spec["permissions"]):
            db.add(RolePermission(role_id=role.id, permission_id=pid))
        roles[key] = role
    db.flush()
    return roles


def get_system_role(db: Session, organization_id: uuid.UUID, key: str) -> Role:
    return db.scalars(
        select(Role).where(Role.organization_id == organization_id, Role.system_key == key)
    ).one()


def role_permission_codes(db: Session, role_id: uuid.UUID) -> set[str]:
    return set(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        )
    )
