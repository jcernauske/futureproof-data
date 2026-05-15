"""Markdown report generation for builds and comparisons.

Produces clean, counselor-friendly markdown that a student can print
and bring to a meeting with parents or an advisor. No RPG framing —
just the data and the model's analysis.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models.career import AppliedSkill, Build
from app.services import receipts
from app.services.career_tree import TreeNode, TreeStats, format_summary, render_tree
from app.services.mcp_client import project_root


def _receipt_block(receipt_lines: list[str], title: str = "Receipts") -> list[str]:
    block = [f"> **📋 {title}**"]
    for line in receipt_lines:
        block.append(f"> {line}")
    block.append("")
    return block


def _reports_dir() -> Path:
    d = project_root() / "reports"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "build"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _wage(value: float | None) -> str:
    return f"${int(value):,}" if isinstance(value, (int, float)) else "N/A"


def _stat(value: int | None) -> str:
    return str(value) if isinstance(value, int) else "—"


def _format_skill_deltas(skill: AppliedSkill) -> str:
    parts: list[str] = []
    for label, val in (
        ("ERN", skill.delta_ern),
        ("ROI", skill.delta_roi),
        ("RES", skill.delta_res),
        ("GRW", skill.delta_grw),
    ):
        if val:
            parts.append(f"{label} {val:+d}")
    if skill.delta_burnout_raw:
        parts.append(f"Burnout risk {skill.delta_burnout_raw:+d}")
    if skill.delta_ceiling_raw:
        parts.append(f"Ceiling {skill.delta_ceiling_raw:+d}")
    if skill.delta_loans_raw:
        parts.append(f"Loan burden {skill.delta_loans_raw:+d}")
    return ", ".join(parts) or "—"


# ---------------------------------------------------------------------------
# Build report
# ---------------------------------------------------------------------------


def generate_build_report(
    build: Build,
    *,
    tree: tuple[TreeNode, TreeStats] | None = None,
) -> Path:
    """Write a markdown report for a single build and return the path."""
    career = build.career
    stats = career.stats
    gauntlet = build.gauntlet

    lines: list[str] = []

    # --- Header ---
    lines.append("# FutureProof Build Report")
    lines.append("")
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append(f"| **School** | {career.institution_name} |")
    lines.append(f"| **Major** | {build.major_text} ({career.cipcode}) |")
    lines.append(
        f"| **Primary Career** | {career.occupation_title} "
        f"({career.soc_code}) |"
    )
    lines.append(f"| **Median Salary** | {_wage(career.median_annual_wage)} |")
    lines.append(
        f"| **Entry Education** | "
        f"{career.education_level_name or 'N/A'} |"
    )
    lines.append(
        f"| **Effort Level** | {build.effort.replace('_', ' ').title()} |"
    )
    lines.append(f"| **Loan Coverage** | {int(build.loan_pct * 100)}% |")
    lines.append(
        f"| **Generated** | "
        f"{datetime.now(timezone.utc).strftime('%B %d, %Y')} |"
    )
    lines.append("")

    # --- Stats ---
    lines.append("## Stats")
    lines.append("")
    lines.append("| Stat | Score | |")
    lines.append("|------|------:|---|")
    stat_labels = [
        ("Earning Power (ERN)", stats.ern),
        ("Return on Investment (ROI)", stats.roi),
        ("AI Resilience (RES)", stats.res),
        ("Growth Outlook (GRW)", stats.grw),
        ("Brand Gravity (AURA)", stats.aura),
    ]
    for label, val in stat_labels:
        score = _stat(val)
        bar = ""
        if isinstance(val, int):
            bar = "█" * val + "░" * (10 - val)
        lines.append(f"| {label} | {score}/10 | `{bar}` |")
    lines.append("")
    lines.extend(_receipt_block(
        receipts.stats_receipt(career, build.effort, build.loan_pct),
        title="Receipts: Stats",
    ))

    # --- The Take ---
    lines.append("## The Take")
    lines.append("")
    lines.append(build.guidance)
    lines.append("")

    # --- Boss Fight Results ---
    lines.append("## Boss Fight Results")
    lines.append("")
    lines.append(
        f"**Overall: {gauntlet.wins}W / {gauntlet.losses}L / "
        f"{gauntlet.draws}D** — {gauntlet.verdict}"
    )
    lines.append("")
    for fight in gauntlet.fights:
        result_tag = fight.result.upper()
        lines.append(f"### {fight.label} — {result_tag}")
        lines.append("")
        lines.append(f"*{fight.reason}*")
        lines.append("")
        lines.extend(_receipt_block(
            [receipts.fight_receipt(fight)],
            title="Receipt",
        ))
        if fight.narrative:
            lines.append(f"> {fight.narrative}")
            lines.append("")
        if fight.rerolled and fight.original_result:
            lines.append(
                f"**Rerolled:** {fight.original_result.upper()} → "
                f"{fight.result.upper()}"
            )
            crafted_for_this = [
                s
                for s in build.skills_crafted
                if fight.boss in s.targets
            ]
            if crafted_for_this:
                lines.append("")
                lines.append("Skills crafted for this fight:")
                lines.append("")
                for skill in crafted_for_this:
                    lines.append(
                        f"- **{skill.title}** "
                        f"({_format_skill_deltas(skill)}) — "
                        f"{skill.rationale}"
                    )
            lines.append("")

    # --- Skills Crafted ---
    if build.skills_crafted:
        lines.append("## Skills Crafted During Rerolls")
        lines.append("")
        lines.append("| Skill | Stat Impact | Rationale |")
        lines.append("|-------|-------------|-----------|")
        for skill in build.skills_crafted:
            lines.append(
                f"| {skill.title} | "
                f"{_format_skill_deltas(skill)} | "
                f"{skill.rationale} |"
            )
        lines.append("")

    # --- Career Branches ---
    if build.branches:
        lines.append("## Career Branches (Stage 3)")
        lines.append("")
        lines.append("| Branch | SOC | Stat Deltas | Unlock |")
        lines.append("|--------|-----|-------------|--------|")
        for branch in build.branches[:8]:
            deltas = ", ".join(
                f"{name} {delta:+d}"
                for name, delta in (
                    ("ERN", branch.delta_ern),
                    ("ROI", branch.delta_roi),
                    ("RES", branch.delta_res),
                    ("GRW", branch.delta_grw),
                    ("AURA", branch.delta_aura),
                )
                if isinstance(delta, int) and delta != 0
            ) or "—"
            lines.append(
                f"| {branch.to_title} | {branch.to_soc} | "
                f"{deltas} | {branch.unlock or '—'} |"
            )
        lines.append("")

    # --- Career Tree ---
    if tree:
        root_node, tree_stats = tree
        lines.append("## Career Tree (Experimental)")
        lines.append("")
        lines.append(
            "Multi-level career evolution tree built from O*NET pathway "
            "data. Each node shows stats (1–10 scale), boss fight results "
            "(W/L/D), and median salary."
        )
        lines.append("")
        lines.append("```")
        lines.append(render_tree(root_node))
        lines.append("```")
        lines.append("")
        lines.append(format_summary(tree_stats))
        lines.append("")

    # --- Skill Recommendations ---
    if build.skill_recs:
        lines.append("## Skill Recommendations")
        lines.append("")
        for rec in build.skill_recs:
            lines.append(
                f"- **{rec.title}** ({rec.stat_impact}) — "
                f"{rec.rationale}"
            )
        lines.append("")
        lines.extend(_receipt_block(
            receipts.skill_recs_receipt(career, gauntlet),
            title="Receipts: Skill Recommendations",
        ))

    # --- Disclaimers ---
    lines.append("---")
    lines.append("")
    lines.append("## Disclaimers")
    lines.append("")
    lines.append(
        "- Stats are AI-estimated scores on a 1–10 scale derived from "
        "federal data sources (College Scorecard, BLS, O*NET). They "
        "reflect program-level and occupation-level averages, not "
        "individual predictions."
    )
    lines.append(
        "- Boss fight results model structural career risks using "
        "published labor market data. They are not guarantees of "
        "outcomes."
    )
    lines.append(
        "- The Take and skill recommendations are AI-generated "
        "guidance. They should complement, not replace, conversations "
        "with school counselors, career advisors, and family."
    )
    lines.append(
        "- Salary figures are national medians from the Bureau of "
        "Labor Statistics. Actual earnings vary by region, employer, "
        "experience, and individual performance."
    )
    lines.append(
        "- This report is generated by FutureProof, powered by Gemma 4. "
        "Gemma is a trademark of Google LLC. "
        "Data as of 2024–2025 academic year."
    )
    lines.append("")

    # Write
    school_slug = _slug(build.school_name)
    major_slug = _slug(build.major_text)
    filename = f"{school_slug}_{major_slug}_{_ts()}.md"
    path = _reports_dir() / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Comparison report
# ---------------------------------------------------------------------------


def generate_comparison_report(
    comparison: dict[str, Any],
    full_builds: list[Build],
) -> Path:
    """Write a side-by-side comparison markdown report."""
    lines: list[str] = []
    build_labels = [b["label"] for b in comparison["builds"]]

    lines.append("# FutureProof Build Comparison")
    lines.append("")
    lines.append(
        f"*Generated {datetime.now(timezone.utc).strftime('%B %d, %Y')}*"
    )
    lines.append("")

    # --- Builds overview ---
    lines.append("## Builds Compared")
    lines.append("")
    lines.append("| | " + " | ".join(build_labels) + " |")
    lines.append("|---|" + "|".join(["---"] * len(build_labels)) + "|")

    career_row = "| **Career** | " + " | ".join(
        b["career"] for b in comparison["builds"]
    ) + " |"
    lines.append(career_row)

    if full_builds:
        salary_row = "| **Salary** | " + " | ".join(
            _wage(b.career.median_annual_wage) for b in full_builds
        ) + " |"
        lines.append(salary_row)
        effort_row = "| **Effort** | " + " | ".join(
            b.effort.replace("_", " ").title() for b in full_builds
        ) + " |"
        lines.append(effort_row)
        loan_row = "| **Loans** | " + " | ".join(
            f"{int(b.loan_pct * 100)}%" for b in full_builds
        ) + " |"
        lines.append(loan_row)
    lines.append("")

    # --- Stats comparison ---
    lines.append("## Stats Comparison")
    lines.append("")
    lines.append("| Stat | " + " | ".join(build_labels) + " |")
    lines.append("|------|" + "|".join(["------:"] * len(build_labels)) + "|")
    for row in comparison["stats"]:
        values = " | ".join(
            _stat(v) for v in row["values"]
        )
        lines.append(f"| **{row['label']}** | {values} |")
    lines.append("")

    # --- Boss comparison ---
    lines.append("## Boss Fight Comparison")
    lines.append("")
    lines.append("| Boss | " + " | ".join(build_labels) + " |")
    lines.append("|------|" + "|".join(["------"] * len(build_labels)) + "|")
    for row in comparison["bosses"]:
        values = " | ".join(row["values"])
        lines.append(f"| **{row['label']}** | {values} |")
    lines.append("")

    # --- Per-build branch previews ---
    if full_builds:
        lines.append("## Career Branch Previews")
        lines.append("")
        for build in full_builds:
            label = f"{build.school_name} — {build.major_text}"
            lines.append(f"### {label}")
            lines.append("")
            if build.branches:
                lines.append("| Branch | SOC | Unlock |")
                lines.append("|--------|-----|--------|")
                for branch in build.branches[:5]:
                    lines.append(
                        f"| {branch.to_title} | {branch.to_soc} | "
                        f"{branch.unlock or '—'} |"
                    )
            else:
                lines.append("*No branches available.*")
            lines.append("")

    # --- Disclaimers ---
    lines.append("---")
    lines.append("")
    lines.append(
        "*Stats are AI-estimated scores derived from federal data. "
        "This comparison is generated by FutureProof, powered by Gemma 4. "
        "Gemma is a trademark of Google LLC. It should complement, not "
        "replace, professional guidance.*"
    )
    lines.append("")

    filename = f"compare_{_ts()}.md"
    path = _reports_dir() / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
