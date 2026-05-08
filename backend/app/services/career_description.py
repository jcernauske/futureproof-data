"""Plain-English career-description service.

See ``docs/specs/feature-career-description-on-pdf.md``.

Single Gemma call returns ``{summary, tasks[]}`` JSON anchored on O*NET
activity importance scores (Tier A), the BLS occupation description
(Tier B), or the occupation title + SOC major group (Tier C). Tier D
raises before invoking Gemma when no anchor at all is available
(malformed SOC, full pipeline failure).

Public surface:
    - ``async get_or_generate(soc_code, occupation_title) -> CareerDescription``
    - ``CareerDescriptionUnavailable`` (Tier D + exhausted retries)
    - ``clear_cache()`` (test/operator helper)

Three sites invoke this:
    1. ``GET /careers/{soc_code}/description`` (sparkle panel cold-cache fetch)
    2. Build-spawn pipeline in ``routers/builds.py`` (eager, joins
       ``_gemma_fanout``'s ``asyncio.gather``)
    3. PDF export router (lazy fallback when ``Build.career_description``
       is None)

Failure contract: every call site treats ``CareerDescriptionUnavailable``
and any unexpected exception as non-fatal — the description is omitted,
the build/PDF/panel still ships.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

from app.models.career import AnchorTier, CareerDescription
from app.services import gemma_client, mcp_client
from app.services.pdf_copy import (
    RPG_TERMS_FORBIDDEN_IN_PDF,
    contains_forbidden_term,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bump when prompts change to invalidate the per-process cache without a
# full restart story. Keyed on (soc, _PROMPT_VERSION) so concurrent demo
# users don't see drift across a hot prompt edit.
_PROMPT_VERSION = "v1"

_MAX_TOKENS = 400
_SUMMARY_CHAR_LIMIT = 500
_TASK_CHAR_LIMIT = 90
_TASKS_MIN = 4
_TASKS_MAX = 6

_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")

_CALL_SITE = "career_description"


# ---------------------------------------------------------------------------
# System prompts (authored by @fp-copywriter, §10 of the spec).
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TIER_A = """You are writing a short, plain-English description of a career for a high school student and their parents. The student is choosing a college major right now. They will read this on screen, and the same words will print on a one-page PDF that gets handed to a counselor or stuck on a fridge.

Career: {occupation_title}

Day-to-day activities for this occupation (sourced from O*NET, ranked by importance score from 0 to 5 — higher means the activity dominates the workday):
{anchor_block}
{multi_detail_note}
Your job: rewrite the highest-importance activities into a description of what a typical day looks like in this career. Use the activities you were given. Do not invent tasks that are not implied by the list. If two activities overlap, combine them; do not pad to fill space.

Voice: cool, direct, factual. Talk like a calm older sibling who has read the data. Short sentences. Concrete nouns. No hype, no warmup, no closer.

Output format — return ONLY this JSON object, nothing else, no prose before or after, no markdown fences:
{{"summary": "...", "tasks": ["...", "...", "...", "..."]}}

Rules:
- summary: 2 to 4 sentences. Maximum 500 characters total. Plain English. Describes the career and what the work is for. No bullet points inside the summary.
- tasks: 4 to 6 short bullets. Each task is one phrase, maximum 90 characters. Start each task with a verb in the present tense ("Review patient charts", "Run financial models", "Lead team standups"). Do not number them. Do not end with periods.
- Use plain words a 16-year-old understands. Technical terms only when the activity itself is technical, and never as jargon for its own sake.

Never use these words or framings — they belong to the app's game layer, not this description, and they will be rejected by an automated check:
boss, bosses, boss fight, gauntlet, fight, win, lose, draw, won, lost, build, builds, reroll, level up, leveled up, quest, battle, defeat, victory.

Never write: "exciting career", "rewarding career", "make a difference", "your journey", "passion", "dream job", "unlock", "empower", "transform". Never use exclamation points. Never start the summary with "This career" or "In this career" — describe the work directly.

