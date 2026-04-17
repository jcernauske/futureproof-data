# Insight Report: Silver → Gold — base.bea_rpp

**Date:** 2026-04-16
**Agent:** @insight-manager
**Source Table:** `base.bea_rpp` (Iceberg, Silver zone)
**Entities:** 51 (50 U.S. states + District of Columbia)
**Records:** 51 (exact — structural closed set)
**Time Range:** Single vintage, `data_year = 2024`
**Downstream consumers already shipped:** `consumable.regional_price_parities` (Gold), MCP tools `get_regional_price_parity` / `compare_purchasing_power` (65-case eval set, 16/16 DQ rules passing)

---

## Domain Context

BEA Regional Price Parities (RPPs) measure state-level price levels relative to the national average (national = 100.0). They are the canonical U.S. government reference for adjusting national salary figures to local purchasing power. The join key everywhere is the state (FIPS / USPS abbr / state name) — this dataset is **orthogonal to the SOC/CIP occupation-program join graph** that connects the other four data sources in FutureProof. It joins at query time, driven by the student's selected home state.

Relevant business terms already in the glossary: BT-098 RPP, BT-099 Purchasing Power Multiplier, BT-100 State FIPS, BT-101 State Name, BT-102 RPP Data Year, BT-103 USPS Abbreviation, BT-104 Census Region, BT-105 Data Verification Status.

---

## Executive Summary

Silver `base.bea_rpp` is the smallest and highest-confidence table in the pipeline: 51 rows, 100% non-null, 39/39 DQ rules passing, exact bijection between FIPS / USPS / state name, and a pre-computed `purchasing_power_multiplier` that is the single source of truth for salary adjustment across FutureProof. The one provenance caveat — 8 BEA-verified rows vs. 43 primary-agent estimates — is already surfaced per-row via the `verification_status` column, closing Bronze staff-review Condition 6. **The mandatory Tier-1 Gold product (`consumable.regional_price_parities`) is already specced AND built** (`docs/specs/gold-regional-price-parities.md`, `src/gold/regional_price_parities_transformer.py`); the MCP serving layer is also live with 65 passing eval cases. The highest-value remaining moves are (a) a lightweight **regional aggregate/ranking view** to power "compare my state to its region" LLM answers without recomputation, (b) a **location-lock feature** that joins RPP to BLS occupation geography so the Fight Location Lock boss from the PRD becomes buildable, and (c) a **post-hackathon refresh path** that flips `verification_status` from 8 to 51 `bea_official` rows when the live BEA API key lands.

---

## What Silver Already Provides (Authoritative Inventory)

| Field | Type | Role | Notes |
|---|---|---|---|
| `record_id` | string | PK | `compute_grain_id(..., prefix='rpp')`, deterministic |
| `state_fips` | string | Natural key | Zero-padded 2-digit; canonical 51-member FIPS set enforced |
| `state_name` | string | Display | Bijection with `state_fips` (P0 DQ) |
| `state_abbr` | string | **Join key for LLM / frontend** | 2-char uppercase USPS; the field Gemma actually receives from the frontend |
| `census_region` | string | Analytical dim | `Northeast / Midwest / South / West`; DC → South (documented Census quirk) |
| `rpp_all_items` | double | Core measure | National=100 scale; observed range **86.9 (AR) → 110.7 (CA)**, mean 96.98 |
| `purchasing_power_multiplier` | double | **Pre-computed salary scaler** | `100.0 / rpp_all_items`; observed range **0.9033 → 1.1507** |
| `verification_status` | string | Provenance | `bea_official` (8 rows) / `estimate` (43 rows) |
| `data_year` | int | Temporal | Constant 2024; supersession = full-table replace, not SCD2 |
| `source_load_date`, `ingested_at` | date/timestamp | Provenance | |

Cross-entity distributions observed in the live Iceberg table:
- `verification_status`: `{bea_official: 8, estimate: 43}` — matches P0 DQ rule SIL-BEA-023
- `census_region`: `{Northeast: 9, Midwest: 12, South: 17, West: 13}` — matches P1 DQ rule SIL-BEA-015 exactly
- `rpp_all_items`: [86.9, 110.7], spread ≈ 24 points, i.e. **~27% cost-of-living gap** between the cheapest and most expensive U.S. state
- `purchasing_power_multiplier`: [0.9033, 1.1507] — well inside the `[0.7, 1.3]` P0 sanity bound

