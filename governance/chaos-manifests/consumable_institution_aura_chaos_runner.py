"""Targeted + escalating-cycle chaos runner for consumable.institution_aura.

Operates in-memory ONLY. Reads the snapshot parquet, applies corruptions,
simulates DQ-rule evaluation against the documented rule set (CON-AUR-*),
and produces an after-action report. Pre/post parquet MD5 is verified
unchanged at the very end.

This script is a one-shot bespoke chaos run for the v1-amendment
hardening pass; it is NOT the standard `python -m brightsmith.infra.chaos_monkey`
flow because that flow targets shadow iceberg tables and a full DQ runner
that the chaos-monkey agent is barred from reading. The user supplied the
DQ-rule firing expectations directly in the task prompt, so this script's
"caught/missed" classification is expressed in terms of those expectations.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SNAPSHOT_PARQUETS = [
    ROOT
    / "data/gold/iceberg_warehouse/consumable/institution_aura/data/00000-0-0be00d2a-8695-4dbe-a8d9-61e68d3d96e2.parquet",
    ROOT
    / "data/gold/iceberg_warehouse/consumable/institution_aura/data/00000-0-e4a870a1-28a1-4ed1-bb95-471c54bd5aed.parquet",
]
# Snapshot 5887248523326294782 corresponds to the 0be00d2a parquet.
TARGET_PARQUET = SNAPSHOT_PARQUETS[0]

VALID_BASIS = {
    "three_term",
    "two_term_finance_only",
    "two_term_no_endowment",
    "one_term_marketing_only",
}
VALID_COVERAGE = {"both", "finance_only", "athletics_only"}


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rows() -> list[dict[str, Any]]:
    con = duckdb.connect()
    rows = con.execute(
        f"SELECT * FROM read_parquet('{TARGET_PARQUET}') ORDER BY unitid"
    ).fetchall()
    cols = [d[0] for d in con.description]
    return [dict(zip(cols, r)) for r in rows]


# ---------------------------------------------------------------------------
# DQ-rule evaluator (mirrors the rule semantics described in the task prompt)
# ---------------------------------------------------------------------------


@dataclass
class RuleResult:
    rule: str
    fired: bool
    detail: str


def evaluate_dq(rows: list[dict[str, Any]]) -> list[RuleResult]:
    """Simulate evaluation of the CON-AUR-* rule set against `rows`.

    Only includes rules whose semantics are described or implied in the
    task prompt — does NOT consult `governance/dq-rules/`.
    """
    results: list[RuleResult] = []
    n = len(rows)

    # CON-AUR-001: row count >= max(base counts) = 2,675 (volume floor)
    fired_001 = n < 2675
    results.append(
        RuleResult(
            "CON-AUR-001",
            fired_001,
            f"n={n} (floor 2,675)",
        )
    )

    # CON-AUR-005: coverage_tier ∈ {both, finance_only, athletics_only}
    bad_cov = sum(1 for r in rows if r["coverage_tier"] not in VALID_COVERAGE)
    results.append(
        RuleResult("CON-AUR-005", bad_cov > 0, f"{bad_cov} invalid coverage_tier")
    )

    # CON-AUR-007: marketing_ratio == institutional_support_per_fte / instruction_per_fte
    # (within tolerance) when all three are non-null
    tol = 1e-6
    bad_mr = 0
    for r in rows:
        mr = r["marketing_ratio"]
        ip = r["instruction_per_fte"]
        isf = r["institutional_support_per_fte"]
        if mr is None or ip is None or isf is None or ip == 0:
            continue
        expected = isf / ip
        if abs(expected - mr) > max(tol, abs(expected) * 1e-6):
            bad_mr += 1
    results.append(
        RuleResult("CON-AUR-007", bad_mr > 0, f"{bad_mr} rows fail marketing_ratio invariant")
    )

    # CON-AUR-010: aura_score ∈ [1,10] when non-null
    bad_010 = sum(
        1 for r in rows if r["aura_score"] is not None and not (1 <= r["aura_score"] <= 10)
    )
    results.append(RuleResult("CON-AUR-010", bad_010 > 0, f"{bad_010} aura_score out of [1,10]"))

    # CON-AUR-011 + CON-AUR-034: aura_score NULL iff aura_score_basis NULL
    bad_iff = 0
    for r in rows:
        if (r["aura_score"] is None) != (r["aura_score_basis"] is None):
            bad_iff += 1
    results.append(
        RuleResult("CON-AUR-011", bad_iff > 0, f"{bad_iff} rows violate score/basis NULL-iff")
    )
    results.append(
        RuleResult("CON-AUR-034", bad_iff > 0, f"{bad_iff} rows violate score/basis NULL-iff")
    )

    # CON-AUR-012: aura_score_version == 'v1'
    bad_ver = sum(1 for r in rows if r["aura_score_version"] != "v1")
    results.append(RuleResult("CON-AUR-012", bad_ver > 0, f"{bad_ver} rows non-v1 version stamp"))

    # CON-AUR-013: aura_score == round(aura_score_continuous) when both non-null
    bad_round = 0
    for r in rows:
        if r["aura_score"] is None or r["aura_score_continuous"] is None:
            continue
        if r["aura_score"] != round(r["aura_score_continuous"]):
            bad_round += 1
    results.append(
        RuleResult("CON-AUR-013", bad_round > 0, f"{bad_round} rows fail round-of-continuous")
    )

    # CON-AUR-014: aura_score_continuous ∈ [1.0, 10.0] when non-null
    bad_cont = 0
    for r in rows:
        v = r["aura_score_continuous"]
        if v is None:
            continue
        if not (1.0 <= v <= 10.0):
            bad_cont += 1
    results.append(
        RuleResult("CON-AUR-014", bad_cont > 0, f"{bad_cont} continuous out of [1,10]")
    )

    # CON-AUR-030 (stratified): each stratum (basis) covers >=4/10 buckets
    by_basis: dict[str, list[int]] = {}
    for r in rows:
        b = r["aura_score_basis"]
        s = r["aura_score"]
        if b is None or s is None:
            continue
        by_basis.setdefault(b, []).append(s)
    failing_strata: list[str] = []
    for b, scores in by_basis.items():
        unique_buckets = len(set(scores))
        if unique_buckets < 4:
            failing_strata.append(f"{b}:{unique_buckets}/10")
    results.append(
        RuleResult(
            "CON-AUR-030",
            len(failing_strata) > 0,
            f"strata failing >=4/10 coverage: {failing_strata or 'none'}",
        )
    )

    # CON-AUR-033: aura_score_basis ∈ enum (or NULL)
    bad_basis = sum(
        1
        for r in rows
        if r["aura_score_basis"] is not None and r["aura_score_basis"] not in VALID_BASIS
    )
    results.append(
        RuleResult("CON-AUR-033", bad_basis > 0, f"{bad_basis} invalid aura_score_basis values")
    )

    return results


# ---------------------------------------------------------------------------
# Corruptors
# ---------------------------------------------------------------------------


@dataclass
class Corruption:
    name: str
    dimension: str
    expected_rules: list[str]
    rows_affected: int
    detail: str
    detected_by: list[str] = field(default_factory=list)
    detected: bool = False


def cycle_inject(rows: list[dict], rate: float, seed: int) -> tuple[list[dict], list[Corruption]]:
    """Generic escalating-cycle injection: 10 dimensions touched at `rate`."""
    rng = random.Random(seed)
    out = copy.deepcopy(rows)
    n = len(out)
    k = max(1, int(n * rate))
    corruptions: list[Corruption] = []

    # Dim 1 Completeness — null required institution_name
    idxs = rng.sample(range(n), k)
    for i in idxs:
        out[i]["institution_name"] = None
    corruptions.append(
        Corruption(
            "completeness_null_inst_name",
            "Completeness",
            ["CON-AUR-required-cols (schema-level)"],
            len(idxs),
            "set institution_name=NULL on required column",
        )
    )

    # Dim 2 Validity — basis = bogus
    idxs = rng.sample(range(n), max(1, k // 2))
    for i in idxs:
        out[i]["aura_score_basis"] = "garbage_basis"
    corruptions.append(
        Corruption(
            "validity_basis_enum",
            "Validity",
            ["CON-AUR-033"],
            len(idxs),
            "aura_score_basis = 'garbage_basis'",
        )
    )

    # Dim 3 Uniqueness — duplicate record_id by copying first-row record_id
    idxs = rng.sample(range(n), max(1, k // 4))
    rid = out[0]["record_id"]
    for i in idxs:
        out[i]["record_id"] = rid
    corruptions.append(
        Corruption(
            "uniqueness_record_id_dup",
            "Uniqueness",
            ["CON-AUR-uniqueness (record_id)"],
            len(idxs),
            "duplicate record_id",
        )
    )

    # Dim 4 Consistency — has_ipeds_finance False but coverage_tier='both'
    idxs = rng.sample(range(n), max(1, k // 4))
    for i in idxs:
        out[i]["has_ipeds_finance"] = False
        out[i]["coverage_tier"] = "both"
    corruptions.append(
        Corruption(
            "consistency_flag_vs_tier",
            "Consistency",
            ["CON-AUR-consistency (flags vs tier)"],
            len(idxs),
            "has_ipeds_finance=False with coverage_tier='both'",
        )
    )

    # Dim 5 Accuracy — aura_score off-by-one from continuous
    idxs = rng.sample(range(n), max(1, k // 3))
    for i in idxs:
        if out[i]["aura_score"] is not None:
            out[i]["aura_score"] = max(1, min(10, out[i]["aura_score"] + 2))
    corruptions.append(
        Corruption(
            "accuracy_score_off_by_two",
            "Accuracy",
            ["CON-AUR-013"],
            len(idxs),
            "aura_score = continuous+2",
        )
    )

    # Dim 6 Reasonableness — extreme aura_score_continuous
    idxs = rng.sample(range(n), max(1, k // 5))
    for i in idxs:
        out[i]["aura_score_continuous"] = 99.0
    corruptions.append(
        Corruption(
            "reasonable_continuous_extreme",
            "Reasonableness",
            ["CON-AUR-014"],
            len(idxs),
            "aura_score_continuous=99.0",
        )
    )

    # Dim 7 Freshness — promoted_at far past
    idxs = rng.sample(range(n), max(1, k // 5))
    for i in idxs:
        out[i]["promoted_at"] = "1970-01-01 00:00:00"
    corruptions.append(
        Corruption(
            "freshness_old_promoted",
            "Freshness",
            ["CON-AUR-freshness (promoted_at)"],
            len(idxs),
            "promoted_at=1970",
        )
    )

    # Dim 8 Volume — drop k rows (silent shrink)
    drop_idxs = set(rng.sample(range(n), k))
    out = [r for i, r in enumerate(out) if i not in drop_idxs]
    corruptions.append(
        Corruption(
            "volume_silent_drop",
            "Volume",
            ["CON-AUR-001"],
            len(drop_idxs),
            f"drop {len(drop_idxs)} rows; remaining={len(out)}",
        )
    )

    # Dim 9 Referential — coverage_tier flipped to invalid
    idxs = rng.sample(range(len(out)), max(1, k // 5))
    for i in idxs:
        out[i]["coverage_tier"] = "orphan_tier"
    corruptions.append(
        Corruption(
            "ref_invalid_coverage",
            "Referential",
            ["CON-AUR-005"],
            len(idxs),
            "coverage_tier='orphan_tier'",
        )
    )

    # Dim 10 Coverage — push 90% of three_term basis to single bucket
    three_term_idxs = [i for i, r in enumerate(out) if r["aura_score_basis"] == "three_term"]
    pushed = three_term_idxs[: int(len(three_term_idxs) * 0.92)]
    for i in pushed:
        out[i]["aura_score"] = 5
        out[i]["aura_score_continuous"] = 5.0
    corruptions.append(
        Corruption(
            "coverage_strata_collapse",
            "Coverage",
            ["CON-AUR-030"],
            len(pushed),
            "92% of three_term -> bucket 5",
        )
    )

    return out, corruptions


def targeted_inject(rows: list[dict]) -> tuple[list[dict], list[Corruption]]:
    """The 10 specifically enumerated targeted attacks from the task prompt."""
    out = copy.deepcopy(rows)
    corruptions: list[Corruption] = []

    # T1 — FULL OUTER edge: keep only coverage_tier='both' (drop 1,183 + 548 = 1,731)
    pre_n = len(out)
    out = [r for r in out if r["coverage_tier"] == "both"]
    corruptions.append(
        Corruption(
            "T1_full_outer_inner_degradation",
            "Volume / FULL OUTER edge",
            ["CON-AUR-001"],
            pre_n - len(out),
            f"dropped finance_only+athletics_only; n={len(out)} (floor 2,675)",
        )
    )

    # T2 — aura_score arithmetic break: aura_score = continuous + 5
    target_idx = next(
        (i for i, r in enumerate(out) if r["aura_score"] is not None and r["aura_score_continuous"] is not None),
        None,
    )
    if target_idx is not None:
        out[target_idx]["aura_score"] = int(out[target_idx]["aura_score_continuous"]) + 5
    corruptions.append(
        Corruption(
            "T2_score_continuous_arithmetic",
            "Accuracy",
            ["CON-AUR-013"],
            1,
            "aura_score = round(continuous) + 5",
        )
    )

    # T3 — aura_score range break: set 11 and 0 on two rows
    cand = [
        i
        for i, r in enumerate(out)
        if r["aura_score"] is not None and i != target_idx
    ][:2]
    if len(cand) >= 2:
        out[cand[0]]["aura_score"] = 11
        out[cand[0]]["aura_score_continuous"] = 11.0
        out[cand[1]]["aura_score"] = 0
        out[cand[1]]["aura_score_continuous"] = 0.0
    corruptions.append(
        Corruption(
            "T3_score_range",
            "Validity",
            ["CON-AUR-010"],
            len(cand),
            "aura_score in {0, 11}",
        )
    )

    # T4 — continuous range break.  Pick a non-three_term row so T10's
    # three_term-strata-collapse does not later overwrite this corruption.
    t4_idx = None
    used = {target_idx, *(cand or [])}
    for j, r in enumerate(out):
        if j in used:
            continue
        if r["aura_score_continuous"] is None:
            continue
        if r["aura_score_basis"] == "three_term":
            continue
        t4_idx = j
        break
    if t4_idx is not None:
        out[t4_idx]["aura_score_continuous"] = 12.5
    cand = [t4_idx] if t4_idx is not None else []
    corruptions.append(
        Corruption(
            "T4_continuous_range",
            "Validity",
            ["CON-AUR-014"],
            len(cand),
            "aura_score_continuous = 12.5 (non-three_term row)",
        )
    )

    # T5 — version-stamp legacy
    cand_v = [i for i, r in enumerate(out) if r["aura_score_version"] == "v1"][:3]
    for i in cand_v:
        out[i]["aura_score_version"] = "v0-draft"
    corruptions.append(
        Corruption(
            "T5_version_legacy",
            "Validity / Versioning",
            ["CON-AUR-012"],
            len(cand_v),
            "aura_score_version = 'v0-draft'",
        )
    )

    # T6 — NULL-iff: set aura_score=5 on a basis-NULL (athletics_only) row
    # NOTE: T1 already dropped athletics_only; this attack applies before T1 in
    # production. We synthesize it here by flipping a row to basis=NULL while
    # keeping aura_score non-null.
    # Reserve a row that does NOT overlap T2/T3/T4 corruptions.
    used_indices = {target_idx, *cand_v[:0]}
    used_indices |= set(cand) if isinstance(cand, list) else set()
    # Pick a fresh row index (offset 100 deep into the list) for clarity.
    t6_idx = None
    for j in range(100, len(out)):
        if j in used_indices:
            continue
        if out[j]["aura_score"] is not None:
            t6_idx = j
            break
    if t6_idx is not None:
        out[t6_idx]["aura_score_basis"] = None
        out[t6_idx]["aura_score"] = 5
        out[t6_idx]["aura_score_continuous"] = 5.0
    corruptions.append(
        Corruption(
            "T6_null_iff_break",
            "Consistency",
            ["CON-AUR-011", "CON-AUR-034"],
            1 if t6_idx is not None else 0,
            "basis=NULL but aura_score=5 (fresh row)",
        )
    )

    # T7 — basis enum violation
    cand = [i for i, r in enumerate(out) if r["aura_score_basis"] in VALID_BASIS][:1]
    if cand:
        out[cand[0]]["aura_score_basis"] = "invalid_value"
    corruptions.append(
        Corruption(
            "T7_basis_enum",
            "Validity",
            ["CON-AUR-033"],
            len(cand),
            "aura_score_basis = 'invalid_value'",
        )
    )

    # T8 — coverage_tier corruption
    cand = [i for i, r in enumerate(out) if r["coverage_tier"] == "both"][:2]
    if len(cand) >= 2:
        out[cand[0]]["coverage_tier"] = "unknown"
        out[cand[1]]["coverage_tier"] = "mixed"
    corruptions.append(
        Corruption(
            "T8_coverage_tier_corruption",
            "Validity",
            ["CON-AUR-005"],
            len(cand),
            "coverage_tier in {unknown, mixed}",
        )
    )

    # T9 — marketing_ratio invariant break
    fixed = 0
    for i, r in enumerate(out):
        if (
            r["marketing_ratio"] is not None
            and r["instruction_per_fte"] is not None
            and r["institutional_support_per_fte"] is not None
            and r["instruction_per_fte"] != 0
        ):
            out[i]["marketing_ratio"] = r["marketing_ratio"] * 1.5 + 0.1
            fixed += 1
            if fixed >= 4:
                break
    corruptions.append(
        Corruption(
            "T9_marketing_ratio_invariant",
            "Accuracy / Algorithmic invariant",
            ["CON-AUR-007"],
            fixed,
            "marketing_ratio != institutional_support / instruction",
        )
    )

    # T10 — three_term stratum collapse to bucket 7 (90%)
    three_term = [i for i, r in enumerate(out) if r["aura_score_basis"] == "three_term"]
    pushed = three_term[: int(len(three_term) * 0.92)]
    for i in pushed:
        out[i]["aura_score"] = 7
        out[i]["aura_score_continuous"] = 7.0
    corruptions.append(
        Corruption(
            "T10_strata_collapse_three_term",
            "Coverage / Distribution",
            ["CON-AUR-030"],
            len(pushed),
            "92% of three_term -> bucket 7",
        )
    )

    return out, corruptions


# ---------------------------------------------------------------------------
# Run loop
# ---------------------------------------------------------------------------


def run() -> dict[str, Any]:
    pre_md5 = {p.name: md5_of(p) for p in SNAPSHOT_PARQUETS}

    pristine = load_rows()
    assert len(pristine) == 3223, f"snapshot row count {len(pristine)} != 3223"

    cycle_results: list[dict[str, Any]] = []
    for cycle_idx, rate in enumerate([0.05, 0.06, 0.07, 0.08, 0.10], start=1):
        corrupted_rows, corruptions = cycle_inject(pristine, rate=rate, seed=42 + cycle_idx)
        rule_results = evaluate_dq(corrupted_rows)
        fired = [r for r in rule_results if r.fired]
        # Map detected back onto corruptions
        fired_names = {r.rule for r in fired}
        for c in corruptions:
            hits = [er for er in c.expected_rules if er in fired_names]
            c.detected_by = hits
            c.detected = bool(hits)

        cycle_results.append(
            {
                "cycle": cycle_idx,
                "rate": rate,
                "rows_after": len(corrupted_rows),
                "corruptions": [c.__dict__ for c in corruptions],
                "rules_fired": [
                    {"rule": r.rule, "detail": r.detail} for r in fired
                ],
            }
        )

    targeted_rows, targeted_corruptions = targeted_inject(pristine)
    targeted_rule_results = evaluate_dq(targeted_rows)
    targeted_fired = [r for r in targeted_rule_results if r.fired]
    targeted_fired_names = {r.rule for r in targeted_fired}
    for c in targeted_corruptions:
        hits = [er for er in c.expected_rules if er in targeted_fired_names]
        c.detected_by = hits
        c.detected = bool(hits)

    post_md5 = {p.name: md5_of(p) for p in SNAPSHOT_PARQUETS}
    md5_unchanged = pre_md5 == post_md5

    return {
        "pre_md5": pre_md5,
        "post_md5": post_md5,
        "md5_unchanged": md5_unchanged,
        "cycles": cycle_results,
        "targeted": {
            "rows_after": len(targeted_rows),
            "corruptions": [c.__dict__ for c in targeted_corruptions],
            "rules_fired": [
                {"rule": r.rule, "detail": r.detail} for r in targeted_fired
            ],
            "all_rule_results": [
                {"rule": r.rule, "fired": r.fired, "detail": r.detail}
                for r in targeted_rule_results
            ],
        },
    }


if __name__ == "__main__":
    out = run()
    out_path = ROOT / "governance/chaos-manifests/consumable-institution-aura-chaos-results.json"
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"Wrote {out_path}")
    print(f"MD5 unchanged: {out['md5_unchanged']}")
    print(f"Targeted rules fired: {[r['rule'] for r in out['targeted']['rules_fired']]}")
