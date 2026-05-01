"""Request body models for POST endpoints.

Thin wrappers capturing what the frontend sends, not what services return.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

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

    - kind="stat": 1 build_id, target_id in ERN/ROI/RES/GRW/HMN
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
            valid_stats = {"ERN", "ROI", "RES", "GRW", "HMN"}
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


class AskResponse(BaseModel):
    """POST /chat/ask response body. ``tool_calls`` may be non-empty
    even when ``response`` is the chat_unavailable fallback string —
    e.g. when one tool call succeeded before Gemma's final turn failed.
    The frontend ignores ``tool_calls``; it exists for telemetry and
    the routing/E2E test that asserts dispatch fired."""

    response: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


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
