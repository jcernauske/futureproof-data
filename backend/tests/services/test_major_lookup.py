"""Tests for ``app.services.major_lookup``.

The module is the deterministic backbone of the intent short-circuit —
if ``lookup_major`` silently returns None when it shouldn't (wrong cwd,
mangled YAML path, case sensitivity regression), the short-circuit
never fires and Bug B is back. These tests pin the contract:

* Exact ``major`` match, case-insensitive
* Alias match, case-insensitive
* Empty/whitespace input returns ``None``
* Unknown input returns ``None``
* Path resolution is cwd-independent (backend pytest vs root pytest)
* Cross-module consistency with ``FutureProofMCPServer._find_major_intent``
  for every entry in ``data/reference/major_to_cip.yaml`` — guards
  against the two copies of matching semantics drifting apart.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from app.services import major_lookup
from app.services.major_lookup import lookup_major

# Make the pipeline's ``mcp_server`` package importable from the backend
# venv so ``TestCrossModuleConsistency`` can invoke
# ``FutureProofMCPServer._find_major_intent``. The backend venv has
# ``backend/`` on sys.path (via the editable pth) but not ``src/``.
_SRC_PATH = (
    Path(__file__).resolve().parents[3] / "src"
)
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from mcp_server.futureproof_server import (  # noqa: E402  (src path insert first)
    FutureProofMCPServer,
)

# ---------------------------------------------------------------------------
# YAML fixture — loaded once at collection time for the parametrized P1 test.
# ---------------------------------------------------------------------------

_YAML_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "reference"
    / "major_to_cip.yaml"
)


def _load_yaml_entries() -> list[dict[str, Any]]:
    """Read the YAML once at import time so pytest can parametrize off it."""
    with _YAML_PATH.open() as f:
        raw = yaml.safe_load(f) or []
    assert isinstance(raw, list) and raw, (
        f"major_to_cip.yaml must be a non-empty list; got {type(raw).__name__}"
    )
    return [e for e in raw if isinstance(e, dict)]


_YAML_ENTRIES = _load_yaml_entries()


def _cross_module_ids() -> list[tuple[dict[str, Any], str]]:
    """Flatten every (entry, query_text) pair — major name + each alias."""
    out: list[tuple[dict[str, Any], str]] = []
    for entry in _YAML_ENTRIES:
        major = str(entry.get("major", ""))
        if major:
            out.append((entry, major))
        for alias in entry.get("aliases") or []:
            alias_str = str(alias)
            if alias_str:
                out.append((entry, alias_str))
    return out


# ---------------------------------------------------------------------------
# TestLookupMajor — P0
# ---------------------------------------------------------------------------


class TestLookupMajor:
    """Core behavior of ``lookup_major``."""

    def test_exact_major_match(self) -> None:
        """Exact ``major`` name (as stored in YAML) returns that entry."""
        result = lookup_major("Marketing")
        assert result is not None
        assert result["cip4"] == "52.14"
        assert result["major"] == "Marketing"

    def test_alias_match(self) -> None:
        """An alias string returns the entry that lists it under aliases."""
        result = lookup_major("mktg")
        assert result is not None
        assert result["cip4"] == "52.14"
        assert result["major"] == "Marketing"

    def test_case_insensitive(self) -> None:
        """Case variations against both major and alias hit the same entry.

        If this regresses, the short-circuit misses 'MARKETING' (user hits
        caps lock), 'Finance' typed as 'finance' — the entire failure mode
        Bug B fixed.
        """
        assert lookup_major("MARKETING") is not None
        assert lookup_major("MaRkEtInG") is not None
        # Alias case: "HR" is the YAML-canonical alias — verify "hr" hits.
        assert lookup_major("hr") is not None
        assert lookup_major("hr")["cip4"] == "52.10"
        # Upper-cased alias on an entry whose alias is already upper.
        assert lookup_major("HR") is not None
        assert lookup_major("HR")["cip4"] == "52.10"

    def test_empty_input_returns_none(self) -> None:
        """Empty/whitespace input must not match the first entry by accident."""
        assert lookup_major("") is None
        assert lookup_major("   ") is None
        assert lookup_major("\t\n") is None

    def test_unknown_returns_none(self) -> None:
        """Inputs with no YAML coverage fall through to Gemma — return None."""
        assert lookup_major("Underwater basket weaving") is None
        # Non-alphanumeric gibberish is a legitimate adversarial test:
        # the audit step catches it downstream; the lookup must not
        # charitably match anything.
        assert lookup_major("asdfghjkl") is None

    def test_path_resolution_is_cwd_independent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Running ``lookup_major`` from two cwds returns identical results.

        Bug B's subtle regression mode: the YAML resolves only when pytest
        runs from one specific cwd. The module walks up from ``__file__``
        precisely to dodge that. This test forces two different cwds and
        asserts both hits return the same entry.
        """
        # Blow away the lru_caches so the first call resolves the path
        # against the module's __file__ under the default cwd.
        major_lookup._yaml_path.cache_clear()
        major_lookup._load.cache_clear()

        monkeypatch.chdir(tmp_path)
        from_tmp = lookup_major("Marketing")

        # Clear again and re-run from the repo root — same result required.
        major_lookup._yaml_path.cache_clear()
        major_lookup._load.cache_clear()

        repo_root = Path(__file__).resolve().parents[3]
        monkeypatch.chdir(repo_root)
        from_repo = lookup_major("Marketing")

        # Both must find the YAML and return the same entry. If the module
        # ever relied on Path.cwd() again, ``from_tmp`` would be None.
        assert from_tmp is not None
        assert from_repo is not None
        assert from_tmp == from_repo
        assert from_tmp["cip4"] == "52.14"


