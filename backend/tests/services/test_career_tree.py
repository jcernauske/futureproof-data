"""Tests for the career tree spike."""

from __future__ import annotations

from app.models.career import (
    BossFightResult,
    BossScores,
    Build,
    CareerOutcome,
    GauntletResult,
    PentagonStats,
)
from app.services import career_tree


def _build(soc: str = "27-2011", title: str = "Actors") -> Build:
    return Build(
        build_id="test-001",
        created_at="2026-04-12T00:00:00Z",
        school_name="Millikin",
        unitid=147244,
        major_text="Acting",
        cipcode="50.05",
        program_name="Drama",
        effort="balanced",
        career=CareerOutcome(
            unitid=147244,
            institution_name="Millikin",
            cipcode="50.05",
            program_name="Drama",
            soc_code=soc,
            occupation_title=title,
            stats=PentagonStats(ern=3, roi=4, res=4, grw=5, hmn=9),
            bosses=BossScores(ai=6, loans=7, market=5, burnout=3, ceiling=4),
            median_annual_wage=55600.0,
        ),
        gauntlet=GauntletResult(
            fights=[
                BossFightResult(
                    boss="ai",  # type: ignore[arg-type]
                    label="Fight AI",
                    result="draw",  # type: ignore[arg-type]
                    raw_score=13,
                    threshold_win=14,
                    threshold_draw=10,
                    reason="test",
                )
            ],
            wins=0,
            losses=0,
            draws=1,
            unknown=0,
            verdict="TEST",
        ),
        branches=[],
        skill_recs=[],
        guidance="test",
    )


def _mock_branches(monkeypatch, branch_map: dict):
    """Patch mcp_client.call to return synthetic branch data.

    ``branch_map`` maps soc_code to a list of tuples. Tuples may be
    either the legacy 5-ary ``(related_soc, related_title, grw, hmn, res)``
    form, or the experience-aware 7-ary
    ``(related_soc, related_title, grw, hmn, res, exp_years, exp_tier)``
    form. When the shorter form is used, experience fields are omitted
    from the row dict entirely (simulating pre-v1.2.0 responses).
    """
    from app.services import mcp_client

    def fake_call(tool, args):
        if tool != "get_career_branches":
            return {"data": []}
        soc = args.get("soc_code", "")
        branches = branch_map.get(soc, [])
        rows = []
        for b in branches:
            row = {
                "soc_code": soc,
                "related_soc_code": b[0],
                "related_title": b[1],
                "related_grw": b[2],
                "related_hmn": b[3],
                "related_res": b[4],
                "related_wage": 60000.0,
                "related_burnout": 5,
                "related_ai_boss": 5,
                "related_education_level": "Bachelor's",
                "best_index": 2,
            }
            if len(b) >= 7:
                row["related_experience_years"] = b[5]
                row["related_experience_tier"] = b[6]
            rows.append(row)
        return {"data": rows}

    monkeypatch.setattr(mcp_client, "call", fake_call)


