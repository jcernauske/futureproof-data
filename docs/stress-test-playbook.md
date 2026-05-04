# FutureProof Stress Test Playbook

> **For:** Claude Cowork (Claude Desktop / Claude Work)
> **Goal:** Simulate 50 students, 4 builds each (200 builds total), catching data inconsistencies, broken paths, and edge cases.

---

## Setup

You are testing a local dev build of the FutureProof web app. **Open your browser and go to:**

**http://localhost:5173**

This is the frontend. The backend API runs at `http://localhost:8000` — you don't need to open it directly, the frontend talks to it automatically. Both servers must already be running before you start.

Every interaction in this playbook happens in the browser at that URL. Navigate, click, type, scroll — use the app exactly like a student sitting at a laptop would.

---

## Your Role

You are a **16-year-old high school junior** using this app for real. You don't know what CIP codes are. You don't know what SOC codes are. You've never heard of the Bureau of Labor Statistics. You're trying to figure out what to do with your life and someone showed you this app.

Act like a real teenager would:
- You type fast and sloppy. You don't proofread your major before hitting enter.
- You don't read instructions carefully. You click things that look interesting.
- You don't know the "correct" name for your major. You type what you'd say to a friend: "business stuff", "something with computers", "idk maybe teaching?"
- If something confuses you, note it. If a number seems weird ("wait, $180k for 4 years of community college?"), note it.
- If something feels wrong even if you can't articulate why, note it. Gut reactions matter.
- You don't care about statistical rigor. You care about whether the app makes sense to *you*.

**But underneath the persona, you are a meticulous observer.** Record everything you see. Your job is to be the student's eyes while keeping the tester's notebook.

## Your ONLY Job: Observe and Record

**DO NOT fix, diagnose, or suggest fixes for anything.** You are not an engineer. You are a student writing down what you see.

- See a bug? Write it down.
- See a weird number? Write it down.
- See a crash? Write it down.
- See something confusing? Write it down.
- Think you know why something broke? **Don't care. Just write down what you saw.**

Your output is a log file. That's it.

## The Log File

**Write all findings to: `reports/stress-test-findings.md`**

Append to this file as you go. Do not wait until the end to write it. After each student's 4 builds are complete, write that student's section immediately. If the app crashes mid-student, write what you have so far.

The file should grow throughout the session. If you are interrupted or the session ends, whatever is in the file is the deliverable.

### Log Format

Start the file with a header and timestamp, then append each student:

```markdown
# FutureProof Stress Test Log
- **Started:** {timestamp}
- **Tester:** Claude Cowork (simulating 16-year-old students)
- **App:** http://localhost:5173

---

## Student #1: {Persona Name}
- **Profile:** {generated character name} / {animal} / Home: {state}
- **Vibe:** {one sentence — how did this feel as a 16-year-old? Confusing? Cool? Boring?}

### Build 1: {school} + "{major typed}" -> {career picked}
- Effort: {level} | Loans: {pct}
- Pentagon: ERN={x} ROI={x} RES={x} GRW={x} AURA={x or "---"}
- Bosses: AI={W/L/D} Loans={W/L/D} Market={W/L/D} Burnout={W/L/D} Ceiling={W/L/D}
- Cost 4yr: ${x} | Starting salary: ${x}
- Weirdness: {anything that seemed off, confusing, or broken. "None" if clean.}

### Build 2: ...
### Build 3: ...
### Build 4: ...

### After All 4 Builds
- **Builds Menu check:** Do the character cards show the right stats? {yes/no + details}
- **Compare check:** Compared builds {X} vs {Y}. Numbers match? {yes/no + details}
- **Receipt spot-check:** Tapped "Explain" on {stat}. Made sense? {yes/no}
- **Branch tree spot-check:** Tree loaded for build {X}? Root node correct? {yes/no}
- **Teenager confusion moments:** {anything that would make a 16-year-old go "huh?"}
```

### Weirdness Categories

When logging weirdness, tag it:

| Tag | What it means |
|-----|--------------|
| `[CRASH]` | App died, white screen, error boundary, infinite spinner |
| `[WRONG NUMBER]` | A number changed between screens or doesn't make sense |
| `[MISSING]` | Expected data not shown (blank where there should be a number) |
| `[CONFUSING]` | A 16-year-old wouldn't understand what they're looking at |
| `[STALE]` | Data from a previous build showing up where it shouldn't |
| `[SLOW]` | Something took noticeably long (more than a few seconds) |
| `[UGLY]` | Visual glitch — overflow, misalignment, overlapping text |
| `[SEARCH FAIL]` | School search didn't find what was expected |
| `[NO CAREERS]` | Major produced zero career results |
| `[SUS]` | Something feels wrong but you can't pin it down |

