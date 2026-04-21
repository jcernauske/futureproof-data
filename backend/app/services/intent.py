"""Gemma intent resolution — maps free-text major input to a CIP code.

Extracted from cli.py._prompt_major_gemma_intent(). The CLI's Rich
console output stays in the CLI; this module handles the data flow only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from app.models.career import IntentResult
from app.services import gemma_client, major_lookup, mcp_client

logger = logging.getLogger(__name__)

_intent_cache: dict[tuple[str, int], dict[str, Any]] = {}

_CIP_PATTERN = re.compile(r"^\d{2}\.\d{4}$")
_CIP_FAMILY_PATTERN = re.compile(r"^\d{2}\.\d{2}$")


def _derive_intent_seed(prompt_input: str) -> int:
    """Deterministic seed per input so the same student text produces the
    same Gemma resolution across runs. Paired with temperature=0 this makes
    the live demo reproducible without a cache layer. 32-bit unsigned int,
    safely inside the OpenAI-compatible seed range."""
    normalized = " ".join(prompt_input.strip().lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def _promote_to_leaf_cip(
    matched_cip: str,
    parent_cip: str,
    school_cips: list[dict[str, str]],
) -> str:
    """Coerce ``matched_cip`` into a 6-digit leaf when Gemma handed back a
    4-digit umbrella.

    Gemma occasionally emits ``"13.10"`` (family) instead of ``"13.1001"``
    (leaf) for umbrella-ish inputs like "deaf ed". We defend the primary
    CIP contract here so the frontend doesn't fall through to the clarify
    picker every time Gemma skimps on precision.

    Resolution order:
    1. If ``matched_cip`` is already a 6-digit leaf, return it unchanged.
    2. If ``matched_cip`` is a 4-digit family AND ``parent_cip`` is a
       6-digit leaf, Gemma swapped the two — promote ``parent_cip``.
    3. If ``matched_cip`` is a 4-digit family, scan the school's reported
       CIPs for a leaf whose family prefix matches; pick the
       lexicographically first one (deterministic + usually the primary
       program in that family).
    4. Otherwise return the original value so the caller's downstream
       validation can raise.
    """
    if _CIP_PATTERN.match(matched_cip):
        return matched_cip
    if _CIP_FAMILY_PATTERN.match(matched_cip):
        if _CIP_PATTERN.match(parent_cip):
            return parent_cip
        family_prefix = matched_cip[:5]  # "13.10"
        descendants = sorted(
            c["cipcode"]
            for c in school_cips
            if c.get("cipcode", "").startswith(family_prefix)
            and _CIP_PATTERN.match(c["cipcode"])
        )
        if descendants:
            return descendants[0]
    return matched_cip

# DUPLICATE: this prompt is mirrored in backend/cli.py:_INTENT_SYSTEM_PROMPT.
# Edits here MUST be applied to the CLI copy (consolidation tracked as
# follow-up in docs/specs/feature-gemma-tiered-matching.md §11).
_INTENT_SYSTEM_PROMPT = """\
You map a student's free-text major to a CIP (Classification of \
Instructional Programs) code. Pick the most specific CIP that matches \
their intent. Full stop.

Students, parents, counselors, and registrars describe the same program \
differently:
- Students: "pre-med", "CS", "business", "art"
- Parents: "Physical Therapy", "Deaf Education", "Criminal Justice"
- Counselors: "Special Ed", "STEM", "Allied Health"
- Registrars: "CIP 51.2308 Physical Therapy/Therapist"

Read through the surface form to the program underneath.

Confidence tiers drive how many alternatives you return.

- "high": The input resolves to exactly one CIP — no ambiguity, even if \
the phrasing is colloquial. Output exactly "alternatives": [].
  Example: "pre-PT" -> 51.2308 Physical Therapy/Therapist.

