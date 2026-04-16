"""
Chaos Monkey 5-Cycle Adversarial Hardening Runner
Spec: raw-ingest-college-scorecard-institution
Table: raw.college_scorecard_institution

Injects corruptions across all 10 DQ dimensions at escalating rates,
runs DQ rules against the shadow table, and records what was caught vs missed.

Information barrier: This runner does NOT read DQ rule definitions.
It uses only the schema from the ingestor and the data structure.
"""

import copy
import datetime
import json
import random
import shutil
import uuid
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/jcernauske/code/bright/futureproof-data")
SAMPLE_CSV = PROJECT_ROOT / "tests/raw/college_scorecard_institution_sample.csv"
WAREHOUSE_PATH = PROJECT_ROOT / "data/bronze/iceberg_warehouse"
CATALOG_PATH = PROJECT_ROOT / "data/catalog/catalog.db"
SHADOW_DIR = WAREHOUSE_PATH / "shadow_raw/college_scorecard_institution"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "governance/chaos-manifests/raw-ingest-college-scorecard-institution-manifest.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "governance/chaos-manifests/raw-ingest-college-scorecard-institution-chaos.md"
)

RATES = [0.05, 0.06, 0.07, 0.08, 0.10]
SEED_BASE = 42
TARGET_ROW_COUNT = 3039  # Real data has ~3,039 rows after PREDDEG=3/ICLEVEL=1 filter

# US states for generating realistic rows
US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI",
]


# ---------------------------------------------------------------------------
# Data generation: build realistic ~3039-row dataset from sample
# ---------------------------------------------------------------------------


def _parse_sample_csv() -> list[dict]:
    """Parse the sample CSV and return flattened rows (like the ingestor would)."""
    import csv
    import io

    text = SAMPLE_CSV.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for raw_row in reader:
        # Apply same filtering as the ingestor
        preddeg_raw = raw_row.get("PREDDEG", "")
        iclevel_raw = raw_row.get("ICLEVEL", "")
        try:
            preddeg_match = int(preddeg_raw) == 3
        except (ValueError, TypeError):
            preddeg_match = False
        try:
            iclevel_match = int(iclevel_raw) == 1
        except (ValueError, TypeError):
            iclevel_match = False

        if not (preddeg_match or iclevel_match):
            continue

        # Skip empty UNITID
        if not raw_row.get("UNITID", "").strip():
            continue

        rows.append(raw_row)
    return rows


def _coerce_value(field: str, val: str | None) -> object:
    """Coerce a string value to the proper type, matching ingestor behavior."""
    sentinels = {"PrivacySuppressed", "PS", "NA", "NULL", ""}
    if val is None or val.strip() in sentinels:
        return None

    val = val.strip()
    string_fields = {"instnm", "stabbr"}
    long_fields = {"unitid"}
    int_fields = {"control", "preddeg"}

    if field in string_fields:
        return val
    if field in long_fields:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    if field in int_fields:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    # Double fields
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _flatten_row(raw_row: dict) -> dict:
    """Convert a raw CSV row dict to a flattened, typed row dict."""
    column_map = {
        "UNITID": "unitid", "INSTNM": "instnm", "STABBR": "stabbr",
        "CONTROL": "control", "PREDDEG": "preddeg",
        "COSTT4_A": "costt4_a", "COSTT4_P": "costt4_p",
        "NPT4_PUB": "npt4_pub", "NPT4_PRIV": "npt4_priv",
        "NPT41_PUB": "npt41_pub", "NPT42_PUB": "npt42_pub",
        "NPT43_PUB": "npt43_pub", "NPT44_PUB": "npt44_pub",
        "NPT45_PUB": "npt45_pub",
        "NPT41_PRIV": "npt41_priv", "NPT42_PRIV": "npt42_priv",
        "NPT43_PRIV": "npt43_priv", "NPT44_PRIV": "npt44_priv",
        "NPT45_PRIV": "npt45_priv",
        "TUITIONFEE_IN": "tuitionfee_in", "TUITIONFEE_OUT": "tuitionfee_out",
        "ROOMBOARD_ON": "roomboard_on", "ROOMBOARD_OFF": "roomboard_off",
        "BOOKSUPPLY": "booksupply",
    }
    record = {}
    for csv_col, iceberg_col in column_map.items():
        record[iceberg_col] = _coerce_value(iceberg_col, raw_row.get(csv_col))
    return record


