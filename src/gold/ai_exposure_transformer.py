"""Gold zone transformer for consumable.ai_exposure.

Blends two Silver sources — base.gemma_ai_exposure (Gemma 4 task-level
scores, ~798 SOCs) and base.karpathy_ai_exposure (Gemini Flash scores,
~342 SOCs with bls_match=true) — into a single consumable table with
Gemma preferred, Karpathy fallback, union coverage.

Grain: soc_code
Record ID: compute_grain_id(row, ['soc_code'], prefix='aie')

Blending truth table:

    | Gemma      | Karpathy    | Result         | scoring_model    |
    | ---------- | ----------- | -------------- | ---------------- |
    | present    | present     | Use Gemma      | gemma-4          |
    | present    | missing     | Use Gemma      | gemma-4          |
    | missing    | present     | Use Karpathy   | gemini-flash     |
    | missing    | missing     | Exclude row    | —                |

``karpathy_rows`` is pre-deduped by soc_code via Silver's
``_dedup_by_soc_code`` (highest num_jobs_2024 wins). The blender
assumes one row per SOC per source. ``gemma_rows`` with ``error != None``
(the scorer failed to parse a valid response) are treated as "Gemma
missing" and fall through to Karpathy fallback.
"""

import datetime
import json
import logging
import os
from pathlib import Path
from typing import Literal

from pyiceberg.schema import Schema
from pyiceberg.types import (
    DoubleType,
    IntegerType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.infra.grain import compute_grain_id
from brightsmith.infra.iceberg_setup import (
    get_catalog,
    get_or_create_table,
    read_with_duckdb,
)
from brightsmith.infra.promote import promote

logger = logging.getLogger(__name__)

SPEC_NAME = "gold-ai-exposure"
GRAIN_FIELDS = ["soc_code"]
GRAIN_PREFIX = "aie"

# Operators set this to "1" to override the A/B fail-closed gate when
# promoting a blend that fails one or more validation gates. Required
# rationale lives in spec §6 Implementation Log.
AB_OVERRIDE_ENV = "AI_EXPOSURE_AB_OVERRIDE"

# SOC 2018 major-group → Karpathy-style category slug.
# Vocabulary matches Karpathy's `category` column verbatim so that
# Gemma-only rows blend cleanly with Karpathy overlap rows in
# `consumable.ai_exposure.category`. Source of truth for Karpathy's
# slug vocabulary: governance/eda/gold-ai-exposure-eda.md (Karpathy
# uses a single `healthcare` bucket, not `healthcare-practitioners-
# and-technical`/`healthcare-support`; uses `education-training-and-
# library`, not `educational-instruction-and-library`). Code "55"
# (military) added per v4 data-reviewer note.
SOC_MAJOR_GROUP_TO_CATEGORY: dict[str, str] = {
    "11": "management",
    "13": "business-and-financial",
    "15": "computer-and-mathematical",
    "17": "architecture-and-engineering",
    "19": "life-physical-and-social-science",
    "21": "community-and-social-service",
    "23": "legal",
    "25": "education-training-and-library",
    "27": "arts-design-entertainment-sports-and-media",
    "29": "healthcare",
    "31": "healthcare",
    "33": "protective-service",
    "35": "food-preparation-and-serving",
    "37": "building-and-grounds-cleaning-and-maintenance",
    "39": "personal-care-and-service",
    "41": "sales-and-related",
    "43": "office-and-administrative-support",
    "45": "farming-fishing-and-forestry",
    "47": "construction-and-extraction",
    "49": "installation-maintenance-and-repair",
    "51": "production",
    "53": "transportation-and-material-moving",
    "55": "military",
}


def get_gold_schema() -> Schema:
    """Iceberg schema for consumable.ai_exposure (23 columns).

    v4 adds five Option B composite fields (IDs 19-23) on top of the
    existing 9 core + 5 Gemma/Karpathy + 4 Anthropic columns. Field 15
    is renamed from ``observed_exposure_pct`` to ``ai_adoption_share``
    because the Silver value semantically measures share of Claude
    conversations, not theoretical task exposure — see spec
    docs/specs/three-signal-ai-exposure-composite-v3.md §4 v4.

    ``stat_res`` (field 5) and ``boss_ai_score`` (field 6) are now
    derived from ``composite_exposure`` (field 19) rather than the raw
    ``exposure_score`` (field 4) when Anthropic adoption data is
    available. ``exposure_score`` is preserved unchanged for downstream
    consumers that still want the Gemma theoretical number.
    """
    return Schema(
        # Original 9 (preserved for backward compatibility)
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "occupation_title", StringType(), required=True),
        NestedField(4, "exposure_score", IntegerType(), required=True),
        NestedField(5, "stat_res", IntegerType(), required=True),
        NestedField(6, "boss_ai_score", IntegerType(), required=True),
        NestedField(7, "rationale", StringType(), required=True),
        NestedField(8, "category", StringType(), required=True),
        NestedField(9, "promoted_at", TimestampType(), required=True),
        # v4 additive fields (Gemma/Karpathy blending)
        NestedField(10, "task_breakdown_automatable", StringType(), required=False),
        NestedField(11, "task_breakdown_human", StringType(), required=False),
        NestedField(12, "scoring_model", StringType(), required=True),
        NestedField(13, "model_tag", StringType(), required=False),
        NestedField(14, "karpathy_score", IntegerType(), required=False),
        # Anthropic Economic Index passthrough
        # Field 15 renamed observed_exposure_pct → ai_adoption_share (v4)
        NestedField(15, "ai_adoption_share", DoubleType(), required=False),
        NestedField(16, "automation_pct", DoubleType(), required=False),
        NestedField(17, "anthropic_task_count", IntegerType(), required=False),
        NestedField(18, "anthropic_source_release", StringType(), required=False),
        # Option B composite fields (v4)
        NestedField(19, "composite_exposure", IntegerType(), required=False),
        NestedField(20, "adoption_percentile", DoubleType(), required=False),
        NestedField(21, "confidence_weight", DoubleType(), required=False),
        NestedField(22, "velocity_label", StringType(), required=False),
        NestedField(23, "composite_method", StringType(), required=False),
    )


