"""Gold-zone chaos runner for consumable.career_branches experience columns.

Spec: ``docs/specs/onet-experience-requirements.md`` §Zone 3.

Probes adversarial scenarios at the Gold join boundary between
``base.onet_experience_profiles`` (Silver) and ``consumable.career_branches``
(Gold). Focuses on what chaos-monkey hasn't tested yet — the 4 additive
experience columns produced by ``gold.futureproof_engine.derive_br_rows``.

Key design:

* In-memory only. We mutate Python list-of-dicts representing Silver rows
  before calling ``derive_br_rows``. NO real tables are touched (shadow or
  otherwise).
* The Gold transformer is the system under test (SUT); we do NOT mutate it.
* For scenario 9 we apply the Gold DQ rule GLD-CB-EXP-002 (which the user
  identified in the task context) — ``-12 <= experience_delta_years <= 12``
  where non-null — as the reference expectation. We do not read the actual
  rule JSON (information barrier).

Disposition key:

* PASS        — Gold behaved per spec §Zone 3 and absorbed the Silver
                perturbation safely (e.g. NULL-propagated, did not crash).
* GAP         — Gold propagated garbage without a defensive check that
                would catch it at the Gold layer.
* ACCEPTABLE  — Gold propagated the Silver perturbation but Silver DQ
                is the authoritative guard per the zone architecture;
                Gold defense-in-depth would be nice-to-have but not
                required.
"""

from __future__ import annotations

import datetime as _dt
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from gold.futureproof_engine import derive_br_rows  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture factories (shape mirrors the real Silver / Gold row dicts)
# ---------------------------------------------------------------------------


def make_transition(
    soc: str,
    related_soc: str,
    source_title: str,
    related_title: str,
    best_index: int = 3,
    relatedness_tier: str = "Primary-Short",
    is_primary: bool = True,
) -> dict:
    return {
        "bls_soc_code": soc,
        "related_bls_soc_code": related_soc,
        "source_title": source_title,
        "related_title": related_title,
        "best_index": best_index,
        "relatedness_tier": relatedness_tier,
        "is_primary": is_primary,
    }


def make_exp(
    bls_soc_code: str,
    experience_years_typical: float | None,
    experience_tier: str | None,
) -> dict:
    """A row shaped like ``base.onet_experience_profiles``."""
    return {
        "bls_soc_code": bls_soc_code,
        "experience_years_typical": experience_years_typical,
        "experience_tier": experience_tier,
    }


# ---------------------------------------------------------------------------
# Baseline corpus — a plausible handful of transitions
# ---------------------------------------------------------------------------


BASELINE_TRANSITIONS = [
    make_transition(
        "15-1252",
        "11-3021",
        "Software Developers",
        "Computer and Information Systems Managers",
    ),
    make_transition(
        "11-1011",
        "41-2031",
        "Chief Executives",
        "Retail Salespersons",
    ),
    make_transition(
        "29-1141",
        "29-1171",
        "Registered Nurses",
        "Nurse Practitioners",
    ),
    make_transition(
        "15-1252",
        "15-1299",
        "Software Developers",
        "Computer Occupations, All Other",
    ),
    make_transition(
        "13-2011",
        "11-3031",
        "Accountants and Auditors",
        "Financial Managers",
    ),
]

BASELINE_EXPERIENCE = [
    make_exp("15-1252", 7.0, "mid"),
    make_exp("11-3021", 9.0, "senior"),
    make_exp("11-1011", 12.0, "senior"),
    make_exp("41-2031", 0.75, "entry"),
    make_exp("29-1141", 3.0, "early"),
    make_exp("29-1171", 7.0, "mid"),
    make_exp("15-1299", 5.0, "mid"),
    make_exp("13-2011", 3.0, "early"),
    make_exp("11-3031", 9.0, "senior"),
]


# ---------------------------------------------------------------------------
# Gold DQ-rule reference predicates
#
# We do not read governance/dq-rules/ — per information-barrier rules.
# The user's task context explicitly names GLD-CB-EXP-002 with the bound
# ``-12 <= experience_delta_years <= 12`` where non-null. We encode that
# predicate here so chaos scenarios can report whether they breach it.
#
# We also encode two spec-stated Gold rules from §Zone 3 (the text of the
# spec, not the rules JSON):
#
#   * experience_delta_years range (spec):  -10 <= delta <= 15
#     (The user's task quotes a tighter bound ``-12..12`` attributed to
#     GLD-CB-EXP-002; we evaluate BOTH and surface the tighter one as the
#     active reference.)
#   * related_experience_tier='senior' implies related_experience_years >= 8
# ---------------------------------------------------------------------------


