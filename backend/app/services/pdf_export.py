"""PDF Report Exports — server-side, byte-streamed, no temp files.

Two public functions render the two PDF surfaces specified by
docs/specs/feature-pdf-report-exports.md §3.5 / §3.6:

- ``generate_build_pdf(build, *, student_name, audience_questions)`` —
  the 2-page My Build PDF for a single build.
- ``generate_comparison_pdf(builds)`` — the 1-page (2-max) Comparison
  PDF for 2-3 builds at the same major.

Both return ``bytes``; neither writes to disk. RPG language is
forbidden — see ``pdf_copy.RPG_TERMS_FORBIDDEN_IN_PDF``. Risk-level
chip rendering, verdict line, glossary copy, "Insufficient data"
chip, and data-coverage caveat all live in ``pdf_copy``.

Implementation notes:
- ReportLab Platypus + ``BaseDocTemplate`` + ``PageTemplate``. Two
  templates per doc ("main" and "last") so the sources citation can
  be drawn by the canvas callback on the final page only — without
  this it orphans to an unwanted extra page.
- Fonts ship at ``backend/app/services/pdf_fonts/``. Lazy registration
  on first call. If any font is missing, falls back to Helvetica with a
  WARNING log so the export still ships in degraded environments.
- Pentagon vertex labels render the stat abbreviations (ERN/ROI/RES/
  GRW/AURA) — these are intentionally NOT in
  ``RPG_TERMS_FORBIDDEN_IN_PDF`` because the chrome renders them.
"""

from __future__ import annotations

import io
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

