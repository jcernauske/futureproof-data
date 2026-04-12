"""Tests for skill_recs parser + fallback path."""

from __future__ import annotations

from app.models.career import (
    BossFightResult,
    BossScores,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import skill_recs


def _career() -> CareerOutcome:
    return CareerOutcome(
        unitid=1,
        institution_name="Test",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="11-2021",
        occupation_title="Marketing Managers",
        stats=PentagonStats(ern=8, roi=9, res=3, grw=6, hmn=7),
        bosses=BossScores(ai=7, loans=2, market=6, burnout=5, ceiling=8),
    )


def _gauntlet_with_ai_loss() -> GauntletResult:
    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="lose",  # type: ignore[arg-type]
                raw_score=10,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 3 + HMN 7 = 10",
            )
        ],
        wins=0,
        losses=1,
        draws=0,
        unknown=0,
        verdict="x",
    )


class TestGenerateRecs:
    def test_parses_pipe_delimited_lines(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kwargs: (
                "Data Analytics Minor | RES+2 | Learn to direct AI analysis.\n"
                "Internship | HMN+1 | Real-world practice.\n"
                "Strategy Course | HMN+1 | Strategic thinking is human-only.\n"
            ),
        )
        recs = skill_recs.generate_recs(_career(), _gauntlet_with_ai_loss())
        assert len(recs) == 3
        assert recs[0].title == "Data Analytics Minor"
        assert recs[0].stat_impact == "RES+2"
        assert "direct AI analysis" in recs[0].rationale

    def test_fallback_when_gemma_empty(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(gemma_client, "generate", lambda **kwargs: "")
        recs = skill_recs.generate_recs(_career(), _gauntlet_with_ai_loss())
        assert len(recs) >= 3
        assert all(rec.stat_impact for rec in recs)

    def test_fallback_when_parser_cant_find_lines(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kwargs: "here are some recommendations for you",
        )
        recs = skill_recs.generate_recs(_career(), _gauntlet_with_ai_loss())
        assert len(recs) >= 3  # fallback


class TestClampImpact:
    """Belt-and-suspenders: the system prompt now tells Gemma to cap
    at +2/+3, but the parser enforces the ceiling regardless. No
    single workshop claims to boost a stat by half the 1-10 scale."""

    def test_plus_two_passes_through(self):
        assert skill_recs._clamp_impact("RES+2") == "RES+2"

    def test_plus_three_passes_through(self):
        """+3 is legitimate for major commitments (full minor, cert)."""
        assert skill_recs._clamp_impact("ROI+3") == "ROI+3"

    def test_plus_four_clamps_to_two(self):
        assert skill_recs._clamp_impact("HMN+4") == "HMN+2"

    def test_plus_five_clamps_to_two(self):
        assert skill_recs._clamp_impact("ROI+5") == "ROI+2"

    def test_ten_clamps_to_two(self):
        """Absurd magnitudes still clamp, don't crash."""
        assert skill_recs._clamp_impact("GRW+10") == "GRW+2"

    def test_negative_passes_through(self):
        """Negative deltas are rare but legitimate; no clamping."""
        assert skill_recs._clamp_impact("GRW-1") == "GRW-1"

    def test_bare_number_normalizes_sign(self):
        """Gemma occasionally omits the + sign."""
        assert skill_recs._clamp_impact("RES2") == "RES+2"

    def test_plus_four_bare_clamps(self):
        assert skill_recs._clamp_impact("RES4") == "RES+2"

    def test_spaces_and_lowercase_normalize(self):
        assert skill_recs._clamp_impact("res + 2") == "RES+2"
        assert skill_recs._clamp_impact("res + 5") == "RES+2"

    def test_unparseable_returns_cleaned(self):
        """Defensive: if the regex doesn't match, return cleaned raw."""
        assert skill_recs._clamp_impact("INVALID+2") == "INVALID+2"

    def test_end_to_end_clamps_in_generate_recs(self, monkeypatch):
        from app.services import gemma_client

        monkeypatch.setattr(
            gemma_client,
            "generate",
            lambda **kwargs: (
                "Data Minor | RES+5 | Would have said +5 before the clamp.\n"
                "Internship | HMN+4 | Another inflated claim.\n"
                "Capstone Project | HMN+2 | Legitimate +2.\n"
            ),
        )
        recs = skill_recs.generate_recs(_career(), _gauntlet_with_ai_loss())
        assert len(recs) == 3
        impacts = [r.stat_impact for r in recs]
        assert impacts[0] == "RES+2"  # clamped from +5
        assert impacts[1] == "HMN+2"  # clamped from +4
        assert impacts[2] == "HMN+2"  # unchanged
