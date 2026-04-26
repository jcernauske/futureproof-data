"""Request body models for POST endpoints.

Thin wrappers capturing what the frontend sends, not what services return.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.career import Build, IntentResult
from app.services.locale import AppLocale


class IntentRequest(BaseModel):
    school_name: str
    unitid: int
    major_text: str
    programs: list[dict]


class IntentConfirmRequest(BaseModel):
    school_name: str
    unitid: int
    major_text: str
    matched_cip: str
    matched_title: str
    # School's reported broad same-family CIP when substitution applies
    # (empty string otherwise). Cached alongside the match so the next
    # cache hit for the same (major_text, unitid) returns the same
    # parent_cip the first intent resolution produced — without it, the
    # frontend's lookupCip routing silently degrades to matched_cip and
    # the backend falls into the broaden fallback (see IU+Marketing
    # regression). Default empty for backward-compat with any client
    # that hasn't been updated yet.
    parent_cip: str = ""


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


class CompareRequest(BaseModel):
    build_ids: list[str]


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
