from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.core import email
from app.core.config import get_settings
from app.core.models import utcnow
from app.core.security import hash_token
from app.models import AuditLog, Organization, PasswordResetToken, Role, User, UserSession
from app.modules.rbac.catalogue import PERMISSIONS
from tests.conftest import PASSWORD, login, register, token_from_last_email

ME = "/api/v1/auth/me"


def actions(db) -> list[str]:
    return list(db.scalars(select(AuditLog.action).order_by(AuditLog.created_at)))


# --- registration ---------------------------------------------------------------------------

def test_register_creates_user_org_owner_membership_and_session(client, db):
    data = register(client, "Owner@Agency.example.com")

    assert data["user"]["email"] == "owner@agency.example.com"
    assert "password_hash" not in data["user"]
    [m] = data["memberships"]
    assert m["organization_name"] == "Acme Agency"
    assert m["organization_slug"] == "acme-agency"
    assert m["role_name"] == "Owner"
    assert m["role_key"] == "owner"
    assert set(m["permissions"]) == set(PERMISSIONS)

    # Logged in straight away, with an HTTP-only, Secure, SameSite=Lax cookie.
    cookie = next(c for c in client.cookies.jar if c.name == "outlogik_session")
    assert cookie.secure
    assert cookie.has_nonstandard_attr("HttpOnly")
    assert cookie.get_nonstandard_attr("SameSite").lower() == "lax"
    assert client.get(ME).status_code == 200

    assert {"auth.register", "organization.create"} <= set(actions(db))
    assert email.outbox[-1].to == "owner@agency.example.com"
    assert "verify-email?token=" in email.outbox[-1].body


def test_register_rejects_duplicate_email_case_insensitively(client, new_client):
    register(client, "dup@agency.example.com")
    res = new_client().post("/api/v1/auth/register", json={
        "email": "DUP@agency.example.com", "password": PASSWORD, "full_name": "X",
        "organization_name": "Other",
    })
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "email_taken"


def test_register_validates_input_with_consistent_errors(client):
    res = client.post("/api/v1/auth/register", json={
        "email": "not-an-email", "password": "short", "full_name": "", "organization_name": "A",
    })
    assert res.status_code == 422
    err = res.json()["error"]
    assert err["code"] == "validation_error"
    assert {d["field"] for d in err["details"]} == {"email", "password", "full_name"}


def test_same_org_name_gets_unique_slug(client, new_client):
    a = register(client, "a@example.com", org="Same Name")
    b = register(new_client(), "b@example.com", org="Same Name")
    slug_a = a["memberships"][0]["organization_slug"]
    slug_b = b["memberships"][0]["organization_slug"]
    assert slug_a == "same-name"
    assert slug_b != slug_a and slug_b.startswith("same-name-")


def test_register_disabled_when_invite_only(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "signup_mode", "invite_only")
    res = client.post("/api/v1/auth/register", json={
        "email": "x@example.com", "password": PASSWORD, "full_name": "X", "organization_name": "X",
    })
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "signup_disabled"


# --- login / sessions -----------------------------------------------------------------------

def test_login_and_me(client, new_client):
    register(client, "user@example.com")
    browser = new_client()
    assert browser.get(ME).status_code == 401
    res = login(browser, "USER@example.com")
    assert res.status_code == 200
    assert browser.get(ME).json()["user"]["email"] == "user@example.com"


@pytest.mark.parametrize("email_addr,password", [
    ("user@example.com", "wrong password!"),
    ("nobody@example.com", PASSWORD),
])
def test_login_failure_is_generic(client, new_client, db, email_addr, password):
    register(client, "user@example.com")
    res = login(new_client(), email_addr, password)
    assert res.status_code == 401
    assert res.json()["error"] == {
        "code": "invalid_credentials", "message": "Incorrect email or password.", "details": None,
    }


def test_failed_login_for_existing_user_is_audited(client, new_client, db):
    register(client, "user@example.com")
    login(new_client(), "user@example.com", "wrong password!")
    assert "auth.login_failed" in actions(db)


def test_session_token_is_stored_only_as_hash(client, db):
    register(client)
    token = client.cookies.get("outlogik_session")
    hashes = list(db.scalars(select(UserSession.token_hash)))
    assert token not in hashes
    assert hash_token(token) in hashes


