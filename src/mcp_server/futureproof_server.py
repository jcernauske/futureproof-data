"""FutureProof MCP server — exposes governed education + career data to AI agents.

Extends Brightsmith's BaseMCPServer with domain-specific tools for
querying AI exposure scores, occupation profiles, career outcomes, and
regional price parities.

Start with: python -m brightsmith.serve
"""

from __future__ import annotations

import collections
import json
import logging
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from brightsmith.mcp.base_mcp_server import BaseMCPServer, ResourceDef, ToolDef

from mcp_server._query_engine import QueryEngine
from mcp_server._state_input import FIPS_TO_STATE_NAME, normalize_state_input
from mcp_server._telemetry import timed

# Fields in program_career_paths and onet_work_profiles that are
# persisted as JSON-encoded strings but should be returned to callers
# as native Python objects. task_breakdown_* added in v4 of
# gemma-ai-exposure-rescore — they ship from Iceberg as JSON strings
# via consumable.ai_exposure; without decoding the consumer receives
# escaped literal JSON instead of an array.
_JSON_STRUCT_FIELDS = (
    "top_5_activities",
    "top_human_activities",
    "burnout_drivers",
    "task_breakdown_automatable",
    "task_breakdown_human",
)


def _decode_json_struct_fields(row: dict) -> dict:
    """Parse JSON-encoded struct fields in-place; return the row.

    Leaves values untouched when they are already parsed, null, or fail
    to decode. Centralized so handlers that surface these fields return
    native objects instead of JSON strings.
    """
    for field in _JSON_STRUCT_FIELDS:
        val = row.get(field)
        if isinstance(val, str):
            try:
                row[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                pass
    return row


logger = logging.getLogger(__name__)

# Response fields returned by get_ai_exposure (excludes record_id, promoted_at).
# Extended in v4 of gemma-ai-exposure-rescore with task_breakdown_*
# (the "Gemma shows its work" surface), scoring_model + model_tag (row-
# level reproducibility), and karpathy_score (preserved for Gemma-
# preferred rows so the A/B comparison is available at query time).
AI_EXPOSURE_RESPONSE_FIELDS = [
    "soc_code",
    "occupation_title",
    "exposure_score",
    "stat_res",
    "boss_ai_score",
    "rationale",
    "category",
    "task_breakdown_automatable",
    "task_breakdown_human",
    "scoring_model",
    "model_tag",
    "karpathy_score",
]

TABLE_NAME = "consumable.ai_exposure"

# ---------------------------------------------------------------------------
# Regional Price Parities tool constants
# ---------------------------------------------------------------------------

RPP_TABLE_NAME = "consumable.regional_price_parities"

# Columns to fetch from Gold. The ``adjusted_examples`` struct is built
# client-side in the handler from the four adjusted_Nk columns, and
# ``verification_status`` is renamed to ``data_source`` in the response.
RPP_QUERY_FIELDS = [
    "state_name",
    "state_abbr",
    "state_fips",
    "census_region",
    "rpp_all_items",
    "purchasing_power_multiplier",
    "cost_tier",
    "adjusted_30k",
    "adjusted_50k",
    "adjusted_75k",
    "adjusted_100k",
    "verification_status",
    "data_year",
]

MAX_SALARY = 10_000_000

# ---------------------------------------------------------------------------
# get_school_programs constants
# ---------------------------------------------------------------------------

SCHOOL_PROGRAMS_TABLE = "consumable.career_outcomes"

SCHOOL_PROGRAMS_RESPONSE_FIELDS = [
    "unitid",
    "institution_name",
    "institution_control",
    "cipcode",
    "program_name",
    "cip_family_name",
    "earnings_1yr_median",
    "earnings_1yr_p25",
    "earnings_1yr_p75",
    "debt_median",
    "debt_p25",
    "debt_p75",
    "debt_to_earnings_annual",
    "debt_to_earnings_tier",
    "program_value_index",
    "confidence_tier",
    "has_earnings",
    "has_debt",
    "outcome_completeness",
    # Institution-level fields (raw-ingest-college-scorecard-institution).
    "state_abbr",
    "net_price_annual",
    "cost_of_attendance_annual",
    "net_price_4yr",
    "tuition_in_state",
    "tuition_out_of_state",
    "room_board_on_campus",
]

# Tier ordering: confidence tiers listed from strictest to loosest.
CONFIDENCE_TIER_ORDER = ["high", "medium", "low", "insufficient"]

# Safety limit — largest schools have ~142 programs; 500 is the spec cap.
SCHOOL_PROGRAMS_MAX_ROWS = 500

# Internal load cap when scanning all rows of career_outcomes for a fuzzy
# match. The table is ~60-80k rows; 200k is the ceiling.
SCHOOL_PROGRAMS_SCAN_LIMIT = 200_000

# ---------------------------------------------------------------------------
# get_career_paths constants
# ---------------------------------------------------------------------------

CAREER_PATHS_TABLE = "consumable.program_career_paths"

CAREER_PATHS_RESPONSE_FIELDS = [
    "unitid",
    "institution_name",
    "cipcode",
    "program_name",
    "cip_family_name",
    "soc_code",
    "occupation_title",
    "soc_major_group_name",
    "stat_ern",
    "stat_roi",
    "stat_res",
    "stat_grw",
    "stat_hmn",
    "boss_ai_score",
    "boss_loans_score",
    "boss_market_score",
    "boss_burnout_score",
    "boss_ceiling_score",
    "earnings_1yr_median",
    "earnings_1yr_p25",
    "earnings_1yr_p75",
    "debt_median",
    "debt_p25",
    "debt_p75",
    "debt_to_earnings_annual",
    "confidence_tier_program",
    "median_annual_wage",
    "growth_category",
    "employment_current",
    "education_level_name",
    "top_5_activities",
    "top_human_activities",
    "burnout_drivers",
    "match_quality",
    "stats_available_count",
    "bosses_available_count",
    "overall_confidence",
    # Institution-level cost fields, threaded through so the stat engine
    # can switch ROI from "median debt of past graduates" to
    # "actual school net price × loan_pct × 4 years". See spec
    # docs/specs/roi-formula-cost-of-attendance.md for the full rationale.
    "institution_control",
    "net_price_annual",
    "cost_of_attendance_annual",
    "net_price_4yr",
    "tuition_in_state",
    "tuition_out_of_state",
    "room_board_on_campus",
    # Option B composite provenance (S4 v4 — three-signal-ai-exposure-composite).
    # Threaded from consumable.ai_exposure via consumable.program_career_paths
    # so the backend can render the RES receipt and Fight AI narrative prompt
    # with method / velocity / adoption context.
    "ai_adoption_share",
    "velocity_label",
    "composite_method",
    "adoption_percentile",
    # Cost-based ROI provenance. Plan:
    # ~/.claude/plans/why-are-we-still-jaunty-curry.md
    "roi_cost_basis",
]

# Defensive LIMIT cap on the standard-path program_career_paths query.
# With predicate pushdown the WHERE unitid=? AND cipcode=? filter
# returns <= 50 rows in practice, so this is a belt-and-suspenders cap,
# not the primary scan gate it was before the performance rewrite.
CAREER_PATHS_SCAN_LIMIT = 1000

# ---------------------------------------------------------------------------
# Peer-school leaderboard (feature-compare-schools-for-career.md)
# ---------------------------------------------------------------------------
# Two whitelists: the HTTP endpoint needs full tuition breakdown for the
# residency-aware label per Decision #8; the MCP/chat tool drops them to
# save Gemma context budget per genai-architect R4.
SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP = [
    "rank",
    "unitid",
    "institution_name",
    "institution_control",
    "state_abbr",
    "cipcode",
    "program_name",
    "soc_code",
    "occupation_title",
    "stat_ern",
    "stat_roi",
    "earnings_1yr_median",
    "net_price_annual",
    "cost_of_attendance_annual",
    "tuition_in_state",
    "tuition_out_of_state",
    "overall_confidence",
    "confidence_tier_program",
    "match_quality",
    "is_anchor",
]

SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_MCP = [
    "rank",
    "unitid",
    "institution_name",
    "institution_control",
    "state_abbr",
    "cipcode",
    "program_name",
    "soc_code",
    "occupation_title",
    "stat_ern",
    "stat_roi",
    "earnings_1yr_median",
    "net_price_annual",
    "overall_confidence",
    "confidence_tier_program",
    "match_quality",
    "is_anchor",
]

_LEADERBOARD_MODES = ("by_soc", "by_cip_and_soc")
_CONFIDENCE_TIERS_DESC = ("high", "medium", "low")
# Defensive scan ceiling — at limit=25 + appended anchor we materialize
# at most ~26 rows from the windowed CTE. The CTE itself can rank
# thousands of rows, so this caps the materialized list returned to
# Python. SOCs with >5,000 programs producing them do not exist in
# practice (largest SOC in PCP has ~2,000 programs).
SCHOOLS_FOR_CAREER_SCAN_LIMIT = 5000

# ---------------------------------------------------------------------------
# CIP intent substitution constants
# ---------------------------------------------------------------------------
#
# See docs/specs/cip-intent-substitution.md. When a student provides
# ``student_major`` and the school only reports the broad XX.01 CIP, we
# substitute the 4-digit CIP whose crosswalk SOCs represent that major,
# while preserving the school's broad-CIP earnings/debt for ERN and ROI.

MAJOR_TO_CIP_LOOKUP_PATH = "data/reference/major_to_cip.yaml"

CIP_SOC_CROSSWALK_TABLE = "base.cip_soc_crosswalk"
OCCUPATION_PROFILES_TABLE = "consumable.occupation_profiles"
ONET_WORK_PROFILES_TABLE = "consumable.onet_work_profiles"
AI_EXPOSURE_TABLE_SUB = "consumable.ai_exposure"
CAREER_OUTCOMES_TABLE = "consumable.career_outcomes"

# Matches a "broad" (XX.01 or XX.0100) CIP — the "General" catch-all in
# every CIP family.
_BROAD_CIP_PATTERN = re.compile(r"^\d{2}\.01(00)?$")

# Fields to pull from consumable.career_outcomes for the school's
# broad-CIP row (used as the earnings/debt basis for blended rows).
_SUB_CO_FIELDS = [
    "unitid",
    "institution_name",
    "cipcode",
    "program_name",
    "cip_family_name",
    "earnings_1yr_median",
    "earnings_1yr_p25",
    "earnings_1yr_p75",
    "debt_median",
    "debt_p25",
    "debt_p75",
    "debt_to_earnings_annual",
    "cip_family_earnings_rank",
    "confidence_tier",
    # Institution-level cost fields propagated into substituted rows
    # so the new ROI formula can use net_price_annual × loan_pct × 4
    # rather than median debt × loan_pct.
    "institution_control",
    "net_price_annual",
    "cost_of_attendance_annual",
    "net_price_4yr",
    "tuition_in_state",
    "tuition_out_of_state",
    "room_board_on_campus",
]

# Fields to pull from consumable.occupation_profiles per SOC.
_SUB_OP_FIELDS = [
    "soc_code",
    "occupation_title",
    "soc_major_group_name",
    "median_annual_wage",
    "wage_percentile_overall",
    "grw_score_rounded",
    "market_score_rounded",
    "growth_category",
    "employment_current",
    "education_level_name",
]

# Fields to pull from consumable.onet_work_profiles per SOC.
_SUB_ONET_FIELDS = [
    "bls_soc_code",
    "primary_title",
    "hmn_score_rounded",
    "burnout_score_rounded",
    "top_5_activities",
    "top_human_activities",
    "burnout_drivers",
]

# Fields to pull from consumable.ai_exposure per SOC.
_SUB_AI_FIELDS = [
    "soc_code",
    "stat_res",
    "boss_ai_score",
]

# ---------------------------------------------------------------------------
# get_occupation_data constants
# ---------------------------------------------------------------------------

OCCUPATION_DATA_TABLE = "consumable.occupation_profiles"

# Uses the actual column names in the consumable.occupation_profiles
# contract. The spec lists aspirational aliases (education_level_code,
# work_experience, training_typical, median_wage_capped) that do not
# exist in the physical schema; we surface the real column names.
OCCUPATION_DATA_RESPONSE_FIELDS = [
    "soc_code",
    "occupation_title",
    "soc_major_group",
    "soc_major_group_name",
    "median_annual_wage",
    "wage_percentile_overall",
    "wage_percentile_education_tier",
    "wage_tier",
    "employment_current",
    "employment_projected",
    "employment_change_pct",
    "openings_annual_avg",
    "growth_category",
    "grw_score",
    "grw_score_rounded",
    "market_score",
    "market_score_rounded",
    "education_code",
    "education_level_name",
    "work_experience_code",
    "training_code",
    "broad_occupation_flag",
    "catchall_flag",
]

# ---------------------------------------------------------------------------
# get_task_breakdown constants
# ---------------------------------------------------------------------------

TASK_BREAKDOWN_TABLE = "consumable.onet_work_profiles"

# Uses the actual column names in consumable.onet_work_profiles. The
# spec references occupation_title / activity_summary / context_summary
# / contact_with_others / deal_with_unpleasant; the physical schema
# exposes primary_title and does not carry the summary/context columns.
TASK_BREAKDOWN_RESPONSE_FIELDS = [
    "bls_soc_code",
    "primary_title",
    "hmn_score",
    "hmn_score_rounded",
    "burnout_score",
    "burnout_score_rounded",
    "top_5_activities",
    "top_human_activities",
    "burnout_drivers",
    "time_pressure",
    "work_hours",
    "consequence_of_error",
    "activity_importance_mean",
    "human_activity_count",
]

# ---------------------------------------------------------------------------
# get_career_branches constants
# ---------------------------------------------------------------------------

CAREER_BRANCHES_TABLE = "consumable.career_branches"

# The spec's "stat_res (source)", "boss_ai_score (source)", and
# "stat_res_delta" aliases map to the physical columns source_res,
# source_ai_boss, and res_delta respectively.
CAREER_BRANCHES_RESPONSE_FIELDS = [
    "soc_code",
    "source_title",
    "related_soc_code",
    "related_title",
    "best_index",
    "relatedness_tier",
    "is_primary",
    "source_grw",
    "source_hmn",
    "source_burnout",
    "source_wage",
    "source_res",
    "source_ai_boss",
    "related_grw",
    "related_hmn",
    "related_burnout",
    "related_wage",
    "related_growth_category",
    "related_education_level",
    "related_res",
    "related_ai_boss",
    "grw_delta",
    "hmn_delta",
    "burnout_delta",
    "wage_delta",
    "res_delta",
    "ai_boss_delta",
    "branch_has_full_data",
    # v1.2.0: O*NET experience requirements (onet-experience-requirements spec).
    # All four fields are nullable — branches where the target or source
    # occupation lacks O*NET ETE coverage return NULL rather than 0.
    "related_experience_years",
    "related_experience_tier",
    "source_experience_years",
    "experience_delta_years",
]

CAREER_BRANCHES_MAX_ROWS = 20

# Load cap when scanning career_branches for a single SOC code. The
# underlying table is on the order of a few thousand rows per source
# SOC, so 100k is a comfortable ceiling.
CAREER_BRANCHES_SCAN_LIMIT = 200_000

# ---------------------------------------------------------------------------
# Validation regexes
# ---------------------------------------------------------------------------

_SOC_CODE_PATTERN = re.compile(r"^\d{2}-\d{4}$")
_CIPCODE_PATTERN = re.compile(r"^\d{2}\.\d{2,4}$")
_CIP4_PATTERN = re.compile(r"^\d{2}\.\d{2}$")


# Bounded-LRU caches keyed on ``(engine_id, ...)`` so
# ``mcp_client.reset_server()`` transparently invalidates between test
# cases: a new ``QueryEngine`` instance has a new ``id``, so prior
# entries become unreachable via the new key. DO NOT switch to a
# content-addressed key (e.g. catalog path hash) without first
# updating test isolation — stable keys would cause cached rows to
# leak across test cases and mask regressions.
#
# Cardinality of the crosswalk cache is bounded by the ~1.6k 4-digit
# CIPs in the taxonomy; 128 entries cover the ones users actually
# touch. The career-paths cache is larger because it keys on
# ``(unitid, cipcode)`` pairs, and ``loan_pct``/``student_cip`` are
# INTENTIONALLY NOT in the key: they are applied by the stat engine
# post-query and do not affect the underlying
# ``query_iceberg_simple`` result. Including them would make the LRU
# miss on essentially every request.
_CROSSWALK_CACHE_MAX = 128
_CAREER_PATHS_CACHE_MAX = 256
_SCHOOLS_FOR_CAREER_CACHE_MAX = 128
_crosswalk_cache: collections.OrderedDict[tuple[int, str], tuple[str, ...]] = (
    collections.OrderedDict()
)
_career_paths_cache: collections.OrderedDict[tuple[int, int, str], tuple] = (
    collections.OrderedDict()
)
# Cache key: (id(engine), mode, soc_code, cipcode_or_empty, min_confidence,
# min_program_confidence, state_abbr_or_empty, limit). build_unitid /
# build_cipcode are NOT in the key — they only affect anchor-row selection
# on a copy of the cached materialized ranked list.
_schools_for_career_cache: collections.OrderedDict[
    tuple[int, str, str, str, str, str, str, int],
    tuple,
] = collections.OrderedDict()
_cache_lock = threading.Lock()

# Guards first-time construction of the per-server QueryEngine.
# Without this, two concurrent first requests would each build their
# own QueryEngine (with its own DuckDB connection), and one would
# orphan when the second overwrote ``self._query_engine``. One-time
# cost per process.
_engine_init_lock = threading.Lock()


def _cache_get(cache: collections.OrderedDict, key: tuple) -> tuple[Any, bool]:
    """Return (value, hit) for the LRU-ordered dict; refresh on hit."""
    with _cache_lock:
        if key in cache:
            cache.move_to_end(key)
            return cache[key], True
        return None, False


def _cache_put(
    cache: collections.OrderedDict, key: tuple, value: Any, maxsize: int
) -> None:
    with _cache_lock:
        if key in cache:
            cache.move_to_end(key)
        elif len(cache) >= maxsize:
            cache.popitem(last=False)
        cache[key] = value


def _career_paths_result_path(result: dict) -> str:
    """Infer which branch ``_handle_get_career_paths`` took for the log."""
    caveat = result.get("data_caveat")
    if isinstance(caveat, dict):
        t = caveat.get("type")
        if t == "blended_substitution":
            return "substituted"
        if t == "gemma_soc_resolution":
            return "fallback_gemma"
        if t in ("broaden_cip", "cip_broadening"):
            return "fallback_broaden"
    if result.get("substitution_applied") and result.get("data"):
        # Broadening path sets substitution_applied=True but type name varies.
        return "fallback_broaden"
    if result.get("data") is None:
        return "error"
    return "standard"


def _cache_drop_engine(engine_id: int) -> None:
    """Drop every entry whose first key component matches ``engine_id``.

    Called by ``FutureProofMCPServer.shutdown()`` so a subsequent server
    instance (potentially reusing the same ``id``) cannot inherit stale
    cached rows.
    """
    with _cache_lock:
        for cache in (
            _crosswalk_cache,
            _career_paths_cache,
            _schools_for_career_cache,
        ):
            stale = [k for k in cache if k[0] == engine_id]
            for k in stale:
                del cache[k]


class FutureProofMCPServer(BaseMCPServer):
    """MCP server for the FutureProof education + career pipeline.

    Exposes domain-specific tools on top of the framework-provided
    query_table, list_tables, get_data_quality, get_lineage, and
    get_contract tools.
    """

    # ------------------------------------------------------------------
    # QueryEngine lifecycle — overrides the brightsmith base helpers
    # ------------------------------------------------------------------

    def _get_query_engine(self) -> QueryEngine:
        """Lazy-initialize the per-server QueryEngine singleton.

        Stashed on the instance rather than in ``__init__`` so
        construction stays import-safe for test code that never queries.

        Double-checked locking: the hot path (engine already built)
        stays lock-free; only the first request per process pays the
        lock. Without this, two concurrent first requests each
        construct their own QueryEngine + DuckDB connection and one
        orphans when the second overwrites ``self._query_engine``.
        """
        engine = getattr(self, "_query_engine", None)
        if engine is not None:
            return engine
        with _engine_init_lock:
            engine = getattr(self, "_query_engine", None)
            if engine is None:
                engine = QueryEngine(self.catalog)
                self._query_engine = engine
            return engine

    def query_iceberg_simple(
        self,
        table_name: str,
        filters: dict | None = None,
        columns: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Predicate-pushdown override of the brightsmith base helper.

        Delegates to the persistent ``QueryEngine`` so filters become a
        SQL ``WHERE`` clause (pushed into DuckDB/Iceberg) rather than a
        Python-side post-filter over a full scan.
        """
        try:
            return self._get_query_engine().query_filtered(
                table_name,
                filters=filters,
                columns=columns,
                limit=limit,
            )
        except Exception as exc:  # noqa: BLE001
            return [{"error": f"Cannot query {table_name}: {exc}"}]

    def query_iceberg(self, sql: str) -> list[dict]:
        """SQL pass-through override of the brightsmith base helper.

        Routes through the persistent ``QueryEngine`` so DuckDB init +
        Iceberg view registration happen exactly once per process
        instead of per call.
        """
        return self._get_query_engine().query_sql(sql)

    def shutdown(self) -> None:
        """Close the persistent DuckDB connection and drop caches.

        Called by ``backend.app.services.mcp_client.reset_server`` so
        test isolation is tight. Idempotent — safe to call on a server
        that never queried.
        """
        engine = getattr(self, "_query_engine", None)
        if engine is not None:
            _cache_drop_engine(id(engine))
            try:
                engine.shutdown()
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("QueryEngine shutdown failed: %s", exc)
            self._query_engine = None

    def _standard_path_rows(self, unitid: int, canonical_cipcode: str) -> list[dict]:
        """Fetch the standard-path program_career_paths rows.

        When ``FUTUREPROOF_OUTCOMES_CACHE=1``, an LRU keyed by
        ``(engine_id, unitid, canonical_cipcode)`` is consulted first.
        The key deliberately excludes ``loan_pct`` and ``student_cip``
        because those are applied downstream by the stat engine and
        do not affect ``query_iceberg_simple`` output.
        """
        cache_enabled = os.environ.get("FUTUREPROOF_OUTCOMES_CACHE") == "1"
        engine = self._get_query_engine()
        key = (id(engine), int(unitid), canonical_cipcode)
        if cache_enabled:
            cached, hit = _cache_get(_career_paths_cache, key)
            self._last_career_paths_cache_hit = hit
            if hit:
                # Return a shallow copy of the list so downstream sort
                # / mutation doesn't poison the cached value.
                return [dict(r) for r in cached]
        else:
            self._last_career_paths_cache_hit = False
        rows = self.query_iceberg_simple(
            CAREER_PATHS_TABLE,
            filters={"unitid": unitid, "cipcode": canonical_cipcode},
            columns=CAREER_PATHS_RESPONSE_FIELDS,
            limit=CAREER_PATHS_SCAN_LIMIT,
        )
        if cache_enabled and not (rows and "error" in rows[0]):
            # Snapshot before caller mutates.
            snapshot = tuple(dict(r) for r in rows)
            _cache_put(_career_paths_cache, key, snapshot, _CAREER_PATHS_CACHE_MAX)
        return rows

    def get_tools(self) -> list[ToolDef]:
        return [
            ToolDef(
                name="get_ai_exposure",
                description=(
                    "Get AI exposure data for an occupation by SOC code. "
                    "Returns exposure_score (0-10), derived stat_res (1-10, "
                    "AI Resilience), boss_ai_score (1-10, Fight AI difficulty), "
                    "a rationale explaining the score, and the BLS category. "
                    "Scores are blended from Gemma 4 (task-level O*NET scoring, "
                    "~798 occupations) and Karpathy (fallback, ~342 occupations); "
                    "scoring_model tells you which source produced this row. "
                    "For Gemma-scored rows, task_breakdown_automatable and "
                    "task_breakdown_human surface the specific tasks Gemma "
                    "flagged as AI-automatable vs human-essential, model_tag "
                    "records the exact Ollama tag for audit, and karpathy_score "
                    "preserves the prior-art score for A/B comparison. Higher "
                    "exposure_score = more AI-exposed; higher stat_res = more "
                    "resilient."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "soc_code": {
                            "type": "string",
                            "description": (
                                "Standard Occupational Classification code in "
                                "XX-XXXX format (e.g., '13-2051' for Financial analysts)"
                            ),
                        },
                    },
                    "required": ["soc_code"],
                },
                handler=self._handle_get_ai_exposure,
            ),
            ToolDef(
                name="get_regional_price_parity",
                description=(
                    "Get the BEA Regional Price Parity (RPP) record for a US "
                    "state. Accepts a 2-letter USPS abbreviation ('CA'), full "
                    "state name ('California'), or 2-digit FIPS code ('06'), "
                    "case insensitive. Returns rpp_all_items, "
                    "purchasing_power_multiplier (full precision), cost_tier, "
                    "a struct of adjusted salaries at 30k/50k/75k/100k, the "
                    "data_source ('bea_official' or 'estimate') so the caller "
                    "can hedge numeric precision, and the data_year. Set "
                    "verified_only=true to refuse rows where "
                    "data_source='estimate' and return a structured null."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "state": {
                            "type": "string",
                            "description": (
                                "US state identifier. Accepts 2-letter USPS "
                                "abbreviation (e.g., 'CA'), full state name "
                                "(e.g., 'California'), or 2-digit FIPS code "
                                "(e.g., '06'). Case insensitive for abbreviations "
                                "and names. Includes District of Columbia as "
                                "'DC' / 'District of Columbia' / '11'."
                            ),
                        },
                        "verified_only": {
                            "type": "boolean",
                            "description": (
                                "If true, refuse to return rows where "
                                "data_source='estimate'. Defaults to false. "
                                "Strict mode for regulated contexts where only "
                                "BEA-authoritative values are acceptable."
                            ),
                            "default": False,
                        },
                    },
                    "required": ["state"],
                },
                handler=self._handle_get_regional_price_parity,
            ),
            ToolDef(
                name="compare_purchasing_power",
                description=(
                    "Compare the purchasing power of a national salary "
                    "between two US states, using BEA Regional Price Parity "
                    "data. Computes adjusted_salary = round(salary * "
                    "purchasing_power_multiplier, 2) for each state and "
                    "returns both sides, the absolute difference, and the "
                    "difference percentage. Both states accept the same "
                    "input formats as get_regional_price_parity. Set "
                    "verified_only=true to require both states to have "
                    "data_source='bea_official'."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "salary": {
                            "type": "number",
                            "description": (
                                "National salary in US dollars (e.g., 65000). "
                                "Must be positive and less than 10,000,000."
                            ),
                        },
                        "state_a": {
                            "type": "string",
                            "description": (
                                "First state. Same format as "
                                "get_regional_price_parity.state."
                            ),
                        },
                        "state_b": {
                            "type": "string",
                            "description": (
                                "Second state. Same format as "
                                "get_regional_price_parity.state."
                            ),
                        },
                        "verified_only": {
                            "type": "boolean",
                            "description": (
                                "If true, both state_a and state_b must have "
                                "data_source='bea_official'; otherwise returns "
                                "a structured null with a message. Defaults to "
                                "false."
                            ),
                            "default": False,
                        },
                    },
                    "required": ["salary", "state_a", "state_b"],
                },
                handler=self._handle_compare_purchasing_power,
            ),
            ToolDef(
                name="get_school_programs",
                description=(
                    "Look up all programs (majors) offered at a US school, "
                    "with earnings, debt, ROI, and confidence tier for each. "
                    "Accepts a fuzzy institution name (case-insensitive "
                    "substring match against institution_name, e.g. "
                    "'Indiana State', 'Harvard') or a numeric unitid for an "
                    "exact lookup. Returns up to 500 programs sorted by "
                    "program_name. When the name matches multiple campuses "
                    "(e.g. 'University of Michigan' -> Ann Arbor/Dearborn/"
                    "Flint), all matches are returned so the caller can "
                    "disambiguate. Set min_confidence to 'medium' or 'high' "
                    "to filter out suppressed/low-data programs. Each row "
                    "also carries institution-level cost fields when "
                    "available: institution_control "
                    "('Public'/'Private nonprofit'/'Private for-profit'), "
                    "net_price_annual (after grants/scholarships), "
                    "cost_of_attendance_annual (sticker), net_price_4yr, "
                    "tuition_in_state, tuition_out_of_state, and "
                    "room_board_on_campus."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "school_name": {
                            "type": "string",
                            "description": (
                                "Institution name to search for (e.g., "
                                "'Indiana State', 'Harvard'). Case-insensitive "
                                "substring match against institution_name. "
                                "If all digits, treated as a numeric unitid "
                                "for an exact lookup."
                            ),
                        },
                        "min_confidence": {
                            "type": "string",
                            "description": (
                                "Minimum confidence_tier to include. One of: "
                                "'high', 'medium', 'low', 'insufficient'. "
                                "Defaults to 'insufficient' (return all)."
                            ),
                            "default": "insufficient",
                        },
                    },
                    "required": ["school_name"],
                },
                handler=self._handle_get_school_programs,
            ),
            ToolDef(
                name="get_career_paths",
                description=(
                    "Core product query. Given a school (unitid) and major "
                    "(cipcode), returns every career outcome (SOC code) the "
                    "program leads to, with the full five-stat pentagon "
                    "(stat_ern, stat_roi, stat_res, stat_grw, stat_hmn), "
                    "the five boss-fight scores (Fight AI, Fight Loans, "
                    "Fight Market, Fight Burnout, Fight Ceiling), BLS "
                    "earnings/growth context, and O*NET task summaries. "
                    "Each row also carries institution-level cost fields "
                    "when available (institution_control, net_price_annual, "
                    "cost_of_attendance_annual, net_price_4yr, "
                    "tuition_in_state, tuition_out_of_state, "
                    "room_board_on_campus) — these power the new ROI "
                    "formula (net_price × loan_pct × 4 years) and the cost "
                    "breakdown receipt. Results are sorted by "
                    "stats_available_count DESC so best-data careers come "
                    "first. Zero results means the program lacks CIP-SOC "
                    "crosswalk coverage. When the school only reports a "
                    "broad XX.01 CIP, pass student_major to substitute the "
                    "major-specific SOC set while preserving the school's "
                    "broad-program earnings for ERN/ROI."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "unitid": {
                            "type": "integer",
                            "description": (
                                "IPEDS 6-digit institution identifier "
                                "(e.g., 151801 for Indiana State University). "
                                "Get this from get_school_programs results."
                            ),
                        },
                        "cipcode": {
                            "type": "string",
                            "description": (
                                "CIP program code in XX.XX or XX.XXXX format "
                                "(e.g., '52.02' for Business Administration). "
                                "Get this from get_school_programs results."
                            ),
                        },
                        "student_major": {
                            "type": "string",
                            "description": (
                                "Optional. The student's stated major "
                                "(e.g., 'Marketing', 'Accounting'). When "
                                "provided and the school's reported CIP is a "
                                "broad XX.01 code, the system substitutes "
                                "the specific CIP's crosswalk SOC mappings "
                                "while keeping the school's broad-program "
                                "earnings for ERN/ROI. When omitted, returns "
                                "the school's reported CIP career paths "
                                "as-is."
                            ),
                        },
                    },
                    "required": ["unitid", "cipcode"],
                },
                handler=self._handle_get_career_paths,
            ),
            ToolDef(
                name="get_occupation_data",
                description=(
                    "BLS occupation profile for a single SOC code. Returns "
                    "median_annual_wage, wage percentiles, employment "
                    "current/projected/change, growth_category, grw_score, "
                    "market_score, and the typical education/training/"
                    "work-experience codes. Use this for deep-dive salary "
                    "and growth details after get_career_paths surfaces the "
                    "SOC code."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "soc_code": {
                            "type": "string",
                            "description": (
                                "Standard Occupational Classification code "
                                "in XX-XXXX format (e.g., '13-2051' for "
                                "Financial analysts)."
                            ),
                        },
                    },
                    "required": ["soc_code"],
                },
                handler=self._handle_get_occupation_data,
            ),
            ToolDef(
                name="get_task_breakdown",
                description=(
                    "O*NET task-level profile for a single SOC code. Returns "
                    "the hmn_score (human-edge strength), the burnout_score "
                    "(Fight Burnout boss strength), top_5_activities, "
                    "top_human_activities (AI-resistant tasks), "
                    "burnout_drivers, time_pressure, work_hours, and "
                    "consequence_of_error context. Use this to generate "
                    "the 'what AI is eating' vs 'what the human edge looks "
                    "like' narrative for a career."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "soc_code": {
                            "type": "string",
                            "description": (
                                "Standard Occupational Classification code "
                                "in XX-XXXX format (e.g., '13-2051'). Queried "
                                "against bls_soc_code in the O*NET table."
                            ),
                        },
                    },
                    "required": ["soc_code"],
                },
                handler=self._handle_get_task_breakdown,
            ),
            ToolDef(
                name="get_career_branches",
                description=(
                    "Stage 3 branching paths for a source occupation. "
                    "Given a SOC code, returns up to 20 related careers "
                    "that are realistic transitions, with the stat deltas "
                    "(grw/hmn/burnout/wage/res/ai_boss) between the source "
                    "and each target. Sorted by best_index ASC (most "
                    "related first). By default only primary branches "
                    "(is_primary=true) are returned; set primary_only=false "
                    "to include the full list. Zero results means O*NET "
                    "has no transition data for that occupation."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "soc_code": {
                            "type": "string",
                            "description": (
                                "Source occupation SOC code in XX-XXXX "
                                "format (e.g., '13-2051' for Financial "
                                "analysts)."
                            ),
                        },
                        "primary_only": {
                            "type": "boolean",
                            "description": (
                                "If true, return only primary branches "
                                "(is_primary=true). Defaults to true."
                            ),
                            "default": True,
                        },
                    },
                    "required": ["soc_code"],
                },
                handler=self._handle_get_career_branches,
            ),
            ToolDef(
                name="get_schools_for_career",
                description=(
                    "Career-to-school leaderboard. Use this tool when the "
                    "student wants to COMPARE SCHOOLS for a specific career "
                    "outcome — not for questions about one school's programs. "
                    "Key distinction: get_career_paths answers 'what does "
                    "[school+major] lead to?' — this tool answers 'which "
                    "schools are best for producing [career]?'. Two modes: "
                    "'by_soc' returns all programs nationally that lead to "
                    "the given occupation, ranked by earnings (ERN) and ROI; "
                    "'by_cip_and_soc' narrows to programs in a specific "
                    "major field (cipcode) that lead to the occupation — the "
                    "tightest apples-to-apples comparison. When "
                    "mode='by_cip_and_soc', cipcode is required. Pass "
                    "build_unitid + build_cipcode together (both or neither) "
                    "to pin the student's current school as a reference row "
                    "in the results."
                ),
                input_schema={
                    "type": "object",
                    "properties": {
                        "mode": {
                            "type": "string",
                            "enum": list(_LEADERBOARD_MODES),
                            "default": "by_soc",
                        },
                        "soc_code": {
                            "type": "string",
                            "description": (
                                "BLS SOC code, e.g. '15-1252' (Software "
                                "Developers). Required for both modes."
                            ),
                        },
                        "cipcode": {
                            "type": "string",
                            "description": (
                                "CIP code, XX.XXXX string. REQUIRED when "
                                "mode='by_cip_and_soc'."
                            ),
                        },
                        "limit": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 25,
                            "default": 5,
                            "description": (
                                "Number of top-ranked programs to return. "
                                "Default 5 is tuned for chat surfaces — "
                                "total program count is always returned via "
                                "total_qualifying_programs regardless. The "
                                "HTTP endpoint may request up to 25."
                            ),
                        },
                        "min_confidence": {
                            "type": "string",
                            "enum": list(_CONFIDENCE_TIERS_DESC),
                            "default": "medium",
                            "description": (
                                "Floor on overall_confidence. Default "
                                "excludes 'low' rows."
                            ),
                        },
                        "min_program_confidence": {
                            "type": "string",
                            "enum": list(_CONFIDENCE_TIERS_DESC),
                            "default": "low",
                            "description": (
                                "Optional floor on confidence_tier_program "
                                "(the upstream completer-count proxy). "
                                "Default 'low' means no program-level "
                                "sample-size filter is applied — the school "
                                "simply needs programs on the books. Tighten "
                                "to 'medium' to require completions_count "
                                ">= 30 at the program level."
                            ),
                        },
                        "state_abbr": {
                            "type": "string",
                            "description": (
                                "Optional 2-letter USPS state abbreviation "
                                "(e.g., 'IN', 'CA', 'NY'). Unknown values "
                                "return an empty result rather than an error."
                            ),
                        },
                        "build_unitid": {
                            "type": "integer",
                            "description": (
                                "Optional. The student's current school "
                                "IPEDS unitid, used to highlight their "
                                "program in the leaderboard. MUST be passed "
                                "together with build_cipcode — either both "
                                "or neither. Passing only one is treated as "
                                "no anchor."
                            ),
                        },
                        "build_cipcode": {
                            "type": "string",
                            "description": (
                                "Optional. The student's current program CIP "
                                "code (XX.XXXX format). MUST be passed "
                                "together with build_unitid — either both or "
                                "neither."
                            ),
                        },
                        "anchor_stat_ern": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 10,
                            "description": (
                                "Optional. The build's stat_ern (0-10). When "
                                "passed with anchor_stat_roi, lets the handler "
                                "compute anchor_estimated_rank for builds "
                                "whose CIP-substituted program has no row in "
                                "the leaderboard table."
                            ),
                        },
                        "anchor_stat_roi": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 10,
                            "description": (
                                "Optional. The build's stat_roi (0-10). Pair "
                                "with anchor_stat_ern."
                            ),
                        },
                    },
                    "required": ["soc_code"],
                },
                handler=self._handle_get_schools_for_career,
            ),
        ]

    def get_resources(self) -> list[ResourceDef]:
        return []

    # ------------------------------------------------------------------
    # Governance enrichment — override to inject quality_tier and owner
    # ------------------------------------------------------------------
    #
    # The framework's BaseMCPServer.attach_governance only emits
    # ``table``, ``contract_version``, and ``contract_status``.  The
    # ``mcp-bea-rpp`` spec (acceptance criterion line 238; example
    # payloads at lines 74-78 and 155-159) requires every success
    # response to also carry ``governance.quality_tier`` and
    # ``governance.owner``.  This override reads those two fields
    # directly from the project's top-level contract YAML files and
    # injects them into the dict returned by the base implementation.
    #
    # The contract files in this project follow a different shape than
    # brightsmith.infra.contract.generate_contract — they hold ``table``,
    # ``owner``, and ``quality_tier`` at the top level of the YAML (not
    # nested under ``metadata`` / ``schema``), so ``list_contracts()``
    # cannot surface those fields.  We read the YAML directly, cache
    # the parsed dict by table name, and degrade gracefully when the
    # contract file is missing or the field is absent.
    #
    # Fix for DQ P0 failure MCP-BEA-002.

    _contract_cache: dict[str, dict | None] = {}

    @staticmethod
    def _table_to_contract_path(table_name: str) -> Path:
        """Resolve a fully-qualified table name to a contract YAML path.

        Convention used in this project: ``namespace.table_name`` maps to
        ``governance/data-contracts/{namespace}-{table-name}.yaml`` with
        underscores replaced by hyphens.
        """
        try:
            from brightsmith.config import PROJECT_ROOT

            root = Path(PROJECT_ROOT)
        except Exception:
            root = Path.cwd()

        namespace, _, table = table_name.partition(".")
        filename = f"{namespace}-{table.replace('_', '-')}.yaml"
        return root / "governance" / "data-contracts" / filename

    def _load_contract_fields(self, table_name: str) -> dict | None:
        """Load and cache the top-level YAML contract for a table.

        Returns ``None`` when the contract cannot be located or parsed.
        """
        if table_name in self._contract_cache:
            return self._contract_cache[table_name]

        path = self._table_to_contract_path(table_name)
        parsed: dict | None = None
        if not path.exists():
            logger.warning(
                "Contract file not found for table %s at %s; "
                "quality_tier/owner will be omitted from governance payload",
                table_name,
                path,
            )
        else:
            try:
                loaded = yaml.safe_load(path.read_text())
                if isinstance(loaded, dict):
                    parsed = loaded
                else:
                    logger.warning(
                        "Contract file %s did not parse to a mapping; "
                        "quality_tier/owner will be omitted",
                        path,
                    )
            except Exception as exc:
                logger.warning(
                    "Failed to parse contract file %s: %s; "
                    "quality_tier/owner will be omitted",
                    path,
                    exc,
                )

        self._contract_cache[table_name] = parsed
        return parsed

    @staticmethod
    def _extract_quality_tier_token(raw: Any) -> str | None:
        """Extract the canonical quality tier token from a raw YAML value.

        The project stores a folded scalar such as
        ``"partial_verification — carried forward from Silver ..."``.
        The DQ contract (MCP-BEA-002) requires the literal string
        ``"partial_verification"``, so we split on whitespace and the
        em-dash separator and return just the first token.  Returns
        ``None`` when the value is missing or empty.
        """
        if raw is None:
            return None
        text = str(raw).strip()
        if not text:
            return None
        # Split on whitespace or em-dash — both seen in contract files.
        for sep in ("\n", " ", "—", "-"):
            if sep in text:
                text = text.split(sep, 1)[0].strip()
                if not text:
                    return None
        return text or None

    def attach_governance(self, result: dict, table_name: str) -> dict:
        """Attach governance metadata, including quality_tier and owner.

        Calls the framework base implementation first (which emits
        ``table``, ``contract_version``, ``contract_status``), then
        injects ``quality_tier`` and ``owner`` from the project's
        top-level contract YAML when available.
        """
        enriched = super().attach_governance(result, table_name)
        governance = enriched.setdefault("governance", {"table": table_name})

        contract = self._load_contract_fields(table_name)
        if contract is None:
            return enriched

        tier = self._extract_quality_tier_token(contract.get("quality_tier"))
        if tier:
            governance["quality_tier"] = tier
        else:
            logger.warning(
                "Contract for %s has no quality_tier field; omitting from "
                "governance payload",
                table_name,
            )

        owner = contract.get("owner")
        if owner:
            governance["owner"] = owner

        return enriched

    # ------------------------------------------------------------------
    # Tool handler: get_ai_exposure
    # ------------------------------------------------------------------

    def _handle_get_ai_exposure(self, input_dict: dict) -> dict:
        """Query consumable.ai_exposure for a single SOC code.

        Returns the matching row with governance metadata, or a null
        result with a message if the SOC code is not found.
        """
        soc_code = input_dict.get("soc_code", "").strip()

        if not soc_code:
            return {
                "data": None,
                "message": "soc_code is required",
            }

        rows = self.query_iceberg_simple(
            TABLE_NAME,
            filters={"soc_code": soc_code},
            columns=AI_EXPOSURE_RESPONSE_FIELDS,
            limit=1,
        )

        # Check for query errors
        if rows and "error" in rows[0]:
            return self.attach_governance(
                {"data": None, "message": rows[0]["error"]},
                TABLE_NAME,
            )

        if not rows:
            return self.attach_governance(
                {
                    "data": None,
                    "message": "No AI exposure data available for this occupation",
                },
                TABLE_NAME,
            )

        return self.enrich_response(
            {"data": _decode_json_struct_fields(rows[0]), "row_count": 1},
            TABLE_NAME,
        )

    # ------------------------------------------------------------------
    # Tool handler: get_regional_price_parity
    # ------------------------------------------------------------------

    def _fetch_rpp_row(self, state_fips: str) -> dict | None:
        """Fetch a single RPP row by FIPS code.

        Returns ``None`` when the row is not found or when the query
        layer returns an error envelope.  Handlers decide how to surface
        that as a structured-null response.
        """
        rows = self.query_iceberg_simple(
            RPP_TABLE_NAME,
            filters={"state_fips": state_fips},
            columns=RPP_QUERY_FIELDS,
            limit=1,
        )
        if not rows:
            return None
        if "error" in rows[0]:
            return None
        return rows[0]

    @staticmethod
    def _rpp_row_to_payload(row: dict) -> dict:
        """Transform a raw Gold RPP row into the Gemma-facing response shape.

        * Builds the ``adjusted_examples`` struct from the four
          ``adjusted_Nk`` columns
        * Renames ``verification_status`` -> ``data_source``
        * Preserves full-precision ``purchasing_power_multiplier``
          (pre-review Advisory #1 — the caller must be able to
          reconstruct arithmetic exactly)
        """
        return {
            "state_name": row["state_name"],
            "state_abbr": row["state_abbr"],
            "state_fips": row["state_fips"],
            "census_region": row["census_region"],
            "rpp_all_items": row["rpp_all_items"],
            "purchasing_power_multiplier": row["purchasing_power_multiplier"],
            "cost_tier": row["cost_tier"],
            "adjusted_examples": {
                "30k": row["adjusted_30k"],
                "50k": row["adjusted_50k"],
                "75k": row["adjusted_75k"],
                "100k": row["adjusted_100k"],
            },
            "data_source": row["verification_status"],
            "data_year": row["data_year"],
        }

    def _handle_get_regional_price_parity(self, input_dict: dict) -> dict:
        """Query consumable.regional_price_parities for a single state.

        Pipeline:
            1. Normalize input to a FIPS code
            2. Unknown input -> null with "Unknown state: ..." message
            3. Fetch row from Gold; missing row -> null with guard message
            4. If verified_only and row is an estimate -> null with
               strict-mode refusal message
            5. Otherwise return the enriched response with governance
               metadata attached
        """
        raw_state = input_dict.get("state")
        verified_only = bool(input_dict.get("verified_only", False))

        fips = normalize_state_input(raw_state)
        if fips is None:
            display = repr(raw_state) if raw_state is not None else "None"
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"Unknown state: {display}. Expected a US state "
                        f"(50 states + DC) by USPS abbreviation, full name, "
                        f"or FIPS code."
                    ),
                },
                RPP_TABLE_NAME,
            )

        row = self._fetch_rpp_row(fips)
        if row is None:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No regional price parity data available for "
                        f"{FIPS_TO_STATE_NAME.get(fips, fips)!r}"
                    ),
                },
                RPP_TABLE_NAME,
            )

        if verified_only and row.get("verification_status") == "estimate":
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"Regional price parity for {row['state_name']!r} is "
                        f"currently an estimate (data_source=estimate) and "
                        f"strict mode is enabled. Disable verified_only to "
                        f"proceed with the estimate."
                    ),
                },
                RPP_TABLE_NAME,
            )

        return self.enrich_response(
            {"data": self._rpp_row_to_payload(row), "row_count": 1},
            RPP_TABLE_NAME,
        )

    # ------------------------------------------------------------------
    # Tool handler: compare_purchasing_power
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_salary(raw: Any) -> tuple[float | None, str | None]:
        """Validate and coerce the ``salary`` input.

        Returns ``(value, None)`` on success, or ``(None, message)`` when
        the input is missing, non-numeric, non-finite, zero, negative,
        or >= MAX_SALARY.  Booleans are explicitly rejected (``bool`` is
        a subclass of ``int`` in Python) to avoid ``True`` silently
        becoming ``$1``.
        """
        if raw is None or isinstance(raw, bool) or not isinstance(raw, (int, float)):
            return None, (
                f"salary must be a positive number less than {MAX_SALARY:,}; "
                f"got {raw!r}"
            )

        # Reject NaN / inf
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None, (
                f"salary must be a positive number less than {MAX_SALARY:,}; "
                f"got {raw!r}"
            )
        if value != value or value in (float("inf"), float("-inf")):
            return None, (
                f"salary must be a positive number less than {MAX_SALARY:,}; "
                f"got {raw!r}"
            )

        if value <= 0 or value >= MAX_SALARY:
            return None, (
                f"salary must be a positive number less than {MAX_SALARY:,}; "
                f"got {raw!r}"
            )

        return value, None

    @staticmethod
    def _compact_side(row: dict, adjusted_salary: float) -> dict:
        """Compact per-state side block for compare_purchasing_power.

        Full-precision purchasing_power_multiplier is preserved per
        pre-review Advisory #1.
        """
        return {
            "state_name": row["state_name"],
            "state_abbr": row["state_abbr"],
            "adjusted_salary": adjusted_salary,
            "cost_tier": row["cost_tier"],
            "purchasing_power_multiplier": row["purchasing_power_multiplier"],
            "data_source": row["verification_status"],
        }

    def _handle_compare_purchasing_power(self, input_dict: dict) -> dict:
        """Compare adjusted purchasing power of a salary between two states.

        Validation order:
            1. Salary validation (type, sign, range, NaN/inf, bool)
            2. Normalize both state inputs; unknown state -> null
            3. Reject same-state-twice (after normalization)
            4. Fetch both rows; any missing -> null
            5. If verified_only and either row is an estimate -> null
               identifying the offending state
            6. Compute adjusted salaries, difference, difference_pct
        """
        salary, msg = self._validate_salary(input_dict.get("salary"))
        if salary is None:
            return self.attach_governance(
                {"data": None, "message": msg},
                RPP_TABLE_NAME,
            )

        raw_a = input_dict.get("state_a")
        raw_b = input_dict.get("state_b")

        fips_a = normalize_state_input(raw_a)
        if fips_a is None:
            display = repr(raw_a) if raw_a is not None else "None"
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"Unknown state: {display}. Expected a US state "
                        f"(50 states + DC) by USPS abbreviation, full name, "
                        f"or FIPS code."
                    ),
                },
                RPP_TABLE_NAME,
            )

        fips_b = normalize_state_input(raw_b)
        if fips_b is None:
            display = repr(raw_b) if raw_b is not None else "None"
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"Unknown state: {display}. Expected a US state "
                        f"(50 states + DC) by USPS abbreviation, full name, "
                        f"or FIPS code."
                    ),
                },
                RPP_TABLE_NAME,
            )

        if fips_a == fips_b:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"state_a and state_b must be different states; "
                        f"got {raw_a!r} and {raw_b!r}"
                    ),
                },
                RPP_TABLE_NAME,
            )

        row_a = self._fetch_rpp_row(fips_a)
        row_b = self._fetch_rpp_row(fips_b)
        if row_a is None:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No regional price parity data available for "
                        f"{FIPS_TO_STATE_NAME.get(fips_a, fips_a)!r}"
                    ),
                },
                RPP_TABLE_NAME,
            )
        if row_b is None:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No regional price parity data available for "
                        f"{FIPS_TO_STATE_NAME.get(fips_b, fips_b)!r}"
                    ),
                },
                RPP_TABLE_NAME,
            )

        verified_only = bool(input_dict.get("verified_only", False))
        if verified_only:
            offenders = [
                r["state_name"]
                for r in (row_a, row_b)
                if r.get("verification_status") == "estimate"
            ]
            if offenders:
                first = offenders[0]
                return self.attach_governance(
                    {
                        "data": None,
                        "message": (
                            f"Strict mode requires both states to be "
                            f"BEA-official; {first!r} is currently an estimate"
                        ),
                    },
                    RPP_TABLE_NAME,
                )

        ppm_a = row_a["purchasing_power_multiplier"]
        ppm_b = row_b["purchasing_power_multiplier"]
        adjusted_a = round(salary * ppm_a, 2)
        adjusted_b = round(salary * ppm_b, 2)
        difference = round(adjusted_b - adjusted_a, 2)
        # Guard against pathological zero adjusted_a (shouldn't happen
        # in the valid RPP domain, but never raise).
        if adjusted_a == 0:
            difference_pct = 0.0
        else:
            difference_pct = round(difference / adjusted_a * 100, 2)

        payload = {
            "salary": float(salary),
            "state_a": self._compact_side(row_a, adjusted_a),
            "state_b": self._compact_side(row_b, adjusted_b),
            "difference": difference,
            "difference_pct": difference_pct,
        }

        return self.enrich_response(
            {"data": payload, "row_count": 2},
            RPP_TABLE_NAME,
        )

    # ------------------------------------------------------------------
    # Tool handler: get_school_programs
    # ------------------------------------------------------------------

    @staticmethod
    def _project_row(row: dict, fields: list[str]) -> dict:
        """Return a copy of ``row`` restricted to the given field list."""
        return {k: row.get(k) for k in fields}

    @staticmethod
    def _confidence_tier_allowed(tier: Any, min_confidence: str) -> bool:
        """Return True when ``tier`` meets the ``min_confidence`` threshold.

        Tier ordering (strictest to loosest): high > medium > low >
        insufficient. Unknown tiers (including None) fail closed when
        a threshold is set, but pass the 'insufficient' floor.
        """
        try:
            threshold_idx = CONFIDENCE_TIER_ORDER.index(min_confidence)
        except ValueError:
            threshold_idx = len(CONFIDENCE_TIER_ORDER) - 1
        if tier is None:
            return threshold_idx == len(CONFIDENCE_TIER_ORDER) - 1
        try:
            tier_idx = CONFIDENCE_TIER_ORDER.index(str(tier))
        except ValueError:
            return threshold_idx == len(CONFIDENCE_TIER_ORDER) - 1
        return tier_idx <= threshold_idx

    def _handle_get_school_programs(self, input_dict: dict) -> dict:
        """Query consumable.career_outcomes by school name or unitid.

        Supports numeric unitid exact match and case-insensitive
        substring match on institution_name. Filters by min_confidence
        tier, sorts by program_name, and caps at 500 rows.
        """
        raw_name = input_dict.get("school_name")
        if raw_name is None or not str(raw_name).strip():
            return {
                "data": None,
                "message": "school_name is required",
            }

        needle = str(raw_name).strip()
        min_confidence = (
            str(input_dict.get("min_confidence") or "insufficient").strip().lower()
        )
        if min_confidence not in CONFIDENCE_TIER_ORDER:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"min_confidence must be one of "
                        f"{CONFIDENCE_TIER_ORDER}; got {min_confidence!r}"
                    ),
                },
                SCHOOL_PROGRAMS_TABLE,
            )

        # Numeric needle -> exact unitid lookup via query_iceberg_simple.
        if needle.isdigit():
            try:
                unitid_value = int(needle)
            except ValueError:
                unitid_value = None
            if unitid_value is not None:
                rows = self.query_iceberg_simple(
                    SCHOOL_PROGRAMS_TABLE,
                    filters={"unitid": unitid_value},
                    columns=SCHOOL_PROGRAMS_RESPONSE_FIELDS,
                    limit=SCHOOL_PROGRAMS_SCAN_LIMIT,
                )
                if rows and "error" in rows[0]:
                    return self.attach_governance(
                        {"data": None, "message": rows[0]["error"]},
                        SCHOOL_PROGRAMS_TABLE,
                    )
                filtered = [
                    r
                    for r in rows
                    if self._confidence_tier_allowed(
                        r.get("confidence_tier"), min_confidence
                    )
                ]
                if not filtered:
                    return self.attach_governance(
                        {
                            "data": None,
                            "message": f"No programs found for '{needle}'",
                        },
                        SCHOOL_PROGRAMS_TABLE,
                    )
                filtered.sort(key=lambda r: str(r.get("program_name") or ""))
                filtered = filtered[:SCHOOL_PROGRAMS_MAX_ROWS]
                return self.enrich_response(
                    {"data": filtered, "row_count": len(filtered)},
                    SCHOOL_PROGRAMS_TABLE,
                )

        # Fuzzy name match — load the full table (with column projection)
        # and filter client-side. query_iceberg_simple only supports
        # exact-equality filters, so ILIKE must happen in Python.
        rows = self.query_iceberg_simple(
            SCHOOL_PROGRAMS_TABLE,
            filters=None,
            columns=SCHOOL_PROGRAMS_RESPONSE_FIELDS,
            limit=SCHOOL_PROGRAMS_SCAN_LIMIT,
        )
        if rows and "error" in rows[0]:
            return self.attach_governance(
                {"data": None, "message": rows[0]["error"]},
                SCHOOL_PROGRAMS_TABLE,
            )

        needle_lower = needle.lower()
        filtered = [
            r
            for r in rows
            if str(r.get("institution_name") or "").lower().find(needle_lower) >= 0
            and self._confidence_tier_allowed(r.get("confidence_tier"), min_confidence)
        ]

        if not filtered:
            return self.attach_governance(
                {
                    "data": None,
                    "message": f"No programs found for '{needle}'",
                },
                SCHOOL_PROGRAMS_TABLE,
            )

        filtered.sort(key=lambda r: str(r.get("program_name") or ""))
        filtered = filtered[:SCHOOL_PROGRAMS_MAX_ROWS]

        return self.enrich_response(
            {"data": filtered, "row_count": len(filtered)},
            SCHOOL_PROGRAMS_TABLE,
        )

    # ------------------------------------------------------------------
    # Tool handler: get_career_paths
    # ------------------------------------------------------------------

    _major_to_cip_cache: list[dict] | None = None

    def _load_major_to_cip_lookup(self) -> list[dict]:
        """Load and cache the major->CIP intent lookup table.

        Reads data/reference/major_to_cip.yaml once per server and caches
        the parsed list. Missing or malformed files log a warning and
        return an empty list so substitution degrades to the standard
        path rather than breaking the handler.

        Path resolution is cwd-independent: we first ask Brightsmith for
        ``PROJECT_ROOT``, and on failure walk up from this module file
        looking for the YAML. Previously this fell back to ``Path.cwd()``,
        which silently no-op'd substitution whenever uvicorn was started
        from ``backend/`` — the YAML isn't at ``backend/data/reference/``,
        so the handler loaded an empty list and every intent lookup
        returned None. Same failure mode the ``major_lookup`` module was
        written to dodge; mirror its walk-up strategy here.
        """
        if self._major_to_cip_cache is not None:
            return self._major_to_cip_cache
        root: Path | None = None
        try:
            from brightsmith.config import PROJECT_ROOT

            root = Path(PROJECT_ROOT)
        except Exception:
            root = None
        path: Path | None = None
        if root is not None:
            candidate = root / MAJOR_TO_CIP_LOOKUP_PATH
            if candidate.is_file():
                path = candidate
        if path is None:
            rel = Path(MAJOR_TO_CIP_LOOKUP_PATH)
            for parent in Path(__file__).resolve().parents:
                candidate = parent / rel
                if candidate.is_file():
                    path = candidate
                    break
        if path is None:
            logger.warning(
                "major_to_cip.yaml not found via Brightsmith PROJECT_ROOT "
                "or walk-up from %s",
                Path(__file__).resolve().parent,
            )
            self._major_to_cip_cache = []
            return self._major_to_cip_cache
        try:
            with path.open() as f:
                data = yaml.safe_load(f) or []
            if not isinstance(data, list):
                logger.warning("major_to_cip.yaml has unexpected shape; expected list")
                self._major_to_cip_cache = []
                return self._major_to_cip_cache
            self._major_to_cip_cache = data
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to load major_to_cip.yaml: %s", e)
            self._major_to_cip_cache = []
        return self._major_to_cip_cache

    def _find_major_intent(self, student_major: str) -> dict | None:
        """Match a student_major string to a lookup entry (case-insensitive).

        Matches against both ``major`` and each alias in ``aliases``.
        Returns the first matching entry or None.
        """
        if not student_major:
            return None
        needle = student_major.strip().lower()
        if not needle:
            return None
        for entry in self._load_major_to_cip_lookup():
            major = str(entry.get("major") or "").lower()
            if needle == major:
                return entry
            for alias in entry.get("aliases") or []:
                if needle == str(alias).lower():
                    return entry
        return None

    @staticmethod
    def _is_broad_cip(cipcode: str) -> bool:
        """True if cipcode is the 'General' XX.01 catch-all in its family."""
        return bool(_BROAD_CIP_PATTERN.match(cipcode))

    @staticmethod
    def _matched_cip_is_more_specific(school_cip: str, matched_cip: str) -> bool:
        """True if matched_cip is a child of school_cip.

        Example: school reports 13.10 (Special Education, General),
        student says "Deaf Education" → matched 13.1003. The matched
        CIP starts with the school CIP prefix and is more specific.
        """
        if len(matched_cip) <= len(school_cip):
            return False
        return matched_cip.startswith(school_cip)

    @staticmethod
    def _cip_family(cipcode: str) -> str:
        """Return the 2-digit family prefix of a CIP code."""
        return cipcode.split(".", 1)[0] if "." in cipcode else cipcode[:2]

    @staticmethod
    def _canonical_cip4(cipcode: str) -> str:
        """Normalize an arbitrary CIP code to the 4-digit XX.YY form.

        ``consumable.career_outcomes`` and ``consumable.program_career_paths``
        are both stored at 4-digit granularity. Callers (Gemma, frontend,
        YAML) may hand in 6-digit forms (``"52.0100"``, ``"52.0101"``,
        ``"52.1401"``) that exact-equals queries against either table will
        miss. Normalize to the 4-digit prefix at every filter site.
        """
        if not cipcode:
            return cipcode
        return cipcode[:5] if len(cipcode) >= 5 else cipcode

    def _fetch_substituted_join(self, cip4: str) -> list[dict]:
        """Return the substituted JOIN rows for a 4-digit CIP.

        Extracted so tests can patch this helper with a fixture while
        production code exercises the real ``QueryEngine``. The SOC CTE
        is bounded by the substituted CIP; LEFT JOINs preserve the
        fan-out's ``{}`` fallback when occupation_profiles /
        onet_work_profiles / ai_exposure has no row for a SOC. No SQL
        ORDER BY — the Python ``_sub_sort_key`` downstream is
        authoritative.

        Format contract: ``base.cip_soc_crosswalk.cipcode`` is stored
        as ``XX.XXXX`` (6 chars); ``SUBSTR(_, 1, 5)`` yields the
        4-digit prefix.
        """
        join_sql = """
        WITH socs AS (
            SELECT DISTINCT soc_code, soc_title
            FROM base_cip_soc_crosswalk
            WHERE SUBSTR(cipcode, 1, 5) = $cip4
              AND soc_code IS NOT NULL
              AND soc_code <> '99-9999'
        )
        SELECT
            socs.soc_code,
            socs.soc_title AS crosswalk_title,
            op.occupation_title,
            op.soc_major_group_name,
            op.median_annual_wage,
            op.wage_percentile_overall,
            op.grw_score_rounded,
            op.market_score_rounded,
            op.growth_category,
            op.employment_current,
            op.education_level_name,
            onet.primary_title,
            onet.hmn_score_rounded,
            onet.burnout_score_rounded,
            onet.top_5_activities,
            onet.top_human_activities,
            onet.burnout_drivers,
            ai.stat_res,
            ai.boss_ai_score
        FROM socs
        LEFT JOIN consumable_occupation_profiles op
            ON op.soc_code = socs.soc_code
        LEFT JOIN consumable_onet_work_profiles onet
            ON onet.bls_soc_code = socs.soc_code
        LEFT JOIN consumable_ai_exposure ai
            ON ai.soc_code = socs.soc_code
        """
        return self._get_query_engine().query_sql(join_sql, {"cip4": cip4})

    @timed(
        "fetch_crosswalk_socs",
        extract=lambda result, self, cip4: {
            "cip4": cip4,
            "row_count": len(result) if isinstance(result, list) else 0,
            "cache_hit": getattr(self, "_last_crosswalk_cache_hit", False),
        },
    )
    def _fetch_crosswalk_socs(self, cip4: str) -> list[str]:
        """Return distinct SOC codes for a 4-digit CIP prefix.

        LRU-cached by ``(engine_id, cip4)``. The cached value is a
        tuple (immutable, hashable-adjacent) that callers convert to a
        list on the way out so downstream code keeps its list contract.
        Cache is flushed by ``shutdown()`` so ``reset_server()`` in
        tests produces clean state.
        """
        # Sanity-check the prefix before formatting into SQL. This value
        # comes from our own YAML file but we still treat it as
        # untrusted input to prevent injection.
        if not _CIP4_PATTERN.match(cip4):
            self._last_crosswalk_cache_hit = False
            return []

        engine = self._get_query_engine()
        key = (id(engine), cip4)
        cached, hit = _cache_get(_crosswalk_cache, key)
        if hit:
            self._last_crosswalk_cache_hit = True
            return list(cached)
        self._last_crosswalk_cache_hit = False

        sql = (
            "SELECT DISTINCT soc_code FROM base_cip_soc_crosswalk "
            "WHERE SUBSTR(cipcode, 1, 5) = $cip4 "
            "AND soc_code IS NOT NULL AND soc_code <> '99-9999' "
            "ORDER BY soc_code"
        )
        try:
            rows = engine.query_sql(sql, {"cip4": cip4})
        except Exception as e:  # noqa: BLE001
            logger.warning("Crosswalk lookup failed for %s: %s", cip4, e)
            return []
        socs: tuple[str, ...] = tuple(
            str(r["soc_code"]) for r in rows if r.get("soc_code")
        )
        _cache_put(_crosswalk_cache, key, socs, _CROSSWALK_CACHE_MAX)
        return list(socs)

    @timed(
        "build_substituted_rows_join",
        extract=lambda result, self, **kw: {
            "unitid": kw.get("unitid"),
            "reported_cipcode": kw.get("reported_cipcode"),
            "substituted_cipcode": kw.get("substituted_cipcode"),
            "row_count": (len(result[0]) if result[0] is not None else 0),
            "error": result[1] if result[1] is not None else None,
        },
    )
    def _build_substituted_rows(
        self,
        *,
        unitid: int,
        reported_cipcode: str,
        substituted_cipcode: str,
        substituted_program_name: str,
        loan_pct: float = 1.0,
        intent_keywords: list[str] | None = None,
    ) -> tuple[list[dict] | None, str | None]:
        """Assemble blended career-path rows for a substitution.

        Pulls the school's broad-CIP row from career_outcomes for the
        earnings/debt basis, fetches the substituted CIP's SOCs from
        the crosswalk, and joins occupation_profiles + onet_work_profiles
        + ai_exposure for each SOC to compute the 5-stat pentagon.

        Replaces the prior 3×N fan-out with a single parameterized JOIN
        against the persistent ``QueryEngine`` views; the school lookup
        is issued first so the zero-school short-circuit (and its
        error message) match the fan-out byte-for-byte.

        Format contracts:
          - ``base.cip_soc_crosswalk.cipcode`` is stored as ``XX.XXXX``
            (6 chars); ``SUBSTR(_, 1, 5)`` yields the 4-digit prefix.
          - ``consumable.career_outcomes.cipcode`` is stored at 4-digit
            (``XX.YY``) granularity.

        Returns (rows, None) on success or (None, message) on failure
        (e.g. school's broad-CIP row missing, crosswalk empty).
        """
        # Lazy import to avoid a hard dependency on the gold module at
        # server import time.
        from gold.futureproof_engine import compute_stat_ern, compute_stat_roi

        # 1. School's broad-CIP row from career_outcomes.
        #    career_outcomes is stored at 4-digit granularity; canonicalize
        #    the caller-supplied cipcode so 6-digit forms ("52.0100") match.
        canonical_reported = self._canonical_cip4(reported_cipcode)
        co_rows = self.query_iceberg_simple(
            CAREER_OUTCOMES_TABLE,
            filters={"unitid": unitid, "cipcode": canonical_reported},
            columns=_SUB_CO_FIELDS,
            limit=1,
        )
        if co_rows and "error" in co_rows[0]:
            return None, co_rows[0]["error"]
        if not co_rows:
            # Short-circuit before issuing the JOIN: CROSS JOIN against
            # an empty school CTE would silently produce zero rows,
            # which is NOT parity with the fan-out's descriptive error.
            return None, (
                f"No career_outcomes row for unitid={unitid}, "
                f"cipcode='{canonical_reported}'; cannot substitute."
            )
        school = co_rows[0]
        cip_fam_rank = school.get("cip_family_earnings_rank")
        dte = school.get("debt_to_earnings_annual")
        # loan_pct scales the student's debt before ROI/loans-boss are
        # derived. 1.0 = full published debt (no-op), 0.0 = no loans
        # taken (DTE pinned to 0, ROI saturates at 10). Applied here so
        # the substitution path's inline stat_roi matches what
        # stat_engine derives for the main path.
        if dte is not None and 0.0 <= loan_pct < 1.0:
            adj_dte: float | None = float(dte) * float(loan_pct)
        else:
            adj_dte = dte

        # 2. Substituted SOCs from the crosswalk.
        socs = self._fetch_crosswalk_socs(substituted_cipcode)
        if not socs:
            return None, (
                f"No crosswalk SOCs found for substituted CIP '{substituted_cipcode}'."
            )

        # 2b. SOC expansion: add intent-driven SOCs from the 832-SOC universe.
        socs = self._expand_socs_if_needed(
            socs, intent_keywords or [], substituted_cipcode,
            program_name=substituted_program_name,
        )

        # 3. Single JOIN for all per-SOC data. Replaces the 3×N fan-out
        # with one parameterized query. Extracted into a helper so
        # test code can patch the JOIN fetch while the parity path
        # exercises the real QueryEngine.
        try:
            joined = self._fetch_substituted_join(substituted_cipcode)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Substituted JOIN failed for cip4=%s: %s",
                substituted_cipcode,
                e,
            )
            return None, f"Substituted JOIN failed: {e}"

        # Index JOIN rows by soc_code so we can preserve the crosswalk
        # SOC ordering (and include SOCs the LEFT JOIN didn't match
        # against any occupation source, matching the fan-out's
        # "{} fallback" behavior).
        by_soc = {r["soc_code"]: r for r in joined if r.get("soc_code")}

        # Expanded SOCs (from Gemma) aren't in the crosswalk CTE, so
        # they won't appear in by_soc. Fetch their data directly from
        # occupation_profiles to avoid blank titles.
        expanded_missing = [s for s in socs if s not in by_soc]
        if expanded_missing:
            engine = self._get_query_engine()
            valid_expanded = [
                s for s in expanded_missing if _SOC_CODE_PATTERN.match(s)
            ]
            if valid_expanded:
                values_sql = ", ".join(f"('{s}')" for s in valid_expanded)
                try:
                    extra = engine.query_sql(
                        f"""
                        SELECT
                            socs.soc_code,
                            op.occupation_title,
                            op.soc_major_group_name,
                            op.median_annual_wage,
                            op.wage_percentile_overall,
                            op.grw_score_rounded,
                            op.market_score_rounded,
                            op.growth_category,
                            op.employment_current,
                            op.education_level_name,
                            onet.primary_title,
                            onet.hmn_score_rounded,
                            onet.burnout_score_rounded,
                            onet.top_5_activities,
                            onet.top_human_activities,
                            onet.burnout_drivers,
                            ai.stat_res,
                            ai.boss_ai_score
                        FROM (VALUES {values_sql}) AS socs(soc_code)
                        LEFT JOIN consumable_occupation_profiles op
                            ON op.soc_code = socs.soc_code
                        LEFT JOIN consumable_onet_work_profiles onet
                            ON onet.bls_soc_code = socs.soc_code
                        LEFT JOIN consumable_ai_exposure ai
                            ON ai.soc_code = socs.soc_code
                        """,
                        {},
                    )
                    for r in extra:
                        if r.get("soc_code"):
                            by_soc[r["soc_code"]] = r
                except Exception:
                    logger.debug("Expanded SOC fetch failed", exc_info=True)
        rows: list[dict] = []
        for soc in socs:
            j = by_soc.get(soc, {})
            op_title = j.get("occupation_title")
            onet_primary = j.get("primary_title")
            xw_title = j.get("crosswalk_title")

            stat_ern = compute_stat_ern(cip_fam_rank, j.get("wage_percentile_overall"))
            stat_roi = compute_stat_roi(adj_dte)
            boss_loans_sub = (11 - stat_roi) if stat_roi is not None else None
            stat_grw = j.get("grw_score_rounded")
            stat_hmn = j.get("hmn_score_rounded")
            stat_res = j.get("stat_res")

            stats_available = sum(
                1
                for v in (stat_ern, stat_roi, stat_res, stat_grw, stat_hmn)
                if v is not None
            )
            boss_ai = j.get("boss_ai_score")
            boss_market = j.get("market_score_rounded")
            boss_burnout = j.get("burnout_score_rounded")
            # boss_ceiling is not derivable from occupation-level tables;
            # it lives on program_career_paths and stays omitted on
            # substituted rows. boss_loans mirrors the inline stat_roi
            # above so the CLI can still render the loans fight.
            bosses_available = sum(
                1
                for v in (boss_ai, boss_loans_sub, boss_market, boss_burnout)
                if v is not None
            )

            row = {
                "unitid": unitid,
                "institution_name": school.get("institution_name"),
                "cipcode": substituted_cipcode,
                "program_name": substituted_program_name,
                "cip_family_name": school.get("cip_family_name"),
                "soc_code": soc,
                "occupation_title": (op_title or onet_primary or xw_title or "Unknown"),
                "soc_major_group_name": j.get("soc_major_group_name"),
                "stat_ern": stat_ern,
                "stat_roi": stat_roi,
                "stat_res": stat_res,
                "stat_grw": stat_grw,
                "stat_hmn": stat_hmn,
                "boss_ai_score": boss_ai,
                "boss_loans_score": boss_loans_sub,
                "boss_market_score": boss_market,
                "boss_burnout_score": boss_burnout,
                "boss_ceiling_score": None,
                "earnings_1yr_median": school.get("earnings_1yr_median"),
                "earnings_1yr_p25": school.get("earnings_1yr_p25"),
                "earnings_1yr_p75": school.get("earnings_1yr_p75"),
                "debt_median": school.get("debt_median"),
                "debt_p25": school.get("debt_p25"),
                "debt_p75": school.get("debt_p75"),
                "debt_to_earnings_annual": school.get("debt_to_earnings_annual"),
                "confidence_tier_program": school.get("confidence_tier"),
                # Institution-level cost fields (mirror school row).
                "institution_control": school.get("institution_control"),
                "net_price_annual": school.get("net_price_annual"),
                "cost_of_attendance_annual": school.get("cost_of_attendance_annual"),
                "net_price_4yr": school.get("net_price_4yr"),
                "tuition_in_state": school.get("tuition_in_state"),
                "tuition_out_of_state": school.get("tuition_out_of_state"),
                "room_board_on_campus": school.get("room_board_on_campus"),
                "median_annual_wage": j.get("median_annual_wage"),
                "growth_category": j.get("growth_category"),
                "employment_current": j.get("employment_current"),
                "education_level_name": j.get("education_level_name"),
                "top_5_activities": j.get("top_5_activities"),
                "top_human_activities": j.get("top_human_activities"),
                "burnout_drivers": j.get("burnout_drivers"),
                "match_quality": "substituted_cip",
                "stats_available_count": stats_available,
                "bosses_available_count": bosses_available,
                "overall_confidence": ("high" if stats_available == 5 else "medium"),
            }
            rows.append(row)
        return rows, None

    # ------------------------------------------------------------------
    # SOC expansion helpers
    # ------------------------------------------------------------------

    def _expand_socs_if_needed(
        self,
        base_socs: list[str],
        intent_keywords: list[str],
        cip4: str,
        *,
        program_name: str = "",
    ) -> list[str]:
        """Call soc_expansion.expand_socs if available; return base_socs on failure."""
        try:
            from app.services.soc_expansion import expand_socs
        except ImportError:
            logger.debug("soc_expansion not importable — skipping expansion")
            return base_socs

        base_soc_titles: list[str] | None = None
        if not intent_keywords and program_name:
            base_soc_titles = self._fetch_soc_titles(base_socs)

        engine = self._get_query_engine()

        try:
            return expand_socs(
                intent_keywords=intent_keywords,
                base_socs=base_socs,
                cip_family=self._cip_family(cip4),
                program_name=program_name,
                base_soc_titles=base_soc_titles,
                query_fn=engine.query_sql,
            )
        except Exception:
            logger.warning("soc_expansion failed — returning base SOCs", exc_info=True)
            return base_socs

    def _fetch_soc_titles(self, soc_codes: list[str]) -> list[str]:
        """Fetch occupation titles for a list of SOC codes."""
        if not soc_codes:
            return []
        try:
            engine = self._get_query_engine()
            valid = [s for s in soc_codes if _SOC_CODE_PATTERN.match(s)]
            if not valid:
                return []
            rows = engine.query_sql(
                "SELECT soc_code, occupation_title "
                "FROM consumable_occupation_profiles "
                "WHERE soc_code IN ("
                + ", ".join(f"'{s}'" for s in valid)
                + ")",
                {},
            )
            by_soc = {r["soc_code"]: r.get("occupation_title", "") for r in rows}
            return [str(by_soc.get(s, "")) for s in soc_codes]
        except Exception:
            logger.debug("_fetch_soc_titles failed", exc_info=True)
            return []

    def _build_expanded_rows(
        self,
        new_socs: list[str],
        existing_rows: list[dict],
        canonical_cipcode: str,
    ) -> list[dict]:
        """Build rows for Gemma-expanded SOCs on the standard path.

        Uses a dynamic JOIN against occupation_profiles, onet_work_profiles,
        and ai_exposure — same as the substituted path's _fetch_substituted_join
        but scoped to the specific new SOCs.
        """
        if not new_socs or not existing_rows:
            return []

        template = existing_rows[0]
        engine = self._get_query_engine()

        soc_list_sql = ", ".join(
            f"'{s}'" for s in new_socs if _SOC_CODE_PATTERN.match(s)
        )
        if not soc_list_sql:
            return []

        try:
            joined = engine.query_sql(
                f"""
                SELECT
                    op.soc_code,
                    op.occupation_title,
                    op.soc_major_group_name,
                    op.median_annual_wage,
                    op.wage_percentile_overall,
                    op.grw_score_rounded,
                    op.market_score_rounded,
                    op.growth_category,
                    op.employment_current,
                    op.education_level_name,
                    onet.primary_title,
                    onet.hmn_score_rounded,
                    onet.burnout_score_rounded,
                    onet.top_5_activities,
                    onet.top_human_activities,
                    onet.burnout_drivers,
                    ai.stat_res,
                    ai.boss_ai_score
                FROM consumable_occupation_profiles op
                LEFT JOIN consumable_onet_work_profiles onet
                    ON onet.bls_soc_code = op.soc_code
                LEFT JOIN consumable_ai_exposure ai
                    ON ai.soc_code = op.soc_code
                WHERE op.soc_code IN ({soc_list_sql})
                """,
                {},
            )
        except Exception:
            logger.warning("_build_expanded_rows JOIN failed", exc_info=True)
            return []

        rows: list[dict] = []
        for j in joined:
            soc = j.get("soc_code", "")
            op_title = j.get("occupation_title")
            onet_primary = j.get("primary_title")
            stat_ern = template.get("stat_ern")
            stat_roi = template.get("stat_roi")
            stat_grw = j.get("grw_score_rounded")
            stat_hmn = j.get("hmn_score_rounded")
            stat_res = j.get("stat_res")
            boss_ai = j.get("boss_ai_score")
            boss_loans = template.get("boss_loans_score")
            boss_market = j.get("market_score_rounded")
            boss_burnout = j.get("burnout_score_rounded")

            stats_available = sum(
                1
                for v in (stat_ern, stat_roi, stat_res, stat_grw, stat_hmn)
                if v is not None
            )
            bosses_available = sum(
                1
                for v in (boss_ai, boss_loans, boss_market, boss_burnout)
                if v is not None
            )

            row = {
                "unitid": template.get("unitid"),
                "institution_name": template.get("institution_name"),
                "cipcode": canonical_cipcode,
                "program_name": template.get("program_name"),
                "cip_family_name": template.get("cip_family_name"),
                "soc_code": soc,
                "occupation_title": (op_title or onet_primary or "Unknown"),
                "soc_major_group_name": j.get("soc_major_group_name"),
                "stat_ern": stat_ern,
                "stat_roi": stat_roi,
                "stat_res": stat_res,
                "stat_grw": stat_grw,
                "stat_hmn": stat_hmn,
                "boss_ai_score": boss_ai,
                "boss_loans_score": boss_loans,
                "boss_market_score": boss_market,
                "boss_burnout_score": boss_burnout,
                "boss_ceiling_score": None,
                "earnings_1yr_median": template.get("earnings_1yr_median"),
                "earnings_1yr_p25": template.get("earnings_1yr_p25"),
                "earnings_1yr_p75": template.get("earnings_1yr_p75"),
                "debt_median": template.get("debt_median"),
                "debt_p25": template.get("debt_p25"),
                "debt_p75": template.get("debt_p75"),
                "debt_to_earnings_annual": template.get("debt_to_earnings_annual"),
                "confidence_tier_program": template.get("confidence_tier_program"),
                "institution_control": template.get("institution_control"),
                "net_price_annual": template.get("net_price_annual"),
                "cost_of_attendance_annual": template.get("cost_of_attendance_annual"),
                "tuition_in_state": template.get("tuition_in_state"),
                "tuition_out_of_state": template.get("tuition_out_of_state"),
                "room_board_on_campus": template.get("room_board_on_campus"),
                "median_annual_wage": j.get("median_annual_wage"),
                "growth_category": j.get("growth_category"),
                "employment_current": j.get("employment_current"),
                "education_level_name": j.get("education_level_name"),
                "top_5_activities": j.get("top_5_activities"),
                "top_human_activities": j.get("top_human_activities"),
                "burnout_drivers": j.get("burnout_drivers"),
                "match_quality": "gemma_expanded",
                "stats_available_count": stats_available,
                "bosses_available_count": bosses_available,
                "overall_confidence": "medium",
            }
            rows.append(row)
        return rows

    # ------------------------------------------------------------------
    # Fallback: CIP broadening (deterministic, fast)
    # ------------------------------------------------------------------

    def _fallback_broaden_cip(
        self,
        unitid: int,
        cipcode: str,
        loan_pct: float,
    ) -> tuple[list[dict] | None, dict | None]:
        """Try broader CIP codes when the exact cipcode has no rows.

        Returns (rows, caveat_dict) on success or (None, None) if all
        broadening attempts fail.
        """
        family = self._cip_family(cipcode)  # "50"
        cip4 = cipcode[:5] if len(cipcode) >= 5 else cipcode  # "50.04"

        # Single query for all rows at this school; filter in Python.
        all_rows = self.query_iceberg_simple(
            CAREER_PATHS_TABLE,
            filters={"unitid": unitid},
            columns=CAREER_PATHS_RESPONSE_FIELDS,
            limit=CAREER_PATHS_SCAN_LIMIT,
        )
        valid_rows = [r for r in all_rows if "error" not in r]

        # Attempt 1: Same 4-digit prefix, same school
        prefix_rows = [
            r for r in valid_rows if str(r.get("cipcode", "")).startswith(cip4)
        ]
        if prefix_rows:
            caveat = {
                "type": "cip_broadened",
                "message": (
                    f"No career data for CIP {cipcode} at this school. "
                    f"Showing results for related programs in the {cip4} family."
                ),
                "original_cipcode": cipcode,
                "broadened_to": f"{cip4}*",
            }
            return prefix_rows, caveat

        # Attempt 2: General CIP for this family (XX.0100).
        # NOTE: career_transitions (valid_rows) is stored at 4-digit
        # granularity — this equality against the 6-digit padded form
        # cannot match today and never has. Known-dead branch, retained
        # here for audit trail; canonicalizing is deferred per
        # bugfix-broad-cip-substitution-and-intent §4.
        general_cip = f"{family}.0100"
        general_rows = [
            r for r in valid_rows if str(r.get("cipcode", "")) == general_cip
        ]
        if general_rows:
            caveat = {
                "type": "cip_broadened",
                "message": (
                    f"No career data for CIP {cipcode} at this school. "
                    f"Showing results for the general {family}.0100 program."
                ),
                "original_cipcode": cipcode,
                "broadened_to": general_cip,
            }
            return general_rows, caveat

        # Attempt 3: Any CIP in this 2-digit family
        family_rows = [
            r for r in valid_rows if str(r.get("cipcode", "")).startswith(f"{family}.")
        ]
        if family_rows:
            caveat = {
                "type": "cip_broadened",
                "message": (
                    f"No career data for CIP {cipcode} at this school. "
                    f"Showing results for other programs in CIP family {family}."
                ),
                "original_cipcode": cipcode,
                "broadened_to": f"{family}.*",
            }
            return family_rows, caveat

        return None, None

    # ------------------------------------------------------------------
    # Fallback: Gemma SOC resolution (AI-estimated)
    # ------------------------------------------------------------------

    def _fallback_gemma_soc_resolution(
        self,
        unitid: int,
        cipcode: str,
        program_name: str,
        loan_pct: float,
    ) -> tuple[list[dict] | None, dict | None]:
        """Ask Gemma to map a CIP to SOC codes when the crosswalk has no coverage.

        Returns (rows, caveat_dict) on success or (None, None) if Gemma
        fails or returns no usable SOCs.
        """
        from gold.futureproof_engine import compute_stat_ern, compute_stat_roi

        try:
            from app.services.gemma_client import generate as gemma_generate
        except ImportError:
            logger.warning("gemma_client not importable — skipping Tier 2 fallback")
            return None, None

        system = (
            "You are a labor economist who maps academic programs to occupations.\n\n"
            f"Program: {program_name} (CIP {cipcode})\n\n"
            "List 5-10 SOC occupation codes that graduates of this program "
            "commonly enter. Use standard 6-character SOC codes (XX-XXXX format).\n\n"
            "Respond in JSON only, no preamble, no markdown:\n"
            '{"soc_codes": [{"soc": "XX-XXXX", "title": "Occupation Title"}, ...]}'
        )

        raw = gemma_generate(
            system=system,
            user=f"What SOC occupations do {program_name} graduates typically enter?",
            max_tokens=400,
            temperature=0.2,
        )

        if not raw:
            logger.warning(
                "Gemma SOC resolution returned empty response for CIP %s", cipcode
            )
            return None, None

        # Parse Gemma's response
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning(
                "Gemma SOC resolution returned unparseable JSON: %s", cleaned[:200]
            )
            return None, None

        soc_list = parsed.get("soc_codes", [])
        if not soc_list:
            return None, None

        # Validate SOC format
        _soc_re = re.compile(r"^\d{2}-\d{4}$")
        valid_socs = [
            s["soc"]
            for s in soc_list
            if isinstance(s, dict) and _soc_re.match(str(s.get("soc", "")))
        ]
        if not valid_socs:
            return None, None

        # Find a school earnings row for this CIP family
        family = self._cip_family(cipcode)
        co_rows = self.query_iceberg_simple(
            CAREER_OUTCOMES_TABLE,
            filters={"unitid": unitid},
            columns=_SUB_CO_FIELDS,
            limit=50,
        )
        school_row = None
        canonical_cip = self._canonical_cip4(cipcode)
        for r in co_rows:
            if "error" not in r and str(r.get("cipcode", "")) == canonical_cip:
                school_row = r
                break
        if school_row is None:
            for r in co_rows:
                if "error" not in r and str(r.get("cipcode", "")).startswith(
                    f"{family}."
                ):
                    school_row = r
                    break
        if school_row is None and co_rows and "error" not in co_rows[0]:
            school_row = co_rows[0]

        # Build rows for each valid SOC
        rows: list[dict] = []
        for soc in valid_socs:
            op_rows = self.query_iceberg_simple(
                OCCUPATION_PROFILES_TABLE,
                filters={"soc_code": soc},
                columns=_SUB_OP_FIELDS,
                limit=1,
            )
            op = op_rows[0] if op_rows and "error" not in op_rows[0] else {}
            if not op:
                continue  # SOC not in our data

            onet_rows = self.query_iceberg_simple(
                ONET_WORK_PROFILES_TABLE,
                filters={"bls_soc_code": soc},
                columns=_SUB_ONET_FIELDS,
                limit=1,
            )
            onet = onet_rows[0] if onet_rows and "error" not in onet_rows[0] else {}

            ai_rows = self.query_iceberg_simple(
                AI_EXPOSURE_TABLE_SUB,
                filters={"soc_code": soc},
                columns=_SUB_AI_FIELDS,
                limit=1,
            )
            ai = ai_rows[0] if ai_rows and "error" not in ai_rows[0] else {}

            # Blend school earnings with occupation data
            row: dict[str, Any] = {**op, **onet, **ai}
            if school_row:
                row["unitid"] = unitid
                row["institution_name"] = school_row.get("institution_name", "")
                row["cipcode"] = cipcode
                row["program_name"] = program_name
                row["earnings_1yr_median"] = school_row.get("earnings_1yr_median")
                row["earnings_1yr_p25"] = school_row.get("earnings_1yr_p25")
                row["earnings_1yr_p75"] = school_row.get("earnings_1yr_p75")
                row["debt_median"] = school_row.get("debt_median")
                row["debt_p25"] = school_row.get("debt_p25")
                row["debt_p75"] = school_row.get("debt_p75")
                row["debt_to_earnings_annual"] = school_row.get(
                    "debt_to_earnings_annual"
                )
                # Institution-level cost fields propagated through the
                # Gemma SOC-resolution fallback so callers get the same
                # ROI inputs whether the path went via crosswalk or AI.
                row["institution_control"] = school_row.get("institution_control")
                row["net_price_annual"] = school_row.get("net_price_annual")
                row["cost_of_attendance_annual"] = school_row.get(
                    "cost_of_attendance_annual"
                )
                row["net_price_4yr"] = school_row.get("net_price_4yr")
                row["tuition_in_state"] = school_row.get("tuition_in_state")
                row["tuition_out_of_state"] = school_row.get("tuition_out_of_state")
                row["room_board_on_campus"] = school_row.get("room_board_on_campus")
                ern = compute_stat_ern(
                    school_row.get("cip_family_earnings_rank"),
                    op.get("wage_percentile_overall"),
                )
                dte = school_row.get("debt_to_earnings_annual")
                if dte is not None and 0.0 <= loan_pct < 1.0:
                    dte = float(dte) * loan_pct
                roi = compute_stat_roi(dte)
                row["stat_ern"] = ern
                row["stat_roi"] = roi
            else:
                row["unitid"] = unitid
                row["cipcode"] = cipcode
                row["program_name"] = program_name

            _decode_json_struct_fields(row)
            rows.append(row)

        if not rows:
            return None, None

        rows.sort(key=lambda r: -(r.get("stats_available_count") or 0))

        gemma_soc_titles = ", ".join(
            s.get("title", s["soc"]) for s in soc_list[:5] if isinstance(s, dict)
        )
        caveat = {
            "type": "gemma_soc_resolution",
            "message": (
                f"No crosswalk data for CIP {cipcode} ({program_name}). "
                f"Career paths were identified by Gemma AI and may not reflect "
                f"typical graduate outcomes. Careers shown: {gemma_soc_titles}."
            ),
            "original_cipcode": cipcode,
            "gemma_socs": valid_socs,
            "ai_estimated": True,
        }
        return rows, caveat

    @timed(
        "career_paths_handler",
        extract=lambda result, self, input_dict: {
            "unitid": input_dict.get("unitid"),
            "cipcode": input_dict.get("cipcode"),
            "path": (
                _career_paths_result_path(result)
                if isinstance(result, dict)
                else "unknown"
            ),
            "row_count": (result.get("row_count") if isinstance(result, dict) else 0),
        },
    )
    def _handle_get_career_paths(self, input_dict: dict) -> dict:
        """Query consumable.program_career_paths by unitid + cipcode.

        Substitution signal resolution order:
        1. ``student_cip`` — caller-provided resolved CIP (e.g. from a
           Gemma intent resolution). Skips the YAML lookup entirely.
        2. ``student_major`` — free-text, resolved via
           ``_find_major_intent`` against ``major_to_cip.yaml``.
           Legacy path retained for the old ``/school`` flow and CLI
           callers that don't already hold a resolved CIP.

        When the resolved (or looked-up) CIP is specific and the
        school's reported cipcode is a broad XX.01 code in the same
        family, substitutes the specific CIP's crosswalk SOC set while
        keeping the school's broad-program earnings for the ERN/ROI
        stats. See docs/specs/cip-intent-substitution.md for the
        substitution flow.
        """
        raw_unitid = input_dict.get("unitid")
        raw_cipcode = input_dict.get("cipcode")
        raw_student_major = input_dict.get("student_major")
        raw_student_cip = input_dict.get("student_cip")
        raw_loan_pct = input_dict.get("loan_pct", 1.0)
        raw_intent_keywords = input_dict.get("intent_keywords", [])
        intent_keywords: list[str] = (
            [str(k) for k in raw_intent_keywords]
            if isinstance(raw_intent_keywords, list)
            else []
        )

        # loan_pct is optional; clamp to [0.0, 1.0] and fall back to 1.0
        # on garbage input so the tool remains permissive.
        try:
            loan_pct_value = float(raw_loan_pct)
        except (TypeError, ValueError):
            loan_pct_value = 1.0
        loan_pct_value = max(0.0, min(1.0, loan_pct_value))

        # Validate unitid: positive integer (accept string of digits too).
        unitid_value: int | None = None
        if isinstance(raw_unitid, bool):
            unitid_value = None
        elif isinstance(raw_unitid, int):
            unitid_value = raw_unitid
        elif isinstance(raw_unitid, str) and raw_unitid.strip().isdigit():
            unitid_value = int(raw_unitid.strip())
        if unitid_value is None or unitid_value <= 0:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"unitid must be a positive integer; got {raw_unitid!r}"
                    ),
                },
                CAREER_PATHS_TABLE,
            )

        # Validate cipcode format.
        cipcode = str(raw_cipcode).strip() if raw_cipcode is not None else ""
        if not cipcode or not _CIPCODE_PATTERN.match(cipcode):
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"cipcode must be in XX.XX or XX.XXXX format; "
                        f"got {raw_cipcode!r}"
                    ),
                },
                CAREER_PATHS_TABLE,
            )

        # ------------------------------------------------------------------
        # CIP intent substitution decision
        # ------------------------------------------------------------------
        student_major = (
            str(raw_student_major).strip() if raw_student_major is not None else ""
        )
        student_cip = (
            str(raw_student_cip).strip() if raw_student_cip is not None else ""
        )
        substitution_note: str | None = None
        substitution: dict | None = None  # set if substitution fires

        # Prefer an explicit resolved CIP from the caller. The new
        # /set-your-course flow passes Gemma's matched_cip directly, so
        # the YAML-backed lookup is skipped. Old /school flow callers and
        # the CLI still fall back to student_major + _find_major_intent.
        entry: dict | None = None
        entry_source: str = ""
        if student_cip and _CIPCODE_PATTERN.match(student_cip):
            entry = {
                "cip4": self._canonical_cip4(student_cip),
                # Use student_major for the human-readable label when
                # the caller provided it alongside the resolved CIP;
                # otherwise derive from the crosswalk/outcomes. This is
                # used only for the substitution caveat message.
                "major": student_major or "",
            }
            entry_source = "resolved_cip"
        elif student_major:
            entry = self._find_major_intent(student_major)
            entry_source = "yaml_lookup" if entry is not None else ""

        hint_label = student_major or student_cip
        if hint_label:
            if entry is None:
                if self._is_broad_cip(cipcode):
                    substitution_note = (
                        f"Could not map '{hint_label}' to a specific "
                        f"program. Showing results for the school's "
                        f"reported program."
                    )
                else:
                    substitution_note = (
                        f"Student hint '{hint_label}' provided but "
                        f"no match found and cipcode '{cipcode}' "
                        f"is already specific; showing reported career "
                        f"paths."
                    )
            else:
                matched_cip4 = str(entry.get("cip4") or "")
                if self._cip_family(matched_cip4) != self._cip_family(cipcode):
                    substitution_note = (
                        f"Student hint '{hint_label}' maps to CIP "
                        f"family {self._cip_family(matched_cip4)}, "
                        f"but the school's reported cipcode "
                        f"'{cipcode}' is in family "
                        f"{self._cip_family(cipcode)}. Showing the "
                        f"reported program; no substitution applied."
                    )
                elif self._is_broad_cip(cipcode) or self._matched_cip_is_more_specific(
                    cipcode, matched_cip4
                ):
                    substitution = {
                        "entry": entry,
                        "matched_cip4": matched_cip4,
                        "source": entry_source,
                    }
                else:
                    substitution_note = (
                        f"Student hint '{hint_label}' matched CIP "
                        f"'{matched_cip4}' but school cipcode "
                        f"'{cipcode}' is equally or more specific; "
                        f"showing reported career paths."
                    )

        # ------------------------------------------------------------------
        # Substituted path
        # ------------------------------------------------------------------
        if substitution is not None:
            entry = substitution["entry"]
            matched_cip4 = substitution["matched_cip4"]
            # Canonicalize the reported cipcode so the caveat and response
            # root always surface the 4-digit form regardless of what the
            # caller handed in ("52.01" vs "52.0100").
            canonical_reported = self._canonical_cip4(cipcode)
            rows, err = self._build_substituted_rows(
                unitid=unitid_value,
                reported_cipcode=cipcode,
                substituted_cipcode=matched_cip4,
                substituted_program_name=str(entry.get("major") or ""),
                loan_pct=loan_pct_value,
                intent_keywords=intent_keywords,
            )
            if err is not None:
                return self.attach_governance(
                    {"data": None, "message": err},
                    CAREER_PATHS_TABLE,
                )

            def _sub_sort_key(row: dict) -> tuple:
                stats = row.get("stats_available_count")
                stats_sort = -(stats if isinstance(stats, (int, float)) else 0)
                return (stats_sort, str(row.get("occupation_title") or ""))

            rows.sort(key=_sub_sort_key)
            for row in rows:
                _decode_json_struct_fields(row)

            # Caller may pass student_cip without student_major (new
            # Gemma-resolution flow has the CIP before the student's
            # raw text lands here). Fall back to the cip_family_name
            # from the substituted rows so the caveat still reads well.
            major_label = (
                str(entry.get("major") or "").strip()
                or (rows[0].get("cip_family_name") if rows else None)
                or f"the matched program ({matched_cip4})"
            )
            caveat = {
                "type": "blended_substitution",
                "message": (
                    f"Earnings and debt reflect all "
                    f"{(rows[0].get('cip_family_name') or 'program').lower()} "
                    f"graduates at this school. Career paths reflect "
                    f"typical {major_label} outcomes nationally. "
                    f"This school does not report "
                    f"{major_label}-specific outcome data."
                ),
                "reported_cipcode": canonical_reported,
                "substituted_cipcode": matched_cip4,
                "substituted_program": major_label,
                "earnings_specificity": "school_broad",
                "career_path_specificity": "national_major_specific",
            }

            response = {
                "data": rows,
                "row_count": len(rows),
                "substitution_applied": True,
                "reported_cipcode": canonical_reported,
                "substituted_cipcode": matched_cip4,
                "student_major": student_major,
                "data_caveat": caveat,
            }
            return self.enrich_response(response, CAREER_PATHS_TABLE)

        # ------------------------------------------------------------------
        # Standard path
        # ------------------------------------------------------------------
        # program_career_paths and career_outcomes are both stored at
        # 4-digit granularity; canonicalize once here so every downstream
        # filter and response field reflects the actual lookup key.
        canonical_cipcode = self._canonical_cip4(cipcode)
        rows = self._standard_path_rows(unitid_value, canonical_cipcode)

        if rows and "error" in rows[0]:
            return self.attach_governance(
                {"data": None, "message": rows[0]["error"]},
                CAREER_PATHS_TABLE,
            )

        if not rows:
            # ── Tier 1: CIP broadening (deterministic) ──
            broadened_rows, broadened_caveat = self._fallback_broaden_cip(
                unitid=unitid_value,
                cipcode=cipcode,
                loan_pct=loan_pct_value,
            )
            if broadened_rows:
                for r in broadened_rows:
                    _decode_json_struct_fields(r)
                broadened_rows.sort(
                    key=lambda r: (
                        -(r.get("stats_available_count") or 0),
                        str(r.get("occupation_title") or ""),
                    )
                )
                return self.enrich_response(
                    {
                        "data": broadened_rows,
                        "row_count": len(broadened_rows),
                        "substitution_applied": True,
                        "reported_cipcode": canonical_cipcode,
                        "substituted_cipcode": broadened_caveat.get("broadened_to", ""),
                        "data_caveat": broadened_caveat,
                    },
                    CAREER_PATHS_TABLE,
                )

            # ── Tier 2: Gemma SOC resolution (AI-estimated) ──
            programs = self.query_iceberg_simple(
                CAREER_OUTCOMES_TABLE,
                filters={"unitid": unitid_value, "cipcode": canonical_cipcode},
                columns=["program_name"],
                limit=1,
            )
            prog_name = (
                str(programs[0].get("program_name", cipcode))
                if programs and "error" not in programs[0]
                else student_major or cipcode
            )
            gemma_rows, gemma_caveat = self._fallback_gemma_soc_resolution(
                unitid=unitid_value,
                cipcode=cipcode,
                program_name=prog_name,
                loan_pct=loan_pct_value,
            )
            if gemma_rows:
                return self.enrich_response(
                    {
                        "data": gemma_rows,
                        "row_count": len(gemma_rows),
                        "substitution_applied": True,
                        "reported_cipcode": canonical_cipcode,
                        "data_caveat": gemma_caveat,
                    },
                    CAREER_PATHS_TABLE,
                )

            # Both fallbacks failed
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No career paths found for unitid={unitid_value}, "
                        f"cipcode='{cipcode}'. Tried CIP broadening and "
                        f"Gemma SOC resolution — no coverage available."
                    ),
                },
                CAREER_PATHS_TABLE,
            )

        # SOC expansion on the standard path: extract base SOCs from
        # pre-joined rows, call expand_socs, and build new rows for any
        # expanded SOCs using the substituted-path's dynamic JOIN.
        base_socs = [
            str(r["soc_code"]) for r in rows
            if r.get("soc_code")
        ]
        program_name_for_expansion = (
            str(rows[0].get("program_name", "")) if rows else ""
        )
        expanded_socs = self._expand_socs_if_needed(
            base_socs, intent_keywords, canonical_cipcode,
            program_name=program_name_for_expansion,
        )
        new_socs = [s for s in expanded_socs if s not in set(base_socs)]
        if new_socs:
            expanded_rows = self._build_expanded_rows(
                new_socs, rows, canonical_cipcode,
            )
            rows.extend(expanded_rows)

        def _sort_key(row: dict) -> tuple:
            stats = row.get("stats_available_count")
            # Descending stats first; stable ascending title secondary.
            stats_sort = -(stats if isinstance(stats, (int, float)) else 0)
            return (stats_sort, str(row.get("occupation_title") or ""))

        rows.sort(key=_sort_key)

        for row in rows:
            _decode_json_struct_fields(row)

        response = {
            "data": rows,
            "row_count": len(rows),
            "substitution_applied": False,
        }
        if substitution_note:
            response["substitution_note"] = substitution_note
        return self.enrich_response(response, CAREER_PATHS_TABLE)

    # ------------------------------------------------------------------
    # Tool handler: get_occupation_data
    # ------------------------------------------------------------------

    def _handle_get_occupation_data(self, input_dict: dict) -> dict:
        """Query consumable.occupation_profiles for a single SOC code."""
        raw_soc = input_dict.get("soc_code")
        soc_code = str(raw_soc).strip() if raw_soc is not None else ""
        if not soc_code:
            return {
                "data": None,
                "message": "soc_code is required",
            }
        if not _SOC_CODE_PATTERN.match(soc_code):
            return self.attach_governance(
                {
                    "data": None,
                    "message": (f"soc_code must be in XX-XXXX format; got {raw_soc!r}"),
                },
                OCCUPATION_DATA_TABLE,
            )

        rows = self.query_iceberg_simple(
            OCCUPATION_DATA_TABLE,
            filters={"soc_code": soc_code},
            columns=OCCUPATION_DATA_RESPONSE_FIELDS,
            limit=1,
        )

        if rows and "error" in rows[0]:
            return self.attach_governance(
                {"data": None, "message": rows[0]["error"]},
                OCCUPATION_DATA_TABLE,
            )

        if not rows:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (f"No occupation data for SOC code '{soc_code}'"),
                },
                OCCUPATION_DATA_TABLE,
            )

        return self.enrich_response(
            {"data": rows[0], "row_count": 1},
            OCCUPATION_DATA_TABLE,
        )

    # ------------------------------------------------------------------
    # Tool handler: get_task_breakdown
    # ------------------------------------------------------------------

    def _handle_get_task_breakdown(self, input_dict: dict) -> dict:
        """Query consumable.onet_work_profiles by bls_soc_code.

        The O*NET Gold table uses ``bls_soc_code`` as its SOC identifier,
        not ``soc_code``. Callers still pass ``soc_code`` for parity with
        the other tools; the handler translates.
        """
        raw_soc = input_dict.get("soc_code")
        soc_code = str(raw_soc).strip() if raw_soc is not None else ""
        if not soc_code:
            return {
                "data": None,
                "message": "soc_code is required",
            }
        if not _SOC_CODE_PATTERN.match(soc_code):
            return self.attach_governance(
                {
                    "data": None,
                    "message": (f"soc_code must be in XX-XXXX format; got {raw_soc!r}"),
                },
                TASK_BREAKDOWN_TABLE,
            )

        rows = self.query_iceberg_simple(
            TASK_BREAKDOWN_TABLE,
            filters={"bls_soc_code": soc_code},
            columns=TASK_BREAKDOWN_RESPONSE_FIELDS,
            limit=1,
        )

        if rows and "error" in rows[0]:
            return self.attach_governance(
                {"data": None, "message": rows[0]["error"]},
                TASK_BREAKDOWN_TABLE,
            )

        if not rows:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (f"No O*NET task data for SOC code '{soc_code}'"),
                },
                TASK_BREAKDOWN_TABLE,
            )

        return self.enrich_response(
            {"data": _decode_json_struct_fields(rows[0]), "row_count": 1},
            TASK_BREAKDOWN_TABLE,
        )

    # ------------------------------------------------------------------
    # Tool handler: get_career_branches
    # ------------------------------------------------------------------

    def _handle_get_career_branches(self, input_dict: dict) -> dict:
        """Query consumable.career_branches by source SOC code."""
        raw_soc = input_dict.get("soc_code")
        soc_code = str(raw_soc).strip() if raw_soc is not None else ""
        if not soc_code:
            return {
                "data": None,
                "message": "soc_code is required",
            }
        if not _SOC_CODE_PATTERN.match(soc_code):
            return self.attach_governance(
                {
                    "data": None,
                    "message": (f"soc_code must be in XX-XXXX format; got {raw_soc!r}"),
                },
                CAREER_BRANCHES_TABLE,
            )

        # Default primary_only=True per spec.
        primary_only_raw = input_dict.get("primary_only", True)
        primary_only = bool(primary_only_raw) if primary_only_raw is not None else True

        rows = self.query_iceberg_simple(
            CAREER_BRANCHES_TABLE,
            filters={"soc_code": soc_code},
            columns=CAREER_BRANCHES_RESPONSE_FIELDS,
            limit=CAREER_BRANCHES_SCAN_LIMIT,
        )

        if rows and "error" in rows[0]:
            return self.attach_governance(
                {"data": None, "message": rows[0]["error"]},
                CAREER_BRANCHES_TABLE,
            )

        if primary_only:
            rows = [r for r in rows if bool(r.get("is_primary"))]

        if not rows:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No career branches found for SOC code '{soc_code}'. "
                        f"This occupation may not have transition data in O*NET."
                    ),
                },
                CAREER_BRANCHES_TABLE,
            )

        def _best_index_key(row: dict) -> float:
            val = row.get("best_index")
            if isinstance(val, (int, float)):
                return float(val)
            return float("inf")

        rows.sort(key=_best_index_key)
        rows = rows[:CAREER_BRANCHES_MAX_ROWS]

        return self.enrich_response(
            {"data": rows, "row_count": len(rows)},
            CAREER_BRANCHES_TABLE,
        )

    # ------------------------------------------------------------------
    # Tool handler: get_schools_for_career
    # ------------------------------------------------------------------

    @timed(
        "get_schools_for_career",
        extract=lambda result, self, input_dict, *a, **kw: {
            "mode": str(input_dict.get("mode", "by_soc")),
            "soc_code": str(input_dict.get("soc_code", "")),
            "cipcode": str(input_dict.get("cipcode") or ""),
            "row_count": len(result.get("rows") or [])
            if isinstance(result, dict)
            else 0,
        },
    )
    def _handle_get_schools_for_career(self, input_dict: dict) -> dict:
        """Career-anchored leaderboard query.

        Materializes a single windowed CTE (``RANK() OVER`` on
        ``(stat_ern + stat_roi)/2``) over ``consumable.program_career_paths``
        filtered by SOC (and optionally CIP), confidence floors, and state.
        Returns the top-N rows with ``is_anchor`` flagged when the optional
        anchor (``build_unitid``, ``build_cipcode``) lands in the top-N, or
        appended at index N when the anchor is below it but still in the
        ranked universe. See feature-compare-schools-for-career.md §4.
        """
        # ---- Parse + validate inputs ----------------------------------
        raw_mode = input_dict.get("mode", "by_soc")
        mode = str(raw_mode).strip() if raw_mode is not None else "by_soc"
        if mode not in _LEADERBOARD_MODES:
            return {
                "error": f"mode must be one of {list(_LEADERBOARD_MODES)}; got {raw_mode!r}",
            }

        raw_soc = input_dict.get("soc_code")
        soc_code = str(raw_soc).strip() if raw_soc is not None else ""
        if not soc_code or not _SOC_CODE_PATTERN.match(soc_code):
            return {
                "error": f"soc_code must be in XX-XXXX format; got {raw_soc!r}",
            }

        raw_cipcode = input_dict.get("cipcode")
        cipcode: str | None = (
            str(raw_cipcode).strip() if raw_cipcode is not None else None
        )
        if cipcode == "":
            cipcode = None
        if cipcode is not None and not _CIPCODE_PATTERN.match(cipcode):
            return {
                "error": f"cipcode must be in XX.XX or XX.XXXX format; got {raw_cipcode!r}",
            }
        if mode == "by_cip_and_soc" and not cipcode:
            return {
                "error": "cipcode is required when mode='by_cip_and_soc'",
            }

        raw_limit = input_dict.get("limit", 5)
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError):
            limit = 5
        limit = max(1, min(limit, 25))

        raw_min_conf = input_dict.get("min_confidence", "medium")
        min_confidence = str(raw_min_conf).strip().lower() if raw_min_conf else "medium"
        if min_confidence not in _CONFIDENCE_TIERS_DESC:
            min_confidence = "medium"

        raw_min_prog = input_dict.get("min_program_confidence", "low")
        min_program_confidence = (
            str(raw_min_prog).strip().lower() if raw_min_prog else "low"
        )
        if min_program_confidence not in _CONFIDENCE_TIERS_DESC:
            min_program_confidence = "low"

        raw_state = input_dict.get("state_abbr")
        state_abbr: str | None = None
        if raw_state is not None:
            candidate = str(raw_state).strip().upper()
            if len(candidate) == 2 and candidate.isalpha():
                state_abbr = candidate

        raw_unitid = input_dict.get("build_unitid")
        raw_anchor_cip = input_dict.get("build_cipcode")
        anchor_unitid: int | None = None
        anchor_cipcode: str | None = None
        if raw_unitid is not None and raw_anchor_cip is not None:
            try:
                if isinstance(raw_unitid, bool):
                    raise TypeError
                if isinstance(raw_unitid, int):
                    anchor_unitid_candidate: int | None = raw_unitid
                elif isinstance(raw_unitid, str) and raw_unitid.strip().isdigit():
                    anchor_unitid_candidate = int(raw_unitid.strip())
                else:
                    raise ValueError
                anchor_cip_candidate = str(raw_anchor_cip).strip()
                if (
                    anchor_unitid_candidate is not None
                    and anchor_unitid_candidate > 0
                    and _CIPCODE_PATTERN.match(anchor_cip_candidate)
                ):
                    anchor_unitid = anchor_unitid_candidate
                    anchor_cipcode = anchor_cip_candidate
            except (TypeError, ValueError):
                anchor_unitid = None
                anchor_cipcode = None

        # Build-time stats for the anchor row. Used to compute
        # ``anchor_estimated_rank`` when the (unitid, cipcode) is absent
        # from the filtered universe — typical for builds whose career
        # was produced via CIP substitution and never materialized into
        # PCP. Both must be 0-10 ints; bools and out-of-range values
        # silently drop so a malformed query degrades to "no estimate"
        # instead of erroring the whole leaderboard.
        anchor_stat_ern: int | None = None
        anchor_stat_roi: int | None = None
        for stat_key in ("anchor_stat_ern", "anchor_stat_roi"):
            raw_stat = input_dict.get(stat_key)
            if raw_stat is None or isinstance(raw_stat, bool):
                continue
            if isinstance(raw_stat, int):
                stat_candidate: int | None = raw_stat
            elif (
                isinstance(raw_stat, str)
                and raw_stat.strip().lstrip("-").isdigit()
            ):
                stat_candidate = int(raw_stat.strip())
            else:
                stat_candidate = None
            if stat_candidate is None or not (0 <= stat_candidate <= 10):
                continue
            if stat_key == "anchor_stat_ern":
                anchor_stat_ern = stat_candidate
            else:
                anchor_stat_roi = stat_candidate

        # ---- Cache lookup ---------------------------------------------
        engine = self._get_query_engine()
        cache_key = (
            id(engine),
            mode,
            soc_code,
            cipcode or "",
            min_confidence,
            min_program_confidence,
            state_abbr or "",
            limit,
        )
        cache_enabled = os.environ.get("FUTUREPROOF_OUTCOMES_CACHE") == "1"
        materialized: list[dict] | None = None
        if cache_enabled:
            cached, hit = _cache_get(_schools_for_career_cache, cache_key)
            if hit:
                materialized = [dict(r) for r in cached]

        # ---- Run the windowed query if not cached ---------------------
        if materialized is None:
            allowed_overall = _confidence_floor_to_set(min_confidence)
            allowed_program = (
                _confidence_floor_to_set(min_program_confidence)
                if min_program_confidence != "low"
                else None
            )

            where_parts = [
                "soc_code = $soc_code",
                "stat_ern IS NOT NULL",
                "stat_roi IS NOT NULL",
            ]
            params: dict[str, Any] = {"soc_code": soc_code}
            if cipcode is not None and mode == "by_cip_and_soc":
                where_parts.append("cipcode = $cipcode")
                params["cipcode"] = cipcode
            if state_abbr is not None:
                where_parts.append("state_abbr = $state_abbr")
                params["state_abbr"] = state_abbr
            if allowed_overall:
                where_parts.append(
                    "overall_confidence IN ("
                    + ", ".join(f"'{tier}'" for tier in allowed_overall)
                    + ")"
                )
            if allowed_program:
                where_parts.append(
                    "confidence_tier_program IN ("
                    + ", ".join(f"'{tier}'" for tier in allowed_program)
                    + ")"
                )
            where_clause = " AND ".join(where_parts)

            sql = f"""
                WITH ranked AS (
                    SELECT
                        unitid,
                        institution_name,
                        institution_control,
                        state_abbr,
                        cipcode,
                        program_name,
                        soc_code,
                        occupation_title,
                        stat_ern,
                        stat_roi,
                        earnings_1yr_median,
                        net_price_annual,
                        cost_of_attendance_annual,
                        tuition_in_state,
                        tuition_out_of_state,
                        overall_confidence,
                        confidence_tier_program,
                        match_quality,
                        (CAST(stat_ern AS DOUBLE)
                         + CAST(stat_roi AS DOUBLE)) / 2.0 AS composite_score,
                        RANK() OVER (
                            ORDER BY
                                (CAST(stat_ern AS DOUBLE)
                                 + CAST(stat_roi AS DOUBLE)) / 2.0 DESC,
                                earnings_1yr_median DESC NULLS LAST,
                                net_price_annual ASC NULLS LAST
                        ) AS abs_rank
                    FROM consumable_program_career_paths
                    WHERE {where_clause}
                )
                SELECT * FROM ranked
                ORDER BY abs_rank
                LIMIT {SCHOOLS_FOR_CAREER_SCAN_LIMIT}
            """
            try:
                rows = engine.query_sql(sql, params)
            except Exception:  # noqa: BLE001
                # Log full trace server-side; return an opaque code to the
                # caller so DuckDB internals (table names, version,
                # stack-frame fragments) don't leak through the HTTP/chat
                # response. Per code-review Finding 2.
                logger.exception(
                    "get_schools_for_career SQL failed",
                    extra={
                        "mode": mode,
                        "soc_code": soc_code,
                        "cipcode": cipcode or "",
                    },
                )
                return {"error": "leaderboard_query_failed"}
            materialized = [dict(r) for r in rows]
            if cache_enabled:
                snapshot = tuple(dict(r) for r in materialized)
                _cache_put(
                    _schools_for_career_cache,
                    cache_key,
                    snapshot,
                    _SCHOOLS_FOR_CAREER_CACHE_MAX,
                )

        total_qualifying_programs = len(materialized)

        # ---- Top-N selection + anchor handling ------------------------
        top_n = [dict(r) for r in materialized[:limit]]

        anchor_in_top_n = False
        anchor_found_in_universe = False
        if anchor_unitid is not None and anchor_cipcode is not None:
            in_top_n = False
            for row in top_n:
                if (
                    row.get("unitid") == anchor_unitid
                    and str(row.get("cipcode")) == anchor_cipcode
                ):
                    row["is_anchor"] = True
                    in_top_n = True
                    anchor_in_top_n = True
                    anchor_found_in_universe = True
                    break
            if not in_top_n:
                appended = next(
                    (
                        dict(r)
                        for r in materialized
                        if r.get("unitid") == anchor_unitid
                        and str(r.get("cipcode")) == anchor_cipcode
                    ),
                    None,
                )
                if appended is not None:
                    appended["is_anchor"] = True
                    top_n.append(appended)
                    anchor_found_in_universe = True

        # ---- Estimated rank for anchors absent from PCP ---------------
        # When the build engine produced the anchor's career via CIP
        # substitution (so PCP has no row for that combination), but the
        # caller passed the build's stat_ern + stat_roi, count rows in
        # the same filtered universe whose composite score outranks the
        # build's. Tied scores rank equally (stable RANK semantics) —
        # matches the CTE's RANK() OVER ordering on composite_score DESC.
        anchor_estimated_rank: int | None = None
        if (
            not anchor_found_in_universe
            and anchor_unitid is not None
            and anchor_cipcode is not None
            and anchor_stat_ern is not None
            and anchor_stat_roi is not None
        ):
            anchor_composite = (anchor_stat_ern + anchor_stat_roi) / 2.0
            higher = sum(
                1
                for r in materialized
                if r.get("composite_score") is not None
                and float(r["composite_score"]) > anchor_composite
            )
            anchor_estimated_rank = higher + 1

        # ---- Mode-aware envelope fields -------------------------------
        occupation_title = ""
        program_name: str | None = None
        if materialized:
            occupation_title = str(materialized[0].get("occupation_title") or "")
            if mode == "by_cip_and_soc":
                program_name = str(materialized[0].get("program_name") or "")
        elif top_n:
            occupation_title = str(top_n[0].get("occupation_title") or "")

        # ---- Trim to MCP whitelist + assign ranks ---------------------
        # The HTTP endpoint reads the full row shape; the MCP/chat path
        # keeps a tighter whitelist (drops tuition + cost_of_attendance) per
        # genai-architect R4. The handler always emits the HTTP shape; the
        # service layer is the boundary. For a chat-originated call the
        # caller can post-filter to the MCP whitelist, but the simplest
        # honest move at v1 is to let the handler emit the HTTP shape and
        # let downstream callers project. We document both whitelists at
        # the top of the file.
        wire_rows = []
        for row in top_n:
            row.setdefault("is_anchor", False)
            row["rank"] = int(row.get("abs_rank") or 0)
            wire_rows.append(
                {k: row.get(k) for k in SCHOOLS_FOR_CAREER_RESPONSE_FIELDS_HTTP}
            )

        return {
            "mode": mode,
            "soc_code": soc_code,
            "occupation_title": occupation_title,
            "cipcode": cipcode if mode == "by_cip_and_soc" else None,
            "program_name": program_name,
            "rows": wire_rows,
            "anchor_in_top_n": anchor_in_top_n,
            "total_qualifying_programs": total_qualifying_programs,
            "anchor_estimated_rank": anchor_estimated_rank,
            "confidence_filter_applied": min_confidence,
            "state_filter_applied": state_abbr,
            "min_program_confidence_applied": min_program_confidence,
            # ISO 8601 string per genai-architect R6 — never a raw datetime
            # object across the MCP serialization boundary.
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


def _confidence_floor_to_set(floor: str) -> tuple[str, ...]:
    """Map a confidence floor to the inclusive set above it.

    'high' -> ('high',); 'medium' -> ('high', 'medium');
    'low' -> ('high', 'medium', 'low').
    """
    order = ("high", "medium", "low")
    if floor not in order:
        return order
    cutoff = order.index(floor) + 1
    return order[:cutoff]
