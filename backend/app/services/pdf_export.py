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

import contextvars
import io
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

import arabic_reshaper
from bidi.algorithm import get_display
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

from app.models.api import (
    AudienceQuestions,
    RiskLevel,
)
from app.models.career import AppliedSkill, Build, CareerBranch, SkillRec
from app.services.career_description import (
    CAREER_DESC_FORBIDDEN_TERMS,
    DISCLAIMER_TIER_B,
    DISCLAIMER_TIER_C,
)
from app.services.locale import AppLocale, normalize_locale
from app.services.pdf_copy import (
    BOSS_ORDER,
    boss_advisory_label,
    contains_forbidden_term,
    data_coverage_caveat,
    risk_level_for_boss,
    risk_one_liner,
    verdict_line,
    where_each_pulls_ahead,
)

# Renamed local alias used inside ``_para()`` only — every other call
# site in this module routes through ``_para()`` for Arabic shaping.
# Keeping the canonical ``Paragraph`` name imported lets type
# annotations on helpers (`-> Paragraph`) work without TypeAlias gymnastics.
_RLParagraph = Paragraph

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
    # Arabic-capable faces — only consulted when locale == "ar". Cairo
    # is a single TTF that ships Arabic + full Latin + ASCII digits and
    # punctuation, so we can substitute it for every Latin slot at
    # Arabic render time and Latin proper nouns / dollar amounts /
    # acronyms embedded inside Arabic body text still get real glyphs
    # instead of ReportLab's silent drop. (The prior NotoSansArabic
    # subset shipped Arabic + digits only — Latin letters, "/", "$",
    # "%" all rendered as missing glyphs and vanished from the PDF.)
    "CairoRegular": "Cairo-Regular.ttf",
    "CairoBold": "Cairo-Bold.ttf",
}
_FONT_FALLBACK = {
    "FredokaOne": "Helvetica-Bold",
    "Nunito": "Helvetica",
    "NunitoBold": "Helvetica-Bold",
    "NunitoItalic": "Helvetica-Oblique",
    "SpaceMono": "Courier",
    "CairoRegular": "Helvetica",
    "CairoBold": "Helvetica-Bold",
}

# When locale == "ar" every Latin font slot resolves to a Cairo face.
# ``NunitoItalic`` has no italic counterpart in the Cairo static set;
# we substitute regular and rely on color (the other half of the
# FYI-caveat visual cue) to keep the register distinct.
# ``SpaceMono`` is monospace; we accept losing the mono treatment for
# Arabic — dollar amounts still render in Western Arabic numerals
# (per the locale.py glossary rule) just in proportional spacing.
_FONT_LOC_OVERRIDE: dict[str, dict[str, str]] = {
    "ar": {
        "FredokaOne": "CairoBold",
        "Nunito": "CairoRegular",
        "NunitoBold": "CairoBold",
        "NunitoItalic": "CairoRegular",
        "SpaceMono": "CairoRegular",
    },
}

_FONTS_REGISTERED = False
_FONT_NAMES: dict[str, str] = {}
_FONTS_LOCK = __import__("threading").Lock()


# Module-level locale carrier. The two public entry points
# (``generate_build_pdf``, ``generate_comparison_pdf``) bind this for
# the duration of a single render so every helper — _font(), _style(),
# _para(), _make_callbacks's canvas drawString calls — picks up the
# right locale without us threading a ``locale`` arg through every
# call site. ContextVar (not threading.local) so concurrent renders
# under FastAPI's thread-pool stay isolated; ReportLab's CPU-bound
# render runs via ``asyncio.to_thread`` per the routers, and each
# thread re-enters this module with its own context.
_current_locale: contextvars.ContextVar[str] = contextvars.ContextVar(
    "pdf_export_locale", default="en",
)


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


def _font(name: str, locale: str | None = None) -> str:
    """Return the resolved font name (TTF or platform fallback).

    For Arabic the requested Latin slot resolves to its Noto Sans
    Arabic counterpart so a single font covers Latin proper nouns,
    Western Arabic numerals, punctuation, and Arabic glyphs in one TTF.
    Avoids ReportLab's missing-glyph fallback path for mixed-script text.

    ``locale`` defaults to whatever ``_current_locale`` carries (the
    public entry points bind this for the duration of a render). Pass
    explicitly only when the caller needs to override the ambient
    locale (e.g., a fallback canvas drawString outside the render).
    """
    loc = locale if locale is not None else _current_locale.get()
    fonts = _register_fonts()
    override = _FONT_LOC_OVERRIDE.get(loc, {}).get(name)
    if override is not None:
        return fonts.get(override, fonts.get(name, name))
    return fonts.get(name, name)


# ---------------------------------------------------------------------------
# Arabic shaping helpers (no-op for non-Arabic locales).
# ---------------------------------------------------------------------------

# Codepoint ranges that require ``arabic-reshaper`` joining + bidi. Bare
# Arabic Unicode passed straight to ReportLab renders as disconnected,
# left-to-right glyphs because ReportLab does not perform shaping or
# RTL reordering itself.
_ARABIC_RANGES: tuple[tuple[int, int], ...] = (
    (0x0600, 0x06FF),  # Arabic
    (0x0750, 0x077F),  # Arabic Supplement
    (0x08A0, 0x08FF),  # Arabic Extended-A
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
)

# arabic_reshaper emits Presentation Forms-B isolated codepoints, but Cairo
# (a modern OpenType font) only maps initial/medial/final forms — not isolated.
# Map each isolated PF-B codepoint back to its base Arabic equivalent, which
# Cairo does have.  Diacritical isolated forms (FE70-FE7F) are also missing;
# map those to their base combining marks.
_ISOLATED_TO_BASE: dict[int, int] = {
    0xFE70: 0x064B,  # fathatan
    0xFE72: 0x064C,  # dammatan
    0xFE74: 0x064D,  # kasratan
    0xFE76: 0x064E,  # fatha
    0xFE78: 0x064F,  # damma
    0xFE7A: 0x0650,  # kasra
    0xFE7C: 0x0651,  # shadda
    0xFE7E: 0x0652,  # sukun
    0xFE80: 0x0621,  # hamza
    0xFE81: 0x0622,  # alef with madda above
    0xFE83: 0x0623,  # alef with hamza above
    0xFE85: 0x0624,  # waw with hamza above
    0xFE87: 0x0625,  # alef with hamza below
    0xFE89: 0x0626,  # yeh with hamza above
    0xFE8D: 0x0627,  # alef
    0xFE8F: 0x0628,  # beh
    0xFE93: 0x0629,  # teh marbuta
    0xFE95: 0x062A,  # teh
    0xFE99: 0x062B,  # theh
    0xFE9D: 0x062C,  # jeem
    0xFEA1: 0x062D,  # hah
    0xFEA5: 0x062E,  # khah
    0xFEA9: 0x062F,  # dal
    0xFEAB: 0x0630,  # thal
    0xFEAD: 0x0631,  # reh
    0xFEAF: 0x0632,  # zain
    0xFEB1: 0x0633,  # seen
    0xFEB5: 0x0634,  # sheen
    0xFEB9: 0x0635,  # sad
    0xFEBD: 0x0636,  # dad
    0xFEC1: 0x0637,  # tah
    0xFEC5: 0x0638,  # zah
    0xFEC9: 0x0639,  # ain
    0xFECD: 0x063A,  # ghain
    0xFED1: 0x0641,  # feh
    0xFED5: 0x0642,  # qaf
    0xFED9: 0x0643,  # kaf
    0xFEDD: 0x0644,  # lam
    0xFEE1: 0x0645,  # meem
    0xFEE5: 0x0646,  # noon
    0xFEE9: 0x0647,  # heh
    0xFEED: 0x0648,  # waw
    0xFEEF: 0x0649,  # alef maksura
    0xFEF1: 0x064A,  # yeh
}
_ISOLATED_TRANS = str.maketrans(_ISOLATED_TO_BASE)


def _has_arabic(text: str) -> bool:
    return any(
        any(start <= ord(ch) <= end for start, end in _ARABIC_RANGES)
        for ch in text
    )


def _shape(text: str, locale: str | None = None) -> str:
    """Reshape + bidi-reorder Arabic text for ReportLab rendering.

    Pure no-op when locale is not Arabic or when the input contains no
    Arabic codepoints, so safe to call from every render site. The
    bidi pass needs to see the COMPLETE final string to position
    embedded LTR runs (school names, dollar amounts, source acronyms)
    correctly inside the surrounding RTL flow — call this at the
    Paragraph creation boundary, not at translation lookup.
    """
    loc = locale if locale is not None else _current_locale.get()
    if loc != "ar" or not text or not _has_arabic(text):
        return text
    shaped: str = get_display(arabic_reshaper.reshape(text))
    return shaped.translate(_ISOLATED_TRANS)


def _para(text: str, style: ParagraphStyle, locale: str | None = None) -> Paragraph:
    """Build a ReportLab Paragraph with Arabic shaping applied."""
    return _RLParagraph(_shape(text, locale), style)


def _rtl_table(
    rows: list[list[Any]],
    col_widths: list[float],
    style_commands: list[Any],
    locale: str | None = None,
) -> tuple[list[list[Any]], list[float], list[Any]]:
    """Flip rows / column widths / cell-coord style commands for RTL.

    Pass logical (label-first) ``rows``, ``col_widths``, and ``style_commands``
    in. For ``locale == "ar"`` this returns RTL-mirrored versions so the label
    column lands on the right edge. For other locales it's a pure no-op
    pass-through so call sites can wrap unconditionally.

    What gets mirrored:
      - Each row's cell list is reversed end-to-end.
      - ``col_widths`` is reversed.
      - Style commands of the form ``(op, (c1, r1), (c2, r2), *args)`` get
        their column coordinates mirrored (``c -> n_cols - 1 - c``, with
        negative indices like ``-1`` resolved against ``n_cols`` first), and
        ``LINEBEFORE`` / ``LINEAFTER`` ops swap to preserve the visual line
        position relative to the (now-flipped) cell content.
      - Whole-grid style commands using ``(0, 0)`` / ``(-1, -1)`` ranges stay
        valid because the mirror is symmetric over the full column range.
    """
    loc = locale if locale is not None else _current_locale.get()
    if loc != "ar":
        return rows, col_widths, style_commands

    n = len(col_widths)
    flipped_rows = [list(reversed(r)) for r in rows]
    flipped_widths = list(reversed(col_widths))

    def _mirror(c: int) -> int:
        idx = c if c >= 0 else n + c
        return n - 1 - idx

    flipped_styles: list[Any] = []
    for cmd in style_commands:
        if (
            isinstance(cmd, tuple)
            and len(cmd) >= 3
            and isinstance(cmd[1], tuple) and len(cmd[1]) == 2
            and isinstance(cmd[2], tuple) and len(cmd[2]) == 2
        ):
            op = cmd[0]
            c1, r1 = cmd[1]
            c2, r2 = cmd[2]
            rest = cmd[3:]
            mc1, mc2 = _mirror(c1), _mirror(c2)
            new_c1, new_c2 = (mc1, mc2) if mc1 <= mc2 else (mc2, mc1)
            # LINEBEFORE meant "line on the left edge of cell at col C".
            # After mirroring, that visual edge becomes the right edge of
            # what's now at the mirrored column — so emit LINEAFTER on the
            # mirrored coord. Symmetric for LINEAFTER → LINEBEFORE.
            if op == "LINEBEFORE":
                op = "LINEAFTER"
            elif op == "LINEAFTER":
                op = "LINEBEFORE"
            flipped_styles.append((op, (new_c1, r1), (new_c2, r2), *rest))
        else:
            flipped_styles.append(cmd)
    return flipped_rows, flipped_widths, flipped_styles


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

