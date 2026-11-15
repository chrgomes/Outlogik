import sys

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app import cli
from app.main import app
from app.models import AuditLog, ProductModule, User
from app.modules.site.service import ensure_defaults
from tests.conftest import login, register

PUBLIC = "/api/v1/public/site"
SETTINGS = "/api/v1/admin/site/settings"
MODULES = "/api/v1/admin/site/modules"


def make_staff(db, email: str, role: str | None = None, super_admin: bool = False):
    db.execute(update(User).where(User.email == email)
               .values(platform_role=role, is_super_admin=super_admin))
    db.commit()


@pytest.fixture
def site_admin(client, db):
    register(client, "admin@outlogik.example.com", org="Outlogik HQ")
    make_staff(db, "admin@outlogik.example.com", "site_admin")
    return client


# --- public -----------------------------------------------------------------------------------

def test_public_site_needs_no_login_and_is_cacheable(new_client):
    res = new_client().get(PUBLIC)
    assert res.status_code == 200
    body = res.json()
    assert [m["slug"] for m in body["modules"]][:2] == ["client-management", "seo-management"]
    assert {m["status"] for m in body["modules"]} == {"available", "in_development"}
    assert body["settings"]["tagline"] == "Digital Marketing. Smarter. Together."
    assert body["settings"]["contact_email"] is None  # nothing shown until set
    assert res.headers["Cache-Control"].startswith("public, max-age=60")


# --- who can use the admin API ------------------------------------------------------------------

def test_admin_api_hidden_from_everyone_but_staff(client, new_client, db):
    assert new_client().get(SETTINGS).status_code == 401  # signed out
    register(client, "owner@agency.example.com")  # an agency owner is not Outlogik staff
    assert client.get(SETTINGS).status_code == 404
    assert client.get(MODULES).status_code == 404

    make_staff(db, "owner@agency.example.com", "content_editor")
    assert client.get(SETTINGS).status_code == 404  # settings are for site admins

    make_staff(db, "owner@agency.example.com", "site_admin")
    assert client.get(SETTINGS).status_code == 200

    make_staff(db, "owner@agency.example.com", None, super_admin=True)
    assert client.get(SETTINGS).status_code == 200


def test_every_admin_route_requires_a_staff_role():
    checked = 0
    for rc in iter_route_contexts(app.routes):
        route = rc.original_route
        if isinstance(route, APIRoute) and (rc.path or "").startswith("/api/v1/admin"):
            deps = []
            stack = list(route.dependant.dependencies)
            while stack:
                d = stack.pop()
                deps.append(d)
                stack.extend(d.dependencies)
            assert any(hasattr(d.call, "staff_roles") for d in deps), rc.path
            checked += 1
    assert checked >= 4


def test_me_reports_staff_role(client, db):
    register(client, "person@example.com")
    assert client.get("/api/v1/auth/me").json()["user"]["platform_role"] is None
    make_staff(db, "person@example.com", "content_editor")
    assert client.get("/api/v1/auth/me").json()["user"]["platform_role"] == "content_editor"
    make_staff(db, "person@example.com", None, super_admin=True)
    assert client.get("/api/v1/auth/me").json()["user"]["platform_role"] == "site_admin"


# --- settings -----------------------------------------------------------------------------------

def test_update_settings_shows_on_public_site_and_is_audited(site_admin, new_client, db):
    current = site_admin.get(SETTINGS).json()["data"]
    current.update(contact_email="Hello@Outlogik.example.com", early_access=True,
                   social_links=[{"network": "linkedin", "url": "https://www.linkedin.com/company/x"}])
    res = site_admin.put(SETTINGS, json=current)
    assert res.status_code == 200, res.text

    public = new_client().get(PUBLIC).json()["settings"]
    assert public["contact_email"] == "hello@outlogik.example.com"
    assert public["social_links"][0]["network"] == "linkedin"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "site.settings_update"))
    assert entry.meta["fields"] == ["contact_email", "social_links"]
    assert entry.organization_id is None


@pytest.mark.parametrize("change", [
    {"contact_email": "not-an-email"},
    {"unknown_setting": True},
    {"social_links": [{"network": "myspace", "url": "https://myspace.com/x"}]},
    {"social_links": [{"network": "x", "url": "javascript:alert(1)"}]},
    {"primary_cta_label": ""},
])
def test_invalid_settings_are_rejected(site_admin, change):
    current = site_admin.get(SETTINGS).json()["data"]
    assert site_admin.put(SETTINGS, json={**current, **change}).status_code == 422


# --- product modules ----------------------------------------------------------------------------

def test_change_module_status(site_admin, new_client, db):
    res = site_admin.patch(f"{MODULES}/seo-management", json={"status": "available"})
    assert res.status_code == 200
    assert res.json()["status"] == "available"
    site_admin.patch(f"{MODULES}/reporting", json={"status": "hidden"})

    public = {m["slug"]: m["status"] for m in new_client().get(PUBLIC).json()["modules"]}
    assert public["seo-management"] == "available"
    assert "reporting" not in public
    # Admins still see hidden modules
    assert "reporting" in {m["slug"] for m in site_admin.get(MODULES).json()}

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "site.module_update")
                      .order_by(AuditLog.created_at))
    assert entry.meta == {"status": {"from": "in_development", "to": "available"}}


def test_module_validation(site_admin):
    assert site_admin.patch(f"{MODULES}/nope", json={"status": "available"}).status_code == 404
    assert site_admin.patch(f"{MODULES}/reporting", json={"status": "launched"}).status_code == 422


def test_defaults_restored_without_overwriting_changes(db):
    ensure_defaults(db)  # this test doesn't start the app, so seed first
    db.execute(update(ProductModule).where(ProductModule.slug == "reporting")
               .values(status="available"))
    db.execute(delete(ProductModule).where(ProductModule.slug == "seo-management"))
    db.commit()
    ensure_defaults(db)
    statuses = dict(db.execute(select(ProductModule.slug, ProductModule.status)).all())
    assert statuses["seo-management"] == "in_development"  # restored
    assert statuses["reporting"] == "available"  # kept


# --- CLI ----------------------------------------------------------------------------------------

def run_cli(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", ["app.cli", *args])
    return cli.main()


def test_grant_and_revoke_staff_via_cli(monkeypatch, client, db):
    register(client, "editor@example.com")
    assert run_cli(monkeypatch, "grant-staff", "--email", "Editor@Example.com",
                   "--role", "site_admin") == 0
    assert client.get(SETTINGS).status_code == 200
    assert run_cli(monkeypatch, "revoke-staff", "--email", "editor@example.com") == 0
    assert client.get(SETTINGS).status_code == 404
    actions = list(db.scalars(select(AuditLog.meta).where(
        AuditLog.action == "admin.staff_role_changed").order_by(AuditLog.created_at)))
    assert [(a["from"], a["to"]) for a in actions] == [(None, "site_admin"), ("site_admin", None)]


def test_grant_staff_requires_existing_account(monkeypatch, db):
    assert run_cli(monkeypatch, "grant-staff", "--email", "ghost@example.com",
                   "--role", "content_editor") == 1


def test_role_must_be_valid_at_database_level(client, db):
    register(client, "x@example.com")
    with pytest.raises(IntegrityError):
        db.execute(update(User).values(platform_role="owner"))
        db.commit()
    db.rollback()
    assert login(client, "x@example.com").status_code == 200
