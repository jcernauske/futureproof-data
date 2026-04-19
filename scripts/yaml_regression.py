"""YAML vs Gemma regression — compare hand-curated CIPs against live Gemma.

Runs every (input, expected_cip) pair from data/reference/major_to_cip.yaml
through resolve_intent with INTENT_YAML_ENABLED=false. Writes a markdown
report to reports/intent-yaml-regression-YYYY-MM-DD-HHMMSS.md.

See docs/specs/completed/bugfix-disable-intent-yaml-regression.md (V1 +
V2 methodology). The default mode is V1 — unanchored, no school context.
Pass --anchored to invoke V2 — each input is run against k=3 real schools
that actually report a CIP in the expected family, mirroring the way
production's UI calls resolve_intent.

Run:
    uv run python scripts/yaml_regression.py                  # V1 unanchored
    uv run python scripts/yaml_regression.py --backend openrouter
    uv run python scripts/yaml_regression.py --family 51 --limit 10
    uv run python scripts/yaml_regression.py --dry-run        # no Gemma calls
    uv run python scripts/yaml_regression.py --anchored       # V2: 3 schools/input
    uv run python scripts/yaml_regression.py --anchored --k 5
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "backend"))

# Disable the YAML short-circuit BEFORE importing intent so resolve_intent
# routes every input through Gemma — the whole point of this script.
os.environ["INTENT_YAML_ENABLED"] = "false"

from app.services import intent  # noqa: E402

# Per §2 decision #7 of the spec: the audit prompt is a separate Gemma
# call that doesn't contribute to the YAML-vs-Gemma intent comparison.
# Patching it to a no-op halves wall time and openrouter cost without
# affecting the matched_cip we report on. Audit-tone behavior is
# covered by the intent test suite, not by this script.
intent._audit_intent_mapping = lambda *a, **kw: None  # type: ignore[assignment]

YAML_PATH = _REPO_ROOT / "data" / "reference" / "major_to_cip.yaml"
REPORT_DIR = _REPO_ROOT / "reports"


def _enumerate_cases(
    path: Path, family_filter: str | None
) -> list[tuple[str, str, str]]:
    """Return list of (student_input, expected_cip4, source_entry_major).

    Enumerates the canonical major + every alias for every YAML entry
    where ``aliases`` is non-empty (the 56 hand-curated entries Bug B
    was built to catch).
    """
    data = yaml.safe_load(path.read_text())
    cases: list[tuple[str, str, str]] = []
    for entry in data:
        aliases = entry.get("aliases") or []
        if not aliases:
            continue
        cip4 = str(entry.get("cip4", ""))
        if family_filter and not cip4.startswith(family_filter):
            continue
        major = str(entry.get("major", ""))
        cases.append((major, cip4, major))
        for alias in aliases:
            cases.append((str(alias), cip4, major))
    return cases


def _run_one(student_input: str) -> dict:
    """Call resolve_intent with the gate already disabled at process start.

    Returns a dict the report renderer consumes. Caller wraps every
    failure (Gemma down, malformed primary CIP, MCP unavailable) into
    the same shape so the report row never crashes mid-write.
    """
    start = time.perf_counter()
    try:
        result = intent.resolve_intent(
            major_text=student_input,
            school_name="University of Central Anywhere",
            unitid=0,
            programs=[],
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": True,
            "returned_cip": result.matched_cip,
            "returned_title": result.matched_title,
            "confidence": result.confidence,
            "reasoning": (result.reasoning or "").replace("\n", " ").strip(),
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # noqa: BLE001 — every failure goes in the report
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": False,
            "returned_cip": "",
            "returned_title": "",
            "confidence": "",
            "reasoning": f"{type(exc).__name__}: {exc}",
            "latency_ms": latency_ms,
        }


def _sample_anchoring_schools(
    expected_cip4: str, k: int = 3
) -> list[tuple[int, str, list[dict[str, str]]]]:
    """Return up to ``k`` (unitid, school_name, programs) triples for
    schools that actually report a CIP in ``expected_cip4``'s family.

    "Family" = the first 5 chars of the cip4 (so ``13.1003`` matches
    ``13.10``-prefixed leaves and ``13.02`` matches ``13.02``-prefixed
    leaves). Sorted by ``unitid`` ASC for determinism — same DuckDB +
    same arguments → same schools across runs.

    ``programs`` is the school's full reported CIP catalog (the same
    list ``intent._get_school_cips`` produces in production), so the
    Gemma prompt sees the exact "Candidate CIPs — programs reported by
    this school" bullet list the UI sends.

    Returns ``[]`` when no school in the dataset offers the family.
    Caller treats that as "no_anchor_available" rather than as an
    error — it's a finding (the YAML may carry CIPs the Gold zone
    doesn't have institutional coverage for).
    """
    if not expected_cip4:
        return []
    family_prefix = expected_cip4[:5]
    server = intent.mcp_client.get_server()
    sql = (
        "SELECT DISTINCT unitid, institution_name "
        "FROM consumable_career_outcomes "
        f"WHERE SUBSTR(cipcode, 1, 5) = '{family_prefix}' "
        "AND institution_name IS NOT NULL "
        "ORDER BY unitid "
        f"LIMIT {int(k)}"
    )
    try:
        rows = server.query_iceberg(sql)
    except Exception:
        return []
    out: list[tuple[int, str, list[dict[str, str]]]] = []
    for row in rows:
        unitid_raw = row.get("unitid")
        name_raw = row.get("institution_name")
        if unitid_raw is None or not name_raw:
            continue
        unitid = int(unitid_raw)
        school_name = str(name_raw)
        programs = intent._get_school_cips(unitid)
        out.append((unitid, school_name, programs))
    return out


def _run_one_anchored(
    student_input: str,
    school_name: str,
    unitid: int,
    programs: list[dict[str, str]],
) -> dict:
    """Anchored variant of :func:`_run_one`.

    Same defensive shape — every failure becomes a row, never a crash —
    but threads the school context through so Gemma's prompt sees the
    "Candidate CIPs — programs reported by this school" bullet list
    that production's UI always provides. This is the difference V2
    exists to measure.
    """
    start = time.perf_counter()
    try:
        result = intent.resolve_intent(
            major_text=student_input,
            school_name=school_name,
            unitid=unitid,
            programs=programs,
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": True,
            "returned_cip": result.matched_cip,
            "returned_title": result.matched_title,
            "confidence": result.confidence,
            "reasoning": (result.reasoning or "").replace("\n", " ").strip(),
            "latency_ms": latency_ms,
        }
    except Exception as exc:  # noqa: BLE001 — every failure goes in the report
        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "ok": False,
            "returned_cip": "",
            "returned_title": "",
            "confidence": "",
            "reasoning": f"{type(exc).__name__}: {exc}",
            "latency_ms": latency_ms,
        }


def _is_match(expected_cip4: str, returned_cip: str) -> bool:
    """Exact 4-digit family match, per §2 decision #5.

    The YAML stores XX.YY (4-digit family). Gemma returns XX.YYYY
    (6-digit leaf). A "match" means the leaf's first 5 chars equal the
    family. Same-family different-leaf would reduce to the same family
    here — that's intentional. We're testing whether Gemma found the
    right family/program, not whether it picked the same arbitrary
    leaf the YAML curator picked.
    """
    if not returned_cip or not expected_cip4:
        return False
    return returned_cip[:5] == expected_cip4 if "." in expected_cip4 else False


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _md_escape(text: str) -> str:
    """Escape pipe characters so a freeform string doesn't break a md table."""
    return text.replace("|", "\\|")


