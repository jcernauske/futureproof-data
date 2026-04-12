#!/usr/bin/env python
"""Throwaway spike — CIP family disaggregation diagnostic.

Queries consumable.career_outcomes to measure how many schools report ONLY
at the broad XX.01 ("general") level vs. at more specific 4-digit series,
per 2-digit CIP family. Writes results as markdown tables into the
Findings section of docs/specs/spike-broad-cip-prevalence.md.

Read-only. Does NOT touch production code or data.
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


SPEC_PATH = PROJECT_ROOT / "docs" / "specs" / "spike-broad-cip-prevalence.md"

# query_iceberg creates views named "<namespace>_<table>" over the
# registered Iceberg catalog, so consumable.career_outcomes becomes
# consumable_career_outcomes.
VIEW = "consumable_career_outcomes"


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

SQL_FAMILY_BREAKDOWN = f"""
WITH base AS (
    SELECT
        unitid,
        institution_name,
        cipcode,
        cip_family_name,
        SUBSTR(cipcode, 1, 2) AS family,
        CASE
            WHEN SUBSTR(cipcode, 1, 5) = SUBSTR(cipcode, 1, 2) || '.01'
            THEN 1 ELSE 0
        END AS is_broad
    FROM {VIEW}
    WHERE cipcode IS NOT NULL AND LENGTH(cipcode) >= 5
),
family_names AS (
    SELECT family, ANY_VALUE(cip_family_name) AS family_name
    FROM base
    GROUP BY family
),
by_school_family AS (
    SELECT
        unitid,
        family,
        MAX(is_broad) AS has_broad,
        MAX(1 - is_broad) AS has_specific
    FROM base
    GROUP BY unitid, family
)
SELECT
    b.family,
    f.family_name,
    SUM(CASE WHEN b.has_broad = 1 AND b.has_specific = 0 THEN 1 ELSE 0 END) AS only_broad,
    SUM(CASE WHEN b.has_broad = 0 AND b.has_specific = 1 THEN 1 ELSE 0 END) AS only_specific,
    SUM(CASE WHEN b.has_broad = 1 AND b.has_specific = 1 THEN 1 ELSE 0 END) AS both,
    COUNT(*) AS total_schools
FROM by_school_family b
LEFT JOIN family_names f USING (family)
GROUP BY b.family, f.family_name
ORDER BY only_broad DESC, b.family ASC
"""

SQL_EXAMPLES_TEMPLATE = f"""
WITH base AS (
    SELECT
        unitid,
        institution_name,
        cipcode,
        SUBSTR(cipcode, 1, 2) AS family,
        CASE
            WHEN SUBSTR(cipcode, 1, 5) = SUBSTR(cipcode, 1, 2) || '.01'
            THEN 1 ELSE 0
        END AS is_broad
    FROM {VIEW}
    WHERE cipcode IS NOT NULL AND LENGTH(cipcode) >= 5
),
by_school_family AS (
    SELECT
        unitid,
        ANY_VALUE(institution_name) AS institution_name,
        family,
        MAX(is_broad) AS has_broad,
        MAX(1 - is_broad) AS has_specific
    FROM base
    GROUP BY unitid, family
)
SELECT DISTINCT institution_name
FROM by_school_family
WHERE family = '{{family}}' AND has_broad = 1 AND has_specific = 0
ORDER BY institution_name
LIMIT 5
"""

SQL_TOTAL_SHARE = f"""
SELECT
    SUM(CASE
        WHEN SUBSTR(cipcode, 1, 5) = SUBSTR(cipcode, 1, 2) || '.01'
        THEN 1 ELSE 0
    END) AS broad_rows,
    COUNT(*) AS total_rows
