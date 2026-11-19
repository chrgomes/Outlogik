"""H1-3: an automated cross-organization attack on every organization route.

An owner of one organization (full permissions there) tries every route that takes an id,
using another organization's ids: in the URL, and in the request body. Every attempt must
fail, and the victim's data must be unchanged afterwards.

Routes are discovered from the app, so new routes are covered automatically. A route with a
kind of id this test doesn't know fails the test until the id is added to VICTIM_IDS.
"""

import re
from datetime import UTC, date, datetime

import pytest
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import select, text

from app.main import app
from app.models import (
    Audit,
    DataSource,
    Integration,
    Organization,
    Role,
    Workspace,
    WorkspaceReview,
)
from app.modules.integrations.crypto import encrypt
from tests.conftest import (
    link_client,
    register,
    seed_client,
    seed_member,
    slug_of,
    token_from_last_email,
)

PREFIX = "/api/v1/orgs/{org_slug}"
API = "/api/v1/orgs"


def id_routes():
    for rc in iter_route_contexts(app.routes):
        route = rc.original_route
        path = rc.path or ""
        if isinstance(route, APIRoute) and path.startswith(PREFIX) and path.count("{") > 1:
            for method in sorted(rc.methods):
                yield method, path


ROUTES = sorted(set(id_routes()), key=lambda r: (r[1], r[0]))

# Victim tables compared before and after the attack
SNAPSHOT = """
    SELECT 'client', c.id::text, c.name || c.status || coalesce(c.notes, '') FROM clients c
      WHERE c.organization_id = :org
    UNION ALL SELECT 'website', w.id::text, w.url || w.name || w.status || w.workspace_id::text
      FROM websites w WHERE w.organization_id = :org
    UNION ALL SELECT 'member', m.id::text, m.role_id::text || m.status FROM organization_members m
      WHERE m.organization_id = :org
    UNION ALL SELECT 'role', r.id::text, r.name || r.workspace_scope FROM roles r
      WHERE r.organization_id = :org
    UNION ALL SELECT 'invitation', i.id::text, coalesce(i.revoked_at::text, 'open') || i.token_hash
      FROM invitations i WHERE i.organization_id = :org
    UNION ALL SELECT 'assignment', a.id::text, a.workspace_id::text FROM workspace_assignments a
      WHERE a.organization_id = :org
    UNION ALL SELECT 'workspace', ws.id::text, ws.name FROM workspaces ws
      WHERE ws.organization_id = :org
    UNION ALL SELECT 'audit', a.id::text, a.status || a.pages_crawled FROM audits a
      WHERE a.organization_id = :org
    UNION ALL SELECT 'integration', i.id::text, i.status || i.refresh_token_encrypted
      FROM integrations i WHERE i.organization_id = :org
    UNION ALL SELECT 'data_source', d.id::text, d.external_id || d.sync_status FROM data_sources d
      WHERE d.organization_id = :org
    UNION ALL SELECT 'review', r.id::text, r.reviewed_at::text FROM workspace_reviews r
      WHERE r.organization_id = :org
    UNION ALL SELECT 'grant', g.id::text, g.status FROM workspace_grants g
      WHERE g.organization_id = :org OR g.agency_organization_id = :org
    ORDER BY 1, 2
"""