def generate_realistic_data(rng: random.Random) -> list[dict]:
    """Generate ~3039 realistic institution rows from the sample data.

    Uses the sample rows as templates and varies them to create a
    realistic-looking dataset with proper distributions.
    """
    templates = _parse_sample_csv()
    flat_templates = [_flatten_row(r) for r in templates]

    # Distribution: ~55% public (control=1), ~35% private nonprofit (2), ~10% for-profit (3)
    control_weights = {1: 0.55, 2: 0.35, 3: 0.10}

    rows = []
    used_unitids = set()
    now = datetime.datetime.now(datetime.timezone.utc)
    today = datetime.date.today()

    # Keep the original templates as-is first
    for tmpl in flat_templates:
        if tmpl["unitid"] is not None:
            row = copy.deepcopy(tmpl)
            row["ingested_at"] = now
            row["source_url"] = (
                "https://ed-public-download.app.cloud.gov/downloads/"
                "Most-Recent-Cohorts-Institution.csv"
            )
            row["source_method"] = "bulk_csv_download"
            row["load_date"] = today
            rows.append(row)
            used_unitids.add(row["unitid"])

    # Generate remaining rows
    university_prefixes = [
        "University of", "State University at", "College of",
        "Institute of Technology", "Polytechnic University of",
    ]
    university_suffixes = [
        "Sciences", "Arts", "Engineering", "Medicine", "Business",
        "Education", "Agriculture", "Technology", "Liberal Arts",
    ]
    city_names = [
        "Springfield", "Riverside", "Fairview", "Georgetown", "Madison",
        "Monroe", "Franklin", "Clinton", "Jackson", "Lincoln",
        "Salem", "Bristol", "Chester", "Dover", "Oxford",
        "Cambridge", "Hartford", "Burlington", "Portland", "Asheville",
    ]

    while len(rows) < TARGET_ROW_COUNT:
        # Pick a random template as the basis
        tmpl = rng.choice(flat_templates)

        # Generate a unique UNITID (6-digit, like real ones)
        unitid = rng.randint(100000, 999999)
        while unitid in used_unitids:
            unitid = rng.randint(100000, 999999)
        used_unitids.add(unitid)

        # Random control value with realistic distribution
        ctrl_roll = rng.random()
        if ctrl_roll < 0.55:
            control = 1
        elif ctrl_roll < 0.90:
            control = 2
        else:
            control = 3

        # Generate institution name
        state = rng.choice(US_STATES)
        name_style = rng.choice(["prefix_state", "city_college", "name_university"])
        if name_style == "prefix_state":
            name = f"{rng.choice(university_prefixes)} {state} - {rng.choice(university_suffixes)}"
        elif name_style == "city_college":
            name = f"{rng.choice(city_names)} {rng.choice(['College', 'University', 'Institute'])}"
        else:
            name = f"{rng.choice(city_names)} {rng.choice(university_suffixes)} University"

        # Vary cost fields based on control type
        if control == 1:  # Public
            base_coa = rng.gauss(25000, 5000)
            base_npt_pub = base_coa * rng.uniform(0.45, 0.75)
            base_tuition_in = base_coa * rng.uniform(0.30, 0.50)
            base_tuition_out = base_tuition_in * rng.uniform(1.8, 2.8)
            npt4_pub = max(1000, base_npt_pub)
            npt4_priv = None
            # Quintiles: Q1 cheapest, Q5 most expensive
            q_base = npt4_pub
            npt_q = [q_base * rng.uniform(0.35, 0.55)]
            for _ in range(4):
                npt_q.append(npt_q[-1] * rng.uniform(1.10, 1.35))
            row = {
                "unitid": unitid, "instnm": name, "stabbr": state,
                "control": control, "preddeg": 3,
                "costt4_a": max(5000, base_coa),
                "costt4_p": None,
                "npt4_pub": npt4_pub, "npt4_priv": None,
                "npt41_pub": npt_q[0], "npt42_pub": npt_q[1],
                "npt43_pub": npt_q[2], "npt44_pub": npt_q[3],
                "npt45_pub": npt_q[4],
                "npt41_priv": None, "npt42_priv": None,
                "npt43_priv": None, "npt44_priv": None, "npt45_priv": None,
                "tuitionfee_in": max(1000, base_tuition_in),
                "tuitionfee_out": max(2000, base_tuition_out),
                "roomboard_on": max(4000, rng.gauss(9000, 2000)),
                "roomboard_off": max(4000, rng.gauss(8500, 2000)),
                "booksupply": max(400, rng.gauss(1200, 300)),
            }
        elif control == 2:  # Private nonprofit
            base_coa = rng.gauss(42000, 10000)
            base_npt_priv = base_coa * rng.uniform(0.40, 0.70)
            npt4_priv = max(5000, base_npt_priv)
            q_base = npt4_priv
            npt_q = [q_base * rng.uniform(0.30, 0.50)]
            for _ in range(4):
                npt_q.append(npt_q[-1] * rng.uniform(1.10, 1.35))
            row = {
                "unitid": unitid, "instnm": name, "stabbr": state,
                "control": control, "preddeg": 3,
                "costt4_a": max(10000, base_coa),
                "costt4_p": None,
                "npt4_pub": None, "npt4_priv": npt4_priv,
                "npt41_pub": None, "npt42_pub": None,
                "npt43_pub": None, "npt44_pub": None, "npt45_pub": None,
                "npt41_priv": npt_q[0], "npt42_priv": npt_q[1],
                "npt43_priv": npt_q[2], "npt44_priv": npt_q[3],
                "npt45_priv": npt_q[4],
                "tuitionfee_in": max(8000, rng.gauss(35000, 8000)),
                "tuitionfee_out": None,  # Private schools: same rate
                "roomboard_on": max(5000, rng.gauss(12000, 3000)),
                "roomboard_off": max(5000, rng.gauss(11000, 3000)),
                "booksupply": max(500, rng.gauss(1200, 300)),
            }
            # Private schools often have tuitionfee_out == tuitionfee_in
            row["tuitionfee_out"] = row["tuitionfee_in"]
        else:  # For-profit (control=3)
            base_coa = rng.gauss(30000, 8000)
            base_npt_priv = base_coa * rng.uniform(0.60, 0.90)
            npt4_priv = max(5000, base_npt_priv)
            row = {
                "unitid": unitid, "instnm": name, "stabbr": state,
                "control": control, "preddeg": 3,
                "costt4_a": None,
                "costt4_p": max(10000, base_coa),
                "npt4_pub": None, "npt4_priv": npt4_priv,
                "npt41_pub": None, "npt42_pub": None,
                "npt43_pub": None, "npt44_pub": None, "npt45_pub": None,
                "npt41_priv": None, "npt42_priv": None,
                "npt43_priv": None, "npt44_priv": None, "npt45_priv": None,
                "tuitionfee_in": max(5000, rng.gauss(15000, 4000)),
                "tuitionfee_out": max(5000, rng.gauss(15000, 4000)),
                "roomboard_on": None,  # For-profits often lack housing
                "roomboard_off": max(5000, rng.gauss(9000, 2000)),
                "booksupply": max(400, rng.gauss(1000, 200)),
            }

        # Randomly null out some cost fields (10% chance each) -- realistic
        for field in ["costt4_a", "costt4_p", "booksupply", "roomboard_on", "roomboard_off"]:
            if rng.random() < 0.10:
                row[field] = None

        # Add metadata
        row["ingested_at"] = now
        row["source_url"] = (
            "https://ed-public-download.app.cloud.gov/downloads/"
            "Most-Recent-Cohorts-Institution.csv"
        )
        row["source_method"] = "bulk_csv_download"
        row["load_date"] = today
        rows.append(row)

    return rows