Anchor on the activity list. Every task in your output must trace back to one of the activities above. The student will see the underlying data right next to your words, so do not embellish."""

_SYSTEM_PROMPT_TIER_B = """You are writing a short, plain-English description of a career for a high school student and their parents. The student is choosing a college major right now. They will read this on screen, and the same words will print on a one-page PDF that gets handed to a counselor or stuck on a fridge.

Career: {occupation_title}

BLS occupation summary (the only anchor you have for this occupation — there is no detailed activity profile available):
{anchor_block}

Your job: infer 4 to 6 day-to-day tasks from the BLS summary above. Stay close to what the summary actually says. Do not invent specifics — tools, software, certifications, client types, employer types, work settings — that are not implied by the summary. If the summary is vague on a point, leave that point out rather than filling it in.

Voice: cool, direct, factual. Talk like a calm older sibling who has read the data. Short sentences. Concrete nouns. No hype, no warmup, no closer.

Output format — return ONLY this JSON object, nothing else, no prose before or after, no markdown fences:
{{"summary": "...", "tasks": ["...", "...", "...", "..."]}}

Rules:
- summary: 2 to 4 sentences. Maximum 500 characters total. Plain English. Describes the career and what the work is for. No bullet points inside the summary.
- tasks: 4 to 6 short bullets. Each task is one phrase, maximum 90 characters. Start each task with a verb in the present tense. Do not number them. Do not end with periods.
- Use plain words a 16-year-old understands.

Never use these words or framings — they belong to the app's game layer, not this description, and they will be rejected by an automated check:
boss, bosses, boss fight, gauntlet, fight, win, lose, draw, won, lost, build, builds, reroll, level up, leveled up, quest, battle, defeat, victory.

Never write: "exciting career", "rewarding career", "make a difference", "your journey", "passion", "dream job", "unlock", "empower", "transform". Never use exclamation points. Never name a specific software product, certification body, or company unless the BLS summary names it first.

Anchor on the BLS summary. The student will see this PDF on a counselor's desk; an inflated description is immediately visible against the rest of the data. When in doubt, say less."""

_SYSTEM_PROMPT_TIER_C = """You are writing a short, plain-English description of a career for a high school student and their parents. The student is choosing a college major right now. They will read this on screen, and the same words will print on a one-page PDF that gets handed to a counselor or stuck on a fridge.

Career: {occupation_title}
Occupation family: {soc_major_group_name}

You have only the occupation title and the family it belongs to. There is no detailed activity profile and no occupation summary available for this role. Your description must reflect that.
{catchall_note}
Your job: describe the typical day in plain terms, at the level of the occupation family. Do not fabricate specific tools, software, certifications, employer names, or client types — none of that is implied by what you have. Speak about the kind of work the family does, with the title narrowing it where you can be confident. If you cannot be confident on a point, leave it out.

Voice: cool, direct, factual. Talk like a calm older sibling who has read the data. Short sentences. Concrete nouns. No hype, no warmup, no closer.

Output format — return ONLY this JSON object, nothing else, no prose before or after, no markdown fences:
{{"summary": "...", "tasks": ["...", "...", "...", "..."]}}

Rules:
- summary: 2 to 4 sentences. Maximum 500 characters total. Plain English. Describes the career and what the work is for at the family level. No bullet points inside the summary.
- tasks: 4 to 6 short bullets. Each task is one phrase, maximum 90 characters. Start each task with a verb in the present tense. Tasks should describe the kind of work the family does, not invented role-specific specifics. Do not number them. Do not end with periods.
- Use plain words a 16-year-old understands.

Never use these words or framings — they belong to the app's game layer, not this description, and they will be rejected by an automated check:
boss, bosses, boss fight, gauntlet, fight, win, lose, draw, won, lost, build, builds, reroll, level up, leveled up, quest, battle, defeat, victory.

Never write: "exciting career", "rewarding career", "make a difference", "your journey", "passion", "dream job", "unlock", "empower", "transform". Never use exclamation points. Never name a specific software product, certification body, employer, or salary figure — you do not have the data to back any of those, and the disclaimer line below your description tells the reader exactly that.

When in doubt, say less. The student will see a disclaimer noting this description is inferred from the title alone; an inflated description against that disclaimer reads dishonest."""


