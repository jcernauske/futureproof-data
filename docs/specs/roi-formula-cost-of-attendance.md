# Spec: roi-formula-cost-of-attendance

**Status:** DRAFT
**Zone:** Backend service + frontend display
**Primary Agent:** @fp-builder
**Created:** 2026-04-14
**Depends On:** `raw-ingest-college-scorecard-institution` (pipeline must be complete first)

---

## Problem Statement

ROI currently uses `debt_median` (what past graduates borrowed) as the cost input. This is misleading — median debt reflects borrowing behavior, not what school actually costs. A student on a full scholarship sees the same ROI as a student who financed everything, because the loan slider scales against the same `debt_median` value.

With institution-level cost data now available (from the `raw-ingest-college-scorecard-institution` pipeline), ROI should reflect the student's actual financing decision:

**New formula:** `ROI = earnings / (net_price_annual × 4 × loan_pct)`

**Old formula:** `ROI = earnings / (debt_median × loan_pct)`

The median debt stays visible as a reference point: "The median debt of graduates from this program is $X" — giving the student a reality check against their modeled number.

## What Changes

### 1. Stat Engine — ROI Computation

**File:** `backend/app/services/stat_engine.py`

**Current behavior:** ROI score (1-10) is derived from `debt_to_earnings_annual`, which uses `debt_median` from the field-of-study Scorecard data, scaled by `loan_pct`.

**New behavior:**
```python
# If net_price_annual is available (from institution-level Scorecard):
modeled_debt = net_price_annual * 4 * loan_pct
debt_to_earnings = modeled_debt / earnings_1yr_median

# Fallback: if net_price_annual is null for this institution:
modeled_debt = debt_median * loan_pct  # existing formula
```

The ROI score (1-10 scale) is derived from `debt_to_earnings` using the same threshold buckets as today — only the input debt figure changes.

**New fields on CareerOutcome:**
```python
# Add to CareerOutcome model (backend/app/models/career.py)
net_price_annual: float | None = None          # From institution-level Scorecard
cost_of_attendance_annual: float | None = None  # Full sticker price
modeled_total_debt: float | None = None         # net_price × 4 × loan_pct (computed)
debt_median_reference: float | None = None      # Renamed from debt_median — now a reference, not a driver
institution_control: str | None = None          # "Public" / "Private nonprofit" / "Private for-profit"
tuition_in_state: float | None = None           # For receipts
tuition_out_of_state: float | None = None       # For receipts
room_board_on_campus: float | None = None       # For receipts
```

**Note:** `debt_median` field stays on the model (don't remove it — it's used elsewhere). Add `debt_median_reference` as an alias that's clearer about its new role.

### 2. Fight Student Loans — Threshold Re-tuning

**File:** `backend/app/services/boss_fights.py`

The loans boss tests ROI. Since ROI inputs change, the fight thresholds may need adjustment.

**Action:** After the ROI formula change lands, run the CLI against 10-20 representative school+major combos and compare old vs. new fight results. If the distribution shifts significantly (e.g., most students who used to win now lose), adjust `BOSS_SPECS["loans"].win_at_or_above` and `draw_at_or_above`.

**Expected behavior:** Net price is typically lower than median debt for well-aided students (ROI improves) but can be higher for students at expensive schools with less aid (ROI worsens). The distribution should spread out, not uniformly shift.

### 3. Receipts — Cost Breakdown

**File:** `backend/app/services/receipts.py`

The ROI receipt gets significantly richer:

```
ROI Receipt:
├── School: Indiana State University (Public)
├── Net price per year: $14,200 (after grants/scholarships)
├── Cost of attendance per year: $22,800 (sticker price)
├── Your loan coverage: 75%
├── Your modeled 4-year debt: $42,600 (net_price × 4 × 75%)
├── Median debt of graduates from this program: $28,400
├── Your modeled debt vs. median: +$14,200 above typical
├── 1-year post-grad earnings: $48,000
├── Debt-to-earnings ratio: 0.89
├── ROI score: 7/10
└── Sources: College Scorecard (Field of Study + Institution Level)
```

The "Your modeled debt vs. median" line is the transparency moment — it shows the student how their financing decision compares to what graduates actually ended up owing.

### 4. Fight Student Loans — Narrative Enhancement

**File:** `backend/app/services/boss_fights.py` (narrative prompt)

Update the boss fight narrative prompt for Fight Student Loans to include cost context:

```python
# Add to the narrative prompt:
f"School net price: ${int(career.net_price_annual):,}/year"
f"Student's modeled 4-year debt: ${int(career.modeled_total_debt):,}"
f"Median debt of graduates from this program: ${int(career.debt_median_reference):,}"
```

