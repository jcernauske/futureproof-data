"""Auto-generate data/reference/major_to_cip.yaml from the crosswalk.

Expands the hand-curated hackathon YAML (52 Business + 13 Education, 56
entries across 2 families) into a broader scaffold covering every 4-digit
CIP that has actual SOC coverage in ``base.cip_soc_crosswalk``.

Existing entries are preserved verbatim — this script only ADDS stubs for
cip4s the file doesn't mention yet. So a curator's hand-written aliases,
custom major names, or deliberate omissions all survive a re-run. The
only failure mode is "someone deleted a YAML entry and didn't remove the
corresponding cip4 from the crosswalk" — but the crosswalk is upstream
truth, so re-adding a missing cip4 is the right move anyway.

Stubs use the crosswalk's ``cip_title`` (trailing periods stripped) as
the major name and leave ``aliases: []``. Curators can fill in aliases
as they come up against real student inputs that miss.

Families tagged 99 ("Other") are excluded — they're the residual bucket
and map to nothing useful.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

# src/ needs to be on the path so we can hit the MCP server's Iceberg
# query helper — same strategy backend/app uses.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from mcp_server.futureproof_server import FutureProofMCPServer  # noqa: E402

YAML_PATH = _REPO_ROOT / "data" / "reference" / "major_to_cip.yaml"
CATALOG_PATH = _REPO_ROOT / "data" / "catalog" / "catalog.db"
WAREHOUSE_PATH = _REPO_ROOT / "data" / "warehouse"

# CIP 2020 family names — stable across editions, safe to hardcode. Pulled
# from the NCES CIP 2020 SOC crosswalk documentation. Used for section-
# header comments so curators can see what they're looking at.
FAMILY_NAMES: dict[str, str] = {
    "01": "Agriculture, Agriculture Operations, and Related Sciences",
    "03": "Natural Resources and Conservation",
    "04": "Architecture and Related Services",
    "05": "Area, Ethnic, Cultural, Gender, and Group Studies",
    "09": "Communication, Journalism, and Related Programs",
    "10": "Communications Technologies/Technicians and Support Services",
    "11": "Computer and Information Sciences and Support Services",
    "12": "Personal and Culinary Services",
    "13": "Education",
    "14": "Engineering",
    "15": "Engineering/Engineering-Related Technologies/Technicians",
    "16": "Foreign Languages, Literatures, and Linguistics",
    "19": "Family and Consumer Sciences/Human Sciences",
    "22": "Legal Professions and Studies",
    "23": "English Language and Literature/Letters",
    "24": "Liberal Arts and Sciences, General Studies and Humanities",
    "25": "Library Science",
    "26": "Biological and Biomedical Sciences",
    "27": "Mathematics and Statistics",
    "28": "Military Science, Leadership and Operational Art",
    "29": "Military Technologies and Applied Sciences",
    "30": "Multi/Interdisciplinary Studies",
    "31": "Parks, Recreation, Leisure, Fitness, and Kinesiology",
    "38": "Philosophy and Religious Studies",
    "39": "Theology and Religious Vocations",
    "40": "Physical Sciences",
    "41": "Science Technologies/Technicians",
    "42": "Psychology",
    "43": "Homeland Security, Law Enforcement, Firefighting, and Related",
    "44": "Public Administration and Social Service Professions",
    "45": "Social Sciences",
    "46": "Construction Trades",
    "47": "Mechanic and Repair Technologies/Technicians",
    "48": "Precision Production",
    "49": "Transportation and Materials Moving",
    "50": "Visual and Performing Arts",
    "51": "Health Professions and Related Programs",
    "52": "Business, Management, Marketing, and Related Support Services",
    "54": "History",
    "60": "Residency Programs",
    "61": "Medical Residency/Fellowship Programs",
}

# 99 is the NCES residual "Other" family — nothing maps to real careers.
# 60/61 are medical residency / fellowship programs — post-graduate
# specialties, not student-facing majors. No prospective undergrad types
# "Acute Care Nurse Practitioner Residency/Fellowship Program" and
# including them just adds false-positive surface area to the lookup.
EXCLUDED_FAMILIES = {"60", "61", "99"}

# NCES assigns a "XX.YY99 — Something, Other" residual bucket to most
# families. Those entries have "Other" as the student-facing signal,
# which is never what a student types. Drop them — if they matter for
# specific schools, a curator can add them back with aliases.
def _is_other_bucket_title(title: str) -> bool:
    stripped = title.rstrip(".").strip()
    return stripped.endswith("Other") or stripped.endswith(", Other")

HEADER = """\
# Major-to-CIP Intent Lookup
# Used when a school reports only a broad XX.01 CIP and the student
# specifies a more specific major. Maps the student's stated intent
# to the specific CIP whose crosswalk SOC mappings best represent
# that major's career paths.
#
# Structure: list of entries, each with:
#   - major: the canonical name for the major
#   - cip4: the 4-digit CIP prefix to substitute (XX.YY)
#   - cip_family: the 2-digit family this belongs to
#   - aliases: alternate names, abbreviations, misspellings
#
# Generated by scripts/regenerate_major_to_cip_yaml.py. Hand-curated
# entries (any cip4 already in the file) are preserved verbatim — the
# generator only adds NEW cip4s from base.cip_soc_crosswalk. Safe to
# re-run; safe to hand-edit aliases and major names in-place.
#
# Source of truth for new entries: base.cip_soc_crosswalk. Any cip4
# with at least one non-catch-all SOC gets a stub.