# Disclaimer strings rendered for Tier B/C generations. Used by both
# the panel header card chip and the PDF italic line. ≤80 chars each.
DISCLAIMER_TIER_B = (
    "AI-inferred from the BLS occupation summary, not from observed activity data."
)
DISCLAIMER_TIER_C = (
    "AI-inferred from the occupation title only — no detailed profile available."
)


# Strengthened-prompt suffixes for retries (architect §5 condition 2,
# decision row 18 in §2).
_RETRY_SUFFIX_PARSE = (
    "\n\nReminder: Output ONLY valid JSON matching the schema. "
    "No prose, no markdown fences, no commentary."
)


def _retry_suffix_voice(offending: list[str]) -> str:
    if not offending:
        return ""
    quoted = ", ".join(f'"{w}"' for w in offending)
    return (
        "\n\nReminder: Do not use the words: "
        f"{quoted}. They belong to the app's game layer, not this description."
    )


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CareerDescriptionUnavailable(RuntimeError):
    """Raised when generation cannot proceed (Tier D) or the bounded
    retry budget is exhausted (transport/parse/voice).

    Both call sites (eager spawn + lazy PDF) catch this and proceed
    without the description; the build, PDF, and sparkle panel all
    tolerate ``career_description=None``.
    """


# ---------------------------------------------------------------------------
# Single-flight cache (decision row 13)
# ---------------------------------------------------------------------------


# Concurrent misses for the same SOC fan out ONE Gemma call. After
# completion the Future stays in the cache — its ``.result()`` is the
# cached payload until ``clear_cache()`` or process restart.
_cache: dict[tuple[str, str], asyncio.Future[CareerDescription]] = {}
_cache_guard: asyncio.Lock | None = None


def _get_cache_guard() -> asyncio.Lock:
    global _cache_guard
    if _cache_guard is None:
        _cache_guard = asyncio.Lock()
    return _cache_guard


def clear_cache() -> None:
    """Drop the per-process cache. Used by tests and emergency
    operations (e.g., a copy regression mid-demo). Production
    invalidation strategy is "bump _PROMPT_VERSION + redeploy"."""
    _cache.clear()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_or_generate(
    soc_code: str,
    occupation_title: str,
) -> CareerDescription:
    """Return a cached or freshly generated CareerDescription.

    Single-flight per ``(soc_code, _PROMPT_VERSION)``. Failure cases:
        - SOC fails ``^\\d{2}-\\d{4}$`` → CareerDescriptionUnavailable (Tier D)
        - mcp_client.call returns no usable data + no occupation_title →
          CareerDescriptionUnavailable (Tier D)
        - Two consecutive Gemma failures (transport / parse / voice) →
          CareerDescriptionUnavailable
    """
    if not _SOC_PATTERN.match(soc_code):
        # Tier D — never call Gemma on a malformed SOC.
        raise CareerDescriptionUnavailable(f"malformed SOC: {soc_code!r}")

    key = (soc_code, _PROMPT_VERSION)

    # Fast-path under the lock: peek for an existing Future.
    guard = _get_cache_guard()
    async with guard:
        existing = _cache.get(key)
        if existing is not None:
            future = existing
        else:
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            _cache[key] = future
            # Schedule generation outside the lock so concurrent waiters
            # don't all sit on the guard waiting for the result.
            asyncio.create_task(_resolve_future(future, soc_code, occupation_title, key))

    return await future


async def _resolve_future(
    future: asyncio.Future[CareerDescription],
    soc_code: str,
    occupation_title: str,
    key: tuple[str, str],
) -> None:
    """Run generation and resolve ``future`` (success → set_result;
    failure → set_exception). On failure, evict the cache entry so a
    later call can retry.
    """
    try:
        result = await _generate(soc_code, occupation_title)
    except CareerDescriptionUnavailable as exc:
        # Don't keep a failed Future in the cache — transient transport
        # failures should be retryable on the next call.
        _cache.pop(key, None)
        future.set_exception(exc)
    except BaseException as exc:  # pragma: no cover - defensive
        _cache.pop(key, None)
        future.set_exception(exc)
    else:
        future.set_result(result)