from reportlab.graphics.shapes import Circle, Drawing, Line, Polygon, String
from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.models.api import AudienceQuestions, RiskLevel
from app.models.career import Build, SkillRec
from app.services.career_description import (
    DISCLAIMER_TIER_B,
    DISCLAIMER_TIER_C,
)
from app.services.pdf_copy import (
    BOSS_ORDER,
    RPG_TERMS_FORBIDDEN_IN_PDF,
    boss_advisory_label,
    contains_forbidden_term,
    data_coverage_caveat,
    risk_level_for_boss,
    risk_one_liner,
    verdict_line,
    where_each_pulls_ahead,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Font registration (lazy, per-process; cached after first call).
# ---------------------------------------------------------------------------

_FONT_DIR = Path(__file__).parent / "pdf_fonts"
_FONT_FILES = {
    "FredokaOne": "FredokaOne-Regular.ttf",
    "Nunito": "Nunito-Regular.ttf",
    "NunitoBold": "Nunito-Bold.ttf",
    "NunitoItalic": "Nunito-Italic.ttf",
    "SpaceMono": "SpaceMono-Regular.ttf",
}
_FONT_FALLBACK = {
    "FredokaOne": "Helvetica-Bold",
    "Nunito": "Helvetica",
    "NunitoBold": "Helvetica-Bold",
    "NunitoItalic": "Helvetica-Oblique",
    "SpaceMono": "Courier",
}
_FONTS_REGISTERED = False
_FONT_NAMES: dict[str, str] = {}
_FONTS_LOCK = __import__("threading").Lock()


def _register_fonts() -> dict[str, str]:
    """Register the 5 TTFs once per process. Returns name → resolved-name.

    If a TTF is missing, the corresponding key maps to its Helvetica/
    Courier fallback. The PDF still renders; it just looks generic.

    Thread-safe via _FONTS_LOCK — FastAPI runs sync handlers in a thread
    pool, so two concurrent first-call requests could otherwise race the
    ReportLab font-registry mutation.
    """
    global _FONTS_REGISTERED, _FONT_NAMES
    if _FONTS_REGISTERED:
        return _FONT_NAMES
    with _FONTS_LOCK:
        if _FONTS_REGISTERED:
            return _FONT_NAMES
        resolved: dict[str, str] = {}
        for name, filename in _FONT_FILES.items():
            path = _FONT_DIR / filename
            if path.exists():
                try:
                    pdfmetrics.registerFont(TTFont(name, str(path)))
                    resolved[name] = name
                    continue
                except Exception as exc:
                    logger.warning(
                        "pdf_export: font registration failed for %s: %s — "
                        "falling back to %s",
                        name, exc, _FONT_FALLBACK[name],
                    )
            else:
                logger.warning(
                    "pdf_export: font file missing %s — falling back to %s",
                    path, _FONT_FALLBACK[name],
                )
            resolved[name] = _FONT_FALLBACK[name]
        _FONT_NAMES = resolved
        _FONTS_REGISTERED = True
        return resolved


def _font(name: str) -> str:
    """Return the resolved font name (TTF or platform fallback)."""
    return _register_fonts().get(name, name)


def _safe(text: str | None) -> str:
    """XML-escape user-controlled text before passing to ReportLab Paragraph.

    ReportLab Paragraph parses its input as mini-XML — a bare `<` in any
    user-controlled string raises ValueError mid-render. Gemma can emit
    `<5%`, `<Python>`, etc.; a student-typed name `<3 design` does the
    same thing. This wraps every user-controlled or LLM-derived string
    that flows into a Paragraph. Defends against staff-engineer S1.
    """
    if text is None:
        return ""
    return _xml_escape(str(text))


# ---------------------------------------------------------------------------
# Print color tokens (§3.4).
# ---------------------------------------------------------------------------

INK_PRIMARY = HexColor("#1A1B2E")
INK_SECONDARY = HexColor("#3D3E52")
INK_MUTED = HexColor("#767888")
RULE_LIGHT = HexColor("#D9DAE4")
BG_ROW_ALT = HexColor("#F7F7FB")

STAT_ERN = HexColor("#C8A820")
STAT_ROI = HexColor("#3DA86A")
STAT_RES = HexColor("#7B66C8")
STAT_GRW = HexColor("#3D8BB8")
STAT_AURA = HexColor("#C47090")

RISK_INK = {
    "Low": HexColor("#2D7A4F"),
    "Moderate": HexColor("#7A6A20"),
    "Elevated": HexColor("#B84C20"),
    "High": HexColor("#8B1A1A"),
    "Insufficient": HexColor("#5C5E70"),
}
RISK_BG = {
    "Low": HexColor("#E8F5EE"),
    "Moderate": HexColor("#FFF8E0"),
    "Elevated": HexColor("#FFF0E8"),
    "High": HexColor("#FCEAEA"),
    "Insufficient": HexColor("#EFF0F4"),
}

LEADING_CELL_BG = HexColor("#EBF9F1")
LEADING_CELL_INK = HexColor("#1A5C38")

STAT_COLORS = {
    "ern": STAT_ERN, "roi": STAT_ROI, "res": STAT_RES,
    "grw": STAT_GRW, "aura": STAT_AURA,
}
STAT_LABELS = {"ern": "ERN", "roi": "ROI", "res": "RES", "grw": "GRW", "aura": "AURA"}
STAT_MEANINGS = {
    "ern": "Earnings",
    "roi": "Return on Investment",
    "res": "AI Resilience",
    "grw": "Growth",
    "aura": "Brand Gravity",
}


# ---------------------------------------------------------------------------
# Page geometry (§3.2).
# ---------------------------------------------------------------------------

PW, PH = letter
MARGIN_L = 0.65 * inch
MARGIN_R = 0.65 * inch
MARGIN_T = 0.90 * inch
MARGIN_B = 0.70 * inch
LIVE_W = PW - MARGIN_L - MARGIN_R
FOOTER_Y = 0.45 * inch

SOURCES_LINE = (
    "Sources: BLS OOH · College Scorecard · O*NET · Karpathy AI Exposure · "
    "BEA RPP. Powered by Gemma 4."
)


# ---------------------------------------------------------------------------
# Style helpers.
# ---------------------------------------------------------------------------


def _style(name: str, **kw: object) -> ParagraphStyle:
    """ParagraphStyle factory with project defaults."""
    base: dict[str, object] = dict(
        fontName=_font("Nunito"), fontSize=9, leading=13,
        textColor=INK_SECONDARY, leftIndent=0, rightIndent=0,
        spaceAfter=0, spaceBefore=0, alignment=TA_LEFT,
    )
    base.update(kw)
    return ParagraphStyle(name, **base)


def _styles() -> dict[str, ParagraphStyle]:
    """Return the canonical style dict. Cheap to call repeatedly."""
    fred = _font("FredokaOne")
    nuni = _font("Nunito")
    nunb = _font("NunitoBold")
    sm = _font("SpaceMono")
    return {
        "verdict": _style("verdict", fontName=fred, fontSize=20, leading=26,
                          textColor=INK_PRIMARY),
        "section": _style("section", fontName=fred, fontSize=11, leading=13,
                          textColor=INK_PRIMARY),
        "section_compact": _style("sectionC", fontName=fred, fontSize=9, leading=11,
                                  textColor=INK_PRIMARY),
        "subsection": _style("subsection", fontName=nunb, fontSize=8, leading=10,
                             textColor=INK_SECONDARY),
        "body": _style("body", fontName=nuni, fontSize=9, leading=13),
        "body_sm": _style("body_sm", fontName=nuni, fontSize=8, leading=11),
        "muted": _style("muted", fontName=nuni, fontSize=7.5, leading=10,
                        textColor=INK_MUTED),
        "stat_value": _style("stat_value", fontName=sm, fontSize=13, leading=16,
                             textColor=INK_PRIMARY),
        "stat_label": _style("stat_label", fontName=nunb, fontSize=7.5, leading=10),
        "stat_meaning": _style("stat_meaning", fontName=nuni, fontSize=8, leading=11),
        "data": _style("data", fontName=sm, fontSize=9, leading=12,
                       textColor=INK_PRIMARY),
        "footer": _style("footer", fontName=nuni, fontSize=7, leading=9,
                         textColor=INK_MUTED),
        "caveat": _style("caveat", fontName=nuni, fontSize=7.5, leading=10,
                         textColor=INK_MUTED, alignment=TA_LEFT),
        "school_name": _style("school_name", fontName=nunb, fontSize=9, leading=12,
                              textColor=INK_PRIMARY, alignment=TA_CENTER),
        "comp_value": _style("comp_value", fontName=sm, fontSize=10, leading=13,
                             textColor=INK_PRIMARY, alignment=TA_CENTER),
        "comp_lead": _style("comp_lead", fontName=sm, fontSize=10, leading=13,
                            textColor=LEADING_CELL_INK, alignment=TA_CENTER),
    }


# ---------------------------------------------------------------------------
# Pentagon drawing.
# ---------------------------------------------------------------------------


def _draw_pentagon(
    stats: dict[str, int | None],
    r: float,
    *,
    show_value_labels: bool = True,
    show_stat_labels: bool = True,
    label_font_size: float = 6.5,
) -> Drawing:
    label_offset = r * 0.28
    label_pad = label_font_size * 1.6 + (label_font_size if show_value_labels else 0)
    max_extent = r + label_offset + label_pad
    w = h = max_extent * 2
    cx = cy = w / 2
    d = Drawing(w, h)

    keys = ["ern", "roi", "res", "grw", "aura"]
    angles = [math.radians(-90 + 72 * i) for i in range(5)]

    for scale in [0.25, 0.50, 0.75, 1.0]:
        pts: list[float] = []
        for a in angles:
            pts += [cx + r * scale * math.cos(a), cy + r * scale * math.sin(a)]
        d.add(Polygon(pts, fillColor=None, strokeColor=RULE_LIGHT,
                      strokeWidth=0.5 if scale < 1.0 else 0.8))
    for a in angles:
        d.add(Line(cx, cy, cx + r * math.cos(a), cy + r * math.sin(a),
                   strokeColor=RULE_LIGHT, strokeWidth=0.5))

    stat_pts: list[float] = []
    for i, key in enumerate(keys):
        v = stats.get(key)
        frac = (v / 10.0) if v is not None else 0.0
        a = angles[i]
        stat_pts += [cx + r * frac * math.cos(a), cy + r * frac * math.sin(a)]
    d.add(Polygon(stat_pts,
                  fillColor=Color(0.24, 0.40, 0.72, 0.12),
                  strokeColor=Color(0.24, 0.40, 0.72, 0.60),
                  strokeWidth=1.2))

    for i, key in enumerate(keys):
        v = stats.get(key)
        if v is None:
            continue
        frac = v / 10.0
        a = angles[i]
        d.add(Circle(cx + r * frac * math.cos(a), cy + r * frac * math.sin(a),
                     3, fillColor=STAT_COLORS[key], strokeColor=None))

    for i, key in enumerate(keys):
        a = angles[i]
        lx = cx + (r + label_offset) * math.cos(a)
        ly = cy + (r + label_offset) * math.sin(a)
        if show_stat_labels:
            d.add(String(lx, ly + 2, STAT_LABELS[key],
                         fontName=_font("NunitoBold"),
                         fontSize=label_font_size,
                         fillColor=STAT_COLORS[key],
                         textAnchor="middle"))
        v = stats.get(key)
        if show_value_labels and v is not None:
            d.add(String(lx, ly - label_font_size - 1, f"{v}/10",
                         fontName=_font("SpaceMono"),
                         fontSize=label_font_size - 1,
                         fillColor=INK_SECONDARY,
                         textAnchor="middle"))
    return d


# ---------------------------------------------------------------------------
# Header / footer canvas callbacks.
# ---------------------------------------------------------------------------


def _draw_sparkle(canvas: object, cx: float, cy: float, size: float) -> None:
    outer = size
    inner = size * 0.28
    p = canvas.beginPath()  # type: ignore[attr-defined]
    first = True
    for i in range(4):
        a_out = math.radians(90 * i - 90)
        ox = cx + outer * math.cos(a_out)
        oy = cy + outer * math.sin(a_out)
        a_in = math.radians(90 * i - 90 + 45)
        ix = cx + inner * math.cos(a_in)
        iy = cy + inner * math.sin(a_in)
        if first:
            p.moveTo(ox, oy)
            first = False
        else:
            p.lineTo(ox, oy)
        p.lineTo(ix, iy)
    p.close()
    canvas.drawPath(p, fill=1, stroke=0)  # type: ignore[attr-defined]


def _make_callbacks(title: str) -> tuple[object, object]:
    def on_page(canvas: object, doc: object) -> None:  # noqa: ANN401
        canvas.saveState()  # type: ignore[attr-defined]
        # Header band
        canvas.setFillColor(INK_PRIMARY)  # type: ignore[attr-defined]
        canvas.rect(0, PH - 0.55 * inch, PW, 0.55 * inch, fill=1, stroke=0)  # type: ignore[attr-defined]
        # Sparkle + wordmark
        STAR_SIZE = 5.5
        WORDMARK_Y = PH - 0.32 * inch
        canvas.setFillColor(white)  # type: ignore[attr-defined]
        _draw_sparkle(canvas, MARGIN_L + STAR_SIZE, WORDMARK_Y + 3.2, STAR_SIZE)
        wordmark_x = MARGIN_L + STAR_SIZE * 2 + 4
        canvas.setFont(_font("NunitoBold"), 9)  # type: ignore[attr-defined]
        canvas.drawString(wordmark_x, WORDMARK_Y, "FUTUREPROOF")  # type: ignore[attr-defined]
        canvas.setFont(_font("Nunito"), 7.5)  # type: ignore[attr-defined]
        canvas.setFillColor(HexColor("#B8BCD4"))  # type: ignore[attr-defined]
        canvas.drawRightString(  # type: ignore[attr-defined]
            PW - MARGIN_R, PH - 0.32 * inch, "FOR STUDENT + COUNSELOR USE ONLY",
        )
        # Gold rule
        canvas.setStrokeColor(STAT_ERN)  # type: ignore[attr-defined]
        canvas.setLineWidth(0.75)  # type: ignore[attr-defined]
        canvas.line(MARGIN_L, PH - 0.57 * inch, PW - MARGIN_R, PH - 0.57 * inch)  # type: ignore[attr-defined]
        # Footer rule
        canvas.setStrokeColor(RULE_LIGHT)  # type: ignore[attr-defined]
        canvas.setLineWidth(0.5)  # type: ignore[attr-defined]
        canvas.line(MARGIN_L, FOOTER_Y, PW - MARGIN_R, FOOTER_Y)  # type: ignore[attr-defined]
        # Footer text
        canvas.setFont(_font("Nunito"), 7)  # type: ignore[attr-defined]
        canvas.setFillColor(INK_MUTED)  # type: ignore[attr-defined]
        canvas.drawString(MARGIN_L, FOOTER_Y - 11, title)  # type: ignore[attr-defined]
        canvas.drawRightString(  # type: ignore[attr-defined]
            PW - MARGIN_R, FOOTER_Y - 11, f"Page {doc.page}",  # type: ignore[attr-defined]
        )
        canvas.restoreState()  # type: ignore[attr-defined]

    def on_last_page(canvas: object, doc: object) -> None:  # noqa: ANN401
        on_page(canvas, doc)
        canvas.saveState()  # type: ignore[attr-defined]
        canvas.setFont(_font("Nunito"), 6)  # type: ignore[attr-defined]
        canvas.setFillColor(INK_MUTED)  # type: ignore[attr-defined]
        # Two-line wrap if needed.
        src = SOURCES_LINE
        if len(src) > 90:
            mid = len(src) // 2
            split = src.rfind("  ", 0, mid + 20)
            if split == -1:
                split = src.find("  ", mid - 20)
            if split == -1:
                split = mid
            line1 = src[:split].strip()
            line2 = src[split:].strip()
        else:
            line1 = src
            line2 = ""
        canvas.drawString(MARGIN_L, 14, line1)  # type: ignore[attr-defined]
        if line2:
            canvas.drawString(MARGIN_L, 7, line2)  # type: ignore[attr-defined]
        canvas.restoreState()  # type: ignore[attr-defined]

    return on_page, on_last_page


# ---------------------------------------------------------------------------
# Section header pattern (§3.7).
# ---------------------------------------------------------------------------


def _section_header(label: str, *, compact: bool = False) -> list[object]:
    s = _styles()
    spacer_h = 3 if compact else 7
    return [
        Spacer(1, spacer_h),
        Paragraph(label, s["section_compact"] if compact else s["section"]),
        HRFlowable(
            width="100%", thickness=0.75, color=RULE_LIGHT,
            spaceBefore=1, spaceAfter=2 if compact else 3,
        ),
    ]


def _subsec_header(label: str, color: HexColor = INK_SECONDARY, spacer: int = 5) -> Paragraph:
    return Paragraph(
        label,
        _style(f"subsection_inline_{spacer}", fontName=_font("NunitoBold"),
               fontSize=8, leading=10, textColor=color, spaceBefore=spacer,
               spaceAfter=1),
    )


# ---------------------------------------------------------------------------
# Risk chip rendering — handles both ALL-CAPS bands AND italic Insufficient.
# ---------------------------------------------------------------------------


def _risk_chip_paragraph(level: RiskLevel) -> Paragraph:
    if level == "Insufficient":
        # Italic Roman sentence-case per §3.4 — italic is the redundant
        # visual differentiator that makes this chip read distinct from
        # "Low" (also a quiet/non-bold band) in B&W photocopy.
        return Paragraph(
            "Insufficient data",
            _style(
                f"chip_{level}",
                fontName=_font("NunitoItalic"),
                fontSize=7.5, leading=10,
                textColor=RISK_INK[level],
                alignment=TA_CENTER,
            ),
        )
    # Low gets quieter weight than warning levels (B&W diff per §3.4).
    font = _font("Nunito") if level == "Low" else _font("NunitoBold")
    return Paragraph(
        level.upper(),
        _style(
            f"chip_{level}",
            fontName=font, fontSize=7.5, leading=10,
            textColor=RISK_INK[level],
            alignment=TA_CENTER,
        ),
    )


# ---------------------------------------------------------------------------
# Document builder.
# ---------------------------------------------------------------------------


def _make_doc(buf: io.BytesIO, title: str) -> BaseDocTemplate:
    doc = BaseDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=title, author="FutureProof",
        subject="Career outcome data for student planning",
        keywords="career, college, major, outcomes, earnings",
        lang="en-US",
    )
    frame = Frame(MARGIN_L, MARGIN_B, LIVE_W, PH - MARGIN_T - MARGIN_B,
                  id="main", showBoundary=0)
    on_page, on_last_page = _make_callbacks(title)
    doc.addPageTemplates([
        PageTemplate(id="main", frames=[frame], onPage=on_page),
        PageTemplate(id="last", frames=[frame], onPage=on_last_page),
    ])
    return doc


