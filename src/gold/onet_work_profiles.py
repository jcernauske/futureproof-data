"""Gold zone transformer for consumable.onet_work_profiles.

Reads base.onet_occupations, base.onet_activity_profiles, and
base.onet_context_profiles from Silver. Pivots activity/context
rows into one row per occupation with HMN score (min/max rescaled),
Burnout score, JSON summaries, and confidence tier. Promotes to
consumable.onet_work_profiles.

Grain: bls_soc_code
Record ID: compute_grain_id(row, ['bls_soc_code'], prefix='wp')
"""

import datetime
import json
import logging
import math
from pathlib import Path

import duckdb
from pyiceberg.schema import Schema
from pyiceberg.types import (
    BooleanType,
    DateType,
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import get_catalog, get_or_create_table
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

SPEC_NAME = "gold-onet-profiles"
GRAIN_FIELDS = ["bls_soc_code"]
GRAIN_PREFIX = "wp"

# ---------------------------------------------------------------------------
# Human-intensive activity element IDs (EDA-corrected).
# 14 of 41 Generalized Work Activities classified as human-intensive.
# ---------------------------------------------------------------------------

HUMAN_INTENSIVE_ELEMENT_IDS = [
    "4.A.4.b.4",  # Guiding, Directing, and Motivating Subordinates
    "4.A.4.b.5",  # Coaching and Developing Others
    "4.A.4.a.7",  # Resolving Conflicts and Negotiating with Others
    "4.A.4.a.8",  # Performing for or Working Directly with the Public
    "4.A.4.a.4",  # Establishing and Maintaining Interpersonal Relationships
    "4.A.4.b.2",  # Developing and Building Teams
    "4.A.4.b.3",  # Training and Teaching Others
    "4.A.4.a.6",  # Selling or Influencing Others
    "4.A.4.b.1",  # Coordinating the Work and Activities of Others
    "4.A.2.b.2",  # Thinking Creatively
    "4.A.2.b.1",  # Making Decisions and Solving Problems
    "4.A.3.a.1",  # Performing General Physical Activities
    "4.A.3.a.2",  # Handling and Moving Objects
    "4.A.4.a.5",  # Assisting and Caring for Others
]

# Burnout element IDs (documented; implementation uses is_burnout_element flag)
BURNOUT_ELEMENT_IDS = [
    "4.C.3.d.1",   # Time Pressure (CX)
    "4.C.3.d.8",   # Duration of Typical Work Week (CT)
    "4.C.3.a.1",   # Consequence of Error (CX)
    "4.C.3.d.3",   # Pace Determined by Speed of Equipment (CX)
    "4.C.3.a.2.b", # Frequency of Decision Making (CX)
    "4.C.3.b.4",   # Importance of Being Exact or Accurate (CX)
    "4.C.3.b.7",   # Importance of Repeating Same Tasks (CX)
    "4.C.3.d.4",   # Work Schedules (CT)
    "4.C.3.a.2.a", # Impact of Decisions on Co-workers (CX)
]

# Individual burnout elements to extract as standalone columns
TIME_PRESSURE_ID = "4.C.3.d.1"
WORK_HOURS_ID = "4.C.3.d.8"
CONSEQUENCE_OF_ERROR_ID = "4.C.3.a.1"


def _round_half_up(x: float) -> int:
    """Round to nearest integer using round-half-up (standard) rounding.

    Python's built-in round() uses banker's rounding (round half to even),
    which differs from DuckDB's ROUND(). This function matches DuckDB.
    """
    return int(math.floor(x + 0.5))


def _normalize_context_value(value: float, scale_id: str) -> float:
    """Normalize a context value to 0-1 range based on scale type.

    CX scale: 1-5 -> (value - 1) / 4
    CT scale: 1-3 -> (value - 1) / 2
    """
    if scale_id == "CX":
        return (value - 1.0) / 4.0
    elif scale_id == "CT":
        return (value - 1.0) / 2.0
    else:
        raise ValueError(f"Unknown scale_id: {scale_id}")


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.onet_work_profiles (27 columns)."""
    return Schema(
        # Occupation Identity (Carried from Silver)
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "bls_soc_code", StringType(), required=True),
        NestedField(3, "primary_title", StringType(), required=True),
        NestedField(4, "description", StringType(), required=True),
        NestedField(5, "multi_detail_flag", BooleanType(), required=True),
        NestedField(6, "data_completeness_tier", StringType(), required=True),
        # Human Edge Assessment (Derived)
        NestedField(7, "hmn_score", DoubleType(), required=False),
        NestedField(8, "hmn_score_rounded", IntegerType(), required=False),
        NestedField(9, "top_human_activities", StringType(), required=False),
        NestedField(10, "human_activity_count", IntegerType(), required=False),
        # Burnout Assessment (Derived)
        NestedField(11, "burnout_score", DoubleType(), required=False),
        NestedField(12, "burnout_score_rounded", IntegerType(), required=False),
        NestedField(13, "burnout_drivers", StringType(), required=False),
        NestedField(14, "time_pressure", DoubleType(), required=False),
        NestedField(15, "work_hours", DoubleType(), required=False),
        NestedField(16, "consequence_of_error", DoubleType(), required=False),
        # Activity Profile Summary (Derived)
        NestedField(17, "activity_importance_mean", DoubleType(), required=False),
        NestedField(18, "top_5_activities", StringType(), required=False),
        NestedField(19, "activity_profile_available", BooleanType(), required=True),
        # Context Profile Summary (Derived)
        NestedField(20, "context_profile_available", BooleanType(), required=True),
        # Data Quality Context (Derived)
        NestedField(21, "confidence_tier", StringType(), required=True),
        NestedField(22, "suppress_pct_activities", DoubleType(), required=False),
        NestedField(23, "suppress_pct_context", DoubleType(), required=False),
        # FutureProof Stat Mapping (Static)
        NestedField(24, "backs_stats", StringType(), required=True),
        NestedField(25, "backs_bosses", StringType(), required=True),
        # Pipeline Metadata
        NestedField(26, "source_load_date", DateType(), required=True),
        NestedField(27, "promoted_at", TimestampType(), required=True),
    )


def derive_gold_rows(
    occupation_rows: list[dict],
    activity_rows: list[dict],
    context_rows: list[dict],
) -> list[dict]:
    """Run Gold derivations over Silver rows.

    Two-phase computation:
      Phase 1: Compute per-occupation metrics (human_ratio, burnout, etc.)
      Phase 2: Min/max rescale human_ratio to HMN score across all occupations.

    Returns a list of dicts ready for grain-id computation and promotion.
    """
    if not occupation_rows:
        return []

    # Index activities by bls_soc_code
    activities_by_soc: dict[str, list[dict]] = {}
    for row in activity_rows:
        soc = row["bls_soc_code"]
        activities_by_soc.setdefault(soc, []).append(row)

    # Index context profiles by bls_soc_code
    contexts_by_soc: dict[str, list[dict]] = {}
    for row in context_rows:
        soc = row["bls_soc_code"]
        contexts_by_soc.setdefault(soc, []).append(row)

    human_set = set(HUMAN_INTENSIVE_ELEMENT_IDS)

    # Phase 1: Per-occupation computation
    phase1_results: list[dict] = []

    for occ in occupation_rows:
        soc = occ["bls_soc_code"]
        result: dict = {
            "bls_soc_code": soc,
            "primary_title": occ["primary_title"],
            "description": occ["description"],
            "multi_detail_flag": occ["multi_detail_flag"],
            "data_completeness_tier": occ["data_completeness_tier"],
            "source_load_date": occ["source_load_date"],
        }

        # --- Activity processing ---
        acts = activities_by_soc.get(soc, [])
        if acts:
            result["activity_profile_available"] = True

            # Suppression percentage
            suppress_count = sum(1 for a in acts if a.get("suppress_flag", False))
            result["suppress_pct_activities"] = (suppress_count / len(acts)) * 100.0

            # Mean importance of all activities
            importances = [a["importance"] for a in acts if a["importance"] is not None]
            result["activity_importance_mean"] = (
                sum(importances) / len(importances) if importances else None
            )

            # Top 5 activities by importance (all 41)
            sorted_all = sorted(
                [a for a in acts if a["importance"] is not None],
                key=lambda a: a["importance"],
                reverse=True,
            )
            top5 = [
                {"activity": a["element_name"], "importance": round(a["importance"], 2)}
                for a in sorted_all[:5]
            ]
            result["top_5_activities"] = json.dumps(top5)

            # Human-intensive activities
            human_acts = [a for a in acts if a["element_id"] in human_set]
            result["human_activity_count"] = len(human_acts)

            human_importance_sum = sum(
                a["importance"] for a in human_acts if a["importance"] is not None
            )
            total_importance_sum = sum(
                a["importance"] for a in acts if a["importance"] is not None
            )

            if total_importance_sum > 0:
                result["human_ratio"] = human_importance_sum / total_importance_sum
            else:
                result["human_ratio"] = None

            # Top human activities JSON (top 5 by importance from human-intensive)
            sorted_human = sorted(
                [a for a in human_acts if a["importance"] is not None],
                key=lambda a: a["importance"],
                reverse=True,
            )
            top_human = [
                {"activity": a["element_name"], "importance": round(a["importance"], 2)}
                for a in sorted_human[:5]
            ]
            result["top_human_activities"] = json.dumps(top_human)
        else:
            result["activity_profile_available"] = False
            result["suppress_pct_activities"] = None
            result["activity_importance_mean"] = None
            result["top_5_activities"] = None
            result["human_activity_count"] = None
            result["human_ratio"] = None
            result["top_human_activities"] = None

        # --- Context processing ---
        ctxs = contexts_by_soc.get(soc, [])
        if ctxs:
            result["context_profile_available"] = True

            # Suppression percentage
            suppress_count = sum(1 for c in ctxs if c.get("suppress_flag", False))
            result["suppress_pct_context"] = (suppress_count / len(ctxs)) * 100.0

            # Burnout elements: use is_burnout_element flag from Silver
            burnout_elems = [c for c in ctxs if c.get("is_burnout_element", False)]

            if burnout_elems:
                normalized_values = []
                normalized_with_name = []
                for elem in burnout_elems:
                    val = elem["context_value"]
                    scale = elem["scale_id"]
                    norm = _normalize_context_value(val, scale)
                    normalized_values.append(norm)
                    normalized_with_name.append({
                        "element": elem["element_name"],
                        "value": round(norm, 2),
                    })

                avg_norm = sum(normalized_values) / len(normalized_values)
                result["burnout_score"] = 1.0 + 9.0 * avg_norm

                # Top 3 burnout drivers by normalized value
                sorted_drivers = sorted(
                    normalized_with_name, key=lambda d: d["value"], reverse=True
                )
                result["burnout_drivers"] = json.dumps(sorted_drivers[:3])
            else:
                result["burnout_score"] = None
                result["burnout_drivers"] = None

            # Extract individual elements
            ctx_by_id = {c["element_id"]: c for c in ctxs}
            tp = ctx_by_id.get(TIME_PRESSURE_ID)
            result["time_pressure"] = tp["context_value"] if tp else None
            wh = ctx_by_id.get(WORK_HOURS_ID)
            result["work_hours"] = wh["context_value"] if wh else None
            ce = ctx_by_id.get(CONSEQUENCE_OF_ERROR_ID)
            result["consequence_of_error"] = ce["context_value"] if ce else None
        else:
            result["context_profile_available"] = False
            result["suppress_pct_context"] = None
            result["burnout_score"] = None
            result["burnout_drivers"] = None
            result["time_pressure"] = None
            result["work_hours"] = None
            result["consequence_of_error"] = None

        phase1_results.append(result)

    # Phase 2: Min/max rescale human_ratio to HMN score
    ratios = [r["human_ratio"] for r in phase1_results if r["human_ratio"] is not None]

    if ratios:
        observed_min = min(ratios)
        observed_max = max(ratios)
        ratio_range = observed_max - observed_min

        for result in phase1_results:
            hr = result.pop("human_ratio", None)
            if hr is not None and ratio_range > 0:
                hmn = 1.0 + 9.0 * (hr - observed_min) / ratio_range
                hmn = max(1.0, min(10.0, hmn))  # clamp
                result["hmn_score"] = hmn
                result["hmn_score_rounded"] = _round_half_up(hmn)
            elif hr is not None:
                # All ratios identical — assign midpoint
                result["hmn_score"] = 5.5
                result["hmn_score_rounded"] = 6
            else:
                result["hmn_score"] = None
                result["hmn_score_rounded"] = None
    else:
        for result in phase1_results:
            result.pop("human_ratio", None)
            result["hmn_score"] = None
            result["hmn_score_rounded"] = None

    # Phase 3: Compute burnout_score_rounded, confidence_tier, static fields
    for result in phase1_results:
        bs = result.get("burnout_score")
        if bs is not None:
            result["burnout_score_rounded"] = _round_half_up(bs)
        else:
            result["burnout_score_rounded"] = None

        # Confidence tier
        if result["data_completeness_tier"] == "partial":
            result["confidence_tier"] = "low"
        elif (
            (result.get("suppress_pct_activities") is not None and result["suppress_pct_activities"] >= 5.0)
            or (result.get("suppress_pct_context") is not None and result["suppress_pct_context"] >= 5.0)
        ):
            result["confidence_tier"] = "medium"
        else:
            result["confidence_tier"] = "high"

        # Static fields
        result["backs_stats"] = "HMN"
        result["backs_bosses"] = "AI,Burnout"

    return phase1_results


def add_record_ids(gold_rows: list[dict], promoted_at: datetime.datetime) -> list[dict]:
    """Add record_id and promoted_at to each Gold row."""
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Gold zone transformation for consumable.onet_work_profiles.

    Reads base.onet_occupations, base.onet_activity_profiles, and
    base.onet_context_profiles from Silver. Pivots activity/context
    rows into one row per occupation with HMN score (min/max rescaled),
    Burnout score, JSON summaries, and confidence tier. Promotes to
    consumable.onet_work_profiles.

    Returns:
        {"rows_read": N, "rows_derived": N, "promoted": N, "skipped": N}
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    # Read from Silver
    logger.info("Reading Silver tables...")
    silver_catalog = get_catalog(silver_warehouse, catalog_path)

    def _read_table(table_name: str) -> list[dict]:
        tbl = silver_catalog.load_table(table_name)
        arrow = tbl.scan().to_arrow()
        con = duckdb.connect()
        rows_raw = con.sql("SELECT * FROM arrow").fetchall()
        cols = [field.name for field in tbl.schema().fields]
        con.close()
        return [dict(zip(cols, r)) for r in rows_raw]

    occupation_rows = _read_table("base.onet_occupations")
    activity_rows = _read_table("base.onet_activity_profiles")
    context_rows = _read_table("base.onet_context_profiles")
    logger.info(
        "Read %d occupations, %d activities, %d contexts",
        len(occupation_rows), len(activity_rows), len(context_rows),
    )

    # Derive Gold fields
    logger.info("Computing Gold derivations...")
    gold_rows = derive_gold_rows(occupation_rows, activity_rows, context_rows)
    logger.info("Derived %d Gold rows", len(gold_rows))

    # Add record_id and promoted_at
    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    add_record_ids(gold_rows, promoted_at)

    # Promote to Gold
    logger.info("Promoting to consumable.onet_work_profiles...")
    gold_catalog = get_catalog(gold_warehouse, catalog_path)
    gold_table = get_or_create_table(
        gold_catalog, "consumable", "onet_work_profiles", get_gold_schema()
    )
    result = promote(
        gold_table,
        gold_rows,
        id_field="record_id",
        spec_name=SPEC_NAME,
        agent_name="@primary-agent",
    )

    logger.info(
        "Promote complete: %d promoted, %d skipped",
        result["promoted"],
        result["skipped"],
    )

    return {
        "rows_read": len(occupation_rows) + len(activity_rows) + len(context_rows),
        "rows_derived": len(gold_rows),
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    result = transform()
    print(f"Gold transform complete: {result}")