# ---------------------------------------------------------------------------
# Option B composite (v4) — percentile-rank confidence blend.
#
# See spec docs/specs/three-signal-ai-exposure-composite-v3.md §4 for full
# derivation. The short version: instead of summing a linear blend of
# theoretical/observed/velocity, Option B treats ai_adoption_share as a
# confidence prior. High real-world adoption → trust Gemma; low adoption
# → lean on Karpathy baseline. Only the *rank* of the adoption share
# matters, so the Silver value's absolute scale (0.0015-7.51, share of
# Claude conversations) is irrelevant.
# ---------------------------------------------------------------------------


VelocityLabel = Literal[
    "saturating", "accelerating", "emerging", "nascent", "unknown"
]
CompositeMethod = Literal[
    "three_signal",
    "two_signal_no_anthropic",
    "gemma_plus_anthropic",
    "gemma_only",
    "karpathy_only",
    "observed_override",
    "no_data",
]


def percent_rank(values: list[float | None]) -> list[float | None]:
    """Return percent-rank * 100 (0-100) preserving None slots.

    Ties share the lower rank (``sort``-stable assignment). With a single
    non-null value we return 100.0 for that slot (``n-1 == 0`` edge case).
    """
    indexed = [(i, v) for i, v in enumerate(values) if v is not None]
    indexed.sort(key=lambda iv: iv[1])
    out: list[float | None] = [None] * len(values)
    n = len(indexed)
    if n == 0:
        return out
    if n == 1:
        out[indexed[0][0]] = 100.0
        return out
    for rank, (idx, _) in enumerate(indexed):
        out[idx] = 100.0 * rank / (n - 1)
    return out


def velocity_from_percentile(percentile: float | None) -> VelocityLabel:
    """Bucket adoption percentile → coarse velocity label."""
    if percentile is None:
        return "unknown"
    if percentile >= 90:
        return "saturating"
    if percentile >= 70:
        return "accelerating"
    if percentile >= 40:
        return "emerging"
    return "nascent"