# ---------------------------------------------------------------------------
# My Build PDF — page 1.
# ---------------------------------------------------------------------------


def _fmt_currency(v: float | None) -> str:
    if v is None:
        return "—"
    return f"${v:,.0f}"


def _fmt_pct(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.0f}%"


def _about_this_career_section(build: Build) -> list[object]:
    """Render the page-1 "About this career" section.

    Sits between verdict line and pentagon. Skipped silently when:
        - ``build.career_description is None`` (most common — no eager
          fetch, lazy fetch failed, or older serialized build before
          this feature shipped)
        - Defensive voice/length checks fail (forbidden term slipped
          through both eager and lazy validators, summary too long, or
          fewer than 4 tasks)

    Reuses ``_section_header()``, ``_subsec_header()``, ``s["body"]``,
    and the existing italic caveat idiom from line ~592 — no new fonts,
    styles, or colors. Tier B/C generations include a one-line italic
    disclaimer; Tier A renders no disclaimer.
    """
    desc = build.career_description
    if desc is None:
        return []

    # Defensive last line of defense — these should already be enforced
    # upstream (Pydantic validator + service-side voice check), but the
    # PDF render is downstream of cache + persistence and self-defends.
    summary = desc.summary
    tasks = desc.tasks
    if not summary or len(summary) > 500:
        return []
    if not (4 <= len(tasks) <= 6):
        return []
    combined = summary + " " + " ".join(tasks)
    if contains_forbidden_term(combined, RPG_TERMS_FORBIDDEN_IN_PDF):
        logger.warning(
            "pdf_export: forbidden term in career_description for soc=%s — "
            "skipping section.",
            build.career.soc_code,
        )
        return []

    s = _styles()
    story: list[object] = []

    story.extend(_section_header("ABOUT THIS CAREER"))
    story.append(Paragraph(_safe(summary), s["body"]))
    story.append(_subsec_header("Day-to-day", spacer=5))

    # Bullets — hanging-indent paragraphs reusing s["body"]. Match the
    # density of the existing risk-profile rows.
    bullet_style = _style(
        "career_desc_bullet",
        fontName=_font("Nunito"), fontSize=9, leading=13,
        textColor=INK_SECONDARY,
        leftIndent=10, firstLineIndent=-10, spaceAfter=1,
    )
    for task in tasks:
        story.append(Paragraph(f"&bull;&nbsp;&nbsp;{_safe(task)}", bullet_style))

    # Tier B/C disclaimer line — italic 7.5pt INK_MUTED, same treatment
    # as the existing data-coverage caveat at pdf_export.py:590–594.
    if desc.anchor_tier in {"description_only", "title_only"}:
        story.append(Spacer(1, 4))
        disclaimer = (
            DISCLAIMER_TIER_B
            if desc.anchor_tier == "description_only"
            else DISCLAIMER_TIER_C
        )
        story.append(
            Paragraph(
                _safe(disclaimer),
                _style(
                    "career_desc_disclaimer",
                    fontName=_font("NunitoItalic"),
                    fontSize=7.5,
                    leading=10,
                    textColor=INK_MUTED,
                ),
            )
        )

    story.append(Spacer(1, 8))
    return story


