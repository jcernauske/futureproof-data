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
- **You have no tool access in this turn.** The career data for the
  student's current resolution has already been fetched and is pasted
  below in the "Pre-fetched career data" block. Reason directly from
  that block and the clarifier. Do NOT emit any tool-call markup —
  no "<|tool_call|>", no "<tool_call>", no function-call pseudo-xml.
  Anything like that will render as literal text to the student and
  break the answer. If the pre-fetched data doesn't cover the case,
  say so honestly in prose; do not pretend to call a tool.
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
no_issue_found>"}}

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
"alternatives": []}}

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
- "alternatives" is [] for high confidence; 2–4 items for medium;
  up to 10 items for low. Never exceed 10.
- Each alternative: {{"cip": "XX.XXXX", "title": "...", "why": "short phrase"}}.

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

    school_cips = intent._get_school_cips(unitid)
    family_prefixes = list({c["cipcode"][:2] for c in school_cips if c.get("cipcode")})
    crosswalk_cips = intent._get_crosswalk_cips_for_families(family_prefixes)

    school_cip_list = "\n".join(
        f"- {c['cipcode']} {c['program_name']}" for c in school_cips
    ) or "(no programs reported)"
    crosswalk_cip_list = "\n".join(
        f"- {c['cipcode']} {c['cip_title']}" for c in crosswalk_cips[:60]
    ) or "(no crosswalk data)"

    system = _STREAM_INTENT_SYSTEM_PROMPT.format(
        student_input=major_text,
        school_name=school_name,
        school_cip_list=school_cip_list,
        crosswalk_cip_list=crosswalk_cip_list,
    )
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
            max_tokens=700,
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
    valid_4digit: set[str] = {
        c.get("cipcode", "")[:5] for c in school_cips if c.get("cipcode")
    }
    # Only reject when we successfully loaded a non-empty crosswalk to
    # validate against. An empty crosswalk usually means the DB call
    # failed or the school has no catalog — falling back to "trust
    # Gemma" is safer than silently degrading every resolution.
    fabricated = (
        bool(matched_cip)
        and _CIP_PATTERN.match(matched_cip) is not None
        and bool(valid_6digit)
        and matched_cip not in valid_6digit
        and matched_cip[:5] not in valid_4digit
    )
    if fabricated:
        logger.warning(
            "set_your_course: Gemma returned matched_cip=%s for %r at "
            "unitid-unknown, not present in crosswalk or school catalog; "
            "degrading to low confidence.",
            matched_cip,
            major_text,
        )
        confidence = "low"
        # Drop the fabricated code so the frontend can route the
        # student through the chip flow instead of querying a fake CIP.
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

    if not _CIP_PATTERN.match(matched_cip):
        # Malformed primary: degrade to low-confidence placeholder but
        # keep any prose we already streamed.
        return IntentResult(
            matched_cip="",
            matched_title=matched_title,
            confidence="low",
            reasoning=prose.strip() or "No program code resolved.",
            careers_preview=[],
            needs_clarification=True,
            alternatives=None,
            parent_cip="",
        )

    careers_preview = intent._get_career_titles_for_cip(matched_cip)
    alternatives = intent._sanitize_alternatives(
        parsed.get("alternatives"), matched_cip
    )

    reasoning = prose.strip() or str(parsed.get("reasoning", "")).strip()

    return IntentResult(
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
    )


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

    For ``not_expected`` we run the chip-routing prompt with a tool
    pre-fetch for grounding.
    """
    if request.chip_id in ("show_less_common", "change_major"):
        return ChipResponse(
            debug_trace="",
            updated_resolution=None,
            bucket=None,
            confirmed_focus=None,
        )

    # not_expected path.
    prefetch_result, tool_call_made = await _prefetch_career_paths(request)
    prefetch_block = _format_prefetch_block(prefetch_result)

    current = request.current_resolution
    initial = request.initial_resolution
    current_cip4 = current.matched_cip[:5] if len(current.matched_cip) >= 5 else ""
    initial_cip4 = initial.matched_cip[:5] if len(initial.matched_cip) >= 5 else ""

    tile_titles = ", ".join(current.careers_preview[:6]) or "(none)"

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

    user_parts = [
        f'Student tapped "not expected" with clarifier: "{request.clarifier or ""}".',
        "Pre-fetched tool context (for grounding):",
        prefetch_block,
        "Classify, reason in 2-4 sentences, and emit the structured tails.",
    ]
    user = "\n\n".join(user_parts)

    extra = {
        "call_site": "set_your_course_chip",
        "chip_id": request.chip_id,
        "unitid": request.unitid,
        "school_name": request.school_name,
        "current_cip": current.matched_cip,
        "initial_cip": initial.matched_cip,
        "clarifier_len": len(request.clarifier or ""),
    }

    raw = await gemma_client.generate_chat_async(
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=600,
        temperature=0.2,
        extra=extra,
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
    )


async def _prefetch_career_paths(
    request: ChipRequest,
) -> tuple[dict[str, Any] | None, bool]:
    """Pre-fetch get_career_paths so Gemma has grounded context.

    Returns ``(result, tool_call_made)``. ``tool_call_made`` is only True
    when the MCP call actually returned data — used as the gate for the
    ``confirmed_focus`` invariant (we never confirm a sub-focus without
    tool verification).
    """
    # Route the pre-fetch through the same substitution semantics the
    # live preview uses: when the school reports a broader parent CIP,
    # send that as the cipcode so the MCP handler's substitution branch
    # fires, and pass Gemma's matched leaf as student_cip so the YAML
    # lookup is skipped entirely. Falls back to the matched CIP alone
    # when no parent is set.
    resolution = request.current_resolution
    lookup_cip = (resolution.parent_cip or resolution.matched_cip).strip()
    args: dict[str, Any] = {
        "unitid": request.unitid,
        "cipcode": lookup_cip,
    }
    if resolution.matched_cip:
        args["student_cip"] = resolution.matched_cip
    for attempt in range(2):
        try:
            result = mcp_client.call("get_career_paths", args)
            if result:
                return result, True
            return None, False
        except Exception as exc:
            logger.warning(
                "set_your_course pre-fetch attempt %d failed: %s",
                attempt + 1,
                exc,
            )
    return None, False


def _format_prefetch_block(result: dict[str, Any] | None) -> str:
    """Render the MCP pre-fetch as a compact prompt block."""
    if not result:
        return "(pre-fetch unavailable — proceed with what the student told us)"
    data = result.get("data") if isinstance(result, dict) else None
    if not data:
        caveat = result.get("data_caveat") if isinstance(result, dict) else None
        if caveat:
            return json.dumps(caveat, default=str)[:1200]
        return "(pre-fetch returned no rows)"
    # Compact top-N summary — don't flood the context window.
    top: list[str] = []
    for row in list(data)[:8]:
        if not isinstance(row, dict):
            continue
        title = row.get("occupation_title") or row.get("soc_title") or "?"
        soc = row.get("soc_code") or row.get("soc") or ""
        top.append(f"- {title} ({soc})" if soc else f"- {title}")
    return "\n".join(top) if top else "(pre-fetch returned no usable rows)"


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

    # Mirror confirmed_focus onto the updated_resolution when it exists.
    if updated_resolution is not None and confirmed_focus:
        updated_resolution = updated_resolution.model_copy(
            update={"confirmed_focus": confirmed_focus}
        )

    return ChipResponse(
        debug_trace=debug_trace,
        updated_resolution=updated_resolution,
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