# ---------------------------------------------------------------------------
# TestCrossModuleConsistency — P1
# ---------------------------------------------------------------------------


class TestCrossModuleConsistency:
    """Guard against drift between ``lookup_major`` and
    ``FutureProofMCPServer._find_major_intent``.

    Both copies walk ``data/reference/major_to_cip.yaml`` with
    case-insensitive ``major``+``aliases`` matching. If the logic diverges
    (e.g. one adds fuzzy matching, the other doesn't), symptom is
    "intent says 52.14 but MCP says 52.01" — a production drift we must
    catch at test time.
    """

    @pytest.fixture(scope="class")
    def mcp_server(self) -> FutureProofMCPServer:
        """Minimal MCP server with the YAML entries pre-populated.

        We bypass ``__init__`` (same pattern the substitution tests use
        at ``tests/mcp/test_cip_substitution.py``) and pre-populate the
        lookup cache directly from the YAML we already parsed. The MCP
        server's ``_load_major_to_cip_lookup`` resolves the path via
        ``brightsmith.config.PROJECT_ROOT``, which in the backend venv
        points at ``backend/`` and mis-resolves under pytest. Bypassing
        that loader with the same data source keeps us honest — both
        sides of the consistency check read the EXACT same bytes — and
        lets us compare the *matching semantics*, which is the thing
        this test guards.
        """
        server = FutureProofMCPServer.__new__(FutureProofMCPServer)
        server._major_to_cip_cache = list(_YAML_ENTRIES)
        return server

    @pytest.mark.parametrize(
        "entry,query",
        _cross_module_ids(),
        ids=lambda v: (
            v if isinstance(v, str) else v.get("major", "?")
        ),
    )
    def test_matches_find_major_intent_for_every_yaml_entry(
        self,
        mcp_server: FutureProofMCPServer,
        entry: dict[str, Any],
        query: str,
    ) -> None:
        """For every (entry, major|alias) pair, both lookups agree."""
        lookup_result = lookup_major(query)
        mcp_result = mcp_server._find_major_intent(query)

        # Both must find a match — this is the whole point of the YAML.
        assert lookup_result is not None, (
            f"lookup_major({query!r}) returned None; "
            f"expected entry {entry.get('major')!r}"
        )
        assert mcp_result is not None, (
            f"_find_major_intent({query!r}) returned None; "
            f"expected entry {entry.get('major')!r}"
        )

        # Both must resolve to the SAME cip4 as the YAML source-of-truth.
        assert lookup_result["cip4"] == entry["cip4"]
        assert mcp_result["cip4"] == entry["cip4"]
        # And they must agree with each other — this is the drift guard.
        assert lookup_result["cip4"] == mcp_result["cip4"]
        assert (
            str(lookup_result.get("major"))
            == str(mcp_result.get("major"))
        )
