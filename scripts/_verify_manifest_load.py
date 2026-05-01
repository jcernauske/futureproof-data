"""Verify the new domain/sources/ipeds_finance.yaml parses correctly via
the Brightsmith SourceConfig loader path.  Pre-existing manifest issue:
domain/sources/onet.yaml lacks a top-level `table:` (multi-table layout),
so load_manifest() raises KeyError on the whole manifest. This helper
parses just the IPEDS Finance source-config in isolation, the way the
ingest runner constructs its in-line SourceConfig.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import yaml

from brightsmith.domain_loader import _load_source_config


def main() -> int:
    cfg = _load_source_config(
        {"source_config": "domain/sources/ipeds_finance.yaml"},
        PROJECT_ROOT,
    )
    print(f"name: {cfg.name}")
    print(f"namespace: {cfg.namespace}")
    print(f"table: {cfg.table}")
    print(f"full_table_name: {cfg.full_table_name}")
    print(f"dedup_grain: {cfg.dedup_grain}")
    print(f"entities: {cfg.entities}")
    print(f"cache_dir: {cfg.cache_dir}")
    print(f"fetch keys: {sorted(cfg.fetch.keys())}")

    # Spot-check the manifest entry exists in domain/manifest.yaml
    manifest_path = PROJECT_ROOT / "domain" / "manifest.yaml"
    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)
    sources = manifest.get("sources", [])
    ipf = [s for s in sources if s["name"] == "ipeds_finance"]
    print(f"manifest sources count: {len(sources)}")
    print(f"ipeds_finance manifest entry: {ipf}")

    return 0 if ipf and cfg.full_table_name == "bronze.ipeds_finance" else 1


if __name__ == "__main__":
    raise SystemExit(main())