## How the App Works

FutureProof is an RPG-style career planning tool. The user flow is:

1. **Profile** (`/profile`) — Generates a random character name + animal. Pick a home state. This is the identity for all builds in a session.
2. **Set Your Course** (`/set-your-course`) — Search for a school, type a major, pick a career from the results, adjust effort slider and loan percentage, then hit "Build My Future."
3. **Build Results** (`/my-build`) — Shows the pentagon chart (ERN, ROI, RES, GRW, AURA scores out of 10), boss fight results (AI, Loans, Market, Burnout, Ceiling), skill recommendations, and Gemma narrative.
4. **Gauntlet** (`/gauntlet`) — Five boss fights with outcomes (win/loss/draw). Can reroll up to 3 times per fight with skills.
5. **Future** (`/future`) — Branch tree showing career evolution paths from the starting occupation.
6. **Save** (`/save`) — Wrapped summary card.
7. **Builds Menu** (`/builds`) — Lists all saved builds with character cards. Compare mode overlays two builds.

## Memory Protocol — CRITICAL

After completing each build, **use your "Remember" feature** to store the following data points. You will cross-check these when the same data appears on later screens.

For each build, remember:

| Field | Where to find it |
|-------|-----------------|
| School name | Set Your Course screen, Build Results header, Builds Menu card |
| Major text | Set Your Course screen, Build Results header, Builds Menu card |
| Career title | Career card on Set Your Course, Build Results header, Builds Menu card |
| Published 4yr cost | Set Your Course (loan slider area), Compare view |
| Starting salary (1yr median earnings) | Career card, Compare view |
| ERN score | Pentagon chart, Builds Menu card, Compare view |
| ROI score | Pentagon chart, Builds Menu card, Compare view |
| RES score | Pentagon chart, Builds Menu card, Compare view |
| GRW score | Pentagon chart, Builds Menu card, Compare view |
| AURA score | Pentagon chart (may be null/dashed), Builds Menu card, Compare view |
| Boss outcomes (5 fights) | Gauntlet screen, Build Results boss bands, Builds Menu W/L/D |
| Effort level | Set Your Course slider |
| Loan percentage | Set Your Course slider |
| Home state | Profile screen (persists across builds) |

**After every build, cross-check these numbers against prior screens.** If a number changed between screens, log it as `[WRONG NUMBER]`.

---

## The 50 Student Personas

Each persona specifies a home state, the 4 schools to search, the major to type, and the career selection strategy. Personas are designed to stress different dimensions: school types, data coverage, geographic diversity, edge-case majors, and out-of-state tuition calculations.

---

### Tier 1: Data-Rich Baselines (Students 1-5)

These use well-known schools and common majors. If these break, something is fundamentally wrong.

**Student 1 — The Indiana Kid**
- Home: IN
- Schools: Indiana University Bloomington, Purdue University, Ball State University, Indiana State University
- Major: "business"
- Career strategy: Pick the highest-salary career each time
- Effort: balanced | Loans: 50%

**Student 2 — California Dreamer**
- Home: CA
- Schools: UCLA, Stanford University, San Diego State University, Cal Poly San Luis Obispo
- Major: "computer science"
- Career strategy: Pick a different career each time (software engineer, data scientist, IT manager, systems analyst)
- Effort: all_in | Loans: 100%

**Student 3 — Texas Two-Step**
- Home: TX
- Schools: University of Texas at Austin, Texas A&M University, Rice University, University of Houston
- Major: "nursing"
- Career strategy: Pick whatever appears first each time
- Effort: working | Loans: 75%

**Student 4 — East Coast Elite**
- Home: NY
- Schools: Columbia University, NYU, Cornell University, SUNY Binghamton
- Major: "economics"
- Career strategy: Pick the career with the lowest salary (stress-test low-earning paths)
- Effort: focused | Loans: 25%

