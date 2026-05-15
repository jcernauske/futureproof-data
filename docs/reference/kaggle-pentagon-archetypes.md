# Kaggle Writeup — Nine Pentagon Archetypes

The Kaggle writeup includes a 3×3 screenshot of aliased pentagons chosen to
teach nine different lessons in three seconds. Real schools and majors are
queried from the gold zone so the shapes are honest data, not synthesized.
**Schools are aliased on-screen** to avoid singling any institution out in the
writeup, but the underlying rows are recorded here so the screenshot is
reproducible and auditable.

## Data source

All numbers come from a single SQL pass over the gold zone, joining the program
view to the institution view:

```sql
SELECT p.institution_name, p.program_name, p.occupation_title,
       p.stat_ern, p.stat_roi, p.stat_res, p.stat_grw,
       a.aura_score,
       p.earnings_1yr_median, p.net_price_annual, p.debt_median,
       p.unitid, p.cipcode, p.soc_code
FROM consumable.program_career_paths p
JOIN consumable.institution_aura  a USING (unitid);
```

Stats are 0–10 integers. AURA is the institution-level brand-gravity score from
`consumable.institution_aura.aura_score` (IPEDS finance + EADA athletics
inputs). The probe script that produced these picks lives at
`scripts/_archetype_probe.py`.

Snapshot taken: 2026-05-13.

## The Nine

Pentagon order on every row: **ERN, ROI, RES, GRW, AURA** (0–10).

| # | Alias | School | Program | Career (SOC) | ERN | ROI | RES | GRW | AURA | 1-yr earn | Net price/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **In-State Flagship** | University of Florida | Computer Engineering (CIP 14.0901) | Computer hardware engineers (17-2061) | 10 | 10 | 7 | 7 | 7 | $76,743 | $6,351 |
| 2 | **All Sizzle, No Steak** | University of Southern California | Visual and Performing Arts, General (CIP 50.0101) | Fine artists, including painters (27-1013) | 3 | 1 | 7 | 4 | 9 | $18,394 | $31,927 |
| 3 | **Good Work If You Can Get It** | University of Washington–Seattle | Allied Health Diagnostic, Intervention, and Treatment Professions (CIP 51.09) | Nuclear technicians (19-4051) | 10 | 10 | 7 | 3 | 8 | $121,083 | $13,485 |
| 4 | **Beware the AI Buzzsaw** | Stanford University | Computer Science (CIP 11.07) | Computer programmers (15-1251) | 9 | 7 | 3 | 3 | 10 | $136,126 | $12,136 |
| 5 | **The Hidden Gem** | Weber State University | Building/Construction Finishing, Management, and Inspection (CIP 46.04) | Solar photovoltaic installers (47-2231) | 8 | 10 | 9 | 10 | 3 | $75,531 | $10,722 |
| 6 | **The Prestige Tax** | Dartmouth College | Fine and Studio Arts (CIP 50.07) | Jewelers and precious stone and metal workers (51-9071) | 7 | 2 | 8 | 3 | 10 | $35,235 | $28,619 |
| 7 | **The Calling** | Northern Michigan University | Mental and Social Health Services and Allied Professions (CIP 51.15) | Psychiatric technicians (29-2053) | 2 | 5 | 9 | 9 | 5 | $27,374 | n/a |
| 8 | **The Wage Trap** | New Jersey Institute of Technology | Business Administration, Management and Operations (CIP 52.02) | Business operations specialists, all other (13-1199) | 5 | 5 | 5 | 6 | 6 | $37,273 | $16,496 |
| 9 | **The Trades** | Farmingdale State College | Industrial Production Technologies/Technicians (CIP 15.06) | Welders, cutters, solderers, and brazers (51-4121) | 5 | 10 | 9 | 5 | 1 | $60,210 | $9,173 |

## Why each row was picked

1. **In-State Flagship** — UF CompEng is the textbook flagship/STEM pairing: low
   in-state net price drives ROI to ceiling, strong earnings, moderate-high
   AURA. The "well-rounded baseline" all other pentagons get judged against.
2. **All Sizzle, No Steak** — USC Fine Arts → Fine artists. AURA peg, ERN/ROI
   floor. The "brand was not a paycheck" story.
3. **Good Work If You Can Get It** — UW Nuclear Technicians earns $121K but
   GRW is 3 (BLS projects flat-to-declining demand). High pay, contracting
   field.
4. **Beware the AI Buzzsaw** — Stanford CS → "Computer programmers" specifically
   (BLS treats this as distinct from "software developers" and projects
   double-digit declines; Karpathy/Anthropic exposure scores also crash RES to
   3). The "even Stanford CS has axes to grind" lesson.
5. **The Hidden Gem** — Weber State + Solar PV installers. Low AURA, but every
   other axis crushes: $75K starting, near-zero AI exposure, BLS projects 22%
   growth (one of the fastest in the country). The unsexy winner.
6. **The Prestige Tax** — Dartmouth + Fine Studio Arts → Jeweler. AURA pegged,
   ROI in the basement, GRW collapses. Ivy sweatshirt, $35K starting.
7. **The Calling** — Psychiatric technician via a regional state school. RES
   and GRW push outward, ERN/ROI/AURA all small. The "society needs the work,
   society won't pay for it" pentagon.
8. **The Wage Trap** — Mid-tier business admin at a non-prestige school. Every
   axis sits at 5–6 — the literal middle of the pentagon. The "fine, fine,
   fine" outcome that nobody sells, nobody warns against, and most students
   land in.
9. **The Trades** — Welding program at a regional state college. ROI and RES
   pegged, ERN/GRW middling, AURA at the floor. Distinct from Hidden Gem
   because the GRW axis is more modest — trades aren't booming, they're
   stable. The "AI can't weld" pentagon.

## Reproducing the screenshot

```bash
uv run python3 scripts/_archetype_probe.py   # archetypes 1–6
uv run python3 scripts/_archetype_probe3.py  # archetypes 8 (Wage Trap) and 9 (Trades)
uv run python3 scripts/_archetype_probe3b.py # archetype 7 (Calling)
```

The probe scripts list 25–30 candidates per archetype; the final pick from each
list is the row in the table above. Any future schema change to
`program_career_paths` or `institution_aura` may shift these rows — re-run the
probes before re-shooting the screenshot and refresh this doc.

To capture the screenshot itself:

```bash
# dev server must be running on localhost:5173
uv run --with playwright python3 scripts/_archetype_screenshot.py
# writes docs/kaggle/assets/archetypes-pentagons.png
```

## On naming schools in the writeup

The Kaggle writeup itself uses only the **alias** column. The schools and
careers are recorded here for auditability without giving any one institution a
public callout in a competition submission.
