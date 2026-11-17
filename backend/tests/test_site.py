import sys

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from app import cli
from app.core.config import get_settings
from app.main import app
from app.models import AuditLog, PortalFeature, SiteSettings, User
from app.modules.site.service import ensure_defaults
from tests.conftest import login, register

PUBLIC = "/api/v1/public/site"
SETTINGS = "/api/v1/admin/site/settings"
FEATURES = "/api/v1/admin/site/portal-features"


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
    features = {f["slug"]: f["status"] for f in body["portal_features"]}
    assert features["client-portal"] == "available"
    assert features["monthly-reports"] == "in_development"
    assert body["settings"]["tagline"] == "Digital Marketing. Smarter. Together."
    assert body["settings"]["consultation_cta_label"] == "Book a free consultation"
    assert body["settings"]["contact_email"] is None  # nothing shown until set
    assert body["signup_open"] is True  # the test suite runs with open sign-up
    assert res.headers["Cache-Control"].startswith("public, max-age=60")


def test_public_site_reports_invite_only(new_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_mode", "invite_only")
    assert new_client().get(PUBLIC).json()["signup_open"] is False


def test_settings_from_older_versions_still_read(db, new_client):
    ensure_defaults(db)
    db.get(SiteSettings, 1).data = {"early_access": True, "demo_cta_label": "Book a demo",
                                    "tagline": "Kept"}
    db.commit()
    assert new_client().get(PUBLIC).json()["settings"]["tagline"] == "Kept"


# --- who can use the admin API ------------------------------------------------------------------

def test_admin_api_hidden_from_everyone_but_staff(client, new_client, db):
    assert new_client().get(SETTINGS).status_code == 401  # signed out
    register(client, "owner@agency.example.com")  # an agency owner is not Outlogik staff
    assert client.get(SETTINGS).status_code == 404
    assert client.get(FEATURES).status_code == 404

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
    current.update(contact_email="Hello@Outlogik.example.com",
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
    {"consultation_cta_label": ""},
    {"early_access": True},  # removed setting: rejected on write
])
def test_invalid_settings_are_rejected(site_admin, change):
    current = site_admin.get(SETTINGS).json()["data"]
    assert site_admin.put(SETTINGS, json={**current, **change}).status_code == 422


# --- client-portal features ---------------------------------------------------------------------

def test_change_feature_status(site_admin, new_client, db):
    res = site_admin.patch(f"{FEATURES}/monthly-reports", json={"status": "available"})
    assert res.status_code == 200
    assert res.json()["status"] == "available"
    site_admin.patch(f"{FEATURES}/seo-health", json={"status": "hidden"})

    public = {f["slug"]: f["status"] for f in new_client().get(PUBLIC).json()["portal_features"]}
    assert public["monthly-reports"] == "available"
    assert "seo-health" not in public
    # Admins still see hidden features
    assert "seo-health" in {f["slug"] for f in site_admin.get(FEATURES).json()}

    entry = db.scalar(select(AuditLog).where(AuditLog.action == "site.portal_feature_update")
                      .order_by(AuditLog.created_at))
    assert entry.meta == {"status": {"from": "in_development", "to": "available"}}


def test_feature_validation(site_admin):
    assert site_admin.patch(f"{FEATURES}/nope", json={"status": "available"}).status_code == 404
    res = site_admin.patch(f"{FEATURES}/seo-health", json={"status": "launched"})
    assert res.status_code == 422


def test_defaults_restored_without_overwriting_changes(db):
    ensure_defaults(db)  # this test doesn't start the app, so seed first
    db.execute(update(PortalFeature).where(PortalFeature.slug == "monthly-reports")
               .values(status="available"))
    db.execute(delete(PortalFeature).where(PortalFeature.slug == "seo-health"))
    db.commit()
    ensure_defaults(db)
    statuses = dict(db.execute(select(PortalFeature.slug, PortalFeature.status)).all())
    assert statuses["seo-health"] == "in_development"  # restored
    assert statuses["monthly-reports"] == "available"  # kept


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


