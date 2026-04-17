"""Tests for the RES receipt scoring_model branching.

v4 of gemma-ai-exposure-rescore: the RES line changes based on
``career.scoring_model``. Gemma-scored rows surface an "AI-estimated"
disclaimer and the model tag; Karpathy fallback keeps the legacy
wording.
"""

from __future__ import annotations

from app.models.career import BossScores, CareerOutcome, PentagonStats
from app.services import receipts


def _career_with_provenance(
    scoring_model: str | None,
    model_tag: str | None = None,
) -> CareerOutcome:
    return CareerOutcome(
        unitid=151801,
        institution_name="Indiana State University",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="13-1131",
        occupation_title="Fundraisers",
        scoring_model=scoring_model,
        model_tag=model_tag,
        stats=PentagonStats(ern=7, roi=6, res=5, grw=6, hmn=6),
        bosses=BossScores(ai=6, loans=5, market=6, burnout=5, ceiling=5),
    )


class TestResReceiptByScoringModel:
    """RES receipt wording tracks the scoring_model provenance."""

    def test_gemma_scoring_model_shows_ai_estimated(self):
        career = _career_with_provenance(
            scoring_model="gemma-4", model_tag="gemma4:26b-a4b"
        )
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "Gemma" in res_line
        assert "AI-estimated" in res_line
        assert "gemma4:26b-a4b" in res_line

    def test_karpathy_scoring_model_uses_legacy_wording(self):
        career = _career_with_provenance(scoring_model="gemini-flash")
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "Karpathy" in res_line

    def test_missing_scoring_model_falls_back_to_karpathy(self):
        """Legacy rows without scoring_model keep the old wording."""
        career = _career_with_provenance(scoring_model=None)
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "Karpathy" in res_line

    def test_gemma_falls_back_to_default_tag_when_none(self):
        """Gemma row with scoring_model set but model_tag None shouldn't crash."""
        career = _career_with_provenance(scoring_model="gemma-4", model_tag=None)
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "Gemma" in res_line
        # Default tag placeholder when model_tag absent.
        assert "gemma-4" in res_line


class TestResReceiptCompositeMethod:
    """S4 v4: composite_method overrides the legacy scoring_model wording."""

    def _career(
        self,
        *,
        composite_method: str | None,
        velocity_label: str | None = None,
        ai_adoption_share: float | None = None,
    ) -> CareerOutcome:
        return CareerOutcome(
            unitid=151801,
            institution_name="Indiana State University",
            cipcode="52.14",
            program_name="Marketing",
            soc_code="13-1131",
            occupation_title="Fundraisers",
            scoring_model="gemma-4",
            model_tag="gemma4:26b-a4b",
            composite_method=composite_method,  # type: ignore[arg-type]
            velocity_label=velocity_label,  # type: ignore[arg-type]
            ai_adoption_share=ai_adoption_share,
            stats=PentagonStats(ern=7, roi=6, res=5, grw=6, hmn=6),
            bosses=BossScores(ai=6, loans=5, market=6, burnout=5, ceiling=5),
        )

    def test_three_signal_method_shows_composite_wording(self) -> None:
        career = self._career(
            composite_method="three_signal",
            velocity_label="accelerating",
            ai_adoption_share=0.25,
        )
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "Option B composite" in res_line
        assert "three_signal" in res_line
        assert "accelerating" in res_line
        # Share value rendered to 4dp
        assert "0.2500" in res_line

    def test_karpathy_only_method_uses_karpathy_wording(self) -> None:
        career = self._career(
            composite_method="karpathy_only", velocity_label="unknown"
        )
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "Karpathy AI exposure baseline" in res_line
        assert "Gemma unavailable" in res_line

    def test_gemma_only_method_uses_gemma_only_wording(self) -> None:
        career = self._career(composite_method="gemma_only", velocity_label="unknown")
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "no observed adoption data" in res_line

    def test_observed_override_also_shows_composite_wording(self) -> None:
        career = self._career(
            composite_method="observed_override",
            velocity_label="saturating",
            ai_adoption_share=0.9,
        )
        lines = receipts.stats_receipt(career, effort="balanced", loan_pct=1.0)
        res_line = next(line for line in lines if line.startswith("RES "))
        assert "observed_override" in res_line
        assert "saturating" in res_line