# Stat-meaning labels are short chrome that appears next to the 3-letter
# code in the page-1 stat table and the comparison stat-glance row.
# Keyed by locale so the en/es/ar render strings line up with the rest
# of the PDF copy. Read via ``_stat_meaning(key)`` so callers don't
# have to know about the locale lookup.
_STAT_MEANINGS_BY_LOCALE: dict[str, dict[str, str]] = {
    "en": {
        "ern": "Earnings",
        "roi": "Return on Investment",
        "res": "AI Resilience",
        "grw": "Growth",
        "aura": "Brand Gravity",
    },
    "es": {
        "ern": "Ingresos",
        "roi": "Retorno sobre la inversión",
        "res": "Resiliencia ante la IA",
        "grw": "Crecimiento",
        "aura": "Gravedad de marca",
    },
    "ar": {
        "ern": "الدخل",
        "roi": "العائد على الاستثمار",
        "res": "المقاومة للذكاء الاصطناعي",
        "grw": "النمو",
        "aura": "جاذبية العلامة",
    },
}


def _stat_meaning(key: str) -> str:
    """Locale-aware stat-meaning label. Reads from ``_current_locale``."""
    loc = _current_locale.get()
    return _STAT_MEANINGS_BY_LOCALE.get(loc, _STAT_MEANINGS_BY_LOCALE["en"])[key]


# Backwards-compat alias for any external test that imports STAT_MEANINGS.
# Resolves to the English copy; locale-aware callers should use
# ``_stat_meaning(key)`` instead.
STAT_MEANINGS = _STAT_MEANINGS_BY_LOCALE["en"]


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
# Localization (per locale.py glossary rules: school names, dollar amounts,
# percentages, and source acronyms (BLS, O*NET, IPEDS, BEA, College
# Scorecard) are preserved verbatim across all locales).
# ---------------------------------------------------------------------------


