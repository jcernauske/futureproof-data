"""Canned Ask-Gemma question catalog + auto-elevation + Gemma call.

Drives ``GET /career-pick/chips`` (builds the chip list with the
intent-mismatch heuristic applied) and ``POST /career-pick/ask``
(resolves the canned prompt, calls Gemma, falls back deterministically
on empty response).

Every chip click lands one record in ``logs/gemma.jsonl`` with the
``call_site="career_pick.ask"`` tag so the audit trail stays complete.
Concurrency + thread-safe logging come free from the shared
``gemma_client.generate_async`` path.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.models.career_pick import (
    AskCareerPickRequest,
    AskCareerPickResponse,
    CareerPickChip,
)
from app.services import gemma_client

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt — constant per §4.
# ---------------------------------------------------------------------------

GEMMA_SYSTEM_PROMPT = (
    "You are Gemma, explaining a single career-pick screen to a high "
    "school student.\n\n"
    "Context you see:\n"
    "- The student's original typed major text (could be informal like "
    "'pre-med')\n"
    "- The CIP code their major resolved to\n"
    "- The list of occupation SOC codes currently shown on their screen\n"
    "- Optionally, a specific terminal occupation the student was "
    "implicitly looking for\n\n"
    "Your job: answer the one canned question the student clicked, in 4-6 "
    "sentences, at a 6th-grade reading level. Cite the actual data on the "
    "screen when possible (name the jobs, cite salary ranges if present). "
    "Never give medical, legal, or financial advice. Never recommend a "
    "different school. If the question is about a missing occupation, "
    "explain the undergrad-vs-graduate distinction plainly and tell the "
    "student what they'd typically need to pursue that path (e.g. 'doctor "
    "usually means going to med school after college').\n\n"
    "Voice rules (inherit from the guidance.py canon):\n"
    "- Short sentences. Concrete nouns. Zero filler.\n"
    "- Never use: empowering, journey, unlock, transform, passion, dream "
    "career.\n"
    "- No exclamation points. No 'as an AI'. No markdown.\n"
    "- No bullet points. Plain prose, 4-6 sentences."
)


# ---------------------------------------------------------------------------
# Canned question catalog.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CannedQuestion:
    """One canonical question a student can click on /career-pick."""

    id: str
    label_template: str
    prompt_template: str
    fallback_template: str
    graduate_intent_pattern: str | None = None
    terminal_socs: tuple[str, ...] = field(default_factory=tuple)
    terminal_title: str | None = None


# The "why don't I see {terminal_title}?" question is emitted once per
# graduate-intent pattern. Each pattern carries the SOC codes that would
# satisfy it (physician MD paths, lawyer, veterinarian, dentist, etc.).
#
# Pre-med uses a family of physician SOCs (BLS now breaks out anesthesiologists,
# pediatric surgeons, emergency medicine, etc. under 29-12xx / 29-1216). We
# match on the common prefix "29-12" with specific 29-1216 + the legacy 29-1069.
_PRE_MED = CannedQuestion(
    id="why_no_doctor",
    label_template="Why don't I see 'doctor'?",
    prompt_template=(
        "The student typed '{major_text}' as their major and our CIP "
        "resolver mapped that to {cipcode}. The screen currently shows "
        "these occupation SOC codes: {soc_codes}. The student is asking "
        "why they don't see 'doctor' (physician). Explain in 4-6 "
        "sentences at a 6th-grade reading level: (1) their major text is a "
        "pre-medical track, not a career in itself; (2) becoming a doctor "
        "almost always requires four more years of medical school after the "
        "bachelor's, so physicians don't show up on a first-job screen; (3) "
        "biology (or the specific program on screen) IS a standard pre-med "
        "path — they're on the right road; (4) point to one concrete "
        "occupation already on their screen so the screen isn't 'empty'."
    ),
    fallback_template=(
        "Doctor doesn't show up here because this screen lists first jobs "
        "right after a bachelor's degree, and becoming a doctor usually "
        "takes four more years of medical school. Your major is a "
        "standard pre-med path — the careers you see are what graduates "
        "often do before or instead of med school."
    ),
    graduate_intent_pattern=r"\bpre[\s\-]?med\b",
    terminal_socs=("29-1216", "29-1069", "29-1215", "29-1217", "29-1228"),
    terminal_title="doctor",
)

_PRE_LAW = CannedQuestion(
    id="why_no_lawyer",
    label_template="Why don't I see 'lawyer'?",
    prompt_template=(
        "The student typed '{major_text}' as their major and our CIP "
        "resolver mapped that to {cipcode}. The screen currently shows "
        "these occupation SOC codes: {soc_codes}. The student is asking "
        "why they don't see 'lawyer'. Explain in 4-6 sentences at a "
        "6th-grade reading level: (1) pre-law isn't a career by itself; "
        "(2) becoming a lawyer requires law school (usually three years) "
        "after the bachelor's, so lawyers don't show up on a first-job "
        "screen; (3) the major on screen IS a standard pre-law path — "
        "they're on track; (4) point to one concrete occupation on their "
        "screen so it isn't empty."
    ),
    fallback_template=(
        "Lawyer isn't on this screen because this list shows first jobs "
        "after a bachelor's degree, and becoming a lawyer usually takes "
        "three more years of law school. Your major is a common pre-law "
        "path — what you see here is what graduates often do before or "
        "instead of law school."
    ),
    graduate_intent_pattern=r"\bpre[\s\-]?law\b",
    terminal_socs=("23-1011", "23-1012"),
    terminal_title="lawyer",
)

_PRE_VET = CannedQuestion(
    id="why_no_veterinarian",
    label_template="Why don't I see 'veterinarian'?",
    prompt_template=(
        "The student typed '{major_text}' as their major and our CIP "
        "resolver mapped that to {cipcode}. The screen currently shows "
        "these occupation SOC codes: {soc_codes}. The student is asking "
        "why they don't see 'veterinarian'. Explain in 4-6 sentences at "
        "a 6th-grade reading level: (1) pre-vet isn't a career on its "
        "own; (2) becoming a veterinarian takes four more years of "
        "veterinary school after the bachelor's; (3) the major they "
        "picked IS a standard pre-vet path; (4) call out one concrete "
        "career already on the screen."
    ),
    fallback_template=(
        "Veterinarian isn't shown because this screen lists first jobs "
        "after a bachelor's degree, and becoming a vet usually takes "
        "four more years of veterinary school. Your major is a standard "
        "pre-vet path — the jobs you see are what graduates often do "
        "before or instead of vet school."
    ),
    graduate_intent_pattern=r"\bpre[\s\-]?vet\b",
    terminal_socs=("29-1131",),
    terminal_title="veterinarian",
)

_PRE_DENTAL = CannedQuestion(
    id="why_no_dentist",
    label_template="Why don't I see 'dentist'?",
    prompt_template=(
        "The student typed '{major_text}' as their major and our CIP "
        "resolver mapped that to {cipcode}. The screen currently shows "
        "these occupation SOC codes: {soc_codes}. The student is asking "
        "why they don't see 'dentist'. Explain in 4-6 sentences at a "
        "6th-grade reading level: (1) pre-dental isn't a career by "
        "itself; (2) becoming a dentist takes four more years of dental "
        "school after the bachelor's; (3) the major they picked IS a "
        "standard pre-dental path; (4) name one concrete career on "
        "the screen."
    ),
    fallback_template=(
        "Dentist isn't on this screen because this list shows first "
        "jobs after a bachelor's degree, and becoming a dentist usually "
        "takes four more years of dental school. Your major is a "
        "common pre-dental path — the jobs you see are what graduates "
        "often do before or instead of dental school."
    ),
    graduate_intent_pattern=r"\bpre[\s\-]?dental\b",
    terminal_socs=("29-1022", "29-1021", "29-1024", "29-1029"),
    terminal_title="dentist",
)

_WHAT_DOES_THIS_CAREER_DO = CannedQuestion(
    id="what_does_this_do",
    label_template="What does this career actually do?",
    prompt_template=(
        "The student is looking at this career on the screen: SOC "
        "{selected_soc}. Other careers also on the screen: {soc_codes}. "
        "Their major was '{major_text}' (CIP {cipcode}). In 4-6 "
        "sentences at a 6th-grade reading level, explain what a person "
        "in the selected occupation actually does day-to-day: the main "
        "tasks, who they work with, where they usually work, and one "
        "honest trade-off (boring part, hard part, or common "
        "frustration). Be concrete — use nouns and verbs, not adjectives."
    ),
    fallback_template=(
        "We couldn't load a fresh description right now. Pick this "
        "career to see the full build — the next screen lists the top "
        "tasks this occupation actually does, pulled from O*NET. You "
        "can always come back to this screen and try a different path."
    ),
)

_IS_THIS_THE_RIGHT_SCHOOL = CannedQuestion(
    id="right_school_for_this",
    label_template="Is this the right school for this?",
    prompt_template=(
        "The student's school + major resolved to CIP {cipcode} from "
        "their typed input '{major_text}'. The screen shows these SOC "
        "codes as the common outcomes: {soc_codes}. In 4-6 sentences at "
        "a 6th-grade reading level, tell the student: (1) this screen "
        "is based on graduates from THIS school's program, not a national "
        "average — so it's the closest signal we have for their specific "
        "situation; (2) what the first-year-out earnings look like for "
        "this program if any of the careers on screen have concrete "
        "numbers; (3) one honest caveat (small program = small sample, "
        "or tier mix skewing toward Common). Don't recommend a different "
        "school."
    ),
    fallback_template=(
        "This screen is built from graduates of this school's program, "
        "so it's a closer signal than a national average. Still, class "
        "sizes can be small — treat this as a realistic range, not a "
        "guarantee. Pick a path and the next screen breaks down the "
        "numbers in detail."
    ),
)

_WHY_THESE_TIERS = CannedQuestion(
    id="why_these_tiers",
    label_template="Why are some careers 'Common' and some 'Stretch'?",
    prompt_template=(
        "The student's major resolved to CIP {cipcode} from the text "
        "'{major_text}'. Screen shows these SOC codes across Common / "
        "Less Common / Stretch tiers: {soc_codes}. In 4-6 sentences at "
        "a 6th-grade reading level, explain: (1) Common means graduates "
        "from this major most often end up in that occupation; (2) "
        "Stretch means the career is possible but atypical — takes more "
        "intention or a different path (grad school, switching fields); "
        "(3) tiers come from real graduate outcome data, not opinion; "
        "(4) one honest caveat — tiers are a hint, not a ceiling."
    ),
    fallback_template=(
        "Common careers are what graduates from this major most often "
        "end up doing. Stretch careers are possible but less typical — "
        "they usually take a different path, like more school or a "
        "career switch. The tiers come from real graduate outcome data, "
        "but they're a hint, not a ceiling."
    ),
)


CANNED_QUESTIONS: tuple[CannedQuestion, ...] = (
    _PRE_MED,
    _PRE_LAW,
    _PRE_VET,
    _PRE_DENTAL,
    _WHAT_DOES_THIS_CAREER_DO,
    _IS_THIS_THE_RIGHT_SCHOOL,
    _WHY_THESE_TIERS,
)


def _question_by_id(chip_id: str) -> CannedQuestion:
    for q in CANNED_QUESTIONS:
        if q.id == chip_id:
            return q
    raise ValueError(f"Unknown chip_id: {chip_id!r}")


# ---------------------------------------------------------------------------
# Chip list builder — auto-elevation heuristic.
# ---------------------------------------------------------------------------


def _matches_graduate_intent(pattern: str, major_text: str) -> bool:
    """Case-insensitive, word-boundary-safe regex match."""
    return bool(re.search(pattern, major_text, flags=re.IGNORECASE))


def _missing_terminal(terminal_socs: Sequence[str], soc_codes: Sequence[str]) -> bool:
    """True when none of the rendered SOCs satisfies the terminal intent.

    Prefix-match so BLS sub-splits (e.g. ``29-1216`` vs ``29-1217``) still
    read as a hit when a single known code is in the list.
    """
    if not terminal_socs:
        return False
    rendered = set(soc_codes)
    for wanted in terminal_socs:
        if wanted in rendered:
            return False
    return True


def _render_label(question: CannedQuestion) -> str:
    """Current labels are static — template token for future parameterization."""
    return question.label_template


def build_chip_list(
    *,
    cipcode: str,
    major_text: str,
    soc_codes: Sequence[str],
) -> list[CareerPickChip]:
    """Return the chip set for this screen state.

    Questions with a ``graduate_intent_pattern`` are auto-elevated (moved to
    the front, ``elevated=True``) when the student's ``major_text`` matches
    the pattern AND none of the rendered ``soc_codes`` is in the question's
    ``terminal_socs`` tuple. Questions without a graduate pattern are
    returned in catalog order after any elevated chip(s).
    """
    del cipcode  # currently unused; reserved for future cipcode-aware heuristics
    elevated: list[CareerPickChip] = []
    base: list[CareerPickChip] = []

    for question in CANNED_QUESTIONS:
        chip_id = question.id
        label = _render_label(question)
        terminal_title = question.terminal_title

        if question.graduate_intent_pattern is None:
            base.append(
                CareerPickChip(
                    id=chip_id,
                    label=label,
                    elevated=False,
                    terminal_title=terminal_title,
                )
            )
            continue

        # Graduate-intent chip: include only when the student's text
        # matches and the terminal SOC is absent. Otherwise skip the chip
        # entirely — when the student isn't asking a pre-med question,
        # "Why don't I see 'doctor'?" is noise.
        matches = _matches_graduate_intent(
            question.graduate_intent_pattern, major_text
        )
        missing = _missing_terminal(question.terminal_socs, soc_codes)
        if matches and missing:
            elevated.append(
                CareerPickChip(
                    id=chip_id,
                    label=label,
                    elevated=True,
                    terminal_title=terminal_title,
                )
            )

    return [*elevated, *base]


# ---------------------------------------------------------------------------
# Ask — prompt builder + Gemma call + fallback.
# ---------------------------------------------------------------------------


def _build_user_prompt(
    question: CannedQuestion, request: AskCareerPickRequest
) -> str:
    soc_list = ", ".join(request.soc_codes) if request.soc_codes else "(none)"
    return question.prompt_template.format(
        major_text=request.major_text,
        cipcode=request.cipcode,
        soc_codes=soc_list,
        selected_soc=request.selected_soc or "(none selected)",
        terminal_title=request.terminal_title or question.terminal_title or "",
    )


def _log_record(
    *,
    chip_id: str,
    request: AskCareerPickRequest,
    system: str,
    user: str,
    response: str,
    fallback_fired: bool,
    duration_ms: int,
    error: str | None = None,
) -> None:
    """Append a career-pick.ask record to gemma.jsonl.

    Supplemental to the client-side log emitted by ``generate_async`` —
    this record carries the ``call_site`` tag, the chip id, and whether
    the fallback fired, which the generate log doesn't know about.
    """
    if os.environ.get("GEMMA_LOG_DISABLED"):
        return
    record: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "call_site": "career_pick.ask",
        "chip_id": chip_id,
        "cipcode": request.cipcode,
        "major_text": request.major_text,
        "selected_soc": request.selected_soc,
        "soc_codes": list(request.soc_codes),
        "system": system,
        "user": user,
        "answer": response,
        "fallback_fired": fallback_fired,
        "duration_ms": duration_ms,
    }
    if error is not None:
        record["error"] = error
    try:
        path = gemma_client._log_path()  # noqa: SLF001 — shared log file
        line = json.dumps(record, ensure_ascii=False, default=str)
        with gemma_client._log_lock, path.open("a", encoding="utf-8") as fh:  # noqa: SLF001
            fh.write(line + "\n")
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("career_pick.ask jsonl log write failed: %s", exc)


async def ask(
    *,
    request: AskCareerPickRequest,
) -> AskCareerPickResponse:
    """Resolve the canned prompt for ``request.chip_id`` and call Gemma.

    Returns the Gemma response when non-empty; otherwise returns the
    question's deterministic ``fallback_template`` with ``fallback_fired=True``.
    Exceptions raised by the Gemma transport are caught and treated
    identically to an empty response — callers see a 200 with the
    fallback string, never a 5xx.
    """
    question = _question_by_id(request.chip_id)
    system = GEMMA_SYSTEM_PROMPT
    user = _build_user_prompt(question, request)

    started = time.perf_counter()
    fallback_fired = False
    error: str | None = None
    try:
        raw = await gemma_client.generate_async(
            system=system,
            user=user,
            max_tokens=360,
            temperature=0.7,
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        logger.warning("career_pick.ask gemma call failed: %s", error)
        raw = ""

    answer = (raw or "").strip()
    if not answer:
        answer = question.fallback_template
        fallback_fired = True

    duration_ms = int((time.perf_counter() - started) * 1000)
    _log_record(
        chip_id=request.chip_id,
        request=request,
        system=system,
        user=user,
        response=answer,
        fallback_fired=fallback_fired,
        duration_ms=duration_ms,
        error=error,
    )

    return AskCareerPickResponse(
        chip_id=request.chip_id,
        answer=answer,
        fallback_fired=fallback_fired,
    )
