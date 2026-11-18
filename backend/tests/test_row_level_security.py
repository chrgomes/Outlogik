"""H1-3: the database itself hides other organizations' rows (migration 0012).

These tests query the database directly, without the application's own organization
filters, to prove the policies hold on their own.
"""

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionLocal, set_tenant
from app.models import (
    AuditLog,
    Client,
    Invitation,
    Organization,
    OrganizationMember,
    Role,
    Subscription,
    Website,
    Workspace,
)
from tests.conftest import register, slug_of, token_from_last_email

API = "/api/v1/orgs"


def _ordinary_user(session) -> None:
    """Superusers ignore row-level security. If the tests connect as one (as CI's default
    Postgres user does), switch to an ordinary role for this transaction."""
    if session.execute(text("SELECT rolsuper OR rolbypassrls FROM pg_roles "
                            "WHERE rolname = current_user")).scalar():
        session.execute(text("""
            DO $$ BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'rls_probe') THEN
                CREATE ROLE rls_probe NOLOGIN NOSUPERUSER NOBYPASSRLS;
              END IF;
            END $$"""))
        session.execute(text("GRANT ALL ON ALL TABLES IN SCHEMA public TO rls_probe"))
        session.execute(text("SET LOCAL ROLE rls_probe"))


@pytest.fixture
def two_orgs(client, new_client, db):
    """Two agencies, each with a client, a website, an invitation and activity."""
    slugs = []
    for browser, name in ((client, "Acme"), (new_client(), "Globex")):
        slug = slug_of(register(browser, f"owner@{name.lower()}.example.com", org=name))
        c = browser.post(f"{API}/{slug}/clients", json={"name": f"{name} Client"}).json()
        browser.post(f"{API}/{slug}/websites",
                     json={"client_id": c["id"], "url": f"{name.lower()}.example.com"})
        member = db.scalar(select(Role.id).join(Organization).where(
            Organization.slug == slug, Role.system_key == "member"))
        browser.post(f"{API}/{slug}/invitations",
                     json={"email": f"new@{name.lower()}.example.com", "role_id": str(member)})
        slugs.append(slug)
    ids = {s: db.scalar(select(Organization.id).where(Organization.slug == s)) for s in slugs}
    return ids


TENANT_MODELS = [Client, Website, Workspace, OrganizationMember, Role, Invitation, AuditLog,
                 Subscription]


def test_each_organization_sees_only_its_own_rows(two_orgs):
    acme, globex = two_orgs.values()
    with SessionLocal() as s:
        _ordinary_user(s)
        set_tenant(s, acme)
        for model in TENANT_MODELS:
            orgs = set(s.scalars(select(model.organization_id)))
            assert orgs == {acme}, model.__tablename__
        # Asking for the other organization's rows by id finds nothing.
        assert s.scalars(select(Client).where(Client.organization_id == globex)).all() == []


def test_the_setting_lasts_for_the_whole_request(two_orgs):
    """A request commits and starts new transactions; each one is limited again."""
    acme = two_orgs["acme"]
    with SessionLocal() as s:
        set_tenant(s, acme)
        s.commit()
        _ordinary_user(s)
        assert set(s.scalars(select(Website.organization_id))) == {acme}


def test_writing_into_another_organization_is_refused(two_orgs):
    acme, globex = two_orgs.values()
    with SessionLocal() as s:
        _ordinary_user(s)
        set_tenant(s, acme)
        s.add(Client(organization_id=globex, name="Smuggled"))
        with pytest.raises(DBAPIError, match="row-level security"):
            s.flush()
        s.rollback()
    with SessionLocal() as s:
        _ordinary_user(s)
        set_tenant(s, acme)
        # Updates and deletes simply don't reach the other organization's rows.
        hit = s.execute(text("UPDATE clients SET name = 'Pwned' WHERE organization_id = :o"),
                        {"o": globex}).rowcount
        gone = s.execute(text("DELETE FROM websites WHERE organization_id = :o"),
                         {"o": globex}).rowcount
        assert hit == 0 and gone == 0
        s.rollback()


def test_without_an_organization_nothing_is_limited(two_orgs):
    """Sign-in, the public site, the CLI and migrations aren't inside one organization."""
    with SessionLocal() as s:
        _ordinary_user(s)
        assert set(s.scalars(select(Client.organization_id))) == set(two_orgs.values())


def test_settings_dont_leak_to_the_next_session(two_orgs):
    with SessionLocal() as s:
        set_tenant(s, two_orgs["acme"])
        s.execute(select(Client)).all()
    with SessionLocal() as s:
        _ordinary_user(s)
        assert len(set(s.scalars(select(Client.organization_id)))) == 2


def test_a_grant_opens_only_the_shared_workspace(client, new_client, db):
    business = slug_of(register(client, "owner@bakery.example.com", org="Bakery",
                                account_type="business"))
    client.post(f"{API}/{business}/websites", json={"url": "bakery.example.com"})
    agency_browser = new_client()
    agency = slug_of(register(agency_browser, "owner@agency.example.com", org="Agency"))
    client.post(f"{API}/{business}/access-grants", json={"email": "owner@agency.example.com"})
    token = token_from_last_email("/agency-access")
    agency_id = db.scalar(select(Organization.id).where(Organization.slug == agency))
    business_id = db.scalar(select(Organization.id).where(Organization.slug == business))
    agency_browser.post("/api/v1/access-grants/accept",
                        json={"token": token, "organization_id": str(agency_id)})
    shared = db.scalar(select(Workspace.id).where(Workspace.organization_id == business_id))

    with SessionLocal() as s:
        _ordinary_user(s)
        set_tenant(s, agency_id, [shared])
        # The shared workspace and its websites are visible…
        assert s.get(Workspace, shared) is not None
        assert [w.domain for w in s.scalars(select(Website))] == ["bakery.example.com"]
        # …but nothing else of the business: its team, roles, invitations or activity.
        for model in (OrganizationMember, Role, Invitation, AuditLog):
            assert business_id not in set(s.scalars(select(model.organization_id))), model
    with SessionLocal() as s:
        _ordinary_user(s)
        set_tenant(s, agency_id, [])  # no grant
        assert s.get(Workspace, shared) is None
        assert s.scalars(select(Website)).all() == []


def test_unknown_organization_sees_nothing(two_orgs):
    with SessionLocal() as s:
        _ordinary_user(s)
        set_tenant(s, uuid.uuid4())
        for model in TENANT_MODELS:
            assert s.scalars(select(model)).all() == [], model.__tablename__
