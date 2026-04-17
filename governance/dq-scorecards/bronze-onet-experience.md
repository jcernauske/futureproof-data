# DQ Scorecard: bronze-onet-experience

**Spec:** onet-experience-requirements
**Zone:** Bronze (Raw)
**Table:** bronze.onet_experience (Iceberg)
**Fully-qualified SQL name:** raw.onet_experience
**Executed:** 2026-04-17T01:39:25Z
**Run ID:** 9690335b
**Evidence Hash:** 3ce1d53cb911c75c
**Agent:** @dq-engineer
**Data Source:** O*NET Education, Training, and Experience (Version 30.2, release date 08/2023)
**Rules File:** governance/dq-rules/raw-onet-experience.json (14 rules)
**Results File:** governance/dq-results/raw-onet-experience-20260417-013925.json

**Supersedes:** 2026-04-17T01:20:02Z run (10 rules, run_id 650f134b). The rule set was expanded from 10 to 14 by @dq-rule-writer on 2026-04-17T02:00Z to close gaps identified by `bs:adversarial-auditor` (audit report: `governance/audit-reports/onet-experience-adversarial-20260417-013427.md`). This scorecard reflects the re-execution of the full 14-rule suite.

---

## Overall Score: 13/14 (92.9%)

**P0 Gate: PASS** (8/8 P0 rules passed)
**P1 Rules: 5/6 PASS, 1 FAIL** (RAW-ONET-EXP-014 -- rule-definition scope bug, not a data defect; see Observation 3)

---

## Execution Method

The PyIceberg catalog entry for `bronze.onet_experience` currently does not
resolve via `catalog.load_table` (NoSuchTableError reported by
`bs:data-analyst`), but the underlying Iceberg data file is intact:

```
data/bronze/iceberg_warehouse/bronze/onet_experience/data/
  00000-0-f09a19fa-5466-46ed-a39d-58f4db0dac5e.parquet  (35,998 rows)
```

Rules were executed by reading this parquet directly with DuckDB
(`read_parquet`) and materializing it in-memory as `raw.onet_experience`,
so the DQ rule SQL ran unchanged. Same execution path as the prior run.

Executor: `scripts/dq_execute_onet_experience.py`

---

## Rule Results

### P0 Rules (Hard Gate) -- 8/8 PASS

| Rule ID | Name | Status | Actual | Threshold | Notes |
|---------|------|--------|--------|-----------|-------|
| RAW-ONET-EXP-001 | Row count 30,000-45,000 | PASS | 35,998 rows | 30,000 <= count <= 45,000 | Squarely inside window |
| RAW-ONET-EXP-002 | onet_soc_code format XX-XXXX.XX | PASS | 0 violations | 0 | 100% conformance across 35,998 rows |
| RAW-ONET-EXP-003 | scale_id in (RL, RW, PT, OJ) | PASS | 0 violations | 0 | Exactly four scales observed |
| RAW-ONET-EXP-004 | data_value in [0.0, 100.0] | PASS | 0 violations | 0 | Observed range [0.0, 100.0] |
| RAW-ONET-EXP-006 | element_id NOT NULL | PASS | 0 nulls | 0 | element_id populated on every row |
| RAW-ONET-EXP-007 | Grain uniqueness (onet_soc_code, element_id, scale_id, category) | PASS | 0 duplicates | 0 | Declared grain holds |
| **RAW-ONET-EXP-011** (new) | **(scale_id, element_id) canonical binding** | **PASS** | 0 violations | 0 | All rows match canonical pairs {(RL,2.D.1),(RW,3.A.1),(PT,3.A.2),(OJ,3.A.3)} -- closes adversarial Gap A |
| **RAW-ONET-EXP-012** (new) | **Per-scale category value ENUM (RL 1-12, RW 1-11, PT 1-9, OJ 1-9)** | **PASS** | 0 violations | 0 | Every category value is in the canonical per-scale integer range -- closes adversarial Gap B |

### P1 Rules (Warning) -- 5/6 PASS, 1 FAIL

