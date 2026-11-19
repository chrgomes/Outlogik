from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.errors import AppError, NotFound
from app.jobs.service import enqueue
from app.modules.auth.deps import DB, OptionalAuth
from app.modules.integrations import google, service
from app.modules.integrations.schemas import (
    AvailableOut,
    ConnectOut,
    DataSourceOut,
    IntegrationOut,
    SourcesIn,
    SummaryOut,
)
from app.modules.integrations.summary import summary
from app.modules.workspaces.context import WorkspaceContext, require_workspace

router = APIRouter(prefix="/orgs/{org_slug}/workspaces/{workspace_id}", tags=["integrations"])
callback_router = APIRouter(prefix="/integrations", tags=["integrations"])


def _out(db, ws) -> IntegrationOut:
    integration = service.integration_for(db, ws)
    if integration is None:
        return IntegrationOut(configured=google.configured(), connected=False)
    return IntegrationOut(
        configured=google.configured(), connected=True, status=integration.status,
        account_email=integration.account_email, connected_at=integration.created_at,
        last_error=integration.last_error,
        sources=[DataSourceOut.model_validate(s, from_attributes=True)
                 for s in service.sources_for(db, integration)])


@router.get("/integrations/google", response_model=IntegrationOut,
            summary="This workspace's Google connection and what it syncs")
def get_google(db: DB, w: WorkspaceContext = Depends(require_workspace("integrations.read"))):
    return _out(db, w.workspace)


@router.post("/integrations/google/connect", response_model=ConnectOut,
             summary="Start connecting Google: returns the address to send the person to")
def connect_google(w: WorkspaceContext = Depends(require_workspace("integrations.manage"))):
    return ConnectOut(url=service.start(w.org, w.workspace))


@router.get("/integrations/google/available", response_model=AvailableOut,
            summary="Analytics properties and Search Console sites the Google account can see")
def available(db: DB, w: WorkspaceContext = Depends(require_workspace("integrations.manage"))):
    return service.available(db, w.workspace)


@router.put("/integrations/google/sources", response_model=IntegrationOut,
            summary="Choose the Analytics property and Search Console site to sync")
def choose_sources(body: SourcesIn, db: DB,
                   w: WorkspaceContext = Depends(require_workspace("integrations.manage"))):
    service.choose(db, w.org, w.workspace, ga4_property=body.ga4_property,
                   search_console_site=body.search_console_site)
    return _out(db, w.workspace)


@router.post("/integrations/google/sync", response_model=IntegrationOut,
             status_code=status.HTTP_202_ACCEPTED, summary="Sync now")
def sync_now(db: DB, w: WorkspaceContext = Depends(require_workspace("integrations.manage"))):
    integration = service.integration_for(db, w.workspace)
    if integration is None:
        raise NotFound("Google isn't connected to this workspace.")
    if integration.status != "connected":
        raise AppError("Reconnect Google first.", code="integration_needs_reconnect",
                       status_code=409)
    for source in service.sources_for(db, integration):
        enqueue("integrations.sync", {"source_id": str(source.id)},
                organization_id=w.workspace.organization_id, dedupe_key=f"sync:{source.id}")
    db.expire_all()
    return _out(db, w.workspace)


@router.delete("/integrations/google", status_code=status.HTTP_204_NO_CONTENT,
               summary="Disconnect Google and delete the data synced from it")
def disconnect(db: DB, w: WorkspaceContext = Depends(require_workspace("integrations.manage"))):
    service.disconnect(db, w.org, w.workspace)


@router.get("/analytics/summary", response_model=SummaryOut,
            summary="Traffic, AI referrals and search results, against the previous period")
def analytics_summary(db: DB, days: Annotated[int, Query(ge=7, le=90)] = 28,
                      w: WorkspaceContext = Depends(require_workspace("analytics.read"))):
    integration = service.integration_for(db, w.workspace)
    return summary(db, service.sources_for(db, integration), days)


@callback_router.get("/google/callback", include_in_schema=False)
def google_callback(db: DB, auth: OptionalAuth, state: str = "", code: str = "",
                    error: str = ""):
    """Google sends the person here after the consent screen. Always redirects back into the
    app with the outcome; never shows a raw error."""
    base = get_settings().frontend_url.rstrip("/")
    if auth is None:
        return RedirectResponse(f"{base}/login", status_code=303)
    if error or not code:
        # They cancelled, or Google refused. Drop the state so it can't be reused.
        slug = service.cancel(state)
        target = f"/o/{slug}/integrations" if slug else "/"
        return RedirectResponse(f"{base}{target}?{urlencode({'google': 'cancelled'})}",
                                status_code=303)
    started_in = service.peek(state)  # where to send them back if it fails
    try:
        slug, ws = service.finish(db, auth.user, state, code)
    except AppError as exc:
        db.rollback()
        reason = getattr(exc, "code", None) or "google_error"
        target = f"/o/{started_in}/integrations" if started_in else "/"
        return RedirectResponse(f"{base}{target}?{urlencode({'google_error': reason})}",
                                status_code=303)
    query = urlencode({"workspace": str(ws.id), "google": "connected"})
    return RedirectResponse(f"{base}/o/{slug}/integrations?{query}", status_code=303)