"""


def _clean_title(raw: str) -> str:
    """Strip the trailing period + collapse double spaces the crosswalk
    occasionally emits (e.g. "American  History")."""
    title = raw.strip()
    while title.endswith("."):
        title = title[:-1]
    return " ".join(title.split())


def _load_existing() -> list[dict[str, Any]]:
    """Return the current YAML as a list (preserving order + duplicates).

    The existing YAML has at least one pair of entries sharing the same
    cip4 (``Business Administration`` and ``Supply Chain Management``
    both claim ``52.02``) because two different aliases lead to the
    same CIP. Both entries are load-bearing for lookup — we keep them
    verbatim and only skip auto-stubs whose cip4 is already represented.
    """
    if not YAML_PATH.is_file():
        return []
    with YAML_PATH.open() as f:
        data = yaml.safe_load(f) or []
    if not isinstance(data, list):
        return []
    return [e for e in data if isinstance(e, dict) and e.get("cip4")]


def _fetch_crosswalk_cip4s() -> list[dict[str, Any]]:
    """Return one row per 4-digit CIP that has usable SOC coverage.

    Picks the title from the lowest-numbered 6-digit code under each
    cip4 (``arg_min(cip_title, cipcode)``). NCES numbers the "General"
    variant of a family first — ``14.0101 Engineering, General`` comes
    before ``14.0103 Applied Engineering`` — so this picks the
    representative title instead of the alphabetically smallest one,
    which used to land on "Applied Engineering" at cip4 ``14.01``.
    """
    server = FutureProofMCPServer(
        warehouse_path=str(WAREHOUSE_PATH),
        catalog_path=str(CATALOG_PATH),
        server_name="regen-yaml",
    )
    rows = server.query_iceberg(
        """
        SELECT SUBSTR(cipcode, 1, 5)           AS cip4,
               arg_min(cip_title, cipcode)     AS title,
               COUNT(DISTINCT soc_code)        AS soc_n
        FROM base_cip_soc_crosswalk
        WHERE soc_code IS NOT NULL
          AND soc_code <> '99-9999'
        GROUP BY cip4
        ORDER BY cip4
        """
    )
    return list(rows)


def _format_entry(entry: dict[str, Any]) -> str:
    """Emit one entry in the YAML shape the existing file uses.

    Explicit formatter (not yaml.dump) so we get consistent quoting,
    predictable field order, and a blank line between entries — the diff
    stays readable when we add new stubs. Avoids yaml.dump's habit of
    reordering keys and dropping the string quotes we want to keep.
    """
    lines = [
        f'- major: "{entry["major"]}"',
        f'  cip4: "{entry["cip4"]}"',
        f'  cip_family: "{entry["cip_family"]}"',
    ]
    aliases = entry.get("aliases") or []
    if aliases:
        lines.append("  aliases:")
        for alias in aliases:
            lines.append(f'    - "{alias}"')
    else:
        lines.append("  aliases: []")
    return "\n".join(lines)


def main() -> int:
    existing = _load_existing()
    existing_cip4s = {str(e.get("cip4", "")) for e in existing}
    # Name collisions would break lookup_major's "first match wins"
    # contract: the 2020 NCES crosswalk introduces "Business Analytics"
    # at 30.7102 (family 30 Data Analytics), and a hand-curated entry
    # already maps that name to 52.13. Auto-generated entries must defer
    # to any hand-curated name or alias, case-insensitive.
    reserved_names: set[str] = set()
    for entry in existing:
        major = str(entry.get("major") or "").strip().lower()
        if major:
            reserved_names.add(major)
        for alias in entry.get("aliases") or []:
            alias_s = str(alias).strip().lower()
            if alias_s:
                reserved_names.add(alias_s)
    crosswalk = _fetch_crosswalk_cip4s()

    # Bucket by family so we can emit readable section headers.
    by_family: dict[str, list[dict[str, Any]]] = {}

    # Start with hand-curated entries — they're authoritative and keep
    # their ordering / duplicates / aliases.
    for entry in existing:
        cip4 = str(entry.get("cip4", ""))
        fam = str(entry.get("cip_family") or cip4[:2])
        if fam in EXCLUDED_FAMILIES:
            continue
        by_family.setdefault(fam, []).append(entry)

    # Layer crosswalk stubs on top — only for cip4s not already covered
    # AND whose title doesn't collide with a curated name/alias.
    skipped_name_collisions: list[tuple[str, str]] = []
    skipped_other_buckets: list[tuple[str, str]] = []
    for row in crosswalk:
        cip4 = str(row["cip4"])
        if cip4 in existing_cip4s:
            continue
        family = cip4[:2]
        if family in EXCLUDED_FAMILIES:
            continue
        title = _clean_title(str(row["title"]))
        if _is_other_bucket_title(title):
            skipped_other_buckets.append((cip4, title))
            continue
        if title.lower() in reserved_names:
            skipped_name_collisions.append((cip4, title))
            continue
        by_family.setdefault(family, []).append({
            "major": title,
            "cip4": cip4,
            "cip_family": family,
            "aliases": [],
        })

    # Within a family, stable-sort by cip4 so the diff is deterministic
    # but curated entries keep their relative order when they tie.
    for fam_entries in by_family.values():
        fam_entries.sort(key=lambda e: str(e.get("cip4", "")))

    # Assemble.
    out_chunks: list[str] = [HEADER]
    for family in sorted(by_family):
        fam_name = FAMILY_NAMES.get(family, "Unknown")
        out_chunks.append(
            "# " + "-" * 75 + "\n"
            f"# CIP Family {family} — {fam_name}\n"
            "# " + "-" * 75 + "\n"
        )
        for entry in by_family[family]:
            out_chunks.append(_format_entry(entry) + "\n")
        out_chunks.append("")  # blank line between families

    output = "\n".join(out_chunks).rstrip() + "\n"
    YAML_PATH.write_text(output)

    # Reporting.
    total_entries = sum(len(v) for v in by_family.values())
    preserved = len(existing)
    new_entries = total_entries - preserved
    print(f"Wrote {YAML_PATH}")
    print(
        f"  families: {len(by_family)} "
        f"(excluded: {sorted(EXCLUDED_FAMILIES)})"
    )
    print(f"  entries:  {total_entries} "
          f"(preserved: {preserved}, new: {new_entries})")
    if skipped_name_collisions:
        print(
            f"  skipped {len(skipped_name_collisions)} crosswalk entries "
            "whose titles collide with curated names:"
        )
        for cip4, title in skipped_name_collisions:
            print(f"    - {cip4} {title!r}")
    if skipped_other_buckets:
        print(
            f"  skipped {len(skipped_other_buckets)} "
            "residual 'Other' buckets (no student signal)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
