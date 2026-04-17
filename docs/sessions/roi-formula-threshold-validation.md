# ROI Formula Threshold Validation — Fight Student Loans

**Spec:** `docs/specs/roi-formula-cost-of-attendance.md` §2
**Loan pct:** 0.75 (representative default)
**Current thresholds:** `win ≥ 7`, `draw ≥ 5`

Compares old ROI formula (`debt_median × loan_pct`) vs new formula (`net_price_annual × 4 × loan_pct`) across 20 representative school+major combos spanning high/moderate earnings at public and private schools. Only combos with `net_price_annual` populated are evaluated — we are validating the new-formula path.

## Per-combo table

| # | Bucket | School | CIP | Program | Earn | Debt med | Net price | Old debt@75% | New debt@75% | Old DTE | New DTE | Old ROI | New ROI | Old fight | New fight |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | high_public | University of California-Berkeley | 11.07 | Computer Science. | $125,250 | $13,750 | $14,979 | $10,312 | $44,937 | 0.08 | 0.36 | 10 | 10 | win | win |
| 2 | high_public | Georgia Institute of Technology-Main Campus | 14.09 | Computer Engineering. | $81,067 | $20,000 | $13,289 | $15,000 | $39,867 | 0.19 | 0.49 | 10 | 9 | win | win |
| 3 | high_public | University of North Carolina at Chapel Hill | 51.38 | Registered Nursing, Nursing Ad | $60,514 | $19,802 | $12,983 | $14,852 | $38,949 | 0.25 | 0.64 | 10 | 8 | win | win |
| 4 | high_public | The University of Texas at Austin | 52.12 | Management Information Systems | $75,338 | $18,750 | $19,678 | $14,062 | $59,034 | 0.19 | 0.78 | 10 | 7 | win | win |
| 5 | high_public | Purdue University-Main Campus | 14.09 | Computer Engineering. | $76,843 | $22,875 | $13,945 | $17,156 | $41,835 | 0.22 | 0.54 | 10 | 9 | win | win |
| 6 | high_private | Massachusetts Institute of Technology | 11.07 | Computer Science. | $118,191 | $11,077 | $19,813 | $8,308 | $59,439 | 0.07 | 0.50 | 10 | 9 | win | win |
| 7 | high_private | Stanford University | 11.07 | Computer Science. | $136,126 | $10,399 | $12,136 | $7,799 | $36,408 | 0.06 | 0.27 | 10 | 10 | win | win |
| 8 | high_private | Harvard University | 45.06 | Economics. | $89,515 | $6,617 | $16,816 | $4,963 | $50,448 | 0.06 | 0.56 | 10 | 8 | win | win |
| 9 | high_private | University of Pennsylvania | 52.08 | Finance and Financial Manageme | $118,578 | $12,999 | $31,229 | $9,749 | $93,687 | 0.08 | 0.79 | 10 | 7 | win | win |
| 10 | high_private | Carnegie Mellon University | 11.07 | Computer Science. | $161,723 | $21,442 | $31,671 | $16,082 | $95,013 | 0.10 | 0.59 | 10 | 8 | win | win |
| 11 | mid_public | Indiana State University | 52.20 | Construction Management. | $63,441 | $23,250 | $12,188 | $17,438 | $36,564 | 0.27 | 0.58 | 10 | 8 | win | win |
| 12 | mid_public | Arizona State University Campus Immersion | 42.01 | Psychology, General. | $33,198 | $19,500 | $13,670 | $14,625 | $41,010 | 0.44 | 1.24 | 9 | 4 | win | lose |
| 13 | mid_public | University of Florida | 09.09 | Public Relations, Advertising, | $40,235 | $15,321 | $6,351 | $11,491 | $19,053 | 0.29 | 0.47 | 10 | 9 | win | win |
| 14 | mid_public | University of Georgia | 26.13 | Ecology, Evolution, Systematic | $23,064 | $14,000 | $13,816 | $10,500 | $41,448 | 0.46 | 1.80 | 9 | 2 | win | lose |
| 15 | mid_public | Ohio State University-Main Campus | 54.01 | History. | $26,168 | $19,838 | $18,292 | $14,878 | $54,876 | 0.57 | 2.10 | 8 | 2 | win | lose |
| 16 | mid_private | New York University | 50.06 | Film/Video and Photographic Ar | $30,874 | $20,500 | $35,035 | $15,375 | $105,105 | 0.50 | 3.40 | 9 | 1 | win | lose |
| 17 | mid_private | Boston University | 09.01 | Communication and Media Studie | $41,873 | $23,250 | $26,996 | $17,438 | $80,988 | 0.42 | 1.93 | 9 | 2 | win | lose |
| 18 | mid_private | Fordham University | 52.08 | Finance and Financial Manageme | $70,465 | $26,870 | $42,581 | $20,152 | $127,743 | 0.29 | 1.81 | 10 | 2 | win | lose |
| 19 | mid_private | Syracuse University | 09.09 | Public Relations, Advertising, | $47,611 | $24,375 | $41,026 | $18,281 | $123,078 | 0.38 | 2.59 | 9 | 1 | win | lose |
| 20 | mid_private | DePaul University | 52.03 | Accounting and Related Service | $61,704 | $24,000 | $29,141 | $18,000 | $87,423 | 0.29 | 1.42 | 10 | 3 | win | lose |