_PAGE_COPY: dict[AppLocale, dict[str, str]] = {
    "en": {
        # --- Header / footer chrome ---
        "header.audience": "FOR STUDENT + COUNSELOR USE ONLY",
        "footer.page": "Page {n}",
        "sources.line": (
            "Sources: BLS OOH · College Scorecard · O*NET · Karpathy AI Exposure · "
            "BEA RPP. Powered by Gemma 4."
        ),

        # --- Profile strip ---
        "profile.default_name": "Student plan",
        "profile.in_state": "in-state",
        "profile.out_of_state": "out-of-state",
        "profile.residency_in_state": "Residency: in-state, {state}",
        "profile.residency_out_of_state": "Residency: out-of-state",
        "profile.program_fallback": "Program",

        # --- Page 1: cost & risk strip ---
        "section.cost_roi": "COST & ROI",
        "cost.4yr": "4-year cost",
        "cost.modeled_debt": "Modeled debt",
        "cost.year1_median": "Year-1 median earnings",
        "cost.year1_median_fb": "Year-1 median earnings*",
        "cost.dte_yr1": "Debt-to-earnings (yr-1)",
        "cost.peer_band_label": "Year-1 peer band (this field):",
        "cost.peer_band_unavailable": " · Program-median Year-1 earnings unavailable for this school.",
        "cost.standout": "Standout earnings",
        "cost.caution": "Earnings caution",
        "cost.standout_clause": " · <b><font color=\"#2D7A4F\">{label}</font></b> — this program's median ({median}) beats the peer 75th percentile.",
        "cost.caution_clause": " · <b><font color=\"#8B1A1A\">{label}</font></b> — this program's median ({median}) sits below the peer 25th percentile.",
        "cost.inside_clause": " · This program's median ({median}) sits within the peer band.",
        "cost.year1_footnote": (
            "* Program-median Year-1 earnings unavailable; figure shown is "
            "the career-level mid-career wage (national OEWS median) as a "
            "reference. Not a graduate's first-year salary."
        ),

        # --- Page 1: risk profile ---
        "section.risk_profile": "CAREER RISK PROFILE",
        "risk.col.factor": "Risk Factor",
        "risk.col.level": "Level",
        "risk.col.context": "Context",
        "risk.chip.insufficient": "Insufficient data",
        "risk.context.insufficient": "Data unavailable for this program.",

        # --- Page 1: about this career ---
        "section.about": "ABOUT THIS CAREER",
        "about.day_to_day": "Day-to-day",

        # --- Page 2: skills + questions + glossary ---
        "section.suggested_skills": "SUGGESTED SKILLS",
        "skills.intro": (
            "Bring this list to your admissions counselor — these are the skills "
            "that may lift your outcomes."
        ),
        "skills.bucket.ai_resilience": "AI-RESILIENCE SKILLS",
        "skills.bucket.career_launch": "CAREER-LAUNCH SKILLS",
        "skills.bucket.earnings_ceiling": "EARNINGS-CEILING SKILLS",
        "section.questions": "QUESTIONS & FOLLOW-UPS",
        "questions.ask_college": "ASK THE COLLEGE",
        "questions.ask_parents": "ASK YOUR GUARDIAN",
        "questions.ask_yourself": "ASK YOURSELF",

        # --- Glossary (8 entries) ---
        "section.glossary": "GLOSSARY",
        "gloss.cip.term": "CIP",
        "gloss.cip.def": "Federal program code (Classification of Instructional Programs) — the standard for naming college majors.",
        "gloss.soc.term": "SOC",
        "gloss.soc.def": "Federal occupation code (Standard Occupational Classification) — how the BLS names jobs.",
        "gloss.ern.term": "ERN",
        "gloss.ern.def": "Earnings — typical pay for graduates of this program working in this occupation.",
        "gloss.roi.term": "ROI",
        "gloss.roi.def": "Return on Investment — how the cost of this program compares to what graduates earn.",
        "gloss.res.term": "RES",
        "gloss.res.def": "AI Resilience — how much of this occupation's work is hard for AI to do, blended from task-level data.",
        "gloss.grw.term": "GRW",
        "gloss.grw.def": "Growth — the BLS 10-year employment-change projection for this occupation.",
        "gloss.aura.term": "AURA",
        "gloss.aura.def": "Brand Gravity — institutional pull (selectivity, completion, financial standing) shared by every program at the school.",
        "gloss.career_risk.term": "Career risk",
        "gloss.career_risk.def": "Five factors that affect long-term outcomes: AI displacement, debt burden, job market, burnout, and earnings ceiling.",

        # --- Comparison page ---
        "compare.title_subject_fallback": "Career comparison",
        "compare.title_template": "{subject}  —  comparing {n} schools  ·  As of {date}",
        "compare.title_label": "FutureProof · {subject} · {n}-School Comparison",
        "compare.residency_prefix": "Residency: ",
        "compare.residency_join": "  |  ",
        "compare.residency_in_state": "in-state",
        "compare.residency_out_of_state": "out-of-state",
        "section.stats_glance": "STATS AT A GLANCE",
        "compare.stat_col_header": "Stat",
        "compare.cost.year1_program_median": "Year-1 program median",
        "compare.cost.year1_peer_band": "Year-1 peer band",
        "compare.cost.peer_band_unavailable": "—",
        "compare.year1_footnote": (
            "* Program-median Year-1 earnings unavailable for this school; "
            "figure shown is the career-level mid-career wage (national OEWS "
            "median) as a reference. Excluded from the Year-1 leader highlight."
        ),
        "section.where_each_ahead": "WHERE EACH SCHOOL PULLS AHEAD",

        # --- School profile ---
        "section.school_profile": "SCHOOL PROFILE",
        "profile.row.type": "Type",
        "profile.row.state": "State",
        "profile.row.residency": "Residency",
        "profile.row.major": "Major",
        "profile.row.career": "Career",

        # --- Cost breakdown ---
        "section.cost_breakdown": "COST BREAKDOWN",
        "breakdown.tuition_residency": "Tuition (annual, residency-aware)",
        "breakdown.tuition_in": "Tuition (in-state)",
        "breakdown.tuition_out": "Tuition (out-of-state)",
        "breakdown.room_board": "Room & board (on-campus)",
        "breakdown.net_price": "Net price (annual avg, after aid)",
        "breakdown.coa_residency": "Cost of attendance (annual, residency-aware)",
        "breakdown.coa_in_state": "Cost of attendance (annual, in-state)",
        "breakdown.cost_4yr": "4-year cost (residency-aware)",
        "breakdown.modeled_debt_total": "Modeled total debt",

        # --- Career branches ---
        "section.career_branches": "CAREER BRANCHES",
        "branches.intro": (
            "Where each path can lead next — top related careers and how their "
            "stats compare against the starting role."
        ),
        "branches.empty": "No branch data.",
    },
    "es": {
        "header.audience": "PARA USO DEL ESTUDIANTE Y EL CONSEJERO",
        "footer.page": "Página {n}",
        "sources.line": (
            "Fuentes: BLS OOH · College Scorecard · O*NET · Karpathy AI Exposure · "
            "BEA RPP. Impulsado por Gemma 4."
        ),

        "profile.default_name": "Plan del estudiante",
        "profile.in_state": "residente del estado",
        "profile.out_of_state": "fuera del estado",
        "profile.residency_in_state": "Residencia: residente del estado, {state}",
        "profile.residency_out_of_state": "Residencia: fuera del estado",
        "profile.program_fallback": "Programa",

        "section.cost_roi": "COSTO Y ROI",
        "cost.4yr": "Costo de 4 años",
        "cost.modeled_debt": "Deuda modelada",
        "cost.year1_median": "Ingresos medianos del primer año",
        "cost.year1_median_fb": "Ingresos medianos del primer año*",
        "cost.dte_yr1": "Deuda-a-ingresos (año 1)",
        "cost.peer_band_label": "Rango de pares para el primer año (este campo):",
        "cost.peer_band_unavailable": " · La mediana del programa para los ingresos del primer año no está disponible para esta escuela.",
        "cost.standout": "Ingresos destacados",
        "cost.caution": "Precaución de ingresos",
        "cost.standout_clause": " · <b><font color=\"#2D7A4F\">{label}</font></b> — la mediana de este programa ({median}) supera el percentil 75 de los pares.",
        "cost.caution_clause": " · <b><font color=\"#8B1A1A\">{label}</font></b> — la mediana de este programa ({median}) está por debajo del percentil 25 de los pares.",
        "cost.inside_clause": " · La mediana de este programa ({median}) se sitúa dentro del rango de pares.",
        "cost.year1_footnote": (
            "* La mediana del programa para los ingresos del primer año no está "
            "disponible; la cifra mostrada es el salario de mitad de carrera a "
            "nivel ocupacional (mediana nacional OEWS) como referencia. No es "
            "el salario del primer año de un graduado."
        ),

        "section.risk_profile": "PERFIL DE RIESGO PROFESIONAL",
        "risk.col.factor": "Factor de riesgo",
        "risk.col.level": "Nivel",
        "risk.col.context": "Contexto",
        "risk.chip.insufficient": "Datos insuficientes",
        "risk.context.insufficient": "Datos no disponibles para este programa.",

        "section.about": "SOBRE ESTA CARRERA",
        "about.day_to_day": "Día a día",

        "section.suggested_skills": "HABILIDADES SUGERIDAS",
        "skills.intro": (
            "Lleva esta lista a tu consejero de admisiones — estas son las "
            "habilidades que pueden mejorar tus resultados."
        ),
        "skills.bucket.ai_resilience": "HABILIDADES DE RESILIENCIA ANTE LA IA",
        "skills.bucket.career_launch": "HABILIDADES DE LANZAMIENTO PROFESIONAL",
        "skills.bucket.earnings_ceiling": "HABILIDADES DE TOPE DE INGRESOS",
        "section.questions": "PREGUNTAS Y SEGUIMIENTO",
        "questions.ask_college": "PREGÚNTALE A LA UNIVERSIDAD",
        "questions.ask_parents": "PREGÚNTALE A TU TUTOR",
        "questions.ask_yourself": "PREGÚNTATE A TI MISMO",

        "section.glossary": "GLOSARIO",
        "gloss.cip.term": "CIP",
        "gloss.cip.def": "Código federal de programa (Classification of Instructional Programs) — el estándar para nombrar las carreras universitarias.",
        "gloss.soc.term": "SOC",
        "gloss.soc.def": "Código federal de ocupación (Standard Occupational Classification) — cómo el BLS nombra los empleos.",
        "gloss.ern.term": "ERN",
        "gloss.ern.def": "Ingresos — pago típico para los graduados de este programa que trabajan en esta ocupación.",
        "gloss.roi.term": "ROI",
        "gloss.roi.def": "Retorno sobre la inversión — cómo se compara el costo de este programa con lo que ganan los graduados.",
        "gloss.res.term": "RES",
        "gloss.res.def": "Resiliencia ante la IA — cuánto del trabajo de esta ocupación es difícil para la IA, combinado a partir de datos a nivel de tareas.",
        "gloss.grw.term": "GRW",
        "gloss.grw.def": "Crecimiento — la proyección del BLS de cambio de empleo a 10 años para esta ocupación.",
        "gloss.aura.term": "AURA",
        "gloss.aura.def": "Gravedad de marca — atracción institucional (selectividad, finalización, situación financiera) compartida por cada programa de la escuela.",
        "gloss.career_risk.term": "Riesgo profesional",
        "gloss.career_risk.def": "Cinco factores que afectan los resultados a largo plazo: desplazamiento por IA, carga de deuda, mercado laboral, agotamiento y tope de ingresos.",

        "compare.title_subject_fallback": "Comparación de carreras",
        "compare.title_template": "{subject}  —  comparando {n} escuelas  ·  Al {date}",
        "compare.title_label": "FutureProof · {subject} · Comparación de {n} escuelas",
        "compare.residency_prefix": "Residencia: ",
        "compare.residency_join": "  |  ",
        "compare.residency_in_state": "residente del estado",
        "compare.residency_out_of_state": "fuera del estado",
        "section.stats_glance": "ESTADÍSTICAS DE UN VISTAZO",
        "compare.stat_col_header": "Estadística",
        "compare.cost.year1_program_median": "Mediana del programa, año 1",
        "compare.cost.year1_peer_band": "Rango de pares, año 1",
        "compare.cost.peer_band_unavailable": "—",
        "compare.year1_footnote": (
            "* La mediana del programa para los ingresos del primer año no está "
            "disponible para esta escuela; la cifra mostrada es el salario de "
            "mitad de carrera a nivel ocupacional (mediana nacional OEWS) como "
            "referencia. Excluida del resaltado del líder del primer año."
        ),
        "section.where_each_ahead": "DÓNDE DESTACA CADA ESCUELA",

        "section.school_profile": "PERFIL DE LA ESCUELA",
        "profile.row.type": "Tipo",
        "profile.row.state": "Estado",
        "profile.row.residency": "Residencia",
        "profile.row.major": "Carrera",
        "profile.row.career": "Profesión",

        "section.cost_breakdown": "DESGLOSE DE COSTOS",
        "breakdown.tuition_residency": "Matrícula (anual, según residencia)",
        "breakdown.tuition_in": "Matrícula (residente del estado)",
        "breakdown.tuition_out": "Matrícula (fuera del estado)",
        "breakdown.room_board": "Alojamiento y comida (en el campus)",
        "breakdown.net_price": "Precio neto (promedio anual, después de ayuda)",
        "breakdown.coa_residency": "Costo de asistencia (anual, según residencia)",
        "breakdown.coa_in_state": "Costo de asistencia (anual, residente del estado)",
        "breakdown.cost_4yr": "Costo de 4 años (según residencia)",
        "breakdown.modeled_debt_total": "Deuda total modelada",

        "section.career_branches": "RAMAS PROFESIONALES",
        "branches.intro": (
            "Hacia dónde puede llevar cada camino — las principales carreras "
            "relacionadas y cómo se comparan sus estadísticas con el rol inicial."
        ),
        "branches.empty": "Sin datos de ramas.",
    },
    "ar": {
        "header.audience": "للاستخدام من قبل الطالب والمرشد فقط",
        "footer.page": "صفحة {n}",
        "sources.line": (
            "المصادر: BLS OOH · College Scorecard · O*NET · Karpathy AI Exposure · "
            "BEA RPP. مدعوم بـ Gemma 4."
        ),

        "profile.default_name": "خطة الطالب",
        "profile.in_state": "مقيم في الولاية",
        "profile.out_of_state": "خارج الولاية",
        "profile.residency_in_state": "الإقامة: مقيم في الولاية، {state}",
        "profile.residency_out_of_state": "الإقامة: خارج الولاية",
        "profile.program_fallback": "البرنامج",

        "section.cost_roi": "التكلفة وعائد الاستثمار",
        "cost.4yr": "تكلفة 4 سنوات",
        "cost.modeled_debt": "الدين المتوقع",
        "cost.year1_median": "الدخل الوسيط للسنة الأولى",
        "cost.year1_median_fb": "الدخل الوسيط للسنة الأولى*",
        "cost.dte_yr1": "الدين إلى الدخل (سنة 1)",
        "cost.peer_band_label": "نطاق الأقران للسنة الأولى (هذا المجال):",
        "cost.peer_band_unavailable": " · وسيط برنامج هذه المدرسة لدخل السنة الأولى غير متاح.",
        "cost.standout": "دخل بارز",
        "cost.caution": "تنبيه بشأن الدخل",
        "cost.standout_clause": " · <b><font color=\"#2D7A4F\">{label}</font></b> — وسيط هذا البرنامج ({median}) يفوق النسبة المئوية 75 للأقران.",
        "cost.caution_clause": " · <b><font color=\"#8B1A1A\">{label}</font></b> — وسيط هذا البرنامج ({median}) أدنى من النسبة المئوية 25 للأقران.",
        "cost.inside_clause": " · وسيط هذا البرنامج ({median}) يقع ضمن نطاق الأقران.",
        "cost.year1_footnote": (
            "* وسيط برنامج هذه المدرسة لدخل السنة الأولى غير متاح؛ الرقم المعروض "
            "هو الأجر في منتصف المسار المهني على مستوى المهنة (وسيط OEWS الوطني) "
            "كمرجع. ليس الراتب الأول للخريج."
        ),

        "section.risk_profile": "ملف المخاطر المهنية",
        "risk.col.factor": "عامل الخطر",
        "risk.col.level": "المستوى",
        "risk.col.context": "السياق",
        "risk.chip.insufficient": "بيانات غير كافية",
        "risk.context.insufficient": "البيانات غير متاحة لهذا البرنامج.",

        "section.about": "حول هذه المهنة",
        "about.day_to_day": "اليوم إلى اليوم",

        "section.suggested_skills": "المهارات المقترحة",
        "skills.intro": (
            "خذ هذه القائمة إلى مرشد القبول — هذه هي المهارات التي قد ترفع نتائجك."
        ),
        "skills.bucket.ai_resilience": "مهارات المقاومة للذكاء الاصطناعي",
        "skills.bucket.career_launch": "مهارات إطلاق المسار المهني",
        "skills.bucket.earnings_ceiling": "مهارات سقف الأرباح",
        "section.questions": "الأسئلة والمتابعة",
        "questions.ask_college": "اسأل الجامعة",
        "questions.ask_parents": "اسأل وليّ أمرك",
        "questions.ask_yourself": "اسأل نفسك",

        "section.glossary": "المصطلحات",
        "gloss.cip.term": "CIP",
        "gloss.cip.def": "رمز البرنامج الفيدرالي (Classification of Instructional Programs) — المعيار لتسمية التخصصات الجامعية.",
        "gloss.soc.term": "SOC",
        "gloss.soc.def": "رمز المهنة الفيدرالي (Standard Occupational Classification) — كيف تسمي BLS الوظائف.",
        "gloss.ern.term": "ERN",
        "gloss.ern.def": "الدخل — الأجر المعتاد لخريجي هذا البرنامج العاملين في هذه المهنة.",
        "gloss.roi.term": "ROI",
        "gloss.roi.def": "العائد على الاستثمار — كيف تقارن تكلفة هذا البرنامج بما يكسبه الخريجون.",
        "gloss.res.term": "RES",
        "gloss.res.def": "المقاومة للذكاء الاصطناعي — مقدار العمل في هذه المهنة الذي يصعب على الذكاء الاصطناعي القيام به، مزيج من بيانات على مستوى المهام.",
        "gloss.grw.term": "GRW",
        "gloss.grw.def": "النمو — توقع BLS لتغير التوظيف خلال 10 سنوات لهذه المهنة.",
        "gloss.aura.term": "AURA",
        "gloss.aura.def": "جاذبية العلامة — جاذبية مؤسسية (الانتقائية، الإكمال، الوضع المالي) يشترك فيها كل برنامج في المدرسة.",
        "gloss.career_risk.term": "المخاطر المهنية",
        "gloss.career_risk.def": "خمسة عوامل تؤثر على النتائج طويلة المدى: الإزاحة بسبب الذكاء الاصطناعي، عبء الديون، سوق العمل، الإرهاق، وسقف الأرباح.",

        "compare.title_subject_fallback": "مقارنة المهن",
        "compare.title_template": "{subject}  —  مقارنة بين {n} مدارس  ·  بتاريخ {date}",
        "compare.title_label": "FutureProof · {subject} · مقارنة {n} مدارس",
        "compare.residency_prefix": "الإقامة: ",
        "compare.residency_join": "  |  ",
        "compare.residency_in_state": "مقيم في الولاية",
        "compare.residency_out_of_state": "خارج الولاية",
        "section.stats_glance": "الإحصائيات في لمحة",
        "compare.stat_col_header": "الإحصائية",
        "compare.cost.year1_program_median": "وسيط البرنامج، السنة الأولى",
        "compare.cost.year1_peer_band": "نطاق الأقران، السنة الأولى",
        "compare.cost.peer_band_unavailable": "—",
        "compare.year1_footnote": (
            "* وسيط برنامج هذه المدرسة لدخل السنة الأولى غير متاح؛ الرقم المعروض "
            "هو الأجر في منتصف المسار المهني على مستوى المهنة (وسيط OEWS الوطني) "
            "كمرجع. مستثناة من إبراز المتقدم في السنة الأولى."
        ),
        "section.where_each_ahead": "أين تتقدّم كل مدرسة",

        "section.school_profile": "ملف المدرسة",
        "profile.row.type": "النوع",
        "profile.row.state": "الولاية",
        "profile.row.residency": "الإقامة",
        "profile.row.major": "التخصص",
        "profile.row.career": "المهنة",

        "section.cost_breakdown": "تفصيل التكلفة",
        "breakdown.tuition_residency": "الرسوم الدراسية (سنوياً، بحسب الإقامة)",
        "breakdown.tuition_in": "الرسوم الدراسية (مقيم في الولاية)",
        "breakdown.tuition_out": "الرسوم الدراسية (خارج الولاية)",
        "breakdown.room_board": "السكن والطعام (داخل الحرم)",
        "breakdown.net_price": "السعر الصافي (متوسط سنوي، بعد المساعدة)",
        "breakdown.coa_residency": "تكلفة الدراسة (سنوياً، بحسب الإقامة)",
        "breakdown.coa_in_state": "تكلفة الدراسة (سنوياً، مقيم في الولاية)",
        "breakdown.cost_4yr": "تكلفة 4 سنوات (بحسب الإقامة)",
        "breakdown.modeled_debt_total": "إجمالي الدين المتوقع",

        "section.career_branches": "الفروع المهنية",
        "branches.intro": (
            "إلى أين يمكن أن يقود كل مسار — أبرز المهن ذات الصلة وكيف تقارن "
            "إحصائياتها مع الدور الابتدائي."
        ),
        "branches.empty": "لا توجد بيانات للفروع.",
    },
}


