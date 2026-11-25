import re
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select

from app.modules.auth.deps import DB
from app.modules.reports import exports, pdf, service
from app.modules.reports.models import Report
from app.modules.reports.schemas import ReportIn, ReportOut
from app.modules.users.models import User
from app.modules.workspaces.service import get_workspace
from app.tenancy.context import OrgContext, require

router = APIRouter(prefix="/orgs/{org_slug}", tags=["reports"])
CsvName = Literal[tuple(exports.TABLES)]  # type: ignore[valid-type]


def _out(db, report: Report) -> ReportOut:
    d = report.data
    p = d["dashboard"]["period"]
    name = db.scalar(select(User.full_name).where(User.id == report.created_by_user_id)) \
        if report.created_by_user_id else None
    return ReportOut(
        id=report.id, workspace_id=report.workspace_id, workspace_name=d["workspace_name"],
        title=report.title, sections=report.sections, period_start=report.period_start,
        period_end=report.period_end, compare=report.compare,
        compare_start=p["compare_start"], compare_end=p["compare_end"], sources=d["sources"],
        unavailable=d["unavailable"], csv_files=exports.available(report),
        created_at=report.created_at, created_by=name)


def _filename(report: Report, ext: str) -> str:
    """A safe download name: letters, digits and dashes only."""
    base = re.sub(r"[^A-Za-z0-9]+", "-", report.title).strip("-")[:80] or "report"
    return f"{base}-{report.period_end.isoformat()}.{ext}"


@router.get("/reports", response_model=list[ReportOut], summary="Saved reports, newest first")
def list_reports(db: DB, workspace_id: uuid.UUID | None = None,
                 ctx: OrgContext = Depends(require("reports.read"))):
    return [_out(db, r) for r in service.list_reports(db, ctx, workspace_id)]


@router.post("/workspaces/{workspace_id}/reports", response_model=ReportOut,
             status_code=status.HTTP_201_CREATED,
             summary="Make a report of a workspace for a period, and save it")
def create_report(workspace_id: uuid.UUID, body: ReportIn, db: DB,
                  ctx: OrgContext = Depends(require("reports.create"))):
    # The report is the caller's own record, so a view-only shared workspace is fine.
    ws = get_workspace(db, ctx, workspace_id)
    report = service.build(db, ctx, ws, sections=body.sections, title=body.title,
                           days=body.days, start=body.start, end=body.end, compare=body.compare)
    return _out(db, report)


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: uuid.UUID, db: DB, ctx: OrgContext = Depends(require("reports.read"))):
    return _out(db, service.get(db, ctx, report_id))


@router.get("/reports/{report_id}/pdf", response_class=Response,
            responses={200: {"content": {"application/pdf": {}}}}, summary="Download as PDF")
def report_pdf(report_id: uuid.UUID, db: DB,
               ctx: OrgContext = Depends(require("reports.read"))):
    report = service.get(db, ctx, report_id)
    return Response(pdf.render(report), media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{_filename(report, "pdf")}"',
        "Cache-Control": "no-store"})


@router.get("/reports/{report_id}/csv/{table}", response_class=Response,
            responses={200: {"content": {"text/csv": {}}}}, summary="Download one table as CSV")
def report_csv(report_id: uuid.UUID, table: CsvName, db: DB,
               ctx: OrgContext = Depends(require("reports.read"))):
    report = service.get(db, ctx, report_id)
    if table not in {f["name"] for f in exports.available(report)}:
        from app.core.errors import NotFound
        raise NotFound("This report has no such table.")
    name = _filename(report, "csv").replace(".csv", f"-{table.replace('_', '-')}.csv")
    return Response(exports.to_csv(report, table), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"',
                             "Cache-Control": "no-store"})


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: uuid.UUID, db: DB,
                  ctx: OrgContext = Depends(require("reports.create"))):
    service.delete(db, ctx, service.get(db, ctx, report_id))
