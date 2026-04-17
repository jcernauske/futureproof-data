# Adversarial Audit — raw.onet_experience (Bronze)

- **Spec:** `docs/specs/onet-experience-requirements.md`
- **Target:** `raw.onet_experience` (Bronze ingest)
- **Ingestor:** `src/raw/onet_ingestor.py::OnetExperienceIngestor`
- **Rules file:** `governance/dq-rules/raw-onet-experience.json` (10 rules)
- **Predicate chaos report:** `governance/chaos-reports/onet-experience-20260417-012743.md`
- **Audit timestamp:** 20260417-013427
- **Auditor:** adversarial-auditor (independent of chaos-monkey)
- **Mode:** read-only + chaos runner re-run + independent adversarial probe script

---

## 1. Verification of S7 fix (empty-file ingestor gap)

The chaos report flagged S7 (`truncated_zip_empty_file`) as an ingestor-level
gap: `OnetExperienceIngestor` silently returned 0 rows when the target TSV
was empty, with no exception raised. The reported fix: add an empty-ness
guard at `OnetBaseIngestor._parse_tsv` that raises `ValueError` when
`len(rows) == 0`.

### 1a. Inspect the fix

`src/raw/onet_ingestor.py::OnetBaseIngestor._parse_tsv` (lines 130–146):

```python
def _parse_tsv(self, content: bytes) -> list[dict[str, str]]:
    """Parse tab-delimited content into a list of row dicts."""
    if content.startswith(b"\xef\xbb\xbf"):
        content = content[3:]
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    rows = list(reader)
    if len(rows) == 0:
        raise ValueError(
            f"{self.SOURCE_FILENAME}: parsed 0 rows (truncated or empty file?)"
        )
    ...
```

The guard is on the shared base class, so it applies to all 6 ONet
subclasses, not only `OnetExperienceIngestor`. That is arguably over-broad
(other O*NET tables could theoretically be empty for legitimate reasons),
but none of the other 5 subclasses have any empty-file use case I can
justify, so I consider this net-beneficial.

### 1b. Re-run the chaos runner to confirm S7 closes

Command:

```bash
uv run python scripts/onet_experience_chaos_runner.py
```

Output excerpt (S7 and S8 behavior checks):

```
--- Behavior checks (S7 truncated ZIP, S8 missing file) ---
  S7: raised=True  ValueError
  S8: raised=True  FileNotFoundError

Report written to governance/chaos-reports/onet-experience-20260417-013054.md

Final: 58/58 caught across 5 cycles. Gaps: 0.
```

New fresh chaos report at `governance/chaos-reports/onet-experience-20260417-013054.md`
confirms: **S7 now raises `ValueError`** — gap CLOSED.

**Verdict on S7 fix: CONFIRMED.**

---

## 2. Regression check — prior 58 rule-targeted scenarios still trigger

The original chaos run reported 58/58 rule-targeted probes caught across 5
cycles. The fresh re-run (above) reports **58/58 caught across 5 cycles,
0 gaps** — byte-for-byte identical scenario-caught matrix.

Additional regression check: the full raw test suite (the 442 existing
tests the fix was claimed not to break):

```bash
uv run pytest tests/raw/ -x --tb=short
```

Result: **442 passed, 1 deselected in 3.05s.** No regressions. This
specifically includes `tests/raw/test_onet_experience_ingestor.py`
(49 tests) and `tests/raw/test_onet_ingestor.py` (89 tests) — both
pass, confirming the `_parse_tsv` guard didn't break the happy path or
any negative-path fixture-based tests.

**Verdict on regression: CLEAN.** Prior 58 caught scenarios still fire;
no new rule failures introduced.

---

## 3. Rule scoping — has the ingestor fix absorbed rule work?

The fix raises at `_parse_tsv` BEFORE any DQ rule ever runs. So the
question is: does any existing rule's SQL rely on the ingestor producing
0 rows as its failure signal? If yes, the fix would silently prevent
those rules from firing in production.

Reviewing all 10 rules' SQL against `raw.onet_experience`:

