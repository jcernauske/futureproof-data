"""Pydantic models for the /career-pick Ask-Gemma chip surface.

Two endpoints share this contract:
- ``GET /career-pick/chips`` returns ``list[CareerPickChip]``.
- ``POST /career-pick/ask`` takes ``AskCareerPickRequest`` and returns
  ``AskCareerPickResponse``.

CIPCODE is always ``str`` per the project-wide rule (``CLAUDE.md``) —
never a float, regardless of how it looks.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
    """Student clicked a chip — resolve the canned prompt + call Gemma."""

    chip_id: str
    cipcode: str
    major_text: str
    soc_codes: list[str] = Field(default_factory=list)
    selected_soc: str | None = None
    terminal_title: str | None = None
    locale: Literal["en", "es"] = "en"


class AskCareerPickResponse(BaseModel):
    """Gemma's answer (or deterministic fallback)."""

    chip_id: str
    answer: str = Field(..., description="4-6 sentences, 6th-grade reading level")
    fallback_fired: bool = Field(default=False)
