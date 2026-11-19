"""Connecting a workspace to Google, choosing what to sync, and disconnecting.

The sign-in round trip:
1. `start()` stores a one-time state (who, which organization and workspace, the PKCE
   verifier) in Redis for 10 minutes and returns Google's consent address.
2. Google sends the person back to `finish()`, which checks the state belongs to the same
   signed-in person, still allowed to manage that workspace, exchanges the code, and stores
   the refresh token encrypted.
"""

import json
import secrets
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, Conflict, NotFound
from app.core.redis import get_redis
from app.jobs.service import enqueue
from app.modules.audit.service import record
from app.modules.integrations import google
from app.modules.integrations.crypto import decrypt, encrypt
from app.modules.integrations.models import DataSource, Integration
from app.modules.users.models import User
from app.modules.workspaces.models import Workspace
from app.tenancy.context import OrgContext, load_org_context

STATE_TTL = 600
NOT_SET_UP = ("Google isn't set up on this Outlogik server yet, so it can't be connected. "
              "Outlogik's team is working on it.")


def _record_both(db: Session, ctx: OrgContext, ws: Workspace, action: str, meta: dict) -> None:
    for org_id in {ctx.org.id, ws.organization_id}:
        record(db, action, actor_user_id=ctx.user.id, organization_id=org_id,
               target_type="workspace", target_id=ws.id, meta=meta)


def integration_for(db: Session, ws: Workspace) -> Integration | None:
    return db.scalar(select(Integration).where(Integration.workspace_id == ws.id,
                                               Integration.provider == "google"))


def sources_for(db: Session, integration: Integration | None) -> list[DataSource]:
    if integration is None:
        return []
    return list(db.scalars(select(DataSource).where(DataSource.integration_id == integration.id)
                           .order_by(DataSource.kind)))


# --- connecting -----------------------------------------------------------------------------

def start(ctx: OrgContext, ws: Workspace) -> str:
    if not google.configured():
        raise Conflict(NOT_SET_UP, code="google_not_configured")
    verifier, challenge = google.pkce()
    state = secrets.token_urlsafe(32)
    get_redis().set(f"oauth:google:{state}", ex=STATE_TTL, value=json.dumps({
        "user_id": str(ctx.user.id), "org_slug": ctx.org.slug, "workspace_id": str(ws.id),
        "verifier": verifier}))
    return google.authorization_url(state, challenge)


def cancel(state: str) -> str | None:
    """Forget a sign-in the person cancelled; returns its organization slug, if known."""
    raw = get_redis().getdel(f"oauth:google:{state}") if state else None
    return json.loads(raw)["org_slug"] if raw else None


def peek(state: str) -> str | None:
    raw = get_redis().get(f"oauth:google:{state}") if state else None
    return json.loads(raw)["org_slug"] if raw else None


def finish(db: Session, user: User, state: str, code: str) -> tuple[str, Workspace]:
    """Returns the organization slug and workspace, for sending the person back."""
    raw = get_redis().getdel(f"oauth:google:{state}") if state else None
    if raw is None:
        raise AppError("This Google sign-in has expired. Start again from Integrations.",
                       code="oauth_state_invalid")
    saved = json.loads(raw)
    if saved["user_id"] != str(user.id):
        raise AppError("This Google sign-in was started by someone else.",
                       code="oauth_state_invalid")
    # Still a member, still allowed to manage integrations, still able to see the workspace.
    ctx = load_org_context(db, user, saved["org_slug"])
    if not ctx.can("integrations.manage"):
        raise NotFound("Workspace not found.")
    from app.modules.workspaces.service import ensure_writable, get_workspace

    ws = get_workspace(db, ctx, uuid.UUID(saved["workspace_id"]))
    ensure_writable(ctx, ws.id)

    tokens = google.exchange_code(code, saved["verifier"])
    if not tokens.refresh_token:
        raise AppError("Google didn't grant lasting access. Try connecting again.",
                       code="oauth_no_refresh_token")
    missing = {s for s in google.SCOPES[2:] if s not in tokens.scopes}
    if missing:
        google.revoke(tokens.refresh_token)
        raise AppError("Outlogik needs read access to both Analytics and Search Console. "
                       "Connect again and leave both boxes ticked.", code="oauth_scopes_missing")
    email = google.email(tokens.access_token)

    integration = integration_for(db, ws)
    if integration is None:
        integration = Integration(organization_id=ws.organization_id, workspace_id=ws.id,
                                  provider="google")
        db.add(integration)
    elif integration.refresh_token_encrypted:
        google.revoke(decrypt(integration.refresh_token_encrypted))  # replaced: revoke the old
    integration.status, integration.last_error = "connected", None
    integration.account_email = email
    integration.scopes = " ".join(tokens.scopes)
    integration.refresh_token_encrypted = encrypt(tokens.refresh_token)
    integration.connected_by_user_id = user.id
    db.flush()
    _record_both(db, ctx, ws, "integration.connect", {"provider": "google", "account": email})
    db.commit()
    return ctx.org.slug, ws