def _t(locale: AppLocale, key: str, **fmt: object) -> str:
    """Locale lookup with English fallback. Optional .format() args."""
    loc = normalize_locale(locale)
    text = _PAGE_COPY[loc].get(key) or _PAGE_COPY["en"].get(key, key)
    if fmt:
        return text.format(**fmt)
    return text


# Month names for date formatting. ``strftime("%B")`` would honor the OS
# locale, which we cannot rely on, so we hand-roll it. Western Arabic
# numerals stay across all locales (matches the rest of the app and the
# locale.py glossary directive).
_MONTH_NAMES: dict[AppLocale, list[str]] = {
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
           "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}


def _format_date(dt: datetime, locale: AppLocale) -> str:
    loc = normalize_locale(locale)
    month = _MONTH_NAMES[loc][dt.month - 1]
    if loc == "es":
        return f"{dt.day} de {month} de {dt.year}"
    if loc == "ar":
        return f"{dt.day} {month} {dt.year}"
    return f"{month} {dt.day}, {dt.year}"


# ---------------------------------------------------------------------------
# Style helpers.
# ---------------------------------------------------------------------------


def _style(name: str, **kw: object) -> ParagraphStyle:
    """ParagraphStyle factory with project defaults.

    For Arabic the default body alignment flips to ``TA_RIGHT`` so flowing
    paragraphs read with the start-of-line on the right (Arabic convention).
    Callers can still override ``alignment`` explicitly — table cells and
    chrome that pin to ``TA_CENTER`` keep their original treatment.

    Locale is read from ``_current_locale`` (set by the entry points),
    so this factory needs no locale arg at the call sites.
    """
    loc = _current_locale.get()
    default_alignment = TA_RIGHT if loc == "ar" else TA_LEFT
    base: dict[str, object] = dict(
        fontName=_font("Nunito"), fontSize=9, leading=13,
        textColor=INK_SECONDARY, leftIndent=0, rightIndent=0,
        spaceAfter=0, spaceBefore=0, alignment=default_alignment,
    )
    base.update(kw)
    return ParagraphStyle(name, **base)


def _styles() -> dict[str, ParagraphStyle]:
    """Return the canonical style dict. Cheap to call repeatedly.

    Locale is read from ``_current_locale``; fonts and default
    alignments adapt automatically.
    """
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
                         textColor=INK_MUTED),
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
    # ERN at the top (12 o'clock), then clockwise — matches the web
    # /my-build pentagon. ReportLab's coordinate system is y-up, so
    # +90° puts ERN above center; subtracting 72° per step rotates
    # clockwise: ROI upper-right, RES lower-right, GRW lower-left,
    # AURA upper-left.
    angles = [math.radians(90 - 72 * i) for i in range(5)]

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


def _make_callbacks(title: str, locale: AppLocale = "en") -> tuple[object, object]:
    loc = normalize_locale(locale)
    # Pre-shape the static chrome strings so the canvas drawString calls
    # (which can't go through the Paragraph/_para wrapper) render correctly
    # for Arabic. ``_shape`` is a no-op for non-Arabic locales.
    audience_label = _shape(_t(loc, "header.audience"), loc)
    page_template = _t(loc, "footer.page")
    sources_text = _t(loc, "sources.line")
    title_for_footer = _shape(title, loc)

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
            PW - MARGIN_R, PH - 0.32 * inch, audience_label,
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
        canvas.drawString(MARGIN_L, FOOTER_Y - 11, title_for_footer)  # type: ignore[attr-defined]
        canvas.drawRightString(  # type: ignore[attr-defined]
            PW - MARGIN_R, FOOTER_Y - 11,
            _shape(page_template.format(n=doc.page), loc),  # type: ignore[attr-defined]
        )
        canvas.restoreState()  # type: ignore[attr-defined]

    def on_last_page(canvas: object, doc: object) -> None:  # noqa: ANN401
        on_page(canvas, doc)
        canvas.saveState()  # type: ignore[attr-defined]
        canvas.setFont(_font("Nunito"), 6)  # type: ignore[attr-defined]
        canvas.setFillColor(INK_MUTED)  # type: ignore[attr-defined]
        # Two-line wrap if needed. Shaping happens AFTER wrapping so each
        # line gets its own bidi pass — bidi must see a complete logical
        # line to position embedded LTR runs (BLS, O*NET) correctly.
        #
        # Split on a real source-list separator (" · " between source names
        # or ". " before the "Powered by" suffix), never inside a proper
        # noun. The old logic searched for "  " (double space) which never
        # appears in the line, so it fell through to a hard midpoint cut
        # that landed inside "Karpathy" → "K" + "arpathy".
        src = sources_text
        line1 = src
        line2 = ""
        if len(src) > 90:
            mid = len(src) // 2
            split = -1
            for sep in (" · ", ". "):
                idx = src.rfind(sep, 0, mid + 20)
                if idx == -1:
                    idx = src.find(sep, mid - 20)
                if idx != -1 and (split == -1 or abs(idx - mid) < abs(split - mid)):
                    split = idx + len(sep)
            if split == -1:
                # Last-ditch fallback: nearest space to the midpoint. Never
                # cut mid-word.
                split = src.rfind(" ", 0, mid + 20)
                if split == -1:
                    split = src.find(" ", mid)
                if split != -1:
                    split += 1
            if split != -1 and 0 < split < len(src):
                line1 = src[:split].rstrip()
                line2 = src[split:].lstrip()
        canvas.drawString(MARGIN_L, 14, _shape(line1, loc))  # type: ignore[attr-defined]
        if line2:
            canvas.drawString(MARGIN_L, 7, _shape(line2, loc))  # type: ignore[attr-defined]
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
        _para(label, s["section_compact"] if compact else s["section"]),
        HRFlowable(
            width="100%", thickness=0.75, color=RULE_LIGHT,
            spaceBefore=1, spaceAfter=2 if compact else 3,
        ),
    ]


def _subsec_header(label: str, color: HexColor = INK_SECONDARY, spacer: int = 5) -> Paragraph:
    return _para(
        label,
        _style(f"subsection_inline_{spacer}", fontName=_font("NunitoBold"),
               fontSize=8, leading=10, textColor=color, spaceBefore=spacer,
               spaceAfter=1),
    )


# ---------------------------------------------------------------------------
# Risk chip rendering — handles both ALL-CAPS bands AND italic Insufficient.
# ---------------------------------------------------------------------------


_RISK_CHIP_LABELS: dict[AppLocale, dict[RiskLevel, str]] = {
    "en": {
        "Low": "LOW",
        "Moderate": "MODERATE",
        "Elevated": "ELEVATED",
        "High": "HIGH",
        "Insufficient": "Insufficient data",
    },
    "es": {
        "Low": "BAJO",
        "Moderate": "MODERADO",
        "Elevated": "ELEVADO",
        "High": "ALTO",
        "Insufficient": "Datos insuficientes",
    },
    "ar": {
        "Low": "منخفض",
        "Moderate": "متوسط",
        "Elevated": "مرتفع نسبياً",
        "High": "عالٍ",
        "Insufficient": "بيانات غير كافية",
    },
}


def _risk_chip_paragraph(level: RiskLevel, locale: AppLocale = "en") -> Paragraph:
    loc = normalize_locale(locale)
    if level == "Insufficient":
        # Italic Roman sentence-case per §3.4 — italic is the redundant
        # visual differentiator that makes this chip read distinct from
        # "Low" (also a quiet/non-bold band) in B&W photocopy.
        return _para(
            _RISK_CHIP_LABELS[loc]["Insufficient"],
            _style(
                f"chip_{level}_{loc}",
                fontName=_font("NunitoItalic"),
                fontSize=7.5, leading=10,
                textColor=RISK_INK[level],
                alignment=TA_CENTER,
            ),
        )
    # Low gets quieter weight than warning levels (B&W diff per §3.4).
    font = _font("Nunito") if level == "Low" else _font("NunitoBold")
    return _para(
        _RISK_CHIP_LABELS[loc][level],
        _style(
            f"chip_{level}_{loc}",
            fontName=font, fontSize=7.5, leading=10,
            textColor=RISK_INK[level],
            alignment=TA_CENTER,
        ),
    )


# ---------------------------------------------------------------------------
# Document builder.
# ---------------------------------------------------------------------------


_DOC_LANG_BY_LOCALE: dict[AppLocale, str] = {
    "en": "en-US",
    "es": "es",
    "ar": "ar",
}


def _make_doc(buf: io.BytesIO, title: str, locale: AppLocale = "en") -> BaseDocTemplate:
    loc = normalize_locale(locale)
    doc = BaseDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title=title, author="FutureProof",
        subject="Career outcome data for student planning",
        keywords="career, college, major, outcomes, earnings",
        lang=_DOC_LANG_BY_LOCALE[loc],
    )
    frame = Frame(MARGIN_L, MARGIN_B, LIVE_W, PH - MARGIN_T - MARGIN_B,
                  id="main", showBoundary=0)
    on_page, on_last_page = _make_callbacks(title, loc)
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


def _year1_earnings_with_fallback(career: Any) -> tuple[float | None, bool]:
    """Pick the Year-1 earnings value to render, mirroring MoneySection.tsx.

    Returns (value, used_fallback). Order:
      1. ``earnings_1yr_median`` (program-specific Scorecard median).
      2. ``median_annual_wage`` (career-level OEWS mid-career) — used as a
         "career wage reference" when the program-level value is null.
      3. None — surface "—".

    used_fallback=True flags the cell for the asterisk + footnote pattern.
    """
    if career.earnings_1yr_median is not None:
        return career.earnings_1yr_median, False
    if career.median_annual_wage is not None:
        return career.median_annual_wage, True
    return None, False