class TestBuildTree:
    def test_root_node_has_build_stats(self, monkeypatch):
        _mock_branches(monkeypatch, {})
        root, stats = career_tree.build_tree(_build(), max_depth=1)
        assert root.soc_code == "27-2011"
        assert root.ern == 3
        assert root.roi == 4
        assert root.hmn == 9
        assert root.level == 0

    def test_expands_one_level(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4),
                ("27-2032", "Choreographers", 7, 10, 9),
            ],
        })
        root, stats = career_tree.build_tree(_build(), max_depth=1)
        assert len(root.children) == 2
        assert root.children[0].soc_code == "27-2012"
        assert root.children[0].grw == 6
        assert root.children[0].level == 1
        assert stats.total_nodes == 3
        assert stats.max_depth_reached == 1

    def test_expands_multiple_levels(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [("27-2012", "Producers", 6, 5, 4)],
            "27-2012": [("11-1021", "Gen Managers", 6, 6, 3)],
            "11-1021": [("11-1011", "CEOs", 5, 8, 2)],
        })
        root, stats = career_tree.build_tree(_build(), max_depth=3)
        assert len(root.children) == 1
        assert len(root.children[0].children) == 1
        assert len(root.children[0].children[0].children) == 1
        assert stats.max_depth_reached == 3
        assert stats.total_nodes == 4

    def test_prunes_cycles(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [("27-2012", "Producers", 6, 5, 4)],
            "27-2012": [("27-2011", "Actors (cycle)", 5, 9, 4)],
        })
        root, stats = career_tree.build_tree(_build(), max_depth=3)
        assert len(root.children) == 1
        assert len(root.children[0].children) == 0

    def test_prunes_duplicates_across_branches(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4),
                ("27-2032", "Choreographers", 7, 10, 9),
            ],
            "27-2012": [("11-1021", "Managers", 6, 6, 3)],
            "27-2032": [("11-1021", "Managers Dup", 6, 6, 3)],
        })
        root, stats = career_tree.build_tree(_build(), max_depth=2)
        l2_socs = []
        for child in root.children:
            for grandchild in child.children:
                l2_socs.append(grandchild.soc_code)
        assert l2_socs.count("11-1021") == 1

    def test_dead_ends_counted(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4),
                ("27-2032", "Choreographers", 7, 10, 9),
            ],
            "27-2012": [],
            "27-2032": [],
        })
        root, stats = career_tree.build_tree(_build(), max_depth=2)
        assert stats.dead_ends == 2

    def test_respects_max_depth(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [("A", "A", 5, 5, 5)],
            "A": [("B", "B", 5, 5, 5)],
            "B": [("C", "C", 5, 5, 5)],
            "C": [("D", "D", 5, 5, 5)],
        })
        root, stats = career_tree.build_tree(_build(), max_depth=2)
        assert stats.max_depth_reached == 2

    def test_boss_results_computed(self, monkeypatch):
        _mock_branches(monkeypatch, {})
        root, _ = career_tree.build_tree(_build(), max_depth=1)
        assert root.boss_ai in ("win", "lose", "draw", "unknown")
        assert root.boss_market in ("win", "lose", "draw", "unknown")

    def test_roi_inherited_from_build(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [("27-2012", "Producers", 6, 5, 4)],
        })
        root, _ = career_tree.build_tree(_build(), max_depth=1)
        child = root.children[0]
        assert child.roi == root.roi == 4
        assert child.ern is None

    def test_build_tree_carries_relatedness(self, monkeypatch):
        """T2.2 (backend): TreeNode.relatedness is populated from
        ``best_index`` on the branch row via ``as_int``. Confirms the
        propagation chain Gold → MCP row → TreeNode.

        Root never carries a relatedness rank (it has no parent to be
        related to). Children inherit the rank from the row's
        ``best_index`` field.
        """
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4),
                ("27-2032", "Choreographers", 7, 10, 9),
            ],
        })
        root, _ = career_tree.build_tree(_build(), max_depth=1)

        # Root has no parent → relatedness stays None.
        assert root.relatedness is None

        # Children pick up ``best_index`` = 2 from the fixture (already
        # int, not float — so as_int passes it through unchanged).
        assert len(root.children) == 2
        assert root.children[0].relatedness == 2
        assert root.children[1].relatedness == 2

    def test_build_tree_relatedness_coerces_floats(self, monkeypatch):
        """DuckDB/Iceberg can return ``best_index`` as a float
        (e.g. 4.0). The TreeNode field is typed ``int | None``; the
        ``as_int`` coercion in expand() must round to int."""
        from app.services import mcp_client

        def fake_call(tool, args):
            if tool != "get_career_branches":
                return {"data": []}
            return {
                "data": [
                    {
                        "soc_code": "27-2011",
                        "related_soc_code": "27-2012",
                        "related_title": "Producers",
                        "related_grw": 6,
                        "related_hmn": 5,
                        "related_res": 4,
                        "related_wage": 60000.0,
                        "related_burnout": 5,
                        "related_ai_boss": 5,
                        "related_education_level": "Bachelor's",
                        "best_index": 4.0,  # float — must coerce to int
                    },
                ],
            }

        monkeypatch.setattr(mcp_client, "call", fake_call)
        root, _ = career_tree.build_tree(_build(), max_depth=1)
        assert root.children[0].relatedness == 4
        assert isinstance(root.children[0].relatedness, int)

    def test_build_tree_relatedness_null_when_best_index_missing(
        self, monkeypatch
    ):
        """Rows without ``best_index`` (legacy or partial data) leave
        ``TreeNode.relatedness`` as None — never a fabricated default."""
        from app.services import mcp_client

        def fake_call(tool, args):
            if tool != "get_career_branches":
                return {"data": []}
            return {
                "data": [
                    {
                        "soc_code": "27-2011",
                        "related_soc_code": "27-2012",
                        "related_title": "Producers",
                        "related_grw": 6,
                        "related_hmn": 5,
                        "related_res": 4,
                        "related_wage": 60000.0,
                        "related_burnout": 5,
                        "related_ai_boss": 5,
                        "related_education_level": "Bachelor's",
                        # NOTE: no best_index key
                    },
                ],
            }

        monkeypatch.setattr(mcp_client, "call", fake_call)
        root, _ = career_tree.build_tree(_build(), max_depth=1)
        assert root.children[0].relatedness is None