def access_token(db: Session, integration: Integration) -> str:
    """A short-lived Google token. Marks the integration as needing reconnection if Google no
    longer accepts it."""
    try:
        return google.access_token(decrypt(integration.refresh_token_encrypted))
    except google.GoogleError as exc:
        if exc.reconnect:
            integration.status = "error"
            integration.last_error = ("Google no longer accepts this connection. Reconnect "
                                      "Google to start syncing again.")
            db.commit()
        raise


def available(db: Session, ws: Workspace) -> dict:
    integration = integration_for(db, ws)
    if integration is None:
        raise NotFound("Google isn't connected to this workspace.")
    token = access_token(db, integration)
    return {"ga4": google.ga4_properties(token),
            "search_console": google.search_console_sites(token)}


def choose(db: Session, ctx: OrgContext, ws: Workspace, *, ga4_property: str | None,
           search_console_site: str | None) -> list[DataSource]:
    """Set which Analytics property and Search Console site this workspace syncs. Only ones the
    connected Google account can actually see are accepted."""
    integration = integration_for(db, ws)
    if integration is None:
        raise NotFound("Google isn't connected to this workspace.")
    options = available(db, ws)
    wanted = {"ga4": ga4_property, "search_console": search_console_site}
    names = {"ga4": {p["id"]: f"{p['name']} ({p['account']})" for p in options["ga4"]},
             "search_console": {s["site_url"]: s["site_url"] for s in options["search_console"]}}
    for kind, value in wanted.items():
        if value is not None and value not in names[kind]:
            raise AppError("The connected Google account can't see that one.",
                           code="source_not_available", status_code=422,
                           details=[{"field": kind, "message": "Not available."}])
    existing = {s.kind: s for s in sources_for(db, integration)}
    for kind, value in wanted.items():
        current = existing.get(kind)
        if value is None:
            if current:
                db.delete(current)  # its history goes with it
            continue
        if current and current.external_id == value:
            continue
        if current:
            db.delete(current)
            db.flush()
        db.add(DataSource(organization_id=ws.organization_id, workspace_id=ws.id,
                          integration_id=integration.id, kind=kind, external_id=value,
                          name=names[kind][value][:300]))
    db.flush()
    _record_both(db, ctx, ws, "integration.sources", {"ga4": ga4_property,
                                                      "search_console": search_console_site})
    db.commit()
    sources = sources_for(db, integration)
    for source in sources:
        if source.sync_status == "pending":
            enqueue("integrations.sync", {"source_id": str(source.id)},
                    organization_id=ws.organization_id, dedupe_key=f"sync:{source.id}")
    return sources_for(db, integration)


def disconnect(db: Session, ctx: OrgContext, ws: Workspace) -> None:
    """Revoke Outlogik's access at Google and delete the connection and its synced data."""
    integration = integration_for(db, ws)
    if integration is None:
        raise NotFound("Google isn't connected to this workspace.")
    google.revoke(decrypt(integration.refresh_token_encrypted))
    _record_both(db, ctx, ws, "integration.disconnect",
                 {"provider": "google", "account": integration.account_email})
    db.delete(integration)  # sources and their history cascade
    db.commit()