- "medium": The input is a well-known shorthand or umbrella term that \
maps to a primary CIP but reasonable students mean different things. \
Return 2-4 alternatives, ordered by how likely you'd pick each if the \
student had phrased it differently. Alternatives must be genuinely \
distinct programs and may span CIP families when a cross-family reading \
is plausible.
  Example: "business" (primary: 52.0201 Business Administration; \
alternatives: 52.0801 Finance, 52.1401 Marketing, 52.0701 \
Entrepreneurship, 42.2804 Industrial-Organizational Psychology).

- "low": The input is too vague, ambiguous, or non-program-like for you \
to stake a primary match confidently. Still return your best primary, \
but include up to 10 alternatives spanning the plausible CIP \
neighborhoods. The frontend will show a picker rather than your primary.
  Examples: "helping people", "something with computers but not coding".

Never pad. If you are high-confident, "alternatives" MUST be []. \
Never exceed 10.

The student typed: "{student_input}"
School: {school_name}

Candidate CIPs — programs reported by this school:
{school_cip_list}

Candidate CIPs — specific programs in the same families from the \
national crosswalk:
{crosswalk_cip_list}

Both lists above are equally valid match candidates. Do NOT prefer a \
school-reported CIP over a crosswalk CIP to "preserve earnings data" — \
the backend blends earnings automatically when it substitutes a broad \
school CIP with a specific cousin. Your job is the match; the blending \
is not yours to protect.

Respond in JSON only, no preamble, no markdown.

"matched_cip" MUST be the full 6-digit leaf format XX.XXXX (e.g. \
13.1001, 51.2308, 52.0201). NEVER put a 4-digit umbrella like XX.XX \
there — if the student's intent lands on a whole family rather than \
one specific program, pick the single most representative leaf from the \
candidates above and put the 4-digit family code in "parent_cip".

"reasoning" is shown to the student. Keep it to one or two sentences. \
Name the program and the tell that anchored the match. Direct, \
confident, no hedging. Do not say "based on" or "as an AI" or "I'm \
not certain" — state the call.

{{"matched_cip": "XX.XXXX", "matched_title": "Program Title", \
"confidence": "high|medium|low", \
"reasoning": "One or two sentences naming the program and why it fits.", \
"parent_cip": "XX.XX (4-digit family code, may equal matched_cip[:5] \
when matched_cip is already a leaf in this family)", \
"alternatives": []}}\
"""

_AUDIT_SYSTEM_PROMPT = """\
You are an auditor checking whether a student's major selection makes sense.

The student typed: "{student_input}"
The system mapped it to: {matched_cip} — {matched_title}
Career outcomes for this mapping include: {top_3_career_titles}

Does the student's input plausibly refer to this academic program?

Respond in JSON only, no preamble, no markdown:
{{"valid": true|false, "tone": "clean|playful_warning|hard_reject", \
"message": "Your message to the student"}}