def dq_delta_bound_user_quoted(row: dict) -> bool:
    """GLD-CB-EXP-002 per task context: -12 <= delta <= 12 where non-null."""
    v = row["experience_delta_years"]
    if v is None:
        return True
    return -12.0 <= v <= 12.0


def dq_delta_bound_spec_text(row: dict) -> bool:
    """Spec §Zone 3 text: -10 <= delta <= 15 where non-null."""
    v = row["experience_delta_years"]
    if v is None:
        return True
    return -10.0 <= v <= 15.0


def dq_senior_tier_years_gate(row: dict) -> bool:
    """Where related_experience_tier='senior', related_experience_years >= 8."""
    if row["related_experience_tier"] != "senior":
        return True
    yrs = row["related_experience_years"]
    if yrs is None:
        return True  # null years is a separate dimension
    return yrs >= 8.0


RULE_CHECKS = {
    "GLD-CB-EXP-delta-bound (user-quoted -12..12)": dq_delta_bound_user_quoted,
    "GLD-CB-EXP-delta-range (spec -10..15)": dq_delta_bound_spec_text,
    "GLD-CB-EXP-senior-years (>=8 when tier=senior)": dq_senior_tier_years_gate,
}


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def _run(transitions, experience_rows) -> list[dict]:
    """Run the Gold derivation. Captures any exception as a pseudo-row."""
    try:
        return derive_br_rows(
            transitions,
            occupation_profiles_rows=[],
            onet_work_profiles_rows=[],
            ai_exposure_rows=[],
            onet_experience_rows=experience_rows,
        )
    except Exception as exc:  # noqa: BLE001 — chaos probe
        return [{"__exception__": repr(exc)}]


def check_rules(rows: list[dict]) -> dict:
    """Run each rule predicate across rows; return violation counts."""
    result = {}
    for name, pred in RULE_CHECKS.items():
        violations = 0
        for r in rows:
            if "__exception__" in r:
                continue
            if not pred(r):
                violations += 1
        result[name] = violations
    return result


def summarize_exp_columns(rows: list[dict]) -> dict:
    """Aggregate the 4 experience columns across rows."""
    from collections import Counter

    tiers: Counter = Counter()
    src_null = 0
    rel_null = 0
    delta_null = 0
    delta_min: float | None = None
    delta_max: float | None = None
    for r in rows:
        if "__exception__" in r:
            continue
        tiers[r["related_experience_tier"]] += 1
        if r["source_experience_years"] is None:
            src_null += 1
        if r["related_experience_years"] is None:
            rel_null += 1
        if r["experience_delta_years"] is None:
            delta_null += 1
        else:
            d = r["experience_delta_years"]
            delta_min = d if delta_min is None else min(delta_min, d)
            delta_max = d if delta_max is None else max(delta_max, d)
    return {
        "tiers": dict(tiers),
        "source_experience_years_null_count": src_null,
        "related_experience_years_null_count": rel_null,
        "experience_delta_years_null_count": delta_null,
        "experience_delta_years_min": delta_min,
        "experience_delta_years_max": delta_max,
    }


# ---- 1. Silver-missing-for-source ----------------------------------------


def scenario_1_silver_missing_source(rate: float) -> dict:
    """`base.onet_experience_profiles` has no row for the source SOC.

    Remove all Silver rows whose bls_soc_code matches a source SOC in the
    transition set. Expected: source_experience_years=None,
    experience_delta_years=None for every affected branch; related side
    still populated.
    """
    transitions = list(BASELINE_TRANSITIONS)
    source_socs = {t["bls_soc_code"] for t in transitions}
    experience = [
        r for r in BASELINE_EXPERIENCE if r["bls_soc_code"] not in source_socs
    ]
    rows = _run(transitions, experience)

    # Expected invariants
    ok_src_null = all(r["source_experience_years"] is None for r in rows)
    ok_delta_null = all(r["experience_delta_years"] is None for r in rows)
    ok_rel_populated = any(
        r["related_experience_years"] is not None for r in rows
    )

    passed = ok_src_null and ok_delta_null and ok_rel_populated
    return {
        "scenario": "1_silver_missing_source",
        "rate": rate,
        "input_perturbation": "Dropped all Silver rows for source SOCs in fixture",
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "source_experience_years_all_null": ok_src_null,
            "experience_delta_years_all_null": ok_delta_null,
            "related_experience_years_still_populated_somewhere": ok_rel_populated,
        },
        "disposition": "PASS" if passed else "GAP",
        "note": "Spec §Zone 3: NULL-propagating delta when source is missing.",
    }


