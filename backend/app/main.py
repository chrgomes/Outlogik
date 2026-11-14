import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from app.core.config import get_settings
from app.core.csrf import install_csrf
from app.core.db import SessionLocal
from app.core.errors import install_error_handlers
from app.modules import health
from app.modules.auth.router import router as auth_router
from app.modules.rbac.service import sync_permissions

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        sync_permissions(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"{settings.app_name} API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
    )
    install_error_handlers(app)
    install_csrf(app)

    api = APIRouter(prefix="/api/v1")
    api.include_router(health.router)
    api.include_router(auth_router)
    app.include_router(api)
    return app


app = create_app()