def _about_this_career_section(build: Build, locale: AppLocale = "en") -> list[object]:
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
    if contains_forbidden_term(combined, CAREER_DESC_FORBIDDEN_TERMS):
        logger.warning(
            "pdf_export: forbidden term in career_description for soc=%s — "
            "skipping section.",
            build.career.soc_code,
        )
        return []

    s = _styles()
    story: list[object] = []

    loc = normalize_locale(locale)
    story.extend(_section_header(_t(loc, "section.about")))
    story.append(_para(_safe(summary), s["body"]))
    story.append(_subsec_header(_t(loc, "about.day_to_day"), spacer=5))

    # Bullets — hanging-indent paragraphs reusing s["body"]. Match the
    # density of the existing risk-profile rows.
    bullet_style = _style(
        "career_desc_bullet",
        fontName=_font("Nunito"), fontSize=9, leading=13,
        textColor=INK_SECONDARY,
        leftIndent=10, firstLineIndent=-10, spaceAfter=1,
    )
    for task in tasks:
        story.append(_para(f"&bull;&nbsp;&nbsp;{_safe(task)}", bullet_style))

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
            _para(
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

    return story


def _build_page1(build: Build, student_name: str | None, locale: AppLocale = "en") -> list[object]:
    loc = normalize_locale(locale)
    s = _styles()
    story: list[object] = []

    # Profile + context strip
    display_name = (
        (student_name or build.profile_name or "").strip()
        or _t(loc, "profile.default_name")
    )
    emoji = build.animal_emoji or ""
    name_label = f"{emoji}  {display_name}".strip()
    today = _format_date(datetime.now(timezone.utc), loc)
    major = build.career.program_name or build.major_text or _t(loc, "profile.program_fallback")
    hdr_left = _para(
        _safe(name_label),
        _style("hdr_name", fontName=_font("FredokaOne"), fontSize=14, leading=18,
               textColor=INK_PRIMARY),
    )
    # Meta strip aligns to the opposite edge from the name. For Arabic
    # the row gets flipped, so the meta needs to land on the LEFT after
    # mirroring — which means it must originate as TA_LEFT here so the
    # mirrored cell still aligns to its visual outer edge.
    hdr_right = _para(
        f"{_safe(build.school_name)}  ·  {_safe(major)}  ·  {today}",
        _style("hdr_meta", fontName=_font("Nunito"), fontSize=8.5, leading=11,
               textColor=INK_SECONDARY,
               alignment=TA_LEFT if loc == "ar" else TA_RIGHT),
    )
    hdr_rows, hdr_widths, hdr_style = _rtl_table(
        [[hdr_left, hdr_right]],
        [LIVE_W * 0.45, LIVE_W * 0.55],
        [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ],
    )
    hdr_table = Table(hdr_rows, colWidths=hdr_widths)
    hdr_table.setStyle(TableStyle(hdr_style))
    story.append(Spacer(1, 4))
    story.append(hdr_table)

    # Residency hint (muted, optional)
    if build.home_state and not build.career.is_out_of_state:
        story.append(_para(
            _t(loc, "profile.residency_in_state", state=_safe(build.home_state)),
            s["muted"],
        ))
    elif build.career.is_out_of_state:
        story.append(_para(_t(loc, "profile.residency_out_of_state"), s["muted"]))

    # Conditional data-coverage caveat (§3.5 / §3.11.5).
    # Italic Nunito 7.5pt INK_MUTED — italic is the load-bearing visual cue
    # for the FYI register (designer audit FAIL fix).
    caveat = data_coverage_caveat(build, loc)
    if caveat:
        story.append(Spacer(1, 6))
        story.append(_para(
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
    story.append(_para(_safe(verdict_line(build, loc)), s["verdict"]))
    story.append(Spacer(1, 8))

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
            _para("●", dot_style),
            _para(STAT_LABELS[key], s["stat_label"]),
            _para(val_str, s["data"]),
            _para(_stat_meaning(key), s["stat_meaning"]),
        ])
    # Stat micro-table — flip column order for Arabic so meaning lands
    # leftmost / dot lands rightmost (RTL reading order: dot → label →
    # value → meaning matches the LTR experience for Arabic readers).
    stat_rows, stat_widths, stat_micro_styles = _rtl_table(
        stat_rows,
        [0.18 * inch, 0.45 * inch, 0.55 * inch, 2.00 * inch],
        [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE_LIGHT),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [white, BG_ROW_ALT]),
        ],
    )
    stat_table = Table(stat_rows, colWidths=stat_widths,
                       rowHeights=[0.22 * inch] * 5)
    stat_table.setStyle(TableStyle(stat_micro_styles))
    pent_w = pentagon.width
    # Pentagon-to-the-left of the stat micro-table in LTR; for Arabic
    # we put pentagon on the right (visually rightmost) so the reader
    # sees pentagon first as their gaze enters the row from the right.
    pent_strip_rows, pent_strip_widths, pent_strip_style = _rtl_table(
        [[pentagon, stat_table]],
        [pent_w + 4, LIVE_W - pent_w - 4],
        [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ],
    )
    pent_stat_table = Table(pent_strip_rows, colWidths=pent_strip_widths)
    pent_stat_table.setStyle(TableStyle(pent_strip_style))
    story.append(pent_stat_table)
    story.append(Spacer(1, 8))

    # Cost & ROI strip — 4-year cost · modeled debt · year-1 earnings · debt-to-earnings %
    story.extend(_section_header(_t(loc, "section.cost_roi")))
    label_style = _style(
        "cost_label", fontName=_font("NunitoBold"), fontSize=8, leading=10,
        textColor=INK_SECONDARY, alignment=TA_CENTER,
    )
    value_style = _style(
        "cost_value", fontName=_font("SpaceMono"), fontSize=9, leading=12,
        textColor=INK_PRIMARY, alignment=TA_CENTER,
    )
    year1_val, year1_fallback = _year1_earnings_with_fallback(build.career)
    year1_label = _t(loc, "cost.year1_median_fb" if year1_fallback else "cost.year1_median")
    year1_text = f"{_fmt_currency(year1_val)}*" if year1_fallback else _fmt_currency(year1_val)
    cost_data = [[
        _para(_t(loc, "cost.4yr"), label_style),
        _para(_t(loc, "cost.modeled_debt"), label_style),
        _para(year1_label, label_style),
        _para(_t(loc, "cost.dte_yr1"), label_style),
    ], [
        _para(_fmt_currency(build.career.published_cost_4yr), value_style),
        _para(_fmt_currency(build.career.modeled_total_debt), value_style),
        _para(year1_text, value_style),
        _para(_fmt_pct(build.career.debt_to_earnings_annual), value_style),
    ]]
    cw = LIVE_W / 4
    cost_data, cost_strip_widths, cost_strip_styles = _rtl_table(
        cost_data,
        [cw] * 4,
        [
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (-1, -1), BG_ROW_ALT),
            ("LINEBELOW", (0, 0), (-1, 0), 0.5, RULE_LIGHT),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBEFORE", (1, 0), (-1, -1), 0.5, RULE_LIGHT),
        ],
    )
    cost_table = Table(cost_data, colWidths=cost_strip_widths)
    cost_table.setStyle(TableStyle(cost_strip_styles))
    story.append(cost_table)
    # Peer-band sub-line + standout/caution callout.
    # The Year-1 cell above renders THIS school's program median (when
    # populated). The peer band below contextualizes that figure against the
    # 25th–75th percentile of all schools' program medians within this
    # 2-digit CIP family (computed in src/gold/college_scorecard_career_
    # outcomes.py §cip_bands). Mirrors the on-screen Year1SalaryBar +
    # MoneySection design — the "Standout earnings" / "Earnings caution"
    # callouts surface when the program median sits outside its peer band.
    peer_p25 = build.career.earnings_1yr_p25
    peer_p75 = build.career.earnings_1yr_p75
    prog_med = build.career.earnings_1yr_median
    if peer_p25 is not None and peer_p75 is not None:
        peer_band_style = _style(
            "year1_peer_band", fontName=_font("Nunito"), fontSize=8,
            leading=11, textColor=INK_SECONDARY, alignment=TA_LEFT,
        )
        story.append(Spacer(1, 4))
        band = (
            f"<b>{_t(loc, 'cost.peer_band_label')}</b> "
            f"{_fmt_currency(peer_p25)} – {_fmt_currency(peer_p75)}"
        )
        if prog_med is None:
            tail = _t(loc, "cost.peer_band_unavailable")
        elif prog_med > peer_p75:
            tail = _t(
                loc, "cost.standout_clause",
                label=_t(loc, "cost.standout"),
                median=_fmt_currency(prog_med),
            )
        elif prog_med < peer_p25:
            tail = _t(
                loc, "cost.caution_clause",
                label=_t(loc, "cost.caution"),
                median=_fmt_currency(prog_med),
            )
        else:
            tail = _t(loc, "cost.inside_clause", median=_fmt_currency(prog_med))
        story.append(_para(band + tail, peer_band_style))
    if year1_fallback:
        # Asterisk footnote: program-median earnings unavailable for this
        # school; we substitute the career-level OEWS mid-career wage so the
        # reader has a salary anchor instead of a blank cell. Mirrors the
        # MoneySection.tsx fallback in /builds compare view.
        footnote_style = _style(
            "year1_footnote", fontName=_font("Nunito"), fontSize=7.5,
            leading=10, textColor=INK_SECONDARY, alignment=TA_LEFT,
        )
        story.append(Spacer(1, 2))
        story.append(_para(
            _t(loc, "cost.year1_footnote"),
            footnote_style,
        ))
    story.append(Spacer(1, 8))

    # Career Risk Profile — 5 rows
    story.extend(_section_header(_t(loc, "section.risk_profile")))
    hdr_style = _style(
        "risk_hdr", fontName=_font("NunitoBold"), fontSize=8, leading=10,
        textColor=white, alignment=TA_LEFT,
    )
    hdr_center = _style(
        "risk_hdr_c", fontName=_font("NunitoBold"), fontSize=8, leading=10,
        textColor=white, alignment=TA_CENTER,
    )
    risk_rows: list[list[object]] = [[
        _para(_t(loc, "risk.col.factor"), hdr_style),
        _para(_t(loc, "risk.col.level"), hdr_center),
        _para(_t(loc, "risk.col.context"), hdr_style),
    ]]
    cell_styles: list[object] = []
    for row_i, boss in enumerate(BOSS_ORDER, start=1):
        fight = next((f for f in build.gauntlet.fights if f.boss == boss), None)
        raw_score = fight.raw_score if fight else None
        level = risk_level_for_boss(boss, raw_score)
        context = (
            _t(loc, "risk.context.insufficient")
            if level == "Insufficient"
            else risk_one_liner(boss, level, build, loc)
        )
        risk_rows.append([
            _para(boss_advisory_label(boss, loc), s["body_sm"]),
            _risk_chip_paragraph(level, loc),
            _para(
                _safe(context),
                _style("ctx", fontName=_font("Nunito"), fontSize=8, leading=11,
                       textColor=INK_SECONDARY),
            ),
        ])
        cell_styles.append(("BACKGROUND", (1, row_i), (1, row_i), RISK_BG[level]))

    # Level column widened to 1.10in to fit "Insufficient data" italic chip.
    risk_col_w = [1.65 * inch, 1.10 * inch, LIVE_W - 1.65 * inch - 1.10 * inch]
    risk_rows, risk_col_w, cell_styles = _rtl_table(risk_rows, risk_col_w, cell_styles)
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


def _normalize_skill_title(s: str) -> str:
    return " ".join((s or "").lower().split())


def _skill_description(rec: SkillRec, pool: list[AppliedSkill]) -> str:
    """Return the richest description sentence available for a SkillRec.

    Prefers an ``AppliedSkill`` from the build's ``skill_pool`` matched by
    normalized title — its rationale is the same descriptive copy the
    student saw on the boss-fight cards. Falls back to the SkillRec's
    own rationale when no match exists.
    """
    target = _normalize_skill_title(rec.title)
    if target:
        for s in pool:
            if _normalize_skill_title(s.title) == target:
                return s.rationale
    return rec.rationale


