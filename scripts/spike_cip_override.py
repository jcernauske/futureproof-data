#!/usr/bin/env python
"""Throwaway spike — CIP override-table feasibility & scale diagnostic.

Answers the four questions in docs/specs/spike-cip-override-table.md:
  1. How many schools report CIP 52.01 (Business/Commerce General)? How
     many also have specific 52.xx breakouts? How many ONLY 52.01?
  2. Repeat for other "general" 4-digit CIPs (24.01, 26.01, 42.01, 23.01).
  3. Top-20 "ONLY 52.01" schools by completions, plus the candidate 52.xx
     sibling CIPs an override table could map them to.
  4. Scale estimate — rows per family and for all general CIPs combined.

Writes the results as markdown tables into the Findings section of
`docs/specs/spike-cip-override-table.md`. Read-only against Iceberg;
does NOT touch production code or data.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from mcp_server.futureproof_server import FutureProofMCPServer  # noqa: E402

SPEC_PATH = PROJECT_ROOT / "docs" / "specs" / "spike-cip-override-table.md"

# query_iceberg creates views named "<namespace>_<table>".
CO_VIEW = "consumable_career_outcomes"
XW_VIEW = "base_cip_soc_crosswalk"

# Consumable career_outcomes stores cipcode at the 4-digit level
# (e.g. "52.01", "52.02"). The "general" 4-digit code within each
# 2-digit family is XX.01.
GENERAL_CIPS: list[tuple[str, str]] = [
    ("52.01", "Business/Commerce, General"),
    ("24.01", "Liberal Arts & Sciences, General Studies"),
    ("26.01", "Biology, General"),
    ("42.01", "Psychology, General"),
    ("23.01", "English Language & Literature, General"),
]


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

SQL_GENERAL_BREAKDOWN = f"""
WITH fam AS (
    SELECT
        unitid,
        cipcode,
        SUBSTR(cipcode, 1, 2) AS family_2dig
    FROM {CO_VIEW}
    WHERE cipcode IS NOT NULL AND LENGTH(cipcode) = 5
      AND SUBSTR(cipcode, 1, 2) = '{{family}}'
),
by_school AS (
    SELECT
        unitid,
        MAX(CASE WHEN cipcode = '{{general_cip}}' THEN 1 ELSE 0 END)
            AS has_general,
        MAX(CASE WHEN cipcode LIKE '{{family}}.%'
                  AND cipcode <> '{{general_cip}}'
                 THEN 1 ELSE 0 END) AS has_specific
    FROM fam
    GROUP BY unitid
)
SELECT
    SUM(has_general) AS schools_with_general,
    SUM(CASE WHEN has_general = 1 AND has_specific = 1 THEN 1 ELSE 0 END)
        AS general_plus_specific,
    SUM(CASE WHEN has_general = 1 AND has_specific = 0 THEN 1 ELSE 0 END)
        AS only_general,
    SUM(CASE WHEN has_general = 0 AND has_specific = 1 THEN 1 ELSE 0 END)
        AS only_specific,
    COUNT(*) AS total_schools_in_family
FROM by_school
"""

SQL_TOP20_ONLY_GENERAL = f"""
WITH fam AS (
    SELECT
        unitid,
        institution_name,
        cipcode,
        completions_count
    FROM {CO_VIEW}
    WHERE cipcode IS NOT NULL AND LENGTH(cipcode) = 5
      AND SUBSTR(cipcode, 1, 2) = '{{family}}'
),
by_school AS (
    SELECT
        unitid,
        ANY_VALUE(institution_name) AS institution_name,
        MAX(CASE WHEN cipcode = '{{general_cip}}' THEN 1 ELSE 0 END)
            AS has_general,
        MAX(CASE WHEN cipcode <> '{{general_cip}}' THEN 1 ELSE 0 END)
            AS has_specific,
        SUM(CASE WHEN cipcode = '{{general_cip}}'
                 THEN COALESCE(completions_count, 0) ELSE 0 END)
            AS general_completions
    FROM fam
    GROUP BY unitid
)
SELECT
    unitid,
    institution_name,
    general_completions