FROM {VIEW}
WHERE cipcode IS NOT NULL AND LENGTH(cipcode) >= 5
"""


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_family_table(rows: list[dict]) -> str:
    header = (
        "| CIP Family | Family Name | Schools: ONLY Broad (XX.01) "
        "| Schools: ONLY Specific | Schools: BOTH | Total Schools |\n"
        "|---|---|---:|---:|---:|---:|"
    )
    lines = [header]
    for r in rows:
        family = r.get("family") or ""
        name = (r.get("family_name") or "—").replace("|", "\\|")
        only_broad = r.get("only_broad") or 0
        only_specific = r.get("only_specific") or 0
        both = r.get("both") or 0
        total = r.get("total_schools") or 0
        lines.append(
            f"| {family} | {name} | {only_broad} | {only_specific} "
            f"| {both} | {total} |"
        )
    return "\n".join(lines)


def render_examples_table(
    top_rows: list[dict], examples: dict[str, list[str]]
) -> str:
    header = (
        "| Rank | CIP Family | Family Name | Schools ONLY Broad "
        "| Example Schools |\n"
        "|---:|---|---|---:|---|"
    )
    lines = [header]
    for i, r in enumerate(top_rows, start=1):
        family = r.get("family") or ""
        name = (r.get("family_name") or "—").replace("|", "\\|")
        only_broad = r.get("only_broad") or 0
        names = examples.get(family, [])
        ex_str = "; ".join(n.replace("|", "\\|") for n in names) if names else "—"
        lines.append(f"| {i} | {family} | {name} | {only_broad} | {ex_str} |")
    return "\n".join(lines)


def render_totals_block(broad_rows: int, total_rows: int) -> str:
    if total_rows == 0:
        pct_str = "—"
    else:
        pct_str = f"{(broad_rows / total_rows * 100):.2f}%"
    return (
        "| Metric | Value |\n"
        "|---|---:|\n"
        f"| Total school+program rows | {total_rows:,} |\n"
        f"| Rows at broad XX.01 level | {broad_rows:,} |\n"
        f"| **Broad XX.01 share of all rows** | **{pct_str}** |"
    )


# ---------------------------------------------------------------------------
# Spec-file update
# ---------------------------------------------------------------------------


def update_findings(markdown_block: str) -> None:
    text = SPEC_PATH.read_text()
    pattern = re.compile(
        r"(## Findings\s*\n).*?(\n---\n)",
        re.DOTALL,
    )
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
        server_name="futureproof-spike",
    )

    print("Running family-breakdown query …", file=sys.stderr)
    family_rows = server.query_iceberg(SQL_FAMILY_BREAKDOWN)
    print(f"  {len(family_rows)} CIP families returned", file=sys.stderr)

    top10 = family_rows[:10]
    examples: dict[str, list[str]] = {}
    for r in top10:
        family = r.get("family") or ""
        if not family:
            continue
        print(f"Fetching examples for family {family} …", file=sys.stderr)
        ex_rows = server.query_iceberg(SQL_EXAMPLES_TEMPLATE.format(family=family))
        examples[family] = [
            str(row.get("institution_name") or "").strip()
            for row in ex_rows
            if row.get("institution_name")
        ]

    print("Running totals query …", file=sys.stderr)
    total_rows_result = server.query_iceberg(SQL_TOTAL_SHARE)
    broad_rows = int(total_rows_result[0].get("broad_rows") or 0)
    total_rows = int(total_rows_result[0].get("total_rows") or 0)

    # ------------------------------------------------------------------
    # Assemble markdown
    # ------------------------------------------------------------------
    blocks: list[str] = []
    blocks.append(
        "_Generated by `scripts/spike_broad_cip.py` against "
        "`consumable.career_outcomes`._\n"
    )

    blocks.append("### 1. CIP Family Breakdown (ranked by ONLY-broad count)\n")
    blocks.append(
        "Each row counts DISTINCT schools that, within the given 2-digit CIP "
        "family, report **only** the broad XX.01 \"general\" series, **only** "
        "more-specific 4-digit series, or **both**.\n"
    )
    blocks.append(render_family_table(family_rows))
    blocks.append("")

    blocks.append(
        "### 2. Top 10 Worst Families — Example Schools Reporting ONLY Broad\n"
    )
    blocks.append(render_examples_table(top10, examples))
    blocks.append("")

    blocks.append("### 3. Overall Share of Broad XX.01 Rows\n")
    blocks.append(render_totals_block(broad_rows, total_rows))
    blocks.append("")

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