def _build_page2(
    build: Build,
    audience_questions: AudienceQuestions,
    locale: AppLocale = "en",
) -> list[object]:
    loc = normalize_locale(locale)
    story: list[object] = []

    # "About this career" section (feature-career-description-on-pdf.md).
    # Originally placed on page 1 between verdict and pentagon (per the
    # design vision), but the section's ~150pt height pushed the 5-row
    # risk profile across the page boundary, leaving SUGGESTED SKILLS
    # stranded on page 3. Relocating to the top of page 2 — the natural
    # "context" lead-in before the skills/questions block — keeps the
    # PDF at a clean 2 pages. Silently skipped when no description is
    # attached or when defensive voice/length checks fail.
    story.extend(_about_this_career_section(build, loc))

    # SUGGESTED SKILLS
    story.extend(_section_header(_t(loc, "section.suggested_skills")))
    intro_style = _style("intro", fontName=_font("Nunito"), fontSize=8, leading=11,
                         textColor=INK_SECONDARY, spaceAfter=2)
    story.append(_para(
        _t(loc, "skills.intro"),
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

    bucket_label_keys = {
        "AI-Resilience": "skills.bucket.ai_resilience",
        "Career-Launch": "skills.bucket.career_launch",
        "Earnings-Ceiling": "skills.bucket.earnings_ceiling",
    }
    last_bucket: str | None = None
    for bucket_name, rec in flat_capped:
        if bucket_name != last_bucket:
            color = bucket_color_map.get(bucket_name, INK_SECONDARY)
            label = _t(loc, bucket_label_keys.get(bucket_name, "skills.bucket.career_launch"))
            story.append(_subsec_header(label, color=color, spacer=4))
            last_bucket = bucket_name

        title_style = _style(
            "skill_title", fontName=_font("NunitoBold"), fontSize=8.5, leading=11,
            textColor=INK_PRIMARY,
        )
        stat_suffix = f" ({_safe(rec.stat_impact)})" if rec.stat_impact else ""
        story.append(_para(f"• {_safe(rec.title)}{stat_suffix}", title_style))

        # Description sentence — matches what the student saw on the
        # boss-fight card when an AppliedSkill from skill_pool aligns by
        # title; otherwise falls back to the SkillRec's own rationale.
        description = _skill_description(rec, build.skill_pool)
        if description:
            desc_style = _style(
                "skill_desc", fontName=_font("Nunito"), fontSize=8, leading=11,
                textColor=INK_SECONDARY, leftIndent=10, spaceAfter=1,
            )
            story.append(_para(_safe(description), desc_style))
        story.append(Spacer(1, 3))

    story.append(HRFlowable(width="100%", thickness=1.0, color=INK_PRIMARY,
                            spaceBefore=2, spaceAfter=2))

    # QUESTIONS & FOLLOW-UPS
    story.extend(_section_header(_t(loc, "section.questions")))
    audience_blocks = (
        (_t(loc, "questions.ask_college"), STAT_ROI, audience_questions.ask_the_college),
        (_t(loc, "questions.ask_parents"), STAT_GRW, audience_questions.ask_your_parents),
        (_t(loc, "questions.ask_yourself"), STAT_RES, audience_questions.ask_yourself),
    )
    for label, color, qs in audience_blocks:
        story.append(_subsec_header(label, color=color, spacer=3))
        for q in qs:
            q_style = _style(
                f"q_{label}", fontName=_font("Nunito"), fontSize=8.5, leading=12,
                textColor=INK_SECONDARY, leftIndent=8,
            )
            story.append(_para(f"• {_safe(q.text)}", q_style))
        story.append(Spacer(1, 1))

    story.append(HRFlowable(width="100%", thickness=0.5, color=RULE_LIGHT,
                            spaceBefore=2, spaceAfter=3))

    # GLOSSARY (4-column, 2-pair layout, 8 entries)
    story.append(_para(
        _t(loc, "section.glossary"),
        _style("gloss_hdr", fontName=_font("FredokaOne"), fontSize=9, leading=11,
               textColor=INK_PRIMARY, spaceBefore=2, spaceAfter=1),
    ))
    # Copy verbatim from §3.11.3 (designer audit FAIL fix — 3 entries had
    # been truncated). Glossary text is fixed copy and not user-controlled,
    # so it doesn't go through _safe().
    glossary = [
        (_t(loc, "gloss.cip.term"), _t(loc, "gloss.cip.def")),
        (_t(loc, "gloss.soc.term"), _t(loc, "gloss.soc.def")),
        (_t(loc, "gloss.ern.term"), _t(loc, "gloss.ern.def")),
        (_t(loc, "gloss.roi.term"), _t(loc, "gloss.roi.def")),
        (_t(loc, "gloss.res.term"), _t(loc, "gloss.res.def")),
        (_t(loc, "gloss.grw.term"), _t(loc, "gloss.grw.def")),
        (_t(loc, "gloss.aura.term"), _t(loc, "gloss.aura.def")),
        (_t(loc, "gloss.career_risk.term"), _t(loc, "gloss.career_risk.def")),
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
        row: list[object] = [_para(l_term, term_style), _para(l_def, def_style)]
        if i < len(right):
            r_term, r_def = right[i]
            row += [_para(r_term, term_style), _para(r_def, def_style)]
        else:
            row += [_para("", def_style), _para("", def_style)]
        rows.append(row)
    # NO rowHeights — let the table auto-size per row. The 8pt definitions
    # wrap to 2-4 lines depending on content; a fixed 18pt row clipped them
    # and made adjacent rows visually collide. Auto-size + VALIGN=TOP makes
    # the term sit at the top of its row aligned with the start of the
    # definition wrap.
    rows, gloss_widths, gloss_styles = _rtl_table(
        rows,
        [term_w, def_w, term_w, def_w],
        [
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -2), 0.3, RULE_LIGHT),
            ("LINEBEFORE", (2, 0), (2, -1), 0.5, RULE_LIGHT),
        ],
    )
    gloss_table = Table(rows, colWidths=gloss_widths)
    gloss_table.setStyle(TableStyle(gloss_styles))
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


def _column_labels(builds: list[Build]) -> list[str]:
    """Per-column header labels for the comparison tables.

    A student can compare two builds at the same school with different
    careers (or the same career across schools that happen to share a
    leading word — "University of Illinois" vs "University of
    Michigan"). The naive `_short_school` collapses both cases into
    "University". This helper picks the smallest disambiguating label
    per column:
      - When the leading-token short label is unique across the set,
        return it (back-compat with the prior layout).
      - Otherwise fall back to "<School short> · <Career short>" so
        each column reads independently.
    """
    short_labels = [_short_school(b.school_name) for b in builds]
    seen: dict[str, int] = {}
    for label in short_labels:
        seen[label] = seen.get(label, 0) + 1
    out: list[str] = []
    for b, label in zip(builds, short_labels):
        if seen.get(label, 0) <= 1:
            out.append(label)
        else:
            career = (b.career.occupation_title or "").split(",")[0].strip()
            career_short = " ".join(career.split()[:2]) if career else ""
            out.append(f"{label} · {career_short}" if career_short else label)
    return out


def _build_comparison(builds: list[Build], locale: AppLocale = "en") -> list[object]:
    loc = normalize_locale(locale)
    s = _styles()
    n = len(builds)
    story: list[object] = []

    # Title strip — same-major and cross-major both supported.
    majors = {(b.career.program_name or b.major_text or "") for b in builds}
    same_major = len(majors) == 1 and bool(next(iter(majors)))
    title_subject = (
        next(iter(majors)) if same_major
        else _t(loc, "compare.title_subject_fallback")
    )
    today = _format_date(datetime.now(timezone.utc), loc)
    story.append(Spacer(1, 4))
    story.append(_para(
        _t(loc, "compare.title_template", subject=_safe(title_subject), n=n, date=today),
        _style("comp_top", fontName=_font("FredokaOne"), fontSize=13, leading=17,
               textColor=INK_PRIMARY),
    ))
    residency_parts: list[str] = []
    column_labels = _column_labels(builds)
    for b, label in zip(builds, column_labels):
        in_state = bool(b.home_state) and not b.career.is_out_of_state
        residency_text = _t(
            loc,
            "compare.residency_in_state" if in_state else "compare.residency_out_of_state",
        )
        residency_parts.append(f"{_safe(label)}: {residency_text}")
    story.append(_para(
        _t(loc, "compare.residency_prefix")
        + _t(loc, "compare.residency_join").join(residency_parts),
        s["muted"],
    ))
    story.append(Spacer(1, 2))
    story.append(HRFlowable(width="100%", thickness=1.0, color=INK_PRIMARY,
                            spaceAfter=4))

    # Mini-pentagon strip — school name + career so a same-school /
    # different-career comparison reads independently.
    col_w = LIVE_W / n
    career_style = _style(
        "comp_career", fontName=_font("Nunito"), fontSize=8, leading=10,
        textColor=INK_SECONDARY, alignment=TA_CENTER,
    )
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
        career_title = b.career.occupation_title or ""
        block_rows: list[list[object]] = [
            [_para(_safe(b.school_name), s["school_name"])],
        ]
        if career_title:
            block_rows.append([_para(_safe(career_title), career_style)])
        block_rows.append([pentagon])
        block = Table(block_rows, colWidths=[col_w - 8])
        block.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ]))
        school_blocks.append(block)
    # No label column on the mini-pentagon strip — flipping reverses the
    # block order so school index 0 lands on the right (where an Arabic
    # reader starts), matching the column order used by the tables below.
    strip_rows, strip_widths, strip_style = _rtl_table(
        [school_blocks],
        [col_w] * n,
        [
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LINEBEFORE", (1, 0), (n - 1, -1), 0.4, RULE_LIGHT),
        ],
    )
    school_strip = Table(strip_rows, colWidths=strip_widths)
    school_strip.setStyle(TableStyle(strip_style))
    story.append(school_strip)
    story.append(Spacer(1, 3))

    # STATS AT A GLANCE
    story.extend(_section_header(_t(loc, "section.stats_glance"), compact=True))
    stat_keys = ("ern", "roi", "res", "grw", "aura")
    label_w = 1.80 * inch
    val_w = (LIVE_W - label_w) / n
    column_labels = _column_labels(builds)
    hdr_row = [_para(_t(loc, "compare.stat_col_header"),
                         _style("stat_hdr", fontName=_font("NunitoBold"),
                                fontSize=8, leading=10, textColor=white))]
    for label in column_labels:
        hdr_row.append(_para(_safe(label),
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
        row: list[object] = [_para(f"{STAT_LABELS[key]}  {_stat_meaning(key)}", label_style)]
        for col_i, v in enumerate(vals):
            text = f"{v}/10" if v is not None else "—"
            style = s["comp_lead"] if col_i in leaders else s["comp_value"]
            row.append(_para(text, style))
            if col_i in leaders:
                cell_styles.append((
                    "BACKGROUND",
                    (col_i + 1, row_i), (col_i + 1, row_i),
                    LEADING_CELL_BG,
                ))
        rows.append(row)
    stat_rows, stat_widths, stat_cell_styles = _rtl_table(
        rows, [label_w] + [val_w] * n, cell_styles,
    )
    stat_tbl = Table(stat_rows, colWidths=stat_widths, repeatRows=1)
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
        *stat_cell_styles,
    ]))
    story.append(stat_tbl)
    story.append(Spacer(1, 4))

    # COST & ROI — leading direction per data reviewer leading-direction table
    story.extend(_section_header(_t(loc, "section.cost_roi"), compact=True))
    cost_label_w = 1.50 * inch
    cost_val_w = (LIVE_W - cost_label_w) / n
    hdr_style = _style("cost_hdr", fontName=_font("NunitoBold"), fontSize=8,
                       leading=10, textColor=white, alignment=TA_CENTER)
    lbl_style = _style("cost_lbl", fontName=_font("Nunito"), fontSize=8.5,
                       leading=11, textColor=INK_SECONDARY)
    data_style = _style("cost_data", fontName=_font("SpaceMono"), fontSize=9,
                        leading=12, textColor=INK_PRIMARY, alignment=TA_CENTER)
    # Year-1 earnings: per-build fallback to median_annual_wage when the
    # program-specific median is null (mirrors MoneySection.tsx). Track which
    # columns used the fallback so they get an asterisk + a footnote — same
    # pattern as the single-build PDF and the on-screen Compare view.
    year1_pairs = [_year1_earnings_with_fallback(b.career) for b in builds]
    year1_values: list[float | None] = [val for val, _ in year1_pairs]
    year1_fallbacks: list[bool] = [fb for _, fb in year1_pairs]
    # Peer band per school — `earnings_1yr_p25/p75` are 2-digit-CIP-family
    # cross-institution percentiles (src/gold/college_scorecard_career_
    # outcomes.py §cip_bands). Rendered as a separate "Year-1 peer band" row
    # so the program-median row above it is clearly THIS school's program,
    # not a peer-wide range. Mirrors MoneySection's two-axis design.
    peer_bands: list[tuple[float | None, float | None]] = [
        (b.career.earnings_1yr_p25, b.career.earnings_1yr_p75) for b in builds
    ]
    has_any_peer_band = any(p25 is not None and p75 is not None for p25, p75 in peer_bands)
    # Standout/caution flags per build (program median above peer p75 / below
    # peer p25). Used to color the program-median cells.
    year1_position: list[str | None] = []
    for (p25, p75), b in zip(peer_bands, builds):
        prog = b.career.earnings_1yr_median
        if p25 is None or p75 is None or prog is None:
            year1_position.append(None)
        elif prog > p75:
            year1_position.append("above")
        elif prog < p25:
            year1_position.append("below")
        else:
            year1_position.append("inside")
    # Internal stable IDs for row identity (locale-independent), with a
    # parallel locale-resolved label for rendering. Branch logic (peer-band
    # insertion, fallback handling, debt-to-earnings %-formatter) keys off
    # the ID, not the displayed label, so it works in every locale.
    cost_rows_meta: list[tuple[str, str, list[float | None], str]] = [
        ("cost_4yr", _t(loc, "cost.4yr"),
         [b.career.published_cost_4yr for b in builds], "low"),
        ("modeled_debt", _t(loc, "cost.modeled_debt"),
         [b.career.modeled_total_debt for b in builds], "low"),
        ("year1_median", _t(loc, "compare.cost.year1_program_median"),
         year1_values, "high"),
        ("dte_yr1", _t(loc, "cost.dte_yr1"),
         [b.career.debt_to_earnings_annual for b in builds], "low"),
    ]
    cost_table_rows: list[list[object]] = [
        [_para("", hdr_style)] +
        [_para(_safe(label), hdr_style) for label in _column_labels(builds)]
    ]
    cost_cell_styles: list[object] = []
    # Peer-band row inserts between "Modeled debt" (row 2) and "Year-1
    # program median" (row 3). Track its row index so it skips leader
    # highlighting (it's informational, not comparable as a single number).
    has_peer_band_row = has_any_peer_band
    program_median_row_offset = 1 if has_peer_band_row else 0
    for row_i, (row_id, label, values, direction) in enumerate(cost_rows_meta, start=1):
        if row_id == "year1_median" and has_peer_band_row:
            # Insert the peer-band row immediately above program-median.
            band_cells: list[object] = [
                _para(_t(loc, "compare.cost.year1_peer_band"), lbl_style)
            ]
            for p25, p75 in peer_bands:
                if p25 is None or p75 is None:
                    band_text = _t(loc, "compare.cost.peer_band_unavailable")
                else:
                    band_text = f"{_fmt_currency(p25)} – {_fmt_currency(p75)}"
                band_cells.append(_para(band_text, data_style))
            cost_table_rows.append(band_cells)
        actual_row_i = row_i + (program_median_row_offset if row_id in {
            "year1_median", "dte_yr1",
        } else 0)
        # Year-1 program median row: don't let a fallback value win the
        # "leading" highlight — we'd be comparing a year-1 program median
        # against a mid-career wage.
        leader_values: list[float | None]
        if row_id == "year1_median":
            leader_values = [
                v if not fb else None
                for v, fb in zip(values, year1_fallbacks)
            ]
        else:
            leader_values = values
        valid_leader: list[float] = [
            v for v in leader_values if v is not None
        ]
        if valid_leader:
            target = min(valid_leader) if direction == "low" else max(valid_leader)
            leaders = [
                i for i, v in enumerate(leader_values)
                if v is not None and v == target
            ]
            if len(leaders) > 1 and len(leaders) == len(valid_leader):
                leaders = []
        else:
            leaders = []
        formatter = _fmt_pct if row_id == "dte_yr1" else _fmt_currency
        cost_cells: list[object]
        if row_id == "year1_median":
            cost_cells = []
            for cv, fb, pos in zip(values, year1_fallbacks, year1_position):
                txt = _fmt_currency(cv)
                if fb:
                    txt += "*"
                if pos == "above":
                    txt = f'<font color="#2D7A4F"><b>{txt} ↑</b></font>'
                elif pos == "below":
                    txt = f'<font color="#8B1A1A"><b>{txt} ↓</b></font>'
                cost_cells.append(_para(txt, data_style))
        else:
            cost_cells = [_para(formatter(cv), data_style) for cv in values]
        row = [_para(label, lbl_style)] + cost_cells
        cost_table_rows.append(row)
        for col_i in leaders:
            cost_cell_styles.append(
                ("BACKGROUND",
                 (col_i + 1, actual_row_i), (col_i + 1, actual_row_i),
                 LEADING_CELL_BG)
            )
    cost_table_rows, cost_table_widths, cost_cell_styles = _rtl_table(
        cost_table_rows, [cost_label_w] + [cost_val_w] * n, cost_cell_styles,
    )
    cost_tbl = Table(cost_table_rows, colWidths=cost_table_widths, repeatRows=1)
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
    if any(year1_fallbacks):
        footnote_style = _style(
            "compare_year1_footnote", fontName=_font("Nunito"), fontSize=7.5,
            leading=10, textColor=INK_SECONDARY, alignment=TA_LEFT,
        )
        story.append(Spacer(1, 2))
        story.append(_para(
            _t(loc, "compare.year1_footnote"),
            footnote_style,
        ))
    story.append(Spacer(1, 4))

    # CAREER RISK PROFILE
    story.extend(_section_header(_t(loc, "section.risk_profile"), compact=True))
    risk_label_w = 1.50 * inch
    risk_val_w = (LIVE_W - risk_label_w) / n
    hdr_left = _style("risk_hdr", fontName=_font("NunitoBold"), fontSize=8,
                      leading=10, textColor=white)
    hdr_center = _style("risk_hdr_c", fontName=_font("NunitoBold"), fontSize=8,
                       leading=10, textColor=white, alignment=TA_CENTER)
    risk_lbl_style = _style("risk_lbl", fontName=_font("Nunito"), fontSize=8.5,
                            leading=11, textColor=INK_SECONDARY)
    risk_table_rows: list[list[object]] = [
        [_para(_t(loc, "risk.col.factor"), hdr_left)] +
        [_para(_safe(label), hdr_center) for label in _column_labels(builds)]
    ]
    risk_cell_styles: list[object] = []
    for row_i, boss in enumerate(BOSS_ORDER, start=1):
        risk_row: list[object] = [
            _para(boss_advisory_label(boss, loc), risk_lbl_style),
        ]
        for col_i, b in enumerate(builds):
            fight = next((f for f in b.gauntlet.fights if f.boss == boss), None)
            raw_score = fight.raw_score if fight else None
            level = risk_level_for_boss(boss, raw_score)
            risk_row.append(_risk_chip_paragraph(level, loc))
            risk_cell_styles.append((
                "BACKGROUND",
                (col_i + 1, row_i), (col_i + 1, row_i),
                RISK_BG[level],
            ))
        risk_table_rows.append(risk_row)
    risk_table_rows, risk_widths, risk_cell_styles = _rtl_table(
        risk_table_rows, [risk_label_w] + [risk_val_w] * n, risk_cell_styles,
    )
    risk_tbl = Table(risk_table_rows, colWidths=risk_widths, repeatRows=1)
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
    story.extend(_section_header(_t(loc, "section.where_each_ahead"), compact=True))
    ahead_lines = where_each_pulls_ahead(builds, loc)
    for line in ahead_lines:
        story.append(_para(
            _safe(line),
            _style("ahead", fontName=_font("Nunito"), fontSize=8, leading=11,
                   textColor=INK_SECONDARY),
        ))
    story.append(Spacer(1, 3))
    return story