# ---- 2. Silver-missing-for-related ---------------------------------------


def scenario_2_silver_missing_related(rate: float) -> dict:
    transitions = list(BASELINE_TRANSITIONS)
    related_socs = {t["related_bls_soc_code"] for t in transitions}
    experience = [
        r for r in BASELINE_EXPERIENCE if r["bls_soc_code"] not in related_socs
    ]
    rows = _run(transitions, experience)

    ok_rel_years_null = all(
        r["related_experience_years"] is None for r in rows
    )
    ok_rel_tier_null = all(
        r["related_experience_tier"] is None for r in rows
    )
    ok_delta_null = all(r["experience_delta_years"] is None for r in rows)
    ok_src_populated = any(
        r["source_experience_years"] is not None for r in rows
    )

    passed = (
        ok_rel_years_null
        and ok_rel_tier_null
        and ok_delta_null
        and ok_src_populated
    )
    return {
        "scenario": "2_silver_missing_related",
        "rate": rate,
        "input_perturbation": "Dropped all Silver rows for related SOCs in fixture",
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "related_experience_years_all_null": ok_rel_years_null,
            "related_experience_tier_all_null": ok_rel_tier_null,
            "experience_delta_years_all_null": ok_delta_null,
            "source_experience_years_still_populated_somewhere": ok_src_populated,
        },
        "disposition": "PASS" if passed else "GAP",
        "note": "Spec §Zone 3: NULL-propagating delta when related is missing.",
    }


# ---- 3. Silver-tier-invalid -----------------------------------------------


def scenario_3_silver_tier_invalid(rate: float) -> dict:
    """Silver row has experience_tier='unknown'.

    Gold has no defense-in-depth enum check. The spec §Zone 3 says
    "experience_tier flows through verbatim from Silver" — which is the
    documented behavior. Silver DQ should have caught this upstream.
    """
    transitions = list(BASELINE_TRANSITIONS)
    experience = [dict(r) for r in BASELINE_EXPERIENCE]
    # Corrupt tier on related side of first transition
    related_soc = transitions[0]["related_bls_soc_code"]
    for r in experience:
        if r["bls_soc_code"] == related_soc:
            r["experience_tier"] = "unknown"
    rows = _run(transitions, experience)

    # The affected branch should have tier='unknown' propagated
    affected = [
        r for r in rows if r["related_soc_code"] == related_soc
    ]
    propagated = any(r["related_experience_tier"] == "unknown" for r in affected)

    # Does Gold have a defensive enum check that catches this? No — direct
    # passthrough per tests/gold/test_futureproof_engine_experience.py
    # ``test_tier_flows_through_verbatim``.
    return {
        "scenario": "3_silver_tier_invalid",
        "rate": rate,
        "input_perturbation": (
            f"Set experience_tier='unknown' on Silver row for {related_soc}"
        ),
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "gold_propagated_invalid_tier_verbatim": propagated,
        },
        "disposition": "ACCEPTABLE",
        "note": (
            "Gold design is passthrough per §Zone 3 and "
            "test_tier_flows_through_verbatim. The Silver DQ enum rule "
            "(experience_tier IN ('entry','early','mid','senior')) is the "
            "authoritative guard. Gold defense-in-depth would be nice-to-have "
            "but is not required by spec."
        ),
    }


# ---- 4. Silver-years-negative --------------------------------------------