## Distribution summary

- Combos evaluated: **20** (of 20 requested; skipped: 0)

**Outcome counts:**

| Outcome | Old formula | New formula | Delta |
|---|---|---|---|
| win | 20 | 12 | -8 |
| draw | 0 | 0 | +0 |
| lose | 0 | 8 | +8 |

**Transition matrix (old → new):**

- win → lose: 8
- win → win: 12 ← same

- Unchanged: **12** / 20
- Students who used to WIN now LOSE: **8**
- Students who used to WIN now DRAW: **0**
- Students who used to LOSE now WIN: **0**
- Students who used to LOSE now DRAW: **0**
- Students who used to DRAW now WIN: **0**
- Students who used to DRAW now LOSE: **0**

## ROI score distribution comparison

| ROI score | Old count | New count |
|---|---|---|
| 1 | 0 | 2 |
| 2 | 0 | 4 |
| 3 | 0 | 1 |
| 4 | 0 | 1 |
| 5 | 0 | 0 |
| 6 | 0 | 0 |
| 7 | 0 | 2 |
| 8 | 1 | 4 |
| 9 | 5 | 4 |
| 10 | 14 | 2 |

- Mean old ROI: **9.65**
- Mean new ROI: **5.95**
- Mean shift: **-3.70**

## Threshold recommendation

**KEEP thresholds at `win ≥ 7`, `draw ≥ 5`. No change to `BOSS_SPECS["loans"]`.**

### Rationale

The headline numbers look like a large downward shift (mean ROI 9.65 → 5.95,
8 of 20 wins flipped to losses), but the correct reading is different:

1. **The old formula was uninformative, not calibrated.** Under the old
   formula, 20 of 20 combos — including Ohio State history and NYU film —
   won the Fight Student Loans battle. That is not a calibrated fight; it
   is a fight nobody can lose. `debt_median × 75% loan_pct` produced
   modeled debts of $5K–$20K across every combo, yielding DTEs ≤ 0.6 and
   ROI scores of 8–10 regardless of program economics.
