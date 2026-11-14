import uuid

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.errors import Forbidden
from app.modules.rbac.catalogue import DEFAULT_ROLES, OWNER, PERMISSIONS
from app.modules.rbac.models import Permission, Role, RolePermission


def sync_permissions(db: Session) -> None:
    """Make the permissions table match the catalogue, and every organization's system roles
    match their default permission sets. Idempotent; runs at startup."""
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for code, description in PERMISSIONS.items():
        if code in existing:
            existing[code].description = description
        else:
            db.add(Permission(code=code, description=description))
    for code, perm in existing.items():
        if code not in PERMISSIONS:
            db.delete(perm)
    db.flush()
    sync_system_roles(db)
    db.commit()


def sync_system_roles(db: Session) -> None:
    """Set-based, so it costs a few statements regardless of the number of organizations."""
    for key, spec in DEFAULT_ROLES.items():
        codes = list(spec["permissions"])
        db.execute(text("""
            DELETE FROM role_permissions rp USING roles r, permissions p
            WHERE rp.role_id = r.id AND rp.permission_id = p.id
              AND r.is_system AND r.system_key = :key AND NOT (p.code = ANY(:codes))
        """), {"key": key, "codes": codes})
        db.execute(text("""
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
            WHERE r.is_system AND r.system_key = :key AND p.code = ANY(:codes)
            ON CONFLICT DO NOTHING
        """), {"key": key, "codes": codes})


def permission_ids(db: Session, codes: set[str]) -> list[uuid.UUID]:
    return list(db.scalars(select(Permission.id).where(Permission.code.in_(codes))))


def set_role_permissions(db: Session, role: Role, codes: set[str]) -> None:
    db.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    for pid in permission_ids(db, codes):
        db.add(RolePermission(role_id=role.id, permission_id=pid))
    db.flush()


def create_default_roles(db: Session, organization_id: uuid.UUID) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for key, spec in DEFAULT_ROLES.items():
        role = Role(organization_id=organization_id, name=spec["name"],
                    description=spec["description"], is_system=True, system_key=key)
        db.add(role)
        db.flush()
        set_role_permissions(db, role, spec["permissions"])
        roles[key] = role
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


def permission_codes_by_role(db: Session, role_ids: list[uuid.UUID]) -> dict[uuid.UUID, set[str]]:
    out: dict[uuid.UUID, set[str]] = {rid: set() for rid in role_ids}
    rows = db.execute(
        select(RolePermission.role_id, Permission.code)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id.in_(role_ids))
    )
    for rid, code in rows:
        out[rid].add(code)
    return out


def ensure_can_grant(db: Session, granter_permissions: set[str], granter_is_owner: bool,
                     role: Role) -> None:
    """No privilege escalation: you can only hand out a role whose permissions you hold.
    Owners hold everything. Only owners can hand out the Owner role."""
    if role.system_key == OWNER and not granter_is_owner:
        raise Forbidden("Only an owner can make someone an owner.", code="owner_required")
    if granter_is_owner:
        return
    extra = role_permission_codes(db, role.id) - granter_permissions
    if extra:
        raise Forbidden("This role has permissions you don't have, so you can't assign it.",
                        code="role_exceeds_yours", details={"permissions": sorted(extra)})


def member_count(db: Session, role_id: uuid.UUID) -> int:
    from app.modules.organizations.models import OrganizationMember

    return db.scalar(select(func.count()).select_from(OrganizationMember)
                     .where(OrganizationMember.role_id == role_id)) or 0