def test_create_organization_via_cli(monkeypatch, new_client, db):
    import getpass as gp

    from app.models import Organization, OrganizationMember, Role
    answers = iter(["a long owner password"] * 2)
    monkeypatch.setattr(gp, "getpass", lambda prompt="": next(answers))
    assert run_cli(monkeypatch, "create-organization", "--name", "Outlogik",
                   "--owner-email", "Founder@Outlogik.example.com",
                   "--owner-name", "Fay Founder") == 0
    org = db.scalar(select(Organization).where(Organization.slug == "outlogik"))
    owner = db.scalar(select(User).where(User.email == "founder@outlogik.example.com"))
    role = db.scalar(select(Role).join(OrganizationMember, OrganizationMember.role_id == Role.id)
                     .where(OrganizationMember.user_id == owner.id))
    assert (org.name, role.system_key) == ("Outlogik", "owner")
    assert owner.email_verified_at is not None
    res = login(new_client(), "founder@outlogik.example.com", "a long owner password")
    assert res.status_code == 200


def test_create_organization_for_existing_user_needs_no_password(monkeypatch, client, db):
    register(client, "existing@example.com")
    assert run_cli(monkeypatch, "create-organization", "--name", "Second Org",
                   "--owner-email", "existing@example.com") == 0
    slugs = {m["organization_slug"] for m in client.get("/api/v1/auth/me").json()["memberships"]}
    assert "second-org" in slugs


def test_create_organization_unknown_owner_without_name_fails(monkeypatch, db):
    assert run_cli(monkeypatch, "create-organization", "--name", "X",
                   "--owner-email", "nobody@example.com") == 1


# --- analytics settings -------------------------------------------------------------------------

def test_analytics_ids_are_optional_and_validated(site_admin, new_client):
    data = site_admin.get(SETTINGS).json()["data"]
    assert data["ga4_measurement_id"] is None and data["clarity_project_id"] is None
    for bad in [{"ga4_measurement_id": "UA-12345-1"}, {"gtm_container_id": "<script>"},
                {"clarity_project_id": "Bad ID!"}]:
        assert site_admin.put(SETTINGS, json={**data, **bad}).status_code == 422, bad
    good = {"ga4_measurement_id": "G-ABC123XYZ", "gtm_container_id": "GTM-AB12CD",
            "clarity_project_id": "abc123defg"}
    assert site_admin.put(SETTINGS, json={**data, **good}).status_code == 200
    public = new_client().get(PUBLIC).json()["settings"]
    assert {k: public[k] for k in good} == good


def test_legal_details_are_optional_and_validated(site_admin, new_client):
    data = site_admin.get(SETTINGS).json()["data"]
    # The business's details are the defaults, so a new site publishes its legal pages.
    assert (data["legal_name"], data["province"], data["privacy_email"], data["address"]) == (
        "Outlogik", "Ontario", "privacy@outlogik.com", "Toronto, Ontario, Canada")
    assert site_admin.put(SETTINGS, json={**data, "province": "Atlantis"}).status_code == 422
    assert site_admin.put(SETTINGS, json={**data, "privacy_email": "nope"}).status_code == 422
    details = {"legal_name": "Outlogik Inc.", "province": "Ontario",
               "privacy_email": "Privacy@Outlogik.example.com",
               "address": "1 Example Street\nToronto, ON"}
    assert site_admin.put(SETTINGS, json={**data, **details}).status_code == 200
    public = new_client().get(PUBLIC).json()["settings"]
    assert public["legal_name"] == "Outlogik Inc." and public["province"] == "Ontario"
    assert public["privacy_email"] == "privacy@outlogik.example.com"


def test_admin_province_list_matches_the_api():
    import re
    from pathlib import Path
    from typing import get_args

    from app.modules.site.schemas import Province

    src = (Path(__file__).parents[2] / "frontend/src/app/features/admin/admin-api.ts").read_text()
    block = src.split("export const PROVINCES = [")[1].split("];")[0]
    assert re.findall(r"'([^']+)'", block) == list(get_args(Province))


def test_sales_and_billing_emails_default_to_the_business_aliases(site_admin, new_client):
    data = site_admin.get(SETTINGS).json()["data"]
    assert (data["sales_email"], data["billing_email"]) == (
        "sales@outlogik.com", "billings@outlogik.com")
    assert site_admin.put(SETTINGS, json={**data, "billing_email": "nope"}).status_code == 422
    assert site_admin.put(SETTINGS, json={**data, "billing_email": "Accounts@Outlogik.com"}
                          ).status_code == 200
    assert new_client().get(PUBLIC).json()["settings"]["billing_email"] == "accounts@outlogik.com"
