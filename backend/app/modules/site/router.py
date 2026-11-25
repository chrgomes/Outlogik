from fastapi import APIRouter, Depends, Request, Response

from app.core.config import get_settings as app_settings
from app.core.errors import NotFound
from app.core.request import client_ip
from app.modules.audit.service import record
from app.modules.auth.deps import DB
from app.modules.site import service
from app.modules.site.models import PortalFeature
from app.modules.site.schemas import (
    AdminSettingsOut,
    PortalFeatureOut,
    PortalFeatureUpdate,
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
            summary="Settings and client-portal features for the website")
def public_site(db: DB, response: Response) -> PublicSiteOut:
    response.headers["Cache-Control"] = PUBLIC_CACHE
    return PublicSiteOut(settings=service.read_settings(db),
                         portal_features=service.list_features(db, include_hidden=False),
                         signup_open=app_settings().signup_mode != "invite_only",
                         signup_code_required=app_settings().signup_mode == "code")


@admin.get("/site/settings", response_model=AdminSettingsOut)
def admin_get_settings(db: DB, _: User = Depends(require_staff(SITE_ADMIN))) -> AdminSettingsOut:
    row = service.get_settings_row(db)
    return AdminSettingsOut(data=service.read_settings(db), updated_at=row.updated_at)


@admin.put("/site/settings", response_model=AdminSettingsOut)
def admin_put_settings(body: SiteSettingsData, request: Request, db: DB,
                 user: User = Depends(require_staff(SITE_ADMIN))) -> AdminSettingsOut:
    row = service.update_settings(db, body, user.id, client_ip(request))
    return AdminSettingsOut(data=service.read_settings(db), updated_at=row.updated_at)


@admin.get("/site/portal-features", response_model=list[PortalFeatureOut])
def get_features(db: DB, _: User = Depends(require_staff(SITE_ADMIN))):
    return service.list_features(db, include_hidden=True)


@admin.patch("/site/portal-features/{slug}", response_model=PortalFeatureOut)
def patch_feature(slug: str, body: PortalFeatureUpdate, request: Request, db: DB,
                  user: User = Depends(require_staff(SITE_ADMIN))):
    feature = db.get(PortalFeature, slug)
    if feature is None:
        raise NotFound("Feature not found.")
    changes = {k: {"from": getattr(feature, k), "to": v}
               for k, v in body.model_dump(exclude_unset=True, exclude_none=True).items()
               if getattr(feature, k) != v}
    for key, change in changes.items():
        setattr(feature, key, change["to"])
    if changes:
        record(db, "site.portal_feature_update", actor_user_id=user.id,
               target_type="portal_feature", target_id=slug, meta=changes, ip=client_ip(request))
    db.commit()
    return feature