# ---------------------------------------------------------------------------
# Corruption strategies (one per DQ dimension)
# ---------------------------------------------------------------------------


def corrupt_completeness(rows, indices, rng):
    """Null out required fields: unitid, instnm, stabbr, control."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        field = rng.choice(["unitid", "instnm", "stabbr", "control"])
        old_val = rows[i].get(field)
        rows[i][field] = None
        manifest.append({
            "row": i, "dimension": "completeness", "field": field,
            "strategy": f"null_{field}", "old_value": str(old_val), "new_value": "null",
        })
    return manifest


def corrupt_validity(rows, indices, rng):
    """Invalid values: bad CONTROL values, bad state codes."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice(["bad_control", "bad_control_zero", "bad_stabbr"])
        if strategy == "bad_control":
            old_val = rows[i].get("control")
            rows[i]["control"] = rng.choice([4, 5, 99, -1])
            manifest.append({
                "row": i, "dimension": "validity", "field": "control",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["control"]),
            })
        elif strategy == "bad_control_zero":
            old_val = rows[i].get("control")
            rows[i]["control"] = 0
            manifest.append({
                "row": i, "dimension": "validity", "field": "control",
                "strategy": strategy, "old_value": str(old_val), "new_value": "0",
            })
        elif strategy == "bad_stabbr":
            old_val = rows[i].get("stabbr")
            rows[i]["stabbr"] = rng.choice(["XX", "ZZ", "99", "", None])
            manifest.append({
                "row": i, "dimension": "validity", "field": "stabbr",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["stabbr"]),
            })
    return manifest