@pytest.fixture
def victim(client, db):
    """An agency (Acme) with one of everything, and a business (Bakery) that granted Acme
    access. Signed in as Acme's owner on `client`."""
    acme = slug_of(register(client, "owner@acme.example.com", org="Acme"))
    c = seed_client(db, acme, "Acme Client")
    site = client.post(f"{API}/{acme}/websites",
                       json={"client_id": str(c.id), "url": "acme-client.example.com"}).json()
    portal = seed_member(db, acme, "portal@acme-client.example.com", "client")
    link_client(db, portal, c)
    manager = seed_member(db, acme, "am@acme.example.com", "account_manager")
    role = client.post(f"{API}/{acme}/roles", json={
        "name": "Custom", "permissions": ["organization.read"]}).json()
    member_role = db.scalar(select(Role.id).join(Organization).where(
        Organization.slug == acme, Role.system_key == "member"))
    invitation = client.post(f"{API}/{acme}/invitations", json={
        "email": "invitee@example.com", "role_id": str(member_role)}).json()
    acme_id = db.scalar(select(Organization.id).where(Organization.slug == acme))
    workspace = db.scalar(select(Workspace.id).where(Workspace.client_id == c.id))
    own = db.scalar(select(Workspace.id).where(Workspace.organization_id == acme_id,
                                               Workspace.kind == "own"))
    audit = Audit(organization_id=acme_id, workspace_id=workspace, website_id=site["id"],
                  url=site["url"], page_limit=10, status="completed")
    db.add(audit)
    integration = Integration(organization_id=acme_id, workspace_id=workspace, provider="google",
                              refresh_token_encrypted=encrypt("victim-refresh-token"))
    db.add(integration)
    db.flush()
    db.add(DataSource(organization_id=acme_id, workspace_id=workspace,
                      integration_id=integration.id, kind="ga4", external_id="properties/1",
                      name="Victim", synced_through=date(2026, 11, 1)))
    db.add(WorkspaceReview(organization_id=acme_id, workspace_id=workspace,
                           reviewed_at=datetime(2026, 11, 1, tzinfo=UTC)))
    db.commit()
    return {"slug": acme, "org_id": acme_id, "client_id": str(c.id), "website_id": site["id"],
            "member_id": str(manager.id), "user_id": str(portal.user_id),
            "role_id": role["id"], "invitation_id": invitation["id"],
            "workspace_id": str(workspace), "own_workspace_id": str(own),
            "audit_id": str(audit.id)}


@pytest.fixture
def business_grant(new_client, db, victim, client):
    """Bakery (a business) shares its workspace with Acme."""
    bakery_browser = new_client()
    bakery = slug_of(register(bakery_browser, "owner@bakery.example.com", org="Bakery",
                              account_type="business"))
    grant = bakery_browser.post(f"{API}/{bakery}/access-grants",
                                json={"email": "owner@acme.example.com"}).json()
    token = token_from_last_email("/agency-access")
    client.post("/api/v1/access-grants/accept",
                json={"token": token, "organization_id": str(victim["org_id"])})
    bakery_id = db.scalar(select(Organization.id).where(Organization.slug == bakery))
    return {"slug": bakery, "org_id": bakery_id, "grant_id": grant["id"],
            "workspace_id": str(db.scalar(select(Workspace.id).where(
                Workspace.organization_id == bakery_id)))}


@pytest.fixture
def attacker(new_client, db):
    browser = new_client()
    slug = slug_of(register(browser, "owner@evil.example.com", org="Evil"))
    own = browser.get(f"{API}/{slug}/workspaces").json()[0]["id"]
    site = browser.post(f"{API}/{slug}/websites", json={"url": "evil.example.com"}).json()
    c = browser.post(f"{API}/{slug}/clients", json={"name": "Evil Client"}).json()
    portal = seed_member(db, slug, "portal@evil-client.example.com", "client")
    am = seed_member(db, slug, "am@evil.example.com", "account_manager")
    member_role = db.scalar(select(Role.id).join(Organization).where(
        Organization.slug == slug, Role.system_key == "member"))
    return {"browser": browser, "slug": slug, "own_workspace_id": own, "website_id": site["id"],
            "client_id": c["id"], "portal_member_id": str(portal.id), "member_id": str(am.id),
            "member_role_id": str(member_role)}


def snapshot(db, *org_ids):
    db.expire_all()
    return [db.execute(text(SNAPSHOT), {"org": o}).all() for o in org_ids]


def fill(path: str, ids: dict) -> str:
    def sub(m):
        name = m.group(1)
        assert name in ids, f"Add {name!r} to the cross-tenant test's victim ids"
        return str(ids[name])
    return re.sub(r"\{(\w+)\}", sub, path.removeprefix(PREFIX))


