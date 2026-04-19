# Completion Report — Disable Intent YAML Short-Circuit + Run 56-Input Regression

**Spec:** [`docs/specs/bugfix-disable-intent-yaml-regression.md`](../docs/specs/bugfix-disable-intent-yaml-regression.md)
**Generated:** 2026-04-19
**Regression report:** [`reports/intent-yaml-regression-2026-04-19.md`](intent-yaml-regression-2026-04-19.md)

---

## TL;DR — DO NOT disable the YAML in production

Gemma alone (no school context, OpenRouter `google/gemma-4-26b-a4b-it`, temperature=0 + input-derived seed) matched the hand-curated YAML on **20 of 219 inputs (9.1%)**. Family 13 (Education) was a complete miss — **0/147 matches**. Family 52 (Business) hit **20/72 (27.8%)**.

The Set Your Course commitment to disable the YAML in production is **rejected on the data**. Recommended action: **keep `INTENT_YAML_ENABLED=true` in prod**. The gate ships defaulted to true, so this is the no-op outcome — the regression simply confirmed the YAML is doing the work the curator built it to do.

---

## Run details

| Field | Value |
|-------|-------|
| Backend | OpenRouter (`google/gemma-4-26b-a4b-it`) |
| Total inputs | 219 (55 distinct YAML entries × ~4 aliases each) |
| Matches | 20 (9.1%) |
| Mismatches | 182 (83.1%) |
| Errors | 17 (7.8%) |
| Wall time | 974 s (~16 min) |
| Confidence breakdown | high=146, medium=50, low=6 |
| Audit prompt | Skipped (per §2 decision #7) |
| `school_name` / `unitid` / `programs` | "University of Central Anywhere" / 0 / `[]` (per §4 example — no school anchor) |

### Errors

17 errors split into two categories:

- **2 malformed Gemma JSON** (`'S11.0101'`, `'S1.0011'`): Gemma prefixed a leaf code with the letter `S`. The strict `_CIP_PATTERN` rejected the response. Inputs: `speech education` (13.1012), `language teaching` (13.1306). Real Gemma defects, not transport failures.
- **15 empty Gemma responses** at the tail of the run (CIP families 52.17–52.21, all 250–350 ms latency, all `Gemma could not resolve …`). The pattern (clustered, sub-second, last 30 inputs) is consistent with OpenRouter rate-limiting kicking in late in the run. Inputs spanning Insurance, General Sales, Specialized Sales, Construction Management, Telecommunications Management. Re-running just those 15 would likely change a few to MISS but not to MATCH given Family 52's overall 28% rate.

Errors do not change the disable-YAML decision — even if all 17 had landed as matches, 37/219 = 17% is still well below "safe to disable."

---

## Family-level breakdown

| Family | Inputs | Matches | Rate | Verdict |
|--------|--------|---------|------|---------|
| 13 — Education | 147 | 0 | 0.0% | **KEEP** entire family in YAML |
| 52 — Business | 72 | 20 | 27.8% | **KEEP** most; **ACCEPT-VARIANCE** for 5 entries |

Family 13's wipeout is the load-bearing finding. Gemma's primary failure mode in education is family-scattering: it picks 21.0101 (Bilingual/Bicultural Education proper), 37.0101 (Educational Counseling), 13.1501 (Higher Ed/Teaching), or 14.XXXX (engineering education) for inputs the YAML maps cleanly to a 13.XX leaf. Without the school's reported CIP list to anchor against, Gemma has no signal that disambiguates "school administration" → 13.04 (Educational Leadership) from 37.0101 (general administration training).

---

## Per-entry recommendations

### KEEP-IN-YAML (50 entries)

All 38 Family 13 entries plus 12 Family 52 entries with <50% Gemma match rate. Gemma cannot reliably resolve these without school context; keep the curated mapping.

| CIP | Major | Gemma matches |
|-----|-------|---------------|
| 13.02 | Bilingual Education | 0/4 |
| 13.03 | Curriculum and Instruction | 0/4 |
| 13.04 | Educational Leadership | 0/5 |
| 13.05 | Instructional Technology | 0/4 |
| 13.10 | Special Education | 0/4 |
| 13.1003 | Deaf Education | 0/6 |
| 13.1005 | Education of the Emotionally Disturbed | 0/4 |
| 13.1006 | Intellectual Disabilities Education | 0/3 |
| 13.1009 | Education of the Visually Impaired | 0/5 |
| 13.1011 | Learning Disabilities Education | 0/4 |
| 13.1012 | Speech-Language Impairments Education | 0/3 (+1 err) |
| 13.1013 | Autism Education | 0/3 |
| 13.1015 | Early Childhood Special Education | 0/4 |
| 13.1101 | School Counseling | 0/4 |
| 13.1201 | Adult Education | 0/3 |
| 13.1202 | Elementary Education | 0/5 |
| 13.1203 | Middle School Education | 0/5 |
| 13.1205 | Secondary Education | 0/5 |
| 13.1209 | Kindergarten Education | 0/3 |
| 13.1210 | Early Childhood Education | 0/6 |
| 13.1301 | Agricultural Education | 0/4 |
| 13.1302 | Art Education | 0/3 |
| 13.1303 | Business Education | 0/3 |
| 13.1305 | English Education | 0/5 |
| 13.1306 | Foreign Language Education | 0/3 (+1 err) |
| 13.1307 | Health Education | 0/3 |
| 13.1311 | Math Education | 0/4 |
| 13.1312 | Music Education | 0/3 |
| 13.1314 | Physical Education | 0/5 |
| 13.1315 | Reading Education | 0/4 |
| 13.1316 | Science Education | 0/3 |
| 13.1318 | Social Studies Education | 0/4 |
| 13.1322 | Biology Education | 0/3 |
| 13.1323 | Chemistry Education | 0/2 |
| 13.1324 | Drama Education | 0/4 |
| 13.1328 | History Education | 0/2 |
| 13.1329 | Physics Education | 0/2 |
| 13.1401 | ESL Education | 0/6 |
| 52.03 | Accounting | 1/4 |
| 52.08 | Finance | 0/4 |
| 52.09 | Hospitality Management | 0/5 |
| 52.10 | Human Resources | 0/5 |
| 52.11 | International Business | 0/4 |
| 52.15 | Real Estate | 0/3 |
| 52.16 | Taxation | 0/3 |
| 52.17 | Insurance | 0/3 (+2 err) |
| 52.18 | General Sales | 0/4 (+4 err) |
| 52.19 | Specialized Sales | 0/3 (+3 err) |
| 52.20 | Construction Management | 0/3 (+3 err) |
| 52.21 | Telecommunications Management | 0/3 (+3 err) |

### ACCEPT-VARIANCE candidates (5 entries, ≥50% match)

These could plausibly be served by Gemma alone, but the YAML still wins on speed and cost — there's no benefit to removing them. Listed here only so a future Set Your Course iteration knows where Gemma is competent if the conversational UI needs to narrate these inputs live.

| CIP | Major | Gemma matches | Notes |
|-----|-------|---------------|-------|
| 52.02 | Supply Chain Management | 6/10 (60%) | Borderline. Misses on `operations management`, `logistics`, `SCM` (Gemma scattered to 42.08xx Industrial Psych and 52.05 Operations Management). |
| 52.07 | Entrepreneurship | 3/4 (75%) | Misses only `small business` (Gemma → 52.0201 Business Admin). |
| 52.12 | Management Information Systems | 4/5 (80%) | Misses only `info systems` shorthand. |
| 52.13 | Business Analytics | 3/5 (60%) | Misses on `BA` and one alias. |
| 52.14 | Marketing | 3/4 (75%) | Misses only `mktg` shorthand. |

### REFINE-PROMPT recommendations

None recommended as a path to disabling the YAML. The Family-13 failure is **systematic, not phrase-specific** — Gemma scatters across at least 6 different families (13, 14, 21, 37, 42, 51) for education inputs. A prompt rewrite could close some specific phrasing gaps but would not close the 0/147 gap.

If we want better Gemma performance on uncovered inputs (the long-tail majors not in YAML), the bigger lever is **giving Gemma the school's reported CIP list** — the regression intentionally ran with `unitid=0` + `programs=[]` to test Gemma in isolation, but production already passes the school's CIPs. Re-running this regression with a real school context (e.g., Indiana University-Bloomington's program list) would give a closer-to-prod read; that's a separate spec.

---

## Decision for Set Your Course

The Set Your Course PRD assumed: *"every input goes through Gemma so the student sees Gemma reasoning live."* This regression rejects that assumption for the 56 hand-curated entries. Two paths forward, both compatible with shipping the gate:

1. **Keep YAML enabled.** Set Your Course routes YAML hits through the conversational UI for narration but does not re-derive the CIP. Gemma still appears live for the long tail (the ~4500 unique inputs students could type that aren't in the YAML).
2. **Pass school context to the regression.** Re-run the script with a real school's `programs` list before any disable-YAML decision. The 9.1% number is a worst-case (school-blind) read; with school CIPs, Gemma would likely match higher.

The bugfix's real ship value: the gate (`INTENT_YAML_ENABLED`) is in place and tested. We can flip it false at any time the data justifies it. Today's data does not.

---

## Cost

OpenRouter cost not surfaced by the script (no token-counting hook in `gemma_client`). Wall time of 974 s × ~150 tokens/response × $0.0006/1k output tokens × 219 calls ≈ ~$0.02 — well under the §2 estimate of $0.50.

---

## Spec actions

- [x] Regression run executed (`reports/intent-yaml-regression-2026-04-19.md`)
- [x] Completion report written (this file)
- [x] Spec §6 Regression Run table filled
- [x] Spec status flipped to COMPLETE
- [x] Spec moved to `docs/specs/completed/`