def _build_page1(build: Build, student_name: str | None) -> list[object]:
    s = _styles()
    story: list[object] = []

    # Profile + context strip
    display_name = (student_name or build.profile_name or "").strip() or "Student plan"
    emoji = build.animal_emoji or ""
    name_label = f"{emoji}  {display_name}".strip()
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    major = build.career.program_name or build.major_text or "Program"
    hdr_left = Paragraph(
        _safe(name_label),
        _style("hdr_name", fontName=_font("FredokaOne"), fontSize=14, leading=18,
               textColor=INK_PRIMARY),
    )
    hdr_right = Paragraph(
        f"{_safe(build.school_name)}  ·  {_safe(major)}  ·  As of {today}",
        _style("hdr_meta", fontName=_font("Nunito"), fontSize=8.5, leading=11,
               textColor=INK_SECONDARY, alignment=TA_RIGHT),
    )
    hdr_table = Table([[hdr_left, hdr_right]],
                      colWidths=[LIVE_W * 0.45, LIVE_W * 0.55])
    hdr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(Spacer(1, 4))
    story.append(hdr_table)

    # Residency hint (muted, optional)
    if build.home_state and not build.career.is_out_of_state:
        story.append(Paragraph(
            f"Residency: in-state, {_safe(build.home_state)}", s["muted"],
        ))
    elif build.career.is_out_of_state:
        story.append(Paragraph("Residency: out-of-state", s["muted"]))

    # Conditional data-coverage caveat (§3.5 / §3.11.5).
    # Italic Nunito 7.5pt INK_MUTED — italic is the load-bearing visual cue
    # for the FYI register (designer audit FAIL fix).
    caveat = data_coverage_caveat(build)
    if caveat:
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            _safe(caveat),
            _style("caveat_line", fontName=_font("NunitoItalic"), fontSize=7.5,
                   leading=10, textColor=INK_MUTED),
        ))
        story.append(Spacer(1, 9))
    else:
        story.append(Spacer(1, 6))

    # Profile-strip separator: 0.75pt RULE_LIGHT per §3.5 (NOT 1pt INK_PRIMARY).
    story.append(HRFlowable(width="100%", thickness=0.75, color=RULE_LIGHT,
                            spaceAfter=8))

    # Verdict line
    story.append(Paragraph(_safe(verdict_line(build)), s["verdict"]))
    story.append(Spacer(1, 8))

    # "About this career" section (feature-career-description-on-pdf.md).
    # Sits between verdict line and pentagon. Silently skipped when no
    # description is attached or when defensive voice/length checks fail.
    story.extend(_about_this_career_section(build))

    # Pentagon + stat micro-table
    stats_dict = {
        "ern": build.career.stats.ern,
        "roi": build.career.stats.roi,
        "res": build.career.stats.res,
        "grw": build.career.stats.grw,
        "aura": build.career.stats.aura,
    }
    pentagon = _draw_pentagon(stats_dict, 0.72 * inch)
    stat_rows = []
    for key in ("ern", "roi", "res", "grw", "aura"):
        val = stats_dict[key]
        val_str = f"{val}/10" if val is not None else "—"
        dot_style = _style(
            f"dot_{key}", fontName=_font("NunitoBold"), fontSize=10, leading=13,
            textColor=STAT_COLORS[key],
        )
        stat_rows.append([
            Paragraph("●", dot_style),
            Paragraph(STAT_LABELS[key], s["stat_label"]),
            Paragraph(val_str, s["data"]),
            Paragraph(STAT_MEANINGS[key], s["stat_meaning"]),
        ])
    stat_table = Table(stat_rows,
                       colWidths=[0.18 * inch, 0.45 * inch, 0.55 * inch, 2.00 * inch],
                       rowHeights=[0.22 * inch] * 5)
    stat_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE_LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, BG_ROW_ALT]),
    ]))
    pent_w = pentagon.width
    pent_stat_table = Table([[pentagon, stat_table]],
                            colWidths=[pent_w + 4, LIVE_W - pent_w - 4])
    pent_stat_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(pent_stat_table)
    story.append(Spacer(1, 8))

    # Cost & ROI strip — 4-year cost · modeled debt · year-1 earnings · debt-to-earnings %
    story.extend(_section_header("COST & ROI"))
    label_style = _style(
        "cost_label", fontName=_font("NunitoBold"), fontSize=8, leading=10,
        textColor=INK_SECONDARY, alignment=TA_CENTER,
    )
    value_style = _style(
        "cost_value", fontName=_font("SpaceMono"), fontSize=9, leading=12,
        textColor=INK_PRIMARY, alignment=TA_CENTER,
    )
    cost_data = [[
        Paragraph("4-year cost", label_style),
        Paragraph("Modeled debt", label_style),
        Paragraph("Year-1 median earnings", label_style),
        Paragraph("Debt-to-earnings (yr-1)", label_style),
    ], [
        Paragraph(_fmt_currency(build.career.published_cost_4yr), value_style),
        Paragraph(_fmt_currency(build.career.modeled_total_debt), value_style),
        Paragraph(_fmt_currency(build.career.earnings_1yr_median), value_style),
        Paragraph(_fmt_pct(build.career.debt_to_earnings_annual), value_style),
    ]]
    cw = LIVE_W / 4
    cost_table = Table(cost_data, colWidths=[cw] * 4)
    cost_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, -1), BG_ROW_ALT),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBEFORE", (1, 0), (-1, -1), 0.5, RULE_LIGHT),
    ]))
    story.append(cost_table)
    story.append(Spacer(1, 8))

    # Career Risk Profile — 5 rows
    story.extend(_section_header("CAREER RISK PROFILE"))
    hdr_style = _style(
        "risk_hdr", fontName=_font("NunitoBold"), fontSize=8, leading=10,
        textColor=white, alignment=TA_LEFT,
    )
    hdr_center = _style(
        "risk_hdr_c", fontName=_font("NunitoBold"), fontSize=8, leading=10,
        textColor=white, alignment=TA_CENTER,
    )
    risk_rows: list[list[object]] = [[
        Paragraph("Risk Factor", hdr_style),
        Paragraph("Level", hdr_center),
        Paragraph("Context", hdr_style),
    ]]
    cell_styles: list[object] = []
    for row_i, boss in enumerate(BOSS_ORDER, start=1):
        fight = next((f for f in build.gauntlet.fights if f.boss == boss), None)
        raw_score = fight.raw_score if fight else None
        level = risk_level_for_boss(boss, raw_score)
        context = (
            "Data unavailable for this program."
            if level == "Insufficient"
            else risk_one_liner(boss, level, build)
        )
        risk_rows.append([
            Paragraph(boss_advisory_label(boss), s["body_sm"]),
            _risk_chip_paragraph(level),
            Paragraph(
                _safe(context),
                _style("ctx", fontName=_font("Nunito"), fontSize=8, leading=11,
                       textColor=INK_SECONDARY),
            ),
        ])
        cell_styles.append(("BACKGROUND", (1, row_i), (1, row_i), RISK_BG[level]))

    # Level column widened to 1.10in to fit "Insufficient data" italic chip.
    risk_col_w = [1.65 * inch, 1.10 * inch, LIVE_W - 1.65 * inch - 1.10 * inch]
    risk_table = Table(risk_rows, colWidths=risk_col_w, repeatRows=1)
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("FONTNAME", (0, 1), (-1, -1), _font("Nunito")),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_ROW_ALT]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE_LIGHT),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, RULE_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        *cell_styles,
    ]))
    story.append(risk_table)
    return story


