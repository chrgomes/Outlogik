"""H1-3: built-in roles by account type, roles limited to assigned workspaces, and choosing a
member's workspaces."""

import pytest
from sqlalchemy import select

from app.models import AuditLog, Organization, Role, WorkspaceAssignment
from app.modules.rbac.service import sync_permissions
from tests.conftest import link_client, login, register, seed_client, signed_in_as, slug_of

API = "/api/v1/orgs"


@pytest.fixture
def agency(client):
    return slug_of(register(client, "owner@agency.example.com", org="Agency"))


def workspaces(c, slug):
    res = c.get(f"{API}/{slug}/workspaces")
    assert res.status_code == 200, res.text
    return {w["name"]: w["id"] for w in res.json()}


def members(c, slug):
    return {m["email"]: m for m in c.get(f"{API}/{slug}/members").json()["items"]}


def set_ws(c, slug, member_id, ids):
    return c.put(f"{API}/{slug}/members/{member_id}/workspaces", json={"workspace_ids": ids})


def roles(c, slug):
    return {r["system_key"] or r["name"]: r for r in c.get(f"{API}/{slug}/roles").json()["items"]}


# --- built-in roles by account type ---------------------------------------------------------

def test_agency_and_business_get_their_own_built_in_roles(client, new_client):
    agency = slug_of(register(client, "a@example.com", org="Agency"))
    names = {k: (r["name"], r["workspace_scope"]) for k, r in roles(client, agency).items()}
    assert names == {
        "owner": ("Owner", "all"), "admin": ("Administrator", "all"),
        "member": ("Marketing Manager", "all"), "viewer": ("Reporting Viewer", "all"),
        "account_manager": ("Account Manager", "assigned"),
        "client": ("Client Viewer", "assigned"),
    }
    other = new_client()
    business = slug_of(register(other, "b@example.com", org="Bakery", account_type="business"))
    assert set(roles(other, business)) == {"owner", "admin", "member", "viewer"}


def test_startup_sync_adds_new_roles_and_renames_old_ones(client, db, agency):
    org = db.scalar(select(Organization).where(Organization.slug == agency))
    # Make the organization look like it did before H1-3.
    db.query(Role).filter(Role.organization_id == org.id,
                          Role.system_key.in_(["viewer", "account_manager"])).delete()
    db.query(Role).filter(Role.organization_id == org.id, Role.system_key == "admin") \
        .update({"name": "Admin"})
    db.query(Role).filter(Role.organization_id == org.id, Role.system_key == "member") \
        .update({"name": "Team Member"})
    db.add(Role(organization_id=org.id, name="Marketing Manager", description="Custom"))
    db.commit()

    sync_permissions(db)
    db.expire_all()
    current = roles(client, agency)
    assert current["account_manager"]["name"] == "Account Manager"
    assert current["viewer"]["permissions"] == sorted(
        ["organization.read", "clients.read", "websites.read", "dashboard.read"])
    assert current["admin"]["name"] == "Administrator"
    # A custom role already has the new name, so the built-in role keeps its old one.
    assert current["member"]["name"] == "Team Member"


# --- members limited to assigned workspaces -------------------------------------------------

@pytest.fixture
def setup(client, new_client, db, agency):
    """An agency with two clients and a website in each, its own website, and an account
    manager assigned to the first client only."""
    a = client.post(f"{API}/{agency}/clients", json={"name": "Alpha"}).json()
    b = client.post(f"{API}/{agency}/clients", json={"name": "Beta"}).json()
    sites = {}
    for name, body in (("alpha", {"client_id": a["id"]}), ("beta", {"client_id": b["id"]}),
                       ("own", {})):
        res = client.post(f"{API}/{agency}/websites", json={"url": f"{name}.example.com", **body})
        sites[name] = res.json()["id"]
    browser, manager = signed_in_as(new_client, db, agency, "am@agency.example.com",
                                    "account_manager")
    ws = workspaces(client, agency)
    assert set_ws(client, agency, manager.id, [ws["Alpha"]]).status_code == 200
    return {"a": a, "b": b, "sites": sites, "browser": browser, "manager": manager, "ws": ws}