def compute_composite(
    gemma_score: int | None,
    karpathy_score: int | None,
    ai_adoption_share: float | None,
    adoption_percentile: float | None,
) -> tuple[int | None, float | None, VelocityLabel, CompositeMethod]:
    """Compute the Option B composite.

    Returns ``(composite_exposure 0-10 | None, confidence 0.3-1.0 | None,
    velocity_label, composite_method)``.

    Fallback routing:
      - both signals None → (None, None, velocity, "no_data")
      - theoretical None → karpathy_only (composite = baseline)
      - baseline None    → gemma_only (no anthropic) or gemma_plus_anthropic
      - theoretical == 0 and share > 0 → observed_override
                                         (composite = baseline * confidence)
      - else → three_signal (with share) or two_signal_no_anthropic
    """
    theoretical = gemma_score
    baseline = karpathy_score

    if adoption_percentile is not None:
        confidence: float | None = max(
            0.3, min(1.0, 0.3 + 0.7 * adoption_percentile / 100.0)
        )
        velocity: VelocityLabel = velocity_from_percentile(adoption_percentile)
    else:
        confidence = 0.5
        velocity = "unknown"

    if theoretical is None and baseline is None:
        return None, None, velocity, "no_data"

    if theoretical is None:
        assert baseline is not None  # for mypy
        return (
            int(round(max(0.0, min(10.0, float(baseline))))),
            confidence,
            velocity,
            "karpathy_only",
        )

    if baseline is None:
        method: CompositeMethod = (
            "gemma_plus_anthropic" if ai_adoption_share is not None else "gemma_only"
        )
        return (
            int(round(max(0.0, min(10.0, float(theoretical))))),
            confidence,
            velocity,
            method,
        )

    # Edge case: Gemma says zero theoretical, but real-world adoption > 0.
    # Trust the observed signal: use Karpathy scaled by adoption confidence.
    if theoretical == 0 and ai_adoption_share is not None and ai_adoption_share > 0:
        assert confidence is not None  # always set when percentile present
        return (
            int(round(max(0.0, min(10.0, float(baseline) * confidence)))),
            confidence,
            velocity,
            "observed_override",
        )

    # Regular blend. `confidence` is always non-None here: either 0.5
    # (fallback) or a real percentile-derived value.
    assert confidence is not None
    composite = confidence * theoretical + (1.0 - confidence) * baseline
    method = (
        "three_signal" if ai_adoption_share is not None else "two_signal_no_anthropic"
    )
    return (
        int(round(max(0.0, min(10.0, composite)))),
        confidence,
        velocity,
        method,
    )


def derive_stats(
    composite_exposure: int | None,
) -> tuple[int | None, int | None]:
    """Derive (stat_res, boss_ai_score) from the composite.

    stat_res = MIN(11 - composite, 10). Higher composite → lower resilience.
    boss_ai_score = MAX(composite, 1). Higher composite → harder fight.
    """
    if composite_exposure is None:
        return None, None
    return min(11 - composite_exposure, 10), max(composite_exposure, 1)


def compute_stat_res(exposure_score: int) -> int:
    """Derive AI Resilience stat (1-10) from exposure score (0-10).

    Higher exposure = lower resilience.
    Formula: MIN(11 - exposure_score, 10)

    Edge case: exposure_score=0 -> 11, capped at 10.
    """
    return min(11 - exposure_score, 10)


def compute_boss_ai_score(exposure_score: int) -> int:
    """Derive Fight AI boss strength (1-10) from exposure score (0-10).

    Higher exposure = harder fight. Floor at 1.
    Formula: MAX(exposure_score, 1)
    """
    return max(exposure_score, 1)


