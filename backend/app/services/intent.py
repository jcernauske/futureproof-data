"""Gemma intent resolution — maps free-text major input to a CIP code.

Extracted from cli.py._prompt_major_gemma_intent(). The CLI's Rich
console output stays in the CLI; this module handles the data flow only.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.models.career import IntentResult
from app.services import gemma_client, mcp_client

logger = logging.getLogger(__name__)

_intent_cache: dict[tuple[str, int], dict[str, Any]] = {}

_INTENT_SYSTEM_PROMPT = """\
You are a college program advisor who understands how students, parents, \
counselors, and registrars all describe academic programs differently.

A student has told you what they want to study. Your job is to match their \
intent to the most appropriate CIP (Classification of Instructional Programs) \
code from the available options.

Consider how different people describe the same program:
- Students say: "pre-med", "CS", "business", "art"
- Parents say: "Physical Therapy", "Deaf Education", "Criminal Justice"
- Counselors say: "Special Ed", "STEM", "Allied Health"
- Registrars say: "CIP 51.2308 Physical Therapy/Therapist"

The student typed: "{student_input}"
School: {school_name}

Programs this school reports (these have earnings data):
{school_cip_list}

Additional specific programs in the same families (from the national \
crosswalk — these have career path data even if the school doesn't report \
them separately):
{crosswalk_cip_list}

Respond in JSON only, no preamble, no markdown:
{{"matched_cip": "XX.XXXX", "matched_title": "Program Title", \
"confidence": "high|medium|low", \
"reasoning": "2-3 sentences explaining why this is the best match", \
"parent_cip": "XX.XX (the school-reported CIP that covers this program, \
if different from matched_cip)", \
"alternatives": [{{"cip": "XX.XXXX", "title": "Title", \
"why": "one sentence"}}]}}\
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
        f"- {c['cipcode']} {c['cip_title']}" for c in crosswalk_cips[:60]
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
        max_tokens=500,
        temperature=0.1,
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
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        stats["parse_error"] = f"Could not parse JSON: {cleaned[:200]}"
        return None, latency, stats

    return parsed, latency, stats


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


def resolve_intent(
    major_text: str,
    school_name: str,
    unitid: int,
    programs: list[dict],
) -> IntentResult:
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

    matched_cip = str(parsed.get("matched_cip", ""))
    matched_title = str(parsed.get("matched_title", ""))
    confidence = str(parsed.get("confidence", "unknown"))
    reasoning = str(parsed.get("reasoning", ""))
    alternatives = parsed.get("alternatives")
    parent_cip = str(parsed.get("parent_cip", ""))

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
) -> None:
    normalized = major_text.lower().strip()
    cache_key = (normalized, unitid)
    _intent_cache[cache_key] = {
        "cip": matched_cip,
        "title": matched_title,
        "confidence": "high",
        "confirmed_by_student": True,
    }