class TestExperienceFiltering:
    """onet-experience-requirements spec §Zone 5: experience-based
    gating on ``build_tree(max_experience_years=...)``."""

    def test_no_filter_returns_all_branches(self, monkeypatch):
        """Default behavior (no kwarg) is preserved — every branch with
        a valid related_soc is expanded regardless of experience."""
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4, 3.0, "early"),
                ("11-1011", "Chief Executives", 5, 8, 2, 12.0, "senior"),
                ("11-2011", "Ad Managers", 6, 6, 3, 7.0, "mid"),
            ],
        })
        root, stats = career_tree.build_tree(_build(), max_depth=1)
        assert len(root.children) == 3
        assert stats.total_nodes == 4

    def test_filter_excludes_branches_over_threshold(self, monkeypatch):
        """max_experience_years=5 skips Chief Executives (12y) and
        Ad Managers (7y); keeps Producers (3y)."""
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4, 3.0, "early"),
                ("11-1011", "Chief Executives", 5, 8, 2, 12.0, "senior"),
                ("11-2011", "Ad Managers", 6, 6, 3, 7.0, "mid"),
            ],
        })
        root, _ = career_tree.build_tree(
            _build(), max_depth=1, max_experience_years=5.0
        )
        titles = [c.title for c in root.children]
        assert titles == ["Producers"]

    def test_null_experience_never_filtered(self, monkeypatch):
        """NULL related_experience_years is treated as 'unknown' and
        MUST NOT be filtered out by ``max_experience_years``."""
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4, 3.0, "early"),
                ("99-9999", "Rare Occupation", 5, 5, 5, None, None),
                ("11-1011", "Chief Executives", 5, 8, 2, 12.0, "senior"),
            ],
        })
        root, _ = career_tree.build_tree(
            _build(), max_depth=1, max_experience_years=5.0
        )
        titles = sorted(c.title for c in root.children)
        # Producers (3y) kept; Rare Occupation (NULL) kept; CEO (12y) dropped
        assert titles == ["Producers", "Rare Occupation"]

    def test_tree_node_has_experience_fields(self, monkeypatch):
        """TreeNode.experience_years / experience_tier should be
        populated from the branch row."""
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4, 3.0, "early"),
            ],
        })
        root, _ = career_tree.build_tree(_build(), max_depth=1)
        child = root.children[0]
        assert child.experience_years == 3.0
        assert child.experience_tier == "early"

    def test_tree_node_experience_null_when_row_has_no_experience(
        self, monkeypatch
    ):
        """Legacy rows without the new keys leave TreeNode fields None."""
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4),  # 5-ary: no experience
            ],
        })
        root, _ = career_tree.build_tree(_build(), max_depth=1)
        child = root.children[0]
        assert child.experience_years is None
        assert child.experience_tier is None

    def test_root_node_experience_unset(self, monkeypatch):
        """Root derives from Build.career, not a branch row, so
        experience fields stay None at level 0."""
        _mock_branches(monkeypatch, {})
        root, _ = career_tree.build_tree(_build(), max_depth=0)
        assert root.experience_years is None
        assert root.experience_tier is None

    def test_filter_does_not_filter_at_boundary(self, monkeypatch):
        """``max_experience_years=5`` keeps branches at exactly 5 years
        (condition is strictly greater-than, not greater-than-or-equal)."""
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("11-2011", "Ad Managers", 6, 6, 3, 5.0, "mid"),
            ],
        })
        root, _ = career_tree.build_tree(
            _build(), max_depth=1, max_experience_years=5.0
        )
        assert len(root.children) == 1

    def test_zero_max_experience_filters_most_senior(self, monkeypatch):
        """Extreme filter: only entry-level (0y) branches pass."""
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("41-2031", "Retail Salespersons", 4, 7, 3, 0.75, "entry"),
                ("11-1011", "Chief Executives", 5, 8, 2, 12.0, "senior"),
            ],
        })
        root, _ = career_tree.build_tree(
            _build(), max_depth=1, max_experience_years=0.0
        )
        # 0.75 > 0 and 12.0 > 0 — both filtered
        assert len(root.children) == 0


class TestRenderTree:
    def test_renders_root_only(self, monkeypatch):
        _mock_branches(monkeypatch, {})
        root, _ = career_tree.build_tree(_build(), max_depth=0)
        text = career_tree.render_tree(root)
        assert "Actors" in text
        assert "ERN 3" in text

    def test_renders_children_with_connectors(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [
                ("27-2012", "Producers", 6, 5, 4),
                ("27-2032", "Choreographers", 7, 10, 9),
            ],
        })
        root, _ = career_tree.build_tree(_build(), max_depth=1)
        text = career_tree.render_tree(root)
        assert "├── Producers" in text
        assert "└── Choreographers" in text


class TestFormatSummary:
    def test_summary_contains_key_metrics(self, monkeypatch):
        _mock_branches(monkeypatch, {
            "27-2011": [("27-2012", "Producers", 6, 5, 4)],
            "27-2012": [],
        })
        _, stats = career_tree.build_tree(_build(), max_depth=2)
        summary = career_tree.format_summary(stats)
        assert "Total nodes" in summary
        assert "Dead ends" in summary
        assert "MCP lookups" in summary
        assert "Data coverage" in summary
        assert "Wall clock" in summary
        assert "ms" in summary
