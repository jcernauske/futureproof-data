"""FutureProof MCP server — exposes governed education + career data to AI agents.

Extends Brightsmith's BaseMCPServer with domain-specific tools for
querying AI exposure scores, occupation profiles, career outcomes, and
regional price parities.

Start with: python -m brightsmith.serve
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

# Fields in program_career_paths and onet_work_profiles that are
# persisted as JSON-encoded strings but should be returned to callers
# as native Python objects.
_JSON_STRUCT_FIELDS = (
    "top_5_activities",
    "top_human_activities",
    "burnout_drivers",
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

import yaml
from brightsmith.mcp.base_mcp_server import BaseMCPServer, ResourceDef, ToolDef

from mcp_server._state_input import FIPS_TO_STATE_NAME, normalize_state_input

logger = logging.getLogger(__name__)

# Response fields returned by get_ai_exposure (excludes record_id, promoted_at)
AI_EXPOSURE_RESPONSE_FIELDS = [
    "soc_code",
    "occupation_title",
    "exposure_score",
    "stat_res",
    "boss_ai_score",
    "rationale",
    "category",
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
    "debt_to_earnings_annual",
    "debt_to_earnings_tier",
    "program_value_index",
    "confidence_tier",
    "has_earnings",
    "has_debt",
    "outcome_completeness",
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
]

# Load cap when scanning program_career_paths for a single unitid+cipcode
# combo. A school+major produces 5-20 rows in practice, but we scan
# without filters then filter in Python to support composite keys.
CAREER_PATHS_SCAN_LIMIT = 500_000

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
    "debt_to_earnings_annual",
    "cip_family_earnings_rank",
    "confidence_tier",
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


class FutureProofMCPServer(BaseMCPServer):
    """MCP server for the FutureProof education + career pipeline.

    Exposes domain-specific tools on top of the framework-provided
    query_table, list_tables, get_data_quality, get_lineage, and
    get_contract tools.
    """

    def get_tools(self) -> list[ToolDef]:
        return [
            ToolDef(
                name="get_ai_exposure",
                description=(
                    "Get AI exposure data for an occupation by SOC code. "
                    "Returns the Karpathy AI exposure score (0-10), the derived "
                    "AI Resilience stat (stat_res, 1-10), the Fight AI boss "
                    "strength (boss_ai_score, 1-10), a rationale explaining "
                    "the score, and the BLS category. Higher exposure_score "
                    "means more AI-exposed; higher stat_res means more resilient."
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
                    "to filter out suppressed/low-data programs."
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
                    "Results are sorted by stats_available_count DESC so "
                    "best-data careers come first. Zero results means the "
                    "program lacks CIP-SOC crosswalk coverage. When the "
                    "school only reports a broad XX.01 CIP, pass "
                    "student_major to substitute the major-specific SOC "
                    "set while preserving the school's broad-program "
                    "earnings for ERN/ROI."
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
            {"data": rows[0], "row_count": 1},
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
        min_confidence = str(input_dict.get("min_confidence") or "insufficient").strip().lower()
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
                    r for r in rows
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
            r for r in rows
            if str(r.get("institution_name") or "").lower().find(needle_lower) >= 0
            and self._confidence_tier_allowed(
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
        """
        if self._major_to_cip_cache is not None:
            return self._major_to_cip_cache
        try:
            from brightsmith.config import PROJECT_ROOT
            root = Path(PROJECT_ROOT)
        except Exception:
            root = Path.cwd()
        path = root / MAJOR_TO_CIP_LOOKUP_PATH
        if not path.exists():
            logger.warning("major_to_cip.yaml not found at %s", path)
            self._major_to_cip_cache = []
            return self._major_to_cip_cache
        try:
            with path.open() as f:
                data = yaml.safe_load(f) or []
            if not isinstance(data, list):
                logger.warning(
                    "major_to_cip.yaml has unexpected shape; expected list"
                )
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
    def _cip_family(cipcode: str) -> str:
        """Return the 2-digit family prefix of a CIP code."""
        return cipcode.split(".", 1)[0] if "." in cipcode else cipcode[:2]

    def _fetch_crosswalk_socs(self, cip4: str) -> list[str]:
        """Return distinct SOC codes for a 4-digit CIP prefix.

        The base.cip_soc_crosswalk view is registered by query_iceberg as
        ``base_cip_soc_crosswalk``. Rows with NULL or catch-all SOCs
        ('99-9999') are excluded.
        """
        # Sanity-check the prefix before formatting into SQL. This value
        # comes from our own YAML file but we still treat it as
        # untrusted input to prevent injection.
        if not re.match(r"^\d{2}\.\d{2}$", cip4):
            return []
        sql = (
            "SELECT DISTINCT soc_code FROM base_cip_soc_crosswalk "
            f"WHERE SUBSTR(cipcode, 1, 5) = '{cip4}' "
            "AND soc_code IS NOT NULL AND soc_code <> '99-9999' "
            "ORDER BY soc_code"
        )
        try:
            rows = self.query_iceberg(sql)
        except Exception as e:  # noqa: BLE001
            logger.warning("Crosswalk lookup failed for %s: %s", cip4, e)
            return []
        return [str(r["soc_code"]) for r in rows if r.get("soc_code")]

    def _build_substituted_rows(
        self,
        *,
        unitid: int,
        reported_cipcode: str,
        substituted_cipcode: str,
        substituted_program_name: str,
        loan_pct: float = 1.0,
    ) -> tuple[list[dict] | None, str | None]:
        """Assemble blended career-path rows for a substitution.

        Pulls the school's broad-CIP row from career_outcomes for the
        earnings/debt basis, fetches the substituted CIP's SOCs from
        the crosswalk, and joins occupation_profiles + onet_work_profiles
        + ai_exposure for each SOC to compute the 5-stat pentagon.

        Returns (rows, None) on success or (None, message) on failure
        (e.g. school's broad-CIP row missing, crosswalk empty).
        """
        # Lazy import to avoid a hard dependency on the gold module at
        # server import time.
        from gold.futureproof_engine import compute_stat_ern, compute_stat_roi

        # 1. School's broad-CIP row from career_outcomes.
        co_rows = self.query_iceberg_simple(
            CAREER_OUTCOMES_TABLE,
            filters={"unitid": unitid, "cipcode": reported_cipcode},
            columns=_SUB_CO_FIELDS,
            limit=1,
        )
        if co_rows and "error" in co_rows[0]:
            return None, co_rows[0]["error"]
        if not co_rows:
            return None, (
                f"No career_outcomes row for unitid={unitid}, "
                f"cipcode='{reported_cipcode}'; cannot substitute."
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
                f"No crosswalk SOCs found for substituted CIP "
                f"'{substituted_cipcode}'."
            )

        # 3. For each SOC, join occupation_profiles, onet, ai_exposure.
        rows: list[dict] = []
        for soc in socs:
            op_rows = self.query_iceberg_simple(
                OCCUPATION_PROFILES_TABLE,
                filters={"soc_code": soc},
                columns=_SUB_OP_FIELDS,
                limit=1,
            )
            op = (
                op_rows[0]
                if op_rows and "error" not in op_rows[0]
                else {}
            )

            onet_rows = self.query_iceberg_simple(
                ONET_WORK_PROFILES_TABLE,
                filters={"bls_soc_code": soc},
                columns=_SUB_ONET_FIELDS,
                limit=1,
            )
            onet = (
                onet_rows[0]
                if onet_rows and "error" not in onet_rows[0]
                else {}
            )

            ai_rows = self.query_iceberg_simple(
                AI_EXPOSURE_TABLE_SUB,
                filters={"soc_code": soc},
                columns=_SUB_AI_FIELDS,
                limit=1,
            )
            ai = (
                ai_rows[0]
                if ai_rows and "error" not in ai_rows[0]
                else {}
            )

            stat_ern = compute_stat_ern(
                cip_fam_rank, op.get("wage_percentile_overall")
            )
            stat_roi = compute_stat_roi(adj_dte)
            boss_loans_sub = (
                (11 - stat_roi) if stat_roi is not None else None
            )
            stat_grw = op.get("grw_score_rounded")
            stat_hmn = onet.get("hmn_score_rounded")
            stat_res = ai.get("stat_res")

            stats_available = sum(
                1
                for v in (stat_ern, stat_roi, stat_res, stat_grw, stat_hmn)
                if v is not None
            )
            boss_ai = ai.get("boss_ai_score")
            boss_market = op.get("market_score_rounded")
            boss_burnout = onet.get("burnout_score_rounded")
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
                "occupation_title": (
                    op.get("occupation_title")
                    or onet.get("primary_title")
                    or None
                ),
                "soc_major_group_name": op.get("soc_major_group_name"),
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
                "debt_to_earnings_annual": school.get(
                    "debt_to_earnings_annual"
                ),
                "confidence_tier_program": school.get("confidence_tier"),
                "median_annual_wage": op.get("median_annual_wage"),
                "growth_category": op.get("growth_category"),
                "employment_current": op.get("employment_current"),
                "education_level_name": op.get("education_level_name"),
                "top_5_activities": onet.get("top_5_activities"),
                "top_human_activities": onet.get("top_human_activities"),
                "burnout_drivers": onet.get("burnout_drivers"),
                "match_quality": "substituted_cip",
                "stats_available_count": stats_available,
                "bosses_available_count": bosses_available,
                "overall_confidence": (
                    "high" if stats_available == 5 else "medium"
                ),
            }
            rows.append(row)
        return rows, None

    def _handle_get_career_paths(self, input_dict: dict) -> dict:
        """Query consumable.program_career_paths by unitid + cipcode.

        When ``student_major`` is provided and the school's reported
        cipcode is a broad XX.01 code, substitutes the matched specific
        CIP's crosswalk SOC set while keeping the school's broad-program
        earnings for the ERN/ROI stats. See docs/specs/
        cip-intent-substitution.md for the full flow.
        """
        raw_unitid = input_dict.get("unitid")
        raw_cipcode = input_dict.get("cipcode")
        raw_student_major = input_dict.get("student_major")
        raw_loan_pct = input_dict.get("loan_pct", 1.0)

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
        cipcode = (str(raw_cipcode).strip() if raw_cipcode is not None else "")
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
            str(raw_student_major).strip()
            if raw_student_major is not None
            else ""
        )
        substitution_note: str | None = None
        substitution: dict | None = None  # set if substitution fires

        if student_major:
            if not self._is_broad_cip(cipcode):
                # School already reports the specific CIP — standard path.
                substitution_note = (
                    f"student_major='{student_major}' provided but cipcode "
                    f"'{cipcode}' is already specific; showing reported "
                    f"career paths."
                )
            else:
                entry = self._find_major_intent(student_major)
                if entry is None:
                    substitution_note = (
                        f"Could not map '{student_major}' to a specific "
                        f"program. Showing results for the school's "
                        f"reported program."
                    )
                else:
                    matched_cip4 = str(entry.get("cip4") or "")
                    if self._cip_family(matched_cip4) != self._cip_family(
                        cipcode
                    ):
                        substitution_note = (
                            f"Student major '{student_major}' maps to CIP "
                            f"family {self._cip_family(matched_cip4)}, "
                            f"but the school's reported cipcode "
                            f"'{cipcode}' is in family "
                            f"{self._cip_family(cipcode)}. Showing the "
                            f"reported program; no substitution applied."
                        )
                    else:
                        substitution = {
                            "entry": entry,
                            "matched_cip4": matched_cip4,
                        }

        # ------------------------------------------------------------------
        # Substituted path
        # ------------------------------------------------------------------
        if substitution is not None:
            entry = substitution["entry"]
            matched_cip4 = substitution["matched_cip4"]
            rows, err = self._build_substituted_rows(
                unitid=unitid_value,
                reported_cipcode=cipcode,
                substituted_cipcode=matched_cip4,
                substituted_program_name=str(entry.get("major") or ""),
                loan_pct=loan_pct_value,
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

            caveat = {
                "type": "blended_substitution",
                "message": (
                    f"Earnings and debt reflect all "
                    f"{(rows[0].get('cip_family_name') or 'program').lower()} "
                    f"graduates at this school. Career paths reflect "
                    f"typical {entry.get('major')} outcomes nationally. "
                    f"This school does not report "
                    f"{entry.get('major')}-specific outcome data."
                ),
                "reported_cipcode": cipcode,
                "substituted_cipcode": matched_cip4,
                "substituted_program": entry.get("major"),
                "earnings_specificity": "school_broad",
                "career_path_specificity": "national_major_specific",
            }

            response = {
                "data": rows,
                "row_count": len(rows),
                "substitution_applied": True,
                "reported_cipcode": cipcode,
                "substituted_cipcode": matched_cip4,
                "student_major": student_major,
                "data_caveat": caveat,
            }
            return self.enrich_response(response, CAREER_PATHS_TABLE)

        # ------------------------------------------------------------------
        # Standard path
        # ------------------------------------------------------------------
        rows = self.query_iceberg_simple(
            CAREER_PATHS_TABLE,
            filters={"unitid": unitid_value, "cipcode": cipcode},
            columns=CAREER_PATHS_RESPONSE_FIELDS,
            limit=CAREER_PATHS_SCAN_LIMIT,
        )

        if rows and "error" in rows[0]:
            return self.attach_governance(
                {"data": None, "message": rows[0]["error"]},
                CAREER_PATHS_TABLE,
            )

        if not rows:
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"No career paths found for unitid={unitid_value}, "
                        f"cipcode='{cipcode}'. This program may not have "
                        f"crosswalk coverage."
                    ),
                },
                CAREER_PATHS_TABLE,
            )

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
        soc_code = (str(raw_soc).strip() if raw_soc is not None else "")
        if not soc_code:
            return {
                "data": None,
                "message": "soc_code is required",
            }
        if not _SOC_CODE_PATTERN.match(soc_code):
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"soc_code must be in XX-XXXX format; got {raw_soc!r}"
                    ),
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
                    "message": (
                        f"No occupation data for SOC code '{soc_code}'"
                    ),
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
        soc_code = (str(raw_soc).strip() if raw_soc is not None else "")
        if not soc_code:
            return {
                "data": None,
                "message": "soc_code is required",
            }
        if not _SOC_CODE_PATTERN.match(soc_code):
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"soc_code must be in XX-XXXX format; got {raw_soc!r}"
                    ),
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
                    "message": (
                        f"No O*NET task data for SOC code '{soc_code}'"
                    ),
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
        soc_code = (str(raw_soc).strip() if raw_soc is not None else "")
        if not soc_code:
            return {
                "data": None,
                "message": "soc_code is required",
            }
        if not _SOC_CODE_PATTERN.match(soc_code):
            return self.attach_governance(
                {
                    "data": None,
                    "message": (
                        f"soc_code must be in XX-XXXX format; got {raw_soc!r}"
                    ),
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