def valid_body(method: str, path: str, victim: dict) -> dict | None:
    """A body that passes validation, so the request reaches the data (and gets its 404)."""
    if method == "PUT":
        return {"workspace_ids": [victim["workspace_id"]]}
    if method == "POST":
        if path.endswith("/users"):
            return {"member_id": victim["member_id"]}
        return {"url": "attack.example.com"}
    if method == "PATCH":
        return {"status": "disabled"} if "/members/" in path else {"name": "Pwned"}
    return None


def test_routes_were_found():
    assert len(ROUTES) >= 25


def test_victim_ids_in_the_url_are_always_refused(db, victim, business_grant, attacker):
    ids = {**victim, "grant_id": business_grant["grant_id"]}
    before = snapshot(db, victim["org_id"], business_grant["org_id"])
    browser = attacker["browser"]
    checked = 0
    for method, path in ROUTES:
        body = valid_body(method, path, victim)
        url = f"{API}/{attacker['slug']}{fill(path, ids)}"
        res = browser.request(method, url, json=body)
        assert res.status_code == 404, f"{method} {path} -> {res.status_code} {res.text[:200]}"
        if "{workspace_id}" in path:
            # The business workspace shared with the victim is off limits too.
            shared = {**ids, "workspace_id": business_grant["workspace_id"]}
            res = browser.request(method, f"{API}/{attacker['slug']}{fill(path, shared)}",
                                  json=body)
            assert res.status_code == 404, f"{method} {path} (shared) -> {res.status_code}"
        checked += 1
    assert checked == len(ROUTES)
    assert snapshot(db, victim["org_id"], business_grant["org_id"]) == before


def test_victim_ids_in_the_body_are_always_refused(db, victim, attacker):
    """The attacker's own records in the URL, the victim's ids in the request."""
    before = snapshot(db, victim["org_id"])
    b, slug = attacker["browser"], attacker["slug"]
    base = f"{API}/{slug}"
    attempts = [
        ("POST", "/websites", {"client_id": victim["client_id"], "url": "x1.example.com"}),
        ("PATCH", f"/websites/{attacker['website_id']}", {"workspace_id": victim["workspace_id"]}),
        ("PATCH", f"/websites/{attacker['website_id']}", {"client_id": victim["client_id"]}),
        ("PATCH", f"/workspaces/{attacker['own_workspace_id']}/websites/{attacker['website_id']}",
         {"workspace_id": victim["own_workspace_id"]}),
        ("POST", "/invitations", {"email": "x@example.com", "role_id": victim["role_id"]}),
        ("PATCH", f"/members/{attacker['member_id']}", {"role_id": victim["role_id"]}),
        ("POST", f"/clients/{attacker['client_id']}/users", {"member_id": victim["member_id"]}),
        ("PUT", f"/members/{attacker['member_id']}/workspaces",
         {"workspace_ids": [victim["workspace_id"]]}),
        ("PUT", f"/members/{attacker['member_id']}/workspaces",
         {"workspace_ids": [victim["own_workspace_id"]]}),
    ]
    for method, path, body in attempts:
        res = b.request(method, base + path, json=body)
        assert res.status_code in (404, 422), f"{method} {path} {body} -> {res.status_code}"
        # The attacker's own website wasn't moved into the victim's workspace either.
    site = b.get(f"{base}/websites/{attacker['website_id']}").json()
    assert site["workspace_id"] == attacker["own_workspace_id"]
    assert snapshot(db, victim["org_id"]) == before


def test_victim_ids_through_a_portal_invitation(db, victim, attacker):
    """Inviting a client-portal user to the victim's client."""
    b, slug = attacker["browser"], attacker["slug"]
    client_role = db.scalar(select(Role.id).join(Organization).where(
        Organization.slug == slug, Role.system_key == "client"))
    res = b.post(f"{API}/{slug}/invitations", json={
        "email": "x@example.com", "role_id": str(client_role), "client_id": victim["client_id"]})
    assert res.status_code == 404
