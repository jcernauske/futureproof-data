"""One-off runner: promote base.ipeds_finance to consumable.ipeds_finance_profile.

Reads the 2,675-row FY2023 ``base.ipeds_finance`` snapshot (F1A public
GASB, F2 private nonprofit FASB, F3 private for-profit) and writes the
matching rows to ``consumable.ipeds_finance_profile`` via the idempotent
promote pattern.  Re-running the script produces 0 new rows.

NOTE: This script intentionally does NOT override ``project_name``.  The
Brightsmith framework's ``get_catalog()`` binds the SqlCatalog to the
module-level ``PROJECT_NAME``.  If this script set ``project_name`` to
anything other than the framework default ('brightsmith'), it would
write Iceberg table rows under a separate ``catalog_name`` that
``dq_runner`` (and every other reader that does not call
``configure()``) cannot see — see the BEA RPP precedent at
``governance/adversarial-audits/raw-ingest-bea-rpp.md`` HIGH-1.

Usage:
    uv run python scripts/promote_ipeds_finance_profile.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import brightsmith.config  # noqa: E402

# Configure project paths but keep the framework default project_name
# ('brightsmith') so that writers and readers resolve the same catalog_name.
brightsmith.config.configure(
    project_root=PROJECT_ROOT,
    require_human_approval=False,
)

from gold.ipeds_finance_profile import transform  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("promote_ipeds_finance_profile")


def main() -> int:
    results = transform(project_dir=PROJECT_ROOT)
    logger.info("Promote results: %s", results)

    # Verify row count + spot-checks against the persistent warehouse via
    # a fresh read.
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    consumable_warehouse = PROJECT_ROOT / "data" / "gold" / "iceberg_warehouse"
    catalog = get_catalog(consumable_warehouse, brightsmith.config.CATALOG_PATH)
    table = catalog.load_table("consumable.ipeds_finance_profile")
    rows = read_with_duckdb(table)
    logger.info("consumable.ipeds_finance_profile row count: %d", len(rows))

    # CON-IFP-004: record_id non-null + unique.
    record_ids = [r.get("record_id") for r in rows]
    nulls = sum(1 for rid in record_ids if rid is None)
    unique_ids = set(record_ids)
    logger.info(
        "record_id: %d non-null, %d unique (== row count: %s)",
        len(record_ids) - nulls,
        len(unique_ids),
        len(unique_ids) == len(record_ids),
    )

    # CON-IFP-005/009: data_completeness_tier distribution.
    tier_counts: dict[str, int] = {}
    for r in rows:
        t = r.get("data_completeness_tier")
        tier_counts[t] = tier_counts.get(t, 0) + 1
    logger.info("data_completeness_tier distribution: %s", sorted(tier_counts.items()))

    # Per-form tier breakdown — useful for confirming the F3 medium-not-high
    # invariant from the v1.2 reviewer rework.
    per_form_tiers: dict[str, dict[str, int]] = {}
    for r in rows:
        form = r.get("report_form")
        tier = r.get("data_completeness_tier")
        per_form_tiers.setdefault(form, {})[tier] = (
            per_form_tiers.setdefault(form, {}).get(tier, 0) + 1
        )
    logger.info(
        "data_completeness_tier by report_form: %s",
        {form: sorted(t.items()) for form, t in sorted(per_form_tiers.items())},
    )

    # Stanford UNITID 243744 spot check (per the spec — should be tier=high
    # with all 4 raw inputs present; marketing_ratio ≈ 0.302).
    stanford = [r for r in rows if r["unitid"] == 243744]
    if stanford:
        s = stanford[0]
        logger.info("Stanford UNITID=243744 consumable row:")
        logger.info("  data_completeness_tier:        %s", s.get("data_completeness_tier"))
        logger.info("  marketing_ratio:               %s", s.get("marketing_ratio"))
        logger.info("  instruction_per_fte:           %s", s.get("instruction_per_fte"))
        logger.info("  institutional_support_per_fte: %s", s.get("institutional_support_per_fte"))
        logger.info("  endowment_per_fte:             %s", s.get("endowment_per_fte"))
        logger.info("  instruction_expenses:          %s", s.get("instruction_expenses"))
        logger.info("  institutional_support_expenses:%s", s.get("institutional_support_expenses"))
        logger.info("  endowment_value:               %s", s.get("endowment_value"))
        logger.info("  total_fte_enrollment:          %s", s.get("total_fte_enrollment"))
        logger.info("  record_id:                     %s", s.get("record_id"))

    # F3 spot-check: an F3 row with the other 3 raw inputs present should
    # be tier=medium (endowment_value structurally NULL → 3 of 4 signals).
    f3_with_three = [
        r
        for r in rows
        if r.get("report_form") == "F3"
        and r.get("instruction_expenses") is not None
        and r.get("institutional_support_expenses") is not None
        and r.get("total_fte_enrollment") is not None
        and r.get("total_fte_enrollment") > 0
        and r.get("endowment_value") is None
    ]
    if f3_with_three:
        sample = f3_with_three[0]
        logger.info(
            "F3 spot-check (UNITID=%s, %s):",
            sample.get("unitid"),
            sample.get("institution_name"),
        )
        logger.info(
            "  data_completeness_tier: %s (expect=medium — endowment_value NULL drives 3/4 signals)",
            sample.get("data_completeness_tier"),
        )
        logger.info("  endowment_value:        %s", sample.get("endowment_value"))
        logger.info("  instruction_expenses:   %s", sample.get("instruction_expenses"))
        logger.info(
            "  institutional_support_expenses: %s",
            sample.get("institutional_support_expenses"),
        )
        logger.info("  total_fte_enrollment:   %s", sample.get("total_fte_enrollment"))

        # Confirm zero F3 rows landed at tier=high (would indicate the
        # v1.2 rework regressed to the v1.0 derived-fields counting bug).
        f3_high = [
            r for r in rows if r.get("report_form") == "F3" and r.get("data_completeness_tier") == "high"
        ]
        logger.info(
            "F3 rows at tier=high: %d (expect 0 — endowment_value structurally NULL on F3)",
            len(f3_high),
        )

    ok = (
        len(rows) == 2_675
        and nulls == 0
        and len(unique_ids) == len(record_ids)
        and set(tier_counts.keys()) <= {"high", "medium", "low", "insufficient"}
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