def derive_category(soc_code: str, karpathy_category: str | None) -> str:
    """Prefer Karpathy category; fall back to SOC major-group mapping.

    For the ~456 Gemma-only SOCs (no Karpathy row), Karpathy's category
    vocabulary isn't available; we derive from SOC 2018 major group
    (first 2 digits). Unrecognized prefixes fall back to "other" rather
    than "Unknown" so Gate 4 (category bias) remains meaningful.
    """
    if karpathy_category and karpathy_category != "Unknown":
        return karpathy_category
    if not soc_code or len(soc_code) < 2:
        return "other"
    return SOC_MAJOR_GROUP_TO_CATEGORY.get(soc_code[:2], "other")


def _gemma_has_score(gemma: dict | None) -> bool:
    """True when Gemma produced a usable score for this SOC.

    A row is usable when ``exposure_score`` is a non-null int AND
    ``error`` is None/missing. This matches the blending truth table:
    failed scorer rows (``error != None``) fall through to Karpathy.

    The ``isinstance(score, bool)`` guard is defensive: ``bool`` is a
    subclass of ``int`` in Python, so a stray ``True``/``False`` would
    otherwise satisfy ``isinstance(score, int)``. Upstream layers
    (scorer + ingestor + Silver schema) already reject booleans; the
    blender is the last line before Gold, so it should be at least as
    strict as the layers above it.
    """
    if gemma is None:
        return False
    if gemma.get("error"):
        return False
    score = gemma.get("exposure_score")
    if isinstance(score, bool):
        return False
    return isinstance(score, int)