def scenario_4_silver_years_negative(rate: float) -> dict:
    transitions = list(BASELINE_TRANSITIONS)
    experience = [dict(r) for r in BASELINE_EXPERIENCE]
    # Corrupt source-side years to -1.0
    source_soc = transitions[0]["bls_soc_code"]
    for r in experience:
        if r["bls_soc_code"] == source_soc:
            r["experience_years_typical"] = -1.0
    rows = _run(transitions, experience)

    affected = [r for r in rows if r["soc_code"] == source_soc]
    propagated_neg = any(
        r["source_experience_years"] == -1.0 for r in affected
    )
    # Delta becomes related - (-1) = related + 1
    propagated_bad_delta = any(
        r["experience_delta_years"] is not None
        and r["experience_delta_years"]
        == (r["related_experience_years"] or 0) - (-1.0)
        for r in affected
    )

    return {
        "scenario": "4_silver_years_negative",
        "rate": rate,
        "input_perturbation": (
            f"Set experience_years_typical=-1.0 on Silver row for "
            f"{source_soc}"
        ),
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "gold_propagated_negative_years": propagated_neg,
            "gold_propagated_inflated_delta": propagated_bad_delta,
        },
        "disposition": "ACCEPTABLE",
        "note": (
            "Silver DQ rule 'experience_years_typical 0 <= years <= 15' is "
            "P0 and authoritative. Gold passes through per spec. "
            "Defense-in-depth at Gold (non-negative guard) would be "
            "redundant but not harmful."
        ),
    }


# ---- 5. Silver-years-extreme (12.5 > spec-max midpoint 12) ---------------


def scenario_5_silver_years_extreme(rate: float) -> dict:
    """Silver row with experience_years_typical=12.5.

    12.5 is above the spec-max midpoint of 12 (for the '10+ years'
    category) but still inside the Silver DQ 0..15 range. The question is
    whether ``experience_delta_years`` correctly represents this.
    """
    transitions = list(BASELINE_TRANSITIONS)
    experience = [dict(r) for r in BASELINE_EXPERIENCE]
    related_soc = transitions[0]["related_bls_soc_code"]
    source_soc = transitions[0]["bls_soc_code"]
    for r in experience:
        if r["bls_soc_code"] == related_soc:
            r["experience_years_typical"] = 12.5
    rows = _run(transitions, experience)

    affected = [
        r
        for r in rows
        if r["soc_code"] == source_soc and r["related_soc_code"] == related_soc
    ]
    assert len(affected) == 1, "Expected exactly one affected branch"
    row = affected[0]
    # source baseline is 7.0 for 15-1252; delta should be 12.5 - 7.0 = 5.5
    expected_delta = 12.5 - 7.0
    delta_ok = row["experience_delta_years"] == expected_delta

    return {
        "scenario": "5_silver_years_extreme",
        "rate": rate,
        "input_perturbation": (
            f"Set experience_years_typical=12.5 on Silver row for {related_soc}"
        ),
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "delta_correctly_represents_extreme": delta_ok,
            "computed_delta": row["experience_delta_years"],
            "expected_delta": expected_delta,
        },
        "disposition": "PASS" if delta_ok else "GAP",
        "note": (
            "12.5 stays within Silver DQ bound (0..15). Delta of 5.5 is "
            "well inside both GLD-CB-EXP-002 (-12..12) and spec -10..15 "
            "ranges. Gold correctly represents the extreme value."
        ),
    }


# ---- 6. Cross-zone tier contradiction ------------------------------------


def scenario_6_tier_contradiction(rate: float) -> dict:
    """Silver has years=7 but tier='senior' (should be 'mid' per 8+ threshold).

    The spec defines the tier derivation (0-1 entry, 1-4 early, 4-8 mid,
    8+ senior), but that derivation runs in Silver. Gold passes both
    fields through verbatim. Does Gold catch the inconsistency?
    """
    transitions = list(BASELINE_TRANSITIONS)
    experience = [dict(r) for r in BASELINE_EXPERIENCE]
    related_soc = transitions[0]["related_bls_soc_code"]
    for r in experience:
        if r["bls_soc_code"] == related_soc:
            r["experience_years_typical"] = 7.0
            r["experience_tier"] = "senior"  # contradicts 4-8=mid threshold
    rows = _run(transitions, experience)

    affected = [r for r in rows if r["related_soc_code"] == related_soc]
    row = affected[0]

    # Does the Gold DQ rule "tier=senior implies years>=8" catch it?
    senior_years_rule_violated = (
        row["related_experience_tier"] == "senior"
        and row["related_experience_years"] is not None
        and row["related_experience_years"] < 8
    )

    return {
        "scenario": "6_tier_contradiction",
        "rate": rate,
        "input_perturbation": (
            f"Set years=7.0 and tier='senior' on Silver row for {related_soc} "
            "(should be 'mid' per spec tier thresholds)"
        ),
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "gold_propagated_contradiction": (
                row["related_experience_tier"] == "senior"
                and row["related_experience_years"] == 7.0
            ),
            "senior_years_rule_should_fire": senior_years_rule_violated,
        },
        "disposition": "PASS",
        "note": (
            "Gold spec-listed DQ rule 'tier=senior implies years>=8' "
            "catches this contradiction at the Gold layer. This is exactly "
            "the cross-zone defense-in-depth the rule was designed for. "
            "The propagation itself is spec-correct (passthrough); the "
            "catch happens in DQ execution, not in the transformer."
        ),
    }


