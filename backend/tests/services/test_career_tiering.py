"""Tests for Gemma-driven career tiering."""

from __future__ import annotations

from app.models.career import BossScores, CareerOutcome, PentagonStats
from app.services import career_tiering


def _outcome(soc: str, title: str = "Test", wage: float = 50000.0) -> CareerOutcome:
    return CareerOutcome(
        unitid=1,
        institution_name="Test U",
        cipcode="52.14",
        program_name="Marketing",
        soc_code=soc,
        occupation_title=title,
        stats=PentagonStats(ern=5, roi=5, res=5, grw=5, hmn=5),
        bosses=BossScores(ai=5, loans=5, market=5, burnout=5, ceiling=5),
        median_annual_wage=wage,
        stats_available_count=5,
        overall_confidence="high",
        education_level_name="Bachelor's degree",
    )


def _outcomes_8() -> list[CareerOutcome]:
    return [
        _outcome("11-2021", "Marketing Managers", 161030),
        _outcome("13-1161", "Market Research Analysts", 76950),
        _outcome("11-2022", "Sales Managers", 138060),
        _outcome("13-1131", "Fundraisers", 66490),
        _outcome("11-2011", "Advertising Managers", 123480),
        _outcome("27-3031", "Public Relations Specialists", 67440),
        _outcome("11-3011", "Administrative Services Managers", 112890),
        _outcome("13-1199", "Business Operations Specialists", 82060),
    ]


class TestParseTiers:
    def test_parses_well_formed_output(self):
        text = (
            "COMMON\n"
            "11-2021\n"
            "13-1161\n"
            "11-2022\n"
            "LESS_COMMON\n"
            "13-1131\n"
            "11-2011\n"
            "27-3031\n"
            "STRETCH\n"
            "11-3011\n"
            "13-1199\n"
        )
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        common = tiers[career_tiering.TIER_COMMON]
        less_common = tiers[career_tiering.TIER_LESS_COMMON]
        stretch = tiers[career_tiering.TIER_STRETCH]
        assert len(common) == 3
        assert len(less_common) == 3
        assert len(stretch) == 2
        assert common[0].soc_code == "11-2021"

    def test_handles_extra_text_around_soc(self):
        text = (
            "COMMON\n"
            "11-2021 Marketing Managers\n"
            "13-1161 (most common analytical path)\n"
            "LESS_COMMON\n"
            "11-2022\n"
            "STRETCH\n"
            "13-1131\n"
        )
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        assert len(tiers[career_tiering.TIER_COMMON]) == 2
        assert len(tiers[career_tiering.TIER_LESS_COMMON]) == 1
        # Unplaced outcomes land in STRETCH via catch-all.
        assert len(tiers[career_tiering.TIER_STRETCH]) >= 1

    def test_unplaced_socs_land_in_stretch(self):
        text = (
            "COMMON\n"
            "11-2021\n"
            "LESS_COMMON\n"
            "13-1161\n"
            "STRETCH\n"
        )
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        placed = (
            len(tiers[career_tiering.TIER_COMMON])
            + len(tiers[career_tiering.TIER_LESS_COMMON])
        )
        assert placed == 2
        assert len(tiers[career_tiering.TIER_STRETCH]) == 6

    def test_unknown_soc_codes_silently_dropped(self):
        text = "COMMON\n99-9999\nLESS_COMMON\nSTRETCH\n"
        outcomes = _outcomes_8()
        lookup = {o.soc_code: o for o in outcomes}
        tiers = career_tiering._parse_tiers(text, lookup)
        assert len(tiers[career_tiering.TIER_COMMON]) == 0

    def test_duplicate_soc_placed_once(self):
        text = (
            "COMMON\n"
            "11-2021\n"
            "11-2021\n"
            "LESS_COMMON\n"
            "11-2021\n"
            "STRETCH\n"
        )
        lookup = {"11-2021": _outcome("11-2021")}
        tiers = career_tiering._parse_tiers(text, lookup)
        total = sum(len(v) for v in tiers.values())
        assert total == 1


class TestTierCareers:
    def test_small_list_skips_gemma(self, monkeypatch):
        calls = []
        monkeypatch.setattr(
            career_tiering.gemma_client,
            "generate",
            lambda **kw: (calls.append(1), "")[1],
        )
        outcomes = _outcomes_8()[:3]
        tiers = career_tiering.tier_careers(
            outcomes, "Test U", "Marketing", "52.14"
        )
        assert calls == []
        assert "All career paths" in tiers
        assert len(tiers["All career paths"]) == 3

    def test_uses_gemma_when_enough_outcomes(self, monkeypatch):
        fake = (
            "COMMON\n11-2021\n13-1161\n11-2022\n"
            "LESS_COMMON\n13-1131\n11-2011\n27-3031\n"
            "STRETCH\n11-3011\n13-1199\n"
        )
        monkeypatch.setattr(
            career_tiering.gemma_client, "generate", lambda **kw: fake
        )
        tiers = career_tiering.tier_careers(
            _outcomes_8(), "Test U", "Marketing", "52.14"
        )
        assert career_tiering.TIER_COMMON in tiers
        assert career_tiering.TIER_LESS_COMMON in tiers
        assert career_tiering.TIER_STRETCH in tiers
        assert len(tiers[career_tiering.TIER_COMMON]) == 3

    def test_gemma_failure_falls_back(self, monkeypatch):
        monkeypatch.setattr(
            career_tiering.gemma_client, "generate", lambda **kw: ""
        )
        tiers = career_tiering.tier_careers(
            _outcomes_8(), "Test U", "Marketing", "52.14"
        )
        assert "All career paths" in tiers
        assert len(tiers["All career paths"]) == 8

    def test_prompt_includes_school_and_all_socs(self, monkeypatch):
        captured: dict = {}

        def capture(**kw):
            captured.update(kw)
            return ""

        monkeypatch.setattr(career_tiering.gemma_client, "generate", capture)
        outcomes = _outcomes_8()
        career_tiering.tier_careers(outcomes, "IU-B", "Marketing", "52.14")
        user = captured["user"]
        assert "IU-B" in user
        assert "Marketing" in user
        assert "52.14" in user
        for outcome in outcomes:
            assert outcome.soc_code in user

    def test_empty_tiers_pruned(self, monkeypatch):
        fake = (
            "COMMON\n11-2021\n13-1161\n11-2022\n13-1131\n"
            "11-2011\n27-3031\n11-3011\n13-1199\n"
            "LESS_COMMON\n"
            "STRETCH\n"
        )
        monkeypatch.setattr(
            career_tiering.gemma_client, "generate", lambda **kw: fake
        )
        tiers = career_tiering.tier_careers(
            _outcomes_8(), "Test U", "Marketing", "52.14"
        )
        assert career_tiering.TIER_LESS_COMMON not in tiers
        assert career_tiering.TIER_STRETCH not in tiers
        assert len(tiers[career_tiering.TIER_COMMON]) == 8
