"""Extract golden-dataset values from consumable.career_outcomes for institution enrichment."""
from pathlib import Path
import sys
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
import brightsmith.config
brightsmith.config.configure(project_root=PROJECT_ROOT, require_human_approval=False)
from brightsmith.infra.iceberg_setup import get_catalog, read_with_duckdb

cat = get_catalog(brightsmith.config.WAREHOUSE_PATH, brightsmith.config.CATALOG_PATH)
tbl = cat.load_table("consumable.career_outcomes")
rows = read_with_duckdb(tbl)

# Known IPEDS UNITIDs with publicly verifiable Scorecard values
# MIT=166683, Princeton=186131, Stanford=243744, UC Berkeley=110635, Harvard=166027
targets = {166683: "MIT", 186131: "Princeton", 243744: "Stanford", 110635: "UC Berkeley", 166027: "Harvard"}
for r in rows:
    if r["unitid"] in targets:
        print(f"{targets[r['unitid']]} (unitid={r['unitid']}): NP={r.get('net_price_annual')}, COA={r.get('cost_of_attendance_annual')}, 4yr={r.get('net_price_4yr')}, control={r.get('institution_control')}, tuit_in={r.get('tuition_in_state')}, tuit_out={r.get('tuition_out_of_state')}, rb={r.get('room_board_on_campus')}")
        break
# Print one row per target
seen = set()
print("---individual rows (one per unitid, first occurrence):")
for r in rows:
    if r["unitid"] in targets and r["unitid"] not in seen:
        seen.add(r["unitid"])
        print(f"{targets[r['unitid']]} (unitid={r['unitid']}): NP={r.get('net_price_annual')}, COA={r.get('cost_of_attendance_annual')}, 4yr={r.get('net_price_4yr')}, control={r.get('institution_control')}")
print(f"---row count: {len(rows)}")