# ---------------------------------------------------------------------------
# My Build PDF — page 2.
# ---------------------------------------------------------------------------


_BUCKET_HINTS = (
    ("AI-Resilience", STAT_RES, ("ai", "automation", "resilience")),
    ("Career-Launch", STAT_ROI, ("internship", "launch", "career")),
    ("Earnings-Ceiling", STAT_ERN, ("ceiling", "earnings", "salary")),
)


def _classify_skill_bucket(rec: SkillRec) -> str:
    """Coarse-bucket a SkillRec by stat_impact keywords. Falls back evenly."""
    text = (rec.stat_impact or "").lower() + " " + (rec.title or "").lower()
    for bucket, _color, hints in _BUCKET_HINTS:
        if any(h in text for h in hints):
            return bucket
    return "Career-Launch"


def _build_page2(build: Build, audience_questions: AudienceQuestions) -> list[object]:
    story: list[object] = []

    # SUGGESTED SKILLS
    story.extend(_section_header("SUGGESTED SKILLS"))
    intro_style = _style("intro", fontName=_font("Nunito"), fontSize=8, leading=11,
                         textColor=INK_SECONDARY, spaceAfter=2)
    story.append(Paragraph(
        "Bring this list to your admissions counselor — these are the skills "
        "the data says will lift your outcomes.",
        intro_style,
    ))

    bucket_color_map = {
        "AI-Resilience": STAT_RES,
        "Career-Launch": STAT_ROI,
        "Earnings-Ceiling": STAT_ERN,
    }

    # Group up to 6 skills into 3 buckets.
    grouped: dict[str, list[SkillRec]] = {b: [] for b, _, _ in _BUCKET_HINTS}
    for rec in build.skill_recs[:12]:  # consider a few more, cap at 6 below
        grouped[_classify_skill_bucket(rec)].append(rec)
    flat_capped: list[tuple[str, SkillRec]] = []
    for bucket_name in ("AI-Resilience", "Career-Launch", "Earnings-Ceiling"):
        for rec in grouped[bucket_name][:2]:
            flat_capped.append((bucket_name, rec))
    # Bring count up to 6 if buckets had fewer than 2 — fill from any leftovers.
    if len(flat_capped) < 6:
        leftovers = [
            (b, r) for b in ("AI-Resilience", "Career-Launch", "Earnings-Ceiling")
            for r in grouped[b][2:]
        ]
        for item in leftovers:
            if len(flat_capped) >= 6:
                break
            flat_capped.append(item)

    last_bucket: str | None = None
    for bucket_name, rec in flat_capped:
        if bucket_name != last_bucket:
            color = bucket_color_map.get(bucket_name, INK_SECONDARY)
            story.append(_subsec_header(f"{bucket_name.upper()} SKILLS",
                                        color=color, spacer=4))
            last_bucket = bucket_name

        title_style = _style(
            "skill_title", fontName=_font("NunitoBold"), fontSize=8.5, leading=11,
            textColor=INK_PRIMARY,
        )
        story.append(Paragraph(f"• {_safe(rec.title)}", title_style))

        rationale_style = _style(
            "skill_rat", fontName=_font("Nunito"), fontSize=7.5, leading=10,
            textColor=INK_MUTED, leftIndent=10,
        )
        if rec.stat_impact:
            story.append(Paragraph(_safe(rec.stat_impact), rationale_style))

        # Blank-line table: Coursework | Clubs/orgs | Internship/cert.
        blank_hdr_style = _style(
            "blank_hdr", fontName=_font("Nunito"), fontSize=7, leading=9,
            textColor=INK_MUTED, alignment=TA_CENTER,
        )
        blank_data = [
            [
                Paragraph("Coursework", blank_hdr_style),
                Paragraph("Clubs / orgs", blank_hdr_style),
                Paragraph("Internship / cert", blank_hdr_style),
            ],
            [
                Paragraph("", blank_hdr_style),
                Paragraph("", blank_hdr_style),
                Paragraph("", blank_hdr_style),
            ],
        ]
        blank_cw = (LIVE_W - 10) / 3
        blank_table = Table(blank_data, colWidths=[blank_cw] * 3, rowHeights=[9, 12])
        blank_table.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 1),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ("BACKGROUND", (0, 0), (-1, -1), BG_ROW_ALT),
            ("LINEBELOW", (0, 1), (-1, 1), 1.2, INK_SECONDARY),
            ("LINEBEFORE", (1, 0), (2, -1), 0.4, RULE_LIGHT),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ]))
        story.append(Spacer(1, 2))
        story.append(blank_table)

        # Counselor question (rationale fallback if empty).
        if rec.rationale:
            ask_style = _style(
                "ask_prompt", fontName=_font("Nunito"), fontSize=7, leading=9,
                textColor=STAT_GRW, leftIndent=10,
            )
            story.append(Paragraph(f'Ask: "{_safe(rec.rationale)}"', ask_style))
        story.append(Spacer(1, 2))

    story.append(HRFlowable(width="100%", thickness=1.0, color=INK_PRIMARY,
                            spaceBefore=2, spaceAfter=2))

    # QUESTIONS & FOLLOW-UPS
    story.extend(_section_header("QUESTIONS & FOLLOW-UPS"))
    audience_blocks = (
        ("ASK THE COLLEGE", STAT_ROI, audience_questions.ask_the_college),
        ("ASK YOUR PARENTS", STAT_GRW, audience_questions.ask_your_parents),
        ("ASK YOURSELF", STAT_RES, audience_questions.ask_yourself),
    )
    for label, color, qs in audience_blocks:
        story.append(_subsec_header(label, color=color, spacer=3))
        for q in qs:
            q_style = _style(
                f"q_{label}", fontName=_font("Nunito"), fontSize=8.5, leading=12,
                textColor=INK_SECONDARY, leftIndent=8,
            )
            story.append(Paragraph(f"• {_safe(q.text)}", q_style))
        story.append(Spacer(1, 1))

    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE_LIGHT,
                            spaceBefore=2, spaceAfter=3))

    # GLOSSARY (4-column, 2-pair layout, 8 entries)
    story.append(Paragraph(
        "GLOSSARY",
        _style("gloss_hdr", fontName=_font("FredokaOne"), fontSize=9, leading=11,
               textColor=INK_PRIMARY, spaceBefore=2, spaceAfter=1),
    ))
    # Copy verbatim from §3.11.3 (designer audit FAIL fix — 3 entries had
    # been truncated). Glossary text is fixed copy and not user-controlled,
    # so it doesn't go through _safe().
    glossary = [
        ("CIP", "Federal program code (Classification of Instructional Programs) — the standard for naming college majors."),
        ("SOC", "Federal occupation code (Standard Occupational Classification) — how the BLS names jobs."),
        ("ERN", "Earnings — typical pay for graduates of this program working in this occupation."),
        ("ROI", "Return on Investment — how the cost of this program compares to what graduates earn."),
        ("RES", "AI Resilience — how much of this occupation's work is hard for AI to do, blended from task-level data."),
        ("GRW", "Growth — the BLS 10-year employment-change projection for this occupation."),
        ("AURA", "Brand Gravity — institutional pull (selectivity, completion, financial standing) shared by every program at the school."),
        ("Career risk", "Five factors that affect long-term outcomes: AI displacement, debt burden, job market, burnout, and earnings ceiling."),
    ]
    half = (len(glossary) + 1) // 2
    left = glossary[:half]
    right = glossary[half:]
    term_w = 0.55 * inch
    def_w = (LIVE_W / 2) - term_w - 0.04 * inch
    # 8pt per §3.5 (designer audit FAIL fix — was 7.5pt).
    term_style = _style("gterm", fontName=_font("NunitoBold"), fontSize=8,
                        leading=11, textColor=INK_PRIMARY)
    def_style = _style("gdef", fontName=_font("Nunito"), fontSize=8,
                       leading=11, textColor=INK_SECONDARY)
    rows: list[list[object]] = []
    for i in range(half):
        l_term, l_def = left[i]
        row: list[object] = [Paragraph(l_term, term_style), Paragraph(l_def, def_style)]
        if i < len(right):
            r_term, r_def = right[i]
            row += [Paragraph(r_term, term_style), Paragraph(r_def, def_style)]
        else:
            row += [Paragraph("", def_style), Paragraph("", def_style)]
        rows.append(row)
    # NO rowHeights — let the table auto-size per row. The 8pt definitions
    # wrap to 2-4 lines depending on content; a fixed 18pt row clipped them
    # and made adjacent rows visually collide. Auto-size + VALIGN=TOP makes
    # the term sit at the top of its row aligned with the start of the
    # definition wrap.
    gloss_table = Table(rows, colWidths=[term_w, def_w, term_w, def_w])
    gloss_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, RULE_LIGHT),
        ("LINEBEFORE", (2, 0), (2, -1), 0.5, RULE_LIGHT),
    ]))
    story.append(gloss_table)
    return story


