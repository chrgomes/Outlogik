"""Admin API for website leads and newsletter subscribers (Outlogik site admins only)."""

import csv
import io
import uuid
from collections.abc import Iterable
from datetime import timedelta
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import NotFound
from app.core.models import utcnow
from app.core.pagination import Page, Paging, like_pattern, paginate
from app.core.request import client_ip
from app.modules.audit.service import record
from app.modules.auth.deps import DB
from app.modules.leads.models import Lead, LeadNote, NewsletterSubscriber
from app.modules.leads.schemas import (
    LeadCounts,
    LeadKind,
    LeadListItem,
    LeadNoteIn,
    LeadNoteOut,
    LeadOut,
    LeadSource,
    LeadStatus,
    LeadUpdate,
    SubscriberOut,
    SubscriberStatus,
)
from app.modules.leads.service import BUDGET_LABELS, SERVICE_LABELS, TOPIC_LABELS
from app.modules.users.models import User
from app.platform import SITE_ADMIN, require_staff

router = APIRouter(prefix="/admin", tags=["admin"])
SiteAdmin = Annotated[User, Depends(require_staff(SITE_ADMIN))]


# --- leads ------------------------------------------------------------------------------------

def _lead_query(kind: LeadKind | None, lead_status: LeadStatus | None, q: str | None):
    stmt = select(Lead)
    # Spam stays out of the inbox unless asked for.
    stmt = stmt.where(Lead.status == lead_status) if lead_status else stmt.where(
        Lead.status != "spam")
    if kind:
        stmt = stmt.where(Lead.kind == kind)
    if q:
        like = like_pattern(q)
        stmt = stmt.where(or_(*(func.lower(c).like(like, escape="\\")
                                for c in (Lead.name, Lead.email, Lead.company))))
    return stmt.order_by(Lead.created_at.desc())


@router.get("/leads", response_model=Page[LeadListItem], summary="The leads inbox")
def list_leads(db: DB, paging: Paging, _: SiteAdmin, kind: LeadKind | None = None,
               status: LeadStatus | None = None,
               q: Annotated[str | None, Query(max_length=100)] = None):
    rows, total = paginate(db, _lead_query(kind, status, q), paging)
    leads = [r[0] for r in rows]
    counts = dict(db.execute(
        select(LeadNote.lead_id, func.count()).where(LeadNote.lead_id.in_([x.id for x in leads]))
        .group_by(LeadNote.lead_id)).all()) if leads else {}
    items = [LeadListItem(
        id=x.id, kind=x.kind, status=x.status, name=x.name, email=x.email, company=x.company,
        services=x.details.get("services", []), utm_source=x.attribution.get("utm_source"),
        note_count=counts.get(x.id, 0), created_at=x.created_at,
    ) for x in leads]
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)


@router.get("/leads/counts", response_model=LeadCounts, summary="Leads per status")
def lead_counts(db: DB, _: SiteAdmin) -> LeadCounts:
    return LeadCounts(**dict(db.execute(
        select(Lead.status, func.count()).group_by(Lead.status)).all()))


DIRECT = "Direct or unknown"


def source_of(attribution: dict) -> str:
    """A campaign tag if there is one, otherwise the referring site, otherwise "Direct"."""
    if attribution.get("utm_source"):
        return attribution["utm_source"].strip().lower()
    host = urlsplit(attribution.get("referrer") or "").hostname or ""
    return host.removeprefix("www.") or DIRECT


@router.get("/leads/sources", response_model=list[LeadSource],
            summary="Where leads came from (first-party, no cookies)")