def test_login_rotates_existing_session(client, db):
    register(client, "user@example.com")
    old = client.cookies.get("outlogik_session")
    assert login(client, "user@example.com").status_code == 200
    new = client.cookies.get("outlogik_session")
    assert new != old
    assert db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(old))) is None


def test_logout_revokes_session_and_clears_cookie(client, db):
    register(client)
    token = client.cookies.get("outlogik_session")
    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.cookies.get("outlogik_session") is None
    assert db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(token))) is None
    # Replaying the old cookie does not work.
    client.cookies.set("outlogik_session", token)
    assert client.get(ME).status_code == 401
    assert "auth.logout" in actions(db)


def test_logout_all_revokes_every_device(client, new_client, db):
    register(client, "user@example.com")
    laptop, phone = new_client(), new_client()
    login(laptop, "user@example.com")
    login(phone, "user@example.com")
    assert phone.post("/api/v1/auth/logout-all").status_code == 204
    for browser in (client, laptop, phone):
        assert browser.get(ME).status_code == 401
    assert "auth.logout_all" in actions(db)


def test_idle_timeout_expires_session(client, db):
    register(client)
    idle = timedelta(minutes=get_settings().session_idle_timeout_minutes + 1)
    db.execute(update(UserSession).values(last_seen_at=utcnow() - idle))
    db.commit()
    res = client.get(ME)
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "session_expired"
    assert db.scalar(select(UserSession)) is None


def test_absolute_lifetime_expires_active_session(client, db):
    register(client)
    db.execute(update(UserSession).values(expires_at=utcnow() - timedelta(seconds=1)))
    db.commit()
    assert client.get(ME).status_code == 401


def test_activity_extends_idle_window(client, db):
    register(client)
    earlier = utcnow() - timedelta(minutes=30)
    db.execute(update(UserSession).values(last_seen_at=earlier))
    db.commit()
    assert client.get(ME).status_code == 200
    db.expire_all()
    assert db.scalar(select(UserSession.last_seen_at)) > earlier


def test_deactivated_user_loses_access(client, new_client, db):
    register(client, "user@example.com")
    db.execute(update(User).values(is_active=False))
    db.commit()
    assert client.get(ME).status_code == 401
    assert login(new_client(), "user@example.com").status_code == 401


# --- CSRF -----------------------------------------------------------------------------------

def test_state_changing_request_requires_csrf_header(client):
    register(client)
    header = get_settings().csrf_header_name
    good = client.headers.pop(header)
    res = client.post("/api/v1/auth/logout")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "csrf_failed"

    client.headers[header] = "forged-value"
    assert client.post("/api/v1/auth/logout").status_code == 403

    client.headers[header] = good
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_csrf_cookie_is_readable_by_javascript(client):
    cookie = next(c for c in client.cookies.jar if c.name == get_settings().csrf_cookie_name)
    assert not cookie.has_nonstandard_attr("HttpOnly")


# --- rate limiting --------------------------------------------------------------------------

def test_login_locks_an_account_after_5_failed_attempts(client, new_client):
    register(client, "user@example.com")
    attacker = new_client()
    max_failures = get_settings().rate_limit_login_failures_email[0]
    assert max_failures == 5
    for _ in range(max_failures):
        assert login(attacker, "user@example.com", "wrong password!").status_code == 401
    # Locked now, even with the right password, until the 15-minute window passes.
    res = login(attacker, "user@example.com", PASSWORD)
    assert res.status_code == 429
    assert res.json()["error"]["code"] == "rate_limited"
    assert 0 < int(res.headers["Retry-After"]) <= 900


def test_successful_sign_ins_do_not_count_and_clear_failures(client, new_client):
    register(client, "user@example.com")
    browser = new_client()
    for _ in range(4):
        assert login(browser, "user@example.com", "wrong password!").status_code == 401
    assert login(browser, "user@example.com", PASSWORD).status_code == 200  # clears the count
    for _ in range(4):
        assert login(browser, "user@example.com", "wrong password!").status_code == 401
    # Signing in often is fine.
    for _ in range(12):
        assert login(new_client(), "user@example.com", PASSWORD).status_code == 200


def test_one_ip_address_guessing_many_accounts_is_locked(new_client):
    attacker = new_client()
    max_failures = get_settings().rate_limit_login_failures_ip[0]
    for i in range(max_failures):
        assert login(attacker, f"victim{i}@example.com", "guess").status_code == 401
    assert login(attacker, "another@example.com", "guess").status_code == 429


