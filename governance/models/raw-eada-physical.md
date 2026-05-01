# Physical Model: raw-eada

**Status:** PROPOSED
**Mode:** Greenfield
**Zone:** Bronze (Raw)
**Spec:** [docs/specs/full-pipeline-eada.md](../../docs/specs/full-pipeline-eada.md) §4
**Conceptual model:** [raw-eada-conceptual.md](raw-eada-conceptual.md)
**Logical model:** [raw-eada-logical.md](raw-eada-logical.md)
**Author:** @doc-generator
**Date:** 2026-04-30
**Approval:** Pending human review (REQUIRE_HUMAN_APPROVAL = true)

---

## Iceberg Table

- **Logical name:** `raw.eada`
- **Physical Iceberg namespace:** `bronze.eada` (matches the catalog convention used by sibling `raw-ingest-*` tables; see e.g. `bronze.college_scorecard_institution`)
- **Format:** Apache Iceberg over Parquet
- **Catalog:** Brightsmith REST catalog (the FutureProof working catalog; see `pyproject.toml` for connection config)
- **Partition spec:** none (single-cycle snapshot in current load; future amendment may partition on `reporting_year`)
- **Sort spec:** none
- **Storage location:** `data/bronze/eada/` (under the project's bronze warehouse root)
- **Created by:** [`src/raw/eada_ingestor.py`](../../src/raw/eada_ingestor.py) — `EadaIngestor`

---

## Iceberg Schema

The schema is defined in code at `EadaIngestor._build_iceberg_schema()` (`src/raw/eada_ingestor.py` ~L580). Field IDs are stable; never reassign on schema evolution.

| Field ID | Field | Iceberg Type | Required | Source-Column Origin | Physical Notes |
|---:|-------|--------------|:--------:|----------------------|----------------|
| 1 | `unitid` | `LongType` | yes | EADA `unitid` (lowercase) | Coerced via `_coerce_long`; tolerates int / quoted-string / zero-padded-string variants from older cycles. |
| 2 | `institution_name` | `StringType` | yes | EADA `institution_name` (lowercase) | Trimmed; no further normalization at Bronze. |
| 3 | `reporting_year` | `IntegerType` | yes | Pinned by ingestor (`DEFAULT_REPORTING_YEAR=2022`) | No in-row column; stamped from cache filename or constructor kwarg. |
| 4 | `total_athletic_expenses` | `DoubleType` | no | EADA `GRND_TOTAL_EXPENSE` | Sentinel scrub (`""`, `-1`, `-2` → NULL) before coercion. |
| 5 | `total_athletic_revenue` | `DoubleType` | no | EADA `GRND_TOTAL_REVENUE` | Sentinel scrub before coercion. |
| 6 | `recruiting_expenses` | `DoubleType` | no | EADA `RECRUITEXP_TOTAL` | Sentinel scrub before coercion. Real `0.0` values are valid (17.8% of rows). |
| 7 | `source_url` | `StringType` | yes | Stamped — `BULK_URL_TEMPLATE = "https://ope.ed.gov/athletics/"` | Constant per batch. |
| 8 | `source_method` | `StringType` | yes | Stamped — currently `"csv_cache"` | Switches to `"bulk_csv_download"` when the SPA refresh path is invoked via `bulk_url` kwarg. |
| 9 | `ingested_at` | `TimestampType` | yes | Stamped — UTC wall-clock | Identical across all rows in a single batch. |
| 10 | `load_date` | `DateType` | yes | Stamped — UTC calendar date | Identical across all rows in a single batch; powers freshness DQ guardrails. |

**Total fields:** 10 (3 identity + 3 monetary + 4 provenance).

### Field-ID Stability

Field IDs 1–10 are pinned. Future schema evolution (adding `EFTotalCount`, `classification_name`, etc.) must allocate IDs ≥ 11 and **never** rebind 1–10 to other columns. This is the standard Iceberg-evolution discipline used across the project (compare `bronze.college_scorecard_institution`, where field IDs 1–24 are similarly pinned).

---

## Ingestor

- **Class:** `EadaIngestor` extends `brightsmith.bronze.base_ingestor.BaseIngestor`
- **Module:** [`src/raw/eada_ingestor.py`](../../src/raw/eada_ingestor.py)
- **Idempotency:** Yes — re-running over the same input deterministically produces the same row set on the same `(unitid, reporting_year)` key.
- **Source method default:** `csv_cache` reading `data/raw/eada_cache/eada_<year>.csv` (the EDA pre-converted `InstLevel.xlsx` → CSV for 2022–23).
- **Source method refresh path:** SPA-API `GET https://ope.ed.gov/athletics/api/dataFiles/file?fileName=EADA_<YYYY-YYYY>.zip` → unzip → extract `InstLevel.xlsx` → CSV. Triggered via `bulk_url` constructor kwarg.

### EDA-Pinned Constants (2026-04-30)

```python
INSTITUTION_TOTAL_FILTER_COLUMN = None     # No in-pipeline filter; InstLevel.xlsx is one-row-per-UNITID
INSTITUTION_TOTAL_FILTER_VALUE  = None
DEFAULT_EXP_COLUMN              = "GRND_TOTAL_EXPENSE"
DEFAULT_REV_COLUMN              = "GRND_TOTAL_REVENUE"
DEFAULT_RECRUITING_COLUMN       = "RECRUITEXP_TOTAL"
UNITID_COLUMN                   = "unitid"
INSTNM_COLUMN                   = "institution_name"
DEFAULT_REPORTING_YEAR          = 2022     # Academic year start of 2022-23 cycle
SUPPRESSION_SENTINELS           = frozenset({"", "-1", "-2"})
USER_AGENT                      = "FutureProof/0.1 (jeff@hyenastudios.com)"
```

All overridable via `__init__` kwargs.

---

## Load Statistics (2022–23 cycle)

| Metric | Value |
|--------|------:|
| Rows | 2,040 |
| Distinct `unitid` | 2,040 (100% unique) |
| `total_athletic_expenses` non-null | 2,040 (100%) |
| `total_athletic_revenue` non-null | 2,040 (100%) |
| `recruiting_expenses` non-null | 2,040 (100%) |
| `recruiting_expenses == $0` | 363 (17.8%, real zeros) |
| Top-row `total_athletic_expenses` | $234,409,941 (Ohio State) |
| `total_athletic_expenses` p50 | $3,452,941 |
| Rows with `total_athletic_expenses > $100M` | 60 (D1 anchors) |
| UNITID overlap with `bronze.college_scorecard_institution` | 1,519 / 2,040 (74.5%) |

Source: `governance/eda/full-pipeline-eada-raw-eda.md`.

---

## Cross-References

| Artifact | Path |
|----------|------|
| Spec | `docs/specs/full-pipeline-eada.md` |
| Ingestor | `src/raw/eada_ingestor.py` |
| EDA report | `governance/eda/full-pipeline-eada-raw-eda.md` |
| DQ rules | `governance/dq-rules/raw-eada.json` (12 rules) |
| DQ scorecard | `governance/dq-scorecards/raw-eada-20260501T040238Z.{json,md}` (12/12 PASS) |
| Chaos report | `governance/chaos-reports/raw-eada-chaos.md` (5-cycle + 6 targeted; 6/6 caught) |
| Adversarial audit | `governance/adversarial-audits/raw-eada-bronze-audit.md` (CLEAR) |
| PII scan | `governance/pii-scans/raw-eada-pii-scan.md` (NONE) |
| Entity resolution | `governance/entity-resolution/raw-eada-er-assessment.md` (N/A) |
| Temporal model | `governance/temporal-models/raw-eada-temporal-assessment.md` (N/A) |
| Lineage event | `governance/lineage/full-pipeline-eada-{timestamp}.json` (forward pointer; produced by lineage-tracker for the Bronze run of this spec) |
| Domain context | `governance/domain-context.md` § EADA Athletics Disclosure |
| Data dictionary | `governance/data-dictionaries/raw-eada.md` |

---

## Modeling Decisions (Physical Layer)

1. **`bronze.eada` namespace, not `raw.eada` at Iceberg.** The spec declares `raw.eada` as the logical name, but every sibling raw table in the FutureProof catalog physically writes to `bronze.*` (matching `BaseIngestor`'s default and the catalog convention demonstrated by `bronze.college_scorecard_institution`, `bronze.bls_ooh`, etc.). The DQ rules SQL in `governance/dq-rules/raw-eada.json` references `bronze.eada` directly. Both names refer to the same physical table.

2. **`DoubleType` for monetary fields, not `DecimalType(p, s)`.** Sibling raw tables (`bronze.college_scorecard_institution.npt4_pub`, etc.) use `DoubleType` for cost-of-attendance figures. EADA is a structurally similar raw landing — accept the upstream-native floating-point representation. Decimal precision concerns belong to downstream zones if they ever materialize.

3. **No partition spec.** The Bronze table is single-cycle today and `reporting_year` is constant across rows. Adding a partition spec when there's only one partition value would only complicate the on-disk layout. Future multi-cycle backfill should add `PARTITION BY reporting_year` as a schema-evolution step.

4. **`required=True` on provenance.** Even though `source_url` / `source_method` / `ingested_at` / `load_date` are pipeline-stamped (never user-provided), Iceberg-level `required=True` codifies the governance contract — a row without provenance cannot enter the table. This catches manual-SQL bypass attempts at write time.

5. **`required=False` on monetary fields.** The 2022–23 cycle has 100% completeness, but the schema permits NULL because (a) future cycles may suppress small-program totals, and (b) the suppression-sentinel scrub maps unparseable values to NULL by design. Locking these to `required=True` would make the ingestor brittle against future EADA codebook drift. Completeness is enforced by RAW-EAD-007/008/009 at runtime instead.

6. **No `record_id` column at Bronze.** The Brightsmith convention reserves `record_id` for Silver+ promotion grain hashing. Bronze keeps the natural key (`unitid`) only.