# ---------------------------------------------------------------------------
# Generation pipeline
# ---------------------------------------------------------------------------


async def _generate(soc_code: str, occupation_title: str) -> CareerDescription:
    """Pick anchor tier, prompt, and run the retry-aware Gemma call."""
    breakdown = await _fetch_breakdown(soc_code)
    anchor_tier, system_prompt, user_prompt = _build_prompt(
        soc_code=soc_code,
        occupation_title=occupation_title,
        breakdown=breakdown,
    )

    # Two-call retry budget: parse-fail + voice-fail counted together.
    summary, tasks = await _generate_with_retries(system_prompt, user_prompt)

    config = gemma_client.current_config()
    return CareerDescription(
        soc_code=soc_code,
        summary=summary,
        tasks=tasks,
        anchor_tier=anchor_tier,
        generated_at=datetime.now(timezone.utc).isoformat(),
        model=config.model,
    )


async def _fetch_breakdown(soc_code: str) -> dict[str, Any]:
    """Call mcp_client.call_async('get_task_breakdown', ...).

    Returns the ``data`` dict (possibly empty) or an empty dict on
    upstream failure. The caller branches on the dict shape to pick
    the anchor tier.
    """
    try:
        result = await mcp_client.call_async(
            "get_task_breakdown", {"soc_code": soc_code}
        )
    except Exception as exc:
        logger.warning("get_task_breakdown failed for %s: %s", soc_code, exc)
        return {}
    data = result.get("data")
    if not isinstance(data, dict):
        return {}
    return data


def _build_prompt(
    soc_code: str,
    occupation_title: str,
    breakdown: dict[str, Any],
) -> tuple[AnchorTier, str, str]:
    """Choose anchor tier and assemble (system_prompt, user_prompt).

    Tier ladder per @fp-data-reviewer §5:
        A: parsed top_5_activities ≥ 4 entries (or top_human_activities ≥ 4)
        B: BLS `description` present
        C: occupation_title + SOC major group only
        D: malformed input (raise) — caught upstream
    """
    activities = _parse_activities(breakdown.get("top_5_activities"))
    if len(activities) < _TASKS_MIN:
        # Defensive — fall through to top_human_activities if available.
        activities = _parse_activities(breakdown.get("top_human_activities"))

    description = breakdown.get("description")
    multi_detail = bool(breakdown.get("multi_detail_flag"))

    # Tier A — full activity anchor.
    if len(activities) >= _TASKS_MIN:
        anchor_block = "\n".join(
            f"- {a['activity']} (importance {a['importance']:.2f})"
            for a in activities[:5]
        )
        multi_note = (
            "\nNote: this code covers multiple related occupations; "
            "describe the day-to-day at the group level rather than picking "
            "specifics.\n"
            if multi_detail
            else "\n"
        )
        system = _SYSTEM_PROMPT_TIER_A.format(
            occupation_title=occupation_title,
            anchor_block=anchor_block,
            multi_detail_note=multi_note,
        )
        user = (
            f"Career: {occupation_title}\n"
            f"SOC code: {soc_code}\n"
            "Write the JSON object now."
        )
        return ("activities", system, user)

    # Tier B — BLS description only.
    if isinstance(description, str) and description.strip():
        system = _SYSTEM_PROMPT_TIER_B.format(
            occupation_title=occupation_title,
            anchor_block=description.strip(),
        )
        user = (
            f"Career: {occupation_title}\n"
            f"SOC code: {soc_code}\n"
            "Write the JSON object now."
        )
        return ("description_only", system, user)

    # Tier C — title-only (always available; we have occupation_title from caller).
    if not occupation_title:
        # Tier D — no anchor at all.
        raise CareerDescriptionUnavailable(
            f"no anchor data for SOC {soc_code} and no occupation_title supplied"
        )

    soc_major_group = _soc_major_group_name(soc_code)
    catchall_note = ""
    title_lower = occupation_title.lower()
    if title_lower.endswith("all other") or title_lower.endswith("all, other"):
        catchall_note = (
            "\nThis is a catchall residual code — its title literally ends in "
            "'all other'. Acknowledge that in spirit (without using game-layer "
            "vocabulary): describe the family of related occupations rather "
            "than a single role.\n"
        )

    system = _SYSTEM_PROMPT_TIER_C.format(
        occupation_title=occupation_title,
        soc_major_group_name=soc_major_group,
        catchall_note=catchall_note,
    )
    user = (
        f"Career: {occupation_title}\n"
        f"SOC code: {soc_code}\n"
        f"Occupation family: {soc_major_group}\n"
        "Write the JSON object now."
    )
    return ("title_only", system, user)