| Rule ID | Name | Status | Actual | Threshold | Notes |
|---------|------|--------|--------|-----------|-------|
| RAW-ONET-EXP-005 | Per (onet_soc_code, scale_id) sum == 100 within ±0.1 | PASS | 0 violations | 0 | 3,512 groups checked; max \|deviation\| = 0.03 |
| RAW-ONET-EXP-008 | RW scale row count 9,000-12,500 | PASS | 9,658 rows | 9,000 <= rw_rows <= 12,500 | 878 occupations × 11 RW categories |
| RAW-ONET-EXP-009 | Occupation coverage 800-1,100 distinct SOCs | PASS | 878 distinct | 800 <= n <= 1,100 | Actual O*NET ETE footprint |
| RAW-ONET-EXP-010 | Per-scale distinct category counts RL=12, RW=11, PT=9, OJ=9 | PASS | 0 violations | 0 | All four exact-count expectations hold |
| **RAW-ONET-EXP-013** (new) | **recommend_suppress in ('Y','N','n/a') and Y rate < 5%** | **PASS** | 0 violations | 0 | Value set is exact {N, n/a, Y}; observed Y rate 2.4% (864/35,998) -- closes adversarial Gap C |
| **RAW-ONET-EXP-014** (new) | **No (onet_soc_code, scale_id) group has MAX(data_value) >= 99.0** | **FAIL** | 2 violations | 0 | See Observation 3 below. Both violations are on **RL** scale, not RW. |

---

## Rule 014 FAIL -- Detail

The two violating groups:

| onet_soc_code | scale_id | MAX(data_value) |
|---------------|----------|-----------------|
| 11-3051.01 (Transportation, Storage, and Distribution Managers) | RL | 100.00 |
| 29-9092.00 (Genetic Counselors) | RL | 100.00 |

Both are on the **RL** (Required Level of Education) scale. RW, the scale
Silver depends on, has zero groups with MAX >= 99.0 (observed RW per-group
max across all 878 occupations is 95.83 -- well below threshold).

---

## Supplementary Statistics

| Metric | Value |
|--------|-------|
| Total rows | 35,998 |
| Distinct onet_soc_codes | 878 |
| Scale distribution -- RL | 10,536 rows (29.3%) |
| Scale distribution -- RW | 9,658 rows (26.8%) |
| Scale distribution -- PT | 7,902 rows (22.0%) |
| Scale distribution -- OJ | 7,902 rows (22.0%) |
| Distinct categories -- RL | 12 |
| Distinct categories -- RW | 11 |
| Distinct categories -- PT | 9 |
| Distinct categories -- OJ | 9 |
| element_id values | {2.D.1 (RL), 3.A.1 (RW), 3.A.2 (PT), 3.A.3 (OJ)} -- 1:1 with scale_id |
| data_value observed range | [0.0, 100.0] |
| Per-scale MAX(data_value) -- RL | 100.00 |
| Per-scale MAX(data_value) -- RW | 95.83 |
| Per-scale MAX(data_value) -- PT | 81.22 |
| Per-scale MAX(data_value) -- OJ | 90.40 |
| Per-(onet_soc_code, scale_id) groups | 3,512 |
| Per-group max \|sum - 100\| | 0.03 |
| recommend_suppress = 'Y' rate | 2.4% (864 / 35,998) |
| Null count -- onet_soc_code | 0 |
| Null count -- element_id | 0 |
| Null count -- scale_id | 0 |
| Null count -- category | 0 |
| Null count -- data_value | 0 |

---

## Observations

1. **All P0 rules pass, including the two new P0 rules from adversarial gap-closing.**
   RAW-ONET-EXP-011 (canonical (scale_id, element_id) pair binding) and
   RAW-ONET-EXP-012 (per-scale category value ENUM) both return 0 violations
   on real data, exactly as EDA predicted. These rules now block the
   attack surface exposed by adversarial probes P1 (scrambled scale<->element
   mapping) and P6 (out-of-range category value).

2. **RAW-ONET-EXP-013 passes cleanly.** The recommend_suppress field is
   well-behaved: exact value set {N, n/a, Y} (0 other values, 0 nulls beyond
   n/a), and overall Y rate is 2.4% -- well inside the 5% ceiling. Closes
   adversarial Gap C.

