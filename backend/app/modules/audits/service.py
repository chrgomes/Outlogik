"""Website audits: starting them (within the plan's limits), running them as background jobs,
scheduling, and comparing each audit with the one before."""

import logging
import uuid
from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.errors import Conflict, NotFound
from app.core.models import utcnow
from app.jobs.service import enqueue
from app.modules.audit.service import record
from app.modules.audits import pagespeed
from app.modules.audits.checks import CHECKS, run_checks
from app.modules.audits.crawler import crawl
from app.modules.audits.models import Audit, AuditIssue, AuditPage
from app.modules.audits.schemas import (
    AuditDetailOut,
    AuditOut,
    AuditPageOut,
    FixedOut,
    IssueGroupOut,
    IssueRef,
)
from app.modules.organizations.models import Organization
from app.modules.plans.service import cap, check_limit, record_use
from app.modules.websites.models import Website
from app.modules.workspaces.models import Workspace

log = logging.getLogger(__name__)

DEFAULT_PAGE_LIMIT = 500   # organizations without a plan
MAX_PAGE_LIMIT = 5000      # whatever the plan says
ITEMS_PER_CHECK = 200
FREQUENCY_DAYS = {"weekly": 7, "monthly": 30}


def _out(a: Audit, website: Website) -> AuditOut:
    return AuditOut(id=a.id, workspace_id=a.workspace_id, website_id=a.website_id,
                    website_name=website.name, url=a.url, status=a.status, trigger=a.trigger,
                    page_limit=a.page_limit, pages_crawled=a.pages_crawled,
                    hit_page_limit=a.hit_page_limit, errors=a.errors, warnings=a.warnings,
                    notices=a.notices, error=a.error, created_at=a.created_at,
                    started_at=a.started_at, finished_at=a.finished_at)


def to_out(db: Session, a: Audit) -> AuditOut:
    return _out(a, db.get(Website, a.website_id))


# --- starting -------------------------------------------------------------------------------

def start(db: Session, website: Website, *, trigger: str = "manual",
          user_id: uuid.UUID | None = None, actor_org_id: uuid.UUID | None = None) -> Audit:
    """Queue an audit of `website`. Counts against the plan of the organization that owns the
    website (a business's, when an agency runs it)."""
    if website.status == "archived":
        raise Conflict("Archived websites aren't audited. Restore it first.",
                       code="website_archived")
    running = db.scalar(select(Audit.id).where(Audit.website_id == website.id,
                                               Audit.status.in_(("queued", "running"))))
    if running:
        raise Conflict("An audit of this website is already running.", code="audit_running",
                       details={"audit_id": str(running)})
    owner = website.organization_id
    check_limit(db, owner, "limits.audits_per_month")
    plan_cap = cap(db, owner, "limits.pages_per_audit")
    audit = Audit(organization_id=owner, workspace_id=website.workspace_id,
                  website_id=website.id, trigger=trigger, requested_by_user_id=user_id,
                  url=website.url, page_limit=min(plan_cap or DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT))
    db.add(audit)
    db.flush()
    record_use(db, owner, "audits")
    for org_id in {owner, actor_org_id} - {None}:
        record(db, "audit.start", actor_user_id=user_id, organization_id=org_id,
               target_type="website", target_id=website.id,
               meta={"url": website.url, "trigger": trigger, "audit_id": str(audit.id)})
    db.commit()
    enqueue("audit.run", {"audit_id": str(audit.id)}, organization_id=owner,
            dedupe_key=f"audit:{website.id}")
    return audit


# --- running (in the worker) ----------------------------------------------------------------

def run(db: Session, audit_id: uuid.UUID) -> None:
    audit = db.get(Audit, audit_id)
    if audit is None or audit.status not in ("queued", "running"):
        return
    # A retry after a worker stopped starts again from scratch.
    db.execute(delete(AuditPage).where(AuditPage.audit_id == audit.id))
    db.execute(delete(AuditIssue).where(AuditIssue.audit_id == audit.id))
    audit.status, audit.started_at, audit.error = "running", utcnow(), None
    db.commit()
    try:
        result = crawl(audit.url, max_pages=audit.page_limit)
        found, facts = run_checks(result)
        if result.home is not None and result.home.fetched.ok:
            facts["pagespeed"] = speed = pagespeed.run(result.home.fetched.final_url)
            if isinstance(speed.get("score"), int) and speed["score"] < 50:
                from app.modules.audits.checks import Found
                found.append(Found("slow_mobile_performance", result.home.fetched.final_url,
                                   {"score": speed["score"]}))
    except Exception as exc:  # noqa: BLE001 - recorded on the audit, not retried
        log.exception("Audit %s failed", audit_id)
        audit.status, audit.finished_at = "failed", utcnow()
        audit.error = f"The audit couldn't finish ({type(exc).__name__})."
        db.commit()
        return

    for p in result.pages:
        db.add(AuditPage(
            audit_id=audit.id, organization_id=audit.organization_id, url=p.url[:2048],
            final_url=p.fetched.final_url[:2048], status_code=p.fetched.status,
            redirects=len(p.fetched.redirects), elapsed_ms=p.fetched.elapsed_ms, depth=p.depth,
            title=(p.page.title or "")[:500] if p.page else None,
            word_count=p.page.word_count if p.page else None,
            error=(p.fetched.error or "")[:300] or None))
    counts = {"error": 0, "warning": 0, "notice": 0}
    for f in found:
        check = CHECKS[f.check]
        counts[check.severity] += 1
        db.add(AuditIssue(audit_id=audit.id, organization_id=audit.organization_id,
                          check_key=f.check, severity=check.severity, area=check.area,
                          url=f.url[:2048] if f.url else None, details=f.details or {}))
    audit.pages_crawled = len(result.pages)
    audit.hit_page_limit = result.hit_page_limit
    audit.errors, audit.warnings, audit.notices = (counts["error"], counts["warning"],
                                                   counts["notice"])
    audit.facts = facts
    audit.status, audit.finished_at = "completed", utcnow()
    db.commit()