def _parse_activities(raw: Any) -> list[dict[str, Any]]:
    """Coerce ``top_5_activities`` / ``top_human_activities`` to a clean
    list of ``{activity, importance}`` dicts.

    The MCP layer decodes JSON struct fields (see
    ``_decode_json_struct_fields`` in ``futureproof_server.py``), so the
    typical shape is already a list[dict]. Defensive code handles the
    legacy stringified-JSON case for parity with the data-reviewer's
    documented production shape.
    """
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return []
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        activity = item.get("activity")
        importance = item.get("importance")
        if not isinstance(activity, str) or not activity.strip():
            continue
        if not isinstance(importance, (int, float)):
            continue
        out.append({"activity": activity.strip(), "importance": float(importance)})
    return out


def _soc_major_group_name(soc_code: str) -> str:
    """Best-effort major-group label from the leading 2 digits.

    Aligned with O*NET / BLS major group names. We keep this local
    rather than reaching into a Gold table because the lookup is
    parameter-only (the prefix maps to a static label) and the Tier C
    prompt only needs a human-readable family name. Misses (unknown
    prefix) fall back to a generic phrase.
    """
    prefix = soc_code.split("-", 1)[0]
    return _SOC_MAJOR_GROUPS.get(prefix, "this occupation family")


# Static prefix → SOC major group label table. BLS Standard Occupational
# Classification 2018 major-group titles. Used by Tier C only.
_SOC_MAJOR_GROUPS: dict[str, str] = {
    "11": "management occupations",
    "13": "business and financial operations occupations",
    "15": "computer and mathematical occupations",
    "17": "architecture and engineering occupations",
    "19": "life, physical, and social science occupations",
    "21": "community and social service occupations",
    "23": "legal occupations",
    "25": "educational instruction and library occupations",
    "27": "arts, design, entertainment, sports, and media occupations",
    "29": "healthcare practitioners and technical occupations",
    "31": "healthcare support occupations",
    "33": "protective service occupations",
    "35": "food preparation and serving related occupations",
    "37": "building and grounds cleaning and maintenance occupations",
    "39": "personal care and service occupations",
    "41": "sales and related occupations",
    "43": "office and administrative support occupations",
    "45": "farming, fishing, and forestry occupations",
    "47": "construction and extraction occupations",
    "49": "installation, maintenance, and repair occupations",
    "51": "production occupations",
    "53": "transportation and material moving occupations",
    "55": "military specific occupations",
}


# ---------------------------------------------------------------------------
# Retry-aware Gemma call (decision row 18)
# ---------------------------------------------------------------------------


