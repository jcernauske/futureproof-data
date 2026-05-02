"""Pydantic models for the /career-pick Ask-Gemma chip surface.

Two endpoints share this contract:
- ``GET /career-pick/chips`` returns ``list[CareerPickChip]``.
- ``POST /career-pick/ask`` takes ``AskCareerPickRequest`` and returns
  ``AskCareerPickResponse``.

CIPCODE is always ``str`` per the project-wide rule (``CLAUDE.md``) —
never a float, regardless of how it looks.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# CIP codes follow the IPEDS XX.XXXX (4 decimals) or XX.XX (2 decimals)
# convention. Anchored validators close the unauthenticated DoS / prompt-
# injection surface on POST /career-pick/ask flagged by the 2026-05-01
# audit followup-3 §P1.
_CIP_PATTERN = re.compile(r"^\d{2}\.\d{2,4}$")
_SOC_PATTERN = re.compile(r"^\d{2}-\d{4}$")


class CareerPickChip(BaseModel):
    """One canned question surfaced on /career-pick.

    Delivered by ``GET /career-pick/chips`` in the order the frontend
    should render. Elevated chips (``elevated=True``) are visually
    distinguished and move to the top of the row. ``terminal_title``
    is populated only when the chip's question is parameterized on a
    terminal occupation the student's intent implies (e.g. "Why don't
    I see 'doctor'?" sets ``terminal_title="doctor"``).
    """

    id: str = Field(
        ..., description="Stable chip identifier, e.g. 'why_no_terminal_soc'"
    )
    label: str = Field(..., description="Button text shown to the student")
    elevated: bool = Field(default=False)
    terminal_title: str | None = Field(
        default=None,
        description="If this chip is about a specific missing occupation",
    )


class AskCareerPickRequest(BaseModel):
    """Student clicked a chip — resolve the canned prompt + call Gemma.

    Field shapes are bounded at the model boundary because every value
    here flows into a Gemma prompt without sanitization (see
    ``career_pick_qna._build_user_prompt``). Without the caps, an
    unauthenticated caller could drive arbitrary-length / arbitrary-
    content text through the LLM as both a cost amplifier and a
    prompt-injection surface.
    """

    chip_id: str = Field(min_length=1, max_length=64)
    cipcode: str
    major_text: str = Field(min_length=1, max_length=200)
    soc_codes: list[str] = Field(default_factory=list, max_length=50)
    selected_soc: str | None = None
    terminal_title: str | None = Field(default=None, max_length=200)
    locale: Literal["en", "es"] = "en"

    @field_validator("cipcode")
    @classmethod
    def _validate_cipcode(cls, v: str) -> str:
        if not _CIP_PATTERN.fullmatch(v):
            raise ValueError("cipcode must match CIP pattern \\d{2}\\.\\d{2,4}")
        return v

    @field_validator("selected_soc")
    @classmethod
    def _validate_selected_soc(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not _SOC_PATTERN.fullmatch(v):
            raise ValueError("selected_soc must match SOC pattern \\d{2}-\\d{4}")
        return v

    @field_validator("soc_codes")
    @classmethod
    def _validate_soc_codes(cls, v: list[str]) -> list[str]:
        for soc in v:
            if not _SOC_PATTERN.fullmatch(soc):
                raise ValueError(
                    f"soc_codes entry {soc!r} must match SOC pattern \\d{{2}}-\\d{{4}}"
                )
        return v


class AskCareerPickResponse(BaseModel):
    """Gemma's answer (or deterministic fallback)."""

    chip_id: str
    answer: str = Field(..., description="4-6 sentences, 6th-grade reading level")
    fallback_fired: bool = Field(default=False)