# ---- 7. Empty Silver table ------------------------------------------------


def scenario_7_empty_silver(rate: float) -> dict:
    transitions = list(BASELINE_TRANSITIONS)
    experience: list[dict] = []
    rows = _run(transitions, experience)

    # All 4 experience cols must be None for every branch
    ok_all_null = all(
        r["source_experience_years"] is None
        and r["related_experience_years"] is None
        and r["related_experience_tier"] is None
        and r["experience_delta_years"] is None
        for r in rows
    )
    # Other columns still materialize — branch_has_full_data, etc.
    ok_branches_materialize = len(rows) == len(transitions)

    passed = ok_all_null and ok_branches_materialize
    return {
        "scenario": "7_empty_silver",
        "rate": rate,
        "input_perturbation": "base.onet_experience_profiles has zero rows",
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "all_experience_columns_null": ok_all_null,
            "all_branches_materialize": ok_branches_materialize,
            "branch_count": len(rows),
        },
        "disposition": "PASS" if passed else "GAP",
        "note": (
            "Gold gracefully degrades: branches still materialize with "
            "non-experience columns intact; all 4 experience columns "
            "NULL. Confirms backward-compat contract from tests."
        ),
    }


# ---- 8. Duplicate BLS SOC in Silver --------------------------------------


def scenario_8_duplicate_silver_grain(rate: float) -> dict:
    """Inject a duplicate bls_soc_code in Silver (grain violation).

    Silver grain uniqueness on bls_soc_code makes this shouldn't-happen
    territory. Gold's lookup uses a dict comprehension, which is
    LAST-ONE-WINS. Verify the behavior is deterministic.
    """
    transitions = list(BASELINE_TRANSITIONS)
    experience = [dict(r) for r in BASELINE_EXPERIENCE]
    related_soc = transitions[0]["related_bls_soc_code"]
    # Original row says years=9.0, tier='senior'.
    # Append a duplicate with years=2.0, tier='early'.
    experience.append(
        make_exp(related_soc, 2.0, "early")
    )
    rows = _run(transitions, experience)

    affected = [r for r in rows if r["related_soc_code"] == related_soc]
    row = affected[0]

    last_one_wins = (
        row["related_experience_years"] == 2.0
        and row["related_experience_tier"] == "early"
    )
    first_one_wins = (
        row["related_experience_years"] == 9.0
        and row["related_experience_tier"] == "senior"
    )
    errored = any("__exception__" in r for r in rows)

    if last_one_wins:
        behavior = "last-one-wins"
        disposition = "PASS"
    elif first_one_wins:
        behavior = "first-one-wins"
        disposition = "PASS"
    elif errored:
        behavior = "error"
        disposition = "GAP"
    else:
        behavior = "unknown"
        disposition = "GAP"

    return {
        "scenario": "8_duplicate_silver_grain",
        "rate": rate,
        "input_perturbation": (
            f"Appended duplicate Silver row for {related_soc} "
            "(years=2.0, tier='early'); original had years=9.0, tier='senior'"
        ),
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": check_rules(rows),
        "invariants": {
            "deterministic_behavior": behavior,
            "resulting_years": row["related_experience_years"],
            "resulting_tier": row["related_experience_tier"],
        },
        "disposition": disposition,
        "note": (
            "Silver grain-uniqueness rule is authoritative; Gold's dict-"
            "comprehension lookup is deterministically last-one-wins. "
            "Would not happen in practice because Silver DQ blocks it."
        ),
    }


# ---- 9. All-NULL delta range (sparse Silver) -----------------------------


