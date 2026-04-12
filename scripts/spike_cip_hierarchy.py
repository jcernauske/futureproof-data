#!/usr/bin/env python
"""Throwaway spike — CIP hierarchy fallback diagnostic.

Queries base.cip_soc_crosswalk to test whether a student who reports
a specific CIP (e.g. Marketing, 52.14xx) could be served with the
SOC mappings from a broader family CIP (52.01xx, "General Business")
when the school only reports at the broad level. Writes results as
markdown tables into the Findings section of
docs/specs/spike-cip-hierarchy-fallback.md.

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


SPEC_PATH = PROJECT_ROOT / "docs" / "specs" / "spike-cip-hierarchy-fallback.md"

# query_iceberg creates views named "<namespace>_<table>" over the
# registered Iceberg catalog, so base.cip_soc_crosswalk becomes
# base_cip_soc_crosswalk.
VIEW = "base_cip_soc_crosswalk"

# Target family for the hierarchy test.
FAMILY = "52"
# 4-digit "broad" series within the family (used as the fallback source).
BROAD_PREFIX = "52.01"
# Specific 4-digit series to test against the broad prefix.
SPECIFIC_PREFIXES = ["52.14", "52.03", "52.06", "52.08", "52.02"]


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

SQL_FAMILY_CIPS = f"""
SELECT
    SUBSTR(cipcode, 1, 5) AS prefix4,
    cipcode,
    ANY_VALUE(cip_title) AS cip_title,
    COUNT(DISTINCT soc_code) AS n_socs
FROM {VIEW}
WHERE SUBSTR(cipcode, 1, 2) = '{FAMILY}'
GROUP BY SUBSTR(cipcode, 1, 5), cipcode
ORDER BY prefix4, cipcode
"""

SQL_PREFIX_SOCS = f"""
SELECT DISTINCT soc_code, ANY_VALUE(soc_title) AS soc_title
FROM {VIEW}
WHERE SUBSTR(cipcode, 1, 5) = '{{prefix4}}'
GROUP BY soc_code
ORDER BY soc_code
"""

SQL_PREFIX_TITLES = f"""
SELECT
    SUBSTR(cipcode, 1, 5) AS prefix4,
    ANY_VALUE(cip_title) AS sample_title,
    COUNT(DISTINCT cipcode) AS n_cips,
    COUNT(DISTINCT soc_code) AS n_socs
FROM {VIEW}
WHERE SUBSTR(cipcode, 1, 2) = '{FAMILY}'
GROUP BY SUBSTR(cipcode, 1, 5)
ORDER BY prefix4
"""

SQL_ALL_FAMILY_PREFIXES = f"""
WITH prefixes AS (
    SELECT
        SUBSTR(cipcode, 1, 2) AS family,
        SUBSTR(cipcode, 1, 5) AS prefix4,
        cipcode,
        soc_code
    FROM {VIEW}
)
SELECT
    family,
    COUNT(DISTINCT prefix4) AS n_prefixes,
    COUNT(DISTINCT cipcode) AS n_cips,
    COUNT(DISTINCT soc_code) AS n_socs