def blend_scores(
    gemma_rows: dict[str, dict],
    karpathy_rows: dict[str, dict],
    promoted_at: datetime.datetime,
    anthropic_rows: dict[str, dict] | None = None,
) -> list[dict]:
    """Blend Gemma + Karpathy sources into Gold rows.

    Union semantics: output covers ``set(gemma_rows) | set(karpathy_rows)``.
    Gemma is preferred when both sources have a SOC; Karpathy is used
    when Gemma is missing or errored. ``karpathy_score`` is preserved
    on Gemma-preferred rows for the A/B comparison report.

    Both inputs must be pre-deduped to one row per SOC. Karpathy Silver
    already does this via ``_dedup_by_soc_code`` (highest num_jobs_2024
    wins). Gemma Silver dedups during SOC normalization.

    Args:
        gemma_rows: ``dict[soc_code, row]`` from base.gemma_ai_exposure.
        karpathy_rows: ``dict[soc_code, row]`` from base.karpathy_ai_exposure
            filtered to ``bls_match=true``.
        promoted_at: Timestamp stamped on every blended row.
        anthropic_rows: Optional ``dict[soc_code, row]`` from
            base.anthropic_observed_exposure. When provided, each output
            row gets ``observed_exposure_pct``, ``automation_pct``,
            ``anthropic_task_count``, and ``anthropic_source_release``
            via LEFT JOIN on soc_code. Unmatched SOCs get None for all
            four fields (additive, non-destructive). When None, the
            four columns are emitted as None on every row so the schema
            stays stable.

    Returns:
        List of blended Gold rows ready for ``promote()``. Rows with
        neither Gemma nor Karpathy source are excluded (Anthropic alone
        is NOT sufficient — the existing Gemma/Karpathy blend gates
        inclusion).
    """
    anthropic_rows = anthropic_rows or {}
    all_socs = set(gemma_rows.keys()) | set(karpathy_rows.keys())
    blended: list[dict] = []

    for soc in sorted(all_socs):
        gemma = gemma_rows.get(soc)
        karpathy = karpathy_rows.get(soc)
        anthropic = anthropic_rows.get(soc)

        if _gemma_has_score(gemma):
            assert gemma is not None  # for mypy — _gemma_has_score guards
            exposure = gemma["exposure_score"]
            title = gemma.get("primary_title") or (
                karpathy.get("occupation_title") if karpathy else None
            )
            if not title:
                # Should never happen for a valid Gemma row, but keep
                # the schema contract (occupation_title required) honest.
                title = f"SOC {soc}"
            row = {
                "soc_code": soc,
                "occupation_title": title,
                "exposure_score": exposure,
                # stat_res / boss_ai_score are provisional here — they
                # will be recomputed from the Option B composite in the
                # second pass below once adoption_percentile is known.
                "stat_res": compute_stat_res(exposure),
                "boss_ai_score": compute_boss_ai_score(exposure),
                "rationale": gemma["rationale"],
                "category": derive_category(
                    soc, karpathy.get("category") if karpathy else None
                ),
                "task_breakdown_automatable": gemma.get("task_breakdown_automatable"),
                "task_breakdown_human": gemma.get("task_breakdown_human"),
                "scoring_model": "gemma-4",
                "model_tag": gemma.get("model_tag"),
                "karpathy_score": (
                    karpathy.get("exposure_score") if karpathy else None
                ),
            }
        elif karpathy is not None:
            exposure = karpathy["exposure_score"]
            row = {
                "soc_code": soc,
                "occupation_title": karpathy["occupation_title"],
                "exposure_score": exposure,
                "stat_res": compute_stat_res(exposure),
                "boss_ai_score": compute_boss_ai_score(exposure),
                "rationale": karpathy["rationale"],
                "category": karpathy["category"],
                "task_breakdown_automatable": None,
                "task_breakdown_human": None,
                "scoring_model": "gemini-flash",
                "model_tag": None,
                "karpathy_score": exposure,
            }
        else:
            continue

        # Anthropic LEFT JOIN (additive). Silver key is observed_exposure_pct
        # for historical reasons; at Gold we expose it as ai_adoption_share
        # because the value semantically measures share of Claude
        # conversations, not theoretical task exposure.
        if anthropic is not None:
            row["ai_adoption_share"] = anthropic.get("observed_exposure_pct")
            row["automation_pct"] = anthropic.get("automation_pct")
            row["anthropic_task_count"] = anthropic.get("task_count")
            row["anthropic_source_release"] = anthropic.get("source_release")
        else:
            row["ai_adoption_share"] = None
            row["automation_pct"] = None
            row["anthropic_task_count"] = None
            row["anthropic_source_release"] = None

        blended.append(row)

    # Second pass — Option B composite. Compute adoption_percentile
    # across ALL rows so the rank reflects the full SOC universe we
    # have data for, then apply the composite row-wise and overwrite
    # stat_res / boss_ai_score.
    shares: list[float | None] = [r.get("ai_adoption_share") for r in blended]
    percentiles = percent_rank(shares)
    for row, percentile in zip(blended, percentiles, strict=True):
        gemma_score = (
            row["exposure_score"] if row["scoring_model"] == "gemma-4" else None
        )
        karpathy_blend_score = row.get("karpathy_score")
        composite, confidence, velocity, method = compute_composite(
            gemma_score,
            karpathy_blend_score,
            row.get("ai_adoption_share"),
            percentile,
        )
        stat_res, boss_ai = derive_stats(composite)

        row["composite_exposure"] = composite
        row["adoption_percentile"] = percentile
        row["confidence_weight"] = confidence
        row["velocity_label"] = velocity
        row["composite_method"] = method

        # Overwrite derived stats with composite-based values. Fall back to
        # the provisional single-source values when the composite itself
        # is None (no_data) so the schema contract (required=True on
        # stat_res / boss_ai_score) stays honest.
        if stat_res is not None:
            row["stat_res"] = stat_res
        if boss_ai is not None:
            row["boss_ai_score"] = boss_ai

        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at

    return blended


def _index_karpathy(silver_rows: list[dict]) -> dict[str, dict]:
    """Index Karpathy Silver rows by soc_code, filtered to bls_match=true.

    Silver has multiple rows per SOC pre-dedup, but ``_dedup_by_soc_code``
    already collapsed them to one row per non-null SOC. This helper
    additionally filters to ``bls_match=true`` (matches original Gold
    behavior) and drops any null-SOC rows that slipped through.
    """
    indexed: dict[str, dict] = {}
    for row in silver_rows:
        soc = row.get("soc_code")
        if not soc:
            continue
        if not row.get("bls_match"):
            continue
        indexed[soc] = row
    return indexed


