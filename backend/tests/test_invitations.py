from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core import email
from app.core.config import get_settings
from app.core.models import utcnow
from app.core.security import hash_token
from app.models import AuditLog, ClientUser, Invitation, User
from tests.conftest import (
    PASSWORD,
    login,
    register,
    role_id,
    seed_client,
    seed_member,
    slug_of,
    token_from_last_email,
)

ACCEPT = "/api/v1/auth/accept-invite"
PREVIEW = "/api/v1/auth/invitations/preview"


@pytest.fixture
def acme(client):
    return slug_of(register(client, "owner@acme.example.com", org="Acme", name="Olive Owner"))


def invite(client, db, slug, email_addr, role_key="member", **extra):
    return client.post(f"/api/v1/orgs/{slug}/invitations", json={
        "email": email_addr, "role_id": role_id(db, slug, role_key), **extra,
    })


def actions(db):
    return set(db.scalars(select(AuditLog.action)))


# --- sending --------------------------------------------------------------------------------

def test_invite_sends_email_and_stores_hashed_token(client, db, acme):
    res = invite(client, db, acme, "New.Person@example.com")
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "new.person@example.com"
    assert body["role"]["name"] == "Team Member"
    assert body["status"] == "pending"
    assert body["invited_by"] == "Olive Owner"

    sent = email.outbox[-1]
    assert sent.to == "new.person@example.com"
    assert "Olive Owner invited you to Acme" in sent.subject
    token = token_from_last_email("/accept-invite")
    assert db.scalar(select(Invitation.token_hash)) == hash_token(token)
    assert "invitation.create" in actions(db)


def test_list_and_revoke_invitations(client, db, acme):
    inv = invite(client, db, acme, "a@example.com").json()
    invite(client, db, acme, "b@example.com")
    listed = client.get(f"/api/v1/orgs/{acme}/invitations").json()
    assert listed["total"] == 2

    assert client.delete(f"/api/v1/orgs/{acme}/invitations/{inv['id']}").status_code == 204
    assert client.get(f"/api/v1/orgs/{acme}/invitations").json()["total"] == 1
    assert client.delete(f"/api/v1/orgs/{acme}/invitations/{inv['id']}").status_code == 404
    assert "invitation.revoke" in actions(db)


def test_revoked_invitation_cannot_be_accepted(client, new_client, db, acme):
    inv = invite(client, db, acme, "a@example.com").json()
    token = token_from_last_email("/accept-invite")
    client.delete(f"/api/v1/orgs/{acme}/invitations/{inv['id']}")
    res = new_client().post(ACCEPT, json={"token": token, "full_name": "A", "password": PASSWORD})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_token"


def test_reinviting_replaces_the_previous_link(client, new_client, db, acme):
    invite(client, db, acme, "a@example.com")
    first = token_from_last_email("/accept-invite")
    invite(client, db, acme, "a@example.com", role_key="admin")
    second = token_from_last_email("/accept-invite")
    assert client.get(f"/api/v1/orgs/{acme}/invitations").json()["total"] == 1

    browser = new_client()
    body = {"full_name": "A", "password": PASSWORD}
    assert browser.post(ACCEPT, json={"token": first, **body}).status_code == 400
    assert browser.post(ACCEPT, json={"token": second, **body}).status_code == 200


def test_resend_issues_a_new_link(client, new_client, db, acme):
    inv = invite(client, db, acme, "a@example.com").json()
    old = token_from_last_email("/accept-invite")
    res = client.post(f"/api/v1/orgs/{acme}/invitations/{inv['id']}/resend")
    assert res.status_code == 200
    new = token_from_last_email("/accept-invite")
    assert new != old
    browser = new_client()
    assert browser.post(PREVIEW, json={"token": old}).status_code == 400
    assert browser.post(PREVIEW, json={"token": new}).status_code == 200


def test_cannot_invite_existing_member(client, db, acme):
    seed_member(db, acme, "bob@acme.example.com", "member")
    res = invite(client, db, acme, "BOB@acme.example.com")
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "already_member"


def test_only_owner_can_invite_owner(client, new_client, db, acme):
    seed_member(db, acme, "admin@acme.example.com", "admin")
    admin = new_client()
    login(admin, "admin@acme.example.com")
    res = invite(admin, db, acme, "x@example.com", role_key="owner")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "owner_required"
    assert invite(client, db, acme, "x@example.com", role_key="owner").status_code == 201


def test_team_member_cannot_invite(new_client, db, acme):
    seed_member(db, acme, "tm@acme.example.com", "member")
    browser = new_client()
    login(browser, "tm@acme.example.com")
    assert invite(browser, db, acme, "x@example.com").status_code == 403
    assert browser.get(f"/api/v1/orgs/{acme}/invitations").status_code == 403


def test_client_invitations_need_a_client(client, db, acme):
    res = invite(client, db, acme, "cu@client.example.com", role_key="client")
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "client_required"

    c = seed_client(db, acme)
    res = invite(client, db, acme, "tm@example.com", role_key="member", client_id=str(c.id))
    assert res.json()["error"]["code"] == "client_not_allowed"


# --- accepting ------------------------------------------------------------------------------

def test_preview_shows_invitation_details(client, new_client, db, acme):
    invite(client, db, acme, "new@example.com")
    token = token_from_last_email("/accept-invite")
    res = new_client().post(PREVIEW, json={"token": token})
    assert res.status_code == 200
    assert res.json() | {"expires_at": None} == {
        "email": "new@example.com", "organization_name": "Acme", "organization_slug": acme,
        "role_name": "Team Member",
        "client_name": None, "invited_by": "Olive Owner", "account_exists": False,
        "expires_at": None,
    }


