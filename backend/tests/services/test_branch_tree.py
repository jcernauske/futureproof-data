"""Tests for branch_tree — row mapping and delta derivation."""

from __future__ import annotations

from app.services import branch_tree


def _stub_mcp(monkeypatch, rows):
    from app.services import mcp_client

    def fake_call(tool, args):
        assert tool == "get_career_branches"
        return {"data": rows}

    monkeypatch.setattr(mcp_client, "call", fake_call)


class TestGetBranches:
    def test_maps_rows(self, monkeypatch):
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "11-2021",
                    "related_soc_code": "11-2011",
                    "related_title": "Advertising Managers",
                    "best_index": 0.95,
                    "relatedness_tier": "high",
                    "related_education_level": "Bachelor's",
                    "wage_delta": 25000,
                    "grw_delta": 1,
                    "hmn_delta": -1,
                    "res_delta": 0,
                },
            ],
        )
        branches = branch_tree.get_branches("11-2021")
        assert len(branches) == 1
        branch = branches[0]
        assert branch.to_soc == "11-2011"
        assert branch.to_title == "Advertising Managers"
        assert branch.delta_ern == 2  # wage_delta 25000 -> +2
        assert branch.delta_roi == 1
        assert branch.delta_grw == 1
        assert branch.delta_hmn == -1
        assert branch.delta_res == 0
        assert branch.unlock == "Bachelor's · high relatedness"

    def test_skips_rows_without_related_soc(self, monkeypatch):
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "11-2021",
                    "related_soc_code": None,
                    "related_title": "Foo",
                },
                {
                    "soc_code": "11-2021",
                    "related_soc_code": "11-2011",
                    "related_title": None,
                },
            ],
        )
        assert branch_tree.get_branches("11-2021") == []

    def test_empty_result(self, monkeypatch):
        _stub_mcp(monkeypatch, [])
        assert branch_tree.get_branches("11-2021") == []

    def test_negative_wage_delta_yields_negative_ern(self, monkeypatch):
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "11-2021",
                    "related_soc_code": "13-1161",
                    "related_title": "Market Research Analysts",
                    "wage_delta": -25000,
                }
            ],
        )
        branches = branch_tree.get_branches("11-2021")
        assert branches[0].delta_ern == -2
        assert branches[0].delta_roi == -1

    def test_small_wage_delta_zero(self, monkeypatch):
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "11-2021",
                    "related_soc_code": "13-1111",
                    "related_title": "Management Analysts",
                    "wage_delta": 2000,
                }
            ],
        )
        assert branch_tree.get_branches("11-2021")[0].delta_ern == 0


class TestExperiencePassthrough:
    """onet-experience-requirements spec §Zone 5: verify the three new
    experience fields flow from the MCP row dict through to CareerBranch.
    """

    def test_all_three_experience_fields_populated(self, monkeypatch):
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "15-1252",
                    "related_soc_code": "11-3021",
                    "related_title": "Computer and Information Systems Managers",
                    "related_experience_years": 7.0,
                    "related_experience_tier": "mid",
                    "source_experience_years": 3.0,
                    "experience_delta_years": 4.0,
                }
            ],
        )
        branch = branch_tree.get_branches("15-1252")[0]
        assert branch.experience_years == 7.0
        assert branch.experience_tier == "mid"
        assert branch.experience_delta == 4.0

    def test_experience_fields_null_when_missing(self, monkeypatch):
        """NULL on the row (missing O*NET ETE coverage) propagates to the
        model as None — never coerced to 0."""
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "15-1252",
                    "related_soc_code": "99-9999",
                    "related_title": "Rare Occupation",
                    "related_experience_years": None,
                    "related_experience_tier": None,
                    "experience_delta_years": None,
                }
            ],
        )
        branch = branch_tree.get_branches("15-1252")[0]
        assert branch.experience_years is None
        assert branch.experience_tier is None
        assert branch.experience_delta is None

    def test_experience_fields_absent_keys_are_none(self, monkeypatch):
        """Pre-v1.2.0 rows that don't carry experience keys at all still
        round-trip cleanly — guards backward compatibility."""
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "15-1252",
                    "related_soc_code": "11-3021",
                    "related_title": "CIS Managers",
                }
            ],
        )
        branch = branch_tree.get_branches("15-1252")[0]
        assert branch.experience_years is None
        assert branch.experience_tier is None
        assert branch.experience_delta is None

    def test_negative_experience_delta_preserved(self, monkeypatch):
        """A lateral/downshift branch (target requires less experience
        than source) surfaces as a negative delta."""
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "11-1011",
                    "related_soc_code": "15-1252",
                    "related_title": "Software Developers",
                    "related_experience_years": 7.0,
                    "related_experience_tier": "mid",
                    "source_experience_years": 12.0,
                    "experience_delta_years": -5.0,
                }
            ],
        )
        branch = branch_tree.get_branches("11-1011")[0]
        assert branch.experience_delta == -5.0

    def test_int_experience_years_coerced_to_float(self, monkeypatch):
        """MCP may surface integer-valued years (e.g. 3); model field is
        float and should coerce transparently."""
        _stub_mcp(
            monkeypatch,
            [
                {
                    "soc_code": "15-1252",
                    "related_soc_code": "11-3021",
                    "related_title": "CIS Managers",
                    "related_experience_years": 7,
                    "experience_delta_years": 4,
                }
            ],
        )
        branch = branch_tree.get_branches("15-1252")[0]
        assert branch.experience_years == 7.0
        assert isinstance(branch.experience_years, float)
        assert branch.experience_delta == 4.0
