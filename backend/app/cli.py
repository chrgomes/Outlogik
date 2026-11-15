"""Backend admin commands.

    python -m app.cli create-super-admin --email you@example.com --name "Your Name"

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


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("create-super-admin", help="Create or promote a Super Admin")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    sub.add_parser("sync-permissions", help="Sync the permission catalogue to the database")
    args = parser.parse_args()

    if args.command == "create-super-admin":
        return create_super_admin(args.email, args.name)
    if args.command == "sync-permissions":
        with SessionLocal() as db:
            sync_permissions(db)
        print("Permissions synced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
