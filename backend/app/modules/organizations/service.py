import re
import secrets
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.rbac.catalogue import OWNER
from app.modules.rbac.service import create_default_roles
from app.modules.users.models import User

RESERVED_SLUGS = {"admin", "api", "app", "auth", "login", "register", "settings", "new", "o"}


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:48].strip("-") or "org"


def unique_slug(db: Session, name: str) -> str:
    base = slugify(name)
    candidate = base if base not in RESERVED_SLUGS else f"{base}-org"
    while db.scalar(select(Organization.id).where(Organization.slug == candidate)):
        candidate = f"{base}-{secrets.token_hex(3)}"
    return candidate


def create_organization(db: Session, name: str, owner: User) -> Organization:
    org = Organization(name=name.strip(), slug=unique_slug(db, name))
    db.add(org)
    db.flush()
    roles = create_default_roles(db, org.id)
    db.add(OrganizationMember(organization_id=org.id, user_id=owner.id, role_id=roles[OWNER].id))
    db.flush()
    return org