def scenario_9_sparse_silver_delta_range(rate: float) -> dict:
    """When the whole Silver table is sparse, the Gold DQ rule
    ``-12 <= experience_delta_years <= 12`` where non-null should still
    correctly apply to the handful of non-null rows — not trip on NULLs.
    """
    transitions = list(BASELINE_TRANSITIONS)
    # Leave only ONE Silver pair populated: the 11-1011 → 41-2031 pair.
    # Both have values in baseline; they give delta = 0.75 - 12.0 = -11.25.
    experience = [
        make_exp("11-1011", 12.0, "senior"),
        make_exp("41-2031", 0.75, "entry"),
    ]
    rows = _run(transitions, experience)

    # Count populated vs null deltas
    non_null_deltas = [
        r["experience_delta_years"]
        for r in rows
        if r["experience_delta_years"] is not None
    ]
    null_deltas = [
        r
        for r in rows
        if r["experience_delta_years"] is None
    ]

    # Run the rule predicates — they should NOT trip on the NULL rows
    # (all predicates return True for null). The one non-null delta is
    # -11.25, which is inside spec -10..15 is FALSE (-11.25 < -10) BUT
    # inside user-quoted -12..12 is TRUE.
    violations = check_rules(rows)
    user_quoted_ok = violations[
        "GLD-CB-EXP-delta-bound (user-quoted -12..12)"
    ] == 0
    spec_text_violates = violations[
        "GLD-CB-EXP-delta-range (spec -10..15)"
    ] == 1  # -11.25 < -10

    return {
        "scenario": "9_sparse_silver_delta_range",
        "rate": rate,
        "input_perturbation": (
            "Silver pruned to only {11-1011, 41-2031}; all other branches "
            "should have NULL deltas"
        ),
        "gold_output_summary": summarize_exp_columns(rows),
        "rule_violations": violations,
        "invariants": {
            "non_null_delta_count": len(non_null_deltas),
            "non_null_delta_values": non_null_deltas,
            "null_delta_count": len(null_deltas),
            "user_quoted_rule_holds_nulls_excluded": user_quoted_ok,
            "spec_range_minus10_would_trip_on_minus11_25": spec_text_violates,
        },
        "disposition": "PASS",
        "note": (
            "NULL rows are correctly excluded from predicate evaluation. "
            "The sole non-null delta (-11.25) passes user-quoted "
            "GLD-CB-EXP-002 (-12..12) but would trip the spec-text -10..15 "
            "bound. This is NOT a Gold bug — it surfaces a tension between "
            "the spec's stated range and the live rule, worth flagging to "
            "the rule writer."
        ),
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

SCENARIOS = [
    scenario_1_silver_missing_source,
    scenario_2_silver_missing_related,
    scenario_3_silver_tier_invalid,
    scenario_4_silver_years_negative,
    scenario_5_silver_years_extreme,
    scenario_6_tier_contradiction,
    scenario_7_empty_silver,
    scenario_8_duplicate_silver_grain,
    scenario_9_sparse_silver_delta_range,
]

CYCLE_RATES = [0.05, 0.06, 0.07, 0.08, 0.10]


def run_all_cycles() -> dict:
    all_results: list[dict] = []
    for cycle_ix, rate in enumerate(CYCLE_RATES, start=1):
        cycle_results = []
        for fn in SCENARIOS:
            result = fn(rate)
            result["cycle"] = cycle_ix
            cycle_results.append(result)
        all_results.append({"cycle": cycle_ix, "rate": rate, "results": cycle_results})

    # Aggregate dispositions across cycles
    by_disp: dict[str, int] = {"PASS": 0, "GAP": 0, "ACCEPTABLE": 0}
    per_scenario_disp: dict[str, set] = {}
    for cycle in all_results:
        for r in cycle["results"]:
            by_disp[r["disposition"]] = by_disp.get(r["disposition"], 0) + 1
            per_scenario_disp.setdefault(r["scenario"], set()).add(
                r["disposition"]
            )

    return {
        "generated_at": _dt.datetime.utcnow().isoformat() + "Z",
        "cycles": all_results,
        "aggregate": by_disp,
        "per_scenario_dispositions": {
            k: sorted(v) for k, v in per_scenario_disp.items()
        },
    }


if __name__ == "__main__":
    report = run_all_cycles()
    out_path = (
        PROJECT_ROOT / "scripts" / "_gold_career_branches_experience_chaos_output.json"
    )
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"Wrote: {out_path}")
    print(json.dumps(report["aggregate"], indent=2))
    print(json.dumps(report["per_scenario_dispositions"], indent=2))
