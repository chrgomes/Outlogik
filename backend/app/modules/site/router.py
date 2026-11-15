from fastapi import APIRouter, Depends, Request, Response

from app.core.errors import NotFound
from app.core.request import client_ip
from app.modules.audit.service import record
from app.modules.auth.deps import DB
from app.modules.site import service
from app.modules.site.models import ProductModule
from app.modules.site.schemas import (
    AdminSettingsOut,
    ProductModuleOut,
    ProductModuleUpdate,
    PublicSiteOut,
    SiteSettingsData,
)
from app.modules.users.models import User
from app.platform import SITE_ADMIN, require_staff

# Public: read by the marketing site. No sign-in; nothing private in the response.
public = APIRouter(prefix="/public", tags=["public"])
# Admin: Outlogik staff only.
admin = APIRouter(prefix="/admin", tags=["admin"])

PUBLIC_CACHE = "public, max-age=60, stale-while-revalidate=300"


@public.get("/site", response_model=PublicSiteOut,
            summary="Settings and product modules for the marketing site")
def public_site(db: DB, response: Response) -> PublicSiteOut:
    response.headers["Cache-Control"] = PUBLIC_CACHE
    return PublicSiteOut(settings=service.read_settings(db),
                         modules=service.list_modules(db, include_hidden=False))


@admin.get("/site/settings", response_model=AdminSettingsOut)
def get_settings(db: DB, _: User = Depends(require_staff(SITE_ADMIN))) -> AdminSettingsOut:
    row = service.get_settings_row(db)
    return AdminSettingsOut(data=service.read_settings(db), updated_at=row.updated_at)


@admin.put("/site/settings", response_model=AdminSettingsOut)
def put_settings(body: SiteSettingsData, request: Request, db: DB,
                 user: User = Depends(require_staff(SITE_ADMIN))) -> AdminSettingsOut:
    row = service.update_settings(db, body, user.id, client_ip(request))
    return AdminSettingsOut(data=service.read_settings(db), updated_at=row.updated_at)


@admin.get("/site/modules", response_model=list[ProductModuleOut])
def get_modules(db: DB, _: User = Depends(require_staff(SITE_ADMIN))):
    return service.list_modules(db, include_hidden=True)


@admin.patch("/site/modules/{slug}", response_model=ProductModuleOut)
def patch_module(slug: str, body: ProductModuleUpdate, request: Request, db: DB,
                 user: User = Depends(require_staff(SITE_ADMIN))):
    module = db.get(ProductModule, slug)
    if module is None:
        raise NotFound("Module not found.")
    changes = {k: {"from": getattr(module, k), "to": v}
               for k, v in body.model_dump(exclude_unset=True, exclude_none=True).items()
               if getattr(module, k) != v}
    for key, change in changes.items():
        setattr(module, key, change["to"])
    if changes:
        record(db, "site.module_update", actor_user_id=user.id, target_type="product_module",
               target_id=slug, meta=changes, ip=client_ip(request))
    db.commit()
    return module