This gives Gemma the context to say things like: "Your modeled debt is $14K above what typical graduates owe — that's the cost of financing 75% at a school where net price is $14,200/year. The median grad only borrowed $28K, which suggests many students at this school had significant scholarship or family support."

### 5. Frontend — Loan Slider Context

**Files:** Frontend components consuming the loan slider.

The loan slider subtitle should update to reflect what it's actually scaling:

**Current:** "How much of your school costs will you cover with loans?"

**New (when net_price_annual is available):**
- Subtitle: "How much of your school costs will you cover with loans?"
- Below slider: Space Mono, `text-data-sm`, `text-muted` — "${net_price_annual}/yr × 4 years = ${net_price_4yr} total"
- As slider moves: show the modeled debt updating live — "At {loan_pct}%: ${modeled_debt} in loans"

**Fallback (no net_price data):** Keep existing behavior with debt_median.

### 6. Frontend — ROI Stat Detail

The stat detail card for ROI (on the reveal screen) should show:

- ROI score (unchanged display)
- "?" receipt expands to show the full cost breakdown from §3 above
- If `modeled_total_debt > debt_median_reference * 1.2`: show a subtle caution indicator — "Your modeled debt is significantly above the program median"
- If `modeled_total_debt < debt_median_reference * 0.8`: show a thrive indicator — "Your modeled debt is well below the program median"

### 7. TypeScript Type Updates

**File:** `frontend/src/types/build.ts`

Add to `CareerOutcome`:
```typescript
net_price_annual: number | null;
cost_of_attendance_annual: number | null;
modeled_total_debt: number | null;
debt_median_reference: number | null;
institution_control: string | null;
tuition_in_state: number | null;
tuition_out_of_state: number | null;
room_board_on_campus: number | null;
```

---

## What Does NOT Change

- **ERN stat** — still based on earnings, unaffected by cost data
- **RES, GRW, HMN stats** — unaffected
- **Fight AI, Fight the Market, Fight Burnout, Fight the Ceiling** — unaffected
- **Branch tree** — branches don't carry cost data
- **Pentagon chart rendering** — unchanged
- **Stat tutorial content** — ROI explanation stays the same ("Compares your expected earnings to your student debt. Your loan percentage drives this.")
- **Compare screen** — works with whatever ROI the backend produces

---

## Migration / Backward Compatibility

- The new fields on `CareerOutcome` are all nullable with defaults of `None`. Existing builds without institution-level data continue to work — the stat engine falls back to `debt_median` when `net_price_annual` is null.
- No database migration needed — builds are stored in memory (not persisted across restarts in the hackathon).
- The Gold engine update (`consumable.career_outcomes` LEFT JOIN) means the MCP queries that power the stat engine will start returning the new fields automatically once the pipeline runs.

---

## Testing

| Priority | Test | What It Validates |
|----------|------|-------------------|
| P0 | ROI with net_price_annual | New formula produces 1-10 score |
| P0 | ROI fallback to debt_median | When net_price_annual is null, old formula still works |
| P0 | modeled_total_debt computation | net_price × 4 × loan_pct matches expected |
| P0 | Fight Student Loans still scores | Boss fight works with new ROI inputs |
| P1 | Receipt includes cost breakdown | Receipt string contains net_price, modeled_debt, debt_median_reference |
| P1 | Narrative prompt includes cost context | Gemma prompt contains the new financial context |
| P1 | Loan slider shows modeled debt | Frontend displays live modeled debt as slider moves |
| P2 | Threshold validation | Run 20 school+major combos, compare old vs. new fight results |

---

## Estimated Effort

| Step | Estimate |
|------|----------|
| CareerOutcome model update (add fields) | 30 min |
| Stat engine ROI formula change + fallback | 1 hour |
| Receipts update (cost breakdown) | 30 min |
| Boss fight narrative prompt update | 30 min |
| TypeScript type update | 15 min |
| Frontend loan slider context display | 1 hour |
| Threshold validation (20 combos) | 1 hour |
| **Total** | **~5 hours** |

**Sequencing:** This spec can ONLY execute after `raw-ingest-college-scorecard-institution` completes the full pipeline (Bronze → Silver → Gold). The Gold engine update adds the new fields to the MCP queries. Then this spec wires those fields through the stat engine, boss fights, receipts, and frontend.

---

## Kaggle Writeup Impact

This change strengthens the "students deserve trustworthy data" narrative:

- **Before:** "ROI uses median graduate debt — a proxy for what you might owe."
- **After:** "ROI uses actual school cost-of-attendance, scaled by your loan coverage. We also show you the median debt of graduates from your specific program, so you can see how your financing decision compares to reality."

The transparency angle — showing modeled debt alongside median debt — is a differentiator. Most tools show one number. FutureProof shows both and explains the gap.

---

*— End of Spec —*
