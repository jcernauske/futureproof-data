"""Tests for the v4 blender in src/gold/ai_exposure_transformer.py.

Covers the 4-cell blending truth table (Gemma × Karpathy), union
coverage, category derivation from SOC major group, required-field
stamping (record_id + promoted_at), model_tag pass-through, and the
fail-closed A/B gate enforcement at promote time.
"""

import datetime
import json

import pytest

from gold.ai_exposure_transformer import (
    AB_OVERRIDE_ENV,
    SOC_MAJOR_GROUP_TO_CATEGORY,
    _check_ab_gate,
    _gemma_has_score,
    blend_scores,
    compute_boss_ai_score,
    compute_stat_res,
    derive_category,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime.datetime(2026, 4, 16, 12, 0, 0, tzinfo=datetime.timezone.utc)


def _gemma_row(
    soc="13-2051",
    exposure=7,
    title="Financial Analysts",
    rationale="Financial analysts build models and process data.",
    automatable='["Data aggregation", "Report generation"]',
    human='["Client relationship management"]',
    model_tag="gemma4:26b-a4b",
    error=None,
):
    return {
        "soc_code_normalized": soc,
        "soc_code": soc,
        "primary_title": title,
        "exposure_score": exposure,
        "rationale": rationale,
        "task_breakdown_automatable": automatable,
        "task_breakdown_human": human,
        "scoring_model": "gemma-4",
        "model_tag": model_tag,
        "error": error,
    }


def _karpathy_row(
    soc="13-2051",
    exposure=8,
    title="Financial analysts",
    category="business-and-financial",
    rationale="Karpathy's baseline rationale for financial analysts.",
):
    return {
        "soc_code": soc,
        "occupation_title": title,
        "exposure_score": exposure,
        "rationale": rationale,
        "category": category,
        "bls_match": True,
    }


# ---------------------------------------------------------------------------
# Blending truth table
# ---------------------------------------------------------------------------


class TestBlendingTruthTable:
    """All 4 cells of the Gemma × Karpathy truth table."""

    def test_gemma_plus_karpathy_uses_gemma(self):
        """Both present → Gemma wins; Karpathy score is preserved for A/B."""
        gemma = {"13-2051": _gemma_row(exposure=7)}
        karpathy = {"13-2051": _karpathy_row(exposure=8)}
        rows = blend_scores(gemma, karpathy, NOW)
        assert len(rows) == 1
        r = rows[0]
        assert r["exposure_score"] == 7
        assert r["scoring_model"] == "gemma-4"
        assert r["karpathy_score"] == 8
        assert r["model_tag"] == "gemma4:26b-a4b"

    def test_gemma_only_uses_gemma_with_soc_category(self):
        """Gemma-only → Gemma wins; category derived from SOC 2018 major group."""
        gemma = {"13-2051": _gemma_row(exposure=7)}
        rows = blend_scores(gemma, {}, NOW)
        assert len(rows) == 1
        r = rows[0]
        assert r["scoring_model"] == "gemma-4"
        assert r["karpathy_score"] is None
        assert r["category"] == "business-and-financial"  # 13 -> business

    def test_karpathy_only_uses_karpathy(self):
        """Gemma missing, Karpathy present → Karpathy wins."""
        karpathy = {"15-1252": _karpathy_row(
            soc="15-1252",
            exposure=8,
            title="Software Developers",
            category="computer-and-mathematical",
        )}
        rows = blend_scores({}, karpathy, NOW)
        assert len(rows) == 1
        r = rows[0]
        assert r["exposure_score"] == 8
        assert r["scoring_model"] == "gemini-flash"
        assert r["model_tag"] is None
        assert r["karpathy_score"] == 8
        assert r["task_breakdown_automatable"] is None

    def test_both_missing_excludes_row(self):
        """Gemma and Karpathy both missing → row excluded."""
        assert blend_scores({}, {}, NOW) == []

    def test_gemma_error_row_falls_through_to_karpathy(self):
        """Gemma error row is treated as missing — Karpathy takes over."""
        gemma = {"13-2051": _gemma_row(error="Failed after 3 attempts")}
        karpathy = {"13-2051": _karpathy_row(exposure=8)}
        rows = blend_scores(gemma, karpathy, NOW)
        assert len(rows) == 1
        assert rows[0]["scoring_model"] == "gemini-flash"
        assert rows[0]["exposure_score"] == 8

    def test_gemma_null_score_falls_through_to_karpathy(self):
        """Gemma row with None exposure_score is treated as missing."""
        gemma = {"13-2051": _gemma_row(exposure=None)}
        karpathy = {"13-2051": _karpathy_row(exposure=8)}
        rows = blend_scores(gemma, karpathy, NOW)
        assert rows[0]["scoring_model"] == "gemini-flash"


# ---------------------------------------------------------------------------
# Union coverage
# ---------------------------------------------------------------------------


class TestUnionCoverage:
    """Output covers Gemma ∪ Karpathy SOCs."""

    def test_union_of_disjoint_sources(self):
        gemma = {"13-2051": _gemma_row(soc="13-2051")}
        karpathy = {"15-1252": _karpathy_row(
            soc="15-1252", category="computer-and-mathematical"
        )}
        rows = blend_scores(gemma, karpathy, NOW)
        socs = {r["soc_code"] for r in rows}
        assert socs == {"13-2051", "15-1252"}

    def test_union_of_overlapping_sources(self):
        """Overlap counts once, with Gemma preferred."""
        gemma = {
            "13-2051": _gemma_row(soc="13-2051"),
            "15-1252": _gemma_row(
                soc="15-1252", exposure=6, title="Software Developers"
            ),
        }
        karpathy = {
            "13-2051": _karpathy_row(),
            "29-1141": _karpathy_row(
                soc="29-1141", exposure=3,
                title="Registered Nurses",
                category="healthcare-practitioners-and-technical",
            ),
        }
        rows = blend_scores(gemma, karpathy, NOW)
        socs = {r["soc_code"] for r in rows}
        assert socs == {"13-2051", "15-1252", "29-1141"}

        # Spot-check Gemma wins on overlap
        fin = next(r for r in rows if r["soc_code"] == "13-2051")
        assert fin["scoring_model"] == "gemma-4"

        # Karpathy-only row comes through as fallback
        rn = next(r for r in rows if r["soc_code"] == "29-1141")
        assert rn["scoring_model"] == "gemini-flash"


# ---------------------------------------------------------------------------
# Record ID + promoted_at stamping
# ---------------------------------------------------------------------------


class TestRecordIdAndPromotedAt:
    """Blender must stamp record_id and promoted_at on every row."""

    def test_every_row_has_record_id(self):
        gemma = {"13-2051": _gemma_row()}
        rows = blend_scores(gemma, {}, NOW)
        for r in rows:
            assert r["record_id"].startswith("aie-")
            assert len(r["record_id"]) > len("aie-")

    def test_every_row_has_promoted_at(self):
        gemma = {"13-2051": _gemma_row()}
        rows = blend_scores(gemma, {}, NOW)
        assert rows[0]["promoted_at"] == NOW

    def test_record_id_deterministic(self):
        """Same SOC → same record_id (stable across runs)."""
        gemma1 = {"13-2051": _gemma_row()}
        gemma2 = {"13-2051": _gemma_row(exposure=9)}  # different score, same SOC
        rows1 = blend_scores(gemma1, {}, NOW)
        rows2 = blend_scores(gemma2, {}, NOW)
        assert rows1[0]["record_id"] == rows2[0]["record_id"]


# ---------------------------------------------------------------------------
# Category derivation
# ---------------------------------------------------------------------------


class TestDeriveCategory:
    """derive_category prefers Karpathy, else SOC 2018 major group."""

    def test_karpathy_category_preferred(self):
        assert (
            derive_category("13-2051", "business-and-financial")
            == "business-and-financial"
        )

    def test_soc_major_group_fallback(self):
        """No Karpathy → derive from SOC 2018 major group (first 2 digits).

        Vocabulary matches Karpathy's (single ``healthcare`` bucket;
        ``education-training-and-library`` not the BLS label).
        """
        assert derive_category("29-1141", None) == "healthcare"
        assert derive_category("31-9092", None) == "healthcare"  # collapses
        assert derive_category("25-2021", None) == "education-training-and-library"
        assert derive_category("15-1252", None) == "computer-and-mathematical"
        assert derive_category("55-1011", None) == "military"

    def test_unknown_karpathy_falls_back(self):
        """derive_category treats the literal 'Unknown' as missing."""
        assert derive_category("15-1252", "Unknown") == "computer-and-mathematical"

    def test_unknown_major_group_returns_other(self):
        """Unrecognized SOC prefix → 'other' (not 'Unknown')."""
        assert derive_category("99-9999", None) == "other"

    def test_all_22_major_groups_cover_category(self):
        """Every listed SOC 2018 major group returns a non-'other' category."""
        for prefix in SOC_MAJOR_GROUP_TO_CATEGORY:
            cat = derive_category(f"{prefix}-0000", None)
            assert cat != "other"
            assert cat != "Unknown"


# ---------------------------------------------------------------------------
# Invariants on blended rows
# ---------------------------------------------------------------------------


class TestBlendedRowInvariants:
    """stat_res and boss_ai_score must match the shipped formulas."""

    @pytest.mark.parametrize("exposure", [0, 1, 5, 7, 10])
    def test_stat_res_matches_formula(self, exposure):
        gemma = {"13-2051": _gemma_row(exposure=exposure)}
        rows = blend_scores(gemma, {}, NOW)
        assert rows[0]["stat_res"] == compute_stat_res(exposure)

    @pytest.mark.parametrize("exposure", [0, 1, 5, 7, 10])
    def test_boss_ai_score_matches_formula(self, exposure):
        gemma = {"13-2051": _gemma_row(exposure=exposure)}
        rows = blend_scores(gemma, {}, NOW)
        assert rows[0]["boss_ai_score"] == compute_boss_ai_score(exposure)

    def test_inverse_invariant_holds(self):
        """stat_res + boss_ai_score = 11 for all exposure ≥ 1."""
        for exposure in range(1, 11):
            gemma = {f"13-205{exposure}": _gemma_row(
                soc=f"13-205{exposure}", exposure=exposure
            )}
            rows = blend_scores(gemma, {}, NOW)
            r = rows[0]
            assert r["stat_res"] + r["boss_ai_score"] == 11


class TestGemmaHasScoreBoolGuard:
    """`_gemma_has_score` rejects bool exposure_score (bool ⊂ int)."""

    def test_int_score_accepted(self):
        assert _gemma_has_score(_gemma_row(exposure=7))

    def test_none_rejected(self):
        assert not _gemma_has_score(_gemma_row(exposure=None))

    def test_bool_rejected(self):
        """``isinstance(True, int)`` is True — guard against bool."""
        assert not _gemma_has_score(_gemma_row(exposure=True))
        assert not _gemma_has_score(_gemma_row(exposure=False))

    def test_error_row_rejected(self):
        assert not _gemma_has_score(_gemma_row(exposure=7, error="oops"))


# ---------------------------------------------------------------------------
# A/B gate enforcement (M2 fix)
# ---------------------------------------------------------------------------


class TestAbGateEnforcement:
    """`_check_ab_gate` blocks the promote when overall_pass is False."""

    def _write_report(self, project_dir, overall_pass: bool, gates: dict | None = None):
        report_dir = project_dir / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "gemma_vs_karpathy_comparison.json"
        report_path.write_text(json.dumps({
            "overall_pass": overall_pass,
            "gates": gates or {},
            "outliers": [],
        }))

    def test_missing_report_proceeds_with_warning(self, tmp_path, caplog):
        """No report → log warning, allow promote."""
        with caplog.at_level("WARNING"):
            _check_ab_gate(tmp_path)
        assert "A/B comparison report not found" in caplog.text

    def test_pass_report_proceeds(self, tmp_path):
        """overall_pass=True → no exception."""
        self._write_report(tmp_path, overall_pass=True)
        _check_ab_gate(tmp_path)

    def test_fail_report_blocks_promote(self, tmp_path, monkeypatch):
        """overall_pass=False with no override → RuntimeError."""
        monkeypatch.delenv(AB_OVERRIDE_ENV, raising=False)
        self._write_report(tmp_path, overall_pass=False, gates={
            "correlation": {"pass": False, "value": 0.3},
        })
        with pytest.raises(RuntimeError, match="overall_pass=False"):
            _check_ab_gate(tmp_path)

    def test_override_env_allows_failed_promote(self, tmp_path, monkeypatch, caplog):
        """AI_EXPOSURE_AB_OVERRIDE=1 → loud warning, no exception."""
        monkeypatch.setenv(AB_OVERRIDE_ENV, "1")
        self._write_report(tmp_path, overall_pass=False, gates={
            "correlation": {"pass": False, "value": 0.3},
        })
        with caplog.at_level("WARNING"):
            _check_ab_gate(tmp_path)
        assert "AI_EXPOSURE_AB_OVERRIDE=1" in caplog.text

    def test_corrupted_report_does_not_crash(self, tmp_path, caplog):
        """Garbage JSON → log warning, allow promote (don't block on infra)."""
        report_dir = tmp_path / "reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "gemma_vs_karpathy_comparison.json").write_text("not json {")
        with caplog.at_level("WARNING"):
            _check_ab_gate(tmp_path)
        assert "unreadable" in caplog.text

    def test_failed_gate_names_in_error(self, tmp_path, monkeypatch):
        """Error message lists the specific failed gates."""
        monkeypatch.delenv(AB_OVERRIDE_ENV, raising=False)
        self._write_report(tmp_path, overall_pass=False, gates={
            "correlation": {"pass": False},
            "mean_absolute_diff": {"pass": True},
            "mode_collapse": {"pass": False},
        })
        with pytest.raises(RuntimeError, match="correlation.*mode_collapse"):
            _check_ab_gate(tmp_path)