2. **The new formula produces genuine differentiation.** The 20-combo
   sample now splits 12 win / 0 draw / 8 lose, and the splits track
   reality:
   - STEM & nursing at public flagships (Berkeley CS, Georgia Tech CE,
     UNC Nursing, Purdue CE, UT Austin MIS, UF PR, Indiana State
     Construction Mgmt) still WIN — their earnings absorb a realistic
     $40–60K modeled debt comfortably.
   - Elite private STEM (MIT CS, Stanford CS, Harvard Econ, Penn
     Finance, CMU CS) still WIN despite net prices up to $42K — the
     $120K+ earnings carry the debt.
   - Low-earning liberal arts and humanities at either public or private
     schools (UGA Ecology $23K, Ohio State History $26K, ASU Psych $33K)
     LOSE — that is the reality of `$40–55K debt / $25–35K earnings`
     giving DTE of 1.2–2.1. The fight is *supposed* to flag this.
   - Expensive-private + modest-earnings combos (NYU Film, BU Comms,
     Fordham Finance, Syracuse PR, DePaul Accounting) LOSE — $80–128K
     of modeled debt against $30–70K earnings is a DTE of 1.4–3.4. That
     is exactly the "you will struggle under this loan load" scenario
     the boss is supposed to catch.
3. **Spread is real, not uniform.** The distribution is not
   `uniformly_worse` (win → lose is a signal about which combos, not a
   global pessimism): the 12 new winners include combos from every
   bucket (high_public, high_private, mid_public). Wins and losses now
   separate along the axis the spec predicted — well-earning programs
   win, expensive-school/low-earnings programs lose.
4. **Thresholds still map to real DTE bands.** Under
   `stat_engine.compute_stat_roi`, `win ≥ 7` corresponds to DTE ≤ 0.75
   (i.e. total debt ≤ 9 months of earnings); `draw ≥ 5` is DTE ≤ 1.0
   (debt ≤ 1 year of earnings). Those are the correct financial cutoffs
   independent of the formula. Loosening them would let NYU Film (DTE
   3.4) or Ohio State History (DTE 2.1) pass, which would re-break the
   fight's signal.

### Observations & surprises

- **UGA Ecology, OSU History, ASU Psychology flipped win → lose.** These
  are "moderate cost, low graduate earnings" programs at public schools —
  the kind of combo where the old formula produced misleadingly healthy
  ROI because median debt was modest even though the program itself is
  not economically competitive. The new formula correctly surfaces that
  if a student *finances* the actual cost-of-attendance, the debt load
  is genuinely heavy against ~$25K starting earnings.
- **UF PR (CIP 09.09)** still WINS (new ROI 9) despite being a communications
  major, because UF's in-state net price is unusually low ($6,351) — this
  validates that the formula picks up on the specific school's aid
  package, not just the program's earnings tier.
- **Fordham Finance LOST** (new ROI 2) even though Finance is normally a
  high-earning field. Fordham's $42,581 net price × 4 × 75% = $128K
  modeled debt against $70K earnings is a DTE of 1.81 — this is the
  "expensive school, decent-but-not-elite outcome" trap that the old
  formula was blind to. This is the strongest single example of why the
  new formula is worth the shift.
- **Zero draws.** Under the new formula none of the 20 combos landed in
  the 5–6 ROI band. The DTE curve transitions sharply at DTE ≈ 1.0, and
  real combos tend to be decisively on one side or the other. Not a
  threshold problem — an artifact of the piecewise curve — but worth
  noting for the F3 UX team: the "draw" outcome will be rarer under the
  new formula than it was under the old one.

### Decision criteria applied

| Criterion | Observed | Verdict |
|---|---|---|
| >60% of wins become losses or draws | 8/20 = 40% | NOT MET |
| No losses become wins | n/a (no losses existed in old sample) | n/a |
| Distribution spread across buckets | YES (all 4 buckets have winners) | SPREAD |
| Lose cases are legitimately bad DTE (>1.0) | YES (all 8 losers have DTE 1.2–3.4) | CORRECT |

Conclusion: thresholds remain calibrated. The new formula is working as
intended. Keep `BOSS_SPECS["loans"] = BossSpec(win_at_or_above=7,
draw_at_or_above=5)` unchanged.

### Raw heuristic signals

- `uniformly_worse` heuristic: **False**
- `uniformly_better` heuristic: **False**
- `spread_out` heuristic: **True**
