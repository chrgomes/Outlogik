from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.audit.service import record
from app.modules.site.models import PortalFeature, SiteSettings
from app.modules.site.schemas import SiteSettingsData

# Defaults restored at startup if missing (migration 0004 seeds the same rows). Statuses are
# honest: only what the app does today is "available". Never overwrites an admin's changes.
DEFAULT_FEATURES = [
    ("client-portal", "Your own client portal", "available",
     "A private sign-in for your business, separate from every other client."),
    ("websites-overview", "Your websites in one place", "available",
     "Every website we look after for you, with its status."),
    ("activity-history", "A record of the work", "available",
     "Changes to your account and websites, with who made them and when."),
    ("monthly-reports", "Monthly reports", "in_development",
     "Your monthly results, ready to read online or download as PDF."),
    ("analytics-dashboards", "Analytics dashboards", "in_development",
     "Traffic and search performance from Google Analytics and Search Console."),
    ("social-approvals", "Social calendar approvals", "in_development",
     "Review and approve social posts before they go out."),
    ("seo-health", "SEO health checks", "in_development",
     "Technical issues found on your sites, and when they were fixed."),
]


def ensure_defaults(db: Session) -> None:
    existing = set(db.scalars(select(PortalFeature.slug)))
    for i, (slug, name, status, summary) in enumerate(DEFAULT_FEATURES, start=1):
        if slug not in existing:
            db.add(PortalFeature(slug=slug, name=name, status=status, summary=summary,
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
    return SiteSettingsData.from_stored(get_settings_row(db).data)


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


def list_features(db: Session, *, include_hidden: bool) -> list[PortalFeature]:
    stmt = select(PortalFeature).order_by(PortalFeature.sort_order, PortalFeature.name)
    if not include_hidden:
        stmt = stmt.where(PortalFeature.status != "hidden")
    return list(db.scalars(stmt))
