"""Public form endpoints for the website. No sign-in and no CSRF token (they never use the
session cookie); instead every request must come from the website's origin, passes spam checks,
and is rate-limited by IP address and by email address."""

from fastapi import APIRouter, Depends, Request, status

from app.core.config import get_settings
from app.core.errors import AppError, Forbidden
from app.core.rate_limit import hit
from app.core.request import client_ip, user_agent
from app.modules.auth.deps import DB
from app.modules.leads import service
from app.modules.leads.schemas import ConsultationIn, ContactIn, NewsletterIn, Received, TokenIn


def require_site_origin(request: Request) -> None:
    origin = (request.headers.get("origin") or "").rstrip("/")
    if origin not in get_settings().public_form_origins:
        raise Forbidden("Forms can only be sent from the Outlogik website.", code="bad_origin")


router = APIRouter(prefix="/public", tags=["public"], dependencies=[Depends(require_site_origin)])


def _limit(request: Request, email: str | None = None) -> None:
    s = get_settings()
    hit("public-form-ip", client_ip(request) or "unknown", s.rate_limit_public_form_ip)
    if email:
        hit("public-form-email", email, s.rate_limit_public_form_email)


@router.post("/leads/consultation", status_code=status.HTTP_201_CREATED, response_model=Received,
             summary="Book a free consultation")
def post_consultation(body: ConsultationIn, request: Request, db: DB) -> Received:
    _limit(request, body.email)
    service.create_consultation(db, body, client_ip(request), user_agent(request))
    return Received()


@router.post("/leads/contact", status_code=status.HTTP_201_CREATED, response_model=Received,
             summary="Send a message")
def post_contact(body: ContactIn, request: Request, db: DB) -> Received:
    _limit(request, body.email)
    service.create_contact(db, body, client_ip(request), user_agent(request))
    return Received()


@router.post("/newsletter", status_code=status.HTTP_202_ACCEPTED, response_model=Received,
             summary="Subscribe to the newsletter (sends a confirmation email)")
def post_newsletter(body: NewsletterIn, request: Request, db: DB) -> Received:
    _limit(request, body.email)
    service.subscribe(db, body, client_ip(request))
    return Received()


class InvalidLink(AppError):
    code = "invalid_link"


@router.post("/newsletter/confirm", response_model=Received, summary="Confirm a subscription")
def post_confirm(body: TokenIn, request: Request, db: DB) -> Received:
    _limit(request)
    if not service.confirm(db, body.token):
        raise InvalidLink("This confirmation link is invalid or has expired.")
    return Received()


@router.post("/newsletter/unsubscribe", response_model=Received, summary="Unsubscribe")
def post_unsubscribe(body: TokenIn, request: Request, db: DB) -> Received:
    _limit(request)
    if not service.unsubscribe(db, body.token):
        raise InvalidLink("This unsubscribe link is invalid.")
    return Received()
