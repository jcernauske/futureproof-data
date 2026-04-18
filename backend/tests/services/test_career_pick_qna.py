"""Tests for the career_pick_qna service.

Covers the chip list builder (catalog order + auto-elevation heuristic)
and the ``ask`` path (happy path, empty-response fallback, raising-client
fallback, unknown chip_id, and the supplemental gemma.jsonl call-site log).

Gemma transport is mocked via ``monkeypatch.setattr`` on
``gemma_client.generate_async``. The autouse ``_reset_gemma_client_state``
fixture in ``conftest.py`` already resets the client cache + semaphore
between tests, so no per-test teardown is required here.
"""

from __future__ import annotations

import json

import pytest

from app.models.career_pick import AskCareerPickRequest
from app.services import career_pick_qna, gemma_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _request(
    *,
    chip_id: str,
    major_text: str = "pre-med",
    cipcode: str = "26.0101",
    soc_codes: list[str] | None = None,
    selected_soc: str | None = None,
    terminal_title: str | None = None,
) -> AskCareerPickRequest:
    return AskCareerPickRequest(
        chip_id=chip_id,
        cipcode=cipcode,
        major_text=major_text,
        soc_codes=soc_codes or [],
        selected_soc=selected_soc,
        terminal_title=terminal_title,
    )


# ---------------------------------------------------------------------------
# build_chip_list — auto-elevation heuristic
# ---------------------------------------------------------------------------


def test_build_chip_list_elevates_pre_med_when_physician_missing() -> None:
    """pre-med major + SOC list lacking any physician code → elevated doctor chip
    is first in the returned list + carries terminal_title="doctor"."""
    chips = career_pick_qna.build_chip_list(
        cipcode="26.0101",
        major_text="pre-med",
        soc_codes=["19-1029", "13-1071"],
    )

    assert len(chips) >= 1, "expected at least the elevated chip + base catalog"
    first = chips[0]
    assert first.id == "why_no_doctor"
    assert first.elevated is True
    assert first.terminal_title == "doctor"

    # Base-catalog chips still follow the elevated chip, in catalog order.
    base_ids = [chip.id for chip in chips[1:]]
    # Other graduate-intent chips should be absent (their patterns don't match).
    assert "why_no_lawyer" not in base_ids
    assert "why_no_dentist" not in base_ids
    # The three non-graduate base chips are always present in the same order.
    assert base_ids == [
        "what_does_this_do",
        "right_school_for_this",
        "why_these_tiers",
    ]


def test_build_chip_list_no_elevation_when_physician_present() -> None:
    """With a physician SOC rendered (29-1216), the doctor chip is NOT elevated
    — and because graduate-intent chips are only emitted on mismatch, not
    present at all."""
    chips = career_pick_qna.build_chip_list(
        cipcode="26.0101",
        major_text="pre-med",
        soc_codes=["19-1029", "29-1216"],  # physician present
    )

    ids = [chip.id for chip in chips]
    assert "why_no_doctor" not in ids, (
        "doctor chip must not appear when physician SOC is already on screen"
    )
    # The base catalog is returned in its declared order.
    assert ids == [
        "what_does_this_do",
        "right_school_for_this",
        "why_these_tiers",
    ]
    assert all(not chip.elevated for chip in chips)


@pytest.mark.parametrize(
    "major_text",
    [
        "pre-med",
        "Pre-Med",
        "PRE-MED",
        "premed",
        "PreMed",
        "pre med",
        "PRE MED",
        "I'm interested in pre-med",
        "pre-med track",
    ],
)
def test_build_chip_list_handles_pre_med_variants(major_text: str) -> None:
    """pre-med / premed / pre med — all case-insensitive — trigger elevation."""
    chips = career_pick_qna.build_chip_list(
        cipcode="26.0101",
        major_text=major_text,
        soc_codes=["19-1029"],
    )
    assert chips, f"expected chips for major_text={major_text!r}"
    assert chips[0].id == "why_no_doctor", (
        f"pre-med variant {major_text!r} did not elevate: got {chips[0].id}"
    )
    assert chips[0].elevated is True


@pytest.mark.parametrize(
    "major_text",
    [
        "premedication",
        "comedy premeditation",
        "premeditated",
    ],
)
def test_build_chip_list_rejects_pre_med_false_positives(major_text: str) -> None:
    """Word-boundary-safe: 'premedication' / 'premeditation' / 'premeditated'
    must NOT trip the pre-med elevator. This is the regression guard for the
    regex \\bpre[\\s-]?med\\b — without the trailing \\b these would match."""
    chips = career_pick_qna.build_chip_list(
        cipcode="26.0101",
        major_text=major_text,
        soc_codes=["19-1029"],
    )
    ids = [chip.id for chip in chips]
    assert "why_no_doctor" not in ids, (
        f"false positive: {major_text!r} incorrectly matched pre-med"
    )


def test_build_chip_list_pre_law_variant() -> None:
    """pre-law → elevated lawyer chip. Terminal title = 'lawyer'."""
    chips = career_pick_qna.build_chip_list(
        cipcode="22.0001",
        major_text="pre-law",
        soc_codes=["19-1029"],
    )
    assert chips[0].id == "why_no_lawyer"
    assert chips[0].elevated is True
    assert chips[0].terminal_title == "lawyer"