def test_account_manager_sees_only_assigned_workspaces(agency, setup):
    am = setup["browser"]
    assert set(workspaces(am, agency)) == {"Alpha"}
    clients = am.get(f"{API}/{agency}/clients").json()
    assert [c["name"] for c in clients["items"]] == ["Alpha"]
    sites = am.get(f"{API}/{agency}/websites").json()
    assert [s["domain"] for s in sites["items"]] == ["alpha.example.com"]
    dash = am.get(f"{API}/{agency}/dashboard").json()
    assert dash["clients"]["total"] == 1 and dash["websites"]["total"] == 1

    # Everything else is a 404, as if it didn't exist.
    assert am.get(f"{API}/{agency}/clients/{setup['b']['id']}").status_code == 404
    assert am.get(f"{API}/{agency}/websites/{setup['sites']['beta']}").status_code == 404
    assert am.get(f"{API}/{agency}/websites/{setup['sites']['own']}").status_code == 404
    assert am.get(f"{API}/{agency}/workspaces/{setup['ws']['Beta']}").status_code == 404
    assert am.patch(f"{API}/{agency}/websites/{setup['sites']['beta']}",
                    json={"name": "x"}).status_code == 404
    # It can work on its own client's sites, but can't move one to a workspace it can't see.
    assert am.patch(f"{API}/{agency}/websites/{setup['sites']['alpha']}",
                    json={"name": "Alpha site"}).status_code == 200
    assert am.patch(f"{API}/{agency}/websites/{setup['sites']['alpha']}",
                    json={"workspace_id": setup["ws"]["Beta"]}).status_code == 404


def test_assignments_change_what_a_member_sees_immediately(client, agency, setup):
    am, ws = setup["browser"], setup["ws"]
    res = set_ws(client, agency, setup["manager"].id, [ws["Alpha"], ws["Beta"], ws["Agency"]])
    assert [w["name"] for w in res.json()] == ["Agency", "Alpha", "Beta"]
    assert set(workspaces(am, agency)) == {"Agency", "Alpha", "Beta"}
    assert am.get(f"{API}/{agency}/websites").json()["total"] == 3

    set_ws(client, agency, setup["manager"].id, [])
    assert workspaces(am, agency) == {}
    assert am.get(f"{API}/{agency}/websites").json()["total"] == 0


def test_assignment_changes_are_audited(client, db, agency, setup):
    set_ws(client, agency, setup["manager"].id, [setup["ws"]["Beta"]])
    entry = db.scalars(select(AuditLog).where(AuditLog.action == "member.workspaces_update")
                       .order_by(AuditLog.created_at.desc())).first()
    assert entry.meta["added"] == ["Beta"] and entry.meta["removed"] == ["Alpha"]


def test_assignment_rules(client, new_client, db, agency, setup):
    ws = setup["ws"]
    m = members(client, agency)
    # A role that sees every workspace doesn't take assignments.
    owner = m["owner@agency.example.com"]
    _, manager2 = signed_in_as(new_client, db, agency, "mm@agency.example.com", "member")
    res = set_ws(client, agency, manager2.id, [ws["Alpha"]])
    assert res.status_code == 409 and res.json()["error"]["code"] == "role_sees_all"
    # Nobody changes their own.
    res = set_ws(client, agency, owner["id"], [])
    assert res.status_code in (403, 409)
    # Client Viewers only get client workspaces.
    _, viewer = signed_in_as(new_client, db, agency, "cv@client.example.com", "client")
    res = set_ws(client, agency, viewer.id, [ws["Agency"]])
    assert res.status_code == 409 and res.json()["error"]["code"] == "client_workspaces_only"
    assert set_ws(client, agency, viewer.id, [ws["Beta"]]).status_code == 200
    # Unknown workspaces are a 404.
    res = set_ws(client, agency, viewer.id, ["00000000-0000-0000-0000-000000000000"])
    assert res.status_code == 404


def test_another_organizations_workspaces_cant_be_assigned(client, new_client, agency, setup):
    other = new_client()
    rival = slug_of(register(other, "rival@example.com", org="Rival"))
    rival_ws = workspaces(other, rival)["Rival"]
    res = set_ws(client, agency, setup["manager"].id, [rival_ws])
    assert res.status_code == 404
    # And the rival can't touch our member's assignments.
    assert set_ws(other, rival, setup["manager"].id, [rival_ws]).status_code == 404
    assert other.get(f"{API}/{rival}/members/{setup['manager'].id}/workspaces").status_code == 404


