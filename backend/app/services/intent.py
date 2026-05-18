"""Gemma intent resolution — maps free-text major input to a CIP code.

This service is part of the canonical web/API path. The original Rich CLI
proof of concept lives in ``archive/spikes/cli`` and may be stale.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections.abc import Mapping, Sequence
from typing import Any

from app.services import gemma_client, mcp_client

logger = logging.getLogger(__name__)

_CIP_PATTERN = re.compile(r"^\d{2}\.\d{4}$")
_CIP_FAMILY_PATTERN = re.compile(r"^\d{2}\.\d{2}$")
_CIP_FAMILY_PREFIX_PATTERN = re.compile(r"^\d{2}$")


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

# NOTE: the archived CLI spike has an older copy of this prompt under
# archive/spikes/cli/cli.py. The web/API path here is authoritative.
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

ILLUSTRATIVE example (do NOT echo these codes/titles — substitute the \
actual match):
{{"matched_cip": "11.0701", "matched_title": "Computer Science", \
"confidence": "high|medium|low", \
"reasoning": "One or two sentences naming the program and why it fits.", \
"parent_cip": "11.07 (4-digit family code, may equal matched_cip[:5] \
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
        logger.warning(
            "intent._get_school_cips query failed; returning empty",
            exc_info=True,
        )
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
    valid_prefixes: list[str] = []
    for p in family_prefixes:
        head = p[:2]
        if _CIP_FAMILY_PREFIX_PATTERN.fullmatch(head):
            valid_prefixes.append(head)
        else:
            logger.debug(
                "intent._get_crosswalk_cips_for_families: dropping malformed prefix %r",
                p,
            )
    if not valid_prefixes:
        return []
    server = mcp_client.get_server()
    conditions = " OR ".join(
        f"SUBSTR(cipcode, 1, 2) = '{p}'" for p in valid_prefixes
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
        logger.warning(
            "intent._get_crosswalk_cips_for_families query failed; returning empty",
            exc_info=True,
        )
        return []
    return [
        {"cipcode": str(r["cipcode"]), "cip_title": str(r.get("cip_title", ""))}
        for r in rows
        if r.get("cipcode")
    ]


def _sample_crosswalk(
    cips: list[dict[str, str]],
    max_total: int = 120,
    student_input: str = "",
) -> list[dict[str, str]]:
    """Sample evenly across CIP families with input-aware boosting.

    Entries whose ``cip_title`` contains a word from the student's input
    are guaranteed a slot before the even-distribution pass fills the
    rest.  This prevents the sampler from dropping the exact program the
    student typed (e.g. "Advertising" buried among 24 entries in the
    09.xx family at a large school).
    """
    if len(cips) <= max_total:
        return cips

    from collections import defaultdict

    tokens = {
        w for w in student_input.lower().split() if len(w) >= 3
    }

    boosted: list[dict[str, str]] = []
    rest: list[dict[str, str]] = []
    boosted_codes: set[str] = set()
    if tokens:
        for c in cips:
            title = (c.get("cip_title") or "").lower()
            if any(t in title for t in tokens):
                boosted.append(c)
                boosted_codes.add(c.get("cipcode", ""))
            else:
                rest.append(c)
    else:
        rest = cips

    remaining_budget = max_total - len(boosted)
    if remaining_budget <= 0:
        return boosted[:max_total]

    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for c in rest:
        family = c.get("cipcode", "")[:2]
        by_family[family].append(c)

    families = sorted(by_family)
    per_family = max(1, remaining_budget // max(len(families), 1))
    sampled: list[dict[str, str]] = []
    for fam in families:
        sampled.extend(by_family[fam][:per_family])

    if len(sampled) < remaining_budget:
        leftover = [c for c in rest if c not in sampled]
        sampled.extend(leftover[: remaining_budget - len(sampled)])

    result = boosted + sampled[:remaining_budget]
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
        logger.warning(
            "intent._get_career_titles_for_cip query failed; returning empty",
            exc_info=True,
        )
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
        for c in _sample_crosswalk(crosswalk_cips, student_input=student_input)
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
        extra={"call_site": "intent_resolve"},
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
    raw: Any, primary_cip: str, *, max_alts: int = 10
) -> list[dict[str, str]] | None:
    """Drop malformed/duplicate alternatives and clamp to *max_alts*.

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
        entry: dict[str, str] = {
            "cip": cip,
            "title": title,
            "why": why,
        }
        raw_parent = item.get("parent_cip")
        if isinstance(raw_parent, str) and raw_parent.strip():
            entry["parent_cip"] = raw_parent.strip()
        cleaned.append(entry)
        if len(cleaned) == max_alts:
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
        extra={"call_site": "intent_audit"},
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