async def _generate_with_retries(
    system: str,
    user: str,
) -> tuple[str, list[str]]:
    """Run the Gemma call with at most one retry, classifying failures.

    Failure classes (per architect §5 item 2):
        empty string ⇒ transport failure → retry once with same prompt
        non-empty + parse fail ⇒ retry once with strengthened prompt
        non-empty + parse ok + voice fail ⇒ retry once with "do not use" reminder

    Two consecutive failures of any combination → CareerDescriptionUnavailable.
    """
    base_extra = {"call_site": _CALL_SITE}

    # Attempt 1
    raw = await gemma_client.generate_async(
        system=system,
        user=user,
        max_tokens=_MAX_TOKENS,
        temperature=0.4,
        extra=base_extra,
    )

    status, summary, tasks_or_offending = _parse_and_validate(raw)
    if status == "ok":
        return summary, tasks_or_offending

    retry_system = _strengthen_for_retry(system, status, tasks_or_offending)
    logger.info(
        "career_description retry for failure_class=%s offending=%s",
        status,
        tasks_or_offending,
    )

    # Attempt 2
    raw = await gemma_client.generate_async(
        system=retry_system,
        user=user,
        max_tokens=_MAX_TOKENS,
        temperature=0.2,  # Lower temperature on retry → less drift.
        extra={**base_extra, "retry_class": status},
    )

    status, summary, tasks_or_offending = _parse_and_validate(raw)
    if status == "ok":
        return summary, tasks_or_offending

    raise CareerDescriptionUnavailable(
        f"two consecutive Gemma failures (last={status}, offending={tasks_or_offending})"
    )


def _strengthen_for_retry(
    system: str, failure_class: str, offending: list[str],
) -> str:
    """Append a class-specific reminder to the original prompt."""
    if failure_class == "transport":
        # No prompt change can fix a transport failure; same prompt.
        return system
    if failure_class == "parse":
        return system + _RETRY_SUFFIX_PARSE
    if failure_class == "voice":
        return system + _retry_suffix_voice(offending)
    return system


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.S)


def _parse_and_validate(
    raw: str,
) -> tuple[str, str, list[str]]:
    """Parse ``raw`` and validate against length/voice rules.

    Returns a discriminated tuple ``(status, summary, tasks_or_offending)``:
        status="ok"        → summary=parsed summary, tasks_or_offending=tasks
        status="transport" → empty Gemma response (network/transport failure)
        status="parse"     → non-empty but malformed JSON / shape / lengths
        status="voice"     → parsed cleanly but contains forbidden RPG terms;
                             tasks_or_offending=list of offending terms for
                             retry-prompt strengthening
    """
    if not raw:
        return ("transport", "", [])

    stripped = _CODE_FENCE_RE.sub("", raw).strip()
    try:
        obj = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return ("parse", "", [])

    if not isinstance(obj, dict):
        return ("parse", "", [])

    summary = obj.get("summary")
    tasks_raw = obj.get("tasks")

    if not isinstance(summary, str) or not summary.strip():
        return ("parse", "", [])
    if not isinstance(tasks_raw, list):
        return ("parse", "", [])

    summary_clean = summary.strip()
    if len(summary_clean) > _SUMMARY_CHAR_LIMIT:
        return ("parse", "", [])

    tasks_clean: list[str] = []
    for item in tasks_raw:
        if not isinstance(item, str):
            return ("parse", "", [])
        text = item.strip().rstrip(".")
        if not text:
            continue
        if len(text) > _TASK_CHAR_LIMIT:
            return ("parse", "", [])
        tasks_clean.append(text)

    if not (_TASKS_MIN <= len(tasks_clean) <= _TASKS_MAX):
        return ("parse", "", [])

    # Voice validation — same RPG_TERMS frozenset as the rendered PDF.
    voice_violations = _collect_forbidden_terms(summary_clean, tasks_clean)
    if voice_violations:
        return ("voice", "", voice_violations)

    return ("ok", summary_clean, tasks_clean)


def _collect_forbidden_terms(summary: str, tasks: list[str]) -> list[str]:
    """Return the unique forbidden words found anywhere in summary or tasks.

    Used only to surface the offending words back into the retry prompt.
    The boolean check against ``contains_forbidden_term`` is the
    contract; this helper exists just so the retry can be specific.
    """
    text = summary + " " + " ".join(tasks)
    if not contains_forbidden_term(text, RPG_TERMS_FORBIDDEN_IN_PDF):
        return []
    seen: set[str] = set()
    found: list[str] = []
    for term in RPG_TERMS_FORBIDDEN_IN_PDF:
        pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.I)
        if pattern.search(text):
            t_low = term.lower()
            if t_low not in seen:
                seen.add(t_low)
                found.append(term)
    return found
