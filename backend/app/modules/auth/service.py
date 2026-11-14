import uuid
from datetime import datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import send_email
from app.core.errors import AppError, Conflict, Forbidden, Unauthorized
from app.core.models import utcnow
from app.core.security import (
    generate_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.modules.audit.service import record
from app.modules.auth.models import EmailVerificationToken, PasswordResetToken, UserSession
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.organizations.service import create_organization
from app.modules.rbac.models import Role
from app.modules.rbac.service import role_permission_codes
from app.modules.users.models import User

INVALID_CREDENTIALS = "Incorrect email or password."
INVALID_LINK = "This link is invalid or has expired."


# --- sessions -------------------------------------------------------------------------------

def create_session(db: Session, user: User, ip: str | None, ua: str | None) -> str:
    s = get_settings()
    token = generate_token()
    now = utcnow()
    db.add(UserSession(
        user_id=user.id, token_hash=hash_token(token), last_seen_at=now,
        expires_at=now + timedelta(hours=s.session_absolute_lifetime_hours), ip=ip, user_agent=ua,
    ))
    return token


def resolve_session(db: Session, token: str) -> tuple[UserSession, User] | None:
    """Return the live session and its user, or None. Expired sessions are deleted."""
    s = get_settings()
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(UserSession.token_hash == hash_token(token))
    ).first()
    if row is None:
        return None
    session, user = row
    now = utcnow()
    idle_limit = session.last_seen_at + timedelta(minutes=s.session_idle_timeout_minutes)
    if now >= session.expires_at or now >= idle_limit or not user.is_active:
        db.delete(session)
        db.commit()
        return None
    if (now - session.last_seen_at).total_seconds() >= s.session_touch_interval_seconds:
        session.last_seen_at = now
        db.commit()
    return session, user


def revoke_session(db: Session, session_id: uuid.UUID) -> None:
    db.execute(delete(UserSession).where(UserSession.id == session_id))


def revoke_all_sessions(db: Session, user_id: uuid.UUID) -> int:
    result = db.execute(delete(UserSession).where(UserSession.user_id == user_id))
    return result.rowcount or 0


# --- registration / login -------------------------------------------------------------------

def register(db: Session, *, email: str, password: str, full_name: str, organization_name: str,
             ip: str | None) -> tuple[User, Organization]:
    if get_settings().signup_mode != "open":
        raise Forbidden("Sign-up is by invitation only.", code="signup_disabled")
    if db.scalar(select(User.id).where(User.email == email)):
        raise Conflict("An account with this email already exists.", code="email_taken")

    user = User(email=email, password_hash=hash_password(password), full_name=full_name)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:  # lost a race with a concurrent sign-up for the same email
        db.rollback()
        raise Conflict("An account with this email already exists.", code="email_taken") from None
    org = create_organization(db, organization_name, owner=user)
    record(db, "auth.register", actor_user_id=user.id, target_type="user", target_id=user.id,
           ip=ip)
    record(db, "organization.create", actor_user_id=user.id, organization_id=org.id,
           target_type="organization", target_id=org.id, meta={"name": org.name}, ip=ip)
    send_verification_email(db, user)
    return user, org


def authenticate(db: Session, *, email: str, password: str, ip: str | None) -> User:
    user = db.scalar(select(User).where(User.email == email))
    ok = verify_password(user.password_hash if user else None, password)
    if not user or not ok or not user.is_active:
        if user:
            record(db, "auth.login_failed", actor_user_id=user.id, target_type="user",
                   target_id=user.id, ip=ip)
            db.commit()
        raise Unauthorized(INVALID_CREDENTIALS, code="invalid_credentials")
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = utcnow()
    record(db, "auth.login", actor_user_id=user.id, target_type="user", target_id=user.id, ip=ip)
    return user


# --- email verification ---------------------------------------------------------------------

def send_verification_email(db: Session, user: User) -> None:
    s = get_settings()
    token = generate_token()
    db.add(EmailVerificationToken(
        user_id=user.id, token_hash=hash_token(token),
        expires_at=utcnow() + timedelta(hours=s.email_verification_token_hours),
    ))
    link = f"{s.frontend_url}/verify-email?token={token}"
    send_email(
        user.email, f"Confirm your email for {s.app_name}",
        f"Hi {user.full_name},\n\nConfirm your email address by opening this link:\n{link}\n\n"
        f"The link expires in {s.email_verification_token_hours} hours.",
    )


def verify_email(db: Session, token: str, ip: str | None) -> User:
    row = _consume_token(db, EmailVerificationToken, token)
    user = db.get(User, row.user_id)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
        record(db, "auth.email_verified", actor_user_id=user.id, target_type="user",
               target_id=user.id, ip=ip)
    return user


# --- password reset -------------------------------------------------------------------------

def request_password_reset(db: Session, email: str, ip: str | None) -> None:
    """Always succeeds from the caller's point of view, so it never reveals which emails exist."""
    s = get_settings()
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active:
        return
    now = utcnow()
    # Only the newest link works.
    db.execute(update(PasswordResetToken)
               .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
               .values(used_at=now))
    token = generate_token()
    db.add(PasswordResetToken(
        user_id=user.id, token_hash=hash_token(token),
        expires_at=now + timedelta(minutes=s.password_reset_token_minutes),
    ))
    record(db, "auth.password_reset_requested", actor_user_id=user.id, target_type="user",
           target_id=user.id, ip=ip)
    db.commit()
    link = f"{s.frontend_url}/reset-password?token={token}"
    send_email(
        user.email, f"Reset your {s.app_name} password",
        f"Hi {user.full_name},\n\nSomeone asked to reset your password. To choose a new one, "
        f"open this link:\n{link}\n\nThe link expires in {s.password_reset_token_minutes} "
        "minutes. If you didn't ask for this, you can ignore this email.",
    )


def reset_password(db: Session, token: str, new_password: str, ip: str | None) -> User:
    row = _consume_token(db, PasswordResetToken, token)
    user = db.get(User, row.user_id)
    if not user.is_active:
        raise AppError(INVALID_LINK, code="invalid_token")
    user.password_hash = hash_password(new_password)
    revoked = revoke_all_sessions(db, user.id)
    record(db, "auth.password_reset", actor_user_id=user.id, target_type="user",
           target_id=user.id, meta={"sessions_revoked": revoked}, ip=ip)
    return user


def _consume_token(db: Session, model, token: str):
    row = db.scalar(select(model).where(model.token_hash == hash_token(token)).with_for_update())
    now: datetime = utcnow()
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise AppError(INVALID_LINK, code="invalid_token")
    row.used_at = now
    return row


# --- me -------------------------------------------------------------------------------------

def memberships_for(db: Session, user: User) -> list[dict]:
    rows = db.execute(
        select(OrganizationMember, Organization, Role)
        .join(Organization, Organization.id == OrganizationMember.organization_id)
        .join(Role, Role.id == OrganizationMember.role_id)
        .where(OrganizationMember.user_id == user.id, OrganizationMember.status == "active")
        .order_by(Organization.name)
    ).all()
    return [
        {
            "organization_id": org.id, "organization_slug": org.slug,
            "organization_name": org.name, "organization_status": org.status,
            "role_id": role.id, "role_name": role.name, "role_key": role.system_key,
            "permissions": sorted(role_permission_codes(db, role.id)),
        }
        for _, org, role in rows
    ]
