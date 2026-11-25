"""The report PDF, drawn with ReportLab from a saved report's data.

ReportLab is pure Python (no system libraries), so PDFs work the same on Windows, macOS and the
servers. Every piece of text from outside (search terms, page addresses, names, titles) goes
through `_t()`, which escapes ReportLab's markup and replaces characters the font can't draw,
so it can't change the layout or break the PDF.
"""

import io
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.reports.models import Report

FONTS = Path(__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("Albert", FONTS / "AlbertSans-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Albert-Bold", FONTS / "AlbertSans-SemiBold.ttf"))
pdfmetrics.registerFontFamily("Albert", normal="Albert", bold="Albert-Bold",
                              italic="Albert", boldItalic="Albert-Bold")
_GLYPHS = set(pdfmetrics.getFont("Albert").face.charToGlyph)

INK = colors.HexColor("#171717")
MUTED = colors.HexColor("#737373")
LINE = colors.HexColor("#e5e5e5")
WELL = colors.HexColor("#fafafa")
SEARCH = colors.HexColor("#3c6e91")
ERROR = colors.HexColor("#b42318")
WARNING = colors.HexColor("#a86b12")
UP = colors.HexColor("#2f7d4f")
WIDTH = LETTER[0] - 1.5 * inch

S = {
    "title": ParagraphStyle("title", fontName="Albert-Bold", fontSize=22, leading=27,
                            textColor=INK, spaceAfter=4),
    "sub": ParagraphStyle("sub", fontName="Albert", fontSize=10.5, leading=15, textColor=MUTED),
    # Headings stay on the same page as what follows them
    "h2": ParagraphStyle("h2", fontName="Albert-Bold", fontSize=14, leading=18, textColor=INK,
                         spaceBefore=14, spaceAfter=6, keepWithNext=1),
    "h3": ParagraphStyle("h3", fontName="Albert-Bold", fontSize=10.5, leading=14,
                         textColor=INK, spaceBefore=8, spaceAfter=4, keepWithNext=1),
    "body": ParagraphStyle("body", fontName="Albert", fontSize=9.5, leading=13.5, textColor=INK),
    "small": ParagraphStyle("small", fontName="Albert", fontSize=8, leading=11, textColor=MUTED),
    "cell": ParagraphStyle("cell", fontName="Albert", fontSize=8.5, leading=11, textColor=INK),
    "num": ParagraphStyle("num", fontName="Albert", fontSize=8.5, leading=11, textColor=INK,
                          alignment=TA_RIGHT),
    "head": ParagraphStyle("head", fontName="Albert-Bold", fontSize=7.5, leading=10,
                           textColor=MUTED),
    "headr": ParagraphStyle("headr", fontName="Albert-Bold", fontSize=7.5, leading=10,
                            textColor=MUTED, alignment=TA_RIGHT),
    "kpi_label": ParagraphStyle("kl", fontName="Albert", fontSize=8, leading=10, textColor=MUTED),
    "kpi_value": ParagraphStyle("kv", fontName="Albert-Bold", fontSize=17, leading=21,
                                textColor=INK),
}


# --- text helpers ---------------------------------------------------------------------------

def _t(value) -> str:
    """Text for a Paragraph: markup escaped, characters the font lacks shown as '?'."""
    text = "" if value is None else str(value)
    return escape("".join(c if ord(c) in _GLYPHS or c in "\n\t" else "?" for c in text))


def _d(value: str | date | None) -> str:
    if not value:
        return ""
    d = date.fromisoformat(value[:10]) if isinstance(value, str) else value
    return f"{d:%B} {d.day}, {d.year}"


def _n(value, digits: int = 0) -> str:
    if value is None:
        return "—"
    return f"{value:,.{digits}f}"


def _pct(value: float | None, digits: int = 1) -> str:
    return "—" if value is None else f"{value * 100:.{digits}f}%"


def _change(now: float, before: float | None, against: str) -> tuple[str, colors.Color]:
    if before is None:
        return "No earlier data to compare", MUTED
    if before == 0:
        return ("New this period", UP) if now else ("No change", MUTED)
    pct = round((now - before) / before * 100)
    if pct == 0:
        return "No change", MUTED
    return (f"{'+' if pct > 0 else '−'}{abs(pct)}% vs {against}", UP if pct > 0 else ERROR)