def lead_sources(db: DB, _: SiteAdmin,
                 days: Annotated[int, Query(ge=1, le=730)] = 90) -> list[LeadSource]:
    since = utcnow() - timedelta(days=days)
    rows: dict[str, LeadSource] = {}
    leads = db.execute(select(Lead.kind, Lead.attribution).where(
        Lead.created_at >= since, Lead.status != "spam")).all()
    subs = db.execute(select(NewsletterSubscriber.attribution).where(
        NewsletterSubscriber.created_at >= since,
        NewsletterSubscriber.status == "confirmed")).all()
    for kind, attribution in leads:
        row = rows.setdefault(source_of(attribution), LeadSource(source=source_of(attribution)))
        if kind == "consultation":
            row.consultations += 1
        else:
            row.messages += 1
    for (attribution,) in subs:
        row = rows.setdefault(source_of(attribution), LeadSource(source=source_of(attribution)))
        row.newsletter += 1
    return sorted(rows.values(), key=lambda r: (-(r.consultations + r.messages + r.newsletter),
                                                r.source))


CSV_COLUMNS = [
    "received", "type", "status", "name", "email", "company", "website", "phone", "services",
    "budget", "best_time", "topic", "message", "page", "landing_page", "referrer",
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
]


def _safe(value: object) -> str:
    """CSV cell text that spreadsheets won't run as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def _csv(rows: Iterable[list[object]], header: list[str]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(header)
    for row in rows:
        writer.writerow([_safe(v) for v in row])
    return out.getvalue()


def _download(content: str, name: str) -> Response:
    stamp = utcnow().strftime("%Y-%m-%d")
    return Response(content="﻿" + content, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{name}-{stamp}.csv"',
        "Cache-Control": "no-store",
    })


@router.get("/leads/export.csv", summary="Download leads as CSV",
            response_class=Response, responses={200: {"content": {"text/csv": {}}}})
def export_leads(request: Request, db: DB, user: SiteAdmin, kind: LeadKind | None = None,
                 status: LeadStatus | None = None,
                 q: Annotated[str | None, Query(max_length=100)] = None) -> Response:
    leads = db.scalars(_lead_query(kind, status, q)).all()

    def row(x: Lead) -> list[object]:
        d, a = x.details, x.attribution
        return [
            x.created_at.isoformat(timespec="seconds"), x.kind, x.status, x.name, x.email,
            x.company, x.website, x.phone,
            "; ".join(SERVICE_LABELS.get(s, s) for s in d.get("services", [])),
            BUDGET_LABELS.get(d.get("budget") or "", ""), d.get("preferred_contact"),
            TOPIC_LABELS.get(d.get("topic") or "", ""), x.message,
            *(a.get(k) for k in CSV_COLUMNS[13:]),
        ]

    record(db, "lead.export", actor_user_id=user.id, ip=client_ip(request),
           meta={"count": len(leads), "kind": kind, "status": status, "q": q})
    db.commit()
    return _download(_csv(map(row, leads), CSV_COLUMNS), "outlogik-leads")


def _get_lead(db: Session, lead_id: uuid.UUID) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise NotFound("Lead not found.")
    return lead


def _lead_out(db: Session, lead: Lead) -> LeadOut:
    notes = db.execute(
        select(LeadNote, User.full_name).outerjoin(User, User.id == LeadNote.author_user_id)
        .where(LeadNote.lead_id == lead.id).order_by(LeadNote.created_at.desc())).all()
    return LeadOut.model_validate({
        **{c: getattr(lead, c) for c in LeadOut.model_fields if c != "notes"},
        "notes": [LeadNoteOut(id=n.id, body=n.body, author_name=name, created_at=n.created_at)
                  for n, name in notes],
    })


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: uuid.UUID, db: DB, _: SiteAdmin) -> LeadOut:
    return _lead_out(db, _get_lead(db, lead_id))


@router.patch("/leads/{lead_id}", response_model=LeadOut, summary="Change a lead's status")
def update_lead(lead_id: uuid.UUID, body: LeadUpdate, request: Request, db: DB,
                user: SiteAdmin) -> LeadOut:
    lead = _get_lead(db, lead_id)
    if lead.status != body.status:
        record(db, "lead.status_change", actor_user_id=user.id, target_type="lead",
               target_id=lead.id, ip=client_ip(request),
               meta={"from": lead.status, "to": body.status})
        lead.status = body.status
        db.commit()
    return _lead_out(db, lead)


@router.post("/leads/{lead_id}/notes", response_model=LeadOut,
             status_code=status.HTTP_201_CREATED, summary="Add a note to a lead")
def add_note(lead_id: uuid.UUID, body: LeadNoteIn, db: DB, user: SiteAdmin) -> LeadOut:
    lead = _get_lead(db, lead_id)
    db.add(LeadNote(lead_id=lead.id, author_user_id=user.id, body=body.body))
    lead.updated_at = utcnow()
    db.commit()
    return _lead_out(db, lead)


@router.delete("/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a lead and its notes (e.g. on a privacy request)")
def delete_lead(lead_id: uuid.UUID, request: Request, db: DB, user: SiteAdmin) -> None:
    lead = _get_lead(db, lead_id)
    # The audit entry deliberately holds no personal details.
    record(db, "lead.delete", actor_user_id=user.id, target_type="lead", target_id=lead.id,
           ip=client_ip(request), meta={"kind": lead.kind})
    db.execute(delete(Lead).where(Lead.id == lead.id))
    db.commit()


# --- newsletter subscribers -------------------------------------------------------------------

def _subscriber_query(sub_status: SubscriberStatus | None, q: str | None):
    stmt = select(NewsletterSubscriber)
    if sub_status:
        stmt = stmt.where(NewsletterSubscriber.status == sub_status)
    if q:
        stmt = stmt.where(func.lower(NewsletterSubscriber.email).like(like_pattern(q),
                                                                      escape="\\"))
    return stmt.order_by(NewsletterSubscriber.created_at.desc())


def _subscriber_out(s: NewsletterSubscriber) -> SubscriberOut:
    return SubscriberOut(id=s.id, email=s.email, status=s.status, consent_at=s.consent_at,
                         confirmed_at=s.confirmed_at, unsubscribed_at=s.unsubscribed_at,
                         source_page=s.attribution.get("page"))


@router.get("/newsletter/subscribers", response_model=Page[SubscriberOut])
def list_subscribers(db: DB, paging: Paging, _: SiteAdmin,
                     status: SubscriberStatus | None = None,
                     q: Annotated[str | None, Query(max_length=100)] = None):
    rows, total = paginate(db, _subscriber_query(status, q), paging)
    return Page(items=[_subscriber_out(r[0]) for r in rows], total=total, page=paging.page,
                page_size=paging.page_size)


@router.get("/newsletter/subscribers/export.csv", response_class=Response,
            summary="Download subscribers as CSV (confirmed only, unless a status is given)",
            responses={200: {"content": {"text/csv": {}}}})
def export_subscribers(request: Request, db: DB, user: SiteAdmin,
                       status: SubscriberStatus = "confirmed") -> Response:
    subs = db.scalars(_subscriber_query(status, None)).all()
    record(db, "newsletter.export", actor_user_id=user.id, ip=client_ip(request),
           meta={"count": len(subs), "status": status})
    db.commit()
    header = ["email", "status", "consent_given", "confirmed", "unsubscribed", "consent_text",
              "signup_page"]
    rows = ([s.email, s.status, s.consent_at.isoformat(timespec="seconds"),
             s.confirmed_at and s.confirmed_at.isoformat(timespec="seconds"),
             s.unsubscribed_at and s.unsubscribed_at.isoformat(timespec="seconds"),
             s.consent_text, s.attribution.get("page")] for s in subs)
    return _download(_csv(rows, header), f"outlogik-newsletter-{status}")


@router.delete("/newsletter/subscribers/{subscriber_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a subscriber and their consent record (e.g. on a privacy request)")
def delete_subscriber(subscriber_id: uuid.UUID, request: Request, db: DB,
                      user: SiteAdmin) -> None:
    sub = db.get(NewsletterSubscriber, subscriber_id)
    if sub is None:
        raise NotFound("Subscriber not found.")
    record(db, "newsletter.delete", actor_user_id=user.id, target_type="newsletter_subscriber",
           target_id=sub.id, ip=client_ip(request))
    db.delete(sub)
    db.commit()