def test_new_user_accepts_and_is_signed_in(client, new_client, db, acme):
    invite(client, db, acme, "new@example.com")
    token = token_from_last_email("/accept-invite")
    browser = new_client()

    res = browser.post(ACCEPT, json={"token": token})
    assert res.status_code == 422
    assert {d["field"] for d in res.json()["error"]["details"]} == {"full_name", "password"}

    res = browser.post(ACCEPT, json={"token": token, "full_name": "Nina New",
                                     "password": PASSWORD})
    assert res.status_code == 200, res.text
    me = res.json()
    assert me["user"]["email_verified_at"] is not None
    assert [(m["organization_slug"], m["role_name"]) for m in me["memberships"]] == [
        (acme, "Team Member")]
    assert browser.get(f"/api/v1/orgs/{acme}").status_code == 200

    # Single use.
    again = new_client().post(ACCEPT, json={"token": token, "full_name": "X",
                                            "password": PASSWORD})
    assert again.status_code == 400
    assert {"invitation.accept", "auth.register"} <= actions(db)


def test_existing_user_must_sign_in_as_the_invited_email(client, new_client, db, acme):
    globex_owner = new_client()
    register(globex_owner, "boss@globex.example.com", org="Globex")
    invite(client, db, acme, "boss@globex.example.com", role_key="admin")
    token = token_from_last_email("/accept-invite")

    anonymous = new_client()
    assert anonymous.post(PREVIEW, json={"token": token}).json()["account_exists"] is True
    res = anonymous.post(ACCEPT, json={"token": token})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "login_required"

    # Signed in as someone else: refused, and no account is created for them.
    stranger = new_client()
    register(stranger, "stranger@example.com", org="Stranger")
    res = stranger.post(ACCEPT, json={"token": token})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "wrong_account"

    res = globex_owner.post(ACCEPT, json={"token": token})
    assert res.status_code == 200
    roles = {m["organization_name"]: m["role_name"] for m in res.json()["memberships"]}
    assert roles == {"Acme": "Admin", "Globex": "Owner"}


def test_signed_in_user_cannot_create_account_for_another_email(client, new_client, db, acme):
    invite(client, db, acme, "new@example.com")
    token = token_from_last_email("/accept-invite")
    other = new_client()
    register(other, "other@example.com", org="Other")
    res = other.post(ACCEPT, json={"token": token, "full_name": "X", "password": PASSWORD})
    assert res.status_code == 403
    assert db.scalar(select(User).where(User.email == "new@example.com")) is None


def test_client_invitation_links_user_to_client(client, new_client, db, acme):
    c = seed_client(db, acme, "Bakery Ltd")
    res = invite(client, db, acme, "cu@bakery.example.com", role_key="client",
                 client_id=str(c.id))
    assert res.json()["client_name"] == "Bakery Ltd"
    token = token_from_last_email("/accept-invite")
    assert "Bakery Ltd client portal" in email.outbox[-1].body

    res = new_client().post(ACCEPT, json={"token": token, "full_name": "Cleo",
                                          "password": PASSWORD})
    assert res.status_code == 200
    assert res.json()["memberships"][0]["role_name"] == "Client"
    link = db.scalar(select(ClientUser))
    assert link.client_id == c.id


def test_expired_invitation_is_rejected(client, new_client, db, acme):
    invite(client, db, acme, "new@example.com")
    token = token_from_last_email("/accept-invite")
    db.execute(update(Invitation).values(expires_at=utcnow() - timedelta(seconds=1)))
    db.commit()
    assert client.get(f"/api/v1/orgs/{acme}/invitations").json()["items"][0]["status"] == \
        "expired"
    res = new_client().post(ACCEPT, json={"token": token, "full_name": "N",
                                          "password": PASSWORD})
    assert res.status_code == 400


def test_invitations_work_when_signup_is_invite_only(client, new_client, db, acme, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_mode", "invite_only")
    invite(client, db, acme, "new@example.com")
    token = token_from_last_email("/accept-invite")
    res = new_client().post(ACCEPT, json={"token": token, "full_name": "N",
                                          "password": PASSWORD})
    assert res.status_code == 200


# --- tenant isolation -----------------------------------------------------------------------

def test_cannot_use_or_manage_another_orgs_invitations(client, new_client, db, acme):
    globex_owner = new_client()
    globex = slug_of(register(globex_owner, "boss@globex.example.com", org="Globex"))
    theirs = invite(globex_owner, db, globex, "target@example.com").json()
    their_client = seed_client(db, globex, "Their Client")

    # Their invitations, via their slug or ours.
    assert client.get(f"/api/v1/orgs/{globex}/invitations").status_code == 404
    assert client.delete(f"/api/v1/orgs/{acme}/invitations/{theirs['id']}").status_code == 404
    assert client.post(
        f"/api/v1/orgs/{acme}/invitations/{theirs['id']}/resend").status_code == 404

    # Inviting into our org with their role or their client.
    res = client.post(f"/api/v1/orgs/{acme}/invitations", json={
        "email": "x@example.com", "role_id": role_id(db, globex, "admin")})
    assert res.status_code == 404
    res = invite(client, db, acme, "x@example.com", role_key="client",
                 client_id=str(their_client.id))
    assert res.status_code == 404

    db.expire_all()
    assert db.get(Invitation, theirs["id"]).revoked_at is None
    assert db.scalar(select(Invitation).where(Invitation.email == "x@example.com")) is None