# ---------------------------------------------------------------------------
# Comparison PDF — single page.
# ---------------------------------------------------------------------------


def _short_school(name: str) -> str:
    """First whitespace-token of a school name. Cheap label for tight columns."""
    if not name:
        return ""
    return name.split()[0]


def _build_comparison(builds: list[Build]) -> list[object]:
    s = _styles()
    n = len(builds)
    story: list[object] = []

    # Title strip — same-major and cross-major both supported.
    majors = {(b.career.program_name or b.major_text or "") for b in builds}
    same_major = len(majors) == 1 and bool(next(iter(majors)))
    title_subject = next(iter(majors)) if same_major else "Career comparison"
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"{_safe(title_subject)}  —  comparing {n} schools  ·  As of {today}",
        _style("comp_top", fontName=_font("FredokaOne"), fontSize=13, leading=17,
               textColor=INK_PRIMARY),
    ))
    residency_parts: list[str] = []
    for b in builds:
        in_state = bool(b.home_state) and not b.career.is_out_of_state
        residency_parts.append(
            f"{_safe(_short_school(b.school_name))}: "
            f"{'in-state' if in_state else 'out-of-state'}"
        )
    story.append(Paragraph(
        "Residency: " + "  |  ".join(residency_parts),
        s["muted"],
    ))
    story.append(Spacer(1, 2))
    story.append(HRFlowable(width="100%", thickness=1.0, color=INK_PRIMARY,
                            spaceAfter=4))

    # Mini-pentagon strip
    col_w = LIVE_W / n
    school_blocks: list[object] = []
    for b in builds:
        stats_dict = {
            "ern": b.career.stats.ern, "roi": b.career.stats.roi,
            "res": b.career.stats.res, "grw": b.career.stats.grw,
            "aura": b.career.stats.aura,
        }
        pentagon = _draw_pentagon(stats_dict, 0.28 * inch,
                                  show_value_labels=False, show_stat_labels=True,
                                  label_font_size=5.0)
        block = Table(
            [[Paragraph(_safe(b.school_name), s["school_name"])], [pentagon]],
            colWidths=[col_w - 8],
        )
        block.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        school_blocks.append(block)
    school_strip = Table([school_blocks], colWidths=[col_w] * n)
    school_strip.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBEFORE", (1, 0), (n - 1, -1), 0.4, RULE_LIGHT),
    ]))
    story.append(school_strip)
    story.append(Spacer(1, 3))

    # STATS AT A GLANCE
    story.extend(_section_header("STATS AT A GLANCE", compact=True))
    stat_keys = ("ern", "roi", "res", "grw", "aura")
    label_w = 1.80 * inch
    val_w = (LIVE_W - label_w) / n
    hdr_row = [Paragraph("Stat", _style("stat_hdr", fontName=_font("NunitoBold"),
                                        fontSize=8, leading=10, textColor=white))]
    for b in builds:
        hdr_row.append(Paragraph(_safe(_short_school(b.school_name)),
                                 _style("stat_hdr_sch", fontName=_font("NunitoBold"),
                                        fontSize=8, leading=10, textColor=white,
                                        alignment=TA_CENTER)))
    rows: list[list[object]] = [hdr_row]
    cell_styles: list[object] = []
    for row_i, key in enumerate(stat_keys, start=1):
        vals: list[int | None] = [getattr(b.career.stats, key) for b in builds]
        valid = [v for v in vals if v is not None]
        leaders = (
            [i for i, v in enumerate(vals) if v is not None and v == max(valid)]
            if valid else []
        )
        # Tie-breaker per data reviewer: when N tie, no one leads.
        if len(leaders) > 1 and len(leaders) == len([v for v in vals if v is not None]):
            leaders = []
        label_style = _style(
            f"stat_lbl_{key}", fontName=_font("NunitoBold"), fontSize=8, leading=11,
            textColor=STAT_COLORS[key],
        )
        row: list[object] = [Paragraph(f"{STAT_LABELS[key]}  {STAT_MEANINGS[key]}", label_style)]
        for col_i, v in enumerate(vals):
            text = f"{v}/10" if v is not None else "—"
            style = s["comp_lead"] if col_i in leaders else s["comp_value"]
            row.append(Paragraph(text, style))
            if col_i in leaders:
                cell_styles.append((
                    "BACKGROUND",
                    (col_i + 1, row_i), (col_i + 1, row_i),
                    LEADING_CELL_BG,
                ))
        rows.append(row)
    stat_tbl = Table(rows, colWidths=[label_w] + [val_w] * n, repeatRows=1)
    stat_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK_PRIMARY),
        ("FONTNAME", (0, 1), (-1, -1), _font("Nunito")),
        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_ROW_ALT]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE_LIGHT),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, RULE_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        *cell_styles,
    ]))
    story.append(stat_tbl)
    story.append(Spacer(1, 4))

    # COST & ROI — leading direction per data reviewer leading-direction table
    story.extend(_section_header("COST & ROI", compact=True))
    cost_label_w = 1.50 * inch
    cost_val_w = (LIVE_W - cost_label_w) / n
    hdr_style = _style("cost_hdr", fontName=_font("NunitoBold"), fontSize=8,
                       leading=10, textColor=white, alignment=TA_CENTER)
    lbl_style = _style("cost_lbl", fontName=_font("Nunito"), fontSize=8.5,
                       leading=11, textColor=INK_SECONDARY)
    data_style = _style("cost_data", fontName=_font("SpaceMono"), fontSize=9,
                        leading=12, textColor=INK_PRIMARY, alignment=TA_CENTER)
    cost_rows: list[tuple[str, list[float | None], str]] = [
        ("4-year cost",
         [b.career.published_cost_4yr for b in builds], "low"),
        ("Modeled debt",
         [b.career.modeled_total_debt for b in builds], "low"),
        ("Year-1 earnings",
         [b.career.earnings_1yr_median for b in builds], "high"),
        ("Debt-to-earnings (yr-1)",
         [b.career.debt_to_earnings_annual for b in builds], "low"),
    ]
    cost_table_rows: list[list[object]] = [
        [Paragraph("", hdr_style)] +
        [Paragraph(_safe(_short_school(b.school_name)), hdr_style) for b in builds]
    ]
    cost_cell_styles: list[object] = []
    for row_i, (label, values, direction) in enumerate(cost_rows, start=1):
        valid = [v for v in values if v is not None]  # type: ignore[misc]
        if valid:
            target = min(valid) if direction == "low" else max(valid)
            leaders = [i for i, v in enumerate(values) if v is not None and v == target]
            if len(leaders) > 1 and len(leaders) == len([v for v in values if v is not None]):
                leaders = []
        else:
            leaders = []
        formatter = _fmt_pct if label.startswith("Debt-to-earnings") else _fmt_currency
        row = [Paragraph(label, lbl_style)] + [
            Paragraph(formatter(v), data_style) for v in values
        ]
        cost_table_rows.append(row)
        for col_i in leaders:
            cost_cell_styles.append(
                ("BACKGROUND",
                 (col_i + 1, row_i), (col_i + 1, row_i),
                 LEADING_CELL_BG)
            )
    cost_tbl = Table(cost_table_rows,
                     colWidths=[cost_label_w] + [cost_val_w] * n,
                     repeatRows=1)
    cost_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK_PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_ROW_ALT]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE_LIGHT),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, RULE_LIGHT),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        *cost_cell_styles,
    ]))
    story.append(cost_tbl)
    story.append(Spacer(1, 4))

    # CAREER RISK PROFILE
    story.extend(_section_header("CAREER RISK PROFILE", compact=True))
    risk_label_w = 1.50 * inch
    risk_val_w = (LIVE_W - risk_label_w) / n
    hdr_left = _style("risk_hdr", fontName=_font("NunitoBold"), fontSize=8,
                      leading=10, textColor=white)
    hdr_center = _style("risk_hdr_c", fontName=_font("NunitoBold"), fontSize=8,
                       leading=10, textColor=white, alignment=TA_CENTER)
    risk_lbl_style = _style("risk_lbl", fontName=_font("Nunito"), fontSize=8.5,
                            leading=11, textColor=INK_SECONDARY)
    risk_table_rows: list[list[object]] = [
        [Paragraph("Risk Factor", hdr_left)] +
        [Paragraph(_safe(_short_school(b.school_name)), hdr_center) for b in builds]
    ]
    risk_cell_styles: list[object] = []
    for row_i, boss in enumerate(BOSS_ORDER, start=1):
        risk_row: list[object] = [Paragraph(boss_advisory_label(boss), risk_lbl_style)]
        for col_i, b in enumerate(builds):
            fight = next((f for f in b.gauntlet.fights if f.boss == boss), None)
            raw_score = fight.raw_score if fight else None
            level = risk_level_for_boss(boss, raw_score)
            risk_row.append(_risk_chip_paragraph(level))
            risk_cell_styles.append((
                "BACKGROUND",
                (col_i + 1, row_i), (col_i + 1, row_i),
                RISK_BG[level],
            ))
        risk_table_rows.append(risk_row)
    risk_tbl = Table(risk_table_rows,
                     colWidths=[risk_label_w] + [risk_val_w] * n,
                     repeatRows=1)
    risk_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK_PRIMARY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, BG_ROW_ALT]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE_LIGHT),
        ("LINEBELOW", (0, -1), (-1, -1), 0.75, RULE_LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        *risk_cell_styles,
    ]))
    story.append(risk_tbl)
    story.append(Spacer(1, 4))

    # WHERE EACH SCHOOL PULLS AHEAD
    story.extend(_section_header("WHERE EACH SCHOOL PULLS AHEAD", compact=True))
    ahead_lines = where_each_pulls_ahead(builds)
    for line in ahead_lines:
        story.append(Paragraph(
            _safe(line),
            _style("ahead", fontName=_font("Nunito"), fontSize=8, leading=11,
                   textColor=INK_SECONDARY),
        ))
    story.append(Spacer(1, 3))
    return story


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def generate_build_pdf(
    build: Build,
    *,
    student_name: str | None,
    audience_questions: AudienceQuestions,
) -> bytes:
    """Render the 2-page My Build PDF for a single build.

    Returns PDF bytes. Never writes to disk.

    Caller MUST resolve audience_questions before calling (typically via
    pdf_questions.generate_audience_questions). This service is pure-sync
    rendering — no Gemma calls inside, no I/O.
    """
    _register_fonts()
    title = f"FutureProof · {build.school_name} · {build.career.program_name or build.major_text}"
    buf = io.BytesIO()
    doc = _make_doc(buf, title)
    story: list[object] = _build_page1(build, student_name)
    # Switch to "last" template BEFORE the page break — sources callback
    # fires on the next page rendered.
    story.append(NextPageTemplate("last"))
    story.append(PageBreak())
    story.extend(_build_page2(build, audience_questions))
    doc.build(story)
    return buf.getvalue()


def generate_comparison_pdf(builds: list[Build]) -> bytes:
    """Render the 1-page (2-max) Comparison PDF for 2-3 builds.

    Cross-major comparisons are supported — the in-app CompareView shows
    them, the PDF matches that contract. Stats (0-10), cost/ROI (dollars
    and %), and the 5-row risk profile are all directly comparable
    across majors. Title falls back to "Career comparison" when majors
    differ.
    """
    if not (2 <= len(builds) <= 3):
        raise ValueError(
            f"Comparison PDF requires 2-3 builds; got {len(builds)}"
        )
    _register_fonts()
    majors = {(b.career.program_name or b.major_text or "") for b in builds}
    same_major = len(majors) == 1 and bool(next(iter(majors)))
    title_subject = next(iter(majors)) if same_major else "Career comparison"
    title = f"FutureProof · {title_subject} · {len(builds)}-School Comparison"
    buf = io.BytesIO()
    doc = _make_doc(buf, title)
    story: list[object] = [NextPageTemplate("last")]
    story.extend(_build_comparison(builds))
    doc.build(story)
    return buf.getvalue()