def _index_gemma(silver_rows: list[dict]) -> dict[str, dict]:
    """Index Gemma Silver rows by soc_code_normalized."""
    indexed: dict[str, dict] = {}
    for row in silver_rows:
        soc = row.get("soc_code_normalized") or row.get("soc_code")
        if not soc:
            continue
        indexed[soc] = row
    return indexed


def _index_anthropic(silver_rows: list[dict]) -> dict[str, dict]:
    """Index Anthropic observed-exposure Silver rows by soc_code.

    Drops rows without a usable SOC code; last write wins on duplicates
    (Silver already guarantees one row per SOC via the grain, but we
    stay defensive to match the Karpathy/Gemma indexing pattern).
    """
    indexed: dict[str, dict] = {}
    for row in silver_rows:
        soc = row.get("soc_code")
        if not soc:
            continue
        indexed[soc] = row
    return indexed


def _check_ab_gate(project_dir: Path) -> None:
    """Block the promote when the A/B comparison report failed.

    Reads ``reports/gemma_vs_karpathy_comparison.json`` (produced by
    ``reports/gemma_vs_karpathy_comparison.py``). When the report
    exists AND ``overall_pass`` is False, raises ``RuntimeError`` to
    stop the promote — unless the operator has set
    ``AI_EXPOSURE_AB_OVERRIDE=1``, in which case we log a loud warning
    and proceed. When the report doesn't exist (e.g., this is the very
    first run before A/B has been generated), we log and skip the
    check rather than crash; the operator should still run A/B before
    treating Gold as authoritative.
    """
    report_path = project_dir / "reports" / "gemma_vs_karpathy_comparison.json"
    if not report_path.exists():
        logger.warning(
            "A/B comparison report not found at %s — promote proceeding "
            "without gate enforcement. Run "
            "reports/gemma_vs_karpathy_comparison.py before treating "
            "Gold as authoritative.",
            report_path,
        )
        return

    try:
        ab_result = json.loads(report_path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(
            "A/B report at %s unreadable (%s); skipping gate check. "
            "Re-run reports/gemma_vs_karpathy_comparison.py.",
            report_path, exc,
        )
        return

    if ab_result.get("overall_pass"):
        logger.info(
            "A/B gate: PASS (%d gates, %d outliers).",
            len(ab_result.get("gates") or {}),
            len(ab_result.get("outliers") or []),
        )
        return

    failed_gates = [
        name for name, gate in (ab_result.get("gates") or {}).items()
        if isinstance(gate, dict) and gate.get("pass") is False
    ]

    if os.getenv(AB_OVERRIDE_ENV) == "1":
        logger.warning(
            "A/B gate FAILED (%s) but %s=1 — proceeding with promote. "
            "Operator MUST document override rationale in spec §6.",
            ", ".join(failed_gates) or "unknown",
            AB_OVERRIDE_ENV,
        )
        return

    raise RuntimeError(
        f"A/B validation overall_pass=False (failed gates: "
        f"{', '.join(failed_gates) or 'unknown'}). Promote blocked. "
        f"Either fix the prompt and re-run the batch, or set "
        f"{AB_OVERRIDE_ENV}=1 and document the rationale in spec §6."
    )


def _evolve_ai_exposure_schema(table) -> None:  # type: ignore[no-untyped-def]
    """Apply v4 schema evolution: rename field 15 + append composite fields.

    Idempotent: inspects the current schema and only issues the rename or
    add_column calls that are actually needed. Safe to call on every
    ``transform()`` invocation including the first (where
    ``get_or_create_table`` already built the target schema and there's
    nothing to evolve).
    """
    existing = {f.name for f in table.schema().fields}
    needs_rename = "observed_exposure_pct" in existing and "ai_adoption_share" not in existing
    target = get_gold_schema()
    new_fields = [f for f in target.fields if f.name not in existing and f.name != "ai_adoption_share"]

    if not needs_rename and not new_fields:
        return

    with table.update_schema() as update:
        if needs_rename:
            update.rename_column("observed_exposure_pct", "ai_adoption_share")
            logger.info("Renamed ai_exposure field observed_exposure_pct → ai_adoption_share")
        for field in new_fields:
            update.add_column(
                field.name, field.field_type, doc=None, required=field.required
            )
        if new_fields:
            logger.info(
                "Evolved ai_exposure schema: added %d fields (%s)",
                len(new_fields), [f.name for f in new_fields],
            )


def transform(
    project_dir: str | Path | None = None,
) -> dict:
    """Run the Gold zone transformation for consumable.ai_exposure.

    Reads both Silver inputs, blends with Gemma preferred, and promotes
    to consumable.ai_exposure via the idempotent promote pattern. When
    base.gemma_ai_exposure is missing (Gemma batch not yet run), falls
    back to Karpathy-only behavior so existing downstream consumers are
    never left without ai_exposure data.

    Returns:
        {"rows_read_karpathy": N, "rows_read_gemma": N,
         "rows_blended": N, "promoted": N, "skipped_dedup": N,
         "snapshot_id": X | None, "gemma_rows_used": N,
         "karpathy_fallback_used": N}
    """
    project_dir = Path(project_dir or ".").resolve()

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    gold_warehouse = project_dir / "data" / "gold" / "iceberg_warehouse"

    silver_catalog = get_catalog(silver_warehouse, catalog_path)

    # Karpathy Silver (always present once S0 Karpathy pipeline has run).
    logger.info("Reading from base.karpathy_ai_exposure...")
    karpathy_table = silver_catalog.load_table("base.karpathy_ai_exposure")
    karpathy_rows = read_with_duckdb(karpathy_table)
    karpathy_indexed = _index_karpathy(karpathy_rows)
    logger.info(
        "Karpathy: %d rows read, %d indexed by soc_code (bls_match=true)",
        len(karpathy_rows), len(karpathy_indexed),
    )

    # Gemma Silver (optional — table may not exist until S1 batch has run).
    gemma_indexed: dict[str, dict] = {}
    try:
        gemma_table = silver_catalog.load_table("base.gemma_ai_exposure")
    except Exception:
        logger.warning(
            "base.gemma_ai_exposure not found — falling back to Karpathy-only. "
            "Run scripts/gemma_ai_exposure_scorer.py and promote through "
            "Bronze/Silver to enable Gemma scoring."
        )
        gemma_table = None

    if gemma_table is not None:
        gemma_rows = read_with_duckdb(gemma_table)
        gemma_indexed = _index_gemma(gemma_rows)
        logger.info(
            "Gemma: %d rows read, %d indexed by soc_code",
            len(gemma_rows), len(gemma_indexed),
        )

    # Anthropic Silver (optional — table may not exist until S3 pipeline
    # has run). LEFT JOIN semantics: when present, each Gold row gets
    # observed_exposure / automation / task_count / source_release;
    # when missing, all four fields are None on every row. Additive-
    # only: the existing Gemma/Karpathy blend behavior is unchanged.
    anthropic_indexed: dict[str, dict] = {}
    try:
        anthropic_table = silver_catalog.load_table(
            "base.anthropic_observed_exposure"
        )
    except Exception:
        logger.warning(
            "base.anthropic_observed_exposure not found — "
            "observed_exposure_pct / automation_pct will be null. "
            "Run the Anthropic Economic Index ingestor + Silver "
            "transformer to populate these columns."
        )
        anthropic_table = None

    if anthropic_table is not None:
        anthropic_rows = read_with_duckdb(anthropic_table)
        anthropic_indexed = _index_anthropic(anthropic_rows)
        logger.info(
            "Anthropic: %d rows read, %d indexed by soc_code",
            len(anthropic_rows), len(anthropic_indexed),
        )

    # Fail-closed A/B gate: when Gemma scoring is in play, refuse to
    # promote a blend that failed validation unless the operator
    # explicitly overrides via AI_EXPOSURE_AB_OVERRIDE=1.
    if gemma_indexed:
        _check_ab_gate(project_dir)

    promoted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    blended = blend_scores(
        gemma_indexed,
        karpathy_indexed,
        promoted_at,
        anthropic_rows=anthropic_indexed,
    )

    gemma_used = sum(1 for r in blended if r["scoring_model"] == "gemma-4")
    karpathy_used = sum(1 for r in blended if r["scoring_model"] == "gemini-flash")
    logger.info(
        "Blended: %d rows (%d Gemma, %d Karpathy fallback)",
        len(blended), gemma_used, karpathy_used,
    )

    gold_catalog = get_catalog(gold_warehouse, catalog_path)
    gold_table = get_or_create_table(
        gold_catalog, "consumable", "ai_exposure", get_gold_schema()
    )
    _evolve_ai_exposure_schema(gold_table)
    result = promote(
        gold_table,
        blended,
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
        "rows_read_karpathy": len(karpathy_indexed),
        "rows_read_gemma": len(gemma_indexed),
        "rows_blended": len(blended),
        "gemma_rows_used": gemma_used,
        "karpathy_fallback_used": karpathy_used,
        "promoted": result["promoted"],
        "skipped_dedup": result["skipped"],
        "snapshot_id": result.get("snapshot_id"),
    }


# ---------------------------------------------------------------------------
# Backward-compatibility helpers retained from the pre-v4 transformer.
# The `karpathy-only` path still uses them when base.gemma_ai_exposure
# is missing, and downstream tests reference them directly.
# ---------------------------------------------------------------------------


def derive_gold_rows(silver_rows: list[dict]) -> list[dict]:
    """Karpathy-only derivation path (pre-v4).

    Kept for backward compatibility with existing tests and ad-hoc
    scripts that import this helper directly. New code should use
    ``blend_scores`` instead.
    """
    gold_rows = []

    for row in silver_rows:
        if not row.get("bls_match"):
            continue

        soc_code = row.get("soc_code")
        if soc_code is None:
            continue

        exposure_score = row["exposure_score"]

        gold_row = {
            "soc_code": soc_code,
            "occupation_title": row["occupation_title"],
            "exposure_score": exposure_score,
            "stat_res": compute_stat_res(exposure_score),
            "boss_ai_score": compute_boss_ai_score(exposure_score),
            "rationale": row["rationale"],
            "category": row["category"],
            # v4-required fields stamped with Karpathy provenance.
            "task_breakdown_automatable": None,
            "task_breakdown_human": None,
            "scoring_model": "gemini-flash",
            "model_tag": None,
            "karpathy_score": exposure_score,
            # Anthropic Economic Index passthrough — Karpathy-only
            # fallback has no Anthropic bridge (the full ``transform()``
            # path does). Field 15 renamed v4.
            "ai_adoption_share": None,
            "automation_pct": None,
            "anthropic_task_count": None,
            "anthropic_source_release": None,
            # Option B composite fields (v4). Without Anthropic data we
            # can't compute a meaningful percentile, so velocity is
            # "unknown", method is "karpathy_only", and composite falls
            # back to the raw Karpathy exposure score.
            "composite_exposure": exposure_score,
            "adoption_percentile": None,
            "confidence_weight": 0.5,
            "velocity_label": "unknown",
            "composite_method": "karpathy_only",
        }

        gold_rows.append(gold_row)

    return gold_rows


def add_record_ids(
    gold_rows: list[dict], promoted_at: datetime.datetime
) -> list[dict]:
    """Add ``record_id`` and ``promoted_at`` to each Gold row in place.

    Retained for backward compatibility. The v4 ``blend_scores`` stamps
    these fields itself; callers that assemble rows without blending
    (e.g., the Karpathy-only fallback) still use this helper.
    """
    for row in gold_rows:
        row["record_id"] = compute_grain_id(row, GRAIN_FIELDS, prefix=GRAIN_PREFIX)
        row["promoted_at"] = promoted_at
    return gold_rows


def _decode_json_field(value: object) -> object:
    """Decode a JSON-string field to a Python object.

    Used by the batch scorer to unpack ``top_5_activities`` and
    ``top_human_activities`` from Gold before re-serializing them into
    a Gemma prompt. Non-strings are passed through unchanged; invalid
    JSON is returned as-is so the scorer can log+skip instead of
    crashing the batch.
    """
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    result = transform()
    print(f"Gold transform complete: {result}")
