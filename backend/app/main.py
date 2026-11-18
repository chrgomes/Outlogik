import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.core.config import get_settings
from app.core.csrf import install_csrf
from app.core.db import SessionLocal
from app.core.errors import install_error_handlers
from app.core.headers import install_security_headers
from app.modules import health
from app.modules.auth.router import router as auth_router
from app.modules.clients.router import router as clients_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.grants.router import linked_router as grants_linked_router
from app.modules.grants.router import open_router as grants_open_router
from app.modules.grants.router import router as grants_router
from app.modules.leads.admin import router as leads_admin_router
from app.modules.leads.router import open_router as leads_open_router
from app.modules.leads.router import router as leads_router
from app.modules.organizations.router import router as organizations_router
from app.modules.rbac.router import router as rbac_router
from app.modules.rbac.service import sync_permissions
from app.modules.site import service as site_service
from app.modules.site.router import admin as site_admin_router
from app.modules.site.router import public as site_public_router
from app.modules.websites.router import router as websites_router
from app.modules.websites.router import workspace_router as workspace_websites_router
from app.modules.workspaces.router import members_router as member_workspaces_router
from app.modules.workspaces.router import router as workspaces_router

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        sync_permissions(db)
        site_service.ensure_defaults(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        lifespan=lifespan,
        # Interactive API docs in development only; production doesn't advertise its API.
        docs_url=None if settings.app_env == "production" else "/api/docs",
        redoc_url=None,
        openapi_url=None if settings.app_env == "production" else "/api/openapi.json",
    )
    install_error_handlers(app)
    install_csrf(app)
    install_security_headers(app)

    api = APIRouter(prefix="/api/v1")
    api.include_router(health.router)
    api.include_router(auth_router)
    api.include_router(organizations_router)
    api.include_router(rbac_router)
    api.include_router(clients_router)
    api.include_router(websites_router)
    api.include_router(workspaces_router)
    api.include_router(member_workspaces_router)
    api.include_router(grants_router)
    api.include_router(grants_linked_router)
    api.include_router(grants_open_router)
    api.include_router(workspace_websites_router)
    api.include_router(dashboard_router)
    api.include_router(site_public_router)
    api.include_router(leads_router)
    api.include_router(leads_open_router)
    api.include_router(leads_admin_router)
    api.include_router(site_admin_router)
    app.include_router(api)
    return app


app = create_app()