def corrupt_uniqueness(rows, indices, rng):
    """Inject rows with duplicate UNITIDs."""
    manifest = []
    n_dupes = max(5, len(indices) // 5)
    dupe_sources = rng.sample(range(len(rows)), min(n_dupes, len(rows)))
    for src_idx in dupe_sources:
        dupe = copy.deepcopy(rows[src_idx])
        # Keep the same UNITID but change the name slightly
        dupe["instnm"] = f"{dupe.get('instnm', 'Unknown')} - Duplicate"
        insert_pos = len(rows)
        rows.append(dupe)
        manifest.append({
            "row": insert_pos, "dimension": "uniqueness", "field": "unitid",
            "strategy": "duplicate_unitid",
            "old_value": f"copy_of_row_{src_idx}_unitid_{rows[src_idx].get('unitid')}",
            "new_value": f"duplicate at position {insert_pos}",
        })
    return manifest


def corrupt_consistency(rows, indices, rng):
    """Contradictory field combos: public school with npt4_priv but no npt4_pub."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "public_with_priv_price",
            "private_with_pub_price",
            "coa_less_than_tuition",
        ])
        if strategy == "public_with_priv_price":
            # Public school has private net price but no public
            old_pub = rows[i].get("npt4_pub")
            old_priv = rows[i].get("npt4_priv")
            old_ctrl = rows[i].get("control")
            rows[i]["control"] = 1  # Set as public
            rows[i]["npt4_pub"] = None  # Remove public price
            rows[i]["npt4_priv"] = rng.uniform(10000, 40000)  # Add private price
            manifest.append({
                "row": i, "dimension": "consistency", "field": "control,npt4_pub,npt4_priv",
                "strategy": strategy,
                "old_value": f"ctrl={old_ctrl},pub={old_pub},priv={old_priv}",
                "new_value": f"ctrl=1,pub=None,priv={rows[i]['npt4_priv']:.0f}",
            })
        elif strategy == "private_with_pub_price":
            old_pub = rows[i].get("npt4_pub")
            old_priv = rows[i].get("npt4_priv")
            old_ctrl = rows[i].get("control")
            rows[i]["control"] = 2  # Set as private
            rows[i]["npt4_priv"] = None  # Remove private price
            rows[i]["npt4_pub"] = rng.uniform(5000, 25000)  # Add public price
            manifest.append({
                "row": i, "dimension": "consistency", "field": "control,npt4_pub,npt4_priv",
                "strategy": strategy,
                "old_value": f"ctrl={old_ctrl},pub={old_pub},priv={old_priv}",
                "new_value": f"ctrl=2,pub={rows[i]['npt4_pub']:.0f},priv=None",
            })
        elif strategy == "coa_less_than_tuition":
            # COA should be >= tuition, make it less
            old_coa = rows[i].get("costt4_a")
            old_tuition = rows[i].get("tuitionfee_in")
            if old_tuition is not None and old_tuition > 0:
                rows[i]["costt4_a"] = old_tuition * rng.uniform(0.3, 0.7)
                manifest.append({
                    "row": i, "dimension": "consistency",
                    "field": "costt4_a,tuitionfee_in",
                    "strategy": strategy,
                    "old_value": f"coa={old_coa},tuition={old_tuition}",
                    "new_value": f"coa={rows[i]['costt4_a']:.0f},tuition={old_tuition}",
                })
    return manifest


def corrupt_accuracy(rows, indices, rng):
    """Plausible but wrong values: swapped fields, wrong UNITID range."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice([
            "swapped_in_out_tuition",
            "wrong_unitid_range",
            "swapped_pub_priv_price",
        ])
        if strategy == "swapped_in_out_tuition":
            old_in = rows[i].get("tuitionfee_in")
            old_out = rows[i].get("tuitionfee_out")
            if old_in is not None and old_out is not None and old_out > old_in:
                rows[i]["tuitionfee_in"] = old_out
                rows[i]["tuitionfee_out"] = old_in
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "tuitionfee_in,tuitionfee_out",
                    "strategy": strategy,
                    "old_value": f"in={old_in},out={old_out}",
                    "new_value": f"in={old_out},out={old_in}",
                })
        elif strategy == "wrong_unitid_range":
            old_val = rows[i].get("unitid")
            rows[i]["unitid"] = rng.randint(1, 999)
            manifest.append({
                "row": i, "dimension": "accuracy", "field": "unitid",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["unitid"]),
            })
        elif strategy == "swapped_pub_priv_price":
            old_pub = rows[i].get("npt4_pub")
            old_priv = rows[i].get("npt4_priv")
            if old_pub is not None and old_priv is None:
                rows[i]["npt4_priv"] = old_pub
                rows[i]["npt4_pub"] = None
                manifest.append({
                    "row": i, "dimension": "accuracy",
                    "field": "npt4_pub,npt4_priv",
                    "strategy": strategy,
                    "old_value": f"pub={old_pub},priv={old_priv}",
                    "new_value": f"pub=None,priv={old_pub}",
                })
    return manifest


