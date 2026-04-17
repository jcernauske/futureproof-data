"""A/B validation: Gemma 4 vs Karpathy AI exposure scores.

Reads both Silver tables, computes the 8 validation gates specified in
``docs/specs/gemma-ai-exposure-rescore-v4.md`` §4, and writes a
markdown report to ``reports/gemma_vs_karpathy_comparison.md``.

Gates (all must pass for the Gold promote to be safe):

  1. Pearson correlation ≥ 0.6
  2. Mean absolute difference ≤ 2.0
  3. Mean signed delta ∈ [-1.0, +1.0]
  4. Max category bias ≤ 2.0 (categories with n ≥ 10 only)
  5. Distribution: max single-score concentration ≤ 40%
  6. Standard deviation ≥ 1.5
  7. Bucket coverage: ≥ 10% each in {0-3, 4-6, 7-10}
  8. Outlier rate: rows with |Δ| ≥ 4 comprise ≤ 5% of the overlap,
     and every outlier is listed in the markdown report for manual
     review.

Fail policy: when ``overall_pass=False``, the Gold promote MUST NOT
run. Operator either (a) revises the prompt / re-runs the batch, or
(b) documents an explicit override rationale in the spec's §6.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gate thresholds (spec §4)
# ---------------------------------------------------------------------------

GATE_CORRELATION_MIN = 0.6
GATE_MAD_MAX = 2.0
GATE_MEAN_DELTA_MIN = -1.0
GATE_MEAN_DELTA_MAX = 1.0
GATE_CATEGORY_BIAS_MAX = 2.0
GATE_CATEGORY_MIN_N = 10  # categories smaller than this don't gate
GATE_MODE_COLLAPSE_MAX_PCT = 40.0
GATE_STD_DEV_MIN = 1.5
GATE_BUCKET_MIN_PCT = 10.0
GATE_OUTLIER_DELTA = 4
GATE_OUTLIER_RATE_MAX_PCT = 5.0


# ---------------------------------------------------------------------------
# Statistics helpers (avoid scipy dep)
# ---------------------------------------------------------------------------


def _pearson(x: list[float], y: list[float]) -> float:
    """Pure-Python Pearson correlation coefficient.

    Returns 0.0 for degenerate inputs (length mismatch, empty, zero
    variance) — the associated gate check will fail loudly elsewhere.
    """
    n = len(x)
    if n == 0 or n != len(y):
        return 0.0
    mx = sum(x) / n
    my = sum(y) / n
    sxy = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    sx2 = sum((xi - mx) ** 2 for xi in x)
    sy2 = sum((yi - my) ** 2 for yi in y)
    denom = math.sqrt(sx2 * sy2)
    if denom == 0:
        return 0.0
    return sxy / denom


def _stdev(values: list[float]) -> float:
    """Sample standard deviation; 0.0 for <2 elements."""
    if len(values) < 2:
        return 0.0
    return statistics.pstdev(values)


# ---------------------------------------------------------------------------
# Gate evaluation
# ---------------------------------------------------------------------------


def validate_ab_comparison(
    gemma_scores: dict[str, dict], karpathy_scores: dict[str, dict]
) -> dict[str, Any]:
    """Compute the 8 validation gates.

    Args:
        gemma_scores: ``{soc_code: {"exposure_score": int, "category": str, ...}}``
        karpathy_scores: ``{soc_code: {"exposure_score": int, "category": str, ...}}``

    Returns:
        Dict with ``overall_pass``, ``gates`` (per-gate result),
        ``outliers`` (list for manual review), and coverage stats.
    """
    overlap = sorted(set(gemma_scores.keys()) & set(karpathy_scores.keys()))

    if not overlap:
        return {
            "overall_pass": False,
            "message": "No overlap between Gemma and Karpathy SOCs — cannot validate.",
            "overlap_count": 0,
            "gemma_coverage": len(gemma_scores),
            "karpathy_coverage": len(karpathy_scores),
            "gates": {},
            "outliers": [],
        }

    gemma_vals = [float(gemma_scores[s]["exposure_score"]) for s in overlap]
    karpathy_vals = [float(karpathy_scores[s]["exposure_score"]) for s in overlap]

    # Gate 1 — Pearson correlation
    correlation = _pearson(gemma_vals, karpathy_vals)
    gate1_pass = correlation >= GATE_CORRELATION_MIN

    # Gate 2 — Mean absolute difference
    mad = sum(abs(g - k) for g, k in zip(gemma_vals, karpathy_vals)) / len(overlap)
    gate2_pass = mad <= GATE_MAD_MAX

    # Gate 3 — Mean signed delta (systematic bias)
    mean_delta = sum(g - k for g, k in zip(gemma_vals, karpathy_vals)) / len(overlap)
    gate3_pass = GATE_MEAN_DELTA_MIN <= mean_delta <= GATE_MEAN_DELTA_MAX

    # Gate 4 — Category-level bias (guard small-N categories)
    category_deltas: dict[str, list[float]] = defaultdict(list)
    for soc, g, k in zip(overlap, gemma_vals, karpathy_vals):
        cat = karpathy_scores[soc].get("category") or "unknown"
        category_deltas[cat].append(g - k)

    category_stats: dict[str, dict[str, Any]] = {}
    gate4_violations: list[dict[str, Any]] = []
    max_gated_bias = 0.0
    for cat, deltas in category_deltas.items():
        mean_bias = sum(deltas) / len(deltas)
        gated = len(deltas) >= GATE_CATEGORY_MIN_N
        category_stats[cat] = {
            "n": len(deltas),
            "mean_delta": round(mean_bias, 3),
            "gated": gated,
        }
        if gated:
            max_gated_bias = max(max_gated_bias, abs(mean_bias))
            if abs(mean_bias) > GATE_CATEGORY_BIAS_MAX:
                gate4_violations.append({
                    "category": cat,
                    "n": len(deltas),
                    "mean_delta": round(mean_bias, 3),
                })
    gate4_pass = len(gate4_violations) == 0

    # Gate 5 — Mode collapse
    score_counts = Counter(gemma_vals)
    top_score, top_count = score_counts.most_common(1)[0]
    max_pct = 100.0 * top_count / len(gemma_vals)
    gate5_pass = max_pct <= GATE_MODE_COLLAPSE_MAX_PCT

    # Gate 6 — Standard deviation floor
    std_dev = _stdev(gemma_vals)
    gate6_pass = std_dev >= GATE_STD_DEV_MIN

    # Gate 7 — Bucket coverage
    low = sum(1 for v in gemma_vals if 0 <= v <= 3)
    mid = sum(1 for v in gemma_vals if 4 <= v <= 6)
    high = sum(1 for v in gemma_vals if 7 <= v <= 10)
    total = len(gemma_vals)
    low_pct = 100.0 * low / total
    mid_pct = 100.0 * mid / total
    high_pct = 100.0 * high / total
    gate7_pass = all(
        pct >= GATE_BUCKET_MIN_PCT for pct in (low_pct, mid_pct, high_pct)
    )

    # Gate 8 — Outlier list + rate
    outliers: list[dict[str, Any]] = []
    for soc, g, k in zip(overlap, gemma_vals, karpathy_vals):
        delta = g - k
        if abs(delta) >= GATE_OUTLIER_DELTA:
            outliers.append({
                "soc_code": soc,
                "gemma": int(g),
                "karpathy": int(k),
                "delta": int(delta),
                "category": karpathy_scores[soc].get("category") or "unknown",
                "title": (
                    karpathy_scores[soc].get("occupation_title")
                    or gemma_scores[soc].get("primary_title")
                    or ""
                ),
                "gemma_rationale": gemma_scores[soc].get("rationale") or "",
                "karpathy_rationale": karpathy_scores[soc].get("rationale") or "",
            })
    outlier_rate_pct = 100.0 * len(outliers) / len(overlap)
    gate8_pass = outlier_rate_pct <= GATE_OUTLIER_RATE_MAX_PCT

    all_pass = all([
        gate1_pass, gate2_pass, gate3_pass, gate4_pass,
        gate5_pass, gate6_pass, gate7_pass, gate8_pass,
    ])

    return {
        "overall_pass": all_pass,
        "overlap_count": len(overlap),
        "gemma_coverage": len(gemma_scores),
        "karpathy_coverage": len(karpathy_scores),
        "gates": {
            "correlation": {
                "value": round(correlation, 3),
                "threshold": f">= {GATE_CORRELATION_MIN}",
                "pass": gate1_pass,
            },
            "mean_absolute_diff": {
                "value": round(mad, 3),
                "threshold": f"<= {GATE_MAD_MAX}",
                "pass": gate2_pass,
            },
            "mean_signed_delta": {
                "value": round(mean_delta, 3),
                "threshold": f"[{GATE_MEAN_DELTA_MIN}, {GATE_MEAN_DELTA_MAX}]",
                "pass": gate3_pass,
            },
            "category_bias": {
                "max_gated_bias": round(max_gated_bias, 3),
                "threshold": f"<= {GATE_CATEGORY_BIAS_MAX} (n>={GATE_CATEGORY_MIN_N})",
                "pass": gate4_pass,
                "violations": gate4_violations,
                "per_category": category_stats,
            },
            "mode_collapse": {
                "top_score": top_score,
                "top_pct": round(max_pct, 2),
                "threshold": f"<= {GATE_MODE_COLLAPSE_MAX_PCT}%",
                "pass": gate5_pass,
            },
            "std_dev_floor": {
                "value": round(std_dev, 3),
                "threshold": f">= {GATE_STD_DEV_MIN}",
                "pass": gate6_pass,
            },
            "bucket_coverage": {
                "low_0_3_pct": round(low_pct, 2),
                "mid_4_6_pct": round(mid_pct, 2),
                "high_7_10_pct": round(high_pct, 2),
                "threshold": f">= {GATE_BUCKET_MIN_PCT}% each",
                "pass": gate7_pass,
            },
            "outlier_rate": {
                "count": len(outliers),
                "rate_pct": round(outlier_rate_pct, 2),
                "threshold": f"<= {GATE_OUTLIER_RATE_MAX_PCT}%",
                "pass": gate8_pass,
            },
        },
        "outliers": outliers,
    }


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


def _check(pass_: bool) -> str:
    return "PASS" if pass_ else "FAIL"


def render_markdown_report(result: dict[str, Any]) -> str:
    """Render the validation result as a markdown report."""
    lines: list[str] = []
    lines.append("# Gemma 4 vs Karpathy AI Exposure Score Comparison")
    lines.append("")
    lines.append(f"**Overall:** {_check(result['overall_pass'])}")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Gemma 4 scored: {result['gemma_coverage']} SOCs")
    lines.append(f"- Karpathy scored: {result['karpathy_coverage']} SOCs")
    lines.append(f"- Overlap: {result['overlap_count']} SOCs (A/B comparison set)")
    if result["gemma_coverage"] and result["karpathy_coverage"]:
        union = result["gemma_coverage"] + result["karpathy_coverage"] - result["overlap_count"]
        lines.append(f"- Union (expected Gold row count): {union}")
    lines.append("")

    if not result.get("gates"):
        lines.append(f"**{result.get('message', 'No gates evaluated.')}**")
        return "\n".join(lines)

    lines.append("## Gate Results")
    lines.append("")
    lines.append("| Gate | Value | Threshold | Result |")
    lines.append("|------|-------|-----------|--------|")
    gates = result["gates"]
    rows = [
        ("1. Pearson correlation", gates["correlation"]["value"], gates["correlation"]["threshold"], gates["correlation"]["pass"]),
        ("2. Mean absolute diff", gates["mean_absolute_diff"]["value"], gates["mean_absolute_diff"]["threshold"], gates["mean_absolute_diff"]["pass"]),
        ("3. Mean signed delta", gates["mean_signed_delta"]["value"], gates["mean_signed_delta"]["threshold"], gates["mean_signed_delta"]["pass"]),
        ("4. Max category bias (n>=10)", gates["category_bias"]["max_gated_bias"], gates["category_bias"]["threshold"], gates["category_bias"]["pass"]),
        ("5. Mode collapse", f"{gates['mode_collapse']['top_pct']}% on {gates['mode_collapse']['top_score']}", gates["mode_collapse"]["threshold"], gates["mode_collapse"]["pass"]),
        ("6. Std dev floor", gates["std_dev_floor"]["value"], gates["std_dev_floor"]["threshold"], gates["std_dev_floor"]["pass"]),
        ("7. Bucket coverage",
         f"low={gates['bucket_coverage']['low_0_3_pct']}% mid={gates['bucket_coverage']['mid_4_6_pct']}% high={gates['bucket_coverage']['high_7_10_pct']}%",
         gates["bucket_coverage"]["threshold"], gates["bucket_coverage"]["pass"]),
        ("8. Outlier rate", f"{gates['outlier_rate']['count']} rows ({gates['outlier_rate']['rate_pct']}%)", gates["outlier_rate"]["threshold"], gates["outlier_rate"]["pass"]),
    ]
    for name, value, threshold, pass_ in rows:
        lines.append(f"| {name} | {value} | {threshold} | {_check(pass_)} |")
    lines.append("")

    violations = gates["category_bias"]["violations"]
    if violations:
        lines.append("### Category bias violations")
        lines.append("")
        lines.append("| Category | n | Mean delta |")
        lines.append("|----------|---|------------|")
        for v in violations:
            lines.append(f"| {v['category']} | {v['n']} | {v['mean_delta']:+.3f} |")
        lines.append("")

    outliers = result.get("outliers") or []
    lines.append(f"## Outlier list (|Δ| ≥ {GATE_OUTLIER_DELTA}): {len(outliers)} rows")
    lines.append("")
    if outliers:
        lines.append("| SOC | Title | Gemma | Karpathy | Δ | Category |")
        lines.append("|-----|-------|-------|----------|---|----------|")
        for o in sorted(outliers, key=lambda r: -abs(r["delta"])):
            title_snippet = (o["title"] or "")[:50]
            lines.append(
                f"| {o['soc_code']} | {title_snippet} | {o['gemma']} | "
                f"{o['karpathy']} | {o['delta']:+d} | {o['category']} |"
            )
        lines.append("")
        lines.append("### Outlier rationale diff (top 10 by |Δ|)")
        lines.append("")
        for o in sorted(outliers, key=lambda r: -abs(r["delta"]))[:10]:
            lines.append(f"**{o['soc_code']} — {o['title']}** (Δ {o['delta']:+d})")
            lines.append("")
            lines.append(f"- *Gemma*: {o['gemma_rationale']}")
            lines.append(f"- *Karpathy*: {o['karpathy_rationale']}")
            lines.append("")
    else:
        lines.append("_No outliers._")
        lines.append("")

    if not result["overall_pass"]:
        lines.append("## Fail policy")
        lines.append("")
        lines.append(
            "`overall_pass=False` blocks the Gold promote. "
            "Operator must either (a) revise the prompt and re-run the "
            "batch, or (b) document an explicit override rationale in "
            "the spec §6 Implementation Log before proceeding."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(project_dir: Path | None = None) -> dict:
    """Run the A/B comparison end-to-end.

    Reads both Silver tables, runs the 8 gates, writes the markdown
    report, and returns the gate result dict.
    """
    import sys

    # Import lazily so `validate_ab_comparison` remains testable without
    # the pipeline deps.
    project_dir = Path(project_dir or Path(__file__).resolve().parent.parent).resolve()
    sys.path.insert(0, str(project_dir / "src"))
    from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

    silver_warehouse = project_dir / "data" / "silver" / "iceberg_warehouse"
    catalog_path = project_dir / "data" / "catalog" / "catalog.db"
    silver_catalog = get_catalog(silver_warehouse, catalog_path)

    gemma_table = silver_catalog.load_table("base.gemma_ai_exposure")
    karpathy_table = silver_catalog.load_table("base.karpathy_ai_exposure")

    gemma_rows = read_with_duckdb(gemma_table)
    karpathy_rows = read_with_duckdb(karpathy_table)

    gemma_scores = {
        (r.get("soc_code_normalized") or r.get("soc_code")): r
        for r in gemma_rows
        if (r.get("soc_code_normalized") or r.get("soc_code"))
        and r.get("exposure_score") is not None
    }
    karpathy_scores = {
        r["soc_code"]: r
        for r in karpathy_rows
        if r.get("soc_code") and r.get("bls_match")
    }

    result = validate_ab_comparison(gemma_scores, karpathy_scores)
    report_md = render_markdown_report(result)

    report_path = project_dir / "reports" / "gemma_vs_karpathy_comparison.md"
    report_path.write_text(report_md)
    logger.info("Report written to %s (overall_pass=%s)", report_path, result["overall_pass"])

    # Also write the machine-readable JSON next to it for CI consumption.
    json_path = project_dir / "reports" / "gemma_vs_karpathy_comparison.json"
    json_path.write_text(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    main()