# ---------------------------------------------------------------------------
# Comparison PDF — extended sections (page 2+).
#
# These sections mirror the depth of the on-screen CompareView:
#   - SCHOOL PROFILE: institution control + state + residency
#   - COST BREAKDOWN: tuition (in/out) + room/board + net price + 4yr
#   - CAREER BRANCHES: top related careers per build
#   - GEMMA'S VERDICT: editorial block (summary + Big Choice + pros/cons +
#     decade projection + pivot question), forwarded from the compare
#     screen via ExportComparisonPdfRequest.insights or fetched server-
#     side as a fallback.
# ---------------------------------------------------------------------------


def _short_name_row(builds: list[Build]) -> list[object]:
    """Per-school header row reused across the extended comparison
    sections so each table reads independently."""
    cells: list[object] = [_para(
        "",
        _style("ext_hdr_blank", fontName=_font("NunitoBold"), fontSize=8,
               leading=10, textColor=white),
    )]
    for label in _column_labels(builds):
        cells.append(_para(
            _safe(label),
            _style("ext_hdr_sch", fontName=_font("NunitoBold"), fontSize=8,
                   leading=10, textColor=white, alignment=TA_CENTER),
        ))
    return cells


def _build_comparison_school_profile(builds: list[Build], locale: AppLocale = "en") -> list[object]:
    """SCHOOL PROFILE section — institution control, state, residency."""
    loc = normalize_locale(locale)
    s = _styles()
    story: list[object] = []
    story.extend(_section_header(_t(loc, "section.school_profile"), compact=True))

    n = len(builds)
    label_w = 1.50 * inch
    val_w = (LIVE_W - label_w) / n

    rows: list[list[object]] = [_short_name_row(builds)]
    cell_styles: list[object] = []

    def _label(text: str) -> Paragraph:
        return _para(
            text,
            _style("ext_lbl", fontName=_font("NunitoBold"), fontSize=8,
                   leading=11, textColor=INK_SECONDARY),
        )

    def _val(text: str, *, lead: bool = False) -> Paragraph:
        return _para(
            text,
            s["comp_lead"] if lead else s["comp_value"],
        )

    rows.append([_label(_t(loc, "profile.row.type"))] + [
        _val(_safe(b.career.institution_control or "—")) for b in builds
    ])
    rows.append([_label(_t(loc, "profile.row.state"))] + [
        _val(_safe(b.career.state_abbr or "—")) for b in builds
    ])
    in_state_label = _t(loc, "compare.residency_in_state")
    out_of_state_label = _t(loc, "compare.residency_out_of_state")
    rows.append([_label(_t(loc, "profile.row.residency"))] + [
        _val(
            out_of_state_label if b.career.is_out_of_state
            else (in_state_label if b.home_state else "—")
        )
        for b in builds
    ])
    rows.append([_label(_t(loc, "profile.row.major"))] + [
        _val(_safe(_shorten(b.career.program_name or b.major_text or "—", 40)))
        for b in builds
    ])
    rows.append([_label(_t(loc, "profile.row.career"))] + [
        _val(_safe(_shorten(b.career.occupation_title or "—", 40)))
        for b in builds
    ])

    rows, widths, cell_styles = _rtl_table(
        rows, [label_w] + [val_w] * n, cell_styles,
    )
    tbl = Table(rows, colWidths=widths, repeatRows=1)
    tbl.setStyle(TableStyle([
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
    story.append(tbl)
    story.append(Spacer(1, 4))
    return story


def _build_comparison_cost_breakdown(builds: list[Build], locale: AppLocale = "en") -> list[object]:
    """COST BREAKDOWN section — residency-aware tuition + COA when the
    student's home state is known on every build; falls back to
    showing both in-state and out-of-state tuition rows + an
    in-state-only COA label when residency context is missing.

    The published ``cost_of_attendance_annual`` field is the school's
    in-state COA. For an out-of-state student attending a public
    school, the actual COA = in-state COA + (OOS tuition − in-state
    tuition). The residency-aware annual COA is derived from
    ``published_cost_4yr / 4`` (which the stat engine already computes
    correctly for each student's residency)."""
    loc = normalize_locale(locale)
    s = _styles()
    story: list[object] = []
    story.extend(_section_header(_t(loc, "section.cost_breakdown"), compact=True))

    # Residency context is "known" only when every build carries a
    # home_state. Mixing known + unknown across columns would force a
    # split label per cell — uglier than just falling back to the both-
    # tuitions presentation.
    residency_known = all(b.home_state for b in builds)

    n = len(builds)
    label_w = 1.80 * inch
    val_w = (LIVE_W - label_w) / n

    def _label(text: str) -> Paragraph:
        return _para(
            text,
            _style("ext_cost_lbl", fontName=_font("NunitoBold"), fontSize=8,
                   leading=11, textColor=INK_SECONDARY),
        )

    def _money_val(v: float | None, *, lead: bool = False) -> Paragraph:
        return _para(
            _fmt_currency(v),
            s["comp_lead"] if lead else s["comp_value"],
        )

    def _row_from_values(
        label: str,
        vals: list[float | None],
        *,
        lower_wins: bool = True,
    ) -> list[object]:
        valid = [v for v in vals if v is not None]
        if not valid:
            leaders: list[int] = []
        else:
            extreme = min(valid) if lower_wins else max(valid)
            leaders = [i for i, v in enumerate(vals) if v is not None and v == extreme]
            # Tie-breaker: when all real values tie, no one leads.
            if len(leaders) > 1 and len(leaders) == len(valid):
                leaders = []
        cells: list[object] = [_label(label)]
        for i, v in enumerate(vals):
            cells.append(_money_val(v, lead=i in leaders))
        return cells

    def _money_row(label: str, attr: str, *, lower_wins: bool = True) -> list[object]:
        vals: list[float | None] = [
            getattr(b.career, attr, None) for b in builds
        ]
        return _row_from_values(label, vals, lower_wins=lower_wins)

    rows: list[list[object]] = [_short_name_row(builds)]

    if residency_known:
        # Single tuition row — residency-correct value per school.
        # Per-cell value = OOS tuition when the student is out-of-state
        # at that school, otherwise in-state.
        tuition_vals: list[float | None] = []
        for b in builds:
            if b.career.is_out_of_state:
                tuition_vals.append(b.career.tuition_out_of_state)
            else:
                tuition_vals.append(b.career.tuition_in_state)
        rows.append(_row_from_values(_t(loc, "breakdown.tuition_residency"), tuition_vals))
    else:
        # No residency context — show both rows so the reader can pick.
        rows.append(_money_row(_t(loc, "breakdown.tuition_in"), "tuition_in_state"))
        rows.append(_money_row(_t(loc, "breakdown.tuition_out"), "tuition_out_of_state"))

    rows.append(_money_row(_t(loc, "breakdown.room_board"), "room_board_on_campus"))
    rows.append(_money_row(_t(loc, "breakdown.net_price"), "net_price_annual"))

    if residency_known:
        # Residency-aware annual COA = published_cost_4yr / 4 (the stat
        # engine has already added the OOS tuition gap for OOS students
        # at public schools). Avoids the confusing "COA < OOS tuition"
        # mismatch where the published in-state COA looks lower than
        # the OOS tuition row.
        coa_vals: list[float | None] = [
            (b.career.published_cost_4yr / 4) if b.career.published_cost_4yr is not None else None
            for b in builds
        ]
        rows.append(_row_from_values(_t(loc, "breakdown.coa_residency"), coa_vals))
    else:
        # Published COA is the school's in-state figure — label it
        # explicitly so a reader doesn't compare it against the OOS
        # tuition row above.
        rows.append(_money_row(_t(loc, "breakdown.coa_in_state"), "cost_of_attendance_annual"))

    rows.append(_money_row(_t(loc, "breakdown.cost_4yr"), "published_cost_4yr"))
    rows.append(_money_row(_t(loc, "breakdown.modeled_debt_total"), "modeled_total_debt"))

    rows, breakdown_widths, _ = _rtl_table(rows, [label_w] + [val_w] * n, [])
    tbl = Table(rows, colWidths=breakdown_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
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
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4))
    return story


def _build_comparison_branches(builds: list[Build], locale: AppLocale = "en") -> list[object]:
    """CAREER BRANCHES section — top 3 related careers per school."""
    if not any(b.branches for b in builds):
        return []  # No branch data → omit the section silently.

    loc = normalize_locale(locale)
    story: list[object] = []
    story.extend(_section_header(_t(loc, "section.career_branches"), compact=True))
    story.append(_para(
        _t(loc, "branches.intro"),
        _style("ext_intro", fontName=_font("Nunito"), fontSize=8, leading=11,
               textColor=INK_SECONDARY, spaceAfter=4),
    ))

    n = len(builds)
    col_w = LIVE_W / n

    def _label(text: str) -> Paragraph:
        return _para(
            _safe(text),
            _style("ext_branch_sch", fontName=_font("NunitoBold"), fontSize=8,
                   leading=10, textColor=INK_PRIMARY, alignment=TA_CENTER),
        )

    column_labels = _column_labels(builds)

    def _branch_block(b: Build, header_label: str) -> Table:
        rows: list[list[object]] = [[_label(header_label)]]
        if not b.branches:
            rows.append([_para(
                _t(loc, "branches.empty"),
                _style("ext_branch_empty", fontName=_font("NunitoItalic"),
                       fontSize=7.5, leading=10, textColor=INK_MUTED,
                       alignment=TA_CENTER),
            )])
        else:
            for branch in b.branches[:3]:
                title_cell = _para(
                    _safe(_shorten(branch.to_title or "—", 40)),
                    _style("ext_branch_title", fontName=_font("NunitoBold"),
                           fontSize=8, leading=10, textColor=INK_PRIMARY),
                )
                deltas = _format_branch_deltas(branch)
                meta_cell = _para(
                    _safe(deltas) if deltas else "—",
                    _style("ext_branch_meta", fontName=_font("Nunito"),
                           fontSize=7.5, leading=10, textColor=INK_SECONDARY),
                )
                rows.append([title_cell])
                rows.append([meta_cell])
        block = Table(rows, colWidths=[col_w - 8])
        block.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("BACKGROUND", (0, 0), (0, 0), BG_ROW_ALT),
            ("LINEBELOW", (0, 0), (0, 0), 0.5, RULE_LIGHT),
        ]))
        return block

    # Branches strip has no label column; flipping just reverses the
    # block order so school index 0 lands rightmost — same column order
    # as the data tables above.
    strip_rows, strip_widths, strip_style = _rtl_table(
        [[_branch_block(b, label) for b, label in zip(builds, column_labels)]],
        [col_w] * n,
        [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LINEBEFORE", (1, 0), (n - 1, -1), 0.4, RULE_LIGHT),
        ],
    )
    strip = Table(strip_rows, colWidths=strip_widths)
    strip.setStyle(TableStyle(strip_style))
    story.append(strip)
    story.append(Spacer(1, 4))
    return story


