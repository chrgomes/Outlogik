"""H1-11: sign-up with an invitation code, staff roles, and the Super Admin (platform) API."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.models import utcnow
from app.models import AuditLog, Organization, SignupCode, User, Website, Workspace
from app.modules.audits.service import schedule_due
from tests.conftest import PASSWORD, login, register, slug_of, token_from_last_email

P = "/api/v1/admin/platform"
API = "/api/v1/orgs"


def staff(new_client, db, email, role=None, *, super_admin=False):
    """A signed-in Outlogik staff member with a platform role (or a Super Admin)."""
    from app.core.security import hash_password
    user = User(email=email, full_name=email.split("@")[0].title(),
                password_hash=hash_password(PASSWORD), platform_role=role,
                is_super_admin=super_admin, email_verified_at=utcnow())
    db.add(user)
    db.commit()
    browser = new_client()
    assert login(browser, email).status_code == 200
    return browser, user


@pytest.fixture
def code_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_mode", "code")


def make_code(browser, **body):
    body.setdefault("label", "Beta wave 1")
    res = browser.post(f"{P}/signup-codes", json=body)
    assert res.status_code == 201, res.text
    return res.json()


def sign_up(browser, email, code=None, kind="agency", org="Shop"):
    body = {"email": email, "password": PASSWORD, "full_name": "New Person",
            "organization_name": org, "account_type": kind}
    if code is not None:
        body["signup_code"] = code
    return browser.post("/api/v1/auth/register", json=body)


# --- sign-up with an invitation code --------------------------------------------------------

def test_sign_up_needs_a_valid_code_in_code_mode(new_client, db, code_mode):
    admin, _ = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    created = make_code(admin, max_uses=2)
    assert created["code"].count("-") == 2 and created["status"] == "active"
    assert sign_up(new_client(), "a@x.example.com").json()["error"]["details"][0]["field"] \
        == "signup_code"
    res = sign_up(new_client(), "b@x.example.com", "NOPE-NOPE-NOPE")
    assert res.status_code == 400 and res.json()["error"]["code"] == "signup_code_invalid"
    # Any case, with or without dashes
    typed = created["code"].replace("-", "").lower()
    res = sign_up(new_client(), "c@x.example.com", typed, kind="business", org="Corner Bakery")
    assert res.status_code == 201, res.text
    org = db.scalar(select(Organization).where(Organization.name == "Corner Bakery"))
    code = db.get(SignupCode, created["id"])
    assert code.uses == 1 and org.signup_code_id == code.id and org.kind == "business"
    entry = db.scalar(select(AuditLog).where(AuditLog.action == "auth.register"))
    assert entry.meta == {"signup_code": "Beta wave 1"}
    assert sign_up(new_client(), "d@x.example.com", created["code"]).status_code == 201
    res = sign_up(new_client(), "e@x.example.com", created["code"])
    assert "already been used" in res.json()["error"]["message"]


def test_codes_can_be_limited_to_one_account_type_expire_and_be_revoked(
        new_client, db, code_mode):
    admin, _ = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    business_only = make_code(admin, account_type="business")
    res = sign_up(new_client(), "a@x.example.com", business_only["code"], kind="agency")
    assert res.json()["error"]["message"] == "That invitation code is for businesses."
    expiring = make_code(admin, expires_in_days=1)
    db.get(SignupCode, expiring["id"]).expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert "expired" in sign_up(new_client(), "b@x.example.com",
                                expiring["code"]).json()["error"]["message"]
    revoked = make_code(admin)
    assert admin.post(f"{P}/signup-codes/{revoked['id']}/revoke").json()["status"] == "revoked"
    assert sign_up(new_client(), "c@x.example.com", revoked["code"]).status_code == 400
    listed = admin.get(f"{P}/signup-codes").json()
    assert {c["status"] for c in listed} == {"active", "expired", "revoked"}
    assert all("code" not in c for c in listed)  # shown once, never again
    assert db.scalar(select(AuditLog).where(AuditLog.action == "platform.signup_code_revoke"))


def test_the_app_knows_a_code_is_needed(client, code_mode):
    body = client.get("/api/v1/public/site").json()
    assert body["signup_open"] is True and body["signup_code_required"] is True


def test_invite_only_still_refuses_sign_up(new_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_mode", "invite_only")
    res = sign_up(new_client(), "a@x.example.com", "ANY")
    assert res.status_code == 403 and res.json()["error"]["code"] == "signup_disabled"


# --- who can use the platform area ----------------------------------------------------------

@pytest.mark.parametrize("role,expected", [
    ("platform_admin", ["orgs.suspend", "plans.assign", "platform.read", "signup_codes.manage",
                        "users.suspend"]),
    ("support_admin", ["platform.read", "users.suspend"]),
    ("billing_admin", ["plans.assign", "platform.read"]),
    ("site_admin", []),
    ("content_editor", []),
])
def test_staff_roles_and_what_they_can_do(new_client, db, role, expected):
    browser, _ = staff(new_client, db, f"{role}@outlogik.example.com", role)
    me = browser.get("/api/v1/auth/me").json()["user"]
    assert me["platform_caps"] == expected and me["platform_role"] == role
    assert browser.get(f"{P}/overview").status_code == (200 if expected else 404)


def test_super_admins_can_do_everything(new_client, db):
    browser, _ = staff(new_client, db, "root@outlogik.example.com", super_admin=True)
    me = browser.get("/api/v1/auth/me").json()["user"]
    assert len(me["platform_caps"]) == 5 and me["platform_role"] == "site_admin"


def test_customers_cant_find_the_platform_api(client):
    register(client)
    for path in ("overview", "organizations", "users", "signup-codes", "plans"):
        assert client.get(f"{P}/{path}").status_code == 404, path


def test_each_role_is_limited_to_its_actions(client, new_client, db):
    slug = slug_of(register(client, "owner@agency.example.com", org="Agency"))
    org_id = db.scalar(select(Organization.id).where(Organization.slug == slug))
    user_id = db.scalar(select(User.id).where(User.email == "owner@agency.example.com"))
    billing, _ = staff(new_client, db, "billing@outlogik.example.com", "billing_admin")
    support, _ = staff(new_client, db, "support@outlogik.example.com", "support_admin")
    plan = {"plan": "agency_starter", "status": "active"}
    assert billing.put(f"{P}/organizations/{org_id}/plan", json=plan).status_code == 200
    assert billing.post(f"{P}/organizations/{org_id}/suspend",
                        json={"reason": "Test"}).status_code == 404
    assert billing.post(f"{P}/users/{user_id}/suspend", json={"reason": "Test"}).status_code \
        == 404
    assert billing.get(f"{P}/signup-codes").status_code == 404
    assert support.put(f"{P}/organizations/{org_id}/plan", json=plan).status_code == 404
    assert support.post(f"{P}/organizations/{org_id}/suspend",
                        json={"reason": "Test"}).status_code == 404
    assert support.post(f"{P}/users/{user_id}/suspend",
                        json={"reason": "Spam sign-ups"}).status_code == 200


# --- overview, organizations, users ---------------------------------------------------------

def test_overview_counts(client, new_client, db):
    register(client, "owner@agency.example.com", org="Agency")
    register(new_client(), "owner@bakery.example.com", org="Bakery", account_type="business")
    admin, _ = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    o = admin.get(f"{P}/overview").json()
    assert o["organizations"]["agency"] == 1 and o["organizations"]["business"] == 1
    assert o["users"]["total"] == 3 and o["users"]["unverified"] == 2
    assert o["subscriptions"]["trialing"] == 2
    assert o["jobs"]["queued"] >= 0 and "oldest_queued_minutes" in o["jobs"]


def test_organizations_list_search_and_detail(client, new_client, db):
    slug = slug_of(register(client, "owner@agency.example.com", org="Northline Agency"))
    register(new_client(), "owner@bakery.example.com", org="Corner Bakery",
             account_type="business")
    client.post(f"{API}/{slug}/clients", json={"name": "Alpha"})
    admin, _ = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    rows = admin.get(f"{P}/organizations", params={"q": "north"}).json()["items"]
    assert [r["name"] for r in rows] == ["Northline Agency"]
    assert rows[0]["plan"] == "Agency Business" and rows[0]["subscription_status"] == "trialing"
    assert rows[0]["clients"] == 1 and rows[0]["members"] == 1
    assert [r["name"] for r in admin.get(f"{P}/organizations",
                                         params={"kind": "business"}).json()["items"]] \
        == ["Corner Bakery"]
    d = admin.get(f"{P}/organizations/{rows[0]['id']}").json()
    assert d["members_list"][0]["email"] == "owner@agency.example.com"
    assert {x["key"] for x in d["limits"]} >= {"limits.websites", "limits.clients"}


def test_assigning_a_plan_is_recorded(client, new_client, db):
    slug = slug_of(register(client, "owner@agency.example.com", org="Agency"))
    org_id = db.scalar(select(Organization.id).where(Organization.slug == slug))
    admin, staffer = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    res = admin.put(f"{P}/organizations/{org_id}/plan",
                    json={"plan": "agency_professional", "status": "trialing"})
    assert res.status_code == 422 and res.json()["error"]["code"] == "trial_days_required"
    d = admin.put(f"{P}/organizations/{org_id}/plan", json={
        "plan": "agency_professional", "status": "active", "interval": "annual"}).json()
    assert d["plan"] == "Agency Professional" and d["billing_interval"] == "annual"
    assert d["history"][0]["action"] == "subscription.change"
    assert d["history"][0]["actor"] == staffer.full_name
    assert client.get(f"{API}/{slug}/subscription").json()["plan"]["key"] \
        == "agency_professional"
    res = admin.put(f"{P}/organizations/{org_id}/plan", json={"plan": "digital_starter"})
    assert res.status_code == 422 and res.json()["error"]["code"] == "plan_kind_mismatch"


def test_suspending_an_organization(client, new_client, db):
    slug = slug_of(register(client, "owner@agency.example.com", org="Agency"))
    org_id = db.scalar(select(Organization.id).where(Organization.slug == slug))
    client.post(f"{API}/{slug}/websites", json={"url": "agency.example.com"})
    db.execute(Website.__table__.update().values(audit_frequency="weekly"))
    db.commit()
    admin, _ = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    assert admin.post(f"{P}/organizations/{org_id}/suspend", json={"reason": "x"}).status_code \
        == 422  # a reason is required
    d = admin.post(f"{P}/organizations/{org_id}/suspend",
                   json={"reason": "Unpaid invoices"}).json()
    assert d["status"] == "suspended" and d["suspended_reason"] == "Unpaid invoices"
    res = client.get(f"{API}/{slug}/websites")
    assert res.status_code == 403 and res.json()["error"]["code"] == "org_suspended"
    assert schedule_due(db) == 0  # no scheduled audits while suspended
    d = admin.post(f"{P}/organizations/{org_id}/reactivate").json()
    assert d["status"] == "active" and d["suspended_reason"] is None
    assert [h["action"] for h in d["history"]][:2] == ["platform.org_reactivate",
                                                       "platform.org_suspend"]
    assert client.get(f"{API}/{slug}/websites").status_code == 200


def test_a_suspended_business_disappears_from_its_agency(client, new_client, db):
    business = new_client()
    bslug = slug_of(register(business, "owner@shop.example.com", org="Shop",
                             account_type="business"))
    aslug = slug_of(register(client, "owner@agency.example.com", org="Agency"))
    business.post(f"{API}/{bslug}/access-grants", json={"email": "owner@agency.example.com"})
    agency_id = db.scalar(select(Organization.id).where(Organization.slug == aslug))
    client.post("/api/v1/access-grants/accept", json={
        "token": token_from_last_email("/agency-access"), "organization_id": str(agency_id)})
    shared = db.scalar(select(Workspace.id).join(Organization).where(Organization.slug == bslug))
    assert any(w["linked"] for w in client.get(f"{API}/{aslug}/workspaces").json())
    admin, _ = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    business_id = db.scalar(select(Organization.id).where(Organization.slug == bslug))
    admin.post(f"{P}/organizations/{business_id}/suspend", json={"reason": "Fraud check"})
    assert not any(w["linked"] for w in client.get(f"{API}/{aslug}/workspaces").json())
    assert client.get(f"{API}/{aslug}/workspaces/{shared}/websites").status_code == 404


def test_suspending_a_user_signs_them_out(client, new_client, db):
    register(client, "owner@agency.example.com", org="Agency")
    user_id = db.scalar(select(User.id).where(User.email == "owner@agency.example.com"))
    support, me = staff(new_client, db, "support@outlogik.example.com", "support_admin")
    d = support.post(f"{P}/users/{user_id}/suspend", json={"reason": "Abuse report"}).json()
    assert d["active"] is False and d["suspended_reason"] == "Abuse report"
    assert d["memberships"][0]["organization_name"] == "Agency"
    assert client.get("/api/v1/auth/me").status_code == 401
    assert login(new_client(), "owner@agency.example.com").status_code == 401
    assert support.get(f"{P}/users", params={"status": "suspended"}).json()["total"] == 1
    support.post(f"{P}/users/{user_id}/reactivate")
    assert login(new_client(), "owner@agency.example.com").status_code == 200
    # Not yourself, and staff only by a Super Admin
    res = support.post(f"{P}/users/{me.id}/suspend", json={"reason": "Oops"})
    assert res.json()["error"]["code"] == "cannot_suspend_self"
    _, other = staff(new_client, db, "billing@outlogik.example.com", "billing_admin")
    res = support.post(f"{P}/users/{other.id}/suspend", json={"reason": "Leaving"})
    assert res.json()["error"]["code"] == "cannot_suspend_staff"
    root, _ = staff(new_client, db, "root@outlogik.example.com", super_admin=True)
    assert root.post(f"{P}/users/{other.id}/suspend",
                     json={"reason": "Leaving"}).status_code == 200


def test_users_list_search(client, new_client, db):
    register(client, "olive@agency.example.com", org="Agency", name="Olive Owner")
    admin, _ = staff(new_client, db, "pa@outlogik.example.com", "platform_admin")
    rows = admin.get(f"{P}/users", params={"q": "olive"}).json()["items"]
    assert [r["email"] for r in rows] == ["olive@agency.example.com"]
    assert rows[0]["organizations"] == 1 and rows[0]["verified"] is False