FROM by_school
WHERE has_general = 1 AND has_specific = 0
ORDER BY general_completions DESC NULLS LAST, institution_name ASC
LIMIT 20
"""

# From the crosswalk, enumerate the distinct 4-digit sibling CIPs that
# exist inside a given 2-digit family (the "override candidates").
SQL_FAMILY_SIBLINGS = f"""
SELECT DISTINCT
    SUBSTR(cipcode, 1, 5) AS cip_4dig
FROM {XW_VIEW}
WHERE SUBSTR(cipcode, 1, 2) = '{{family}}'
ORDER BY cip_4dig
"""

# Count: how many distinct 6-digit CIPs in the crosswalk belong to the
# 2-digit family (used for a wide-override scale estimate).
SQL_FAMILY_SIXDIGIT_COUNT = f"""
SELECT COUNT(DISTINCT cipcode) AS n_6dig
FROM {XW_VIEW}
WHERE SUBSTR(cipcode, 1, 2) = '{{family}}'
"""

# Scale across ALL families: for every 2-digit family that has an XX.01
# general code in the consumable data, how many schools report ONLY the
# general code (no sibling 4-digit breakouts)?
SQL_ALL_FAMILIES_ONLY_GENERAL = f"""
WITH fam AS (
    SELECT
        unitid,
        cipcode,
        SUBSTR(cipcode, 1, 2) AS family_2dig
    FROM {CO_VIEW}
    WHERE cipcode IS NOT NULL AND LENGTH(cipcode) = 5
),
by_school_family AS (
    SELECT
        unitid,
        family_2dig,
        MAX(CASE WHEN cipcode = family_2dig || '.01' THEN 1 ELSE 0 END)
            AS has_general,
        MAX(CASE WHEN cipcode <> family_2dig || '.01' THEN 1 ELSE 0 END)
            AS has_specific
    FROM fam
    GROUP BY unitid, family_2dig
)
SELECT
    family_2dig,
    SUM(has_general) AS schools_with_general,
    SUM(CASE WHEN has_general = 1 AND has_specific = 0 THEN 1 ELSE 0 END)
        AS only_general
