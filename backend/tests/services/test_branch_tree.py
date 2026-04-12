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
