"""Rebase committed Iceberg metadata to repo-root-relative paths.

The Brightsmith pipeline writes Iceberg metadata with absolute filesystem
paths (e.g. ``/Users/jcernauske/code/bright/futureproof-data/data/...``).
Those paths get baked into:

  1. SQLite catalogs (``data/catalog/catalog.db``, ``data/iceberg_catalog.db``)
     in the ``metadata_location`` / ``previous_metadata_location`` columns.
  2. Every ``*.metadata.json`` file — ``location`` plus per-snapshot
     ``manifest-list`` paths.
  3. Every ``*.avro`` manifest list — references to manifest files.
  4. Every ``*.avro`` manifest file — references to ``*.parquet`` data files.

When the repo is cloned to any other path, all four layers point at
nonexistent files and ``iceberg_scan`` returns empty results. This script
rewrites all four layers to repo-root-relative paths (``data/bronze/...``),
which DuckDB's ``iceberg_scan`` resolves against the process CWD. After
rebasing, anyone who runs the backend from the repo root reads the data
correctly, on any machine.

Usage:
    uv run --with fastavro scripts/rebase_iceberg_paths.py --check
    uv run --with fastavro scripts/rebase_iceberg_paths.py --apply

``--check`` is read-only: it scans for any remaining absolute-path
references and exits non-zero if found. Safe to run in CI to prevent
re-introduction of absolute paths.

``--apply`` performs the rewrite in place. Each file is written via a
``.tmp`` sibling and ``os.replace`` so a crash mid-run cannot leave a
half-written file. Idempotent: re-running ``--apply`` after a clean
rebase finds nothing to change and exits 0.

When to re-run: after any pipeline run that materializes new Iceberg
snapshots locally and before committing those snapshots. The Brightsmith
ingestors will keep writing absolute paths; this script is the
last-mile normalizer.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

try:
    import fastavro
except ImportError:
    sys.stderr.write(
        "fastavro is required. Run via: "
        "uv run --with fastavro scripts/rebase_iceberg_paths.py ...\n"
    )
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

# Catalog DBs to rewrite. Empty ones are no-ops; missing ones are skipped.
CATALOG_DBS = [
    DATA_DIR / "catalog" / "catalog.db",
    DATA_DIR / "iceberg_catalog.db",
    DATA_DIR / "catalog.db",
    DATA_DIR / "bronze" / "catalog.db",
    DATA_DIR / "silver" / "catalog.db",
    DATA_DIR / "gold" / "catalog.db",
]

# Iceberg warehouses under data/. Each contains metadata/*.json and
# metadata/*.avro chains plus data/*.parquet files referenced by manifests.
WAREHOUSE_GLOB = "data/*/iceberg_warehouse"


def detect_baked_prefix() -> str | None:
    """Find the absolute path prefix baked into committed metadata.

    Reads one metadata.json and pulls the ``location`` field, then strips
    the part that lives below the repo root. Returns the host-specific
    prefix (everything *before* ``data/``) with a trailing slash, or
    ``None`` if no absolute paths are detected.
    """
    sample_files = glob.glob(
        str(REPO_ROOT / "data" / "*" / "iceberg_warehouse" / "*" / "*" / "metadata" / "*.metadata.json")
    )
    if not sample_files:
        return None
    for sample in sample_files:
        try:
            with open(sample) as f:
                meta = json.load(f)
            loc = meta.get("location", "")
        except (OSError, json.JSONDecodeError):
            continue
        if not loc or not loc.startswith("/"):
            continue
        # location ends with .../data/<zone>/iceberg_warehouse/<ns>/<table>
        # so the prefix-to-strip is everything before "data/".
        marker = "/data/"
        idx = loc.find(marker)
        if idx == -1:
            continue
        return loc[: idx + 1]  # keep trailing slash before "data/"
    return None


def rebase_sqlite(db_path: Path, old_prefix: str, *, apply: bool) -> tuple[int, int]:
    """Rewrite ``metadata_location`` / ``previous_metadata_location`` columns.

    Returns ``(rows_with_absolute_paths, rows_rewritten)``. In ``--check``
    mode the second value is always 0.
    """
    if not db_path.exists():
        return (0, 0)
    found = 0
    rewritten = 0
    con = sqlite3.connect(str(db_path))
    try:
        cur = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='iceberg_tables'"
        )
        if cur.fetchone() is None:
            return (0, 0)
        for col in ("metadata_location", "previous_metadata_location"):
            cur = con.execute(
                f"SELECT COUNT(*) FROM iceberg_tables WHERE {col} LIKE ?",
                (f"%{old_prefix}%",),
            )
            n = cur.fetchone()[0]
            found += n
            if apply and n:
                con.execute(
                    f"UPDATE iceberg_tables SET {col} = REPLACE({col}, ?, '')",
                    (old_prefix,),
                )
                rewritten += n
        if apply and rewritten:
            con.commit()
    finally:
        con.close()
    return (found, rewritten)


def rebase_json(path: Path, old_prefix: str, *, apply: bool) -> bool:
    """Rewrite a single metadata.json. Returns True if changes were made/needed."""
    with open(path) as f:
        raw = f.read()
    if old_prefix not in raw:
        return False
    if not apply:
        return True
    new_raw = raw.replace(old_prefix, "")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w") as f:
        f.write(new_raw)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return True


def _swap(value: Any, old_prefix: str) -> Any:
    """Recursively replace ``old_prefix`` in any string within a JSON-like tree."""
    if isinstance(value, str):
        return value.replace(old_prefix, "") if old_prefix in value else value
    if isinstance(value, dict):
        return {k: _swap(v, old_prefix) for k, v in value.items()}
    if isinstance(value, list):
        return [_swap(v, old_prefix) for v in value]
    return value


def rebase_avro(path: Path, old_prefix: str, *, apply: bool) -> bool:
    """Rewrite a single avro manifest/manifest-list. Returns True if changed."""
    with open(path, "rb") as f:
        reader = fastavro.reader(f)
        schema = reader.writer_schema
        codec = reader.codec
        records = list(reader)

    changed = False
    new_records = []
    for r in records:
        new_r = _swap(r, old_prefix)
        if new_r != r:
            changed = True
        new_records.append(new_r)

    if not changed:
        return False
    if not apply:
        return True

    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as f:
        fastavro.writer(f, schema, new_records, codec=codec)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Report absolute-path occurrences. Exit 1 if any are found.",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite catalogs/metadata/avro in place.",
    )
    parser.add_argument(
        "--prefix",
        help="Override the auto-detected absolute prefix to strip "
        "(must end with '/'). Useful for testing.",
    )
    args = parser.parse_args()

    if args.prefix:
        old_prefix = args.prefix
    else:
        detected = detect_baked_prefix()
        if detected is None:
            print("No absolute paths detected. Nothing to do.")
            return 0
        old_prefix = detected
    if not old_prefix.endswith("/"):
        sys.stderr.write(f"--prefix must end with '/': {old_prefix!r}\n")
        return 2

    print(f"Rebasing absolute prefix: {old_prefix!r} -> '' (repo-root-relative)")
    print(f"Mode: {'APPLY' if args.apply else 'CHECK (read-only)'}\n")

    total_db_refs = 0
    total_db_rewritten = 0
    for db in CATALOG_DBS:
        found, rewritten = rebase_sqlite(db, old_prefix, apply=args.apply)
        if found:
            print(f"  catalog: {db.relative_to(REPO_ROOT)} — {found} rows with prefix, {rewritten} rewritten")
        total_db_refs += found
        total_db_rewritten += rewritten

    json_files = glob.glob(
        str(REPO_ROOT / WAREHOUSE_GLOB / "**" / "*.metadata.json"),
        recursive=True,
    )
    json_changed = 0
    for jp in json_files:
        if rebase_json(Path(jp), old_prefix, apply=args.apply):
            json_changed += 1

    avro_files = glob.glob(
        str(REPO_ROOT / WAREHOUSE_GLOB / "**" / "*.avro"),
        recursive=True,
    )
    avro_changed = 0
    for ap in avro_files:
        if rebase_avro(Path(ap), old_prefix, apply=args.apply):
            avro_changed += 1

    print(f"\nSummary:")
    print(f"  SQLite catalog rows:    {total_db_refs} found, {total_db_rewritten} rewritten")
    print(f"  metadata.json files:    {len(json_files)} scanned, {json_changed} {'changed' if args.apply else 'need change'}")
    print(f"  avro manifest files:    {len(avro_files)} scanned, {avro_changed} {'changed' if args.apply else 'need change'}")

    total_needing_change = total_db_refs + json_changed + avro_changed
    if args.check:
        if total_needing_change > 0:
            print(f"\nCHECK FAILED: {total_needing_change} artifacts still carry absolute paths.")
            print("Run with --apply to rewrite.")
            return 1
        print("\nCHECK OK: no absolute paths remain.")
        return 0

    print(f"\nAPPLY complete. {total_needing_change} artifacts rewritten.")
    print("Re-run with --check to verify, then commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