def test_sign_in_forms_need_the_browser_check(client, new_client, monkeypatch):
    import hashlib

    register(client, "user@example.com")
    monkeypatch.setattr(get_settings(), "auth_challenge_required", True)
    monkeypatch.setattr(get_settings(), "form_challenge_max_number", 500)
    browser = new_client()
    res = login(browser, "user@example.com", PASSWORD)  # no proof
    assert res.status_code == 400 and res.json()["error"]["code"] == "bot_check_failed"
    res = browser.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    assert res.status_code == 400

    ch = browser.get("/api/v1/public/challenge").json()
    number = next(n for n in range(501) if hashlib.sha256(
        f"{ch['salt']}{n}".encode()).hexdigest() == ch["challenge"])
    proof = {**{k: ch[k] for k in ("algorithm", "challenge", "salt", "signature")},
             "number": number}
    res = browser.post("/api/v1/auth/login", json={"email": "user@example.com",
                                                   "password": PASSWORD, "pow": proof})
    assert res.status_code == 200
    # Each check works once.
    res = new_client().post("/api/v1/auth/login", json={"email": "user@example.com",
                                                        "password": PASSWORD, "pow": proof})
    assert res.status_code == 400


# --- password reset -------------------------------------------------------------------------

def test_forgot_password_does_not_reveal_unknown_emails(client):
    res = client.post("/api/v1/auth/forgot-password", json={"email": "ghost@example.com"})
    assert res.status_code == 202
    assert email.outbox == []


def test_password_reset_flow(client, new_client, db):
    register(client, "user@example.com")
    other_device = new_client()
    login(other_device, "user@example.com")

    browser = new_client()
    res = browser.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    assert res.status_code == 202
    token = token_from_last_email("/reset-password")
    assert db.scalar(select(PasswordResetToken.token_hash)) == hash_token(token)

    new_password = "a brand new password"
    res = browser.post("/api/v1/auth/reset-password",
                       json={"token": token, "password": new_password})
    assert res.status_code == 200

    # Every existing session is signed out.
    assert client.get(ME).status_code == 401
    assert other_device.get(ME).status_code == 401
    assert login(browser, "user@example.com", PASSWORD).status_code == 401
    assert login(browser, "user@example.com", new_password).status_code == 200

    # The link works once.
    res = browser.post("/api/v1/auth/reset-password", json={"token": token, "password": PASSWORD})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "invalid_token"
    assert {"auth.password_reset_requested", "auth.password_reset"} <= set(actions(db))


def test_only_newest_reset_link_works(client):
    register(client, "user@example.com")
    client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    first = token_from_last_email("/reset-password")
    client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    second = token_from_last_email("/reset-password")
    body = {"password": "another long password"}
    assert client.post("/api/v1/auth/reset-password",
                       json={"token": first, **body}).status_code == 400
    assert client.post("/api/v1/auth/reset-password",
                       json={"token": second, **body}).status_code == 200


def test_expired_reset_link_is_rejected(client, db):
    register(client, "user@example.com")
    client.post("/api/v1/auth/forgot-password", json={"email": "user@example.com"})
    token = token_from_last_email("/reset-password")
    db.execute(update(PasswordResetToken).values(expires_at=utcnow() - timedelta(seconds=1)))
    db.commit()
    res = client.post("/api/v1/auth/reset-password",
                      json={"token": token, "password": "another long password"})
    assert res.status_code == 400


# --- email verification ---------------------------------------------------------------------

def test_email_verification(client, db):
    register(client, "user@example.com")
    token = token_from_last_email("/verify-email")
    assert client.get(ME).json()["user"]["email_verified_at"] is None
    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 200
    assert client.get(ME).json()["user"]["email_verified_at"] is not None
    assert client.post("/api/v1/auth/verify-email", json={"token": token}).status_code == 400
    assert "auth.email_verified" in actions(db)


def test_resend_verification_requires_login(new_client):
    res = new_client().post("/api/v1/auth/resend-verification")
    assert res.status_code == 401


def test_new_org_gets_default_roles(client, db):
    register(client)
    org = db.scalar(select(Organization))
    names = set(db.scalars(select(Role.name).where(Role.organization_id == org.id)))
    assert names == {"Owner", "Administrator", "Marketing Manager", "Account Manager",
                     "Reporting Viewer", "Client Viewer"}
