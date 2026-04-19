"""Request body models for POST endpoints.

Thin wrappers capturing what the frontend sends, not what services return.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


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
    effort: str = "balanced"
    loan_pct: float = 1.0


class TierRequest(BaseModel):
    outcomes: list[dict]
    school_name: str
    program_name: str
    cipcode: str


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


class RerollRequest(BaseModel):
    boss_id: str
    skill_ids: list[str]


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class CompareRequest(BaseModel):
    build_ids: list[str]


class ProfileLookupRequest(BaseModel):
    name_query: str = Field(..., max_length=200)


class ProfileRerollRequest(BaseModel):
    current_name: str = Field(..., max_length=200)