**Student 5 — Midwest Practical**
- Home: OH
- Schools: Ohio State University, University of Cincinnati, Case Western Reserve, Ohio University
- Major: "engineering"
- Career strategy: Pick mechanical, electrical, civil, and chemical engineering careers
- Effort: balanced | Loans: 50%

---

### Tier 2: Out-of-State Tuition Stress (Students 6-10)

Home state deliberately mismatches school state to stress OOS tuition calculations.

**Student 6 — New Yorker Goes South**
- Home: NY
- Schools: University of Alabama, University of Georgia, University of Florida, Clemson University
- Major: "psychology"
- Career strategy: Vary each build
- Effort: working_hard | Loans: 0%
- **Verify:** OOS tuition gap appears. Published 4yr cost should reflect out-of-state rates for public schools.

**Student 7 — Californian Heads East**
- Home: CA
- Schools: University of Michigan, Penn State University, University of Virginia, Boston University
- Major: "biology"
- Career strategy: Vary each build
- Effort: all_in | Loans: 100%

**Student 8 — Floridian Goes Private**
- Home: FL
- Schools: Vanderbilt University, Emory University, Tulane University, Duke University
- Major: "political science"
- Career strategy: Pick any career related to law or government
- Effort: focused | Loans: 75%
- **Verify:** Private schools should NOT show OOS tuition gap.

**Student 9 — Hawaii to Mainland**
- Home: HI
- Schools: University of Oregon, University of Washington, Arizona State University, University of Nevada Las Vegas
- Major: "education"
- Career strategy: Pick teaching-related careers each time
- Effort: balanced | Loans: 50%

**Student 10 — DC Resident**
- Home: DC
- Schools: George Washington University, Georgetown University, Howard University, American University
- Major: "communications"
- Career strategy: Vary each build
- Effort: working | Loans: 25%

---

### Tier 3: Edge-Case Majors (Students 11-20)

These majors are chosen to stress CIP code resolution. Some are niche, some are ambiguous, some are misspelled on purpose.