Rules:
- If the mapping is legitimate: valid=true, tone="clean", message is \
a brief encouraging confirmation
- If the input is vaguely off but close enough: valid=true, \
tone="playful_warning", message gently notes the mismatch but accepts it
- If the input is obviously nonsense, adversarial, or a joke: \
valid=false, tone="hard_reject", message calls it out directly. \
Be real with them. This is a $100K+ decision. Don't be mean, but \
don't play along.
- Keep it short — 1-2 sentences max\
"""


def _get_school_cips(unitid: int) -> list[dict[str, str]]:
    server = mcp_client.get_server()
    sql = (
        "SELECT DISTINCT cipcode, program_name "
        "FROM consumable_career_outcomes "
        f"WHERE unitid = {int(unitid)} "
        "ORDER BY cipcode"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
    return [
        {"cipcode": str(r["cipcode"]), "program_name": str(r.get("program_name", ""))}
        for r in rows
        if r.get("cipcode")
    ]


def _get_crosswalk_cips_for_families(
    family_prefixes: list[str],
) -> list[dict[str, str]]:
    if not family_prefixes:
        return []
    server = mcp_client.get_server()
    conditions = " OR ".join(
        f"SUBSTR(cipcode, 1, 2) = '{p[:2]}'" for p in family_prefixes
    )
    sql = (
        f"SELECT DISTINCT cipcode, cip_title "
        f"FROM base_cip_soc_crosswalk "
        f"WHERE ({conditions}) "
        f"ORDER BY cipcode"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
    return [
        {"cipcode": str(r["cipcode"]), "cip_title": str(r.get("cip_title", ""))}
        for r in rows
        if r.get("cipcode")
    ]


def _sample_crosswalk(
    cips: list[dict[str, str]], max_total: int = 60
) -> list[dict[str, str]]:
    """Sample evenly across CIP families so every family gets representation.

    A naive ``cips[:60]`` starves high-numbered families (biology, health,
    business) when a large school spans many CIP families.
    """
    if len(cips) <= max_total:
        return cips

    from collections import defaultdict

    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for c in cips:
        family = c.get("cipcode", "")[:2]
        by_family[family].append(c)

    families = sorted(by_family)
    per_family = max(1, max_total // len(families))
    result: list[dict[str, str]] = []
    for fam in families:
        result.extend(by_family[fam][:per_family])

    if len(result) < max_total:
        remaining = [c for c in cips if c not in result]
        result.extend(remaining[: max_total - len(result)])

    return result[:max_total]


def _get_career_titles_for_cip(cipcode: str) -> list[str]:
    server = mcp_client.get_server()
    prefix = cipcode[:5] if len(cipcode) >= 5 else cipcode
    if not re.match(r"^\d{2}\.\d{2}", prefix):
        return []
    sql = (
        "SELECT DISTINCT soc_title "
        "FROM base_cip_soc_crosswalk "
        f"WHERE SUBSTR(cipcode, 1, 5) = '{prefix}' "
        "AND soc_title IS NOT NULL "
        "ORDER BY soc_title "
        "LIMIT 5"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
    return [str(r["soc_title"]) for r in rows if r.get("soc_title")]


def _call_gemma_intent(
    student_input: str,
    school_name: str,
    school_cips: list[dict[str, str]],
    crosswalk_cips: list[dict[str, str]],
    clarification: str | None = None,
) -> tuple[dict[str, Any] | None, float, dict[str, Any]]:
    school_cip_list = "\n".join(
        f"- {c['cipcode']} {c['program_name']}" for c in school_cips
    )
    crosswalk_cip_list = "\n".join(
        f"- {c['cipcode']} {c['cip_title']}"
        for c in _sample_crosswalk(crosswalk_cips, max_total=60)
    )
    prompt_input = student_input
    if clarification:
        prompt_input = f"{student_input} (clarification: {clarification})"

    system = _INTENT_SYSTEM_PROMPT.format(
        student_input=prompt_input,
        school_name=school_name,
        school_cip_list=school_cip_list or "(no programs reported)",
        crosswalk_cip_list=crosswalk_cip_list or "(no crosswalk data)",
    )

    start = time.perf_counter()
    raw_response = gemma_client.generate(
        system=system,
        user=f'Match this student input to a CIP code: "{prompt_input}"',
        max_tokens=1500,
        temperature=0.0,
        seed=_derive_intent_seed(prompt_input),
    )
    latency = time.perf_counter() - start

    config = gemma_client.current_config()
    stats: dict[str, Any] = {
        "latency_s": round(latency, 2),
        "model": config.model,
        "backend": config.backend,
        "raw_response": raw_response,
    }

    if not raw_response:
        return None, latency, stats

    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    # Drop any trailing prose Gemma appends after the top-level JSON body.
    last_brace = cleaned.rfind("}")
    if last_brace != -1:
        cleaned = cleaned[: last_brace + 1]
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        stats["parse_error"] = f"Could not parse JSON: {cleaned[:200]}"
        return None, latency, stats

    return parsed, latency, stats


def _sanitize_alternatives(
    raw: Any, primary_cip: str
) -> list[dict[str, str]] | None:
    """Drop malformed/duplicate alternatives and clamp to 10.

    Gemma occasionally hallucinates CIP codes, echoes the primary CIP in
    the alternatives list, or returns a non-list value entirely. We defend
    the frontend contract here rather than raising.
    """
    if not isinstance(raw, list):
        return None
    seen: set[str] = {primary_cip}
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        raw_cip = item.get("cip")
        raw_title = item.get("title")
        if not isinstance(raw_cip, str) or not isinstance(raw_title, str):
            continue
        cip = raw_cip.strip()
        title = raw_title.strip()
        if not cip or not title:
            continue
        if not _CIP_PATTERN.match(cip):
            continue
        if cip in seen:
            continue
        seen.add(cip)
        raw_why = item.get("why", "")
        why = raw_why.strip() if isinstance(raw_why, str) else ""
        cleaned.append({
            "cip": cip,
            "title": title,
            "why": why,
        })
        if len(cleaned) == 10:
            break
    return cleaned


def _audit_intent_mapping(
    student_input: str,
    matched_cip: str,
    matched_title: str,
    career_titles: list[str],
) -> dict[str, Any] | None:
    top_3 = ", ".join(career_titles[:3]) or "unknown"
    system = _AUDIT_SYSTEM_PROMPT.format(
        student_input=student_input,
        matched_cip=matched_cip,
        matched_title=matched_title,
        top_3_career_titles=top_3,
    )
    raw = gemma_client.generate(
        system=system,
        user=(
            f'Student typed: "{student_input}"\n'
            f"Mapped to: {matched_cip} — {matched_title}\n"
            f"Careers: {top_3}\n"
            "Is this a valid mapping?"
        ),
        max_tokens=200,
        temperature=0.3,
    )
    if not raw:
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def _derive_parent_cip(
    cip4: str, programs: Sequence[Mapping[str, Any]]
) -> str:
    """Pick the school's reported broader-family CIP (if any) that the
    YAML-matched cip4 should substitute against.

    The frontend uses a non-empty ``parent_cip`` as the "substitution will
    apply" signal on the major-confirm card (MajorInput.tsx:102). On the
    /build/outcomes side, ``_handle_get_career_paths`` fires the
    substitution branch when the caller passes a broad CIP
    (``_is_broad_cip``) AND the YAML has a specific cip4. We surface the
    broad reported CIP here so the confirm card matches what outcomes
    will do.

    Rules (tight — callers pass raw programs from IntentRequest, so we
    defend against missing/bad cipcode values):

    - If ``programs`` contains an entry whose canonical 4-digit cipcode
      equals ``cip4`` exactly, the school reports the specific program.
      No substitution needed — return ``""``.
    - Otherwise, scan for an entry in the same 2-digit family as ``cip4``
      that matches ``_BROAD_CIP_PATTERN`` semantics (raw ``XX.01`` or
      zero-padded ``XX.0100``). Specific 6-digit forms (``XX.0101``) do
      not qualify as a substitution parent. Return the first match's
      canonical 4-digit form.
    - Otherwise return ``""``. The outcomes path will handle the miss
      via its existing broadening fallback.
    """
    if not cip4 or not programs:
        return ""
    family = cip4[:2]
    if not family.isdigit():
        return ""
    candidates: list[str] = []
    for program in programs:
        # FastAPI validates IntentRequest.programs as list[dict], but
        # defend against direct internal callers that might bypass
        # that validation (CLI, future tests).
        if not isinstance(program, Mapping):
            continue
        raw = str(program.get("cipcode", "") or "")
        if not raw:
            continue
        canonical = raw[:5] if len(raw) >= 5 else raw
        if canonical == cip4:
            return ""
        if canonical[:2] != family:
            continue
        if raw in (f"{family}.01", f"{family}.0100"):
            candidates.append(canonical)
    return candidates[0] if candidates else ""


def resolve_intent(
    major_text: str,
    school_name: str,
    unitid: int,
    programs: list[dict],
) -> IntentResult:
    """Resolve a student's free-text major to an ``IntentResult``.

    Post-condition asymmetry on ``matched_cip``: the Gemma path guards
    with ``_CIP_PATTERN`` (6-digit XX.XXXX, see the ``ValueError`` at
    the malformed-primary check below) and raises on a 4-digit leak.
    The deterministic YAML short-circuit can return a 4-digit family
    code when the YAML entry itself stores a family (e.g. "Special
    Education" → ``13.10``) AND the school's catalog has no descendant
    leaf for ``_promote_to_leaf_cip`` to promote to. Downstream MCP
    queries accept 4-digit cipcodes (``_CIPCODE_PATTERN`` in
    ``futureproof_server.py`` permits XX.YY and XX.YYYY), so neither
    path crashes, but a consumer that assumes 6-digit leaves must
    handle both post-conditions.
    """
    normalized = major_text.lower().strip()
    cache_key = (normalized, unitid)

    if cache_key in _intent_cache:
        cached = _intent_cache[cache_key]
        return IntentResult(
            matched_cip=cached["cip"],
            matched_title=cached["title"],
            confidence=cached.get("confidence", "high"),
            reasoning=cached.get("reasoning", "Cache hit"),
            careers_preview=cached.get("careers_preview", []),
            parent_cip=cached.get("parent_cip", ""),
        )

    # Deterministic YAML short-circuit. When the student's input is an
    # exact or alias match for a known major in
    # data/reference/major_to_cip.yaml, we have the answer without
    # calling Gemma — skip both the Gemma call and the prompt-bias
    # failure mode that broad-CIP schools otherwise trigger.
    #
    # parent_cip contract: frontend reads `parent_cip !== ""` as "the
    # backend will substitute on /build/outcomes" (MajorInput.tsx:102).
    # _derive_parent_cip walks the school's reported programs to pick
    # the broad same-family CIP when it exists, so the confirm card and
    # outcomes stay in sync.
    #
    # Cache policy: this block deliberately does NOT write to
    # _intent_cache. Cache writes are owned by confirm_intent and
    # happen only after the student confirms the match — same
    # invariant as the Gemma path.
    #
    # INTENT_YAML_ENABLED gate: set to "false" to skip the YAML
    # short-circuit entirely so every input goes through Gemma. Read
    # per-call (not at import) so tests and scripts can flip it via
    # monkeypatch.setenv / os.environ assignment without a process
    # restart. Default "true" preserves today's production behavior.
    yaml_enabled = (
        os.environ.get("INTENT_YAML_ENABLED", "true").strip().lower() == "true"
    )
    deterministic = (
        major_lookup.lookup_major(major_text) if yaml_enabled else None
    )
    if deterministic is not None:
        cip4 = str(deterministic.get("cip4", ""))
        title = str(deterministic.get("major", ""))
        parent_cip = _derive_parent_cip(cip4, programs)
        # Some YAML entries store a 4-digit family code (e.g. "Special
        # Education" → "13.10"). The frontend and downstream career
        # queries want a 6-digit leaf when the school reports one, so
        # promote using the school's catalog — same semantics as the
        # Gemma path at L407 below.
        school_cips = _get_school_cips(unitid)
        matched_cip = _promote_to_leaf_cip(cip4, parent_cip, school_cips)
        careers = _get_career_titles_for_cip(matched_cip)
        audit = _audit_intent_mapping(major_text, matched_cip, title, careers)
        audit_flag = None
        audit_message = None
        if audit:
            tone = str(audit.get("tone", "clean"))
            message = str(audit.get("message", ""))
            if not bool(audit.get("valid", True)):
                audit_flag = "hard_reject"
                audit_message = message
            elif tone == "playful_warning":
                audit_flag = "playful_warning"
                audit_message = message
        return IntentResult(
            matched_cip=matched_cip,
            matched_title=title,
            confidence="high",
            reasoning="Deterministic match from major_to_cip.yaml.",
            careers_preview=careers,
            audit_flag=audit_flag,
            audit_message=audit_message,
            needs_clarification=False,
            alternatives=None,
            parent_cip=parent_cip,
        )

    school_cips = _get_school_cips(unitid)
    family_prefixes = list({c["cipcode"][:2] for c in school_cips})
    crosswalk_cips = _get_crosswalk_cips_for_families(family_prefixes)

    parsed, latency, stats = _call_gemma_intent(
        major_text, school_name, school_cips, crosswalk_cips,
    )

    if parsed is None:
        raise ValueError(
            stats.get("parse_error", f"Gemma could not resolve '{major_text}'")
        )

    matched_cip = str(parsed.get("matched_cip", "")).strip()
    parent_cip = str(parsed.get("parent_cip", "")).strip()
    # Gemma occasionally hands back a 4-digit umbrella (e.g. "13.10") in
    # matched_cip instead of a 6-digit leaf (e.g. "13.1001"). Salvage
    # before the strict regex gate below — the alternative is a spurious
    # "Gemma couldn't match that" fallback for legitimate picks.
    matched_cip = _promote_to_leaf_cip(matched_cip, parent_cip, school_cips)
    if not _CIP_PATTERN.match(matched_cip):
        # Gemma is the source of `matched_cip`; we regex-filter every
        # alternative but must also guard the primary or a malformed CIP
        # gets persisted to `_intent_cache` via /intent/confirm and leaks
        # into downstream MCP queries. Fall through to phase="fallback".
        raise ValueError(
            f"Gemma returned a malformed primary CIP "
            f"({matched_cip!r}) for {major_text!r}"
        )
    matched_title = str(parsed.get("matched_title", ""))
    confidence = str(parsed.get("confidence", "unknown"))
    reasoning = str(parsed.get("reasoning", ""))
    alternatives = _sanitize_alternatives(parsed.get("alternatives"), matched_cip)

    career_titles = _get_career_titles_for_cip(matched_cip)

    audit = _audit_intent_mapping(
        major_text, matched_cip, matched_title, career_titles,
    )
    audit_flag = None
    audit_message = None
    if audit:
        tone = str(audit.get("tone", "clean"))
        message = str(audit.get("message", ""))
        valid = bool(audit.get("valid", True))
        if not valid:
            audit_flag = "hard_reject"
            audit_message = message
        elif tone == "playful_warning":
            audit_flag = "playful_warning"
            audit_message = message

    # Routing contract: low -> clarify picker on the frontend; medium and high
    # both render the match card (the frontend uses `confidence !== "high"` to
    # light up the caution styling + alternatives list — see MajorInput.tsx
    # `isUncertain`). Changing this predicate requires a paired frontend edit.
    return IntentResult(
        matched_cip=matched_cip,
        matched_title=matched_title,
        confidence=confidence,
        reasoning=reasoning,
        careers_preview=career_titles,
        audit_flag=audit_flag,
        audit_message=audit_message,
        needs_clarification=confidence == "low",
        alternatives=alternatives,
        parent_cip=parent_cip,
    )


def confirm_intent(
    matched_cip: str,
    matched_title: str,
    major_text: str,
    unitid: int,
    parent_cip: str = "",
) -> None:
    """Persist a confirmed match in the intent cache.

    ``parent_cip`` must be forwarded from the IntentResult the student
    confirmed. The cache-hit branch at ``resolve_intent`` L451 returns
    ``parent_cip=""`` when the key is missing — without this field,
    every second lookup for the same (major_text, unitid) silently
    drops the substitution signal the frontend needs. Default ``""`` for
    back-compat with pre-fix clients that don't send it.
    """
    normalized = major_text.lower().strip()
    cache_key = (normalized, unitid)
    _intent_cache[cache_key] = {
        "cip": matched_cip,
        "title": matched_title,
        "confidence": "high",
        "confirmed_by_student": True,
        "parent_cip": parent_cip,
    }