def _path(url: str) -> str:
    from urllib.parse import urlsplit
    try:
        parts = urlsplit(url)
        return (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    except ValueError:
        return url


# --- building blocks ------------------------------------------------------------------------

def _table(header: list[str], rows: list[list], widths: list[float], right: set[int]):
    data = [[Paragraph(_t(h).upper(), S["headr" if i in right else "head"])
             for i, h in enumerate(header)]]
    for row in rows:
        data.append([Paragraph(_t(v), S["num" if i in right else "cell"])
                     for i, v in enumerate(row)])
    table = Table(data, colWidths=[w * WIDTH for w in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _kpis(items: list[tuple[str, str, str, colors.Color]]):
    cells = []
    for label, value, note, tone in items:
        note_style = ParagraphStyle("note", parent=S["small"], textColor=tone)
        cells.append([Paragraph(_t(label), S["kpi_label"]), Paragraph(_t(value), S["kpi_value"]),
                      Paragraph(_t(note), note_style)])
    per_row = 3
    rows = [cells[i:i + per_row] for i in range(0, len(cells), per_row)]
    rows[-1] += [""] * (per_row - len(rows[-1]))
    table = Table(rows, colWidths=[WIDTH / per_row] * per_row)
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def _labels(days: list[str], count: int = 6) -> list[str]:
    step = max(1, len(days) // count)
    return [_short(d) if i % step == 0 else "" for i, d in enumerate(days)]


def _short(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{d:%b} {d.day}"


def _axis_style(chart, values: list[float]):
    chart.valueAxis.valueMin = 0
    top = max([v for v in values if v is not None] + [1])
    chart.valueAxis.valueMax = top * 1.15
    chart.valueAxis.labels.fontName = "Albert"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fillColor = MUTED
    chart.valueAxis.strokeColor = LINE
    chart.valueAxis.gridStrokeColor = LINE
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.labelTextFormat = lambda v: f"{v:,.0f}"
    chart.categoryAxis.labels.fontName = "Albert"
    chart.categoryAxis.labels.fontSize = 7
    chart.categoryAxis.labels.fillColor = MUTED
    chart.categoryAxis.strokeColor = LINE
    chart.categoryAxis.visibleTicks = False


def _line_chart(days: list[str], now: list, before: list | None, height: float = 150):
    drawing = Drawing(WIDTH, height)
    chart = HorizontalLineChart()
    chart.x, chart.y, chart.width, chart.height = 34, 18, WIDTH - 44, height - 26
    series = ([[v or 0 for v in before]] if before else []) + [[v or 0 for v in now]]
    chart.data = series
    chart.categoryAxis.categoryNames = _labels(days)
    _axis_style(chart, [v for s in series for v in s])
    chart.joinedLines = True
    if before:
        chart.lines[0].strokeColor = MUTED
        chart.lines[0].strokeWidth = 1
        chart.lines[0].strokeDashArray = (3, 2)
    chart.lines[len(series) - 1].strokeColor = INK
    chart.lines[len(series) - 1].strokeWidth = 1.8
    drawing.add(chart)
    return drawing


def _bar_chart(labels: list[str], series: list[list], fills: list, height: float = 130):
    drawing = Drawing(WIDTH, height)
    chart = VerticalBarChart()
    # Few bars (an audit history) stay narrow instead of filling the page
    width = min(WIDTH - 44, len(labels) * len(series) * 26 + 40)
    chart.x, chart.y, chart.width, chart.height = 34, 18, width, height - 26
    chart.data = [[v or 0 for v in s] for s in series]
    chart.categoryAxis.categoryNames = labels
    _axis_style(chart, [v for s in chart.data for v in s])
    chart.barSpacing = 1
    chart.groupSpacing = 3
    for i, fill in enumerate(fills):
        chart.bars[i].fillColor = fill
        chart.bars[i].strokeColor = None
    drawing.add(chart)
    return drawing


def _key(items: list[tuple[str, colors.Color, bool]]):
    """A small legend, drawn: (label, colour, dashed)."""
    drawing = Drawing(WIDTH, 12)
    x = 0.0
    for label, color, dashed in items:
        line = Line(x, 5, x + 14, 5, strokeColor=color, strokeWidth=1.2 if dashed else 2.5)
        if dashed:
            line.strokeDashArray = (3, 2)
        drawing.add(line)
        text = _plain(label)
        drawing.add(String(x + 18, 2, text, fontName="Albert", fontSize=7.5, fillColor=MUTED))
        x += 18 + pdfmetrics.stringWidth(text, "Albert", 7.5) + 14
    return drawing


# --- the document ---------------------------------------------------------------------------

def render(report: Report) -> bytes:
    data, dash = report.data, report.data["dashboard"]
    p = dash["period"]
    against = "the same period last year" if p["compare"] == "year" else "before"
    against_short = "last year" if p["compare"] == "year" else "before"
    sections = set(report.sections)
    story: list = []

    # Title block
    story.append(Paragraph(_t(report.title), S["title"]))
    who = f"Prepared by {_t(data['prepared_by'])}"
    if data.get("prepared_for"):
        who += f" for {_t(data['prepared_for'])}"
    period = f"{_d(p['start'])} to {_d(p['end'])}"
    if p["compare"] != "none":
        period += f", compared with {_d(p['compare_start'])} to {_d(p['compare_end'])}"
    story.append(Paragraph(f"{who}<br/>{_t(period)}<br/>Made on {_d(report.created_at.date())}",
                           S["sub"]))
    story.append(Spacer(1, 12))

    # About this report: sources and what's unavailable (spec §10)
    about = [Paragraph("About this report", S["h3"])]
    if data["sources"]:
        about.append(Paragraph("<b>Sources</b>", S["body"]))
        about.append(ListFlowable([ListItem(Paragraph(
            f"{_t(s['name'])}: {_t(s['detail'])}"
            + (f" ({'checked on' if s['name'].endswith('audit') else 'data through'} "
               f"{_d(s['through'])})" if s.get("through") else ""), S["body"]),
            leftIndent=10) for s in data["sources"]], bulletType="bullet", start="•",
            leftIndent=10, bulletFontName="Albert"))
    if data["unavailable"]:
        about.append(Spacer(1, 4))
        about.append(Paragraph("<b>Not available or limited</b>", S["body"]))
        about.append(ListFlowable([ListItem(Paragraph(_t(u), S["body"]), leftIndent=10)
                                   for u in data["unavailable"]], bulletType="bullet",
                                  start="•", leftIndent=10, bulletFontName="Albert"))
    about.append(Spacer(1, 4))
    about.append(Paragraph("Every figure comes from the sources above. Outlogik doesn't estimate "
                           "missing data or forecast results.", S["small"]))
    box = Table([[about]], colWidths=[WIDTH])
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WELL),
                             ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                             ("LEFTPADDING", (0, 0), (-1, -1), 12),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                             ("TOPPADDING", (0, 0), (-1, -1), 4),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story.append(box)

    # What changed: only sentences about the sections included
    keep = {"Visits": "traffic", "AI tools": "ai", "Google search": "search",
            "The latest audit": "audit"}
    changes = [c for c in dash["changes"]
               if next((sec for start, sec in keep.items() if c.startswith(start)), None)
               in sections]
    if changes:
        story.append(Paragraph("What changed", S["h2"]))
        story.append(ListFlowable([ListItem(Paragraph(_t(c), S["body"]), leftIndent=10)
                                   for c in changes], bulletType="bullet", start="•",
                                  leftIndent=10, bulletFontName="Albert"))

    # Key figures
    kpis = []
    ga4, gsc, audit = dash["ga4"], dash["search_console"], dash["audit"]
    if ga4 and "traffic" in sections:
        for key, label in (("sessions", "Visits"), ("users", "Visitors"),
                           ("key_events", "Key events")):
            m = ga4["metrics"][key]
            kpis.append((label, _n(m["value"]), *_change(m["value"], m["previous"], against_short)))
    if ga4 and "ai" in sections:
        now = sum(r["sessions"] for r in dash["ai_referrals"])
        before = None if ga4["metrics"]["sessions"]["previous"] is None else sum(
            r["previous"] or 0 for r in dash["ai_referrals"])
        kpis.append(("Visits from AI tools", _n(now), *_change(now, before, against_short)))
    if gsc and "search" in sections:
        m = gsc["metrics"]["clicks"]
        kpis.append(("Search clicks", _n(m["value"]), *_change(m["value"], m["previous"],
                                                                against_short)))
        pos = gsc["metrics"]["position"]
        kpis.append(("Average position", _n(pos["value"], 1),
                     f"Click rate {_pct(gsc['metrics']['ctr']['value'])}", MUTED))
    if audit and "audit" in sections:
        kpis.append(("Audit errors", _n(audit["errors"]),
                     f"{audit['warnings']} warnings · {audit['notices']} notices", MUTED))
    if kpis:
        story.append(Paragraph("Key figures", S["h2"]))
        story.append(_kpis(kpis))

    series = dash["series"]
    if "traffic" in sections and ga4:
        story.append(Paragraph("Traffic", S["h2"]))
        points = [x for x in series if x["sessions"] is not None]
        has_before = any(x["previous_sessions"] is not None for x in points)
        story.append(KeepTogether([
            Paragraph("Visits per day", S["h3"]),
            _key([("This period", INK, False)]
                 + ([(f"Compared with {against}", MUTED, True)] if has_before else [])),
            _line_chart([x["day"] for x in points], [x["sessions"] for x in points],
                        [x["previous_sessions"] for x in points] if has_before else None)]))
        if dash["channels"]:
            total = sum(c["sessions"] for c in dash["channels"]) or 1
            story.append(KeepTogether([Paragraph("Where visits came from", S["h3"]), _table(
                ["Channel", "Visits", "Share", "Before"],
                [[c["name"], _n(c["sessions"]), _pct(c["sessions"] / total, 0),
                  _n(c["previous"])] for c in dash["channels"][:10]],
                [0.55, 0.15, 0.15, 0.15], {1, 2, 3})]))
        if dash["top_pages"]:
            story.append(KeepTogether([Paragraph("Pages that bring the most visits", S["h3"]),
                Paragraph("The page each visit started on.", S["small"]), _table(
                ["Page", "Visits", "Before", "Key events"],
                [[r["path"], _n(r["sessions"]), _n(r["previous"]), _n(r["key_events"])]
                 for r in dash["top_pages"]], [0.55, 0.15, 0.15, 0.15], {1, 2, 3})]))

    if "ai" in sections and ga4:
        story.append(Paragraph("Visits from AI tools", S["h2"]))
        if dash["ai_referrals"]:
            story.append(_table(["AI tool", "Visits", "Before"],
                                [[r["name"], _n(r["sessions"]), _n(r["previous"])]
                                 for r in dash["ai_referrals"]], [0.6, 0.2, 0.2], {1, 2}))
        else:
            story.append(Paragraph("No visits from ChatGPT, Perplexity, Gemini, Copilot or "
                                   "Claude in this period.", S["body"]))
        story.append(Spacer(1, 4))
        story.append(Paragraph("Visits where Google Analytics recorded an AI assistant as the "
                               "referring site. Some AI tools don't pass this on, so the real "
                               "number can be higher.", S["small"]))

    if "search" in sections and gsc:
        story.append(Paragraph("Google search", S["h2"]))
        m = gsc["metrics"]
        story.append(Paragraph(
            f"{_n(m['clicks']['value'])} clicks from {_n(m['impressions']['value'])} searches, "
            f"average position {_n(m['position']['value'], 1)}, click rate "
            f"{_pct(m['ctr']['value'])}. Data through {_d(gsc['through'])}.", S["body"]))
        points = [x for x in series if x["clicks"] is not None]
        if points:
            story.append(KeepTogether([Paragraph("Search clicks per day", S["h3"]), _bar_chart(
                _labels([x["day"] for x in points]), [[x["clicks"] for x in points]],
                [SEARCH])]))
        snapshot = _d(dash["search_snapshot_end"])
        if dash["top_queries"]:
            story.append(KeepTogether([Paragraph("Top Google searches", S["h3"]), _table(
                ["Search", "Clicks", "Impressions", "Click rate", "Position"],
                [[q["query"], _n(q["clicks"]), _n(q["impressions"]), _pct(q["ctr"]),
                  _n(q["position"], 1)] for q in dash["top_queries"]],
                [0.48, 0.12, 0.14, 0.13, 0.13], {1, 2, 3, 4})]))
        if dash["almost_ranking"]:
            story.append(KeepTogether([
                Paragraph("Searches you almost rank for", S["h3"]),
                Paragraph("Positions 8 to 20: just off, or at the bottom of, Google's first "
                          "page. Improving these pages is often the quickest win.", S["small"]),
                _table(["Search", "Page", "Impressions", "Position"],
                       [[a["query"], _path(a["page"]), _n(a["impressions"]),
                         _n(a["position"], 1)] for a in dash["almost_ranking"]],
                       [0.38, 0.36, 0.13, 0.13], {2, 3})]))
        if dash["low_ctr_pages"]:
            story.append(KeepTogether([
                Paragraph("Shown in search, rarely clicked", S["h3"]),
                Paragraph("On Google's first page, but clicked less than half as often as the "
                          f"site's other pages ({_pct(dash['site_ctr'])}). A clearer title and "
                          "description usually help.", S["small"]),
                _table(["Page", "Impressions", "Click rate", "Position"],
                       [[_path(x["page"]), _n(x["impressions"]), _pct(x["ctr"]),
                         _n(x["position"], 1)] for x in dash["low_ctr_pages"]],
                       [0.55, 0.15, 0.15, 0.15], {1, 2, 3})]))
        if snapshot and (dash["top_queries"] or dash["almost_ranking"]
                         or dash["low_ctr_pages"]):
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"The search and page lists cover the 28 days to {snapshot}, "
                                   "Search Console's latest data when the report was made.",
                                   S["small"]))

    if "audit" in sections and audit:
        story.append(Paragraph("Website audit", S["h2"]))
        finished = _d(audit["finished_at"])
        line = (f"{_t(audit['website_name'])}, checked on {finished}: {audit['pages_crawled']} "
                f"pages, {audit['errors']} errors, {audit['warnings']} warnings, "
                f"{audit['notices']} notices.")
        if audit["new_issues"] is not None:
            line += (f" Since the audit before: {audit['new_issues']} new, "
                     f"{audit['fixed_issues']} fixed.")
        story.append(Paragraph(line, S["body"]))
        if len(audit["history"]) > 1:
            h = audit["history"]
            story.append(KeepTogether([
                Paragraph(f"Errors and warnings, last {len(h)} audits", S["h3"]),
                _key([("Errors", ERROR, False), ("Warnings", WARNING, False)]),
                _bar_chart([_short(a["finished_at"]) for a in h],
                           [[a["errors"] for a in h], [a["warnings"] for a in h]],
                           [ERROR, WARNING], height=110)]))
        if data["audit_issues"]:
            story.append(KeepTogether([Paragraph("Issues, most serious first", S["h3"]), _table(
                ["Issue", "Severity", "Count", "How to fix it"],
                [[i["title"], i["severity"].capitalize(), _n(i["count"]), i["fix"]]
                 for i in data["audit_issues"]], [0.26, 0.11, 0.09, 0.54], {2})]))

    story = _glue(story)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, leftMargin=0.75 * inch,
                            rightMargin=0.75 * inch, topMargin=0.75 * inch,
                            bottomMargin=0.75 * inch, title=_plain(report.title),
                            author=_plain(data["prepared_by"]), creator="Outlogik")
    footer = _plain(f"{report.title} · prepared by {data['prepared_by']}")

    def on_page(canvas, document):
        canvas.saveState()
        canvas.setFont("Albert", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(0.75 * inch, 0.45 * inch, footer[:110])
        canvas.drawRightString(LETTER[0] - 0.75 * inch, 0.45 * inch, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return buffer.getvalue()


def _glue(story: list) -> list:
    """Keep each section heading on the same page as the first thing under it (keepWithNext
    alone doesn't hold when that thing is itself a KeepTogether group)."""
    out, i = [], 0
    while i < len(story):
        item = story[i]
        if isinstance(item, Paragraph) and item.style.name == "h2" and i + 1 < len(story):
            group = [item]
            i += 1
            # short lines straight after the heading, then the first block
            while i < len(story) and isinstance(story[i], (Paragraph, Spacer)) \
                    and getattr(story[i].style if isinstance(story[i], Paragraph) else None,
                                "name", "") not in ("h2",) and len(group) < 4:
                group.append(story[i])
                i += 1
            if i < len(story) and not (isinstance(story[i], Paragraph)
                                       and story[i].style.name == "h2"):
                group.append(story[i])
                i += 1
            out.append(KeepTogether(group))
            continue
        out.append(item)
        i += 1
    return out


def _plain(text: str) -> str:
    """For the PDF's metadata and footer (drawn as plain text, not markup)."""
    return "".join(c if ord(c) in _GLYPHS else "?" for c in text)