---

## Data Products — Ranked

### Tier 1: High Value, High Feasibility (MANDATORY)

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|---|---|---|---|---|
| T1-1 | **`consumable.regional_price_parities`** | 51-row shaped reference with `cost_tier` + 4 pre-computed `adjusted_Nk` columns + `verification_status` carry-forward | `base.bea_rpp` | `adjusted_50k`, `cost_tier` | **Already built and signed off.** This is the canonical table Gemma's MCP tools read. Covered by 39/39 Silver rules + Gold DQ rules + 65 MCP eval cases. |

**Verification criteria:** `SELECT COUNT(*) FROM consumable.regional_price_parities = 51`; `cost_tier IN ('very_high','high','average','low','very_low')` for every row; `COUNT(*) WHERE verification_status='bea_official' = 8`; CA `adjusted_50k < 50000`; IA `adjusted_50k > 50000`. **All currently passing.** No new spec required — document this as the discharged Tier-1 obligation for the silver→gold transition.

### Tier 2: High Value, Moderate Effort (PROPOSED)

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|---|---|---|---|---|
| T2-1 | **`consumable.regional_price_parities_by_region`** | 4-row aggregate: min/median/mean/max `rpp_all_items`, state count, representative states per Census region | `base.bea_rpp` | `region_mean_rpp`, `region_rpp_spread` | Lets Gemma answer "how does my state compare to its region?" in one MCP call instead of fetching 51 rows and aggregating client-side. Mirrors the pattern Gemma already uses for BLS occupation groups. |
| T2-2 | **`consumable.rpp_state_ranks`** | Wide view adding `rpp_rank_national` (1..51, 1=most expensive), `rpp_rank_in_region`, `cost_percentile_national` to the existing 51 rows | `base.bea_rpp` | `rpp_rank_national` | Students ask "is my state cheap or expensive?" — rank is more intuitive than an index. Trivial derivation; no new source data needed. |
| T2-3 | **New MCP tool `rank_states_by_cost(direction, limit, region?)`** | Top/bottom-N purchasing-power states, optionally filtered to one Census region | `consumable.regional_price_parities_by_region` + `consumable.rpp_state_ranks` | returned list | Natural-language questions like "what are the 5 cheapest states in the South?" are currently unanswerable without Gemma doing 51-row arithmetic. A ranked-lookup tool is a direct win for the chat UX. |
| T2-4 | **`consumable.location_locked_occupations`** | Join `consumable.occupation_profiles` × `consumable.regional_price_parities` × (future) BLS state-level wage table to flag SOC codes where > X% of national employment sits in ≤ 3 states AND those states are `cost_tier IN ('high','very_high')` | `consumable.occupation_profiles`, `consumable.regional_price_parities`, BLS OES state wages (NEW SOURCE) | `location_lock_score` | **Unblocks the Fight Location Lock boss** from the PRD Tier-3 stretch. Requires one new Bronze ingest (BLS OES state wages). Without it, the boss is a dead concept. |

**Verification criteria (T2-1):** `COUNT(*) = 4`; `region IN ('Northeast','Midwest','South','West')`; `SUM(state_count) = 51`; passthrough invariant — the region's `region_mean_rpp` equals `AVG(rpp_all_items)` over the member rows within 1e-9.

**Verification criteria (T2-2):** `MIN(rpp_rank_national)=1, MAX=51`; `COUNT(DISTINCT rpp_rank_national)=51`; CA rank IN [1,3]; AR rank IN [49,51]; within each region, `MIN(rpp_rank_in_region)=1`.

**Verification criteria (T2-3):** MCP eval set adds ≥ 15 ranking cases ("top 5 cheapest", "bottom 3 in West", "rank New Jersey nationally"); every returned list is sorted and length ≤ `limit`; unknown region returns `data=null` with a non-empty helpful message (matches MCP-BEA-010 pattern).