| Rule | What it checks | Could an empty-file state have been its only failure signal? |
|------|----------------|--------------------------------------------------------------|
| RAW-ONET-EXP-001 | Row count in [30K, 45K] | NO — this rule catches count<30K including 0, but is also meant to catch count>45K (over-ingest). Fix does not absorb it. |
| RAW-ONET-EXP-002 | SOC format | NO — regex rule, nothing to do with count. |
| RAW-ONET-EXP-003 | scale_id IN set | NO |
| RAW-ONET-EXP-004 | data_value in [0, 100] | NO |
| RAW-ONET-EXP-005 | per-occ×scale sum≈100 | NO |
| RAW-ONET-EXP-006 | element_id not null | NO |
| RAW-ONET-EXP-007 | grain uniqueness | NO |
| RAW-ONET-EXP-008 | RW rows in [9K, 12.5K] | NO — similar to 001. |
| RAW-ONET-EXP-009 | distinct occ in [800, 1100] | NO |
| RAW-ONET-EXP-010 | per-scale category counts | NO |

**No over-correction.** The fix is strictly fail-faster on a symptom
(0 rows) that no existing rule depends on as its sole detection surface.
Rules 001 and 008 would eventually catch a 0-row ingest too — the fix
just moves detection from "post-Iceberg-write, at DQ time" to
"pre-Iceberg-write, at parse time," which is the correct gravity.

**Verdict on rule scoping: STRONG.** Fix does not absorb rule work.

---

## 4. Independent adversarial probes — 15 hand-crafted attacks

I authored 15 adversarial probes independent of the chaos runner's
scenario library. Runner: `scripts/_adversarial_probe_onet_exp.py`.
Each probe mutates a clean 878-SOC synthetic baseline and runs all 10
rules. Only probes producing **new** rule fails (beyond the already-clean
baseline) are considered "caught"; probes producing no new fails expose
real adversarial gaps.

### Caught probes (7 of 15)

| # | Probe | Catcher rule(s) |
|---|-------|-----------------|
| P3 | Embedded whitespace inside SOC code (`"11- 1011.00"`) | RAW-ONET-EXP-002 (regex) |
| P4 | Unicode en-dash instead of ASCII hyphen in SOC | RAW-ONET-EXP-002 |
| P5 | scale_id `"RW "` (trailing space) post-ingest | RAW-ONET-EXP-003 |
| P7 | Duplicate RW cat=1 row for one occupation | RAW-ONET-EXP-007 + 005 |
| P8 | Per-occupation RW sum just over ±0.1 tolerance | RAW-ONET-EXP-005 |
| P9 | NaN data_value (`float('nan')`) in one RW row | RAW-ONET-EXP-004 + 005 |
| P15 | Swap cat=1 and cat=11 values within occupation (skewed but sum-preserving) | RAW-ONET-EXP-004 + 005 (triggered via a per-cat value out of [0,100] in my probe implementation, NOT via a semantic check) |

Note on P15: I set cat=2 to a negative value as a by-product of the
rebalance arithmetic — that's what the rule caught. A cleaner
implementation would preserve sum=100 without going negative and would
expose the gap. See §4.3 below for the actual semantic-corruption gap.

### 4.2 Adversarial gaps (7 of 15 probes) — ranked by severity

All 7 probes below produced zero new rule fails. They represent real
corruption patterns that would ship to Silver.

#### Gap A — `scale_id`/`element_id` mismatch (P1, P10) — **CRITICAL**