3. **RAW-ONET-EXP-014 FAIL is a rule-definition scope mismatch, not a data defect.**

   The rule's stated intent per the task briefing from `bs:adversarial-auditor`
   and the rule's own `rationale` text is **scoped to the RW scale** ("P1,
   scoped to RW per writer's tuning recommendation"). The rule's SQL,
   however, is unscoped and runs against all four scales. The two failing
   groups are both on the **RL** scale, where a MAX(data_value) of 100.00 is
   legitimate and EDA-documented ("RL's per-scale max is exactly 100.00 on a
   small number of rows" -- from the rule's own rationale block).

   The **RW-scoped probe that motivated this rule (collapsed all-entry-level
   distribution) remains trapped** -- scoping the SQL to `WHERE scale_id =
   'RW'` would yield 0 violations today (verified) and would still catch
   probe P2 from the adversarial audit.

   **Proposed fix** (for @dq-rule-writer): add `WHERE scale_id = 'RW'` to
   the subject query. The per-@dq-engineer scope boundary forbids this
   agent from modifying the rule file directly; escalating to
   @governance-reviewer.

   **Gating impact:** P1 only. Does NOT block the Bronze gate. Spec may
   proceed to Silver pending governance disposition.

4. **No regression on the original 10 rules.** Rules 001-010 return
   identical results to the 2026-04-17T01:20:02Z baseline run. Data is
   unchanged (same parquet file, 35,998 rows, run_id 650f134b -> 9690335b is
   a pure rule-set expansion).

5. **Follow-up still required:** Re-register `bronze.onet_experience` in
   the PyIceberg catalog so `catalog.load_table("bronze.onet_experience")`
   resolves. Unchanged from prior scorecard.

---

## Comparison to EDA Expectations

| Metric | EDA Prediction | Actual | Match |
|--------|---------------|--------|-------|
| Row count | 35,998 | 35,998 | exact |
| Distinct SOCs | 878 | 878 | exact |
| Scale RL rows | 10,536 | 10,536 | exact |
| Scale RW rows | 9,658 | 9,658 | exact |
| Scale PT rows | 7,902 | 7,902 | exact |
| Scale OJ rows | 7,902 | 7,902 | exact |
| Per-scale categories RL/RW/PT/OJ | 12 / 11 / 9 / 9 | 12 / 11 / 9 / 9 | exact |
| Per-group max \|sum-100\| | 0.03 | 0.03 | exact |
| onet_soc_code format violations | 0 | 0 | exact |
| data_value out-of-range | 0 | 0 | exact |
| element_id null rate | 0.00% | 0.00% | exact |
| Grain duplicates | 0 | 0 | exact |
| (scale_id, element_id) off-canonical pairs | 0 | 0 | exact (new) |
| Per-scale category-value out-of-range | 0 | 0 | exact (new) |
| recommend_suppress 'Y' rate | 2.4% | 2.4% | exact (new) |
| RW groups with MAX(data_value) >= 99.0 | 0 | 0 | exact (new) |
| All-scales groups with MAX(data_value) >= 99.0 | 2 (RL) | 2 (RL) | exact (new) -- rule scope issue, not data surprise |

No data surprises. All EDA measurements reproduce exactly. The rule 014
FAIL is a rule-SQL scoping defect, not a divergence from EDA.

---

## P0 Gate Decision

**PASS.** All eight P0 rules passed with zero violations on real data.
Zone 1 (Bronze) deliverable for `onet-experience-requirements` is cleared
from a DQ perspective. Spec may proceed to Zone 2 (Silver) work.

The one P1 FAIL (RAW-ONET-EXP-014) is a rule-definition scope bug with no
data-quality implication for Silver. Escalated to @governance-reviewer for
disposition: either (a) accept as a documented false-positive on RL scale
until @dq-rule-writer narrows the SQL to `WHERE scale_id = 'RW'`, or (b)
block Silver pending rule correction. This agent's recommendation: (a),
because Silver consumes only scale_id='RW' rows and no RW group violates.

---

*Generated by @dq-engineer on 2026-04-17T01:39:25Z*
