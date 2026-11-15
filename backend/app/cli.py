"""Backend admin commands.

    python -m app.cli create-super-admin --email you@example.com --name "Your Name"
    python -m app.cli grant-staff --email editor@example.com --role content_editor
    python -m app.cli revoke-staff --email editor@example.com

Super Admins can only be created here, never through the API or UI.
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.models import utcnow
from app.core.security import hash_password
from app.models import User
from app.modules.audit.service import record
from app.modules.rbac.service import sync_permissions
from app.modules.users.models import PLATFORM_ROLES


def create_super_admin(email: str, name: str) -> int:
    email = email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            # Existing account: promote it and leave its password alone.
            user.is_super_admin = True
            print(f"Promoted existing user {email} to Super Admin.")
        else:
            password = getpass.getpass("Password (min 10 characters): ")
            if len(password) < 10 or password != getpass.getpass("Repeat password: "):
                print("Passwords must match and be at least 10 characters.", file=sys.stderr)
                return 1
            user = User(email=email, full_name=name, password_hash=hash_password(password),
                        is_super_admin=True, email_verified_at=utcnow())
            db.add(user)
            db.flush()
            print(f"Created Super Admin {email}.")
        record(db, "admin.super_admin_granted", target_type="user", target_id=user.id,
               meta={"via": "cli"})
        db.commit()
    return 0


def set_staff_role(email: str, role: str | None) -> int:
    """Grant (or with role=None, revoke) Outlogik staff access to the admin area."""
    email = email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            print(f"No account for {email}. They need to sign up first.", file=sys.stderr)
            return 1
        before = user.platform_role
        user.platform_role = role
        record(db, "admin.staff_role_changed", target_type="user", target_id=user.id,
               meta={"via": "cli", "from": before, "to": role})
        db.commit()
    print(f"{email}: staff role {'removed' if role is None else 'set to ' + role}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-super-admin", help="Create or promote a Super Admin")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    sub.add_parser("sync-permissions", help="Sync the permission catalogue to the database")
    g = sub.add_parser("grant-staff", help="Give an existing user access to the admin area")
    g.add_argument("--email", required=True)
    g.add_argument("--role", required=True, choices=PLATFORM_ROLES)
    r = sub.add_parser("revoke-staff", help="Remove a user's access to the Outlogik admin area")
    r.add_argument("--email", required=True)
    args = parser.parse_args()

    if args.command == "create-super-admin":
        return create_super_admin(args.email, args.name)
    if args.command == "grant-staff":
        return set_staff_role(args.email, args.role)
    if args.command == "revoke-staff":
        return set_staff_role(args.email, None)
    if args.command == "sync-permissions":
        with SessionLocal() as db:
            sync_permissions(db)
        print("Permissions synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