**Verification criteria (T2-4):** schema includes `soc_code`, `location_lock_score` ∈ [0,1], `top_state_abbr`, `top_state_rpp`, `concentration_pct`; P0 rule that every row with `location_lock_score > 0.7` has ≥ 50% of national employment in ≤ 3 states; spot checks for 3 canonical location-locked careers (e.g., petroleum engineers, film/video editors, financial analysts) and 3 canonical non-locked careers (e.g., RN, K-12 teacher, accountant).

### Tier 3: Exploratory / Future (DOCUMENTED)

| # | Data Product | Description | Dependency | Why It Matters |
|---|---|---|---|---|
| T3-1 | **MSA-level RPP** | BEA also publishes RPPs for metropolitan statistical areas (~380 MSAs) | New Bronze ingest from BEA SARPP MSA table | Students picking "Austin" vs. "rural TX" get radically different purchasing power. State-level is a crude proxy. |
| T3-2 | **Temporal RPP (2008 → 2024)** | BEA publishes RPPs back to 2008; a time-series lets Gemma narrate cost-of-living drift | New Bronze ingest (same BEA table, wider year range) | Powers the "your parents' paycheck in your city" kind of question; good for Gemma Take color commentary |
| T3-3 | **RPP component breakdown** | BEA also publishes RPPs for Goods, Services, and Rents separately | New Bronze ingest (LineCode 2/3/4 instead of just 1=All Items) | Rent is the largest component of cost differences; splitting it out lets the UI explain *why* California is expensive |
| T3-4 | **County-level BLS QCEW cost proxies** | Join state RPP with county-level employment density to approximate sub-state purchasing power | New Bronze ingest (QCEW) + state→county disaggregation heuristic | Higher engineering effort, lower confidence than T3-1 (MSA). Prefer MSA. |

---

## Cross-Entity Coverage Matrix

| CDE / Attribute | Entities Reporting | Time Range | Coverage Quality | Notes |
|---|---|---|---|---|
| `state_fips` | 51 / 51 | 2024 | 100%, canonical | Zero-padded, bijection-enforced |
| `state_abbr` | 51 / 51 | 2024 | 100% | Primary LLM-facing key |
| `census_region` | 51 / 51 | 2024 | 100% | DC → South (documented) |
| `rpp_all_items` | 51 / 51 | 2024 | 100% non-null; 8/51 BEA-verified | The provenance asymmetry is the one real gap |
| `purchasing_power_multiplier` | 51 / 51 | 2024 | 100% | Derived; inverse invariant checked |
| `verification_status` | 51 / 51 | 2024 | 100% | `{bea_official:8, estimate:43}` |

All downstream consumers (frontend, Gold transformer, MCP tools) consume exactly this grain. No sparsity. No missing joins. The cross-entity coverage is as good as this domain allows.

---

## External Data Opportunities

| External Source | Join Key | What It Unlocks | Effort | Priority |
|---|---|---|---|---|
| **BLS OES State-Level Wage Data** (`https://www.bls.gov/oes/current/oes_research_estimates.htm`) | `(soc_code, state_abbr)` | State-level median wage × state RPP = *location-adjusted* earnings per SOC. **Directly powers Fight Location Lock boss (T2-4) and unlocks "what does this career pay *where I live*" — the single most requested feature implied by the PRD.** | Medium (~1 day Bronze + Silver; BLS OES is CSV, ~2M rows, well-documented) | **P0 (highest external ROI)** |
| **BLS OES MSA-Level Wage Data** | `(soc_code, msa_cbsa_code)` | Combined with T3-1 (MSA-level RPP), enables true metro-level salary adjustment | Medium+ | P2 (blocked on T3-1) |
| **Census ACS Median Household Income by State** | `state_fips` | Context column on the Gold table — "the state's RPP-adjusted median household income" — gives Gemma a reference point for "is this salary actually good here?" | Small (~2 hours; ACS 1-year is trivial API) | P1 |
| **HUD Fair Market Rent by State** | `state_fips` | Separates the rent component of cost of living — addresses T3-3 gap without waiting for BEA component data | Small | P1 |
| **BEA Regional Personal Income** | `state_fips` | Ratios of RPP to personal income growth reveal states where cost of living is outrunning wages (i.e., getting worse to live in) | Small | P2 — nice-to-have, not core |