**Student 11 — Deaf Education Specialist**
- Home: IN
- Schools: Indiana University Bloomington, Gallaudet University, University of Northern Colorado, Rochester Institute of Technology
- Major: "deaf education"
- Career strategy: Pick whatever appears
- Effort: balanced | Loans: 50%
- **Why this matters:** Real user (Jeff's wife teaches deaf ed). Tests narrow CIP resolution.

**Student 12 — The Pre-Law Student**
- Home: MA
- Schools: Harvard University, Boston College, Northeastern University, University of Massachusetts Amherst
- Major: "pre-law"
- Career strategy: Pick lawyer-adjacent careers
- Effort: all_in | Loans: 100%
- **Why this matters:** "Pre-law" is not a CIP code. Tests how the system resolves ambiguous intent.

**Student 13 — Marine Biologist**
- Home: FL
- Schools: University of Miami, Florida State University, University of South Florida, Nova Southeastern University
- Major: "marine biology"
- Career strategy: Pick whatever appears
- Effort: focused | Loans: 50%

**Student 14 — Music Therapy**
- Home: PA
- Schools: Temple University, Drexel University, Slippery Rock University, Duquesne University
- Major: "music therapy"
- Career strategy: Vary each build
- Effort: balanced | Loans: 75%

**Student 15 — Misspelled Major**
- Home: IL
- Schools: University of Illinois Urbana-Champaign, Northwestern University, DePaul University, Illinois State University
- Major: "buisness adminstration" (intentional misspelling)
- Career strategy: Pick whatever appears
- Effort: working | Loans: 50%
- **Why this matters:** Tests fuzzy matching / Gemma's ability to handle typos.

**Student 16 — Super Niche STEM**
- Home: CO
- Schools: Colorado School of Mines, Colorado State University, University of Colorado Boulder, University of Denver
- Major: "petroleum engineering"
- Career strategy: Pick whatever appears
- Effort: all_in | Loans: 100%

**Student 17 — Fine Arts**
- Home: NY
- Schools: Pratt Institute, Parsons School of Design, Rhode Island School of Design, School of Visual Arts
- Major: "fine arts"
- Career strategy: Pick whatever appears
- Effort: working_hard | Loans: 0%
- **Why this matters:** Art school economics are unusual. Tests low-ROI paths.

**Student 18 — Agricultural Science**
- Home: IA
- Schools: Iowa State University, University of Iowa, Grinnell College, Drake University
- Major: "agriculture"
- Career strategy: Vary each build
- Effort: balanced | Loans: 50%

**Student 19 — Criminal Justice**
- Home: NJ
- Schools: Rutgers University, Seton Hall University, Montclair State University, Stockton University
- Major: "criminal justice"
- Career strategy: Pick law enforcement and corrections careers
- Effort: working | Loans: 75%

**Student 20 — Philosophy**
- Home: WA
- Schools: University of Washington, Seattle University, Whitman College, Gonzaga University
- Major: "philosophy"
- Career strategy: Pick whatever appears (test what careers map to philosophy)
- Effort: focused | Loans: 25%

---

### Tier 4: Tiny and Unusual Schools (Students 21-30)

These schools may have sparse data in College Scorecard. Tests graceful handling of missing data.

**Student 21 — Community College Start**
- Home: CA
- Schools: Santa Monica College, Pasadena City College, De Anza College, El Camino College
- Major: "general studies"
- Career strategy: Pick whatever appears
- Effort: balanced | Loans: 0%
- **Why this matters:** Community colleges often have limited Scorecard data.

**Student 22 — Tiny Liberal Arts**
- Home: VT
- Schools: Middlebury College, Bennington College, Sterling College, Green Mountain College
- Major: "environmental science"
- Career strategy: Vary each build
- Effort: focused | Loans: 50%
- **Watch for:** Some of these schools may not be in the database. Green Mountain College closed in 2019.

**Student 23 — HBCU Tour**
- Home: GA
- Schools: Morehouse College, Spelman College, Clark Atlanta University, Savannah State University
- Major: "sociology"
- Career strategy: Vary each build
- Effort: balanced | Loans: 75%

**Student 24 — Trade-Adjacent**
- Home: MI
- Schools: Ferris State University, Lawrence Technological University, Kettering University, Lake Superior State University
- Major: "construction management"
- Career strategy: Pick whatever appears
- Effort: all_in | Loans: 50%

**Student 25 — Tribal College**
- Home: MT
- Schools: Salish Kootenai College, University of Montana, Montana State University, Chief Dull Knife College
- Major: "social work"
- Career strategy: Pick whatever appears
- Effort: working | Loans: 100%
- **Why this matters:** Tribal colleges are small, may have sparse data.

**Student 26 — Online University**
- Home: AZ
- Schools: Arizona State University Online, University of Phoenix, Grand Canyon University, Western Governors University
- Major: "information technology"
- Career strategy: Vary each build
- Effort: balanced | Loans: 75%
- **Watch for:** Online-only institutions may have different data profiles.

**Student 27 — Religious Institution**
- Home: UT
- Schools: Brigham Young University, Westminster College, Utah Valley University, Southern Utah University
- Major: "accounting"
- Career strategy: Pick accounting and finance careers
- Effort: focused | Loans: 25%
- **Why this matters:** BYU has unusually low tuition. Tests cost reasonableness.

**Student 28 — Conservatory**
- Home: OH
- Schools: Oberlin Conservatory, Cleveland Institute of Music, Cincinnati Conservatory of Music, Baldwin Wallace University
- Major: "music performance"
- Career strategy: Pick whatever appears
- Effort: working_hard | Loans: 0%

**Student 29 — Military Academy**
- Home: VA
- Schools: Virginia Military Institute, The Citadel, Virginia Tech, James Madison University
- Major: "history"
- Career strategy: Vary each build
- Effort: all_in | Loans: 0%

**Student 30 — For-Profit Scrutiny**
- Home: FL
- Schools: Full Sail University, Keiser University, DeVry University, Art Institutes of Fort Lauderdale
- Major: "game design"
- Career strategy: Pick whatever appears
- Effort: balanced | Loans: 100%
- **Why this matters:** For-profit schools often have poor outcomes. Tests that the data honestly reflects this.

---

### Tier 5: Geographic Edge Cases (Students 31-35)

**Student 31 — Alaska Isolation**
- Home: AK
- Schools: University of Alaska Fairbanks, University of Alaska Anchorage, Alaska Pacific University, University of Montana
- Major: "natural resources"
- Career strategy: Pick whatever appears
- Effort: balanced | Loans: 50%
- **Watch for:** Regional price parity for AK is unusual.

**Student 32 — Puerto Rico (if supported)**
- Home: FL (closest mainland)
- Schools: University of Puerto Rico, Inter American University, Ana G. Mendez University, Florida International University
- Major: "biology"
- Career strategy: Pick whatever appears
- Effort: working | Loans: 75%
- **Watch for:** PR institutions may or may not be in the database.

**Student 33 — Rural Appalachia**
- Home: WV
- Schools: West Virginia University, Marshall University, Shepherd University, Fairmont State University
- Major: "education"
- Career strategy: Pick teaching careers
- Effort: balanced | Loans: 100%

**Student 34 — Mississippi Delta**
- Home: MS
- Schools: University of Mississippi, Mississippi State University, Jackson State University, Delta State University
- Major: "public health"
- Career strategy: Pick whatever appears
- Effort: focused | Loans: 50%

**Student 35 — New England Premium**
- Home: CT
- Schools: Yale University, University of Connecticut, Trinity College, Wesleyan University
- Major: "english"
- Career strategy: Pick whatever appears (test what maps to English majors)
- Effort: working_hard | Loans: 25%

---

### Tier 6: Career Diversity Stress (Students 36-45)

Same school, different majors — tests that the same institution produces different stat profiles per program.

**Student 36 — Penn State Multidisciplinary**
- Home: PA
- Schools: Penn State University (all 4 builds)
- Majors: "nursing", "computer science", "art history", "mechanical engineering"
- Career strategy: Pick the top career for each major
- Effort: balanced | Loans: 50%
- **Verify:** Same school, different majors should produce noticeably different pentagon shapes and boss outcomes.

**Student 37 — Georgia Tech Focus**
- Home: GA
- Schools: Georgia Institute of Technology (all 4 builds)
- Majors: "computer science", "industrial engineering", "architecture", "biology"
- Career strategy: Pick the top career for each
- Effort: all_in | Loans: 75%

**Student 38 — Michigan Sweep**
- Home: MI
- Schools: University of Michigan (all 4 builds)
- Majors: "business", "social work", "aerospace engineering", "philosophy"
- Career strategy: Pick whatever appears first
- Effort: focused | Loans: 50%

**Student 39 — Community College vs Ivy**
- Home: NY
- Schools: Borough of Manhattan Community College, Columbia University, SUNY Buffalo, Cornell University
- Major: "psychology" (same major, all 4)
- Career strategy: Pick the same career type each time if possible
- Effort: balanced | Loans: 50%
- **Verify:** Same major + career across wildly different schools should show big differences in cost, ROI, and AURA.

**Student 40 — Effort Slider Sweep**
- Home: TX
- Schools: University of Texas at Austin (all 4 builds)
- Major: "business" (same each time)
- Career strategy: Pick the same career each time
- Effort: **working_hard, working, balanced, all_in** (one per build)
- Loans: 50% (constant)
- **Verify:** Effort level changes the pentagon stats. ERN should differ between working_hard and all_in.

**Student 41 — Loan Slider Sweep**
- Home: CA
- Schools: UCLA (all 4 builds)
- Major: "economics" (same each time)
- Career strategy: Pick the same career each time
- Effort: balanced (constant)
- Loans: **0%, 25%, 75%, 100%** (one per build)
- **Verify:** Loan percentage should change the Loans boss outcome and modeled debt, but NOT ERN, GRW, or RES.

**Student 42 — Same Career, Different Schools**
- Home: IL
- Schools: University of Chicago, Illinois State University, Southern Illinois University, Loyola University Chicago
- Major: "psychology"
- Career strategy: Pick "Psychologist" or closest equivalent every time
- Effort: balanced | Loans: 50%
- **Verify:** Same career from different schools should show different ERN/ROI/cost profiles.

**Student 43 — Health Sciences Variety**
- Home: MN
- Schools: University of Minnesota, Mayo Clinic School, St. Catherine University, Augsburg University
- Majors: "nursing", "public health", "biology", "health administration"
- Career strategy: Pick health-related careers
- Effort: working | Loans: 75%

**Student 44 — Engineering Showdown**
- Home: MA
- Schools: MIT, Worcester Polytechnic Institute, University of Massachusetts Amherst, Tufts University
- Major: "electrical engineering"
- Career strategy: Pick the top career each time
- Effort: all_in | Loans: 50%

**Student 45 — Education Across States**
- Home: OR
- Schools: University of Oregon, Portland State University, Oregon State University, Lewis & Clark College
- Major: "elementary education"
- Career strategy: Pick teaching careers
- Effort: balanced | Loans: 50%

---

### Tier 7: Chaos and Adversarial (Students 46-50)

Intentionally adversarial inputs to find crashes and bad UX.

**Student 46 — The Typo Monster**
- Home: TX
- Schools: Search "Univrsity of Texss", "standford", "Haravrd", "MIT" (test fuzzy search)
- Major: "compter sceince"
- Career strategy: Pick whatever appears
- Effort: balanced | Loans: 50%
- **Why this matters:** Real students can't spell.

**Student 47 — The Emoji Student**
- Home: CA
- Schools: UCLA, UC Berkeley, UC Davis, UC Santa Cruz
- Major: Try typing just "science" — a very broad term
- Career strategy: Pick the most unexpected career that appears
- Effort: working_hard | Loans: 0%
- **Why this matters:** Ambiguous one-word majors test Gemma's CIP resolution.

**Student 48 — Rapid-Fire Builds**
- Home: NY
- Schools: NYU (all 4, but start building before previous build finishes loading)
- Major: "finance"
- Career strategy: Don't wait for one build to complete — start the next immediately
- Effort: balanced | Loans: 50%
- **Why this matters:** Race conditions in the build pipeline.

**Student 49 — The Back-Button Warrior**
- Home: FL
- Schools: University of Florida, FSU, UCF, USF
- Major: "marketing"
- Career strategy: Pick a career, start building, hit back button mid-build, try again
- Effort: balanced | Loans: 50%
- **Why this matters:** Navigation interrupts during async build/SSE streaming.

**Student 50 — The Comparison Fiend**
- Home: OH
- Schools: Ohio State University, University of Cincinnati, Xavier University, Miami University
- Major: "finance" for first 2, "nursing" for last 2
- Career strategy: Vary each build
- Effort: balanced | Loans: 50%
- **After all 4 builds:** Open the Builds Menu. Compare every possible pair (1v2, 1v3, 1v4, 2v3, 2v4, 3v4). For each comparison, verify:
  - Pentagon overlay aligns with individual build stats
  - Cost, salary, and debt numbers match the original builds
  - Boss outcomes match
  - No data from one build bleeds into the other's column

---

## After-Build Checks (Run After Each Student's 4 Builds)

These checks happen after you finish all 4 builds for a student. Log results in the student's section of the report.

### 1. Cross-Screen Data Match
Go to `/builds`. For each build's character card, compare against what you remembered:
- School name matches what was entered
- Major text matches what was typed
- Career title matches what was selected
- W/L/D record matches what happened in the gauntlet
- Pentagon stats (ERN, ROI, RES, GRW, AURA) match the build results screen
- **If anything doesn't match, log it as `[WRONG NUMBER]` or `[STALE]`**

### 2. Compare Mode Consistency
Select any two builds and open Compare. Check:
- Each column's stats match their respective build results
- Cost data matches (published 4yr cost, net price, tuition)
- Earnings data matches
- Boss outcomes match
- **If anything doesn't match, log it. If you're confused by the layout, log that too as `[CONFUSING]`**

### 3. Stat Receipt Spot-Check
For at least one build per student, tap the "Explain this to me" button on 2 different stats (e.g., ERN and ROI):
- Does the receipt open?
- Do the numbers in the receipt match the pentagon score?
- Does it make sense to a 16-year-old?

### 4. Branch Tree Spot-Check
For at least one build per student, navigate to `/future`:
- Does the tree load?
- Is the root node the career you selected?
- Do the branches look like real jobs?

---

## End-of-Session Summary

After all 50 students (or as many as you complete), append a summary to `reports/stress-test-findings.md`:

```markdown
---

# Summary

- **Builds completed:** X/200
- **Builds that crashed or errored:** X
- **Schools not found in search:** {list}
- **Majors that produced no careers:** {list}

## All Weirdness by Tag
### [CRASH]
- {list every crash with student # and build #}

### [WRONG NUMBER]
- {list every data inconsistency}

### [MISSING]
- ...

### [CONFUSING]
- {these are gold — a 16-year-old's confusion is a UX bug}

### [STALE]
### [SLOW]
### [UGLY]
### [SEARCH FAIL]
### [NO CAREERS]
### [SUS]

## Teenager Highlight Reel
{Top 5 moments where the 16-year-old persona was most confused, surprised, or delighted. Direct quotes from the persona's perspective.}
```
