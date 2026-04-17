# Physical Model — raw-ingest-college-scorecard-institution (multi-zone)

**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md`
**Zones:** Raw → Silver → Gold
**Created:** 2026-04-16

This spec spans three zones. Each zone's physical model is maintained under its own canonical path. This file is a pointer index to the three physical models and a summary of their final schemas.

---

## Zone 1 — Bronze (Raw Ingest)

**Iceberg table:** `raw.college_scorecard_institution` (alt: `bronze.college_scorecard_institution` per BaseIngestor default)
**Rows:** 3,039 (after PREDDEG=3 OR ICLEVEL=1 filter)
**Grain:** One row per UNITID
**Schema:** ~24 columns — see the ingestor at `src/raw/college_scorecard_institution_ingestor.py` and DQ rules at `governance/dq-rules/raw-ingest-college-scorecard-institution.json`
**DQ status:** 13/13 PASS against real Iceberg (run 2026-04-16T15:22:20Z, run_id `d3e9cd2a`)

---

## Zone 2 — Silver (Base)

**Iceberg table:** `base.college_scorecard_institution`
**Rows:** 3,039 (1:1 from Bronze after dedup on UNITID)
**Grain:** One row per UNITID
**Physical model:** `governance/models/silver-base-college-scorecard-institution-physical.md`
**Data contract:** `governance/data-contracts/silver-base-college-scorecard-institution.yaml` (26 CDE, 35 columns)
**DQ status:** 23/23 PASS against real Iceberg (run 2026-04-16T15:23:05Z, run_id `7389603f`) — closes advisory A3

---

## Zone 3 — Gold (Enrichment)

**Iceberg table:** `consumable.career_outcomes`
**Rows:** 69,947 (preserved exactly by LEFT JOIN re-promote)
**Grain:** unitid × cipcode × credlev (unchanged)
**Physical model:** `governance/models/gold-career-outcomes-college-scorecard-physical.md`
**Data contract:** `governance/data-contracts/consumable-career-outcomes.yaml` (v1.1.0, 13 CDE, 37 columns)
**DQ status:** 51/51 PASS against real Iceberg (9 new GLD-CSI-* + 42 GLD-CO-* regression; run 2026-04-16T16:21:06Z, run_id `9dd4463a`, evidence hash `1f57cd28e28b296b`)
**Chaos:** 5 cycles, 45/45 detections (100%)

### New columns added at Gold (7)

| Field | Type | Field ID | Nullable | CDE |
|-------|------|----------|----------|-----|
| net_price_annual | double | 32 | YES | **YES** |
| cost_of_attendance_annual | double | 33 | YES | **YES** |
| net_price_4yr | double | 34 | YES | No |
| tuition_in_state | double | 35 | YES | No |
| tuition_out_of_state | double | 36 | YES | No |
| room_board_on_campus | double | 37 | YES | No |
| institution_control | string | 4 (re-sourced in place) | YES | No |

Field IDs 1-31 preserved exactly across the schema evolution.

---

## Lineage

`governance/lineage/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T163000Z.json` — names **2** Silver inputs (`base.college_scorecard`, `base.college_scorecard_institution`) and supersedes the prior single-input event.

---

## Golden Dataset

`governance/golden-datasets/raw-ingest-college-scorecard-institution-golden.json` — 5 named institutions (MIT, Princeton, Stanford, UC Berkeley, Harvard) with independently verifiable values against https://collegescorecard.ed.gov/, plus row-count and coverage invariants.
