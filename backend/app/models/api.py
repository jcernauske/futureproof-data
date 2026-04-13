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