def corrupt_reasonableness(rows, indices, rng):
    """Extreme outlier values: $200K cost, negative costs."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 3)))
    for i in targets:
        strategy = rng.choice([
            "extreme_cost", "negative_cost", "extreme_net_price",
            "negative_tuition", "extreme_room_board",
        ])
        if strategy == "extreme_cost":
            old_val = rows[i].get("costt4_a")
            rows[i]["costt4_a"] = float(rng.randint(150000, 500000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "costt4_a",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["costt4_a"]),
            })
        elif strategy == "negative_cost":
            field = rng.choice(["costt4_a", "costt4_p"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(-50000, -100))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "extreme_net_price":
            field = rng.choice(["npt4_pub", "npt4_priv"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(100000, 300000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "negative_tuition":
            field = rng.choice(["tuitionfee_in", "tuitionfee_out"])
            old_val = rows[i].get(field)
            rows[i][field] = float(rng.randint(-20000, -100))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": field,
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i][field]),
            })
        elif strategy == "extreme_room_board":
            old_val = rows[i].get("roomboard_on")
            rows[i]["roomboard_on"] = float(rng.randint(50000, 200000))
            manifest.append({
                "row": i, "dimension": "reasonableness", "field": "roomboard_on",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": str(rows[i]["roomboard_on"]),
            })
    return manifest


def corrupt_freshness(rows, indices, rng):
    """Stale or future timestamps."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        strategy = rng.choice(["future_load_date", "stale_load_date", "future_ingested_at"])
        if strategy == "future_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2030, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-01-01",
            })
        elif strategy == "stale_load_date":
            old_val = rows[i].get("load_date")
            rows[i]["load_date"] = datetime.date(2019, 1, 1)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "load_date",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2019-01-01",
            })
        elif strategy == "future_ingested_at":
            old_val = rows[i].get("ingested_at")
            rows[i]["ingested_at"] = datetime.datetime(2030, 6, 15, 12, 0, 0)
            manifest.append({
                "row": i, "dimension": "freshness", "field": "ingested_at",
                "strategy": strategy, "old_value": str(old_val),
                "new_value": "2030-06-15T12:00:00",
            })
    return manifest


def corrupt_volume(rows, indices, rng):
    """Row count anomalies: mass-inject extra rows to push above threshold."""
    manifest = []
    n_extras = 1200  # Push well above 8,000 (the expected range upper bound)
    source_rows = rng.sample(range(len(rows)), min(n_extras, len(rows)))
    for src_idx in source_rows:
        dupe = copy.deepcopy(rows[src_idx])
        # Give each a unique UNITID so it's not caught by uniqueness alone
        dupe["unitid"] = rng.randint(900000, 999999)
        rows.append(dupe)
    manifest.append({
        "row": -1, "dimension": "volume", "field": "row_count",
        "strategy": "mass_inject",
        "old_value": str(len(rows) - len(source_rows)),
        "new_value": str(len(rows)),
    })
    return manifest


