"""Set Your Course — unified-screen chip dispatch service.

Owns:
- The chip-routing system prompt (``_CHIP_ROUTING_SYSTEM_PROMPT``).
- A prose-first streaming intent prompt (``_STREAM_INTENT_SYSTEM_PROMPT``).
- ``stream_initial_resolution`` — streamed major-resolution generator.
- ``handle_chip_dispatch`` — single-turn chip handler with an MCP
  pre-fetch for grounding.
- ``record_commit`` — correction-log writer wrapper invoked on commit.

See docs/specs/feature-set-your-course.md §4.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator, Mapping, Sequence
from typing import Any

from app.models.api import (
    ChipBucket,
    ChipRequest,
    ChipResponse,
    CommitRequest,
    CtaLink,
    GradCredentialNoticePayload,
)
from app.models.career import IntentResult
from app.services import (
    community_suggestions,
    correction_log,
    gemma_client,
    intent,
    mcp_client,
)
from app.services.correction_log import CorrectionLogRecord
from app.services.locale import AppLocale, gemma_language_instruction, normalize_locale

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data-source context interpolated into the chip prompt.
# ---------------------------------------------------------------------------

# Acronym-spell-out rule per §2 Decision #14: first reference full name
# with parenthetical acronym. When Gemma cites a source in prose, it uses
# this registry to stay consistent with the rest of the product.
_SOURCES_PROMPT_CONTEXT = """\
Canonical data sources (use full name on first reference, acronym after):
- Bureau of Labor Statistics (BLS) — occupation wage, outlook, task
  profiles from the Occupational Outlook Handbook.
- College Scorecard — school-level program outcomes, earnings, debt;
  provided by the U.S. Department of Education.
- Integrated Postsecondary Education Data System (IPEDS) — how schools
  officially report their programs. Used to explain reporting quirks.
- Occupational Information Network (O*NET) — task-level and work-
  context profiles of occupations.
- Bureau of Economic Analysis (BEA) — regional cost-of-living parities
  used for purchasing-power comparisons across states.
"""


# ---------------------------------------------------------------------------
# Chip-routing system prompt.
# ---------------------------------------------------------------------------
#
# DUPLICATE: this prompt body is the sole Gemma chip-routing prompt for
# set-your-course. If it is ever copied elsewhere, add a DUPLICATE
# banner to the other copy pointing here — mirrors the discipline in
# backend/app/services/intent.py.

_CHIP_ROUTING_SYSTEM_PROMPT = """\
You are FutureProof's career-planning assistant, triggered when a student
tapped "Not what I expected" on their Set Your Course screen. Your job is
to classify why the student's expectation missed the data, run the right
debug trace, and either confirm the current resolution or update it.

# Student's clarifier
The student filled in a scoped prompt ("What were you hoping to see?")
with: "{clarifier}"

# Current state
- School: {school_name} (unitid {unitid})
- Initial major input: "{initial_major_text}"
- Current resolution: {current_cip4} {current_title} (confidence: {current_confidence})
- Current confirmed sub-focus (if any): {current_confirmed_focus}
- Initial resolution: {initial_cip4} {initial_title}
- Career tiles currently shown: {current_tile_titles}

# Debug-bucket taxonomy — classify the clarifier into ONE of these
1. crosswalk_mismatch — the school reports the program under a broader
   or sibling code than the student expects. Example: student at IU
   types "marketing" and is seeing Business/Commerce jobs because IU
   reports Marketing inside its Business program. Action: look up the
   narrower program and surface those jobs, flag the reporting quirk.
2. semantic_drift — the student's word means something different than
   the program it maps to. Example: student says "design" meaning UX
   design; the resolved program is graphic design. Action: re-resolve
   using the clarifier as additional intent signal.
3. school_gap — this school genuinely does not offer the program the
   student wanted. Example: student at a liberal-arts college types
   "nursing" but the school has no nursing program. Action: say so
   plainly; the response will carry a cta_link to the School Discovery
   stub.
4. data_suppression — the program exists but the published detail was
   suppressed for privacy (small sample size). Example: a small
   program's earnings are withheld by the Integrated Postsecondary
   Education Data System (IPEDS). Action: explain the suppression rule;
   don't pretend the data is there.
5. tier_placement — the target job exists for this program but is in a
   less-common or stretch tier the student hasn't revealed yet.
   Example: student sees only Common tier and expected an ambitious
   option. Action: point them to the tier toggle.
6. intent_divergence — the student's typed major and their clarified
   career goal don't align. Example: student typed "Marketing" but
   clarifier says "I want to be a doctor." This is NOT "student picked
   the wrong major." Action: honestly surface the gap and OFFER
   alternative majors that lead to the clarified career. Never as
   corrections — as options.
7. peer_variance — other schools report this program differently and
   the student is comparing. Example: "my friend at another school
   saw Marketing tiles on day one." Action: query 2–3 peer schools
   and show variance.
8. no_issue_found — the clarifier doesn't match any debug bucket
   cleanly. Example: "I just don't like these jobs." Action: acknowledge
   plainly, do NOT force a bucket, do NOT update the resolution.
9. requires_graduate_credential — the career the student named in the
   clarifier requires graduate or professional school as its entry
   credential. Example: student typed "Marketing" and clarified "I want
   to be a physical therapist." Becoming a physical therapist requires
   a Doctor of Physical Therapy (DPT). Counter-example: student typed
   "Marketing" and clarified "I want to be a software developer" — that's
   intent_divergence, not requires_graduate_credential, because software
   development has an undergrad path.

   IMPORTANT: Also classify as this bucket when the student's currently-
   resolved typed major IS a known feeder for that credential (e.g.,
   "Biology major says they want to be a doctor" — the student is on a
   sensible track but needs the grad-school heads-up rather than
   alternative-major suggestions).

   Action: call `get_occupation_education_requirements` for the SOC the
   clarifier names. If `requires_grad_school` is true, classify as this
   bucket. If requires_grad_school is false (education_code 3-8), classify
   as intent_divergence instead.

   Do NOT name specific undergraduate majors in your response — the
   frontend renders a separate tile with feeder-major cards. Keep your
   prose to 2-3 sentences naming the credential and the reframe.

# Rules
- Ground every claim in the data. If you don't have data for a school
  or program, say so plainly. Do not invent careers, salaries, or
  schools.
- Voice: cool, confident, data-honest. No hype. No "unlock your future."
  Don't tell students what to do; show them what the data says.
- Narrate at the 4-digit program level unless the student has confirmed
  a sub-specialty. Any sub-specialty label narrower than the program
  (e.g. "Deaf Education," "UX Design," "Forensic Accounting") is
  legitimate ONLY IF the student named it first in their clarifier AND
  a tool call verified it is a real sub-area of the resolved program.
  Do not invent or auto-select a sub-specialty from your training data.