def _format_branch_deltas(branch: CareerBranch) -> str:
    """Compact 'ERN +2 · ROI -1' style summary for a branch.

    Only renders deltas that are non-None and non-zero. Empty result
    when nothing meaningful changes (rare — most branches shift at
    least one stat)."""
    parts: list[str] = []
    for label, val in (
        ("ERN", branch.delta_ern),
        ("ROI", branch.delta_roi),
        ("RES", branch.delta_res),
        ("GRW", branch.delta_grw),
    ):
        if val is None or val == 0:
            continue
        parts.append(f"{label} {val:+d}")
    return "  ·  ".join(parts)




def _shorten(text: str, max_len: int) -> str:
    """Truncate ``text`` to ``max_len`` chars with an ellipsis tail.

    Used by the comparison extended sections so multi-column tables
    don't blow out their cells when school names or career titles run
    long.
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def generate_build_pdf(
    build: Build,
    *,
    student_name: str | None,
    audience_questions: AudienceQuestions,
    locale: AppLocale = "en",
) -> bytes:
    """Render the 2-page My Build PDF for a single build.

    Returns PDF bytes. Never writes to disk.

    Caller MUST resolve audience_questions before calling (typically via
    pdf_questions.generate_audience_questions). This service is pure-sync
    rendering — no Gemma calls inside, no I/O.

    ``locale`` controls every PDF-rendered string (chrome, table headers,
    glossary, footnotes, sources line, page numbers). The data values
    themselves — school names, dollar amounts, percentages, source
    acronyms — are preserved verbatim per locale.py glossary rules.
    """
    loc = normalize_locale(locale)
    token = _current_locale.set(loc)
    try:
        _register_fonts()
        title = f"FutureProof · {build.school_name} · {build.career.program_name or build.major_text}"
        buf = io.BytesIO()
        doc = _make_doc(buf, title, loc)
        story: list[object] = _build_page1(build, student_name, loc)
        # Switch to "last" template BEFORE the page break — sources callback
        # fires on the next page rendered.
        story.append(NextPageTemplate("last"))
        story.append(PageBreak())
        story.extend(_build_page2(build, audience_questions, loc))
        doc.build(story)
        return buf.getvalue()
    finally:
        _current_locale.reset(token)


def generate_comparison_pdf(
    builds: list[Build],
    locale: AppLocale = "en",
) -> bytes:
    """Render the multi-page Comparison PDF for 2-4 builds.

    Cross-major comparisons are supported — the in-app CompareView shows
    them, the PDF matches that contract. Stats (0-10), cost/ROI (dollars
    and %), and the 5-row risk profile are all directly comparable
    across majors. Title falls back to the locale's "Career comparison"
    string when majors differ.

    Section flow (page-1 → tail):
        1. Mini-pentagon strip + STATS / COST & ROI / RISK / WHERE
           EACH PULLS AHEAD (the original 1-page summary)
        2. SCHOOL PROFILE (control, state, residency, major, career)
        3. COST BREAKDOWN (tuition in/out, R&B, net price, COA, debt)
        4. CAREER BRANCHES (top related careers per build, when
           branch data is present on at least one build)

    The PDF flows naturally across pages — ReportLab's flowables wrap
    onto page 2/3 as content demands. No explicit PageBreak is forced
    inside the comparison.
    """
    if not (2 <= len(builds) <= 4):
        raise ValueError(
            f"Comparison PDF requires 2-4 builds; got {len(builds)}"
        )
    loc = normalize_locale(locale)
    token = _current_locale.set(loc)
    try:
        _register_fonts()
        majors = {(b.career.program_name or b.major_text or "") for b in builds}
        same_major = len(majors) == 1 and bool(next(iter(majors)))
        title_subject = (
            next(iter(majors)) if same_major
            else _t(loc, "compare.title_subject_fallback")
        )
        title = _t(loc, "compare.title_label", subject=title_subject, n=len(builds))
        buf = io.BytesIO()
        doc = _make_doc(buf, title, loc)
        story: list[object] = [NextPageTemplate("last")]
        story.extend(_build_comparison(builds, loc))
        story.extend(_build_comparison_school_profile(builds, loc))
        story.extend(_build_comparison_cost_breakdown(builds, loc))
        story.extend(_build_comparison_branches(builds, loc))
        doc.build(story)
        return buf.getvalue()
    finally:
        _current_locale.reset(token)
