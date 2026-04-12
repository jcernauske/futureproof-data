"""Tests for markdown report generation."""

from __future__ import annotations

from app.models.career import (
    AppliedSkill,
    BossFightResult,
    BossScores,
    Build,
    CareerBranch,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
    SkillRec,
)
from app.services import report_gen


def _career() -> CareerOutcome:
    return CareerOutcome(
        unitid=151351,
        institution_name="Indiana University-Bloomington",
        cipcode="52.14",
        program_name="Marketing",
        soc_code="11-2021",
        occupation_title="Marketing Managers",
        stats=PentagonStats(ern=8, roi=7, res=4, grw=6, hmn=7),
        bosses=BossScores(ai=7, loans=4, market=6, burnout=5, ceiling=8),
        median_annual_wage=161030.0,
        education_level_name="Bachelor's degree",
    )


def _gauntlet() -> GauntletResult:
    return GauntletResult(
        fights=[
            BossFightResult(
                boss="ai",  # type: ignore[arg-type]
                label="Fight AI",
                result="draw",  # type: ignore[arg-type]
                raw_score=11,
                threshold_win=14,
                threshold_draw=10,
                reason="RES 4 + HMN 7 = 11",
                narrative="IU-B marketing grads face moderate AI risk.",
                rerolled=True,
                reroll_count=1,
                original_result="lose",
                original_raw_score=8,
            ),
            BossFightResult(
                boss="loans",  # type: ignore[arg-type]
                label="Fight Student Loans",
                result="win",  # type: ignore[arg-type]
                raw_score=7,
                threshold_win=7,
                threshold_draw=5,
                reason="ROI 7",
                narrative="Kelley's ROI is strong.",
            ),
        ],
        wins=1,
        losses=0,
        draws=1,
        unknown=0,
        verdict="SOLID BUILD with one soft spot.",
    )


def _build() -> Build:
    return Build(
        build_id="iub-marketing-001",
        created_at="2026-04-12T00:00:00Z",
        school_name="Indiana University-Bloomington",
        unitid=151351,
        major_text="Marketing",
        cipcode="52.14",
        program_name="Marketing",
        effort="balanced",
        loan_pct=1.0,
        career=_career(),
        gauntlet=_gauntlet(),
        branches=[
            CareerBranch(
                from_soc="11-2021",
                to_soc="11-2022",
                to_title="Sales Managers",
                delta_ern=2,
                unlock="3 years experience",
            )
        ],
        skill_recs=[
            SkillRec(
                title="Data Analytics Minor",
                stat_impact="RES+2",
                rationale="Helps direct AI tools.",
            )
        ],
        guidance="IU-B Marketing points toward strong careers.",
        skills_crafted=[
            AppliedSkill(
                id="ai_kelley_analytics",
                title="Kelley Analytics Certificate",
                rationale="Direct AI tools at Kelley.",
                targets=["ai"],
                delta_res=2,
            )
        ],
    )


class TestBuildReport:
    def test_generates_markdown_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        path = report_gen.generate_build_report(_build())
        assert path.exists()
        assert path.suffix == ".md"

    def test_contains_header_fields(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Indiana University-Bloomington" in content
        assert "Marketing" in content
        assert "Marketing Managers" in content
        assert "$161,030" in content
        assert "Bachelor's degree" in content

    def test_contains_stats_table(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Earning Power (ERN)" in content
        assert "8/10" in content
        assert "AI Resilience (RES)" in content
        assert "4/10" in content

    def test_contains_guidance(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "IU-B Marketing points toward" in content

    def test_contains_boss_fights(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Fight AI" in content
        assert "DRAW" in content
        assert "Fight Student Loans" in content
        assert "WIN" in content

    def test_contains_reroll_info(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Rerolled" in content
        assert "LOSE" in content
        assert "Kelley Analytics Certificate" in content

    def test_contains_skills_crafted(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Skills Crafted" in content
        assert "RES +2" in content

    def test_contains_branches(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Sales Managers" in content
        assert "11-2022" in content
        assert "3 years experience" in content

    def test_contains_skill_recs(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Data Analytics Minor" in content
        assert "RES+2" in content

    def test_contains_disclaimers(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        content = report_gen.generate_build_report(_build()).read_text()
        assert "Disclaimers" in content
        assert "not replace" in content.lower()

    def test_filename_includes_school_and_major(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        path = report_gen.generate_build_report(_build())
        assert "indiana" in path.name.lower()
        assert "marketing" in path.name.lower()

    def test_no_skills_crafted_section_when_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        build = _build()
        build.skills_crafted = []
        content = report_gen.generate_build_report(build).read_text()
        assert "Skills Crafted" not in content


class TestComparisonReport:
    def test_generates_comparison_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        comparison = {
            "builds": [
                {
                    "build_id": "a-001",
                    "label": "IU-B — Marketing",
                    "career": "Mktg Mgrs",
                },
                {
                    "build_id": "b-001",
                    "label": "Purdue — CS",
                    "career": "Software Devs",
                },
            ],
            "stats": [
                {"label": "ERN", "values": [8, 9]},
                {"label": "ROI", "values": [7, 6]},
            ],
            "bosses": [
                {"label": "AI", "values": ["DRAW", "WIN"]},
                {"label": "Loans", "values": ["WIN", "LOSE"]},
            ],
        }
        path = report_gen.generate_comparison_report(comparison, [])
        assert path.exists()
        assert "compare_" in path.name
        content = path.read_text()
        assert "IU-B — Marketing" in content
        assert "Purdue — CS" in content
        assert "8" in content
        assert "DRAW" in content

    def test_includes_branch_previews_with_full_builds(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(report_gen, "_reports_dir", lambda: tmp_path)
        comparison = {
            "builds": [
                {"build_id": "a", "label": "IU-B — Mktg", "career": "Mktg"},
            ],
            "stats": [{"label": "ERN", "values": [8]}],
            "bosses": [{"label": "AI", "values": ["WIN"]}],
        }
        path = report_gen.generate_comparison_report(
            comparison, [_build()]
        )
        content = path.read_text()
        assert "Sales Managers" in content
        assert "Career Branch Previews" in content