- NEVER use internal taxonomy terms in student-facing prose. Forbidden:
  "CIP," "SOC," "crosswalk," or any numeric code like "52.02" or
  "11-2021." Translate:
  - CIP → "program" or the plain-English program title
  - SOC → "career" or the plain-English job title
  - crosswalk → "the data" or rephrase around it
  - Numeric codes → drop them
- CITE SOURCES with the acronym-spell-out rule. First reference in your
  response uses full name + parenthetical acronym (e.g. "Bureau of
  Labor Statistics (BLS)"); subsequent references may use the acronym
  alone. Applies to sources (BLS, IPEDS, O*NET, BEA, College
  Scorecard) — NOT to internal taxonomies (CIP, SOC stay forbidden).
- You have access to these tools:
  get_career_paths(unitid, cipcode) — returns the matched career list
  for a school + program. Call this when:
  * The clarifier mentions a sub-specialty you can't verify is offered
    at this school (e.g., "deaf education" inside a Special Ed CIP).
  * The clarifier suggests a different program than current_resolution
    and you need to check if the school offers it.
  * You need to ground a feasibility judgment in actual data.
  get_occupation_education_requirements(soc_code) — returns education
  requirements for a career. Call this when the clarifier names a specific
  career to check if it requires graduate school.
  Do NOT call a tool when:
  * The decision is clear from the clarifier alone (e.g., "I want
    something completely different" — that's a change_major case).
  * You've already called it once this turn and got a useful result.
  After your tool call (if any) returns, emit your final structured
  chip response per the format spec below.
- If you change the resolution, emit the structured tail. If not, omit.
- Keep the prose to 2–4 sentences — the clarifier is a moment, not a
  lecture.

# Sources registry
{sources_for_prompt_context}

# Your response format
Reply with 2–4 sentences of student-facing reasoning (plain English,
no CIP/SOC/crosswalk/numeric-code terms). Use the student's own wording
for any sub-specialty they named in their clarifier, but only after you
have tool-verified it is a real sub-area of the resolved program.

If you're changing the resolution, append (on its own lines):
  ---UPDATED_RESOLUTION---
  {{"matched_cip": "XX.XXXX", "matched_title": "...",
    "confidence": "high|medium|low", "reasoning": "..."}}

The matched_cip you emit MUST be a real CIP code that exists in the
pre-fetched data block above. Do NOT invent codes that look plausible
(e.g. "52.0601" is NOT a real Marketing code — Marketing is 52.1401;
52.06 is not a valid CIP family). If none of the codes in the pre-
fetched data fit, leave the resolution unchanged and explain in prose
why — never fabricate.

Always append the classification tail (even if no resolution change):
  ---BUCKET---
  {{"bucket": "<one of: crosswalk_mismatch, semantic_drift, school_gap, \
data_suppression, tier_placement, intent_divergence, peer_variance, \
no_issue_found, requires_graduate_credential>"}}

If the student named a sub-specialty in their clarifier AND you verified
it via tool call as a legitimate sub-area of the resolved program, also
append:
  ---CONFIRMED_FOCUS---
  {{"confirmed_focus": "<student's own words for the sub-specialty>"}}
Omit ---CONFIRMED_FOCUS--- entirely if (a) the student did not name a
sub-specialty, (b) your verification failed, or (c) the clarifier
routed to semantic_drift or intent_divergence.
"""


# ---------------------------------------------------------------------------
# Prose-first streaming intent prompt.
# ---------------------------------------------------------------------------
#
# Unlike the existing _INTENT_SYSTEM_PROMPT which returns a single JSON
# object, this one streams natural-language prose first, then delimits a
# machine-readable JSON tail with ---INTENT_JSON---. The prose is what the
# student actually watches arrive; the tail is parsed server-side to
# build the IntentResult.

_STREAM_INTENT_SYSTEM_PROMPT = """\
You map a student's free-text major to a program (CIP code). Your
response has two parts separated by a delimiter.

# Part 1: Prose (streamed to the student)
Two sentences. First sentence names the program the student seems to
mean. Second sentence explains why that reading fits their wording.
Direct, confident, no hedging. Never use internal taxonomy terms in the
prose — no "CIP," "SOC," "crosswalk," or numeric codes. Use the plain-
English program title (e.g. "Marketing" or "Biology") not the code.

# Part 2: JSON tail (parsed by the backend)
After the two sentences, emit EXACTLY this delimiter on its own line:
---INTENT_JSON---
Then on the next line emit a single JSON object and nothing after it:
{{"matched_cip": "XX.XXXX", "matched_title": "Program Title", \
"confidence": "high|medium|low", \
"parent_cip": "XX.XX (4-digit family code; may equal matched_cip[:5] \
when matched_cip is already a leaf)", \
"alternatives": [{{"cip": "XX.XXXX", "title": "Second Match", \
"why": "Also matches because...", "parent_cip": "XX.XX"}}], \
"remaining_count": 0, \
"narrowing_hint": "", \
"intent_keywords": []}}

Rules for the JSON tail:
- "matched_cip" MUST be a 6-digit leaf in XX.XXXX format (e.g. 13.1001,
  51.2308, 52.1401). Do NOT invent codes. The code MUST appear in one
  of the two candidate lists below. If you can't find a clean match in
  either list, set confidence to "low" and pick the nearest crosswalk
  entry you can defend — never fabricate a number.
- **Prefer the specific program the student named over a broader
  school-reported one.** When the student types a specific term like
  "marketing," "accounting," "physical therapy," or "deaf education,"
  you MUST pick the specific leaf from the crosswalk list — even if
  the school only reports a broader parent like "Business/Commerce"
  or "Health Professions." Set "parent_cip" to the school's broader
  reported 4-digit code in the same family so the backend can blend
  the school's earnings with the specific program's careers at lookup
  time. Example for "marketing" at a school that only reports 52.01:
  matched_cip="52.1401" Marketing, parent_cip="52.01" Business/Commerce.
- Only fall back to the school's broad-reported code as matched_cip
  when the student's input is itself broad (e.g. "business,"
  "science," "engineering"). In that case set parent_cip equal to
  matched_cip[:5].
- If the student's input matches multiple programs at this school, return
  up to 3 ranked matches total (primary + up to 2 alternatives). Rank by
  semantic relevance to the student's input, NOT by outcome quality.
  Rules for alternatives:
  * Only include alternatives when 2+ distinct programs genuinely match.
  * Each alternative's "cip" MUST exist in one of the candidate CIP lists.
  * Do NOT include alternatives that are just degree-level variants of
    the primary (e.g., BS vs MS in the same field).
  * "remaining_count" = total matching CIPs minus however many you listed
    (primary + alternatives). 0 if you listed them all.
  * "narrowing_hint" = plain-English suggestion for how the student could
    narrow their search. Omit if remaining_count is 0.
  * If only 1 program matches, set "alternatives" to [], "remaining_count"
    to 0, and omit "narrowing_hint".
- Each alternative: {{"cip": "XX.XXXX", "title": "...", "why": "short phrase", \
"parent_cip": "XX.XX"}}.
- "intent_keywords" is a list of 0–6 lowercase tokens that capture the \
student's stated career direction, including sub-specialties INSIDE \
the matched program. Extract these whenever the student's text is more \
specific than the program title alone. Examples:
    * "pre-med" matched to Biology → ["pre-med", "doctor", "physician"]
    * "deaf ed" matched to "Special Education and Teaching, Specific \
Subject Areas" → ["deaf education", "special education", "teacher"] \
(the program IS the intent — emit them anyway)
    * "I want to design video games" matched to a CS or Game Design \
program → ["game design", "video games"]
    * Plain "marketing" matched to Marketing CIP → [] (no signal beyond \
the program name itself)
    * Plain "biology" matched to Biology CIP → [] (same)
  The rule: if the student named a role, target career, or sub-specialty, \
those tokens go in. If they only named the program at the same granularity \
as the matched CIP, leave it empty.

Context:
The student typed: "{student_input}"
School: {school_name}

Candidate CIPs — programs reported by this school (the school only
reports at these granularities; this is the "parent_cip" universe):
{school_cip_list}

Candidate CIPs — specific programs from the national crosswalk (this
is the "matched_cip" universe whenever the student names a specific
program not directly reported by the school):
{crosswalk_cip_list}

Both lists above are equally valid match candidates. Your matched_cip
MUST appear in one of them.
"""


# ---------------------------------------------------------------------------
# Streaming intent resolution.
# ---------------------------------------------------------------------------


_JSON_DELIM = "---INTENT_JSON---"
_CIP_PATTERN = re.compile(r"^\d{2}\.\d{4}$")
_NUMERIC_CODE_PARENTHETICAL = re.compile(r"\s*\(\s*\d{2}\.\d{2,4}\s*\)")


async def stream_initial_resolution(
    major_text: str,
    school_name: str,
    unitid: int,
    programs: Sequence[Mapping[str, Any]],
    locale: AppLocale = "en",
) -> AsyncIterator[dict[str, Any]]:
    """Stream the initial major-resolution.

    Yields event dicts of shape ``{"event": <name>, "data": <payload>}``.
    Event stream, in order:

    1. Zero or more ``{"event": "delta", "data": {"text": <str>}}`` with
       the prose chunks as they arrive. The ``---INTENT_JSON---``
       delimiter and everything after it are stripped before yielding.
    2. Exactly one ``{"event": "structured", "data": <IntentResult>}``
       once the JSON tail has been parsed and the final IntentResult
       built (with ``parent_cip`` derived from the programs list and any
       4-digit matched_cip promoted to a 6-digit leaf).
    3. Exactly one ``{"event": "suggestions", "data": list[Suggestion]}``
       with the community-suggestion lookup for the normalized input.
    4. Exactly one ``{"event": "done", "data": {}}``.

    If Gemma fails or returns an unparseable JSON tail, the generator
    still emits ``structured`` with a best-effort ``IntentResult`` (low
    confidence + plain reasoning) so the frontend has something to
    render rather than hanging.
    """
    input_normalized = community_suggestions.normalize_input(major_text)

    # Pre-flag short-circuit: if the student typed a pre-X pattern, skip
    # Gemma entirely and show a GradCredentialNotice immediately.
    from app.services import grad_credentials

    cred_id = grad_credentials.lookup_credential_by_pre_x_pattern(input_normalized)
    if cred_id is not None:
        result = _build_pre_flag_result(
            credential_id=cred_id,
            major_text=major_text,
            school_name=school_name,
            programs=programs,
            unitid=unitid,
        )
        feeder_title = result.matched_title or "a related science program"
        yield {
            "event": "delta",
            "data": {
                "text": _pre_flag_prose(cred_id, school_name, feeder_title),
            },
        }
        yield {"event": "structured", "data": result.model_dump()}

        # Emit grad-credential payload so the frontend can render the
        # GradCredentialNotice tile without a second round-trip.
        cred_entry = next(
            (c for c in grad_credentials._load_credentials()
             if c.get("credential_id") == cred_id),
            None,
        )
        if cred_entry is not None:
            feeders = grad_credentials.feeder_majors_at_school(
                unitid, cred_id
            )
            if feeders:
                payload = GradCredentialNoticePayload(
                    credential_id=cred_id,
                    credential_name_full=(
                        cred_entry["credential_name_full"]
                    ),
                    credential_acronym=(
                        cred_entry["credential_acronym"]
                    ),
                    target_career_title=major_text,
                    target_soc=None,
                    school_name=school_name,
                    feeders=feeders,
                    tone="info",
                )
                yield {
                    "event": "grad_credential_payload",
                    "data": payload.model_dump(),
                }

        suggestions = community_suggestions.get_suggestions(
            unitid=unitid, input_normalized=input_normalized
        )
        yield {"event": "suggestions", "data": list(suggestions)}
        yield {"event": "done", "data": {}}
        return

    school_cips = intent._get_school_cips(unitid)
    family_prefixes = list({c["cipcode"][:2] for c in school_cips if c.get("cipcode")})
    crosswalk_cips = intent._get_crosswalk_cips_for_families(family_prefixes)

    school_cip_list = "\n".join(
        f"- {c['cipcode']} {c['program_name']}" for c in school_cips
    ) or "(no programs reported)"
    crosswalk_cip_list = "\n".join(
        f"- {c['cipcode']} {c['cip_title']}"
        for c in intent._sample_crosswalk(
            crosswalk_cips, student_input=major_text,
        )
    ) or "(no crosswalk data)"

    locale = normalize_locale(locale)
    system = _STREAM_INTENT_SYSTEM_PROMPT.format(
        student_input=major_text,
        school_name=school_name,
        school_cip_list=school_cip_list,
        crosswalk_cip_list=crosswalk_cip_list,
    )
    system = f"{system}\n\n{gemma_language_instruction(locale)}"
    user = f'Match this student input to a program: "{major_text}"'

    extra = {
        "call_site": "set_your_course_resolve",
        "unitid": unitid,
        "school_name": school_name,
        "major_text": major_text,
        "input_normalized": input_normalized,
    }

    # Prose-vs-tail state machine. We emit delta events with prose only,
    # holding back the tail end of each chunk until we can confirm it's
    # not the start of the delimiter. Without the hold-back, a chunk
    # carrying "---INTENT_JSON" (without the trailing "---") would be
    # emitted as prose before the next chunk completes the delimiter.
    assembled: list[str] = []
    delim_seen = False
    emitted_len = 0
    holdback = len(_JSON_DELIM) - 1

    try:
        async for chunk in gemma_client.generate_stream_async(
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=1500,
            temperature=0.0,
            seed=intent._derive_intent_seed(major_text),
            extra=extra,
        ):
            assembled.append(chunk)
            if delim_seen:
                continue
            combined = "".join(assembled)
            delim_idx = combined.find(_JSON_DELIM)
            if delim_idx != -1:
                # Full delimiter present. Flush prose up to it and stop.
                if delim_idx > emitted_len:
                    yield {
                        "event": "delta",
                        "data": {"text": combined[emitted_len:delim_idx]},
                    }
                emitted_len = delim_idx
                delim_seen = True
            else:
                # No delimiter yet. Emit everything except the last
                # (len(delim) - 1) chars, which could be the start of a
                # delimiter completing in the next chunk.
                safe_end = max(emitted_len, len(combined) - holdback)
                if safe_end > emitted_len:
                    yield {
                        "event": "delta",
                        "data": {"text": combined[emitted_len:safe_end]},
                    }
                    emitted_len = safe_end
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("stream_initial_resolution gemma error: %s", exc)

    # Stream ended. If no delimiter ever arrived, flush any remaining
    # held-back prose so legitimate tail text doesn't get dropped.
    if not delim_seen:
        full = "".join(assembled)
        if len(full) > emitted_len:
            yield {
                "event": "delta",
                "data": {"text": full[emitted_len:]},
            }

    # Parse the tail.
    full = "".join(assembled)
    prose, tail = _split_at_delim(full)
    parsed_json = _safe_parse_tail(tail)

    intent_result = _build_intent_result_from_tail(
        major_text=major_text,
        prose=prose,
        parsed=parsed_json,
        school_cips=school_cips,
        programs=programs,
    )

    yield {"event": "structured", "data": intent_result.model_dump()}

    suggestions = community_suggestions.get_suggestions(
        unitid=unitid, input_normalized=input_normalized
    )
    yield {"event": "suggestions", "data": list(suggestions)}

    yield {"event": "done", "data": {}}


def _split_at_delim(text: str) -> tuple[str, str]:
    """Split ``text`` on the first occurrence of the JSON delimiter."""
    idx = text.find(_JSON_DELIM)
    if idx == -1:
        return text, ""
    return text[:idx].rstrip(), text[idx + len(_JSON_DELIM) :].strip()


def _safe_parse_tail(tail: str) -> dict[str, Any] | None:
    """Best-effort parse of the JSON body that follows the delimiter."""
    if not tail:
        return None
    cleaned = tail.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace <= first_brace:
        return None
    try:
        parsed = json.loads(cleaned[first_brace : last_brace + 1])
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _parse_intent_keywords(raw: Any) -> list[str]:
    """Safely extract intent_keywords from a parsed JSON value."""
    if not isinstance(raw, list):
        return []
    return [str(k).lower().strip() for k in raw if isinstance(k, str) and k.strip()]


def _merge_confirmed_focus_into_keywords(ir: IntentResult) -> IntentResult:
    """Append lowercased confirmed_focus to intent_keywords if not already present."""
    if not ir.confirmed_focus:
        return ir
    token = ir.confirmed_focus.lower().strip()
    if not token or token in ir.intent_keywords:
        return ir
    return ir.model_copy(
        update={"intent_keywords": [*ir.intent_keywords, token]}
    )


_FALLBACK_JSON_SYSTEM = """\
Pick the best CIP code for the student's input from the list below.
If multiple programs genuinely match, return up to 3 ranked by relevance.
Reply with ONLY a JSON object, nothing else. No explanation, no markdown.

{{"matched_cip": "XX.XXXX", "matched_title": "Program Title", \
"confidence": "high", "parent_cip": "XX.XX", \
"alternatives": [{{"cip": "XX.XXXX", "title": "Second Match", \
"why": "reason", "parent_cip": "XX.XX"}}], \
"remaining_count": 0, "narrowing_hint": "", \
"intent_keywords": ["keyword1"]}}

Programs at this school:
{school_cip_list}

Crosswalk codes:
{crosswalk_cip_list}
"""


def _fallback_resolve(
    major_text: str,
    school_cips: list[dict[str, str]],
    programs: Sequence[Mapping[str, Any]],
) -> IntentResult | None:
    """Simple JSON-only Gemma call as fallback.

    Called when the streaming prompt didn't produce a parseable JSON
    tail (common with smaller models like e4b that can't follow the
    two-part prose+delimiter+JSON format).
    """
    family_prefixes = list({
        c.get("cipcode", "")[:2] for c in school_cips if c.get("cipcode")
    })
    crosswalk_cips = intent._get_crosswalk_cips_for_families(family_prefixes)
    sampled = intent._sample_crosswalk(crosswalk_cips, student_input=major_text)

    school_list = "\n".join(
        f"- {c['cipcode']} {c['program_name']}" for c in school_cips
    ) or "(none)"
    xwalk_list = "\n".join(
        f"- {c['cipcode']} {c['cip_title']}" for c in sampled
    ) or "(none)"

    system = _FALLBACK_JSON_SYSTEM.format(
        school_cip_list=school_list, crosswalk_cip_list=xwalk_list,
    )
    try:
        raw = gemma_client.generate(
            system=system,
            user=f'Student typed: "{major_text}"',
            max_tokens=200,
            temperature=0.0,
        )
        parsed = _safe_parse_tail(raw)
        if not parsed or not parsed.get("matched_cip"):
            return None

        matched_cip = str(parsed["matched_cip"]).strip()
        matched_title = str(parsed.get("matched_title", "")).strip()
        confidence = str(parsed.get("confidence", "medium")).strip()
        raw_parent = str(parsed.get("parent_cip", "")).strip()
        matched_cip = intent._promote_to_leaf_cip(
            matched_cip, raw_parent, school_cips
        )
        cip4 = matched_cip[:5] if len(matched_cip) >= 5 else ""
        parent_cip = next(
            (c["cipcode"][:5] for c in school_cips
             if c.get("cipcode", "")[:2] == cip4[:2]),
            cip4,
        ) if cip4 else ""
        alternatives = intent._sanitize_alternatives(
            parsed.get("alternatives"), matched_cip, max_alts=2
        )
        remaining_count = max(0, min(50, int(parsed.get("remaining_count", 0) or 0)))
        narrowing_hint = str(parsed.get("narrowing_hint", "") or "").strip()[:120]
        return IntentResult(
            matched_cip=matched_cip,
            matched_title=_NUMERIC_CODE_PARENTHETICAL.sub("", matched_title),
            confidence=confidence,
            reasoning=f"Matched to {matched_title}.",
            careers_preview=[],
            needs_clarification=confidence == "low",
            alternatives=alternatives,
            parent_cip=parent_cip,
            student_major_text=major_text,
            intent_keywords=_parse_intent_keywords(
                parsed.get("intent_keywords")
            ),
            remaining_count=remaining_count,
            narrowing_hint=narrowing_hint,
        )
    except Exception as exc:
        logger.warning("_fallback_resolve failed: %s", exc)
    return None


def _build_intent_result_from_tail(
    *,
    major_text: str,
    prose: str,
    parsed: dict[str, Any] | None,
    school_cips: list[dict[str, str]],
    programs: Sequence[Mapping[str, Any]],
) -> IntentResult:
    """Synthesize an IntentResult from the streamed tail + prose.

    On a missing/unparseable tail we fall back to a low-confidence
    placeholder so the frontend always has something to render.
    """
    if parsed is None:
        fallback = _fallback_resolve(major_text, school_cips, programs)
        if fallback is not None:
            return fallback
        return IntentResult(
            matched_cip="",
            matched_title="",
            confidence="low",
            reasoning=prose.strip()
            or "Could not resolve a program from that input.",
            careers_preview=[],
            needs_clarification=True,
            alternatives=None,
            parent_cip="",
            student_major_text=major_text,
        )

    matched_cip = str(parsed.get("matched_cip", "")).strip()
    matched_title = str(parsed.get("matched_title", "")).strip()
    confidence = str(parsed.get("confidence", "low")).strip() or "low"
    raw_parent_cip = str(parsed.get("parent_cip", "")).strip()

    # Promote 4-digit matches to 6-digit leaves when we can.
    matched_cip = intent._promote_to_leaf_cip(
        matched_cip, raw_parent_cip, school_cips
    )

    # Validate the returned code against the real crosswalk + school
    # universe. Gemma occasionally hallucinates well-formed but fake CIPs
    # (e.g. "52.0601" for Marketing when the real code is 52.1401). We
    # only trust a matched_cip that actually exists in either the school
    # catalog or the crosswalk for this request.
    crosswalk_cips = intent._get_crosswalk_cips_for_families(
        list({c.get("cipcode", "")[:2] for c in school_cips if c.get("cipcode")})
    )
    valid_6digit: set[str] = {
        c["cipcode"] for c in crosswalk_cips if c.get("cipcode")
    }
    # Retry promotion using crosswalk leaves when school only reports
    # 4-digit families (e.g. Stanford reports "45.06" Economics but Gemma
    # also returns "45.06" — promote to "45.0601" via the crosswalk).
    if (
        not _CIP_PATTERN.match(matched_cip)
        and len(matched_cip) == 5
        and matched_cip[2] == "."
    ):
        crosswalk_leaves = sorted(
            c for c in valid_6digit if c.startswith(matched_cip)
        )
        if crosswalk_leaves:
            matched_cip = crosswalk_leaves[0]

    valid_4digit: set[str] = {
        c.get("cipcode", "")[:5] for c in school_cips if c.get("cipcode")
    }
    # Only reject when we successfully loaded a non-empty crosswalk to
    # validate against. An empty crosswalk usually means the DB call
    # failed or the school has no catalog — falling back to "trust
    # Gemma" is safer than silently degrading every resolution.
    not_in_school_universe = (
        bool(matched_cip)
        and _CIP_PATTERN.match(matched_cip) is not None
        and bool(valid_6digit)
        and matched_cip not in valid_6digit
        and matched_cip[:5] not in valid_4digit
    )
    program_not_at_school = False
    if not_in_school_universe:
        national_cips = intent._get_crosswalk_cips_for_families(
            [matched_cip[:2]]
        )
        national_6digit = {c["cipcode"] for c in national_cips if c.get("cipcode")}
        if matched_cip in national_6digit:
            logger.info(
                "set_your_course: matched_cip=%s (%s) for %r is a real "
                "program but not offered at this school.",
                matched_cip,
                matched_title,
                major_text,
            )
            program_not_at_school = True
            confidence = "low"
            matched_cip = ""
            matched_title = matched_title or "Program not offered here"
        else:
            logger.warning(
                "set_your_course: Gemma returned matched_cip=%s for %r at "
                "unitid-unknown, not present in crosswalk or school catalog; "
                "degrading to low confidence.",
                matched_cip,
                major_text,
            )
            confidence = "low"
            matched_cip = ""
            matched_title = matched_title or "Couldn't confirm a program"

    # Always derive parent_cip from the school's programs so the frontend
    # substitution signal stays correct regardless of what Gemma emitted.
    cip4_for_parent = matched_cip[:5] if len(matched_cip) >= 5 else ""
    parent_cip = (
        intent._derive_parent_cip(cip4_for_parent, programs)
        if cip4_for_parent
        else ""
    )

    intent_keywords = _parse_intent_keywords(parsed.get("intent_keywords") or [])

    if not _CIP_PATTERN.match(matched_cip):
        return IntentResult(
            matched_cip="",
            matched_title=matched_title,
            confidence="low",
            reasoning=prose.strip() or "No program code resolved.",
            careers_preview=[],
            needs_clarification=True,
            alternatives=None,
            parent_cip="",
            student_major_text=major_text,
            intent_keywords=intent_keywords,
            program_not_at_school=program_not_at_school,
        )

    careers_preview = intent._get_career_titles_for_cip(matched_cip)
    alternatives = intent._sanitize_alternatives(
        parsed.get("alternatives"), matched_cip, max_alts=2
    )

    reasoning = prose.strip() or str(parsed.get("reasoning", "")).strip()

    remaining_count = int(parsed.get("remaining_count", 0) or 0)
    narrowing_hint = str(parsed.get("narrowing_hint", "") or "").strip()

    result = IntentResult(
        matched_cip=matched_cip,
        matched_title=matched_title,
        confidence=confidence,
        reasoning=reasoning,
        careers_preview=careers_preview,
        audit_flag=None,
        audit_message=None,
        needs_clarification=confidence == "low",
        alternatives=alternatives,
        parent_cip=parent_cip,
        confirmed_focus=None,
        student_major_text=major_text,
        intent_keywords=intent_keywords,
        remaining_count=remaining_count,
        narrowing_hint=narrowing_hint,
    )
    return _merge_confirmed_focus_into_keywords(result)


# ---------------------------------------------------------------------------
# Chip dispatch.
# ---------------------------------------------------------------------------


_TRANSPORT_FAILURE_MESSAGE = (
    "I'm having trouble reaching the model. Try again in a moment."
)


async def handle_chip_dispatch(request: ChipRequest) -> ChipResponse:
    """One stateless chip tap.

    For ``show_less_common`` and ``change_major`` the backend does
    nothing — the frontend handles these — and we return an empty
    response (no Gemma call, no log). The endpoint exists for symmetry.

    For ``not_expected`` we run the chip-routing prompt through a real
    Gemma tool-calling loop against the MCP server.
    """
    if request.chip_id in ("show_less_common", "change_major"):
        return ChipResponse(
            debug_trace="",
            updated_resolution=None,
            bucket=None,
            confirmed_focus=None,
        )

    # not_expected path — real Gemma tool-calling loop.
    current = request.current_resolution
    initial = request.initial_resolution
    current_cip4 = current.matched_cip[:5] if len(current.matched_cip) >= 5 else ""
    initial_cip4 = initial.matched_cip[:5] if len(initial.matched_cip) >= 5 else ""

    tile_titles = ", ".join(current.careers_preview[:6]) or "(none)"

    chip_locale = normalize_locale(request.locale)
    system = _CHIP_ROUTING_SYSTEM_PROMPT.format(
        clarifier=(request.clarifier or "(empty)"),
        school_name=request.school_name,
        unitid=request.unitid,
        initial_major_text=initial.matched_title or "(unknown)",
        current_cip4=current_cip4 or "(unknown)",
        current_title=current.matched_title or "(unknown)",
        current_confidence=current.confidence,
        current_confirmed_focus=current.confirmed_focus or "(none)",
        initial_cip4=initial_cip4 or "(unknown)",
        initial_title=initial.matched_title or "(unknown)",
        current_tile_titles=tile_titles,
        sources_for_prompt_context=_SOURCES_PROMPT_CONTEXT,
    )
    system = f"{system}\n\n{gemma_language_instruction(chip_locale)}"

    user_msg = (
        f'Student tapped "not expected" with clarifier: '
        f'"{request.clarifier or ""}".\n\n'
        f"Classify, reason in 2-4 sentences, and emit the structured tails."
    )

    extra = {
        "call_site": "chip_dispatch_tool_call",
        "chip_id": request.chip_id,
        "unitid": request.unitid,
        "school_name": request.school_name,
        "current_cip": current.matched_cip,
        "initial_cip": initial.matched_cip,
        "clarifier_len": len(request.clarifier or ""),
    }

    tool_schema = mcp_client.get_tool_openai_schema("get_career_paths")
    edu_tool_schema = mcp_client.get_tool_openai_schema(
        "get_occupation_education_requirements"
    )
    tools = [s for s in [tool_schema, edu_tool_schema] if s is not None]
    if not tools:
        logger.error("No tool schemas found in MCP server for chip dispatch")
        return ChipResponse(
            debug_trace=_TRANSPORT_FAILURE_MESSAGE,
            updated_resolution=None,
            bucket=None,
            confirmed_focus=None,
        )

    async def _dispatch(tool_name: str, tool_args: dict[str, Any]) -> dict[str, Any]:
        # Inject student_cip for substitution semantics when Gemma
        # calls get_career_paths — same as the old pre-fetch.
        if tool_name == "get_career_paths" and current.matched_cip:
            tool_args = {**tool_args, "student_cip": current.matched_cip}
        return await mcp_client.call_async(tool_name, tool_args)

    raw, tool_call_log = await gemma_client.generate_with_tools_loop(
        system=system,
        user=user_msg,
        tools=tools,
        dispatch=_dispatch,
        max_turns=3,
        max_wall_time_s=30.0,
        temperature=0.2,
        max_tokens=600,
        extra=extra,
    )

    tool_call_made = len(tool_call_log) > 0 and any(
        tc.error is None for tc in tool_call_log
    )

    if not raw:
        return ChipResponse(
            debug_trace=_TRANSPORT_FAILURE_MESSAGE,
            updated_resolution=None,
            bucket=None,
            confirmed_focus=None,
        )

    return _parse_chip_response(
        raw=raw,
        request=request,
        tool_call_made=tool_call_made,
        tool_call_log=tool_call_log,
    )


_UPDATED_TAIL = "---UPDATED_RESOLUTION---"
_BUCKET_TAIL = "---BUCKET---"
_CONFIRMED_TAIL = "---CONFIRMED_FOCUS---"

# Gemma 4 occasionally emits OpenAI-style tool-call pseudo-xml when we
# ask it to "use a tool" but don't register one via the API. We pre-fetch
# tool results into the prompt instead, so any emitted tool-call tokens
# are vestigial and should never reach the student. Strip them from the
# prose before returning.
_TOOL_CALL_PATTERNS = (
    re.compile(r"<\|tool_call\|>.*?<\|?/?\s*tool_call\s*\|?>", re.DOTALL),
    re.compile(r"<\|tool_call\|>[^<]*", re.DOTALL),
    re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL),
    re.compile(r"<function_call>.*?</function_call>", re.DOTALL),
    re.compile(r"<\|tool_call\|>", re.DOTALL),
)


def _strip_tool_call_markup(text: str) -> str:
    cleaned = text
    for pat in _TOOL_CALL_PATTERNS:
        cleaned = pat.sub("", cleaned)
    # Collapse any triple-newlines the strip leaves behind.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _parse_chip_response(
    *,
    raw: str,
    request: ChipRequest,
    tool_call_made: bool,
    tool_call_log: Any = None,
) -> ChipResponse:
    """Parse the three structured tails and apply service-side invariants."""
    text = raw.strip()

    # Split by the three markers. Each returns (body, tail_json).
    prose_and_tails, updated_body = _cut_at(text, _UPDATED_TAIL)
    prose_and_tails, bucket_body = _cut_at(prose_and_tails, _BUCKET_TAIL)
    prose_and_tails, confirmed_body = _cut_at(prose_and_tails, _CONFIRMED_TAIL)
    debug_trace = _strip_tool_call_markup(prose_and_tails)

    bucket = _parse_bucket(bucket_body)
    updated_resolution = _parse_updated_resolution(
        updated_body, request=request
    )
    confirmed_focus = _parse_confirmed_focus(confirmed_body)

    # Invariants.
    if bucket in ("semantic_drift", "intent_divergence"):
        confirmed_focus = None
    if not tool_call_made:
        confirmed_focus = None
    if confirmed_focus:
        confirmed_focus = _NUMERIC_CODE_PARENTHETICAL.sub("", confirmed_focus).strip()
        confirmed_focus = confirmed_focus or None

    # Mirror confirmed_focus onto the updated_resolution when it exists,
    # then merge its tokens into intent_keywords for downstream tiering.
    if updated_resolution is not None and confirmed_focus:
        updated_resolution = updated_resolution.model_copy(
            update={"confirmed_focus": confirmed_focus}
        )
        updated_resolution = _merge_confirmed_focus_into_keywords(
            updated_resolution
        )

    # Build CTA link for requires_graduate_credential bucket.
    cta_link: CtaLink | None = None
    if bucket == "requires_graduate_credential":
        target_soc = _extract_soc_from_tool_log(tool_call_log)
        if target_soc:
            cta_link = _build_grad_credential_cta(
                target_soc=target_soc,
                target_career_title=request.clarifier or "",
                school_name=request.school_name,
                unitid=request.unitid,
                current_cip=request.current_resolution.matched_cip,
            )
            if cta_link is None:
                # YAML doesn't have feeders for this SOC — downgrade
                bucket = "intent_divergence"

    return ChipResponse(
        debug_trace=debug_trace,
        updated_resolution=updated_resolution,
        cta_link=cta_link,
        bucket=bucket,
        confirmed_focus=confirmed_focus,
    )


def _cut_at(text: str, marker: str) -> tuple[str, str]:
    """Split ``text`` on the first occurrence of ``marker``.

    Returns ``(before, after_body)`` where ``after_body`` is stripped of
    any following markers — so each tail body only contains its own JSON.
    """
    idx = text.find(marker)
    if idx == -1:
        return text, ""
    before = text[:idx]
    after = text[idx + len(marker) :]
    # Stop the body at the next known marker (if any).
    for other in (_UPDATED_TAIL, _BUCKET_TAIL, _CONFIRMED_TAIL):
        if other == marker:
            continue
        other_idx = after.find(other)
        if other_idx != -1:
            # Keep the other marker intact in `before` so the caller can
            # still find it on a subsequent cut.
            before = before + after[other_idx:]
            after = after[:other_idx]
    return before, after.strip()


def _parse_bucket(body: str) -> ChipBucket | None:
    parsed = _safe_parse_tail(body)
    if not parsed:
        return None
    raw_bucket = parsed.get("bucket")
    allowed: tuple[ChipBucket, ...] = (
        "crosswalk_mismatch",
        "semantic_drift",
        "school_gap",
        "data_suppression",
        "tier_placement",
        "intent_divergence",
        "peer_variance",
        "no_issue_found",
        "requires_graduate_credential",
    )
    if isinstance(raw_bucket, str) and raw_bucket in allowed:
        return raw_bucket
    return None


def _parse_updated_resolution(
    body: str, *, request: ChipRequest
) -> IntentResult | None:
    parsed = _safe_parse_tail(body)
    if not parsed:
        return None
    matched_cip = str(parsed.get("matched_cip", "")).strip()
    if not _CIP_PATTERN.match(matched_cip):
        return None

    matched_title = str(parsed.get("matched_title", "")).strip()
    confidence = str(parsed.get("confidence", "medium")).strip() or "medium"
    reasoning = str(parsed.get("reasoning", "")).strip()

    cip4 = matched_cip[:5]

    # Validate against the crosswalk universe — Gemma occasionally
    # hallucinates well-formed CIPs (e.g. "52.0601" for Marketing when
    # the real code is 52.1401). If the code doesn't exist in the
    # crosswalk for this school's families, reject the update so the
    # frontend doesn't route a fake code to /build/outcomes.
    school_cips = intent._get_school_cips(request.unitid)
    families = list({c.get("cipcode", "")[:2] for c in school_cips if c.get("cipcode")})
    crosswalk_cips = intent._get_crosswalk_cips_for_families(families)
    valid_6digit = {c["cipcode"] for c in crosswalk_cips if c.get("cipcode")}
    valid_4digit = {c.get("cipcode", "")[:5] for c in school_cips if c.get("cipcode")}
    if (
        valid_6digit
        and matched_cip not in valid_6digit
        and cip4 not in valid_4digit
    ):
        logger.warning(
            "set_your_course chip: rejected fabricated matched_cip=%s "
            "(title=%r) for unitid=%s; not in crosswalk or school catalog.",
            matched_cip,
            matched_title,
            request.unitid,
        )
        return None

    parent_cip = intent._derive_parent_cip(cip4, request.programs)
    careers = intent._get_career_titles_for_cip(matched_cip)

    current = request.current_resolution
    return IntentResult(
        matched_cip=matched_cip,
        matched_title=matched_title,
        confidence=confidence,
        reasoning=reasoning,
        careers_preview=careers,
        audit_flag=None,
        audit_message=None,
        needs_clarification=confidence == "low",
        alternatives=None,
        parent_cip=parent_cip,
        confirmed_focus=None,  # applied by caller when invariants allow
        student_major_text=current.student_major_text if current else "",
        intent_keywords=list(current.intent_keywords) if current else [],
    )


def _parse_confirmed_focus(body: str) -> str | None:
    parsed = _safe_parse_tail(body)
    if not parsed:
        return None
    raw = parsed.get("confirmed_focus")
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    return cleaned or None


# ---------------------------------------------------------------------------
# Grad-credential helpers.
# ---------------------------------------------------------------------------


def _extract_soc_from_tool_log(tool_call_log: Any) -> str | None:
    """Extract target_soc from the education requirements tool call log.

    Scans tool_call_log entries for a successful
    get_occupation_education_requirements call and reads the soc_code
    from its arguments.
    """
    if not tool_call_log:
        return None
    for tc in tool_call_log:
        tool_name = getattr(tc, "tool_name", None) or getattr(tc, "name", "")
        if tool_name == "get_occupation_education_requirements":
            args = (
                getattr(tc, "tool_args", None)
                or getattr(tc, "args", None)
                or getattr(tc, "arguments", {})
            )
            if isinstance(args, dict):
                soc = str(args.get("soc_code", ""))
                if soc and re.fullmatch(r"\d{2}-\d{4}", soc):
                    return soc
    return None


def _build_grad_credential_cta(
    *,
    target_soc: str,
    target_career_title: str,
    school_name: str,
    unitid: int,
    current_cip: str,
) -> CtaLink | None:
    """Build a CtaLink with GradCredentialNoticePayload for the chip response.

    Returns None when the YAML doesn't have feeders for this SOC or when
    fewer than 3 feeders are available (graceful downgrade).
    """
    from app.services import grad_credentials

    cred = grad_credentials.lookup_credential_for_soc(target_soc)
    if cred is None:
        return None

    feeders = grad_credentials.feeder_majors_at_school(unitid, cred["credential_id"])
    if len(feeders) < 3:
        return None

    # Determine tone per genai-architect Finding 5: "info" when student's
    # current major IS already a feeder for this credential, "caution"
    # otherwise.
    current_cip4 = current_cip[:5] if len(current_cip) >= 5 else ""
    feeder_cips = [f.get("cip4", "") for f in cred.get("feeder_cip4_codes", [])]
    is_already_feeder = current_cip4 in feeder_cips
    tone: str = "info" if is_already_feeder else "caution"

    payload = GradCredentialNoticePayload(
        credential_id=cred["credential_id"],
        credential_name_full=cred["credential_name_full"],
        credential_acronym=cred["credential_acronym"],
        target_career_title=target_career_title,
        target_soc=target_soc,
        school_name=school_name,
        feeders=feeders,
        tone=tone,
    )
    acronym = cred["credential_acronym"]
    return CtaLink(
        label=f"How students at {school_name} get to {acronym} school",
        href="#grad-credential-notice",
        kind="grad_credential_notice",
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Pre-flag short-circuit helpers.
# ---------------------------------------------------------------------------

_CREDENTIAL_PROSE_TEMPLATES: dict[str, str] = {
    "dpt": (
        "Pre-PT isn't an undergrad major itself — it's a track toward "
        "Doctor of Physical Therapy (DPT) school. "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
    "jd": (
        "Pre-Law isn't an undergrad major itself — it's a track toward "
        "law school (Juris Doctor). "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
    "md": (
        "Pre-Med isn't an undergrad major itself — it's a track toward "
        "medical school (Doctor of Medicine). "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
    "dds": (
        "Pre-Dental isn't an undergrad major itself — it's a track toward "
        "dental school (Doctor of Dental Surgery). "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
    "dvm": (
        "Pre-Vet isn't an undergrad major itself — it's a track toward "
        "veterinary school (Doctor of Veterinary Medicine). "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
    "pharmd": (
        "Pre-Pharmacy isn't an undergrad major itself — it's a track toward "
        "pharmacy school (Doctor of Pharmacy). "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
    "od": (
        "Pre-Optometry isn't an undergrad major itself — it's a track toward "
        "optometry school (Doctor of Optometry). "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
    "ms-pa": (
        "Pre-PA isn't an undergrad major itself — it's a track toward "
        "physician assistant school (Master of Science in PA Studies). "
        "The closest matching program at {school_name} is {feeder_title}."
    ),
}


def _pre_flag_prose(credential_id: str, school_name: str, feeder_title: str) -> str:
    """Return the pre-flag prose for a credential."""
    template = _CREDENTIAL_PROSE_TEMPLATES.get(
        credential_id,
        "This career requires a graduate credential. "
        "The closest matching program at {school_name} is {feeder_title}.",
    )
    return template.format(school_name=school_name, feeder_title=feeder_title)


def _build_pre_flag_result(
    *,
    credential_id: str,
    major_text: str,
    school_name: str,
    programs: Sequence[Mapping[str, Any]],
    unitid: int = 0,
) -> IntentResult:
    """Build an IntentResult for the pre-flag short-circuit path.

    Picks the broadest feeder offered at the school as the matched program.
    """
    from app.services import grad_credentials

    feeders = grad_credentials.feeder_majors_at_school(unitid, credential_id)

    # Find the best feeder that's offered at the school.
    school_cip4s = {
        str(p.get("cipcode", ""))[:5]
        for p in programs
        if p.get("cipcode")
    }

    best_feeder_cip = ""
    best_feeder_title = ""
    for feeder in feeders:
        if feeder.cip4 in school_cip4s:
            best_feeder_cip = feeder.cip4
            best_feeder_title = feeder.cip_title
            break

    # If no feeder is offered, just use the first feeder.
    if not best_feeder_cip and feeders:
        best_feeder_cip = feeders[0].cip4
        best_feeder_title = feeders[0].cip_title

    # Find a 6-digit CIP from the school's programs for the matched feeder.
    matched_cip_6 = ""
    matched_title = best_feeder_title
    for p in programs:
        cip = str(p.get("cipcode", ""))
        if cip[:5] == best_feeder_cip:
            matched_cip_6 = cip
            matched_title = str(p.get("program_name", best_feeder_title))
            break

    return IntentResult(
        matched_cip=matched_cip_6 or best_feeder_cip,
        matched_title=matched_title,
        confidence="low",
        reasoning=(
            f"Matched as a pre-professional track toward "
            f"{credential_id.upper()}."
        ),
        careers_preview=[],
        needs_clarification=False,
        alternatives=None,
        parent_cip=best_feeder_cip,
        student_major_text=major_text,
        intent_keywords=[major_text.lower().strip()],
        pre_flag_credential_id=credential_id,
    )


# ---------------------------------------------------------------------------
# Commit — write one correction record.
# ---------------------------------------------------------------------------


def record_commit(request: CommitRequest) -> bool:
    """Append a correction log record for this commit.

    Returns ``True`` when a record was written, ``False`` when skipped.
    No-op when the initial and current resolutions' CIPs are identical
    (no correction happened — nothing to learn from).
    """
    if request.initial_resolution.matched_cip == request.current_resolution.matched_cip:
        return False

    input_normalized = community_suggestions.normalize_input(request.major_text)
    config = gemma_client.current_config()

    initial_cip4 = (
        request.initial_resolution.matched_cip[:5]
        if len(request.initial_resolution.matched_cip) >= 5
        else request.initial_resolution.matched_cip
    )
    final_cip4 = (
        request.current_resolution.matched_cip[:5]
        if len(request.current_resolution.matched_cip) >= 5
        else request.current_resolution.matched_cip
    )

    record: CorrectionLogRecord = {
        "schema_version": "1.0",
        "kind": "correction",
        "timestamp": "",  # filled in by _ensure_timestamp
        "school_unitid": int(request.unitid),
        "school_name": request.school_name,
        "input_normalized": input_normalized,
        "initial_major_text": request.major_text,
        "initial_cip4": initial_cip4,
        "final_cip4": final_cip4,
        "clicked_soc": request.clicked_soc,
        "clicked_career_title": request.clicked_career_title,
        "feasibility_mode": request.feasibility_mode,
        "chips_tapped": list(request.chips_tapped),
        "clarifier": request.clarifier,
        "bucket": request.bucket,
        "backend": config.backend,
        "model": config.model,
    }
    correction_log.record_correction(record)
    return True