**Probe P1:** For every RW row, replace `element_id = "3.A.1"` with
`"3.A.3"` (OJ's element_id). Every RW row now says "I'm Related Work
Experience scale, but my element is On-the-Job Training."

**Probe P10:** For one occupation, set `element_id = "2.D.1"` (RL's)
while leaving `scale_id = "RW"`.

**Why this matters:** The Silver transformer filters rows with
`scale_id = 'RW' AND element_id = '3.A.1'` (spec §Zone 2). A mismatch
means:
- P1: ALL 878 occupations silently drop out of Silver (no rows match
  the AND-filter). Silver base table is empty.
- P10: The affected occupation silently disappears from Silver.

Bronze DQ has rule 006 for "element_id not null" and rule 003 for
"scale_id in set," but nothing binds `scale_id` ↔ `element_id`. Yet the
EDA (quoted in rule 007's rationale) explicitly documents the
invariant: "element_id is 1:1 with scale_id." This is a known
relationship that is NOT enforced by any rule.

**Severity: CRITICAL.** A subtle upstream parsing bug or a new O*NET
file format could scramble this mapping and Silver would go dark.

#### Gap B — `category` value range per scale (P6) — **HIGH**

**Probe P6:** Replace all RW rows where `category = 11` with
`category = 15`. RW is defined to have categories 1–11 only; category
15 is out-of-range.

**What the existing rule does:** RAW-ONET-EXP-010 checks
`COUNT(DISTINCT category) per scale_id`. For RW, it expects exactly 11
distinct categories. Because the probe **replaces** one category with
another, the distinct count is still 11 — rule passes.

**Why this matters:** The Silver transformer maps category → midpoint
years using a hardcoded table (spec §Zone 1). Category 15 has no
midpoint — it would either KeyError (loud) or silently produce a
missing value / wrong tier (quiet). The Silver `experience_category_median`
DQ rule enforces `1 ≤ cat ≤ 11`, but a corrupt row passing Bronze
should be caught at Bronze, not relied on to be caught at Silver.

**Missing rule:** Per-scale category ENUM validation (not just count).
E.g., for `scale_id = 'RW'`, every `category` must be in {1..11}.

**Severity: HIGH.** Spec §Zone 1 explicitly states the allowed
categories; no rule enforces them.

#### Gap C — `recommend_suppress` unguarded (P12, P13) — **MEDIUM**

**Probe P12:** Set `recommend_suppress = 'Y'` on every RW row.
**Probe P13:** Set `recommend_suppress = NULL` on a row.

**What the existing rules do:** Nothing. Bronze has zero rules on
`recommend_suppress`.

**Why this matters:**
- P12: Silver's `suppress_flag` is set when any contributing Bronze row
  has `recommend_suppress = 'Y'`. If *everything* is suppressed, every
  Silver row has `suppress_flag = True`, and the spec's spot-check rules
  (11-1011=senior, 15-1252=mid, 41-2031=entry) would all EXCLUDE those
  occupations — Silver DQ rule says "exclude suppressed rows from spot
  checks." So the occupations might pass Silver silently because the
  spot checks no longer apply.
- P13: Null `recommend_suppress` is ambiguous — does it mean "not
  suppressed" or "unknown"? Silver will likely treat null as
  not-suppressed, which could be wrong.

**Missing rule:** Bronze should enforce `recommend_suppress IN ('Y', 'N')`
OR be null in a bounded rate, AND flag when the suppress rate exceeds a
threshold (e.g., >5% of rows).

**Severity: MEDIUM.** Does not produce wrong numeric values, but does
undermine the confidence the spec derives from spot checks.

#### Gap D — mixed vintage `date` within one occupation (P11) — **LOW**

**Probe P11:** Split one occupation's RW rows across two date strings
("08/2023" on some rows, "08/2024" on others). The spec says `date`
is not-required; no rule enforces per-occupation date homogeneity.

**Why this matters:** Low. The `date` field is not consumed by Silver
for experience derivation. But it is a provenance signal that an
auditor would expect to be internally consistent per occupation.

**Severity: LOW.** Not a data-correctness issue, a hygiene issue.

#### Gap E — distribution collapsed into one category (P2) — **HIGH**

**Probe P2:** For every occupation, set RW `data_value = 100.0` for
`category = 1` and `0.0` for all other categories. Per-occupation
×-scale sum is still exactly 100.0. Grain uniqueness holds. Valid SOC,
valid scale, valid element. Rule 004 (`0.0 ≤ data_value ≤ 100.0`)
passes. Rule 005 (sum=100±0.1) passes. Rule 010 (per-scale category
count) passes — all 11 categories still present, just with 10 of them
zeroed.

**Why this matters:** Silver weighted-median logic would return
category=1 → years=0 → tier="entry" for EVERY occupation. The entire
experience-gating feature would collapse into "everyone is entry-level."

This is the archetypal silent-corruption-passes-Bronze pattern the
spec's §Test Matrix explicitly cares about. The spec calls out the
"single category 100%" edge case as a Silver test, but Bronze has no
rule that would refuse to load 878 occupations all concentrated at
category 1 — which is a VERY unlikely real distribution.

**Missing rule:** Bronze could flag pathological distributions —
e.g., for `scale_id = 'RW'`, no more than 5% of occupations should
have ≥99% mass in a single category. (Real EDA would inform the exact
threshold.)

**Severity: HIGH.** Real-world likelihood is low (O*NET would have to
regress catastrophically), but the existing rules give zero warning if
it ever happened.

### 4.3 Non-gap: P14 grain collision

On review, my P14 probe ("8% extra duplicated rows via rerun bug") did
NOT actually create duplicate grains — it appended 70 NEW unique SOCs.
Total rows 38,868 (in volume range), total SOCs 948 (in coverage range).
P14 is a bogus probe, not a real gap.

The real rerun-duplication risk IS caught by rule 007 (grain uniqueness)
as demonstrated by P7. So this risk is adequately covered.

---

## 5. Summary — gaps and risk disposition

| Gap | Severity | Missing rule / mitigation |
|-----|----------|---------------------------|
| A. scale_id ↔ element_id binding unenforced | CRITICAL | Add rule: every `(scale_id, element_id)` pair must be in the canonical set `{('RL','2.D.1'), ('RW','3.A.1'), ('PT','3.A.2'), ('OJ','3.A.3')}`. |
| B. Per-scale category-value ENUM unenforced | HIGH | Add rule: for each scale_id, category ∈ expected-value-set (RL: 1–12, RW: 1–11, PT: 1–9, OJ: 1–9). Rule 010 only checks COUNT(DISTINCT category), not the category values themselves. |
| E. Distribution-collapsed-to-one-category | HIGH | Add rule (advisory, P1): for `scale_id='RW'`, no more than X% of occupations may have ≥99% mass in a single category. |
| C. recommend_suppress unguarded | MEDIUM | Add rule: `recommend_suppress IN ('Y', 'N', NULL)` AND suppression rate < threshold (suggest 5%). |
| D. Mixed vintage date per occupation | LOW | Advisory: flag occupations whose `date` is not homogeneous across their rows. |

All 5 gaps are **data-integrity gaps not introduced by the S7 fix** —
they are pre-existing blind spots in the original rule set that the
chaos runner's scenario library happens not to probe.

### What the existing defense is good at

- Grain uniqueness (rule 007): solid.
- SOC format (rule 002): regex is strict enough to catch unicode
  hyphens AND embedded whitespace.
- Volume / coverage bands (rules 001, 008, 009): sufficient margin for
  O*NET version variance without being lax.
- Per-scale distinct-category count (rule 010): catches scale adding
  OR dropping a category.
- Sum-to-100 consistency (rule 005): tight tolerance, real max
  deviation 0.03 vs 0.1 rule limit.
- S7 empty-file fix: correctly raises at parse time, not post-load.

---

## 6. Verdict

**GAPS FOUND — 5 unrelated to S7 fix**

The S7 fix is verified: re-run shows `ValueError` raised; 58/58 rule
probes still caught; 442/442 raw tests pass; no rule is over-absorbed
by the fix.

**However**, independent adversarial probing surfaced 5 pre-existing
rule gaps (Gap A CRITICAL, Gaps B + E HIGH, Gap C MEDIUM, Gap D LOW)
that the chaos runner did not probe. Gap A in particular — an
unenforced `scale_id ↔ element_id` invariant that the EDA explicitly
documents as 1:1 but no rule tests — is a concrete regulator-visible
weakness: a malformed or re-formatted source could silently empty the
Silver table.

**Recommendation:**
1. Proceed with S7 closure — the fix is correct and proven.
2. Before Phase 3 (Silver) begins, re-open Phase 2 rule-writing to
   add at minimum the Gap A rule (scale_id × element_id pair
   enforcement) and the Gap B rule (per-scale category value ENUM).
3. Treat Gaps C, D, E as follow-up rule candidates that can be added
   alongside Silver DQ rule authorship without blocking Bronze.
4. Update the chaos runner scenario library to include mutators for
   each of these 5 gaps so they stay regression-tested.

Bronze is NOT YET ready to proceed as "CLEAN" in an adversarial sense.
The S7 gap is closed, but the rule coverage was not exhaustive to
begin with; this audit has surfaced what chaos-monkey's scenario set
missed. Per the spec's Phase 2 step 16 skip rule
(`bs:adversarial-auditor` may be skipped only if chaos-monkey
reports no gaps across 5 cycles), the auditor SHOULD NOT be skipped
and this report's findings should be remediated.

---

### Artifacts

- Fresh chaos run (post-fix): `governance/chaos-reports/onet-experience-20260417-013054.md`
- Independent probe script: `scripts/_adversarial_probe_onet_exp.py`
- This audit report: `governance/audit-reports/onet-experience-adversarial-20260417-013427.md`
