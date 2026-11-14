from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core.models import utcnow
from app.models import Invitation, Website
from tests.conftest import (
    link_client,
    register,
    role_id,
    seed_client,
    seed_member,
    signed_in_as,
    slug_of,
)


@pytest.fixture
def acme(client):
    return slug_of(register(client, "owner@acme.example.com", org="Acme", name="Olive Owner"))


def dash(c, slug):
    res = c.get(f"/api/v1/orgs/{slug}/dashboard")
    assert res.status_code == 200, res.text
    return res.json()


def add_site(c, slug, client_id, url, **extra):
    res = c.post(f"/api/v1/orgs/{slug}/websites", json={"client_id": str(client_id), "url": url,
                                                         **extra})
    assert res.status_code == 201, res.text
    return res.json()


def test_new_organization_dashboard_is_all_zeros(client, acme):
    d = dash(client, acme)
    assert d["clients"] == {"total": 0, "active": 0, "archived": 0}
    assert d["websites"] == {"total": 0, "active": 0, "paused": 0, "archived": 0}
    assert d["team"] == {"members": 1, "client_users": 0, "pending_invitations": 0}
    # Creating the organization is the first activity.
    assert [a["action"] for a in d["recent_activity"]] == ["organization.create"]


def test_counts_reflect_real_records(client, acme, db):
    a = seed_client(db, acme, "A")
    b = seed_client(db, acme, "B")
    seed_client(db, acme, "Old")
    client.patch(f"/api/v1/orgs/{acme}/clients/{seed_client(db, acme, 'Gone').id}",
                 json={"status": "archived"})
    add_site(client, acme, a.id, "a.example.com")
    add_site(client, acme, a.id, "a2.example.com", status="paused")
    add_site(client, acme, b.id, "b.example.com")
    seed_member(db, acme, "tm@acme.example.com", "member")
    seed_member(db, acme, "off@acme.example.com", "member", status="disabled")
    seed_member(db, acme, "cu@client.example.com", "client")
    client.post(f"/api/v1/orgs/{acme}/invitations", json={
        "email": "new@example.com", "role_id": role_id(db, acme, "member")})
    client.post(f"/api/v1/orgs/{acme}/invitations", json={
        "email": "late@example.com", "role_id": role_id(db, acme, "member")})
    db.execute(update(Invitation).where(Invitation.email == "late@example.com")
               .values(expires_at=utcnow() - timedelta(days=1)))
    db.commit()

    d = dash(client, acme)
    assert d["clients"] == {"total": 4, "active": 3, "archived": 1}
    assert d["websites"] == {"total": 3, "active": 2, "paused": 1, "archived": 0}
    # Active only; client-portal users counted separately; expired invitations excluded.
    assert d["team"] == {"members": 2, "client_users": 1, "pending_invitations": 1}


def test_activity_is_newest_first_limited_and_named(client, acme, db):
    for i in range(12):
        client.post(f"/api/v1/orgs/{acme}/clients", json={"name": f"Client {i}"})
    activity = dash(client, acme)["recent_activity"]
    assert len(activity) == 10
    assert activity[0]["action"] == "client.create"
    assert activity[0]["meta"]["name"] == "Client 11"
    assert activity[0]["actor_name"] == "Olive Owner"
    times = [a["created_at"] for a in activity]
    assert times == sorted(times, reverse=True)


def test_team_member_sees_counts_but_not_activity(new_client, db, acme):
    browser, _ = signed_in_as(new_client, db, acme, "tm@acme.example.com", "member")
    d = dash(browser, acme)
    assert d["team"]["pending_invitations"] is None  # no members.invite
    assert d["team"]["members"] == 2
    assert d["recent_activity"] is None  # no audit.read


def test_client_user_sees_only_their_clients_and_no_team(client, new_client, db, acme):
    mine = seed_client(db, acme, "Mine")
    other = seed_client(db, acme, "Other")
    add_site(client, acme, mine.id, "mine.example.com")
    add_site(client, acme, other.id, "other.example.com")
    add_site(client, acme, other.id, "other2.example.com")
    browser, member = signed_in_as(new_client, db, acme, "cu@client.example.com", "client")
    link_client(db, member, mine)

    d = dash(browser, acme)
    assert d["clients"]["total"] == 1
    assert d["websites"]["total"] == 1
    assert d["team"] is None
    assert d["recent_activity"] is None


def test_dashboard_is_tenant_isolated(client, new_client, db, acme):
    globex_owner = new_client()
    globex = slug_of(register(globex_owner, "boss@globex.example.com", org="Globex"))
    theirs = seed_client(db, globex, "Their Client")
    add_site(globex_owner, globex, theirs.id, "their.example.com")
    globex_owner.post(f"/api/v1/orgs/{globex}/clients", json={"name": "Secret Project"})

    assert client.get(f"/api/v1/orgs/{globex}/dashboard").status_code == 404
    d = dash(client, acme)
    assert d["clients"]["total"] == 0 and d["websites"]["total"] == 0
    assert all("Secret" not in str(a["meta"]) for a in d["recent_activity"])
    assert db.query(Website).count() == 1