def schedule_due(db: Session) -> int:
    """Start the audits websites have asked for (weekly or monthly). Skips websites whose plan
    has no audits left this month (they're tried again the next day), and suspended
    organizations."""
    started = 0
    sites = db.scalars(select(Website).join(Organization,
                                            Organization.id == Website.organization_id)
                       .where(Website.audit_frequency != "off", Website.status == "active",
                              Organization.status != "suspended")).all()
    now = utcnow()
    for site in sites:
        last = db.scalar(select(func.max(Audit.created_at)).where(Audit.website_id == site.id))
        if last and last > now - timedelta(days=FREQUENCY_DAYS[site.audit_frequency]):
            continue
        try:
            start(db, site, trigger="scheduled")
            started += 1
        except Exception as exc:  # noqa: BLE001 - one website mustn't stop the others
            db.rollback()
            log.info("Scheduled audit of %s skipped: %s", site.url, exc)
    return started


# --- reading --------------------------------------------------------------------------------

def get(db: Session, workspace: Workspace, audit_id: uuid.UUID) -> Audit:
    audit = db.scalar(select(Audit).where(Audit.id == audit_id,
                                          Audit.workspace_id == workspace.id))
    if audit is None:
        raise NotFound("Audit not found.")
    return audit


def _previous(db: Session, audit: Audit) -> Audit | None:
    return db.scalar(select(Audit).where(Audit.website_id == audit.website_id,
                                         Audit.status == "completed",
                                         Audit.created_at < audit.created_at)
                     .order_by(Audit.created_at.desc()).limit(1))


def _keys(db: Session, audit_id: uuid.UUID) -> set[tuple[str, str | None]]:
    return set(db.execute(select(AuditIssue.check_key, AuditIssue.url)
                          .where(AuditIssue.audit_id == audit_id)).all())


def detail(db: Session, audit: Audit) -> AuditDetailOut:
    base = to_out(db, audit).model_dump()
    prev = _previous(db, audit) if audit.status == "completed" else None
    new = fixed = None
    if prev:
        now_keys, before = _keys(db, audit.id), _keys(db, prev.id)
        new, fixed = len(now_keys - before), len(before - now_keys)
    return AuditDetailOut(**base, facts=audit.facts, previous_audit_id=prev.id if prev else None,
                          new_issues=new, fixed_issues=fixed)


SEVERITY_ORDER = {"error": 0, "warning": 1, "notice": 2}


def issues(db: Session, audit: Audit) -> list[IssueGroupOut]:
    prev = _previous(db, audit)
    before = _keys(db, prev.id) if prev else None
    groups: dict[str, list[AuditIssue]] = {}
    for issue in db.scalars(select(AuditIssue).where(AuditIssue.audit_id == audit.id)
                            .order_by(AuditIssue.url)):
        groups.setdefault(issue.check_key, []).append(issue)
    out = []
    for key, rows in groups.items():
        check = CHECKS[key]
        refs = [IssueRef(url=r.url, details=r.details,
                         is_new=before is not None and (key, r.url) not in before) for r in rows]
        out.append(IssueGroupOut(check=key, title=check.title, severity=check.severity,
                                 area=check.area, why=check.why, fix=check.fix, count=len(rows),
                                 new=sum(r.is_new for r in refs), items=refs[:ITEMS_PER_CHECK]))
    return sorted(out, key=lambda g: (SEVERITY_ORDER[g.severity], -g.count, g.title))


def fixed(db: Session, audit: Audit) -> list[FixedOut]:
    prev = _previous(db, audit)
    if prev is None:
        return []
    gone = sorted(_keys(db, prev.id) - _keys(db, audit.id), key=lambda k: (k[0], k[1] or ""))
    return [FixedOut(check=k, title=CHECKS[k].title, url=u) for k, u in gone[:500]]


def pages(db: Session, audit: Audit) -> list[AuditPageOut]:
    rows = db.scalars(select(AuditPage).where(AuditPage.audit_id == audit.id)
                      .order_by(AuditPage.depth, AuditPage.url))
    return [AuditPageOut(url=p.url, final_url=p.final_url, status_code=p.status_code,
                         redirects=p.redirects, elapsed_ms=p.elapsed_ms, depth=p.depth,
                         title=p.title, word_count=p.word_count, error=p.error) for p in rows]
