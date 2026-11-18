"""Backend admin commands.

    python -m app.cli create-super-admin --email you@example.com --name "Your Name"
    python -m app.cli create-organization --name "Outlogik" --owner-email you@example.com
    python -m app.cli grant-staff --email editor@example.com --role content_editor
    python -m app.cli revoke-staff --email editor@example.com

Super Admins can only be created here, never through the API or UI.
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.errors import AppError
from app.core.models import utcnow
from app.core.security import hash_password
from app.models import Organization, User
from app.modules.audit.service import record
from app.modules.organizations.service import create_organization
from app.modules.plans.catalogue import DEFAULT_PLANS, INTERVALS, STATUSES, TRIAL_DAYS
from app.modules.plans.service import set_plan
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


def create_organization_cmd(name: str, owner_email: str, owner_name: str | None,
                            kind: str = "agency", plan: str | None = None) -> int:
    """Create an organization with its owner. With invite-only sign-up, this is how Outlogik's
    own workspace (or any organization) is set up; everyone else is then invited from the app."""
    owner_email = owner_email.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == owner_email))
        if user is None:
            if not owner_name:
                print("No account for that email; pass --owner-name to create one.",
                      file=sys.stderr)
                return 1
            password = getpass.getpass("Owner password (min 10 characters): ")
            if len(password) < 10 or password != getpass.getpass("Repeat password: "):
                print("Passwords must match and be at least 10 characters.", file=sys.stderr)
                return 1
            user = User(email=owner_email, full_name=owner_name,
                        password_hash=hash_password(password), email_verified_at=utcnow())
            db.add(user)
            db.flush()
        org = create_organization(db, name, owner=user, kind=kind, plan=plan)
        record(db, "organization.create", actor_user_id=user.id, organization_id=org.id,
               target_type="organization", target_id=org.id,
               meta={"name": org.name, "kind": org.kind, "via": "cli"})
        db.commit()
        print(f"Created {org.kind} organization {org.name!r} (/o/{org.slug}) "
              f"owned by {owner_email}.")
    return 0


def set_plan_cmd(slug: str, plan: str, status: str, interval: str,
                 trial_days: int | None) -> int:
    """Assign a plan by hand (until billing exists)."""
    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.slug == slug.lower()))
        if org is None:
            print(f"No organization with the address /o/{slug}.", file=sys.stderr)
            return 1
        try:
            set_plan(db, org, plan, status=status, interval=interval, trial_days=trial_days)
        except AppError as exc:
            print(exc.message, file=sys.stderr)
            return 1
        db.commit()
    detail = f"trial for {trial_days or TRIAL_DAYS} days" if status == "trialing" else status
    print(f"{org.name}: {plan} ({interval}), {detail}.")
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
    o = sub.add_parser("create-organization", help="Create an organization and its owner")
    o.add_argument("--name", required=True)
    o.add_argument("--owner-email", required=True)
    o.add_argument("--owner-name", help="Needed only if the owner has no account yet")
    o.add_argument("--kind", choices=("agency", "business"), default="agency",
                   help="agency (works for clients; the default) or business")
    o.add_argument("--plan", choices=[p["key"] for p in DEFAULT_PLANS],
                   help="Start on this plan; without it, a free trial")
    sp = sub.add_parser("set-plan", help="Assign an organization's plan (until billing exists)")
    sp.add_argument("--org", required=True, help="The organization's address, e.g. outlogik")
    sp.add_argument("--plan", required=True, help="e.g. agency_professional, digital_growth")
    sp.add_argument("--status", choices=STATUSES, default="active")
    sp.add_argument("--interval", choices=INTERVALS, default="monthly")
    sp.add_argument("--trial-days", type=int, help="With --status trialing (default 14)")
    g = sub.add_parser("grant-staff", help="Give an existing user access to the admin area")
    g.add_argument("--email", required=True)
    g.add_argument("--role", required=True, choices=PLATFORM_ROLES)
    r = sub.add_parser("revoke-staff", help="Remove a user's access to the Outlogik admin area")
    r.add_argument("--email", required=True)
    args = parser.parse_args()

    if args.command == "create-super-admin":
        return create_super_admin(args.email, args.name)
    if args.command == "create-organization":
        return create_organization_cmd(args.name, args.owner_email, args.owner_name,
                                       args.kind, args.plan)
    if args.command == "set-plan":
        return set_plan_cmd(args.org, args.plan, args.status, args.interval, args.trial_days)
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