def _default_output_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    return REPORT_DIR / f"intent-yaml-regression-{stamp}.md"


def _default_anchored_output_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    return REPORT_DIR / f"intent-yaml-regression-anchored-{stamp}.md"


def _summarize_by_family(rows: list[dict]) -> list[tuple[str, int, int]]:
    """Per-CIP-family (rate, total, matches) — for the family table."""
    by_family: dict[str, list[bool]] = {}
    for row in rows:
        family = row["expected_cip"][:2]
        by_family.setdefault(family, []).append(bool(row["match"]))
    out: list[tuple[str, int, int]] = []
    for family in sorted(by_family):
        flags = by_family[family]
        out.append((family, len(flags), sum(flags)))
    return out


def _write_report(
    rows: list[dict],
    output_path: Path,
    *,
    backend: str,
    wall_seconds: float,
) -> None:
    total = len(rows)
    matches = sum(1 for r in rows if r["match"])
    mismatches = sum(1 for r in rows if r["ok"] and not r["match"])
    errors = sum(1 for r in rows if not r["ok"])
    rate = (matches / total * 100) if total else 0.0
    confidence_counts = Counter(
        r["confidence"] for r in rows if r["ok"] and r["confidence"]
    )

    lines: list[str] = []
    lines.append("# Intent YAML Regression — Gemma vs Hand-Curated CIPs")
    lines.append("")
    lines.append(
        f"Generated by `scripts/yaml_regression.py` at "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}."
    )
    lines.append("")
    lines.append(
        "Spec: `docs/specs/bugfix-disable-intent-yaml-regression.md`"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Backend | `{backend}` |")
    lines.append(f"| Total inputs | {total} |")
    lines.append(f"| Matches | {matches} |")
    lines.append(f"| Mismatches | {mismatches} |")
    lines.append(f"| Errors | {errors} |")
    lines.append(f"| Match rate | {rate:.1f}% |")
    lines.append(f"| Wall time | {wall_seconds:.1f}s |")
    if confidence_counts:
        breakdown = ", ".join(
            f"{tier}={n}" for tier, n in sorted(confidence_counts.items())
        )
        lines.append(f"| Confidence breakdown | {breakdown} |")
    lines.append("")

    lines.append("## Match rate by CIP family")
    lines.append("")
    lines.append("| Family | Inputs | Matches | Rate |")
    lines.append("|--------|--------|---------|------|")
    for family, n, m in _summarize_by_family(rows):
        family_rate = (m / n * 100) if n else 0.0
        lines.append(f"| {family} | {n} | {m} | {family_rate:.1f}% |")
    lines.append("")

    lines.append("## All inputs")
    lines.append("")
    lines.append(
        "| # | Input | Expected | Returned | Match | Confidence | "
        "Latency | Reasoning |"
    )
    lines.append(
        "|---|-------|----------|----------|-------|------------|---------|------|"
    )
    for idx, row in enumerate(rows, 1):
        flag = "✅" if row["match"] else ("❌" if row["ok"] else "⚠️")
        lines.append(
            "| {idx} | `{inp}` | `{exp}` | `{ret}` | {flag} | {conf} | "
            "{lat}ms | {why} |".format(
                idx=idx,
                inp=_md_escape(row["input"]),
                exp=row["expected_cip"],
                ret=row["returned_cip"] or "—",
                flag=flag,
                conf=row["confidence"] or "—",
                lat=row["latency_ms"],
                why=_md_escape(_truncate(row["reasoning"], 120)),
            )
        )
    lines.append("")

    mismatch_rows = [r for r in rows if r["ok"] and not r["match"]]
    if mismatch_rows:
        lines.append("## Mismatches (Gemma disagreed with the YAML)")
        lines.append("")
        lines.append(
            "| Input | Expected | Returned | Confidence | Reasoning |"
        )
        lines.append(
            "|-------|----------|----------|------------|-----------|"
        )
        for row in mismatch_rows:
            lines.append(
                "| `{inp}` | `{exp}` | `{ret}` | {conf} | {why} |".format(
                    inp=_md_escape(row["input"]),
                    exp=row["expected_cip"],
                    ret=row["returned_cip"] or "—",
                    conf=row["confidence"] or "—",
                    why=_md_escape(_truncate(row["reasoning"], 200)),
                )
            )
        lines.append("")

    error_rows = [r for r in rows if not r["ok"]]
    if error_rows:
        lines.append("## Errors (resolve_intent raised)")
        lines.append("")
        lines.append("| Input | Expected | Error |")
        lines.append("|-------|----------|-------|")
        for row in error_rows:
            lines.append(
                "| `{inp}` | `{exp}` | {err} |".format(
                    inp=_md_escape(row["input"]),
                    exp=row["expected_cip"],
                    err=_md_escape(_truncate(row["reasoning"], 200)),
                )
            )
        lines.append("")

    output_path.write_text("\n".join(lines))


def _summarize_anchored_by_family(
    rows: list[dict],
) -> list[tuple[str, int, int]]:
    """Per-family (family, attempts, matches) — counts (input, school)
    rows where ``ok`` is true, attempted-but-mismatched and matched
    both contribute to ``attempts``. ``no_anchor_available`` rows are
    included in attempts but never count as matches (the family-level
    rate honestly reflects "schools where we tried")."""
    by_family: dict[str, list[bool]] = {}
    for row in rows:
        family = row["expected_cip"][:2]
        by_family.setdefault(family, []).append(bool(row["match"]))
    out: list[tuple[str, int, int]] = []
    for family in sorted(by_family):
        flags = by_family[family]
        out.append((family, len(flags), sum(flags)))
    return out


def _per_input_aggregate(rows: list[dict]) -> list[dict]:
    """Collapse per-(input, school) rows into one row per input.

    Returns rows of the form
    ``{input, expected_cip, source_entry, schools_tested, matches,
       modal_returned_cip, worst_reasoning}``.
    Iteration is stable on first-appearance order so the report stays
    in the YAML's enumeration order.
    """
    seen: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for row in rows:
        key = (row["input"], row["expected_cip"])
        if key not in seen:
            seen[key] = {
                "input": row["input"],
                "expected_cip": row["expected_cip"],
                "source_entry": row.get("source_entry", ""),
                "schools_tested": 0,
                "matches": 0,
                "returned_cips": [],
                "worst_reasoning": "",
            }
            order.append(key)
        agg = seen[key]
        agg["schools_tested"] += 1
        if row.get("match"):
            agg["matches"] += 1
        if row.get("returned_cip"):
            agg["returned_cips"].append(row["returned_cip"])
        if not row.get("match") and row.get("reasoning"):
            agg["worst_reasoning"] = row["reasoning"]
    out: list[dict] = []
    for key in order:
        agg = seen[key]
        cips = agg.pop("returned_cips")
        if cips:
            agg["modal_returned_cip"] = Counter(cips).most_common(1)[0][0]
        else:
            agg["modal_returned_cip"] = ""
        out.append(agg)
    return out


def _write_anchored_report(
    rows: list[dict],
    output_path: Path,
    *,
    backend: str,
    wall_seconds: float,
    k: int,
    no_anchor_inputs: list[tuple[str, str, str]],
    v1_rate_pct: float = 9.1,
) -> None:
    total_attempts = len(rows)
    matches = sum(1 for r in rows if r["match"])
    mismatches = sum(1 for r in rows if r["ok"] and not r["match"])
    errors = sum(1 for r in rows if not r["ok"])
    rate = (matches / total_attempts * 100) if total_attempts else 0.0
    per_input = _per_input_aggregate(rows)
    confidence_counts = Counter(
        r["confidence"] for r in rows if r["ok"] and r["confidence"]
    )

    bucket = Counter()
    for agg in per_input:
        if agg["schools_tested"] == 0:
            bucket["0/0"] += 1
            continue
        bucket[f"{agg['matches']}/{agg['schools_tested']}"] += 1

    # Go/no-go bands per §12.
    if rate >= 85.0:
        verdict = (
            "**DISABLE-YAML SAFE.** Anchored match rate ≥85%. "
            "Set Your Course can ship with `INTENT_YAML_ENABLED=false`."
        )
    elif rate >= 60.0:
        verdict = (
            "**MIXED — per-family disable.** Anchored match rate in the "
            "60–85% band. YAML stays on; consider per-family disable for "
            "the strong families."
        )
    else:
        verdict = (
            "**KEEP YAML.** Anchored match rate <60%. YAML stays on in "
            "production; Set Your Course routes chip corrections through "
            "Gemma but trusts YAML for initial resolution."
        )

    lines: list[str] = []
    lines.append(
        "# Intent YAML Regression — V2 Anchored (Gemma vs Hand-Curated CIPs)"
    )
    lines.append("")
    lines.append(
        f"Generated by `scripts/yaml_regression.py --anchored --k {k}` at "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}."
    )
    lines.append("")
    lines.append(
        "Spec: `docs/specs/completed/bugfix-disable-intent-yaml-regression.md`"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")
    lines.append(f"| Mode | Anchored (V2) — k={k} schools per input |")
    lines.append(f"| Backend | `{backend}` |")
    lines.append(f"| Inputs enumerated | {len(per_input)} |")
    lines.append(f"| Total (input, school) attempts | {total_attempts} |")
    lines.append(f"| Matches | {matches} |")
    lines.append(f"| Mismatches | {mismatches} |")
    lines.append(f"| Errors | {errors} |")
    lines.append(f"| Inputs with no anchoring school | {len(no_anchor_inputs)} |")
    lines.append(f"| Anchored match rate | {rate:.1f}% |")
    lines.append(f"| V1 (unanchored) match rate | {v1_rate_pct:.1f}% |")
    lines.append(
        f"| Δ (anchored − unanchored) | {rate - v1_rate_pct:+.1f} pp |"
    )
    lines.append(f"| Wall time | {wall_seconds:.1f}s |")
    if confidence_counts:
        breakdown = ", ".join(
            f"{tier}={n}" for tier, n in sorted(confidence_counts.items())
        )
        lines.append(f"| Confidence breakdown | {breakdown} |")
    lines.append("")
    lines.append(f"**Verdict.** {verdict}")
    lines.append("")

    lines.append("## Per-input aggregate (matches / schools_tested)")
    lines.append("")
    lines.append("| Bucket | Inputs |")
    lines.append("|--------|--------|")
    for label in sorted(bucket, key=lambda s: (int(s.split('/')[1]), -int(s.split('/')[0]))):
        lines.append(f"| {label} | {bucket[label]} |")
    lines.append("")

    lines.append("## Match rate by CIP family (V2 anchored)")
    lines.append("")
    lines.append("| Family | Attempts | Matches | Rate |")
    lines.append("|--------|----------|---------|------|")
    for family, n, m in _summarize_anchored_by_family(rows):
        family_rate = (m / n * 100) if n else 0.0
        lines.append(f"| {family} | {n} | {m} | {family_rate:.1f}% |")
    lines.append("")

    lines.append("## Per-input results")
    lines.append("")
    lines.append(
        "| # | Input | Expected | Schools Tested | Matches | Modal Returned | "
        "Worst-case Reasoning |"
    )
    lines.append(
        "|---|-------|----------|----------------|---------|----------------|------|"
    )
    for idx, agg in enumerate(per_input, 1):
        lines.append(
            "| {idx} | `{inp}` | `{exp}` | {st} | {m}/{st} | `{ret}` | {why} |"
            .format(
                idx=idx,
                inp=_md_escape(agg["input"]),
                exp=agg["expected_cip"],
                st=agg["schools_tested"],
                m=agg["matches"],
                ret=agg["modal_returned_cip"] or "—",
                why=_md_escape(_truncate(agg["worst_reasoning"], 100)),
            )
        )
    lines.append("")

    lines.append("## Full per-(input, school) table")
    lines.append("")
    lines.append(
        "| # | Input | Expected | School | UnitID | Returned | Match | "
        "Confidence | Latency |"
    )
    lines.append(
        "|---|-------|----------|--------|--------|----------|-------|"
        "------------|---------|"
    )
    for idx, row in enumerate(rows, 1):
        flag = "✅" if row["match"] else ("❌" if row["ok"] else "⚠️")
        lines.append(
            "| {idx} | `{inp}` | `{exp}` | {school} | {uid} | `{ret}` | "
            "{flag} | {conf} | {lat}ms |".format(
                idx=idx,
                inp=_md_escape(row["input"]),
                exp=row["expected_cip"],
                school=_md_escape(_truncate(row.get("anchor_school", ""), 40)),
                uid=row.get("anchor_unitid", "—"),
                ret=row["returned_cip"] or "—",
                flag=flag,
                conf=row["confidence"] or "—",
                lat=row["latency_ms"],
            )
        )
    lines.append("")

    if no_anchor_inputs:
        lines.append("## Inputs with no anchoring school")
        lines.append("")
        lines.append(
            "These inputs map to a YAML cip4 that no school in the Gold "
            "zone reports. Possible causes: niche CIPs that rolled up to "
            "broader umbrellas in the data we ingested; brand-new CIP "
            "codes; data-coverage gaps."
        )
        lines.append("")
        lines.append("| Input | Expected | Source Entry |")
        lines.append("|-------|----------|--------------|")
        for student_input, expected_cip, source in no_anchor_inputs:
            lines.append(
                f"| `{_md_escape(student_input)}` | `{expected_cip}` | "
                f"{_md_escape(source)} |"
            )
        lines.append("")

    error_rows = [r for r in rows if not r["ok"]]
    if error_rows:
        lines.append("## Errors (resolve_intent raised)")
        lines.append("")
        lines.append("| Input | Expected | School | Error |")
        lines.append("|-------|----------|--------|-------|")
        for row in error_rows:
            lines.append(
                "| `{inp}` | `{exp}` | {school} | {err} |".format(
                    inp=_md_escape(row["input"]),
                    exp=row["expected_cip"],
                    school=_md_escape(_truncate(row.get("anchor_school", ""), 40)),
                    err=_md_escape(_truncate(row["reasoning"], 200)),
                )
            )
        lines.append("")

    output_path.write_text("\n".join(lines))


def _run_anchored(
    cases: list[tuple[str, str, str]],
    args: argparse.Namespace,
    backend: str,
) -> int:
    """V2 anchored loop: per input, fan out across k anchoring schools.

    Logs to stdout in a single line per (input, school) pair so the
    background runner / monitor can grep "OK"/"MISS"/"ERR" without
    parsing the full report. Inputs with no anchoring school in the
    Gold zone are recorded separately and reported in §"Inputs with
    no anchoring school" of the V2 report.
    """
    print(
        f"V2 anchored mode: {len(cases)} inputs × up to {args.k} schools "
        f"each (backend={backend}, INTENT_YAML_ENABLED=false)"
    )
    rows: list[dict] = []
    no_anchor_inputs: list[tuple[str, str, str]] = []
    wall_start = time.perf_counter()

    for case_idx, (student_input, expected_cip, source) in enumerate(cases, 1):
        anchors = _sample_anchoring_schools(expected_cip, k=args.k)
        if not anchors:
            no_anchor_inputs.append((student_input, expected_cip, source))
            print(
                f"  [{case_idx:>3}/{len(cases)}] SKIP "
                f"{expected_cip} <- {student_input!r:<40s} "
                f"(no anchoring school in Gold zone)",
                flush=True,
            )
            continue
        for unitid, school_name, programs in anchors:
            result = _run_one_anchored(
                student_input, school_name, unitid, programs
            )
            match = _is_match(expected_cip, result["returned_cip"])
            rows.append({
                "input": student_input,
                "expected_cip": expected_cip,
                "source_entry": source,
                "anchor_unitid": unitid,
                "anchor_school": school_name,
                "match": match,
                **result,
            })
            flag = "OK " if match else ("MISS" if result["ok"] else "ERR ")
            print(
                f"  [{case_idx:>3}/{len(cases)}] {flag} "
                f"{expected_cip} <- {student_input!r:<40s} "
                f"@ {school_name[:30]:<30s} "
                f"-> {result['returned_cip'] or '—':<8s} "
                f"({result['latency_ms']}ms)",
                flush=True,
            )
            if args.sleep > 0:
                time.sleep(args.sleep)

    wall_seconds = time.perf_counter() - wall_start

    output_path = (
        Path(args.output) if args.output else _default_anchored_output_path()
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_anchored_report(
        rows,
        output_path,
        backend=backend,
        wall_seconds=wall_seconds,
        k=args.k,
        no_anchor_inputs=no_anchor_inputs,
    )

    matches = sum(1 for r in rows if r["match"])
    rate = (matches / len(rows) * 100) if rows else 0.0
    print(
        f"\n{matches}/{len(rows)} matched ({rate:.1f}%) across "
        f"{len(rows)} (input, school) attempts in {wall_seconds:.1f}s. "
        f"{len(no_anchor_inputs)} inputs had no anchoring school."
    )
    print(f"wrote {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Gemma's intent resolution against the hand-curated "
            "YAML for the 56 entries with aliases."
        )
    )
    parser.add_argument(
        "--backend",
        choices=["ollama", "openrouter"],
        default=None,
        help="Override INFERENCE_BACKEND for this run.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Stop after N inputs (debugging).",
    )
    parser.add_argument(
        "--family",
        type=str,
        default=None,
        help="Restrict to YAML entries whose cip4 starts with this prefix.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=(
            "Override report path. Defaults to "
            "reports/intent-yaml-regression-YYYY-MM-DD-HHMMSS.md"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the inputs without calling Gemma.",
    )
    parser.add_argument(
        "--anchored",
        action="store_true",
        help=(
            "V2 anchored mode: for each input, run resolve_intent against "
            "k schools that actually report a CIP in the expected family "
            "(production-realistic). Default: V1 unanchored."
        ),
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Anchored mode: schools per input (default 3). Ignored without --anchored.",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help=(
            "Seconds to wait between anchored Gemma calls. Use 0.5–1.0 to "
            "spread OpenRouter rate-limit pressure on long V2 runs."
        ),
    )
    args = parser.parse_args(argv)

    if args.backend:
        os.environ["INFERENCE_BACKEND"] = args.backend
    backend = os.environ.get("INFERENCE_BACKEND", "ollama")

    cases = _enumerate_cases(YAML_PATH, args.family)
    if args.limit is not None:
        cases = cases[: args.limit]

    if args.dry_run:
        if args.anchored:
            print(
                f"Would test {len(cases)} inputs × up to {args.k} anchoring "
                f"schools each with backend={backend}:"
            )
            for student_input, expected_cip, source in cases:
                anchors = _sample_anchoring_schools(expected_cip, k=args.k)
                anchor_strs = (
                    ", ".join(f"{u}({n[:25]})" for u, n, _ in anchors)
                    if anchors
                    else "(no anchoring school)"
                )
                print(
                    f"  {expected_cip}  {source!r}  <- {student_input!r}  "
                    f"@ [{anchor_strs}]"
                )
        else:
            print(f"Would test {len(cases)} inputs with backend={backend}:")
            for student_input, expected_cip, source in cases:
                print(f"  {expected_cip}  {source!r}  <- {student_input!r}")
        return 0

    if args.anchored:
        return _run_anchored(cases, args, backend)

    print(
        f"Running {len(cases)} inputs through Gemma "
        f"(backend={backend}, INTENT_YAML_ENABLED=false)..."
    )
    rows: list[dict] = []
    wall_start = time.perf_counter()
    for idx, (student_input, expected_cip, source) in enumerate(cases, 1):
        result = _run_one(student_input)
        match = _is_match(expected_cip, result["returned_cip"])
        rows.append({
            "input": student_input,
            "expected_cip": expected_cip,
            "source_entry": source,
            "match": match,
            **result,
        })
        flag = "OK " if match else ("MISS" if result["ok"] else "ERR ")
        print(
            f"  [{idx:>3}/{len(cases)}] {flag} "
            f"{expected_cip} <- {student_input!r:<40s} "
            f"-> {result['returned_cip'] or '—':<8s} "
            f"({result['latency_ms']}ms)"
        )
    wall_seconds = time.perf_counter() - wall_start

    output_path = (
        Path(args.output) if args.output else _default_output_path()
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_report(rows, output_path, backend=backend, wall_seconds=wall_seconds)

    matches = sum(1 for r in rows if r["match"])
    print(
        f"\n{matches}/{len(rows)} matched "
        f"({(matches / len(rows) * 100) if rows else 0:.1f}%) "
        f"in {wall_seconds:.1f}s"
    )
    print(f"wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