def test_build_chip_list_pre_vet_variant() -> None:
    """pre-vet → elevated veterinarian chip when the vet SOC is missing."""
    chips = career_pick_qna.build_chip_list(
        cipcode="01.0000",
        major_text="pre-vet",
        soc_codes=["19-1029"],  # 29-1131 absent
    )
    assert chips[0].id == "why_no_veterinarian"
    assert chips[0].elevated is True
    assert chips[0].terminal_title == "veterinarian"


def test_build_chip_list_pre_dental_variant() -> None:
    """pre-dental → elevated dentist chip when the dental SOC is missing."""
    chips = career_pick_qna.build_chip_list(
        cipcode="26.0101",
        major_text="pre-dental",
        soc_codes=["19-1029"],  # 29-1022 etc absent
    )
    assert chips[0].id == "why_no_dentist"
    assert chips[0].elevated is True
    assert chips[0].terminal_title == "dentist"


def test_build_chip_list_non_graduate_intent_returns_base_catalog() -> None:
    """A generic major (marketing) → no elevation, base catalog in declared order."""
    chips = career_pick_qna.build_chip_list(
        cipcode="52.1401",
        major_text="marketing",
        soc_codes=["13-1161"],
    )
    ids = [chip.id for chip in chips]
    assert ids == [
        "what_does_this_do",
        "right_school_for_this",
        "why_these_tiers",
    ]
    assert all(chip.elevated is False for chip in chips)
    assert all(chip.terminal_title is None for chip in chips)


# ---------------------------------------------------------------------------
# ask() — happy path, fallbacks, unknown chip
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Gemma returns a real answer, service forwards it with
    fallback_fired=False."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")  # avoid touching disk

    async def _fake_generate_async(**_kwargs: object) -> str:
        return "canned answer"

    monkeypatch.setattr(gemma_client, "generate_async", _fake_generate_async)

    response = await career_pick_qna.ask(
        request=_request(chip_id="what_does_this_do"),
    )

    assert response.chip_id == "what_does_this_do"
    assert response.answer == "canned answer"
    assert response.fallback_fired is False


@pytest.mark.asyncio
async def test_ask_falls_back_when_gemma_returns_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty Gemma response → deterministic fallback; fallback_fired=True."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")

    async def _empty(**_kwargs: object) -> str:
        return ""

    monkeypatch.setattr(gemma_client, "generate_async", _empty)

    response = await career_pick_qna.ask(
        request=_request(chip_id="why_no_doctor", terminal_title="doctor"),
    )

    assert response.fallback_fired is True
    # Answer should be the pre-med canned fallback (substring match so test
    # stays resilient to minor copy edits).
    assert "med" in response.answer.lower()
    assert response.answer.strip() != ""


@pytest.mark.asyncio
async def test_ask_falls_back_when_gemma_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemma raising RuntimeError must NOT propagate — service catches it and
    emits the fallback. Callers never see a 5xx."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")

    async def _raise(**_kwargs: object) -> str:
        raise RuntimeError("transport blew up")

    monkeypatch.setattr(gemma_client, "generate_async", _raise)

    response = await career_pick_qna.ask(
        request=_request(chip_id="what_does_this_do"),
    )

    assert response.fallback_fired is True
    assert response.answer.strip() != ""
    assert response.chip_id == "what_does_this_do"


@pytest.mark.asyncio
async def test_ask_unknown_chip_id_raises_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown chip_id raises ValueError (router translates to 422)."""
    monkeypatch.setenv("GEMMA_LOG_DISABLED", "1")

    async def _unused(**_kwargs: object) -> str:  # pragma: no cover
        return "should not be called"

    monkeypatch.setattr(gemma_client, "generate_async", _unused)

    with pytest.raises(ValueError, match="Unknown chip_id"):
        await career_pick_qna.ask(
            request=_request(chip_id="totally_not_real"),
        )


# ---------------------------------------------------------------------------
# ask() — supplemental gemma.jsonl record
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ask_writes_call_site_to_gemma_jsonl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The ``ask`` path stamps ``call_site="career_pick.ask"`` and
    chip-correlation fields onto the single gemma.jsonl record via
    ``generate_async``'s ``extra`` kwarg (post-code-review refactor —
    was previously a supplemental second record, now merged).

    We capture the ``extra`` payload passed to the mocked ``generate_async``
    and assert the required correlation fields are present.
    """
    captured: dict[str, object] = {}

    async def _fake_generate_async(**kwargs: object) -> str:
        captured.update(kwargs)
        return "hello"

    monkeypatch.setattr(gemma_client, "generate_async", _fake_generate_async)

    await career_pick_qna.ask(
        request=_request(
            chip_id="what_does_this_do",
            major_text="pre-med",
            selected_soc="15-1252",
            soc_codes=["15-1252", "15-2051"],
        ),
    )

    extra = captured.get("extra")
    assert isinstance(extra, dict), (
        "expected ask() to pass extra kwarg to generate_async"
    )
    assert extra["call_site"] == "career_pick.ask"
    assert extra["chip_id"] == "what_does_this_do"
    assert extra["selected_soc"] == "15-1252"
    assert extra["soc_codes"] == ["15-1252", "15-2051"]
    assert extra["cipcode"] == "26.0101"
    assert extra["major_text"] == "pre-med"