def test_limited_member_can_only_hand_out_what_they_see(client, new_client, db, agency, setup):
    """A custom role limited to assigned workspaces, but allowed to manage the team."""
    res = client.post(f"{API}/{agency}/roles", json={
        "name": "Team Lead", "workspace_scope": "assigned",
        # Everything an Account Manager has, so it may manage one (no escalation).
        "permissions": ["organization.read", "members.read", "members.invite",
                        "members.update", "roles.read", "clients.read", "client_users.manage",
                        "websites.read", "websites.write", "dashboard.read"]})
    assert res.status_code == 201 and res.json()["workspace_scope"] == "assigned"
    lead_browser, lead = signed_in_as(new_client, db, agency, "lead@agency.example.com", "member")
    client.patch(f"{API}/{agency}/members/{lead.id}", json={"role_id": res.json()["id"]})
    ws = setup["ws"]
    set_ws(client, agency, lead.id, [ws["Alpha"]])
    set_ws(client, agency, setup["manager"].id, [ws["Alpha"], ws["Beta"]])

    # The lead sees only Alpha of the manager's workspaces.
    seen = lead_browser.get(f"{API}/{agency}/members/{setup['manager'].id}/workspaces").json()
    assert [w["name"] for w in seen] == ["Alpha"]
    # Can't add Beta (invisible to them)…
    res = set_ws(lead_browser, agency, setup["manager"].id, [ws["Alpha"], ws["Beta"]])
    assert res.status_code == 404
    # …and clearing their list leaves Beta, which they can't see, in place.
    assert set_ws(lead_browser, agency, setup["manager"].id, []).status_code == 200
    rows = db.scalars(select(WorkspaceAssignment.workspace_id).where(
        WorkspaceAssignment.member_id == setup["manager"].id)).all()
    assert {str(r) for r in rows} == {ws["Beta"]}
    # Nor can they invite someone with a role that sees every workspace.
    member_role = roles(client, agency)["member"]["id"]
    res = lead_browser.post(f"{API}/{agency}/invitations",
                            json={"email": "x@example.com", "role_id": member_role})
    assert res.status_code == 403 and res.json()["error"]["code"] == "role_exceeds_yours"


def test_custom_role_scope_can_change(client, new_client, db, agency, setup):
    res = client.post(f"{API}/{agency}/roles", json={
        "name": "Freelancer", "workspace_scope": "assigned",
        "permissions": ["organization.read", "clients.read", "websites.read"]})
    role = res.json()
    browser, member = signed_in_as(new_client, db, agency, "fl@example.com", "member")
    client.patch(f"{API}/{agency}/members/{member.id}", json={"role_id": role["id"]})
    assert workspaces(browser, agency) == {}

    res = client.patch(f"{API}/{agency}/roles/{role['id']}", json={"workspace_scope": "all"})
    assert res.json()["workspace_scope"] == "all"
    assert len(workspaces(browser, agency)) == 3


def test_client_portal_links_are_workspace_assignments(client, new_client, db, agency):
    c = seed_client(db, agency, "Gamma")
    browser, viewer = signed_in_as(new_client, db, agency, "cv@gamma.example.com", "client")
    res = client.post(f"{API}/{agency}/clients/{c.id}/users", json={"member_id": str(viewer.id)})
    assert res.status_code == 200 and [u["email"] for u in res.json()] == ["cv@gamma.example.com"]
    assert set(workspaces(browser, agency)) == {"Gamma"}
    listed = client.get(f"{API}/{agency}/clients/{c.id}").json()
    assert listed["portal_user_count"] == 1

    client.delete(f"{API}/{agency}/clients/{c.id}/users/{viewer.user_id}")
    assert workspaces(browser, agency) == {}


def test_memberships_report_the_role_scope(new_client, db, agency):
    c = seed_client(db, agency, "Delta")
    browser, viewer = signed_in_as(new_client, db, agency, "cv@delta.example.com", "client")
    link_client(db, viewer, c)
    me = browser.get("/api/v1/auth/me").json()
    assert me["memberships"][0]["workspace_scope"] == "assigned"
    assert login(new_client(), "owner@agency.example.com").json()["memberships"][0][
        "workspace_scope"] == "all"
