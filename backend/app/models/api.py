"""Request body models for POST endpoints.

Thin wrappers capturing what the frontend sends, not what services return.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.career import Build, IntentResult
from app.services.locale import AppLocale


class OutcomesRequest(BaseModel):
    unitid: int
    cipcode: str
    student_major: str | None = None
    # Caller-resolved CIP (e.g. Gemma's matched_cip from the new
    # /set-your-course flow). When set, the MCP handler skips the
    # YAML-backed major_to_cip lookup and uses this CIP directly to
    # drive the substitution decision. Optional for backwards
    # compatibility with legacy callers that only have student_major.
    student_cip: str | None = None
    effort: str = "balanced"
    loan_pct: float = 1.0
    intent_keywords: list[str] = Field(default_factory=list)
    home_state: str | None = None

    @field_validator("home_state", mode="before")
    @classmethod
    def _normalize_home_state(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("must be a 2-letter state abbreviation")
        return v


class TierRequest(BaseModel):
    outcomes: list[dict]
    school_name: str
    program_name: str
    cipcode: str
    student_major_text: str | None = None
    intent_keywords: list[str] = Field(default_factory=list)


class BuildRequest(BaseModel):
    profile_name: str
    school_name: str
    unitid: int
    cipcode: str
    cip_title: str
    major_text: str
    effort: str
    loan_pct: float
    selected_soc: str
    selected_title: str
    student_major: str | None = None
    # Caller-resolved CIP (mirrors OutcomesRequest). New flow forwards
    # Gemma's matched_cip so /build stays consistent with the preview.
    student_cip: str | None = None
    intent_keywords: list[str] = Field(default_factory=list)
    home_state: str | None = None
    school_state: str | None = None
    published_cost_4yr: float | None = None
    animal_emoji: str | None = None
    locale: AppLocale = "en"

    @field_validator("home_state", "school_state", mode="before")
    @classmethod
    def _normalize_state(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", v):
            raise ValueError("must be a 2-letter state abbreviation")
        return v


class RerollRequest(BaseModel):
    boss_id: str
    skill_ids: list[str]


class WrapupRequest(BaseModel):
    boss_id: str
    all_skill_titles: list[str]
    all_narratives: list[str]


class RescoreRequest(BaseModel):
    effort: str = "balanced"
    loan_pct: float = 1.0


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    locale: AppLocale | None = None


# ---------------------------------------------------------------------------
# Ask Gemma — scope-aware chat surface (POST /chat/ask).
# See docs/specs/feature-ask-gemma.md §4.
# ---------------------------------------------------------------------------

AskScopeKind = Literal["stat", "boss", "skill", "build", "compare", "branch"]

# SOC codes follow the BLS XX-XXXX shape exactly. branch scope target_id
# flows directly into a parameterized DuckDB lookup; rejecting non-SOC
# input at the boundary closes the unauthenticated /chat/ask DoS-amplifier
# surface flagged by the 2026-05-01 staff engineer audit (S3).
_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")


class AskScope(BaseModel):
    """Scope discriminator for POST /chat/ask.

    - kind="stat": 1 build_id, target_id in ERN/ROI/RES/GRW/AURA
    - kind="boss": 1 build_id, target_id in ai/loans/market/burnout/ceiling
    - kind="skill": 1 build_id, target_id is the AppliedSkill.id
      (length-capped at 64 chars; existence is checked at the service
      layer against the in-memory build skill list)
    - kind="build": 1 build_id, target_id is None
    - kind="compare": 2-4 build_ids, target_id is None
    - kind="branch": 1 build_id, target_id is the branch's to_soc (or
      the build's root soc_code for the anchor-at-root case). Must
      match the SOC ``\\d{2}-\\d{4}`` shape; existence is then checked
      at the service layer against build.branches / build.career.
    """

    kind: AskScopeKind
    build_ids: list[str] = Field(min_length=1, max_length=4)
    target_id: str | None = None

    @model_validator(mode="after")
    def _validate_cardinality(self) -> "AskScope":
        if self.kind == "compare":
            if not (2 <= len(self.build_ids) <= 4):
                raise ValueError("compare scope requires 2-4 build_ids")
            if self.target_id is not None:
                raise ValueError("compare scope must not set target_id")
        else:
            if len(self.build_ids) != 1:
                raise ValueError(
                    f"{self.kind} scope requires exactly 1 build_id"
                )
        if self.kind in ("stat", "boss", "skill", "branch"):
            if not self.target_id:
                raise ValueError(
                    f"{self.kind} scope requires target_id"
                )
        if self.kind == "stat":
            valid_stats = {"ERN", "ROI", "RES", "GRW", "AURA"}
            if self.target_id not in valid_stats:
                raise ValueError(
                    f"stat target_id must be one of {sorted(valid_stats)}"
                )
        if self.kind == "boss":
            valid_bosses = {"ai", "loans", "market", "burnout", "ceiling"}
            if self.target_id not in valid_bosses:
                raise ValueError(
                    f"boss target_id must be one of {sorted(valid_bosses)}"
                )
        if self.kind == "branch":
            # fullmatch (not match): Python's `$` in re.match allows a
            # trailing newline, so "11-3021\n" would otherwise slip
            # through this security-critical validator.
            if not _SOC_PATTERN.fullmatch(self.target_id or ""):
                raise ValueError(
                    "branch target_id must match SOC pattern \\d{2}-\\d{4}"
                )
        if self.kind == "skill":
            # Defense-in-depth length cap. AppliedSkill.id is a
            # snake_case identifier in the curated skill pool; 64 chars
            # is generous and keeps the lookup surface bounded for
            # unauthenticated callers.
            if len(self.target_id or "") > 64:
                raise ValueError("skill target_id must be <= 64 chars")
        return self


class AskRequest(BaseModel):
    """POST /chat/ask request body."""

    scope: AskScope
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict[str, Any]] = Field(default_factory=list)
    locale: AppLocale | None = None


class TraceEventPayload(BaseModel):
    """One enriched tool-call entry for ``AskResponse.tool_calls``.

    Also serves as the wire payload of ``turn_complete`` SSE events on
    ``POST /chat/ask/stream``. The ``turn`` field carries the per-
    dispatch monotonic ``dispatch_index`` from
    ``ToolCallTurn.dispatch_index`` (Decision #13) — unique even with
    parallel tool calls in one outer LLM turn. ``<GemmaTrace>`` uses
    this as the row-correlation key.

    See ``docs/specs/feature-gemma-trace.md`` §4 Data Model.
    """

    turn: int
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_preview: str = ""
    duration_ms: int = 0
    error: str | None = None


# ---------------------------------------------------------------------------
# ExplainStatReceipt — structured-JSON output for the "Explain this stat"
# affordance on /my-build. Fires only on the sentinel opener
# ``[explain-this:ERN]``; all other Ask Gemma traffic continues to use the
# free-form prose path. See docs/specs/feature-explain-stat-receipt.md.
# ---------------------------------------------------------------------------

# Module-level helper used by ``StatComponent`` and ``ExplainStatReceipt``
# prose-field validators. Catches Gemma echoing the system-appendix
# placeholder sentinels back into the JSON instead of replacing them with
# real prose. Without this guard a string like "__FILL_IN__" would pass
# Pydantic and render to the student.
_SENTINEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"__FILL[_ ]IN__", re.IGNORECASE),
    re.compile(r"\[\s*FILL[\s_-]*IN", re.IGNORECASE),
    re.compile(r"<\s*FILL[\s_-]*IN", re.IGNORECASE),
    re.compile(r"\bONE-SENTENCE\s+DEFINITION\s+HERE\b", re.IGNORECASE),
    # The naked word "placeholder" can appear in legitimate prose
    # (e.g. "the score is a placeholder for...") so the sentinel
    # form requires the underscored / bracketed wrapper that an
    # actual template echo would carry.
    re.compile(r"__PLACEHOLDER__|\[PLACEHOLDER\]|<PLACEHOLDER>", re.IGNORECASE),
)


def _reject_sentinel_passthrough(value: str) -> str:
    """Reject prose strings that contain unreplaced template sentinels.

    Used as a Pydantic field_validator on every prose field
    (one_liner, components[*].explainer, components[*].anchor_text,
    why_mix_paragraph). Triggers the markdown fallback path when Gemma
    echoes the appendix's placeholder sentinels back instead of writing
    real content.
    """
    for pattern in _SENTINEL_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"prose field contains unreplaced template sentinel: "
                f"{value[:80]!r}"
            )
    return value


class ScoringTier(BaseModel):
    """One row in a stat's scoring scale — maps an input range to a score."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(description="Human-readable tier name, e.g. 'Excellent'.")
    range: str = Field(description="Input range, e.g. '≤ 0.25' or '0.25 – 0.50'.")
    score: str = Field(description="Score or range, e.g. '10' or '9 – 7'.")


class ReceiptSource(BaseModel):
    """A data source citation rendered as a pill in the receipt UI."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(
        description="Human-readable category, e.g. 'Graduate earnings'."
    )
    name: str = Field(
        description=(
            "Full source name, e.g. 'College Scorecard "
            "(U.S. Department of Education)'."
        )
    )


class StatComponent(BaseModel):
    """One mixed-in piece of a stat's score (e.g. the 60% school-rank
    piece of ERN, or the 40% occupation-wage piece). Generic across
    all five pentagon stats (ERN/ROI/RES/GRW/AURA)."""

    model_config = ConfigDict(extra="forbid")

    weight_pct: int = Field(
        ge=0,
        le=100,
        description=(
            "Percentage weight in the formula (e.g. 60 for the 60% "
            "school-rank piece). Sum across components <= 100."
        ),
    )
    label: str = Field(
        description=(
            "Plain-English component name, e.g. 'your school's "
            "program rank'. Server-normalized against a per-stat "
            "allowlist in _postprocess_ern_explain_receipt."
        )
    )
    explainer: str = Field(
        description=(
            "Gemma-written 1-2 sentence explanation of what this "
            "component measures and where the percentile comes from. "
            "Voice rules from pentagon-stat-explanation/SKILL.md apply. "
            "Must NOT contain numeric score references; the score "
            "callout is the UI's responsibility."
        )
    )
    value_pct: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Percentile rank (0-100). Null when the underlying input "
            "is missing — the renderer reads this as 'we don't have "
            "this yet,' not as zero. Server-stamped from the tool "
            "result, never from Gemma."
        ),
    )
    anchor_text: str = Field(
        description=(
            "The named entity this percentile attaches to, e.g. "
            "'Indiana University Computer Science grads' or "
            "'Software Developer'. Used in the bullet's lead phrase."
        )
    )
    anchor_dollars: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Dollar amount associated with the anchor (median "
            "earnings, median wage). Null when missing. "
            "Server-stamped from the tool result."
        ),
    )
    missing_reason: str | None = Field(
        default=None,
        description=(
            "When value_pct or anchor_dollars is null, this string "
            "explains why in plain English (e.g. 'no median earnings "
            "reported for this program yet'). Server-stamped, not "
            "from Gemma."
        ),
    )
    evidence_bullets: list[str] | None = Field(
        default=None,
        max_length=6,
        description=(
            "Optional server-stamped concrete evidence for this component. "
            "For RES, these are task examples such as work AI can already "
            "handle or tasks that still require humans. Gemma may omit this; "
            "postprocessors overwrite it from trusted build/tool data."
        ),
    )

    _reject_sentinel_explainer = field_validator("explainer")(
        _reject_sentinel_passthrough
    )
    _reject_sentinel_anchor_text = field_validator("anchor_text")(
        _reject_sentinel_passthrough
    )


class ExplainStatReceipt(BaseModel):
    """Structured explainer-receipt payload for one of the five
    pentagon stats (ERN, ROI, RES, GRW, AURA). AURA uses the
    additive score_provenance field for institution-level basis."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["receipt"] = Field(
        default="receipt",
        description=(
            "Self-discriminator field. Lets the frontend Zod parser "
            "distinguish a receipt response from a plain-string "
            "response on the union type str | ExplainStatReceipt "
            "without object-shape sniffing. Always 'receipt'."
        ),
    )
    stat_code: Literal["ERN", "ROI", "RES", "GRW", "AURA"] = Field(
        description="Pentagon stat code; mirrors AskScope.target_id."
    )
    stat_name: str = Field(
        description=(
            "Plain-English stat name, e.g. 'Earning Power'. "
            "Mirrors ask_gemma._STAT_ALIAS but Pydantic-typed."
        )
    )
    score: int | None = Field(
        default=None,
        ge=1,
        le=10,
        description=(
            "The student's score on this stat. Server-stamped from "
            "build.career.stats.<stat>; whatever Gemma emits in this "
            "field is overwritten unconditionally. Null when the "
            "underlying inputs are missing — the renderer shows an "
            "open-ring callout instead of a number, and per-component "
            "missing_reason fields explain which input is unavailable."
        ),
    )
    score_max: int = Field(
        default=10,
        description=(
            "Maximum possible score. Fixed at 10 in v1.0; "
            "parameterized for future stat-system changes."
        ),
    )
    one_liner: str = Field(
        description=(
            "Gemma-written one-sentence definition of the score. "
            "Voice rules from pentagon-stat-explanation/SKILL.md "
            "apply. Must NOT contain numeric score references."
        )
    )
    components: list[StatComponent] = Field(
        min_length=1,
        max_length=5,
        description=(
            "The mixed-in pieces of the score. ERN uses 2 (60% + "
            "40%); ROI uses 1; GRW uses 1; RES uses 2 (post-reshape "
            "blended)."
        ),
    )
    math_line: str = Field(
        description=(
            "Server-rendered math expression, e.g. "
            "'0.6 × 0.87 + 0.4 × 0.92 → score 9/10'. Null inputs "
            "render as 'n/a'. **Always server-built unconditionally; "
            "the value Gemma emits in this field (if any) is "
            "discarded.** When effort != 'balanced', a separate "
            "effort line is appended on a new line."
        )
    )
    sources: list[ReceiptSource] = Field(
        min_length=1,
        description="Data sources rendered as pills in the receipt UI.",
    )
    why_mix_paragraph: str = Field(
        max_length=800,
        description=(
            "Gemma-written ~3-sentence 'two students contrast' "
            "paragraph. Voice rules from "
            "pentagon-stat-explanation/SKILL.md apply. Must NOT "
            "contain numeric score references. max_length=800 "
            "catches token-budget truncations as a Pydantic "
            "validation failure."
        )
    )
    scoring_scale: list[ScoringTier] | None = Field(
        default=None,
        description=(
            "Optional scoring tier table rendered below the math "
            "line. Server-built from the stat's breakpoint table; "
            "Gemma never populates this."
        ),
    )
    score_provenance: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "Server-stamped institution-level provenance for stat-level "
            "metadata that doesn't fit the per-component StatComponent "
            "shape. AURA-only in v1.0 (server-stamped from "
            "_humanize_basis(career.aura_score_basis)); ERN/ROI/RES/GRW "
            "emit None. The renderer surfaces this as a subtle byline "
            "under the score callout when populated; suppresses entirely "
            "when None. Gemma never writes this field."
        ),
    )

    _reject_sentinel_one_liner = field_validator("one_liner")(
        _reject_sentinel_passthrough
    )
    _reject_sentinel_why_mix = field_validator("why_mix_paragraph")(
        _reject_sentinel_passthrough
    )

    @field_validator("score_provenance")
    @classmethod
    def _reject_sentinel_score_provenance(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _reject_sentinel_passthrough(value)


class AskResponse(BaseModel):
    """POST /chat/ask response body.

    ``tool_calls`` carries the enriched per-turn payload that powers
    ``<GemmaTrace>``'s post-hoc (fallback) render — when SSE
    streaming is unavailable the frontend reads this list and
    synthesizes ``turn_start`` + ``turn_complete`` events from it.

    May be non-empty even when ``response`` is the chat_unavailable
    fallback string — e.g. when one tool call succeeded before
    Gemma's final turn failed.

    ``response`` is a discriminated union: a plain string for every
    existing scope (boss, skill, build, branch, compare, free-form
    stat questions), or a structured ``ExplainStatReceipt`` when the
    stat-scope explain-this-stat sentinel fires successfully.
    """

    response: str | ExplainStatReceipt
    tool_calls: list[TraceEventPayload] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# SSE wire-format models for POST /chat/ask/stream
#
# Each event below is the JSON payload that arrives in the ``data:`` field
# of one SSE frame. The discriminated union allows future event types
# (e.g. ``thinking``, ``final_text_delta``) to be added without breaking
# older consumers, provided the frontend parser silently skips unknown
# ``type`` values per Decision #15.
#
# In ``TraceTurnStart`` and ``TraceTurnComplete``, the ``turn`` field
# carries the backend's ``dispatch_index`` — the per-dispatch monotonic
# correlation key, NOT the loop's outer LLM turn_number.
# ---------------------------------------------------------------------------


class TraceTurnStart(BaseModel):
    """Emitted immediately before each ``await dispatch(...)`` call —
    so the UI shows the in-progress shimmer the moment Gemma issues
    the call, not after the result lands."""

    type: Literal["turn_start"] = "turn_start"
    turn: int
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class TraceTurnComplete(BaseModel):
    """Emitted immediately after the matching ``ToolCallTurn`` is
    appended to ``tool_call_log``. Carries the same ``turn`` (=
    dispatch_index) as the prior ``turn_start`` so the consumer pairs
    them as one row."""

    type: Literal["turn_complete"] = "turn_complete"
    turn: int
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    result_preview: str = ""
    duration_ms: int = 0
    error: str | None = None


class TraceFinalText(BaseModel):
    """Carries Gemma's final text answer. Always emitted exactly once
    per stream, even on transport failure (in which case ``response``
    is the localized ``chat_unavailable`` fallback string).

    ``response`` matches ``AskResponse.response`` — a plain string for
    every existing scope, or a structured ``ExplainStatReceipt`` when
    the stat-scope explain-this-stat sentinel fires successfully.
    """

    type: Literal["final_text"] = "final_text"
    response: str | ExplainStatReceipt


class TraceDone(BaseModel):
    """Trailer event signaling end-of-stream. The frontend can stop
    reading after this event arrives."""

    type: Literal["done"] = "done"


TraceEvent = Annotated[
    TraceTurnStart | TraceTurnComplete | TraceFinalText | TraceDone,
    Field(discriminator="type"),
]


class CompareRequest(BaseModel):
    build_ids: list[str] = Field(min_length=2, max_length=4)


class ProfileLookupRequest(BaseModel):
    name_query: str = Field(..., max_length=200)


class ProfileRerollRequest(BaseModel):
    current_name: str = Field(..., max_length=200)


# ---------------------------------------------------------------------------
# Set Your Course — new unified-screen models.
# See docs/specs/feature-set-your-course.md §4.
# ---------------------------------------------------------------------------

ChipId = Literal["not_expected", "show_less_common", "change_major"]
FeasibilityMode = Literal[
    "direct_hit",
    "crosswalk_quirk",
    "adjacent_reachable",
    "school_gap",
    "genuinely_impossible",
]
ChipBucket = Literal[
    "crosswalk_mismatch",
    "semantic_drift",
    "school_gap",
    "data_suppression",
    "tier_placement",
    "intent_divergence",
    "peer_variance",
    "no_issue_found",
]


class IntentStreamRequest(BaseModel):
    """POST /intent/stream — initial resolution with streaming prose."""

    major_text: str
    school_name: str
    unitid: int
    programs: list[dict[str, Any]] = Field(default_factory=list)
    locale: AppLocale = "en"


class Suggestion(BaseModel):
    """One community-suggestion card shown under the career preview."""

    clicked_soc: str
    clicked_career_title: str
    canonical_cip4: str
    count: int


class CtaLink(BaseModel):
    """Outbound link attached to a chip response (e.g. the School Discovery
    v0.5 stub for the school_gap bucket)."""

    label: str
    href: str


class ChipRequest(BaseModel):
    """POST /intent/chip — one stateless chip tap."""

    chip_id: ChipId
    clarifier: str | None = Field(default=None, max_length=280)
    current_resolution: IntentResult
    initial_resolution: IntentResult
    school_name: str
    unitid: int
    programs: list[dict[str, Any]] = Field(default_factory=list)
    locale: AppLocale = "en"

    @model_validator(mode="after")
    def _require_clarifier_for_not_expected(self) -> "ChipRequest":
        if self.chip_id == "not_expected":
            if self.clarifier is None or self.clarifier.strip() == "":
                raise ValueError(
                    "clarifier is required when chip_id is 'not_expected'"
                )
        return self


class ChipResponse(BaseModel):
    """Response for POST /intent/chip."""

    debug_trace: str
    updated_resolution: IntentResult | None = None
    cta_link: CtaLink | None = None
    bucket: ChipBucket | None = None
    confirmed_focus: str | None = None


class CheckpointRequest(BaseModel):
    screen: str
    profile_data: dict | None = None
    build_input_data: dict | None = None
    build_id: str | None = None
    gauntlet_data: dict | None = None
    tiered_careers_data: dict | None = None
    selected_career_data: dict | None = None


class SessionResponse(BaseModel):
    session_id: str
    last_screen: str
    profile_data: dict | None = None
    build_input_data: dict | None = None
    build_id: str | None = None
    build: Build | None = None
    gauntlet_data: dict | None = None
    tiered_careers_data: dict | None = None
    selected_career_data: dict | None = None
    created_at: str
    updated_at: str


class RebuildRequest(BaseModel):
    effort: str = "balanced"
    loan_pct: float = 1.0


class CommitRequest(BaseModel):
    """POST /intent/commit — append one correction log record on commit."""

    school_name: str
    unitid: int
    major_text: str
    initial_resolution: IntentResult
    current_resolution: IntentResult
    chips_tapped: list[ChipId] = Field(default_factory=list)
    clarifier: str | None = Field(default=None, max_length=280)
    bucket: ChipBucket | None = None
    clicked_soc: str | None = None
    clicked_career_title: str | None = None
    feasibility_mode: FeasibilityMode | None = None
