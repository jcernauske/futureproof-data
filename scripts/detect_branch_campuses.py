"""Detect multi-campus university families with inherited earnings data.

Spec: docs/specs/feature-branch-campus-suppression.md (§4 Phase 1).

Run via:
    uv run python scripts/detect_branch_campuses.py

Output:
    logs/branch_campus_detection_<timestamp>.json

Reads ``consumable.career_outcomes`` from the Gold Iceberg parquet, clusters
institutions by name prefix (text before the first hyphen, with ampersand
whitespace normalized), and for each candidate family identifies a flagship
and flags branches whose per-CIP earnings inherit the flagship's value.

The output is a one-time human-reviewed artifact: nothing in the codebase
consumes this JSON directly. After human review, the approved subset is
hand-translated into ``backend/app/config/branch_campuses.py``.

Calibration (per @fp-data-reviewer in spec §5):
- Pre-normalize ``" & "`` whitespace around ampersands so Texas A&M variants
  collapse into one prefix group.
- Flagship pick prefers (a) known-suffix list, (b) "main"/"main campus"
  keyword, (c) most CIPs (for breadth), (d) highest median earnings as
  final tiebreak. Sort by UNITID before picking to keep results deterministic.
- ``family_size`` reported per family is ``1 + count(branches recommended for
  suppression)``, NOT the raw prefix-group size, so prefix collisions like
  Stevens-Henager / Stevens-Institute don't inflate the count.
- ``low_overlap_warning = True`` when fewer than 10 CIPs overlap with the
  flagship — flags Embry-Riddle-style cases where a 1.00 inheritance ratio
  on a thin overlap could be coincidence rather than systemic inheritance.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

# Resolve relative to the repo root (parent of this script's directory) so
# the script works regardless of the caller's CWD. Don't switch to a
# CWD-relative path here — running from ``scripts/`` would silently match
# zero files and produce an empty config update.
_REPO_ROOT = Path(__file__).resolve().parents[1]
PARQUET_GLOB = str(
    _REPO_ROOT
    / "data"
    / "gold"
    / "iceberg_warehouse"
    / "consumable"
    / "career_outcomes"
    / "data"
    / "*.parquet"
)
LOGS_DIR = _REPO_ROOT / "logs"

DETECTION_THRESHOLD = 3
INHERITANCE_THRESHOLD = 0.80
LOW_OVERLAP_THRESHOLD = 10

KNOWN_FLAGSHIP_SUFFIXES: dict[str, list[str]] = {
    "Ohio University": ["Main Campus"],
    "Indiana University": ["Bloomington"],
    "Pennsylvania State University": ["University Park", "Main Campus"],
    "University of Wisconsin": ["Madison"],
    "Purdue University": ["Main Campus", "West Lafayette"],
    "Texas A & M University": ["College Station"],
}

GENERIC_FLAGSHIP_KEYWORDS = ["main campus", "main"]


def normalize_name(raw: str) -> str:
    """Collapse ampersand whitespace so ``Texas A&M`` and ``Texas A & M`` agree."""
    return re.sub(r"\s*&\s*", " & ", raw).strip()


def name_prefix(name: str) -> str:
    return name.split("-", 1)[0].strip()


def load_career_outcomes() -> pd.DataFrame:
    con = duckdb.connect()
    df = con.sql(
        f"""
        SELECT DISTINCT
            unitid,
            institution_name,
            cipcode,
            earnings_1yr_median
        FROM read_parquet('{PARQUET_GLOB}')
        WHERE earnings_1yr_median IS NOT NULL
          AND institution_name IS NOT NULL
        """
    ).df()
    if df.empty:
        raise RuntimeError(
            f"No rows loaded from {PARQUET_GLOB}. Verify that the Gold "
            "consumable.career_outcomes table has been materialized — run "
            "the College Scorecard pipeline first."
        )
    df["institution_name_norm"] = df["institution_name"].map(normalize_name)
    df["name_prefix"] = df["institution_name_norm"].map(name_prefix)
    return df


def identify_flagship(family_df: pd.DataFrame, prefix: str) -> int:
    """Return the UNITID of the flagship for this family.

    Determinism: sort by UNITID before any ``.iloc[0]`` so that ties on the
    chosen heuristic don't depend on parquet row ordering.
    """
    family_df = family_df.sort_values("unitid")

    suffixes = KNOWN_FLAGSHIP_SUFFIXES.get(prefix, [])
    for suffix in suffixes:
        match = family_df[
            family_df["institution_name_norm"].str.contains(
                re.escape(suffix), case=False, regex=True
            )
        ]
        if not match.empty:
            return int(match["unitid"].iloc[0])

    for keyword in GENERIC_FLAGSHIP_KEYWORDS:
        match = family_df[
            family_df["institution_name_norm"]
            .str.lower()
            .str.contains(keyword, regex=False)
        ]
        if not match.empty:
            return int(match["unitid"].iloc[0])

    cip_count = family_df.groupby("unitid")["cipcode"].nunique()
    earnings_median = family_df.groupby("unitid")["earnings_1yr_median"].median()
    ranking = (
        pd.DataFrame({"cip_count": cip_count, "earnings": earnings_median})
        .sort_values(["cip_count", "earnings"], ascending=[False, False])
    )
    return int(ranking.index[0])


def analyze_branch(
    branch_df: pd.DataFrame, flagship_earnings: pd.Series
) -> tuple[int, int, float, bool]:
    inherited = 0
    total = 0
    for _, row in branch_df.iterrows():
        cip = row["cipcode"]
        if cip not in flagship_earnings.index:
            continue
        total += 1
        if abs(row["earnings_1yr_median"] - flagship_earnings.loc[cip]) < 1.0:
            inherited += 1
    ratio = inherited / total if total > 0 else 0.0
    suppress = total > 0 and ratio >= INHERITANCE_THRESHOLD
    return inherited, total, ratio, suppress


def detect() -> dict:
    df = load_career_outcomes()

    family_unitid_counts = df.groupby("name_prefix")["unitid"].nunique()
    candidate_prefixes = sorted(
        family_unitid_counts[family_unitid_counts >= DETECTION_THRESHOLD].index
    )

    families: list[dict] = []
    for prefix in candidate_prefixes:
        family_df = df[df["name_prefix"] == prefix].copy()
        flagship_unitid = identify_flagship(family_df, prefix)
        flagship_rows = family_df[family_df["unitid"] == flagship_unitid]
        flagship_name = str(flagship_rows["institution_name"].iloc[0])
        flagship_earnings = (
            flagship_rows.drop_duplicates(subset=["cipcode"])
            .set_index("cipcode")["earnings_1yr_median"]
        )

        branch_unitids = sorted(
            int(u)
            for u in family_df[family_df["unitid"] != flagship_unitid][
                "unitid"
            ].unique()
        )

        branches: list[dict] = []
        suppress_count = 0
        for branch_uid in branch_unitids:
            branch_rows = family_df[family_df["unitid"] == branch_uid]
            branch_name = str(branch_rows["institution_name"].iloc[0])
            inherited, total, ratio, suppress = analyze_branch(
                branch_rows, flagship_earnings
            )
            if suppress:
                suppress_count += 1
            branches.append(
                {
                    "unitid": branch_uid,
                    "institution_name": branch_name,
                    "inherited_earnings_count": inherited,
                    "total_overlapping_cips": total,
                    "inheritance_ratio": round(ratio, 4),
                    "suppress_recommended": suppress,
                    "low_overlap_warning": total < LOW_OVERLAP_THRESHOLD,
                }
            )

        families.append(
            {
                "name_prefix": prefix,
                "raw_prefix_group_size": int(len(branch_unitids) + 1),
                "family_size_for_suppression": suppress_count + 1,
                "flagship_unitid": int(flagship_unitid),
                "flagship_name": flagship_name,
                "flagship_cip_count": int(len(flagship_earnings)),
                "branches_recommended_for_suppression": suppress_count,
                "branches": branches,
            }
        )

    families.sort(
        key=lambda f: (-f["branches_recommended_for_suppression"], f["name_prefix"])
    )

    total_suppressed = sum(
        f["branches_recommended_for_suppression"] for f in families
    )
    families_with_suppression = sum(
        1 for f in families if f["branches_recommended_for_suppression"] > 0
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "spec": "docs/specs/feature-branch-campus-suppression.md",
        "source_parquet_glob": PARQUET_GLOB,
        "detection_threshold_unitids": DETECTION_THRESHOLD,
        "inheritance_threshold_ratio": INHERITANCE_THRESHOLD,
        "low_overlap_threshold_cips": LOW_OVERLAP_THRESHOLD,
        "summary": {
            "candidate_families": len(families),
            "families_with_suppression": families_with_suppression,
            "total_branches_recommended": total_suppressed,
        },
        "families": families,
    }


def main() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    output = detect()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = LOGS_DIR / f"branch_campus_detection_{timestamp}.json"
    with out_path.open("w") as f:
        json.dump(output, f, indent=2)

    s = output["summary"]
    print(f"candidate_families:           {s['candidate_families']}")
    print(f"families_with_suppression:    {s['families_with_suppression']}")
    print(f"total_branches_recommended:   {s['total_branches_recommended']}")
    print(f"output:                       {out_path}")
    print(
        "Review the output and translate the approved subset to "
        "backend/app/config/branch_campuses.py."
    )


if __name__ == "__main__":
    main()
