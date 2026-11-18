import os

# Configure before the app is imported.
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql+psycopg://outlogik:outlogik@localhost:5432/outlogik_test"
)
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
os.environ["REDIS_URL"] = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/15")
os.environ["APP_ENV"] = "test"
os.environ["EMAIL_BACKEND"] = "memory"
os.environ["FRONTEND_URL"] = "https://app.test"
# Production default is invite-only; tests create accounts through open sign-up.
os.environ["SIGNUP_MODE"] = "open"
# No DNS lookups in tests (example.com accepts no email); tests of the check switch it on.
os.environ["EMAIL_DOMAIN_CHECK"] = "false"
# Form tests don't solve proof-of-work puzzles; tests of the check switch it on.
os.environ["FORM_CHALLENGE_REQUIRED"] = "false"
os.environ["AUTH_CHALLENGE_REQUIRED"] = "false"

import re  # noqa: E402

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core import email  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.redis import get_redis  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

BASE_URL = "https://testserver"
KEEP_TABLES = {"permissions"}


@pytest.fixture(scope="session", autouse=True)
def _schema():
    """Build the test schema from the real migrations, so migrations are tested too."""
    cfg = Config("alembic.ini")
    cfg.attributes["configure_logger"] = False
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_state():
    yield
    tables = [t.name for t in Base.metadata.sorted_tables if t.name not in KEEP_TABLES]
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))
    get_redis().flushdb()
    email.outbox.clear()


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


def make_client() -> TestClient:
    """A browser-like client: it holds cookies and echoes the CSRF token like Angular does."""
    client = TestClient(app, base_url=BASE_URL)
    client.__enter__()
    client.get("/api/v1/auth/csrf")
    client.headers[get_settings().csrf_header_name] = client.cookies[
        get_settings().csrf_cookie_name
    ]
    return client


@pytest.fixture
def client():
    c = make_client()
    yield c
    c.__exit__(None, None, None)


@pytest.fixture
def new_client():
    """Factory for extra independent browsers (e.g. a second user or device)."""
    made: list[TestClient] = []

    def _make() -> TestClient:
        c = make_client()
        made.append(c)
        return c

    yield _make
    for c in made:
        c.__exit__(None, None, None)


PASSWORD = "correct horse battery"


def register(client: TestClient, email: str = "owner@agency.example.com", *,
             org: str = "Acme Agency",
             name: str = "Olive Owner", password: str = PASSWORD):
    res = client.post("/api/v1/auth/register", json={
        "email": email, "password": password, "full_name": name, "organization_name": org,
    })
    assert res.status_code == 201, res.text
    return res.json()


def login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def token_from_last_email(path: str) -> str:
    body = email.outbox[-1].body
    match = re.search(rf"{re.escape(path)}\?token=([\w-]+)", body)
    assert match, body
    return match.group(1)


# --- organization helpers -------------------------------------------------------------------

def seed_member(db, org_slug: str, email: str, role_key: str, *, name: str | None = None,
                password: str = PASSWORD, status: str = "active"):
    """Create a user and add them straight to an organization (bypassing invitations)."""
    from sqlalchemy import select as _select

    from app.core.security import hash_password
    from app.models import Organization, OrganizationMember, Role, User

    org = db.scalar(_select(Organization).where(Organization.slug == org_slug))
    role = db.scalar(_select(Role).where(Role.organization_id == org.id,
                                         Role.system_key == role_key))
    user = db.scalar(_select(User).where(User.email == email))
    if user is None:
        user = User(email=email, full_name=name or email.split("@")[0].title(),
                    password_hash=hash_password(password))
        db.add(user)
        db.flush()
    member = OrganizationMember(organization_id=org.id, user_id=user.id, role_id=role.id,
                                status=status)
    db.add(member)
    db.commit()
    return member


def seed_client(db, org_slug: str, name: str = "Client Co"):
    from sqlalchemy import select as _select

    from app.models import Client, Organization

    org = db.scalar(_select(Organization).where(Organization.slug == org_slug))
    client = Client(organization_id=org.id, name=name)
    db.add(client)
    db.commit()
    return client


def role_id(db, org_slug: str, role_key: str) -> str:
    from sqlalchemy import select as _select

    from app.models import Organization, Role

    return str(db.scalar(
        _select(Role.id).join(Organization, Organization.id == Role.organization_id)
        .where(Organization.slug == org_slug, Role.system_key == role_key)
    ))


def slug_of(me: dict) -> str:
    return me["memberships"][0]["organization_slug"]


def signed_in_as(new_client, db, org_slug: str, email: str, role_key: str):
    """Seed a member with a built-in role and return (browser, member), already logged in."""
    member = seed_member(db, org_slug, email, role_key)
    browser = new_client()
    assert login(browser, email).status_code == 200
    return browser, member


def link_client(db, member, client) -> None:
    from app.models import ClientUser

    db.add(ClientUser(organization_id=client.organization_id, client_id=client.id,
                      user_id=member.user_id))
    db.commit()
