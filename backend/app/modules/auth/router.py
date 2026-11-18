from fastapi import APIRouter, Request, Response, status

from app.core.config import get_settings
from app.core.errors import AppError, Unauthorized
from app.core.rate_limit import check_failures, clear_failures, hit, record_failure
from app.core.request import client_ip, user_agent
from app.modules.audit.service import record
from app.modules.auth import service
from app.modules.auth.cookies import clear_session_cookie, set_session_cookie
from app.modules.auth.deps import DB, CurrentAuth, CurrentUser, OptionalAuth
from app.modules.auth.schemas import (
    AcceptInviteIn,
    ForgotPasswordIn,
    InvitePreviewOut,
    LoginIn,
    MeOut,
    MessageOut,
    RegisterIn,
    ResetPasswordIn,
    TokenIn,
    UserOut,
)
from app.modules.leads import challenge
from app.modules.organizations import invitations
from app.platform import staff_role

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(db, user) -> MeOut:
    out = UserOut.model_validate(user)
    out.platform_role = staff_role(user)
    return MeOut(user=out, memberships=service.memberships_for(db, user))


@router.get("/csrf", status_code=status.HTTP_204_NO_CONTENT,
            summary="Ensure the CSRF cookie is set (call once when the app loads)")
def csrf() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/register", response_model=MeOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, request: Request, response: Response, db: DB) -> MeOut:
    ip = client_ip(request)
    hit("register", ip or "unknown", get_settings().rate_limit_register)
    user, _ = service.register(db, email=body.email, password=body.password,
                               full_name=body.full_name,
                               organization_name=body.organization_name,
                               account_type=body.account_type, ip=ip)
    token = service.create_session(db, user, ip, user_agent(request))
    db.commit()
    set_session_cookie(response, token)
    return _me(db, user)


def require_human(proof) -> None:
    """The invisible browser check the app's sign-in forms send (see leads/challenge.py)."""
    if get_settings().auth_challenge_required and challenge.problem(proof):
        raise AppError("Please try again.", code="bot_check_failed")


@router.post("/login", response_model=MeOut)
def login(body: LoginIn, request: Request, response: Response, db: DB) -> MeOut:
    s = get_settings()
    ip = client_ip(request) or "unknown"
    # Locked after too many recent failures, for this account or from this IP address.
    check_failures("login-fail:email", body.email, s.rate_limit_login_failures_email)
    check_failures("login-fail:ip", ip, s.rate_limit_login_failures_ip)
    try:
        require_human(body.pow)
        user = service.authenticate(db, email=body.email, password=body.password, ip=ip)
    except (Unauthorized, AppError):
        record_failure("login-fail:email", body.email, s.rate_limit_login_failures_email)
        record_failure("login-fail:ip", ip, s.rate_limit_login_failures_ip)
        raise
    clear_failures("login-fail:email", body.email)
    # Rotate: drop any session this browser already had.
    old = request.cookies.get(get_settings().session_cookie_name)
    if old and (resolved := service.resolve_session(db, old)):
        service.revoke_session(db, resolved[0].id)
    token = service.create_session(db, user, ip, user_agent(request))
    db.commit()
    set_session_cookie(response, token)
    return _me(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, db: DB) -> Response:
    token = request.cookies.get(get_settings().session_cookie_name)
    if token and (resolved := service.resolve_session(db, token)):
        session, user = resolved
        service.revoke_session(db, session.id)
        record(db, "auth.logout", actor_user_id=user.id, target_type="user", target_id=user.id,
               ip=client_ip(request))
        db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT,
             summary="Sign out of every device, including this one")
def logout_all(auth: CurrentAuth, request: Request, db: DB) -> Response:
    count = service.revoke_all_sessions(db, auth.user.id)
    record(db, "auth.logout_all", actor_user_id=auth.user.id, target_type="user",
           target_id=auth.user.id, meta={"sessions_revoked": count}, ip=client_ip(request))
    db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response)
    return response


@router.get("/me", response_model=MeOut)
def me(user: CurrentUser, db: DB) -> MeOut:
    return _me(db, user)


@router.post("/forgot-password", response_model=MessageOut,
             status_code=status.HTTP_202_ACCEPTED)
def forgot_password(body: ForgotPasswordIn, request: Request, db: DB) -> MessageOut:
    ip = client_ip(request)
    limit = get_settings().rate_limit_password_reset
    hit("reset:ip", ip or "unknown", (limit[0] * 4, limit[1]))
    hit("reset:email", body.email, limit)
    require_human(body.pow)
    service.request_password_reset(db, body.email, ip)
    return MessageOut(message="If an account exists for this email, we've sent a reset link.")


@router.post("/reset-password", response_model=MessageOut)
def reset_password(body: ResetPasswordIn, request: Request, db: DB) -> MessageOut:
    hit("reset-submit:ip", client_ip(request) or "unknown", get_settings().rate_limit_login)
    service.reset_password(db, body.token, body.password, client_ip(request))
    db.commit()
    return MessageOut(message="Your password has been changed. Please sign in.")


@router.post("/verify-email", response_model=MessageOut)
def verify_email(body: TokenIn, request: Request, db: DB) -> MessageOut:
    service.verify_email(db, body.token, client_ip(request))
    db.commit()
    return MessageOut(message="Your email address is confirmed.")


@router.post("/resend-verification", response_model=MessageOut,
             status_code=status.HTTP_202_ACCEPTED)
def resend_verification(user: CurrentUser, db: DB) -> MessageOut:
    if user.email_verified_at is None:
        hit("verify-resend", str(user.id), get_settings().rate_limit_password_reset)
        service.send_verification_email(db, user)
        db.commit()
    return MessageOut(message="If your email isn't confirmed yet, we've sent a new link.")


@router.post("/invitations/preview", response_model=InvitePreviewOut,
             summary="Show who invited whom to what, for the accept-invite page")
def preview_invitation(body: TokenIn, request: Request, db: DB) -> InvitePreviewOut:
    hit("invite:ip", client_ip(request) or "unknown", get_settings().rate_limit_login)
    found = invitations.find_open(db, body.token)
    return InvitePreviewOut(
        email=found.invitation.email, organization_name=found.organization.name,
        organization_slug=found.organization.slug,
        role_name=found.role.name, client_name=found.client.name if found.client else None,
        invited_by=found.inviter.full_name if found.inviter else None,
        account_exists=found.existing_user is not None,
        expires_at=found.invitation.expires_at,
    )


@router.post("/accept-invite", response_model=MeOut)
def accept_invite(body: AcceptInviteIn, request: Request, response: Response, db: DB,
                  auth: OptionalAuth) -> MeOut:
    ip = client_ip(request)
    hit("invite:ip", ip or "unknown", get_settings().rate_limit_login)
    require_human(body.pow)
    user, _, created = invitations.accept(
        db, body.token, current_user=auth.user if auth else None,
        full_name=body.full_name, password=body.password, ip=ip,
    )
    if created:
        token = service.create_session(db, user, ip, user_agent(request))
        set_session_cookie(response, token)
    db.commit()
    return _me(db, user)