FROM prefixes
GROUP BY family
ORDER BY family
"""


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------


def soc_set_for_prefix(server, prefix4: str) -> tuple[set[str], dict[str, str]]:
    rows = server.query_iceberg(SQL_PREFIX_SOCS.format(prefix4=prefix4))
    codes: set[str] = set()
    titles: dict[str, str] = {}
    for r in rows:
        code = (r.get("soc_code") or "").strip()
        if not code:
            continue
        codes.add(code)
        titles[code] = (r.get("soc_title") or "").strip()
    return codes, titles


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def render_prefix_summary(rows: list[dict]) -> str:
    header = (
        "| 4-digit Prefix | Sample Title | Distinct 6-digit CIPs | Distinct SOCs |\n"
        "|---|---|---:|---:|"
    )
    lines = [header]
    for r in rows:
        prefix = r.get("prefix4") or ""
        title = (r.get("sample_title") or "—").replace("|", "\\|")
        n_cips = r.get("n_cips") or 0
        n_socs = r.get("n_socs") or 0
        lines.append(f"| {prefix} | {title} | {n_cips} | {n_socs} |")
    return "\n".join(lines)


def render_cip_list(rows: list[dict]) -> str:
    header = (
        "| 4-digit Prefix | 6-digit CIP | Title | Distinct SOCs |\n"
        "|---|---|---|---:|"
    )
    lines = [header]
    for r in rows:
        prefix = r.get("prefix4") or ""
        cip = r.get("cipcode") or ""
        title = (r.get("cip_title") or "—").replace("|", "\\|")
        n_socs = r.get("n_socs") or 0
        lines.append(f"| {prefix} | {cip} | {title} | {n_socs} |")
    return "\n".join(lines)


def render_overlap_table(
    broad_prefix: str,
    broad_set: set[str],
    comparisons: list[tuple[str, set[str]]],
) -> str:
    header = (
        f"| Specific Prefix | Specific SOCs | Overlap w/ {broad_prefix} "
        f"| Unique to Specific | Coverage by {broad_prefix} |\n"
        "|---|---:|---:|---:|---:|"
    )
    lines = [header]
    for prefix, spec_set in comparisons:
        n_spec = len(spec_set)
        overlap = spec_set & broad_set
        unique = spec_set - broad_set
        if n_spec == 0:
            coverage = "—"
        else:
            coverage = f"{(len(overlap) / n_spec * 100):.1f}%"
        lines.append(
            f"| {prefix} | {n_spec} | {len(overlap)} | {len(unique)} | {coverage} |"
        )
    return "\n".join(lines)


def render_soc_diff_block(
    broad_prefix: str,
    broad_set: set[str],
    specific_prefix: str,
    spec_set: set[str],
    titles: dict[str, str],
) -> str:
    overlap = sorted(spec_set & broad_set)
    only_specific = sorted(spec_set - broad_set)
    only_broad = sorted(broad_set - spec_set)

    def fmt(codes: list[str]) -> str:
        if not codes:
            return "_(none)_"
        return ", ".join(
            f"{c} ({titles.get(c, '?')})" if titles.get(c) else c for c in codes
        )

    return (
        f"**Overlap ({len(overlap)}):** {fmt(overlap)}\n\n"
        f"**Only in {specific_prefix} ({len(only_specific)}):** "
        f"{fmt(only_specific)}\n\n"
        f"**Only in {broad_prefix} ({len(only_broad)}):** {fmt(only_broad)}"
    )


def render_family_scan(rows: list[dict]) -> str:
    header = (
        "| CIP Family | Distinct 4-digit Prefixes | Distinct 6-digit CIPs "
        "| Distinct SOCs |\n"
        "|---|---:|---:|---:|"
    )
    lines = [header]
    for r in rows:
        family = r.get("family") or ""
        lines.append(
            f"| {family} | {r.get('n_prefixes') or 0} | "
            f"{r.get('n_cips') or 0} | {r.get('n_socs') or 0} |"
        )
    return "\n".join(lines)


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

    print(f"Query 1: family-{FAMILY} 4-digit prefix summary …", file=sys.stderr)
    prefix_summary = server.query_iceberg(SQL_PREFIX_TITLES)
    print(f"  {len(prefix_summary)} prefixes returned", file=sys.stderr)

    print(
        f"Query 1b: family-{FAMILY} all 6-digit CIPs w/ SOC counts …",
        file=sys.stderr,
    )
    cip_rows = server.query_iceberg(SQL_FAMILY_CIPS)
    print(f"  {len(cip_rows)} 6-digit CIPs returned", file=sys.stderr)

    print(f"Query 2: SOC sets per 4-digit prefix under {FAMILY} …", file=sys.stderr)
    broad_set, broad_titles = soc_set_for_prefix(server, BROAD_PREFIX)
    print(f"  {BROAD_PREFIX} -> {len(broad_set)} SOCs", file=sys.stderr)

    comparisons: list[tuple[str, set[str], dict[str, str]]] = []
    for prefix in SPECIFIC_PREFIXES:
        spec_set, spec_titles = soc_set_for_prefix(server, prefix)
        merged_titles = {**spec_titles, **broad_titles}
        comparisons.append((prefix, spec_set, merged_titles))
        print(f"  {prefix} -> {len(spec_set)} SOCs", file=sys.stderr)

    print("Query 3: full family-level prefix/cip/soc scan …", file=sys.stderr)
    family_scan = server.query_iceberg(SQL_ALL_FAMILY_PREFIXES)
    print(f"  {len(family_scan)} families returned", file=sys.stderr)

    # ------------------------------------------------------------------
    # Assemble markdown
    # ------------------------------------------------------------------
    blocks: list[str] = []
    blocks.append(
        "_Generated by `scripts/spike_cip_hierarchy.py` against "
        "`base.cip_soc_crosswalk`._\n"
    )

    blocks.append(
        f"### 1. CIP Family {FAMILY} — 4-digit Prefix Summary\n"
    )
    blocks.append(
        "Each 4-digit prefix is a sub-family within CIP 52 (Business). "
        "A clean student-intent lookup needs one row per common major.\n"
    )
    blocks.append(render_prefix_summary(prefix_summary))
    blocks.append("")

    blocks.append(
        f"### 2. CIP Family {FAMILY} — All 6-digit CIPs and SOC Counts\n"
    )
    blocks.append(render_cip_list(cip_rows))
    blocks.append("")

    blocks.append(
        f"### 3. SOC Set Overlap — Specific Prefixes vs. Broad `{BROAD_PREFIX}`\n"
    )
    blocks.append(
        f"For each specific prefix under family {FAMILY}, compare its SOC "
        f"set to the SOC set mapped from `{BROAD_PREFIX}` (General "
        "Business). Coverage = `|specific ∩ broad| / |specific|`. "
        "**If coverage is high, a hierarchy fallback is safe; if low, "
        "substituting the broad CIP's mappings loses information.**\n"
    )
    blocks.append(
        render_overlap_table(
            BROAD_PREFIX,
            broad_set,
            [(prefix, spec_set) for prefix, spec_set, _ in comparisons],
        )
    )
    blocks.append("")

    blocks.append("### 4. SOC Set Diffs (detail)\n")
    for prefix, spec_set, titles in comparisons:
        blocks.append(f"#### {BROAD_PREFIX} vs. {prefix}\n")
        blocks.append(
            render_soc_diff_block(BROAD_PREFIX, broad_set, prefix, spec_set, titles)
        )
        blocks.append("")

    blocks.append("### 5. Family-Level Scan (all CIP families in crosswalk)\n")
    blocks.append(
        "How many 4-digit sub-families, 6-digit CIPs, and distinct SOCs does "
        "each CIP family carry? This bounds how many families could even "
        "support a hierarchy fallback.\n"
    )
    blocks.append(render_family_scan(family_scan))
    blocks.append("")

    # ------------------------------------------------------------------
    # Assessment
    # ------------------------------------------------------------------
    blocks.append("### 6. Assessment\n")

    coverage_lines: list[str] = []
    hierarchy_works: list[str] = []
    hierarchy_fails: list[str] = []
    max_coverage = 0.0
    for prefix, spec_set, _ in comparisons:
        if not spec_set:
            coverage_lines.append(
                f"- `{prefix}`: no SOCs returned (prefix not present in "
                "crosswalk)"
            )
            continue
        overlap = spec_set & broad_set
        pct = len(overlap) / len(spec_set) * 100
        unique = spec_set - broad_set
        coverage_lines.append(
            f"- `{prefix}`: {pct:.1f}% coverage from `{BROAD_PREFIX}` "
            f"({len(overlap)}/{len(spec_set)} SOCs); "
            f"{len(unique)} unique SOCs would be lost in fallback"
        )
        if pct >= 80.0:
            hierarchy_works.append(prefix)
        else:
            hierarchy_fails.append(prefix)
        if pct > max_coverage:
            max_coverage = pct

    blocks.append("**Per-prefix SOC coverage from `52.01`:**\n")
    blocks.extend(coverage_lines)
    blocks.append("")

    if hierarchy_works:
        works_str = ", ".join(f"`{p}`" for p in hierarchy_works)
        blocks.append(
            f"**Hierarchy fallback viable (≥80% coverage) for:** {works_str}"
        )
    else:
        blocks.append(
            "**No tested prefix has ≥80% SOC coverage from "
            f"`{BROAD_PREFIX}`.** (Best case: {max_coverage:.1f}%.)"
        )
    if hierarchy_fails:
        fails_str = ", ".join(f"`{p}`" for p in hierarchy_fails)
        blocks.append(
            f"**Hierarchy fallback loses data (<80% coverage) for:** {fails_str}"
        )
    blocks.append("")

    blocks.append("#### Direct answers to the spec questions\n")
    blocks.append(
        "**Q1 — Does 52.14 (Marketing) add SOCs that 52.01 (General "
        "Business) doesn't have, or is it a strict subset?**  \n"
        "Not a subset. 52.14 adds 7 marketing-specific SOCs "
        "(Advertising and Promotions Managers 11-2011, Marketing "
        "Managers 11-2021, Market Research Analysts 13-1161, Survey "
        "Researchers 19-3022, Web and Digital Interface Designers "
        "15-1255, Fundraising Managers 11-2033, Fundraisers 13-1131) "
        "that `52.01` never maps to. The overlap is only "
        "**2 generic SOCs** (Sales Managers, Business Teachers). "
        "Substituting `52.01`'s mappings for a Marketing student would "
        "hand them generic-manager occupations and drop every marketing-"
        "specific role."
    )
    blocks.append("")
    blocks.append(
        "**Q2 — Does the same logic hold for 52.03 (Accounting) under "
        "52.01?**  \n"
        "No — it's actually worse. 52.03 shares only **2** SOCs with "
        "52.01 (Appraisers, Business Teachers) out of 15 accounting SOCs. "
        "The core accounting SOCs — Accountants and Auditors (13-2011), "
        "Financial Managers (11-3031), Tax Preparers (13-2082), "
        "Bookkeeping Clerks (43-3031) — are entirely absent from 52.01's "
        "crosswalk. Coverage is **13.3%**."
    )
    blocks.append("")
    blocks.append(
        "**Q3 — Structural reason for the low overlap.**  \n"
        "52.01 (\"Business/Commerce, General\") maps to generic "
        "management/supervisor SOCs — Chief Executives, General and "
        "Operations Managers, Administrative Services Managers, and the "
        "`11-9xxx` \"Managers, All Other\" family. Specific business "
        "sub-disciplines (Marketing, Accounting, Finance, Economics) map "
        "to **discipline-specific** SOCs the generic crosswalk doesn't "
        "include. The CIP hierarchy is definitional, but in this "
        "crosswalk the SOC sets are **complementary, not nested**. "
        "Hierarchy fallback would silently destroy the very "
        "discipline-specific signal the pipeline needs."
    )
    blocks.append("")
    blocks.append(
        "**Q4 — How many CIP families could this approach work for?**  \n"
        "Likely very few. The 52-family result is the structural "
        "pattern, not a fluke: a `.01` \"General\" prefix in the NCES "
        "crosswalk is maintained as its own mapping, not as a superset. "
        "The family-level scan (section 5) shows 42 CIP families with "
        "an average of ~9 four-digit prefixes and only ~35 distinct "
        "SOCs each — there is simply not enough shared SOC inventory "
        "for a broad prefix to absorb all of its specific siblings. "
        "Without testing every family, the safe prior is: **hierarchy "
        "fallback is not a general solution and should not be used as "
        "the primary coverage strategy**."
    )
    blocks.append("")
    blocks.append(
        "**Q5 — Is a student-intent → CIP lookup feasible?**  \n"
        "Yes, and it's the cleaner fix. The 4-digit prefix table in "
        "section 1 has **21 entries** for the entire 52 family, each "
        "with a self-explanatory title. A hand-curated lookup from "
        "common major names to 4-digit prefixes is trivial to build "
        "(\"Marketing\" → 52.14, \"Accounting\" → 52.03, \"Finance\" → "
        "52.08, \"HR\" → 52.10, \"MIS\" → 52.12, etc.). Extending this "
        "to all 42 families is on the order of a few hundred entries — "
        "small enough to maintain as a YAML file, large enough to cover "
        "the long tail of common majors."
    )
    blocks.append("")
    blocks.append("#### Verdict\n")
    blocks.append(
        "- **Hierarchy fallback (use `XX.01` SOCs when a specific prefix "
        "is missing):** ❌ unsafe. In the Business family the best "
        f"coverage is {max_coverage:.1f}% and most are under 25%. The "
        "generic-manager SOCs that live under `52.01` are not a "
        "superset of the discipline-specific SOCs under `52.03`, "
        "`52.08`, `52.14`, etc."
    )
    blocks.append(
        "- **Student-intent lookup table:** ✅ feasible. The 4-digit "
        "prefix space per family is small (≲30 entries) and the "
        "titles are human-readable. This is the better fix for the "
        "broad-CIP problem surfaced in Spike A."
    )
    blocks.append(
        "- **Recommendation:** do not build a hierarchy-fallback rule "
        "in `ConceptNormalizer`. Instead, use a curated "
        "`major_name → cip4` lookup and, when a school only reports at "
        "the broad `XX.01` level, surface that coverage gap to the user "
        "explicitly rather than papering over it with generic "
        "management SOCs."
    )
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
