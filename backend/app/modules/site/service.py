from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.service import record
from app.modules.site.models import ProductModule, SiteSettings
from app.modules.site.schemas import SiteSettingsData

# Defaults restored at startup if missing (the migration seeds the same rows). Statuses
# reflect Phase 1: only Client Management exists. Never overwrites an admin's changes.
DEFAULT_MODULES = [
    ("client-management", "Client Management", "available",
     "Clients, websites, team roles and client portals in one workspace."),
    ("seo-management", "SEO Management", "in_development",
     "Technical audits, keywords and search visibility for every site."),
    ("website-analytics", "Website Analytics", "in_development",
     "Google Analytics 4 and Search Console, side by side."),
    ("social-media-management", "Social Media Management", "in_development",
     "Plan, schedule and approve posts across your clients’ channels."),
    ("content-marketing", "Content Marketing", "in_development",
     "Editorial calendars and keyword-to-content planning."),
    ("marketing-analytics", "Marketing Analytics", "in_development",
     "Channels, campaigns and conversions in one view."),
    ("reporting", "Reporting", "in_development",
     "Clear client reports with PDF and CSV exports."),
]


def ensure_defaults(db: Session) -> None:
    existing = set(db.scalars(select(ProductModule.slug)))
    for i, (slug, name, status, summary) in enumerate(DEFAULT_MODULES, start=1):
        if slug not in existing:
            db.add(ProductModule(slug=slug, name=name, status=status, summary=summary,
                                 sort_order=i * 10))
    if db.get(SiteSettings, 1) is None:
        db.add(SiteSettings(id=1, data={}))
    db.commit()


def get_settings_row(db: Session) -> SiteSettings:
    row = db.get(SiteSettings, 1)
    if row is None:
        ensure_defaults(db)
        row = db.get(SiteSettings, 1)
    return row


def read_settings(db: Session) -> SiteSettingsData:
    # Stored data is merged over the defaults, so new settings get sensible values.
    return SiteSettingsData.model_validate(get_settings_row(db).data or {})


def update_settings(db: Session, data: SiteSettingsData, actor_id, ip: str | None) -> SiteSettings:
    row = get_settings_row(db)
    before = read_settings(db).model_dump(mode="json")
    after = data.model_dump(mode="json")
    row.data = after
    row.updated_by_user_id = actor_id
    changed = sorted(k for k in after if before.get(k) != after.get(k))
    if changed:
        record(db, "site.settings_update", actor_user_id=actor_id, target_type="site_settings",
               target_id="1", meta={"fields": changed}, ip=ip)
    db.commit()
    return row


def list_modules(db: Session, *, include_hidden: bool) -> list[ProductModule]:
    stmt = select(ProductModule).order_by(ProductModule.sort_order, ProductModule.name)
    if not include_hidden:
        stmt = stmt.where(ProductModule.status != "hidden")
    return list(db.scalars(stmt))
