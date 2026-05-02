# Physical Model: raw-ipeds-finance

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Bronze (Raw)
**Spec:** [docs/specs/full-pipeline-ipeds-finance.md](../../docs/specs/full-pipeline-ipeds-finance.md) §4
**Conceptual model:** [raw-ipeds-finance-conceptual.md](raw-ipeds-finance-conceptual.md)
**Logical model:** [raw-ipeds-finance-logical.md](raw-ipeds-finance-logical.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Iceberg Table

- **Logical name:** `raw.ipeds_finance`
- **Physical Iceberg namespace:** `bronze.ipeds_finance` (matches the catalog convention used by sibling `raw-ingest-*` and `raw-eada` tables; see e.g. `bronze.college_scorecard_institution`, `bronze.eada`)
- **Format:** Apache Iceberg over Parquet
- **Catalog:** Brightsmith REST catalog (the FutureProof working catalog; see `pyproject.toml` for connection config)
- **Partition spec:** none (single-cycle snapshot in current load; future amendment may partition on `fiscal_year`)
- **Sort spec:** none
- **Storage location:** `data/bronze/ipeds_finance/` (under the project's bronze warehouse root)
- **Created by:** [`src/raw/ipeds_finance_ingestor.py`](../../src/raw/ipeds_finance_ingestor.py) — `IpedsFinanceIngestor`

---

## Iceberg Schema

The schema is defined in code at `IpedsFinanceIngestor._build_iceberg_schema()` (`src/raw/ipeds_finance_ingestor.py` ~L1101). Field IDs are stable; never reassign on schema evolution.

| Field ID | Field | Iceberg Type | Required | Source-Column Origin | Physical Notes |
|---:|-------|--------------|:--------:|----------------------|----------------|
| 1 | `unitid` | `LongType` | yes | Finance form `UNITID` | Coerced via `_coerce_long`; tolerates int / quoted-string / zero-padded-string variants. |
| 2 | `institution_name` | `StringType` | yes | HD `INSTNM` (joined on UNITID at ingest from `HD2023.csv`) | Trimmed; no further normalization at Bronze. |
| 3 | `report_form` | `StringType` | yes | Stamped by ingestor based on which form CSV the row came from | Enum-valued: `F1A` / `F2` / `F3`. Validated by RAW-IPF-004 (P0). |
| 4 | `fiscal_year` | `IntegerType` | yes | Pinned by ingestor (`DEFAULT_FISCAL_YEAR=2023`) | No in-row column; stamped from constructor kwarg. EDA §0 gate 1 confirmed FY24 is not yet released by NCES — current promote target is FY23 (provisional). |
| 5 | `institutional_support_expenses` | `DoubleType` | no | F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1` | Sentinel scrub (`""`, `-1`, `-2`, `.`, `"PrivacySuppressed"` → NULL) before coercion. F3 column locked v1.3 (post-2014-15 schedule populated; 100% non-null on FY23). |
| 6 | `instruction_expenses` | `DoubleType` | no | F1A `F1C011` / F2 `F2E011` / F3 `F3E011` | Sentinel scrub before coercion. F3 column locked v1.3 (provisional `F3E01` was wrong; the `1` suffix denotes "Total amount"). |
| 7 | `endowment_value` | `DoubleType` | no | F1A `F1H02` / F2 `F2H02` / F3 N/A | Sentinel scrub before coercion. F3 has no `F3H` family — column coalesces to NULL for 100% of F3 rows by design. |
| 8 | `total_fte_enrollment` | `DoubleType` | no | EFIA NULL-safe sum of `FTEUG + FTEGD + FTEDPP` | Computed at ingest via `_build_efia_lookup`. NULL only when all three components are NULL. EFIA is one row per UNITID (no dedup needed). |
| 9 | `source_url` | `StringType` | yes | Stamped — pipe-delimited list of all 5 source URLs | Constant per batch (F1A + F2 + F3 + EFIA + HD bulk-CSV URLs). |
| 10 | `source_method` | `StringType` | yes | Stamped — `"bulk_csv_download"` | Constant per batch. |
| 11 | `ingested_at` | `TimestampType` | yes | Stamped — UTC wall-clock | Identical across all rows in a single batch. |
| 12 | `load_date` | `DateType` | yes | Stamped — UTC calendar date | Identical across all rows in a single batch; powers freshness DQ guardrails. |
| 13 | `endowment_value_flag` (v1.4) | `StringType` | no | F1A `XF1H02` / F2 `XF2H02` / F3 N/A | **NEW v1.4** — IPEDS-published imputation flag for `endowment_value`. Coalesced from the two source columns into a single string column in the same UNION-ALL across forms that produces `endowment_value`. Domain `{R, A, P, Z, N}` OR NULL. **Sentinel handling:** never sentinel-scrubbed (string enum, not numeric); blank / `.` / `PrivacySuppressed` mapped to NULL. **Authoritative semantics (corrected v1.2 against v1.3-EDA-§7 narrative inversion):** `R` = Reported by institution; `A` = **Not applicable** (no endowment fund — exact `A`↔NULL coupling on `endowment_value`); `N` = **Imputed using Nearest Neighbor procedure**; `P` = Imputed prior year; `Z` = Imputed zero. F3 NULL by structure (no `F3H` family). Validated by RAW-IPF-015 (P0). |

**Total fields:** 13 (4 identity + 3 monetary + 1 enrollment + 4 provenance + **1 imputation provenance, v1.4**).

### Field-ID Stability

Field IDs 1–13 are pinned. Field IDs 1–12 are unchanged from v1.0–v1.3; field ID 13 (`endowment_value_flag`) was added in v1.4 — strictly additive at the tail. Future schema evolution (adding HD columns like `SECTOR` / `CONTROL`, or capturing additional `X*` imputation-flag columns if a future cycle's prevalence on a non-endowment field rises above ~5%) must allocate IDs ≥ 14 and **never** rebind 1–13 to other columns. This is the standard Iceberg-evolution discipline used across the project (compare `bronze.college_scorecard_institution`, where field IDs 1–24 are similarly pinned, and `bronze.eada` where field IDs 1–10 are pinned).

---

## Ingestor

- **Class:** `IpedsFinanceIngestor` extends `brightsmith.bronze.base_ingestor.BaseIngestor`
- **Module:** [`src/raw/ipeds_finance_ingestor.py`](../../src/raw/ipeds_finance_ingestor.py) (1,117 lines)
- **Idempotency:** Yes — re-running over the same input deterministically produces the same row set on the same `[unitid]` key.
- **Source method default:** `bulk_csv_download` — fetches `F2223_F1A.zip`, `F2223_F2.zip`, `F2223_F3.zip`, `EFIA2023.zip`, `HD2023.zip` from `https://nces.ed.gov/ipeds/datacenter/data/`, unzips each, reads the CSV in chunks (50,000 rows per CLAUDE.md rule), coalesces form-specific columns, joins EFIA + HD on UNITID, applies the `ICLEVEL = 1 AND HLOFFER >= 5` filter, scrubs sentinels, coerces types, and stamps provenance.
- **Caching:** ZIPs cached at `data/raw/ipeds_finance_cache/` (one ZIP per file × five files × however many cycles).

### EDA-Pinned Constants (FY23 promote, 2026-04-30)

The ingestor in `src/raw/ipeds_finance_ingestor.py` carries the EDA-pinned constants for the FY23 cycle:

```python
DEFAULT_FISCAL_YEAR              = 2023            # FY24 not yet released by NCES; FY23 is the operative cycle
DEFAULT_F1A_INSTRUCTION_COL      = "F1C011"        # Part C functional expenses (NOT Part B revenues)
DEFAULT_F1A_INSTITUTIONAL_SUPPORT_COL = "F1C071"   # Part C functional expenses
DEFAULT_F1A_ENDOWMENT_EOY_COL    = "F1H02"
DEFAULT_F2_INSTRUCTION_COL       = "F2E011"        # Section E functional expenses
DEFAULT_F2_INSTITUTIONAL_SUPPORT_COL = "F2E061"
DEFAULT_F2_ENDOWMENT_EOY_COL     = "F2H02"
DEFAULT_F3_INSTRUCTION_COL       = "F3E011"        # locked v1.3 — was provisional "F3E01"
DEFAULT_F3_INSTITUTIONAL_SUPPORT_COL = "F3E03C1"   # locked v1.3 — post-2014-15 schedule populated
DEFAULT_F3_ENDOWMENT_EOY_COL     = None            # F3 has no F3H family — endowment is structural NULL
EFIA_FILE_PREFIX                 = "EFIA"          # locked v1.3 — NOT EFFY (which is headcount)
EFIA_FILE_SUFFIX                 = ""              # EFIA filename has no A/B suffix
EFIA_DEDUP_COL                   = None            # EFIA is 1 row per UNITID — no dedup needed
EFIA_DEDUP_VALUE                 = None
EFIA_FTE_COMPUTATION             = "COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)"  # locked v1.3
HD_FILE_PREFIX                   = "HD"
HD_FILTER_PREDICATE              = "ICLEVEL = 1 AND HLOFFER >= 5"   # IPEDS-native 4-year bachelor's-or-above
SUPPRESSION_SENTINELS            = frozenset({"", "-1", "-2", ".", "PrivacySuppressed"})
USER_AGENT                       = "FutureProof/0.1 (jeff@hyenastudios.com)"
```

All overridable via `__init__` kwargs. Future cycles need only `IpedsFinanceIngestor(fiscal_year=2024)` once NCES publishes FY24.

### EDA-Discovered Code Changes (vs. spec-as-originally-written)

EDA §0 identified three ingestor gates that needed code changes (not just config overrides) before the FY23 promote could run. All three were applied to the current ingestor:

1. **`_build_efia_lookup` replaces `_build_effy_lookup`** — single-column lookup replaced with three-column NULL-safe sum (`FTEUG + FTEGD + FTEDPP`).
2. **EFIA filename routing** — `effy_file_prefix="EFIA"` + `effy_file_suffix=""` produces `EFIA2023.zip`, not the old `EFFY2223A.zip`.
3. **F3 column overrides** — `f3_instruction_col="F3E011"` (was provisional `F3E01`) and `f3_institutional_support_col="F3E03C1"` (was None).

All three are configuration-pinned now; the ingestor reads the right files and the right columns out-of-the-box for FY23.

---

## Load Statistics (FY23 cycle, fiscal_year=2023)

| Metric | Value |
|--------|------:|
| Rows | 2,675 |
| Distinct `unitid` | 2,675 (100% unique) |
| `report_form` distinct values | 3 — F1A 819 (30.6%) / F2 1,579 (59.0%) / F3 277 (10.4%) |
| `instruction_expenses` non-null | 2,675 (100.0%) |
| `institutional_support_expenses` non-null | 2,675 (100.0%) |
| `endowment_value` non-null | 2,033 (76.0%) |
| `total_fte_enrollment` non-null | 2,620 (97.94%) |
| F3 endowment NULL count (structural) | 277 / 277 (100%) |
| F2 endowment NULL count (small private institutions w/o endowment) | ~253 / 1,579 (~16%) |
| Top-row `instruction_expenses` | $3,504,073,000 (Stanford) |
| `instruction_expenses` p50 | $15,220,174 |
| Rows with `instruction_expenses > $100M` | 269 (R1 anchors — UMich, UCLA, Penn State, etc.) |
| `endowment_value` max | $50,748,594,000 (Stanford) |
| `total_fte_enrollment` max | 135,698 |
| `total_fte_enrollment` min | 6 (SUNY Empire State College, FY23 transition year — verified plausible) |
| Bureau-imputed value prevalence (any field) | ≤1.22% |
| UNITID overlap with `bronze.college_scorecard_institution` | 2,621 / 2,675 (98.0%) |

Source: `governance/eda/full-pipeline-ipeds-finance-raw-eda.md`.

---

## Cross-References

| Artifact | Path |
|----------|------|
| Spec | `docs/specs/full-pipeline-ipeds-finance.md` |
| Ingestor | `src/raw/ipeds_finance_ingestor.py` |
| EDA report | `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` |
| Pre-flight EDA | `governance/eda/raw-ingest-ipeds-finance-preflight.md` |
| DQ rules | `governance/dq-rules/raw-ipeds-finance.json` (14 rules) |
| DQ scorecard | `governance/dq-scorecards/raw-ipeds-finance-20260501T202737Z.{json,md}` (14/14 PASS) |
| Chaos report | `governance/chaos-reports/raw-ipeds-finance-chaos.md` |
| Lineage event | `governance/lineage/full-pipeline-ipeds-finance-{timestamp}.json` (forward pointer; produced by lineage-tracker for the Bronze run of this spec) |
| Domain context | `governance/domain-context.md` § IPEDS Finance Survey |
| Data dictionary | `governance/data-dictionaries/raw-ipeds-finance.md` |
| Conceptual model | `governance/models/raw-ipeds-finance-conceptual.md` |
| Logical model | `governance/models/raw-ipeds-finance-logical.md` |

---

## Modeling Decisions (Physical Layer)

1. **`bronze.ipeds_finance` namespace, not `raw.ipeds_finance` at Iceberg.** The spec declares `raw.ipeds_finance` as the logical name, but every sibling raw table in the FutureProof catalog physically writes to `bronze.*` (matching `BaseIngestor`'s default and the catalog convention demonstrated by `bronze.college_scorecard_institution`, `bronze.eada`, `bronze.bls_ooh`, etc.). The DQ rules SQL in `governance/dq-rules/raw-ipeds-finance.json` references `bronze.ipeds_finance` directly. Both names refer to the same physical table.

2. **`DoubleType` for monetary fields, not `DecimalType(p, s)`.** Sibling raw tables (`bronze.eada` monetary fields, `bronze.college_scorecard_institution` cost-of-attendance fields) use `DoubleType`. IPEDS Finance is a structurally similar raw landing — accept the upstream-native floating-point representation. Decimal precision concerns belong to downstream zones if they ever materialize.

3. **`DoubleType` for `total_fte_enrollment`, not `IntegerType`.** Although FTE counts are conceptually integer-like, the upstream EFIA columns are published as floating-point (NCES-estimated FTE values can carry tenths). Using `DoubleType` matches the source and avoids precision loss when summing the three components.

4. **No partition spec.** The Bronze table is single-cycle today and `fiscal_year` is constant across rows. Adding a partition spec when there's only one partition value would only complicate the on-disk layout. Future multi-cycle backfill should add `PARTITION BY fiscal_year` as a schema-evolution step.

5. **`required=True` on provenance.** Even though `source_url` / `source_method` / `ingested_at` / `load_date` are pipeline-stamped (never user-provided), Iceberg-level `required=True` codifies the governance contract — a row without provenance cannot enter the table. This catches manual-SQL bypass attempts at write time.

6. **`required=True` on `report_form`.** Although it is a stamped value (not source-derived), `report_form` is part of every row's identity (every Finance row came from exactly one of three forms). A NULL `report_form` would mean the row's form-of-origin was lost — a governance violation. Validated by RAW-IPF-004 (P0).

7. **`required=False` on monetary fields and FTE.** The FY23 cycle has 100% completeness on the two expense fields, 76% on endowment, and 97.94% on FTE. The schema permits NULL because (a) endowment is structurally NULL on F3 (no `F3H` family), (b) suppression-sentinel scrub maps unparseable values to NULL by design, and (c) EFIA join is LEFT, so newly-opened or late-filer institutions land with NULL FTE. Locking these to `required=True` would make the ingestor brittle against future IPEDS codebook drift and against the structural F3 endowment NULL. Completeness is enforced by RAW-IPF-009 / 010 / 011 / 012 at runtime instead.

8. **No `record_id` column at Bronze.** The Brightsmith convention reserves `record_id` for Silver+ promotion grain hashing. Bronze keeps the natural key (`unitid`) only. The Silver layer (`base.ipeds_finance`) computes `record_id` via `compute_grain_id(row, ['unitid'], prefix='ipf')`.

9. **No imputation-flag columns at v1.0–v1.3 (revised v1.4 narrowly).** Per v1.3 §2 Decision #8, `X*`-prefixed bureau-imputation flag columns are not stored. EDA Req 7 measured prevalence ≤1.22% on instruction / institutional support — well below the threshold (~5%) where the cost of a flag-column schema change would be justified. **v1.4 amends this narrowly for the endowment flag pair only** (field ID 13, `endowment_value_flag`) because endowment carries a 25–31% imputation prevalence on F1A/F2 — meaningful for longitudinal consumers. The other `X*` flag columns remain unstored. The v1.4 column is `StringType` (not numeric) and never sentinel-scrubbed.

10. **`source_url` as a single pipe-delimited string, not an array.** Iceberg supports list types, but pipe-delimited strings match the convention used by `bronze.eada` and `bronze.college_scorecard_institution` for multi-file lineage, and they are easier for downstream consumers to inspect via simple SQL `CONTAINS` checks. The cost is that consumers must split on `|` if they want individual URLs — that is acceptable given multi-file lineage is a Bronze-zone concern only.