---

## Coverage Gaps & Risks

| Gap | Impact | Mitigation |
|---|---|---|
| 43/51 rows are primary-agent **estimates**, not BEA-verified | All non-verified states report RPP with unknown precision. For the hackathon demo, this is hedged via `verification_status` + MCP strict-mode refusal, but it is the single largest data-quality liability in the entire FutureProof pipeline. | Post-hackathon, register for a BEA API key, run the live API refresh; the Silver and Gold DQ rules `COUNT(*) WHERE verification_status='bea_official' = 8` are explicitly designed to flip to `= 51` with a one-line allow-list change. No schema changes needed. |
| Only **state-level** granularity | California RPP (110.7) averages SF Bay (very high) with Central Valley (low). Students in low-cost regions of high-cost states get a misleading adjustment, and vice versa. | Tier 3 MSA-level RPP (T3-1). Defer until post-hackathon. |
| Only **All Items** RPP | Rent drives most of the state-level variance; students asking "is housing expensive where I want to live?" cannot get a direct answer from the current table. | Tier 3 component RPPs (T3-3) or HUD FMR external join. Low effort for HUD path. |
| **Single vintage** (2024 only) | Cannot answer "is my state getting more expensive?" | Tier 3 temporal ingest (T3-2). Low priority for MVP. |
| The Gold/MCP layers are already built and running — anything we ship now is **additive**, not remedial | No risk of breaking existing consumers, but any new table must not collide on the `rpp`/`rpc` record_id namespace | New tables must use new grain prefixes (e.g., `rpr` for regional rollup, `rps` for state-rank, `rll` for location-lock) |

---

## AI-Ready Considerations

The BEA RPP dataset is already exceptionally LLM-friendly for three reasons:

1. **Small, closed, and structural.** 51 rows that every American knows by name. No entity resolution issues, no temporal drift, no sparsity.
2. **Pre-computed multipliers.** `purchasing_power_multiplier` and the four `adjusted_Nk` columns mean Gemma never has to do arithmetic — it just reads a value. This is the correct shape for small-model inference.
3. **Provenance surfaced per row.** `verification_status` lets Gemma hedge estimate rows ("this state's RPP is an approximation pending BEA's live data…") without the caller having to know the data history.

What would make it even better:

- **Natural-language cost-tier descriptions.** Add a `cost_tier_description` column to Gold (e.g., `very_high` → "significantly more expensive than the national average; expect 8–11% less purchasing power on a national salary"). Let Gemma quote the description verbatim instead of paraphrasing. Low effort, high grounding benefit.
- **Pre-computed region comparisons.** T2-1 (`_by_region`) gives Gemma a one-query path to "your state vs. its region" framing.
- **Pre-computed rank text.** T2-2's `rpp_rank_national` lets Gemma say "your state is the 17th most expensive" without counting.
- **Grounding snippet in MCP responses.** The MCP tool already returns `governance.quality_tier='partial_verification'` and `governance.owner='@doc-generator'` (see MCP-BEA-002 remediation). A short `governance.narrative` string — one sentence explaining what RPP is — would save Gemma from hallucinating the definition.

---

## Chat Agent (MCP) Design Considerations

The MCP layer for RPP is already live with 65 eval cases covering 11 spec requirement categories. The design considerations below are **forward-looking** — what additional tooling would improve LLM UX if the Tier-2 products land:

**Current tools work well for:**
- Point-lookup: "what's the RPP in California?" (`get_regional_price_parity`)
- 2-state comparison: "California vs. Iowa at $65K" (`compare_purchasing_power`)
- Verification hedging: "is this number official?" (strict mode)
- Bad-input robustness: 7/7 unknown-state and 7/7 invalid-salary cases return `data=null` with helpful messages — zero exceptions

**Questions the current tools can't answer well:**
1. **Ranking questions.** "What are the 5 cheapest states?" → would require 51 point-lookups. Needs T2-3 `rank_states_by_cost`.
2. **Regional comparison.** "How does my state compare to the rest of the Midwest?" → would require 12 point-lookups and aggregation. Needs T2-1 `consumable.regional_price_parities_by_region` + a new `get_region_summary(region)` tool.
3. **"Where should I move for this career?"** — the archetypal FutureProof question. Needs T2-4 `consumable.location_locked_occupations` + a new `recommend_states_for_career(soc_code)` tool.

