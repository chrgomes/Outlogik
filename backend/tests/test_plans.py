"""H1-4: plans, trials and limits."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.cli import set_plan_cmd
from app.core.models import utcnow
from app.models import AuditLog, Organization, Role, Subscription
from app.modules.plans.service import set_plan
from tests.conftest import (
    PASSWORD,
    register,
    seed_member,
    signed_in_as,
    slug_of,
    token_from_last_email,
)

API = "/api/v1/orgs"


def org(db, slug):
    return db.scalar(select(Organization).where(Organization.slug == slug))


def plan(db, slug, key, **kw):
    set_plan(db, org(db, slug), key, **kw)
    db.commit()


def sub(c, slug):
    res = c.get(f"{API}/{slug}/subscription")
    assert res.status_code == 200, res.text
    return res.json()


def limit_of(body, key):
    return next(x for x in body["limits"] if x["key"] == key)


def add_site(c, slug, url):
    return c.post(f"{API}/{slug}/websites", json={"url": url})


@pytest.fixture
def business(client):
    return slug_of(register(client, "owner@bakery.example.com", org="Bakery",
                            account_type="business"))


@pytest.fixture
def agency(client):
    return slug_of(register(client, "owner@agency.example.com", org="Agency"))


# --- trials and the plan page ---------------------------------------------------------------

def test_new_accounts_get_a_14_day_trial_of_the_top_plan(client, new_client, db, business):
    body = sub(client, business)
    assert body["plan"]["key"] == "digital_professional" and body["status"] == "trialing"
    ends = org(db, business)
    s = db.scalar(select(Subscription).where(Subscription.organization_id == ends.id))
    assert timedelta(days=13, hours=23) < s.trial_ends_at - utcnow() <= timedelta(days=14)
    other = new_client()
    agency = slug_of(register(other, "a@agency.example.com", org="Agency"))
    assert sub(other, agency)["plan"]["key"] == "agency_business"


def test_plan_page_shows_prices_limits_and_usage(client, business):
    add_site(client, business, "bakery.example.com")
    body = sub(client, business)
    assert body["plan"]["monthly_price_cents"] == 9900
    assert body["plan"]["annual_price_cents"] == 95040 and body["plan"]["currency"] == "CAD"
    assert limit_of(body, "limits.websites") == {
        "key": "limits.websites", "label": "Websites (archived ones don't count)",
        "limit": 10, "used": 1}
    assert limit_of(body, "limits.team_members")["used"] == 1
    # Businesses have no clients, so the page doesn't mention them.
    assert [x["key"] for x in body["limits"]] == ["limits.websites", "limits.team_members"]


def test_only_owners_and_admins_see_the_plan(new_client, db, agency):
    for role in ("member", "client", "account_manager"):
        browser, _ = signed_in_as(new_client, db, agency, f"{role}@x.example.com", role)
        assert browser.get(f"{API}/{agency}/subscription").status_code == 403, role


# --- limits ---------------------------------------------------------------------------------

def test_website_limit(client, db, business):
    plan(db, business, "digital_starter")
    assert add_site(client, business, "one.example.com").status_code == 201
    res = add_site(client, business, "two.example.com")
    assert res.status_code == 403
    err = res.json()["error"]
    assert err["code"] == "plan_limit_reached"
    assert err["message"].startswith("The Digital Starter plan includes 1 website.")
    assert err["details"] == {"limit": "limits.websites", "allowed": 1, "used": 1}


def test_archived_websites_dont_count_but_restoring_does(client, db, business):
    plan(db, business, "digital_starter")
    first = add_site(client, business, "one.example.com").json()
    client.patch(f"{API}/{business}/websites/{first['id']}", json={"status": "archived"})
    assert add_site(client, business, "two.example.com").status_code == 201
    res = client.patch(f"{API}/{business}/websites/{first['id']}", json={"status": "active"})
    assert res.status_code == 403 and res.json()["error"]["code"] == "plan_limit_reached"
    # Other edits to the archived website still work.
    res = client.patch(f"{API}/{business}/websites/{first['id']}", json={"name": "Old site"})
    assert res.status_code == 200


def test_client_limit(client, db, agency):
    plan(db, agency, "agency_starter")
    ids = [client.post(f"{API}/{agency}/clients", json={"name": f"C{i}"}).json()["id"]
           for i in range(5)]
    res = client.post(f"{API}/{agency}/clients", json={"name": "C6"})
    assert res.status_code == 403
    assert "The Agency Starter plan includes 5 clients." in res.json()["error"]["message"]
    client.patch(f"{API}/{agency}/clients/{ids[0]}", json={"status": "archived"})
    assert client.post(f"{API}/{agency}/clients", json={"name": "C6"}).status_code == 201
    res = client.patch(f"{API}/{agency}/clients/{ids[0]}", json={"status": "active"})
    assert res.status_code == 403


def _role_id(db, slug, key):
    return str(db.scalar(select(Role.id).join(Organization).where(
        Organization.slug == slug, Role.system_key == key)))


def test_team_limit_counts_members_and_open_invitations(client, new_client, db, business):
    plan(db, business, "digital_starter")  # 2 team members: the owner and one more
    member_role = _role_id(db, business, "member")
    res = client.post(f"{API}/{business}/invitations",
                      json={"email": "one@example.com", "role_id": member_role})
    assert res.status_code == 201
    token = token_from_last_email("/accept-invite")
    res = client.post(f"{API}/{business}/invitations",
                      json={"email": "two@example.com", "role_id": member_role})
    assert res.status_code == 403
    assert "includes 2 team members" in res.json()["error"]["message"]
    # The counted invitation can still be accepted.
    res = new_client().post("/api/v1/auth/accept-invite", json={
        "token": token, "full_name": "One", "password": PASSWORD})
    assert res.status_code == 200
    assert limit_of(sub(client, business), "limits.team_members")["used"] == 2


def test_client_portal_users_dont_count(client, new_client, db, agency):
    plan(db, agency, "agency_starter")  # 3 team members
    for i in range(2):
        seed_member(db, agency, f"t{i}@agency.example.com", "member")
    c = client.post(f"{API}/{agency}/clients", json={"name": "Bakery"}).json()
    res = client.post(f"{API}/{agency}/invitations", json={
        "email": "jo@bakery.example.com", "role_id": _role_id(db, agency, "client"),
        "client_id": c["id"]})
    assert res.status_code == 201
    res = client.post(f"{API}/{agency}/invitations", json={
        "email": "x@agency.example.com", "role_id": _role_id(db, agency, "member")})
    assert res.status_code == 403


def test_restoring_a_disabled_member_counts(client, db, business):
    plan(db, business, "digital_starter")
    m = seed_member(db, business, "a@bakery.example.com", "member")
    client.patch(f"{API}/{business}/members/{m.id}", json={"status": "disabled"})
    seed_member(db, business, "b@bakery.example.com", "member")
    res = client.patch(f"{API}/{business}/members/{m.id}", json={"status": "active"})
    assert res.status_code == 403 and res.json()["error"]["code"] == "plan_limit_reached"


def test_unlimited_when_a_plan_doesnt_set_a_limit(client, db, business):
    from app.models import Plan, PlanEntitlement

    starter = db.scalar(select(Plan).where(Plan.key == "digital_starter"))
    row = db.scalar(select(PlanEntitlement).where(PlanEntitlement.plan_id == starter.id,
                                                  PlanEntitlement.key == "limits.websites"))
    row.value = None
    db.commit()
    try:
        plan(db, business, "digital_starter")
        for i in range(3):
            assert add_site(client, business, f"s{i}.example.com").status_code == 201
        assert limit_of(sub(client, business), "limits.websites")["limit"] is None
    finally:
        row.value = 1
        db.commit()


# --- trial ended and cancelled --------------------------------------------------------------

def test_after_the_trial_nothing_new_can_be_added_but_nothing_is_lost(client, db, business):
    site = add_site(client, business, "bakery.example.com").json()
    s = db.scalar(select(Subscription).where(Subscription.organization_id == org(db, business).id))
    s.trial_ends_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert sub(client, business)["status"] == "trial_ended"
    res = add_site(client, business, "new.example.com")
    assert res.status_code == 403 and res.json()["error"]["code"] == "trial_ended"
    assert "Everything you've added is kept" in res.json()["error"]["message"]
    # Reading and editing still work.
    assert client.get(f"{API}/{business}/websites").json()["total"] == 1
    res = client.patch(f"{API}/{business}/websites/{site['id']}", json={"name": "Shop"})
    assert res.status_code == 200


def test_cancelled_blocks_adding(client, db, business):
    plan(db, business, "digital_growth", status="cancelled")
    res = add_site(client, business, "x.example.com")
    assert res.status_code == 403 and res.json()["error"]["code"] == "subscription_cancelled"


# --- assigning plans ------------------------------------------------------------------------

def test_set_plan_records_the_change_and_checks_the_account_type(db, business):
    plan(db, business, "digital_growth", interval="annual")
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "subscription.change")).all()[-1]
    assert entry.meta["from"]["plan"] == "digital_professional"
    assert entry.meta["to"] == {"plan": "digital_growth", "status": "active",
                                "interval": "annual"}
    with pytest.raises(Exception, match="is for agency accounts"):
        set_plan(db, org(db, business), "agency_starter")


def test_cli_sets_a_plan(client, db, business, capsys):
    assert set_plan_cmd(business, "digital_starter", "active", "annual", None) == 0
    assert "Bakery: digital_starter (annual), active." in capsys.readouterr().out
    body = sub(client, business)
    assert body["plan"]["key"] == "digital_starter" and body["billing_interval"] == "annual"
    assert set_plan_cmd("nope", "digital_starter", "active", "monthly", None) == 1
    assert set_plan_cmd(business, "agency_starter", "active", "monthly", None) == 1


# --- shared workspaces ----------------------------------------------------------------------

def test_an_agency_adding_to_a_shared_workspace_uses_the_business_plan(
        client, new_client, db, business):
    plan(db, business, "digital_starter")
    add_site(client, business, "bakery.example.com")
    agency_browser = new_client()
    agency = slug_of(register(agency_browser, "owner@agency.example.com", org="Agency"))
    client.post(f"{API}/{business}/access-grants", json={"email": "owner@agency.example.com"})
    token = token_from_last_email("/agency-access")
    agency_browser.post("/api/v1/access-grants/accept",
                        json={"token": token, "organization_id": str(org(db, agency).id)})
    ws = next(w for w in agency_browser.get(f"{API}/{agency}/workspaces").json() if w["linked"])
    res = agency_browser.post(f"{API}/{agency}/workspaces/{ws['id']}/websites",
                              json={"url": "shop.bakery.example.com"})
    assert res.status_code == 403
    assert "Digital Starter" in res.json()["error"]["message"]