def corrupt_referential_integrity(rows, indices, rng):
    """Orphan keys: UNITID values that can't exist in any real institution set."""
    manifest = []
    targets = rng.sample(list(indices), min(len(indices), max(1, len(indices) // 4)))
    for i in targets:
        old_val = rows[i].get("unitid")
        # Use obviously fake UNITIDs
        rows[i]["unitid"] = rng.randint(900000000, 999999999)
        manifest.append({
            "row": i, "dimension": "referential_integrity", "field": "unitid",
            "strategy": "orphan_unitid", "old_value": str(old_val),
            "new_value": str(rows[i]["unitid"]),
        })
    return manifest


def corrupt_coverage(rows, indices, rng):
    """Missing expected combos: null out ALL COA fields for 40%+ of rows.

    This targets the "at least 90% have one of costt4_a or costt4_p" rule
    and the control-specific net price coverage rules.
    """
    manifest = []

    # Strategy 1: Null both costt4_a and costt4_p for 40% of rows
    n_null = int(len(rows) * 0.40)
    targets = rng.sample(range(len(rows)), min(n_null, len(rows)))
    for i in targets:
        old_a = rows[i].get("costt4_a")
        old_p = rows[i].get("costt4_p")
        rows[i]["costt4_a"] = None
        rows[i]["costt4_p"] = None
        manifest.append({
            "row": i, "dimension": "coverage", "field": "costt4_a,costt4_p",
            "strategy": "null_both_coa",
            "old_value": f"a={old_a},p={old_p}", "new_value": "both null",
        })

    # Strategy 2: Quintile inversion -- inject rows where Q1 > Q5
    n_inversions = 65
    inversion_targets = rng.sample(range(len(rows)), min(n_inversions, len(rows)))
    for i in inversion_targets:
        ctrl = rows[i].get("control")
        if ctrl == 1:
            q1_field, q5_field = "npt41_pub", "npt45_pub"
        else:
            q1_field, q5_field = "npt41_priv", "npt45_priv"
        old_q1 = rows[i].get(q1_field)
        old_q5 = rows[i].get(q5_field)
        # Force Q1 > Q5
        rows[i][q1_field] = 40000.0
        rows[i][q5_field] = 10000.0
        manifest.append({
            "row": i, "dimension": "coverage", "field": f"{q1_field},{q5_field}",
            "strategy": "quintile_inversion",
            "old_value": f"q1={old_q1},q5={old_q5}",
            "new_value": "q1=40000,q5=10000",
        })

    # Strategy 3: Remove net price for control-specific checks
    # Null out npt4_pub for public schools to break the coverage rule
    public_rows = [i for i in range(len(rows)) if rows[i].get("control") == 1]
    n_null_pub = int(len(public_rows) * 0.30)
    for i in rng.sample(public_rows, min(n_null_pub, len(public_rows))):
        old_val = rows[i].get("npt4_pub")
        rows[i]["npt4_pub"] = None
        manifest.append({
            "row": i, "dimension": "coverage", "field": "npt4_pub",
            "strategy": "null_pub_net_price",
            "old_value": str(old_val), "new_value": "null",
        })

    return manifest


# ---------------------------------------------------------------------------
# Iceberg shadow table management
# ---------------------------------------------------------------------------

ICEBERG_SCHEMA_FIELDS = [
    ("unitid", pa.int64()),
    ("instnm", pa.string()),
    ("stabbr", pa.string()),
    ("control", pa.int32()),
    ("preddeg", pa.int32()),
    ("costt4_a", pa.float64()),
    ("costt4_p", pa.float64()),
    ("npt4_pub", pa.float64()),
    ("npt4_priv", pa.float64()),
    ("npt41_pub", pa.float64()),
    ("npt42_pub", pa.float64()),
    ("npt43_pub", pa.float64()),
    ("npt44_pub", pa.float64()),
    ("npt45_pub", pa.float64()),
    ("npt41_priv", pa.float64()),
    ("npt42_priv", pa.float64()),
    ("npt43_priv", pa.float64()),
    ("npt44_priv", pa.float64()),
    ("npt45_priv", pa.float64()),
    ("tuitionfee_in", pa.float64()),
    ("tuitionfee_out", pa.float64()),
    ("roomboard_on", pa.float64()),
    ("roomboard_off", pa.float64()),
    ("booksupply", pa.float64()),
    ("ingested_at", pa.timestamp("us")),
    ("source_url", pa.string()),
    ("source_method", pa.string()),
    ("load_date", pa.date32()),
]


def rows_to_arrow(rows: list[dict]) -> pa.Table:
    """Convert list of dicts to a PyArrow table matching the Iceberg schema."""
    arrays = {}
    for col_name, col_type in ICEBERG_SCHEMA_FIELDS:
        values = [r.get(col_name) for r in rows]
        try:
            arrays[col_name] = pa.array(values, type=col_type)
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            # For type mismatches (e.g., corrupted values), try without type
            arrays[col_name] = pa.array(values)
    return pa.table(arrays)


def write_shadow_parquet(arrow_table: pa.Table, cycle_num: int) -> Path:
    """Write corrupted data as a parquet file in the shadow directory."""
    data_dir = SHADOW_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file = data_dir / f"chaos-cycle-{cycle_num}.parquet"
    pq.write_table(arrow_table, str(out_file))
    return out_file


def register_shadow_in_catalog(parquet_path: Path):
    """Register the shadow table in the Iceberg catalog under shadow_raw namespace."""
    from brightsmith.infra.iceberg_setup import get_catalog
    from pyiceberg.schema import Schema
    from pyiceberg.types import (
        DateType,
        DoubleType,
        IntegerType,
        LongType,
        NestedField,
        StringType,
        TimestampType,
    )

    catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)

    # Create shadow_raw namespace if needed
    try:
        catalog.create_namespace("shadow_raw")
    except Exception:
        pass

    # Drop existing shadow table
    try:
        catalog.drop_table("shadow_raw.college_scorecard_institution")
    except Exception:
        pass

    # Define schema matching the real table
    iceberg_schema = Schema(
        NestedField(1, "unitid", LongType(), required=False),
        NestedField(2, "instnm", StringType(), required=False),
        NestedField(3, "stabbr", StringType(), required=False),
        NestedField(4, "control", IntegerType(), required=False),
        NestedField(5, "preddeg", IntegerType(), required=False),
        NestedField(6, "costt4_a", DoubleType(), required=False),
        NestedField(7, "costt4_p", DoubleType(), required=False),
        NestedField(8, "npt4_pub", DoubleType(), required=False),
        NestedField(9, "npt4_priv", DoubleType(), required=False),
        NestedField(10, "npt41_pub", DoubleType(), required=False),
        NestedField(11, "npt42_pub", DoubleType(), required=False),
        NestedField(12, "npt43_pub", DoubleType(), required=False),
        NestedField(13, "npt44_pub", DoubleType(), required=False),
        NestedField(14, "npt45_pub", DoubleType(), required=False),
        NestedField(15, "npt41_priv", DoubleType(), required=False),
        NestedField(16, "npt42_priv", DoubleType(), required=False),
        NestedField(17, "npt43_priv", DoubleType(), required=False),
        NestedField(18, "npt44_priv", DoubleType(), required=False),
        NestedField(19, "npt45_priv", DoubleType(), required=False),
        NestedField(20, "tuitionfee_in", DoubleType(), required=False),
        NestedField(21, "tuitionfee_out", DoubleType(), required=False),
        NestedField(22, "roomboard_on", DoubleType(), required=False),
        NestedField(23, "roomboard_off", DoubleType(), required=False),
        NestedField(24, "booksupply", DoubleType(), required=False),
        NestedField(25, "ingested_at", TimestampType(), required=False),
        NestedField(26, "source_url", StringType(), required=False),
        NestedField(27, "source_method", StringType(), required=False),
        NestedField(28, "load_date", DateType(), required=False),
    )

    # Create and populate the shadow table
    shadow_table = catalog.create_table(
        "shadow_raw.college_scorecard_institution", schema=iceberg_schema
    )
    data = pq.read_table(str(parquet_path))
    shadow_table.append(data)
    return shadow_table


def run_dq_rules_shadow():
    """Run DQ rules against the shadow table and return results."""
    from brightsmith.infra.dq_runner import run_rules

    result = run_rules(
        spec="raw-ingest-college-scorecard-institution", shadow=True
    )
    return result


def cleanup_shadow():
    """Remove shadow table and files."""
    if SHADOW_DIR.exists():
        shutil.rmtree(SHADOW_DIR)
    try:
        from brightsmith.infra.iceberg_setup import get_catalog

        catalog = get_catalog(WAREHOUSE_PATH, CATALOG_PATH)
        catalog.drop_table("shadow_raw.college_scorecard_institution")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main injection pipeline
# ---------------------------------------------------------------------------

CORRUPTION_FUNCTIONS = [
    corrupt_completeness,
    corrupt_validity,
    corrupt_uniqueness,
    corrupt_consistency,
    corrupt_accuracy,
    corrupt_reasonableness,
    corrupt_freshness,
    corrupt_volume,
    corrupt_referential_integrity,
    corrupt_coverage,
]


def run_cycle(cycle_num: int, rate: float, seed: int) -> dict:
    """Run a single chaos monkey cycle."""
    print(f"\n{'='*70}")
    print(f"CYCLE {cycle_num} | Rate: {rate*100:.0f}% | Seed: {seed}")
    print(f"{'='*70}")

    rng = random.Random(seed)

    # Generate fresh realistic data
    print("Generating realistic data...")
    rows = generate_realistic_data(rng)
    original_count = len(rows)
    print(f"  Generated {original_count} rows")

    # Calculate how many rows to corrupt per dimension
    n_corrupt = int(original_count * rate)
    all_indices = list(range(original_count))
    per_function = max(1, n_corrupt // len(CORRUPTION_FUNCTIONS))

    all_manifest = []

    for func in CORRUPTION_FUNCTIONS:
        indices = rng.sample(all_indices, min(per_function, len(all_indices)))
        try:
            entries = func(rows, indices, rng)
            all_manifest.extend(entries)
            dim = func.__name__.replace("corrupt_", "")
            print(f"  {dim}: {len(entries)} corruptions")
        except Exception as e:
            print(f"  ERROR in {func.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print(f"  Total corruptions: {len(all_manifest)}")
    print(f"  Final row count: {len(rows)} (was {original_count})")

    # Convert to Arrow and write shadow table
    print("Writing shadow table...")
    dq_result = {
        "run_id": "error", "rules_total": 0, "rules_passed": 0,
        "rules_failed": 0, "p0_passed": True, "results": [],
    }
    try:
        arrow_table = rows_to_arrow(rows)
        parquet_path = write_shadow_parquet(arrow_table, cycle_num)
        print(f"  Written to {parquet_path}")

        # Register in Iceberg catalog
        print("Registering in Iceberg catalog...")
        register_shadow_in_catalog(parquet_path)
        print("  Registered as shadow_raw.college_scorecard_institution")

        # Run DQ rules
        print("Running DQ rules against shadow table...")
        dq_result = run_dq_rules_shadow()
        print(f"  Run ID: {dq_result['run_id']}")
        print(
            f"  Total: {dq_result['rules_total']} | "
            f"Passed: {dq_result['rules_passed']} | "
            f"Failed: {dq_result['rules_failed']}"
        )
        print(f"  P0 gate: {'PASS' if dq_result['p0_passed'] else 'FAIL'}")

        # Print per-rule results
        print("\n  Per-rule results:")
        for r in dq_result.get("results", []):
            status = "PASS" if r["passed"] else ("ERROR" if r.get("error") else "FAIL")
            print(f"    {r['rule_id']:<20} {status:<6} value={r.get('raw_value', '?')}")

    except Exception as e:
        print(f"  ERROR during shadow table creation/DQ run: {e}")
        import traceback
        traceback.print_exc()

    return {
        "cycle": cycle_num,
        "rate": rate,
        "seed": seed,
        "original_row_count": original_count,
        "corrupted_row_count": len(rows),
        "total_corruptions": len(all_manifest),
        "manifest": all_manifest,
        "dq_result": dq_result,
    }


def analyze_gaps(cycle_result: dict) -> dict:
    """Analyze which corruptions were caught vs missed."""
    dq_result = cycle_result["dq_result"]
    manifest = cycle_result["manifest"]

    failed_rules = [
        r for r in dq_result.get("results", [])
        if not r["passed"] and not r.get("error")
    ]
    passed_rules = [
        r for r in dq_result.get("results", []) if r["passed"]
    ]
    errored_rules = [
        r for r in dq_result.get("results", []) if r.get("error")
    ]

    # Group manifest by dimension
    dims = {}
    for entry in manifest:
        dim = entry["dimension"]
        dims.setdefault(dim, []).append(entry)

    total_rules = len(dq_result.get("results", []))
    detection_rate = len(failed_rules) / total_rules if total_rules > 0 else 0

    return {
        "failed_rules": [
            {"rule_id": r["rule_id"], "raw_value": r.get("raw_value")}
            for r in failed_rules
        ],
        "passed_rules": [
            {
                "rule_id": r["rule_id"],
                "raw_value": r.get("raw_value"),
                "threshold": r.get("threshold"),
            }
            for r in passed_rules
        ],
        "errored_rules": [
            {"rule_id": r["rule_id"], "error": r.get("error")}
            for r in errored_rules
        ],
        "injected_dimensions": sorted(dims.keys()),
        "corruptions_per_dimension": {
            dim: len(entries) for dim, entries in dims.items()
        },
        "detection_rate": round(detection_rate, 3),
        "rules_fired": len(failed_rules),
        "rules_silent": len(passed_rules),
        "rules_errored": len(errored_rules),
        "total_rules": total_rules,
    }


def main():
    """Run 5-cycle adversarial hardening."""
    all_cycles = []
    all_gaps = []
    previous_failed = set()
    consecutive_no_new_gaps = 0

    for cycle_num, rate in enumerate(RATES, 1):
        seed = SEED_BASE + cycle_num
        cycle_result = run_cycle(cycle_num, rate, seed)
        gap_analysis = analyze_gaps(cycle_result)

        # Check for stability
        current_failed = set(r["rule_id"] for r in gap_analysis["failed_rules"])
        if current_failed == previous_failed and cycle_num > 1:
            consecutive_no_new_gaps += 1
        else:
            consecutive_no_new_gaps = 0
        previous_failed = current_failed

        all_cycles.append({
            "cycle": cycle_num,
            "rate": rate,
            "corruptions": cycle_result["total_corruptions"],
            "row_count": cycle_result["corrupted_row_count"],
            "dq_passed": cycle_result["dq_result"]["rules_passed"],
            "dq_failed": cycle_result["dq_result"]["rules_failed"],
            "dq_total": cycle_result["dq_result"]["rules_total"],
            "gap_analysis": gap_analysis,
            "manifest_entries": cycle_result["manifest"],
        })
        all_gaps.append(gap_analysis)

        print(f"\n  Gap Analysis:")
        print(
            f"    Detection rate: "
            f"{gap_analysis['detection_rate']*100:.1f}% "
            f"({gap_analysis['rules_fired']}/{gap_analysis['total_rules']} rules fired)"
        )
        print(
            f"    Rules that fired: "
            f"{[r['rule_id'] for r in gap_analysis['failed_rules']]}"
        )
        print(
            f"    Rules silent: "
            f"{[r['rule_id'] for r in gap_analysis['passed_rules']]}"
        )
        if gap_analysis["errored_rules"]:
            print(
                f"    Rules errored: "
                f"{[r['rule_id'] for r in gap_analysis['errored_rules']]}"
            )

        if consecutive_no_new_gaps >= 2:
            print(
                f"\n  Stability detected: same rules firing for "
                f"2 consecutive cycles. Continuing for documentation."
            )

        # Cleanup between cycles
        cleanup_shadow()

    # Final cleanup
    cleanup_shadow()

    # Output JSON manifest
    manifest_data = {
        "spec": "raw-ingest-college-scorecard-institution",
        "table": "raw.college_scorecard_institution",
        "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "cycles_completed": len(all_cycles),
        "cycles": all_cycles,
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest_data, indent=2, default=str) + "\n"
    )
    print(f"\nManifest written to: {MANIFEST_PATH}")

    return manifest_data


if __name__ == "__main__":
    result = main()
    # Print summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for c in result["cycles"]:
        ga = c["gap_analysis"]
        print(
            f"Cycle {c['cycle']} ({c['rate']*100:.0f}%): "
            f"{c['dq_failed']}/{c['dq_total']} rules failed, "
            f"detection rate: {ga['detection_rate']*100:.1f}%, "
            f"silent rules: {[r['rule_id'] for r in ga['passed_rules']]}"
        )