**Recommended eval-set extensions (for future MCP specs building on T2-1 through T2-4):**

| Category | Minimum cases | Notes |
|---|---|---|
| Point lookup (existing) | 16 | Already covered |
| 2-state compare (existing) | 16+ | Already covered |
| Ranking | 10 | "Top N cheapest", "Bottom N in West", mixed directions |
| Regional aggregate | 8 | One per region + 4 cross-region comparisons |
| Location-lock | 10 | 3 canonical locked careers + 3 canonical portable careers + 4 edge cases |
| Edge cases | 10 | Territory attempts (PR, GU), ZIP codes, city names, ambiguous inputs |
| **Minimum total for a Tier-2-expanded MCP spec** | **70** | vs. the current 65 |

---

## Priorities and Dependencies

```
T1-1 (Gold table) — DONE
   └── MCP tools — DONE
T2-1 (regional aggregate)   ── depends only on base.bea_rpp          ← safest, smallest win
T2-2 (state ranks)          ── depends only on base.bea_rpp          ← trivial
T2-3 (rank_states_by_cost tool) ── depends on T2-1 and T2-2
T2-4 (location_locked_occupations)
   └── REQUIRES new Bronze ingest: BLS OES state-level wages
   └── REQUIRES Silver/Gold join tables over (soc_code, state_abbr)
   └── Directly unblocks Fight Location Lock boss (PRD Tier-3 stretch)
T3-1..T3-4 — deferred to post-hackathon
```

Dependency note: nothing in Tier 2 requires schema changes to existing tables. Everything is additive. The only blocking dependency is **BLS OES state wages** for T2-4, and that is a standalone Bronze ingest comparable in size to the existing BLS OOH ingest.

---

## Recommended Spec Order

1. **`gold-regional-price-parities-by-region`** — T2-1. Smallest possible Gold spec: 4-row aggregate, 2 hours end-to-end with governance. Gate-widens the "compare to my region" question.
2. **`gold-rpp-state-ranks`** — T2-2. Either a new 51-row view or two new columns on `consumable.regional_price_parities`. Trivial.
3. **`mcp-rank-states-by-cost`** — T2-3. Adds the `rank_states_by_cost` MCP tool and ~15 eval cases.
4. **`raw-ingest-bls-oes-state-wages`** — NEW SOURCE. Prerequisite for T2-4.
5. **`silver-base-bls-oes-state-wages`** — Normalize wage by (soc_code, state_abbr).
6. **`gold-location-locked-occupations`** — T2-4. The Fight Location Lock enabling table.
7. **`mcp-recommend-states-for-career`** — New MCP tool fronting T2-4.
8. Post-hackathon follow-ups: BEA API refresh (flip 43 estimates → bea_official), T3-1 MSA-level ingest.

Specs 1–3 are the safest "ship it this week" path. Specs 4–7 require one new data source but unlock the most talked-about stretch feature in the PRD.

---

## Discharged Obligations (Audit Trail)

- Mandatory Tier-1 "deduplicated metrics table" for this zone transition: **`consumable.regional_price_parities`** — already built (`src/gold/regional_price_parities_transformer.py`), specced (`docs/specs/gold-regional-price-parities.md`), DQ-rule'd, and MCP-served. No new spec required.
- Bronze Condition 6 (per-row `verification_status`): **closed** at Silver (rule SIL-BEA-022).
- Bronze Condition 7 (Gold carry-forward of `verification_status`): **closed** at Gold (per `docs/specs/gold-regional-price-parities.md` §Bronze Staff Review Conditions).
- MCP Condition 7 extension (strict-mode refusal of estimate rows): **closed** by MCP-BEA-007 / MCP-BEA-008 / MCP-BEA-009.
- Post-hackathon BEA API refresh path: **specified** — the allow-list constant `BEA_VERIFIED_FIPS` in `src/silver/_us_state_reference.py` plus three DQ count rules are the only three places that need to change.

---

*— End of Insight Report —*