FROM by_school_family
GROUP BY family_2dig
ORDER BY only_general DESC, family_2dig ASC
"""


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def render_q1q2_table(rows: list[dict]) -> str:
    header = (
        "| CIP | Label | Schools w/ General | General + Specific "
        "| ONLY General | ONLY Specific | Total Schools in Family |\n"
        "|---|---|---:|---:|---:|---:|---:|"
    )
    lines = [header]
    for r in rows:
        lines.append(
            "| {cip} | {label} | {swg} | {gps} | {og} | {os} | {tot} |".format(
                cip=r["cip"],
                label=_md_escape(r["label"]),
                swg=r["schools_with_general"],
                gps=r["general_plus_specific"],
                og=r["only_general"],
                os=r["only_specific"],
                tot=r["total_schools_in_family"],
            )
        )
    return "\n".join(lines)


def render_top20_table(rows: list[dict]) -> str:
    header = (
        "| Rank | UNITID | Institution | Completions (52.01) |\n"
        "|---:|---:|---|---:|"
    )
    lines = [header]
    for i, r in enumerate(rows, start=1):
        name = _md_escape(str(r.get("institution_name") or "—"))
        comp = r.get("general_completions")
        comp_str = f"{int(comp):,}" if comp is not None else "—"
        lines.append(
            f"| {i} | {r.get('unitid') or '—'} | {name} | {comp_str} |"
        )
    return "\n".join(lines)


def render_sibling_table(siblings: list[str]) -> str:
    if not siblings:
        return "_(no sibling 4-digit CIPs found in crosswalk)_"
    header = "| 4-digit CIP (candidate) |\n|---|"
    lines = [header]
    for s in siblings:
        lines.append(f"| {s} |")
    return "\n".join(lines)


def render_scale_table(
    per_family: dict[str, dict],
    six_dig_counts: dict[str, int],
    all_rows: list[dict],
) -> str:
    header = (
        "| CIP Family | Label | Schools ONLY General "
        "| Sibling 4-digit CIPs | Narrow Override Rows | "
        "Wide Override Rows (× 4-dig siblings) |\n"
        "|---|---|---:|---:|---:|---:|"
    )
    lines = [header]
    total_narrow = 0
    total_wide = 0
    for cip, label in GENERAL_CIPS:
        family = cip.split(".")[0]
        pf = per_family.get(cip, {})
        only_general = pf.get("only_general", 0) or 0
        n_siblings = len(pf.get("siblings", []))
        narrow = only_general
        wide = only_general * n_siblings
        total_narrow += narrow
        total_wide += wide
        lines.append(
            f"| {cip} | {_md_escape(label)} | {only_general} "
            f"| {n_siblings} | {narrow} | {wide} |"
        )
    lines.append(
        f"| **Subtotal (5 families)** | — | **{sum((per_family[c].get('only_general') or 0) for c, _ in GENERAL_CIPS)}** "
        f"| — | **{total_narrow}** | **{total_wide}** |"
    )

    # All-families roll-up (XX.01 general across every 2-digit family)
    all_total_only = sum(int(r.get("only_general") or 0) for r in all_rows)
    all_total_any = sum(int(r.get("schools_with_general") or 0) for r in all_rows)
    lines.append(
        f"| **ALL families (every XX.01)** | — | **{all_total_only}** "
        f"| — | **{all_total_only}** | _varies_ |"
    )
    return "\n".join(lines), all_total_only, all_total_any


# ---------------------------------------------------------------------------
# Spec-file update
# ---------------------------------------------------------------------------


def update_findings(markdown_block: str) -> None:
    text = SPEC_PATH.read_text()
    pattern = re.compile(r"(## Findings\s*\n).*?(\n---\n)", re.DOTALL)
    replacement = r"\1\n" + markdown_block + r"\n\2"
    new_text, n = pattern.subn(replacement, text, count=1)
    if n == 0:
        raise RuntimeError(
            "Could not locate Findings section followed by '---' divider in "
            f"{SPEC_PATH}; refusing to write."
        )
    SPEC_PATH.write_text(new_text)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run() -> int:
    server = FutureProofMCPServer(
        warehouse_path=str(PROJECT_ROOT / "data" / "warehouse"),
        catalog_path=str(PROJECT_ROOT / "data" / "catalog" / "catalog.db"),
        server_name="futureproof-spike-override",
    )

    per_family: dict[str, dict] = {}
    q1q2_rows: list[dict] = []

    # --- Q1 + Q2: general-CIP breakdown across the five target families ----
    for cip, label in GENERAL_CIPS:
        family = cip.split(".")[0]
        print(f"Breakdown for {cip} ({label}) …", file=sys.stderr)
        sql = SQL_GENERAL_BREAKDOWN.format(family=family, general_cip=cip)
        result = server.query_iceberg(sql)
        row = result[0] if result else {}
        entry = {
            "cip": cip,
            "label": label,
            "schools_with_general": int(row.get("schools_with_general") or 0),
            "general_plus_specific": int(row.get("general_plus_specific") or 0),
            "only_general": int(row.get("only_general") or 0),
            "only_specific": int(row.get("only_specific") or 0),
            "total_schools_in_family": int(row.get("total_schools_in_family") or 0),
        }
        q1q2_rows.append(entry)
        per_family[cip] = dict(entry)

        # Sibling 4-digit CIPs from crosswalk
        sib_rows = server.query_iceberg(SQL_FAMILY_SIBLINGS.format(family=family))
        siblings = sorted(
            str(r.get("cip_4dig"))
            for r in sib_rows
            if r.get("cip_4dig")
        )
        per_family[cip]["siblings"] = siblings

        # 6-digit count per family (just informational)
        six = server.query_iceberg(
            SQL_FAMILY_SIXDIGIT_COUNT.format(family=family)
        )
        per_family[cip]["n_6dig"] = int((six[0].get("n_6dig") if six else 0) or 0)

    # --- Q3: top-20 ONLY-52.01 schools + candidate siblings ----------------
    print("Top-20 ONLY-52.01 schools …", file=sys.stderr)
    top20 = server.query_iceberg(
        SQL_TOP20_ONLY_GENERAL.format(family="52", general_cip="52.01")
    )

    # --- Q4: scale across all families ------------------------------------
    print("All-family scale query …", file=sys.stderr)
    all_family_rows = server.query_iceberg(SQL_ALL_FAMILIES_ONLY_GENERAL)

    # ----------------------------------------------------------------------
    # Assemble markdown
    # ----------------------------------------------------------------------
    blocks: list[str] = []
    blocks.append(
        "_Generated by `scripts/spike_cip_override.py` against "
        "`consumable.career_outcomes` and `base.cip_soc_crosswalk`. "
        "NOTE: `consumable.career_outcomes` stores cipcode at the 4-digit "
        "level (e.g. `52.01`), so \"general\" throughout this spike means "
        "the 4-digit `XX.01` code; \"specific\" means any other `XX.yy` "
        "sibling in the same 2-digit family._\n"
    )

    blocks.append("### 1 & 2. General-CIP breakdown (target families)\n")
    blocks.append(
        "For each \"general\" 4-digit CIP, counts DISTINCT schools that, "
        "within the same 2-digit family, report: the general code, the "
        "general code **plus** at least one sibling, **only** the general "
        "code, or **only** sibling 4-digit codes.\n"
    )
    blocks.append(render_q1q2_table(q1q2_rows))
    blocks.append("")

    blocks.append("### 3. Top-20 schools reporting ONLY CIP 52.01\n")
    blocks.append(
        "Ranked by completions at 52.01 (no direct enrollment column in "
        "`consumable.career_outcomes`; `completions_count` is the closest "
        "proxy). These are the schools an override table for family 52 "
        "would need to fill in.\n"
    )
    blocks.append(render_top20_table(top20))
    blocks.append("")

    blocks.append(
        "#### Candidate override targets — 4-digit siblings in CIP family 52\n"
    )
    blocks.append(
        "From `base.cip_soc_crosswalk`, rolled up to 4-digit. These are the "
        "sibling CIPs an override table for family 52 could map a "
        "\"ONLY 52.01\" school to.\n"
    )
    blocks.append(render_sibling_table(per_family["52.01"]["siblings"]))
    blocks.append("")

    blocks.append("### 4. Scale estimate\n")
    blocks.append(
        "Two sizing models:\n\n"
        "- **Narrow override** — 1 row per school needing an override "
        "(i.e. `unitid` with a single proposed replacement 4-digit CIP).\n"
        "- **Wide override** — 1 row per `(unitid, candidate 4-digit CIP)` "
        "pair, i.e. the full cross-product against the family's sibling "
        "CIPs. This is the upper bound if the override table holds "
        "mix-weighted allocations rather than a single hard replacement.\n"
    )
    scale_md, all_only, all_any = render_scale_table(
        per_family, {}, all_family_rows
    )
    blocks.append(scale_md)
    blocks.append("")

    # Verdict
    pick = "5,000-row" if all_only > 2000 else ("500-row" if all_only > 200 else "50-row")
    blocks.append("### Verdict\n")
    blocks.append(
        f"Across **all** 2-digit families with an `XX.01` general code, "
        f"**{all_only:,}** distinct (school × family) combinations report "
        f"ONLY the general 4-digit code and therefore would need an "
        f"override row in the narrow model. That puts this squarely in "
        f"**{pick} territory** — a narrow override is a hand-maintainable "
        f"table; a wide cross-product override balloons quickly and is "
        f"likely better computed on-the-fly.\n"
    )

    markdown = "\n".join(blocks)

    update_findings(markdown)
    print(f"\nWrote findings to {SPEC_PATH}")
    return 0


if __name__ == "__main__":
    import traceback

    try:
        sys.exit(run())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
