import uuid

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.core.errors import Forbidden
from app.modules.rbac.catalogue import ALL_WORKSPACES, DEFAULT_ROLES, OWNER, PERMISSIONS, roles_for
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
    """Keep every organization's built-in roles current: add roles new to its account type,
    update names, descriptions, scope and permissions. Set-based, so it costs a few statements
    regardless of the number of organizations. A built-in role keeps its old name if a custom
    role already uses the new one."""
    for key, spec in DEFAULT_ROLES.items():
        params = {"key": key, "name": spec["name"], "description": spec["description"],
                  "scope": spec["scope"], "kinds": sorted(spec["kinds"])}
        db.execute(text("""
            INSERT INTO roles (id, organization_id, name, description, is_system, system_key,
                               workspace_scope)
            SELECT gen_random_uuid(), o.id,
                   CASE WHEN EXISTS (SELECT 1 FROM roles c WHERE c.organization_id = o.id
                                     AND lower(c.name) = lower(CAST(:name AS text)))
                        THEN CAST(:name AS text) || ' (built-in)' ELSE CAST(:name AS text) END,
                   CAST(:description AS text), true, CAST(:key AS text), CAST(:scope AS text)
            FROM organizations o
            WHERE o.kind = ANY(CAST(:kinds AS text[]))
              AND NOT EXISTS (SELECT 1 FROM roles r WHERE r.organization_id = o.id
                              AND r.system_key = CAST(:key AS text))
        """), params)
        db.execute(text("""
            UPDATE roles r
               SET description = CAST(:description AS text),
                   workspace_scope = CAST(:scope AS text),
                   name = CASE WHEN EXISTS (SELECT 1 FROM roles c
                                            WHERE c.organization_id = r.organization_id
                                              AND c.id <> r.id
                                              AND lower(c.name) = lower(CAST(:name AS text)))
                               THEN r.name ELSE CAST(:name AS text) END
            WHERE r.is_system AND r.system_key = CAST(:key AS text)
              AND (r.description IS DISTINCT FROM CAST(:description AS text)
                   OR r.workspace_scope <> CAST(:scope AS text) OR r.name <> CAST(:name AS text))
        """), params)
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


def create_default_roles(db: Session, organization_id: uuid.UUID,
                         kind: str = "agency") -> dict[str, Role]:
    """The built-in roles for this account type (rbac/catalogue.py)."""
    roles: dict[str, Role] = {}
    for key, spec in roles_for(kind).items():
        role = Role(organization_id=organization_id, name=spec["name"],
                    description=spec["description"], is_system=True, system_key=key,
                    workspace_scope=spec["scope"])
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
                     role: Role, granter_scope: str = ALL_WORKSPACES) -> None:
    """No privilege escalation: you can only hand out a role whose permissions you hold, and
    someone limited to assigned workspaces can't hand out a role that sees all of them.
    Owners hold everything. Only owners can hand out the Owner role."""
    if role.system_key == OWNER and not granter_is_owner:
        raise Forbidden("Only an owner can make someone an owner.", code="owner_required")
    if granter_is_owner:
        return
    if granter_scope != ALL_WORKSPACES and role.workspace_scope == ALL_WORKSPACES:
        raise Forbidden("This role sees every workspace and you don't, so you can't assign it.",
                        code="role_exceeds_yours")
    extra = role_permission_codes(db, role.id) - granter_permissions
    if extra:
        raise Forbidden("This role has permissions you don't have, so you can't assign it.",
                        code="role_exceeds_yours", details={"permissions": sorted(extra)})


def member_count(db: Session, role_id: uuid.UUID) -> int:
    from app.modules.organizations.models import OrganizationMember

    return db.scalar(select(func.count()).select_from(OrganizationMember)
                     .where(OrganizationMember.role_id == role_id)) or 0
