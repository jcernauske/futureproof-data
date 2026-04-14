# FutureProof — Hackathon PRD v8

*What Ships May 18, 2026*

**Hackathon:** Gemma 4 Good (Kaggle / Google DeepMind)
**Deadline:** May 18, 2026 (11:59 PM UTC)
**Scope:** This document defines what gets built. Supersedes PRD v7 and the hackathon PRD.
**Companion doc:** `futureproof-spike-vs-prd-analysis.md` — explains every divergence from v7 and why.

-----

## What Ships

A web application where a student gets an auto-generated profile name, picks a school, types what they want to study, sees Gemma map that to a real program, chooses from tiered career paths, sees five data-backed stats with a first-time tutorial explaining each one, fights boss battles representing real career threats with an interactive reroll mechanic that teaches them what to do about their weaknesses, explores branching career paths computed dynamically from O*NET data, gets a concrete post-gauntlet action checklist, and shares a Spotify Wrapped-style story sequence to Instagram. Multiple builds can be saved, compared via a risk-focused tradeoff screen, and explored further through freeform chat with Gemma.

**Core loop:** Landing → Profile Name → School + Major (Gemma intent) → Effort + Loans → Career Pick (tiered) → Reveal (tutorial + stats) → Gauntlet (with rerolls) → Next Steps → Branch Tree → Save + Share (Wrapped) → Menu (compare / explore / chat / new build).

-----

## Submission Deliverables

| Deliverable | Spec | Owner |
|---|---|---|
| **Live Demo** | Publicly accessible URL, no login required | Jeff |
| **Video** | 3 min max, YouTube. Story, not product demo. | Jeff |
| **Kaggle Writeup** | 1,500 words max. Architecture, Gemma 4 usage, challenges. | Jeff |
| **GitHub Repo** | Public, well-documented, reproducible. Includes Ollama setup instructions. | Jeff |
| **Media Gallery** | Cover image, screenshots, architecture diagrams. | Jeff |

-----

## Hackathon Tracks

| Track | Prize | What We Show |
|---|---|---|
| **Main Track** | Up to $50K | Full product: Build → Fight → Reroll → Branch → Compare → Share |
| **Future of Education** | $10K | Equity narrative: every student gets the same AI-aware career guidance |
| **Ollama** | $10K | Same app running locally via Ollama. Demonstrated in video + reproducible from repo. |
| **Unsloth** (optional) | $10K | Fine-tuned CareerGemma model. Only if Bogdan joins. |

**Prize ceiling:** $70K solo / $80K with Bogdan.

-----

## Scope Boundary

### Ships

- **Auto-generated profile name:** Three-word whimsical name (adjective + adjective + animal emoji). Collision-checked silently. Reroll button. Lookup by name for returning users. No PII.
- **School search:** Fuzzy match against College Scorecard institutions.
- **Gemma intent resolution for majors:** Free-text input → Gemma maps to CIP code → presents match with career previews → student confirms. Audit pass catches adversarial/joke inputs. Clarification round if needed. Confirmed mappings cached.
- **Effort slider:** Working / Balanced / All-in. Maps to 25th/50th/75th percentile. Adjusts ERN only.
- **Loan percentage slider:** 0% / 25% / 50% / 75% / 100%. Scales debt-to-earnings before ROI and Fight Student Loans derivation. Independent from effort.
- **Five-stat pentagon:** ERN, ROI, RES, GRW, HMN — all computed from public data. Pentagon radar chart visualization.
- **Stat explainer tutorial:** First build only. Guided walkthrough overlay highlighting each stat with plain-English explanation. Persistent "?" tooltips on subsequent builds.
- **Gemma-powered career tiering:** Career outcomes grouped into Common / Less Common / Stretch tiers. Student picks which career to build around.
- **Gemma's Take:** 4-6 sentence coaching narrative. Leads the reveal — student reads the narrative first, then sees stats as proof.
- **Boss gauntlet (5 + Final Boss):** Fight AI, Fight Student Loans, Fight the Market, Fight Burnout, Fight the Ceiling. Fight the Future (composite). Emoji-based visuals.
- **Boss fight reroll mechanic:** On loss/draw, Gemma generates 3-5 skills with machine-readable stat deltas. Student equips skills, fight rescores live. Skills are build-wide. Pool exhaustion triggers structural loss messaging.
- **Next Steps checklist:** Post-gauntlet Gemma call. Drops RPG metaphor entirely. Concrete, data-grounded action items referencing the student's specific school/major/career.
- **Dynamic branch tree:** Career tree computed from O*NET pathway data at query time. Up to 3 levels deep. Each node carries absolute stats and boss fight results.
- **Graceful fallback:** Careers with no O*NET pathway data show full Stage 2 (stats, boss fights, skill recs) with a "branches coming soon" indicator.
- **Receipts (data provenance):** Every determination gets a collapsible receipt showing raw inputs, thresholds, and sources. Tappable "?" icons in frontend.
- **Save/load builds:** Multiple builds per profile. Labeled by profile name.
- **Spotify Wrapped share experience:** Multi-frame story sequence optimized for Instagram Stories (1080×1920). Profile name + emoji → stats → boss scorecard → comparative insights → risk highlight. Server-side rendered (Puppeteer).
- **Risk comparison screen:** Tradeoff-focused comparison of 2-3 builds. Surfaces which risks each build wins/loses, not just raw stat numbers. "Build A survives AI but gets crushed by loans. Build B is the opposite."
- **Ask Gemma:** Freeform chat panel with full build context loaded. Multi-turn conversation history.
- **Skill recommendations:** Gemma-generated post-build recommendations showing which skills boost which stats.
- **Personalized loading:** "Specing dancing happy bear 🐻..." — uses the student's profile name during computation.
- **Mobile-responsive web:** Students will access on phones. Web-first but must work on mobile viewports.
- **Ollama local deployment:** Same codebase, config switch for inference backend. Video shows split-screen cloud vs. local.

### Ships If Time Permits

- **Historical parallels on boss losses:** Slot accommodated in boss fight narrative prompt. Curated data added only if time remains after core frontend.
- **Counselor/parent report:** Backend working (`report_gen.py`). "Download report" button added if time remains after Wrapped experience ships.

### Does Not Ship

- Native mobile app (iOS/Android)
- User accounts or authentication (profile name is the identity layer)
- Character creation (animal picker, accessories, color) — replaced by profile names
- Midjourney art (deeply deprioritized — emoji-only for hackathon)
- Pre-computed Stage 3 branching (dynamic computation proved sufficient)
- Interactive craftable skill nodes (reroll mechanic is better)
- "What if" scenario comparisons (compare + new build covers this)
- Financial aid overlay on ROI
- Full school coverage (4,000+ institutions)
- Animated share card (TikTok/Reels variant)
- Parent/counselor separate view
- B2B features, subscriptions, payments
- Notable Alumni Enrichment — agentic search pipeline prefetching alumni data for suppressed school+major combos. Pipeline enrichment, not frontend.
- Course Catalog Crawler — Brightsmith ingestor crawling school websites for minors, certificates, electives, clubs. Powers "How do I fix this?" on risk assessments. Big scope.
- Brightforge Lineage UI — full data lineage visualization from Brightsmith's sister project. Receipts cover the hackathon need; the visual lineage explorer is post-hackathon.
- Tier 3 Data Update — one-button update mechanism for school self-hosted deployments. Deployment infrastructure, not product. Hackathon demos Ollama; production update pipeline is post-hackathon.
- Native AI Exposure Scoring — rebuild Karpathy's scores natively with Gemma using O*NET task-level data. Bonus spec exists (`gemma-ai-exposure-rescore`). Ships only if time remains after core frontend. Strengthens the writeup but not critical path.
- Career Pathfinding skill gap analysis — detailed Gemma-computed skill/experience gaps between current position and target role using O*NET task deltas. The branch tree already shows the hops; the gap analysis is polish on top.

-----

## Profile System

Replaces the character creation system from PRD v7. Zero PII, zero friction, full identity.

### How It Works

When a student hits the CTA, the app generates a three-word name: **adjective + adjective + animal emoji**. The animal comes from the design system emoji set (🐻 🐰 🐢 🐿️ 🦊 + others). The adjective pools are warm/positive — "brave," "curious," "steady," "bold," "dancing," "bright," etc. (~50 each). Pool size: ~50 × ~50 × ~8 = 20,000 combinations.

- Student sees "You are **dancing happy bear 🐻**" with a reroll button
- On collision with an existing name, silently regenerate — never expose that another profile exists
- Name persists across builds and labels all saved data
- To return: student types their profile name (case-insensitive, fuzzy-tolerant) to retrieve saved builds
- No email, no password, no account creation

### What This Replaces

The PRD v7 character system required: animal species picker (6-8 options), accessory tray (wheelchair, hijab, pride pin, glasses, prosthetic, etc.), fur/skin color slider, 6-8 Midjourney starter renders, 8-12 Stage 2 career bear renders, ~15 accessory overlays, Stage 1 → Stage 2 evolution animation. All cut.

### What Survives

The emoji animal provides visual identity on share cards, the compare screen, and throughout the UI. "Dancing Happy Bear 🐻" on a Wrapped frame still triggers "what did you get?" The social loop works without rendered art.

### Backend

`Build` model gets `profile_name: str`. New `profile.py` service handles name generation, collision detection, and lookup.

-----

## The Five-Stat System

Five stats. All hard public data. Pentagon radar chart.

| Stat | Full Name | What It Measures | Data Source | Plain-English (shown in tutorial) |
|---|---|---|---|---|
| **ERN** | Earning Power | What you'll make | College Scorecard + BLS OOH | "Based on what graduates of this program at this school actually earn." |
| **ROI** | Return on Investment | Earnings vs. debt | College Scorecard | "Compares your expected earnings to your student debt. Your loan percentage drives this." |
| **RES** | AI Resilience | Automation exposure | Karpathy + O*NET tasks | "How exposed is this career to AI automation? Higher means the work needs humans." |
| **GRW** | Growth | Field expansion/contraction | BLS Employment Projections | "Is this field growing or shrinking? Based on 10-year job projections." |
| **HMN** | Human Edge | Human-skill dependency | O*NET task dimensions | "How much does this job depend on uniquely human skills?" |

### Stat Explainer Tutorial (First Build Only)

On the student's first build, the reveal screen shows a guided walkthrough that highlights each stat one at a time: highlight → explain → next. Plain English, no jargon, empowering tone ("here's why you should care about this number"). The walkthrough fades after all five stats are explained and the student proceeds to boss fights. Subsequent builds skip the tutorial. A persistent "?" icon on each stat provides the explanation on tap for return visits.

-----

## Effort + Loan Sliders

Two distinct inputs. Independent variables.

### Effort Slider

"How much time will you have to focus on school?"

| Level | Percentile | ERN Shift |
|---|---|---|
| Working + school — limited focus | 25th | −1 |
| Balanced — solid effort | 50th | 0 |
| All-in — maximum focus | 75th | +1 |

Adjusts ERN only. Does not affect ROI — a student working two jobs doesn't reduce tuition.

### Loan Percentage Slider

"How much of your school costs will you cover with loans?"

| Level | Loan % | Effect |
|---|---|---|
| No loans (scholarships, savings, family) | 0% | ROI maximized, Fight Student Loans advantage |
| Some loans | 25% | Moderate debt load |
| Half loans | 50% | Balanced |
| Mostly loans | 75% | Significant debt |
| All loans — full published debt load | 100% | ROI reflects worst-case DTE |

Scales debt-to-earnings ratio before ROI and Fight Student Loans derivation. A full-scholarship student at a $60K/year school sees dramatically different ROI than a fully-financed student at the same school. The spike models this correctly.

-----

## Gemma Intent Resolution

The major selection flow is Gemma-powered, not a dropdown picker.

### Flow

1. Student types free text: "pre-med", "CS", "business", "nursing"
2. Gemma matches to the correct CIP code using the school's actual program list + national crosswalk data
3. App presents the match with career previews: "Gemma thinks 'pre-med' maps to Biology (CIP 26.0101). This would show you careers like: Physicians, Surgeons, Medical Scientists..."
4. Student confirms, clarifies, or picks an alternative
5. Audit pass catches adversarial/joke inputs: "Look, this is one of the biggest financial decisions of your life. The tool works better when you give it something real."
6. Confirmed mappings cached for instant resolution on repeat queries

### Gemma Calls

Three distinct calls per resolution: intent resolution → audit → optional clarification round. This is a genuine Gemma showcase — the model doing real work, not just chat.

### CIP Substitution

When a school reports only a broad CIP code (e.g., "Business" at 52.00) but the student typed something specific (e.g., "Marketing"), the system uses the specific CIP's crosswalk SOCs for career paths while falling back to the school's broad earnings data for ERN/ROI. Validated end-to-end in the spike via YAML override table.

-----

## Career Tiering

After the stat engine returns career outcomes for a school+major, Gemma groups them into three tiers:

- **Common paths** — the 3-5 careers graduates of this school+major most frequently enter
- **Less common but realistic** — the next 5-7 plausible careers
- **Stretch paths** — remaining crosswalk matches that are possible but less typical

Gemma considers school prestige, program emphasis, regional labor market, and O*NET education requirements. Deterministic fallback if Gemma fails (all outcomes in a single "All career paths" tier). The student picks any career from any tier.

-----

## Boss Fight System

### What Ships

Five boss fights + one Final Boss. Each tests specific stats. Results are win/lose/draw with Gemma-generated narrative. Emoji-based visuals.

| Boss | Emoji | Tests | Data |
|---|---|---|---|
| Fight AI | 🤖 | RES + HMN | O*NET tasks + Karpathy |
| Fight Student Loans | 💰 | ROI + ERN | College Scorecard debt/earnings |
| Fight the Market | 📈 | GRW + ERN | BLS Employment Projections |
| Fight Burnout | 🔥 | O*NET work context | Hours, stress, schedule, time pressure |
| Fight the Ceiling | 📊 | Long-term ERN trajectory | BLS salary by experience level |
| **Fight the Future** | ⚔️ | **Composite** | **All mini boss results** |

### Reroll Mechanic

The signature interactive feature. On a loss or draw:

1. Gemma generates 3-5 skills specific to the losing boss, grounded in the student's actual career. Each skill has machine-readable stat deltas (e.g., "Data Analytics Minor: RES +2").
2. Student equips one or more skills.
3. Fight rescores live with the new stats. Outcome can flip: LOSE → DRAW, LOSE → WIN, DRAW → WIN.
4. Skills are **build-wide** — crafting RES+2 for Fight AI also helps later fights that use RES.
5. Loop continues until the result improves, the student skips, or the skill pool is exhausted.

### Structural Loss

When the skill pool is exhausted and the result still hasn't improved, the student sees:

*"Every available skill for this fight has been equipped, and the result is still a loss. That's the most important signal this tool can give you: the gap isn't a skill-tree problem. It's structural to this school + major + career combination. Worth taking seriously."*

This is the moment the student might consider a different build. It's the most honest thing the product says.

### Historical Parallels (If Time Permits)

A slot is accommodated in the boss fight narrative prompt for historical parallels (bank tellers vs. ATMs, journalists vs. internet, etc.). If Gemma naturally surfaces good parallels, they appear. Curated parallel data added only if time remains after core frontend ships.

-----

## Skill Crafting

Replaces the read-only skill tree from PRD v7. Skills are interactive, machine-readable, and build-wide.

### How Skills Work

Each `AppliedSkill` has:
- `title` — what the student sees ("Data Analytics Minor")
- `rationale` — why it helps ("Learn to direct AI analysis tools instead of competing with them")
- `targets` — which bosses this skill surfaces on during a loss screen
- `delta_*` — stat deltas (e.g., `delta_res: 2`) that clamp to [1, 10] when applied

### Generation

Primary: Gemma generates 3-5 skills per losing boss, grounded in the student's actual career. Fallback: hand-curated generic pool ensures the reroll mechanic never breaks.

### Post-Build Skill Recommendations

Separate from the reroll pool. Gemma generates a list of courses, certifications, internships, and minors that boost stats — presented as recommendations after the gauntlet. Read-only in the frontend.

-----

## Next Steps Checklist

A dedicated Gemma call after the gauntlet. Drops all RPG metaphor. Produces four sections of specific, data-grounded actions the student can take into the real world. Every item references something concrete from the student's data: their school name, major, career, stats, boss fight results, or skills crafted.

Tone: empowering, specific, actionable. Respectful of parents — not adversarial. When the data shows real weaknesses, acknowledges them honestly and pairs with mitigation.

This is the deliverable the student prints and brings to a meeting with parents or a counselor.

-----

## Branch Tree

### What Ships

Dynamic career tree computed from O*NET pathway data at query time. Up to 3 levels deep from any career. No pre-computation.

Each branch shows:
- Career progression nodes (e.g., Financial Analyst → Sr. Analyst → Quant → Portfolio Manager)
- Absolute stats at each node (GRW, HMN, RES from branch data)
- Boss fight results per branch
- Skill unlock requirements (read-only descriptions)

### Visualization

The branch tree is the signature UI element. Stage 2 career at center, branches extending outward. Tap a branch node to reveal stats and boss fight profile. On a web viewport this can spread across the full screen.

### Fallback

Careers with no O*NET pathway data get the full Stage 2 experience (stats, boss fights, skill recs, Gemma's Take, Next Steps) with a tasteful "We're mapping the career branches for [Career]. Check back soon." indicator. The product is fully useful without branches — branches are additive.

-----

## Receipts (Data Provenance)

Every determination gets inline provenance. In the frontend, these surface as tappable "?" icons that expand to show:

- **Stats receipt:** Raw data inputs, effort shift applied, loan % scaling, source datasets
- **Boss fight receipt:** Raw score, win/draw thresholds, which stats contributed
- **Reroll receipt:** Pre/post scores, skills applied, delta breakdown
- **Career tiering receipt:** Which career was picked, total outcomes available, tiering method
- **Skill recommendations receipt:** Career context, gauntlet results used as input

This supports the "Show Your Work" story and the adversarial auditor narrative in the writeup. It differentiates from every other hackathon entry: "We don't just show you data — we show you where the data came from and how we computed every number."

-----

## Spotify Wrapped Share Experience

The viral growth mechanic. Replaces the static character card from PRD v7.

### What It Is

A multi-frame story sequence optimized for Instagram Stories (1080×1920). Each frame is a self-contained visual on a dark background (#1B1D30) that tells the story of the student's build. The student taps through the sequence, screenshots individual frames, or shares the whole thing.

### Frame Sequence (Example)

1. **Identity:** "Steady Bold Turtle 🐢 just speced ISU Business"
2. **Pentagon:** Stats animating in on the radar chart
3. **Boss scorecard:** Win/lose icons for each boss, Fight the Future verdict
4. **Comparative insight:** "Your AI Resilience is higher than 62% of business paths"
5. **Risk highlight:** "Your biggest risk: Student Loans 💰"
6. **CTA:** "See where your path leads → futureproof.app"

### Social Loop

Student builds → shares Wrapped frames → caption: "I'm Steady Bold Turtle 🐢" → friend sees it → "what name did you get?" → friend opens FutureProof → repeat.

### Rendering

Server-side: Puppeteer screenshots of styled HTML templates, each populated with the build's data. Served as downloadable PNGs from the backend. Each frame is a separate template.

-----

## Risk Comparison

Replaces the simple stat-table compare screen from PRD v7. The compare experience is tradeoff-focused.

### What It Shows

When a student compares 2-3 builds, they don't see columns of numbers. They see:

- **Risk profiles:** Which bosses does each build win/lose? "Build A survives Fight AI but gets crushed by Student Loans. Build B is the opposite. Which risk are you more willing to live with?"
- **Pentagon overlays:** Stat shapes overlaid to show where builds diverge
- **Branch previews:** Which builds open which Stage 3 paths?
- **Gemma comparison summary:** Tradeoff analysis highlighting what each build optimizes for and what it sacrifices

The compare never declares a winner. Tradeoffs only. The student decides which risks they can live with.

### Backend

`builds.compare_builds()` produces the underlying data. The frontend treatment transforms it into a risk-focused experience.

-----

## Ask Gemma

Freeform chat with full build context loaded. The student taps "Ask Gemma" from the post-build menu and gets a conversation panel.

- Full build context rides in every message (career, stats, gauntlet, branches, skills)
- Multi-turn conversation history maintained
- Student can ask anything: "What internships should I look for?" "Is this career path better in California or Texas?" "What if I add a data science minor?"

This is the 10th Gemma integration surface and a strong demo moment.

-----

## Gemma Integration Surfaces (10)

Stats and boss fight scoring are deterministic (reproducible). Narratives and coaching are Gemma-generated (personalized). This split is deliberate.

| # | Surface | What Gemma Does | Fallback |
|---|---|---|---|
| 1 | Intent resolution | Maps free-text major input to CIP code | Substring match against program list |
| 2 | Intent audit | Catches adversarial/joke inputs | Accept all inputs |
| 3 | Career tiering | Groups career outcomes into Common/Less Common/Stretch | All outcomes in single flat list |
| 4 | Gemma's Take | 4-6 sentence coaching narrative | Generic "your build has N wins and M losses" |
| 5 | Boss fight narratives | 1-2 sentence explanation per fight | Deterministic reason string only |
| 6 | Reroll commentary | Commentary when a skill flip changes a fight outcome | No commentary, just the result change |
| 7 | Skill pool generation | 3-5 skills per losing boss with stat deltas | Hand-curated generic fallback pool |
| 8 | Skill recommendations | Post-build course/cert/internship recommendations | Empty recommendations |
| 9 | Next Steps checklist | Post-gauntlet action items, no RPG framing | No checklist |
| 10 | Freeform chat | Multi-turn conversation with build context | N/A (feature disabled) |

Every Gemma surface has a deterministic fallback so the app never crashes if Gemma is unavailable or returns unparseable output.

-----

## Data Pipeline

### Sources (All Public, All Through Brightsmith Gold)

| Source | Rows | What It Provides |
|---|---|---|
| **College Scorecard** | 69,947 | Salary, debt, employment by school+major. `unitid × cipcode × credlev` grain. |
| **BLS OOH** | 832 | Salary ranges, task breakdowns, occupation profiles. Keyed by SOC. |
| **O*NET** | 798 occupations, 15,944 transitions | Task data, work activities, work context, career pathways. |
| **Karpathy AI Exposure** | 389 | 0-10 AI exposure per occupation. Starting point for RES. |
| **BEA Regional Price Parities** | 51 | State-level cost-of-living adjustment. Enables "what does this salary mean where you live?" |
| **CIP-SOC Crosswalk** | ~626K paths | Bridges Scorecard programs to BLS/O*NET occupations. The hardest data problem. |

### Pipeline Architecture

Brightsmith processes each source through Bronze → Silver → Gold → MCP zones. 280+ DQ rules, 7 data contracts, chaos monkey testing.

### Gold Consumable Tables

| Table | Rows | Powers |
|---|---|---|
| `consumable.career_outcomes` | 69,947 | ERN, ROI, effort slider |
| `consumable.occupation_profiles` | 832 | ERN (BLS), Burnout, Ceiling boss data |
| `consumable.onet_work_profiles` | 798 | HMN stat, Burnout boss |
| `consumable.program_career_paths` | 626K | Career matching, full pentagon |
| `consumable.career_transitions` | 15,944 | Branch tree |
| `consumable.career_branches` | 16K | Branch stat deltas |
| `consumable.ai_exposure` | 389 | RES stat, Fight AI boss |

-----

## Technical Architecture

### Current State: Backend Is Built

The spike produced a fully functional backend at `futureproof-data/backend/`. This is not a throwaway prototype — it's the production service layer. The entire core loop runs end-to-end today via `uv run python backend/cli.py` from the project root.

**What runs right now:**
- School search → Gemma intent resolution for majors → effort + loan sliders → five-stat pentagon computation → Gemma career tiering → career pick → Gemma's Take narrative → boss gauntlet with interactive reroll → Next Steps checklist → dynamic branch tree → skill recommendations → save/load/compare builds → freeform Gemma chat → markdown report generation

**What needs to happen for frontend:**
1. Wire FastAPI routers to the existing service layer (the Pydantic models are already shaped as API contracts)
2. Add `profile.py` service for name generation/collision/lookup
3. Add Wrapped frame rendering endpoint (Puppeteer)
4. Build the React frontend consuming the API

### The Spike Codebase

**Location:** `~/code/bright/futureproof-data/backend/`

**Entry point:** `backend/cli.py` — interactive Rich CLI that walks through the full experience. This is the reference implementation for the frontend. Every screen in the UX flow maps to a function in this file.

**CLI → Frontend mapping:**

| CLI Function | UX Screen | What It Does |
|---|---|---|
| `_prompt_school()` | Screen 3: School + Major | Fuzzy school search via `school_lookup.search_schools()` |
| `_prompt_major_gemma_intent()` | Screen 3: School + Major | Full Gemma intent pipeline: free text → match → career preview → confirm → audit → cache |
| `_prompt_effort()` | Screen 4: Effort + Loans | Three effort levels → ERN shift |
| `_prompt_loans()` | Screen 4: Effort + Loans | Five loan % options → ROI scaling |
| `_build_full()` | Screen 5-6: Career Pick + Reveal | Orchestrates: `stat_engine.compute_pentagon()` → `career_tiering.tier_careers()` → `boss_fights.run_gauntlet()` → `branch_tree.get_branches()` → `skill_recs.generate_recs()` → `skill_pool.generate_pool()` → `guidance.generate_guidance()` |
| `_prompt_tiered_career_pick()` | Screen 5: Career Pick | Gemma-tiered career menu (Common / Less Common / Stretch) |
| `_display_build()` | Screen 6: Reveal + Stats | Renders Gemma's Take → pentagon → career header |
| `_run_gauntlet_paced()` | Screen 7: Boss Gauntlet | Sequential fights with reroll flow on loss/draw, then Next Steps |
| `_reroll_loss_flow()` | Screen 7: Boss Gauntlet | Interactive skill craft → rescore → structural loss |
| `_render_branches()` | Screen 8: Branch Tree | Stage 3 branch display |
| `_compare_flow()` | Screen 10: Risk Comparison | Multi-build comparison with report generation |
| `_branch_explore_flow()` | Screen 10: Branch Detail | Deep-dive into a specific branch |
| `_ask_gemma_flow()` | Screen 10: Ask Gemma | Multi-turn chat with build context |
| `_career_tree_flow()` | Screen 10: Career Tree | Experimental 3-level tree expansion |

### Service Layer

All business logic lives in `backend/app/services/`. Each service is stateless and testable. The CLI calls them directly; FastAPI routers will call the same functions.

| Service | File | What It Does | Tests |
|---|---|---|---|
| School lookup | `school_lookup.py` | Fuzzy search + program listing via MCP | `test_school_lookup.py` |
| Stat engine | `stat_engine.py` | Pentagon computation, effort/loan adjustments. Thin wrapper around MCP `get_career_paths`. | `test_stat_engine.py` |
| Career tiering | `career_tiering.py` | Gemma groups careers into Common/Less Common/Stretch. Deterministic fallback. | `test_career_tiering.py` |
| Boss fights | `boss_fights.py` | Gauntlet scoring with configurable thresholds. Reroll rescoring. Gemma narratives. | `test_boss_fights.py` |
| Skill pool | `skill_pool.py` | Gemma generates 3-5 skills per losing boss. `apply_skills()` mutates career stats. Fallback pool. | `test_skill_pool.py` |
| Skill recs | `skill_recs.py` | Post-build Gemma recommendations. | `test_skill_recs.py` |
| Guidance | `guidance.py` | "Gemma's Take" narrative + `chat_with_context()` for freeform chat. | `test_guidance.py` |
| Next Steps | `next_steps.py` | Post-gauntlet action checklist. No RPG framing. | — |
| Branch tree | `branch_tree.py` | Stage 3 branches from MCP. | `test_branch_tree.py` |
| Career tree | `career_tree.py` | Dynamic multi-level tree expansion. Experimental. | `test_career_tree.py` |
| Builds | `builds.py` | Save/load/compare. JSON persistence. | `test_builds.py` |
| Receipts | `receipts.py` | Inline provenance for every determination. | — |
| Report gen | `report_gen.py` | Markdown reports for builds and comparisons. | `test_report_gen.py` |
| Gemma client | `gemma_client.py` | Inference abstraction. Supports Ollama (local) and OpenRouter (cloud). Config switch. | — |
| MCP client | `mcp_client.py` | Brightsmith MCP server client. Wraps `query_iceberg()`. | — |

### Pydantic Models (API Contracts)

`backend/app/models/career.py` defines all data types. These are the API contract — the frontend will consume the exact same shapes once FastAPI routers are wired up.

**Key models:**

| Model | Fields | Used By |
|---|---|---|
| `Build` | `build_id`, `profile_name`, `school_name`, `unitid`, `major_text`, `cipcode`, `effort`, `loan_pct`, `career` (CareerOutcome), `gauntlet` (GauntletResult), `branches`, `skill_recs`, `guidance`, `skills_crafted`, `skill_pool`, `next_steps` | Everything — the master build object |
| `CareerOutcome` | `stats` (PentagonStats), `bosses` (BossScores), `soc_code`, `occupation_title`, `median_annual_wage`, `debt_to_earnings_annual`, `top_5_activities`, `burnout_drivers`, `substitution_applied`, `data_caveat` | Stat engine output, career display |
| `PentagonStats` | `ern`, `roi`, `res`, `grw`, `hmn` — all `int | None`, range 1-10 | Pentagon chart, boss fight scoring |
| `BossFightResult` | `boss`, `result`, `raw_score`, `threshold_win`, `threshold_draw`, `reason`, `narrative`, `rerolled`, `reroll_count`, `original_result` | Boss fight display, reroll tracking |
| `GauntletResult` | `fights` (list), `wins`, `losses`, `draws`, `verdict` | Gauntlet scorecard |
| `AppliedSkill` | `id`, `title`, `rationale`, `targets` (list of boss IDs), `delta_ern`, `delta_roi`, `delta_res`, `delta_grw`, `delta_hmn`, `delta_burnout_raw`, `delta_ceiling_raw` | Reroll mechanic, skill crafting |
| `CareerBranch` | `from_soc`, `to_soc`, `to_title`, `delta_ern/roi/res/grw/hmn`, `unlock` | Branch tree display |

### What the Frontend Consumes

The frontend doesn't need to know about DuckDB, MCP, CIP codes, or Brightsmith zones. It talks to a FastAPI backend that exposes endpoints mapping to the service layer:

| Endpoint (proposed) | Service Call | Returns |
|---|---|---|
| `POST /profile` | `profile.generate_name()` | `{profile_name: str}` |
| `GET /profile/{name}` | `profile.lookup(name)` | `{builds: BuildSummary[]}` |
| `GET /schools?q=` | `school_lookup.search_schools(q)` | `SchoolMatch[]` |
| `GET /schools/{unitid}/programs` | `school_lookup.get_programs(unitid)` | `Program[]` |
| `POST /intent` | Gemma intent resolution | `{matched_cip, matched_title, confidence, careers_preview}` |
| `POST /build` | `stat_engine.compute_pentagon()` + `career_tiering.tier_careers()` | `{outcomes: CareerOutcome[], tiers: {}}` |
| `POST /build/{id}/gauntlet` | `boss_fights.run_gauntlet(career)` | `GauntletResult` |
| `POST /build/{id}/reroll` | `skill_pool.apply_skills()` + `boss_fights.rescore_fight()` | `BossFightResult` (rescored) |
| `POST /build/{id}/next-steps` | `next_steps.generate_next_steps(build)` | `{checklist: str}` |
| `GET /branches/{soc}` | `branch_tree.get_branches(soc)` | `CareerBranch[]` |
| `GET /tree/{soc}` | `career_tree.build_tree(build)` | `TreeNode` (nested) |
| `POST /build/{id}/guidance` | `guidance.generate_guidance()` | `{narrative: str}` |
| `POST /build/{id}/chat` | `guidance.chat_with_context()` | `{response: str}` |
| `POST /builds/compare` | `builds.compare_builds(ids)` | `{stats, bosses, branches}` |
| `POST /build/{id}/save` | `builds.save_build(build)` | `{path: str}` |
| `GET /build/{id}/wrapped` | Puppeteer frame rendering | `{frames: [url, url, ...]}` |

### Stack

```
┌─────────────────────────────────────────┐
│           Web Frontend (React/Vite)     │
│         Dark-first, responsive          │
│         Brightpath design system        │
└──────────────┬──────────────────────────┘
               │ JSON API
┌──────────────┴──────────────────────────┐
│         Backend API (FastAPI)           │
│  - Routers → service layer (from spike) │
│  - 16 service modules, all working      │
│  - Pydantic models = API contracts      │
│  - Puppeteer for Wrapped frame render   │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────┴──────┐  ┌──────┴───────────────────────────┐
│  Gemma 4    │  │  Brightsmith Data Products        │
│  (Ollama)   │  │  (DuckDB-backed Gold zone)        │
│             │  │  7 consumable tables               │
│             │  │  280+ DQ rules                     │
│             │  │  MCP tool-use layer                │
└─────────────┘  └──────────────────────────────────┘
```

### Deployment

**Hackathon demo:** Frontend on Vercel/Netlify, backend + Gemma on cloud GPU.

**Ollama demo (for video + Ollama track):** Same codebase running entirely locally. Backend points to `localhost:11434`. Config switch, not code change. Video shows split-screen.

-----

## UX Flow

### Screen 1: Landing
Hero with tagline, pentagon glow animation, single CTA: "See where your path leads ✦"

### Screen 2: Profile Name
Auto-generated: "You are **dancing happy bear 🐻**" — reroll button — "Let's go →"
Returning users: "Already have a name?" → lookup field

### Screen 3: School + Major
Search school (fuzzy match) → type major (free text) → Gemma intent resolution → career preview → confirm → "See your build →"

### Screen 4: Effort + Loans
Two sliders side by side. Stat preview adjusts live. "Spec my build →"

### Screen 5: Career Pick
Tiered career list (Common / Less Common / Stretch). Student picks which career to build around.

### Screen 6: Reveal + Stats
Personalized loading: "Specing dancing happy bear 🐻..."
First build: stat tutorial walkthrough (each stat highlighted + explained)
Then: Gemma's Take narrative → pentagon radar chart animates in → career title + salary + ROI → "Fight the Bosses →"

### Screen 7: Boss Gauntlet
Sequential bosses with emoji icons. On loss/draw: reroll flow (skill options → equip → rescore → narrative). Structural loss messaging when pool exhausted. Next Steps checklist after gauntlet completes.

### Screen 8: Branch Tree
Dynamic tree from career center. Tap nodes to reveal stats + boss fight profiles. Fallback indicator for careers without pathway data.

### Screen 9: Save + Share
Save build → generate Wrapped frames → tap through story sequence → download/share → "Create another build?" or "Compare"

### Screen 10: Menu
- Compare builds (risk comparison)
- Explore a career branch in detail
- Ask Gemma (chat panel)
- Download report (if time permits)
- Create new build

-----

## Visual Design: Brightpath Design System

The frontend is built on **Brightpath**, a fully documented design system already implemented in the codebase. All visual decisions flow from the design system — no ad hoc hex codes or one-off styling.

### Design System Artifacts (Already Built)

| Artifact | Location | What It Contains |
|---|---|---|
| Design philosophy & token definitions | `docs/design-system-proposal.md` | Emotional framework per screen, three visual pillars (Cinematic Dark, Plush Materiality, Progressive Illumination), full color/type/spacing rationale |
| CSS custom properties (source of truth) | `frontend/src/styles/tokens.css` | All tokens: backgrounds, accents, stat colors, boss colors, borders, typography, radii, shadows, spacing, transitions, breakpoints |
| Tailwind configuration | `frontend/tailwind.config.ts` | Maps CSS custom properties to Tailwind utilities (`bg-bp-deep`, `text-accent-thrive`, `shadow-glow-insight`, etc.) |
| Interactive reference mockup | `docs/mockups/brightpath-design-system.html` | Live HTML reference showing all tokens rendered |

### Design Principles

1. **Cinematic Dark** — indigo-navy backgrounds (`#1B1D30` base), not black. Accent colors read as lights in the darkness. The student's future is literally being illuminated.
2. **Plush Materiality** — rounded corners (`14-20px`), gentle shadows, smooth gradients. Nothing hard or clinical. Makes a terrifying topic feel safe to explore.
3. **Progressive Illumination** — screens get brighter as the student progresses. Character select is warm. Stat reveal bursts. Branch tree is a constellation. The light levels mirror the journey from uncertainty to clarity.

### Token System

Every color, font, spacing value, and shadow in the frontend comes from CSS custom properties in `tokens.css`. Components use Tailwind utilities mapped to these tokens — never raw hex codes.

**Backgrounds:** `bg-void` → `bg-deep` → `bg-mid` → `bg-surface` → `bg-raised` (layered elevation)

**Accents (semantic):** `accent-thrive` (wins, growth, CTAs), `accent-alert` (losses, warnings), `accent-caution` (draws, attention), `accent-insight` (AI/data), `accent-info` (neutral information), `accent-empathy` (human edge, emotional)

**Stat colors (one per pentagon axis):** `stat-ern` (gold), `stat-roi` (green), `stat-res` (purple), `stat-grw` (blue), `stat-hmn` (pink)

**Boss colors (one per boss):** `boss-ai` (purple), `boss-loans` (orange), `boss-market` (blue), `boss-burnout` (pink), `boss-ceiling` (grey)

**Typography:** Display: Fredoka. Body: Nunito. Data: Space Mono. Scale: 1.25 ratio, base 16px.

**Motion:** CSS transitions for hover/focus (150ms/200ms/300ms ease-out). Spring animations for stat reveals and branch tree illumination defined in component code.

### What PRD v8 Changes in the Design System

The profile name system and emoji-only approach don't require new tokens — they use existing text and accent tokens. The Wrapped share frames use the same dark background and accent system. The stat tutorial overlay uses `bg-raised` with `accent-*` highlights. No design system changes needed for v8 scope.

-----

## Video Strategy (3 Minutes)

### Scene 1: The Question (0:00–0:15)
Student overwhelmed by AI headlines. *"Which school? Which major? Everyone's talking about AI taking jobs. Nobody's showing me where my path actually leads."*

### Scene 2: The Name + Build (0:15–0:45)
Hits CTA → "You are **brave curious fox 🦊**" → laughs → picks ISU → types "business" → Gemma maps it → career previews → confirms. Adjusts effort and loans. *"FutureProof starts with your school and your major — not abstract career data."*

### Scene 3: The Gauntlet + Reroll (0:45–1:30)
Stats reveal with tutorial. Fights bosses. Loses Fight AI → equips "Data Analytics Minor" → LOSE → WIN. Loses Fight Student Loans with 100% loans → equips everything → still loses → structural loss message. *"Some weaknesses you can fix. Some you can't. That's the most important thing this tool tells you."*

### Scene 4: The Branches (1:30–2:10)
Branch tree extends outward. Taps a management branch — AI resilience jumps. Taps the technical branch — earnings ceiling rises but burnout spikes. *"A degree isn't a destination. It's a starting position. See where every branch leads."*

Creates a second build. Risk comparison screen: two builds, different risk profiles.

### Scene 5: Share + Equity Punch (2:10–3:00)
Student taps "Share" → Wrapped frames appear → screenshots → shares to Stories → *"What name did you get?"* → friend opens FutureProof.

Ollama split screen: same app, local hardware. *"Because Gemma is open, any school can run this on their own server. No cloud. No cost. No data leaves the building. Every student gets this. Forever."*

-----

## Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Gemma intent resolution latency | Slow major selection | Cache confirmed mappings. Show "thinking" state. |
| Gemma response quality (generic advice) | Playbooks feel useless | Heavy prompt engineering. Gold-standard examples in prompts. |
| Inference latency (Gemma via Ollama) | Poor UX | Cache aggressively. Personalized loading animations. |
| CIP → SOC crosswalk gaps | School+major doesn't map to careers | Tiered matching + Gemma supplementation. Label estimated distributions. |
| O*NET pathway data thin for some careers | Branch tree empty | Graceful fallback. Full Stage 2 experience still works. |
| Reroll skill pool too generic | Skills don't feel real | Gemma generates personalized pool per career. Fallback pool as safety net. |
| Profile name collisions at scale | Name generation fails | Silent regeneration. 20K combinations is sufficient for hackathon. |
| School sensitivity (perceived ranking) | Backlash | Empowerment tone. Risk comparison shows tradeoffs, never declares winners. |
| AI scores presented as fact | Credibility/liability | Heavy disclaimers. "AI-estimated" labels everywhere. |
| Wrapped frame rendering performance | Slow share experience | Pre-render common frame templates. Optimize Puppeteer pipeline. |

-----

## Disclaimers (Must Ship in Product)

- "AI exposure scores are AI-generated estimates based on job task analysis, not empirical measurements."
- "Career outcome distributions are modeled from public data and may not reflect individual outcomes."
- "This tool provides information to support your decision-making. It is not a substitute for professional career counseling."
- "Career branches represent common career transitions observed in labor market data, not guaranteed outcomes."
- Where Gemma-estimated data is used: clearly labeled as "AI-estimated" vs. observed data.
- Receipts on every data point show source and methodology.

-----

## Week 6 Submission Emphasis

- Lead with the adversarial auditor / self-correcting pipeline story: 280+ DQ rules, chaos monkey testing, pipeline that catches its own LLM mistakes
- Story frame: *"Students deserve trustworthy data, not hallucinated guidance."*
- Highlight scale: 700K+ cross-source rows, 7 data contracts, Bronze → Silver → Gold governance
- Highlight Gemma depth: 10 distinct integration surfaces, not a chat wrapper
- Highlight the reroll mechanic + structural loss as the coaching innovation
- Highlight the Wrapped share experience as the viral growth mechanic

-----

## Spec Backlog

Specs are written to `docs/specs/` and executed by Claude Code. This table tracks what needs to be built, in priority order.

### Backend Specs

| # | Spec Name | Scope | Status | Depends On |
|---|---|---|---|---|
| B1 | `fastapi-router-wiring` | Wire FastAPI routers to existing service layer. ~15 endpoints from the proposed API table. All services exist — this is plumbing. | 🟡 Partially complete | — |

> **B1 status detail:** Server starts, health endpoint works, `/docs` shows all 26 endpoints, school search works, profile endpoints work, CORS configured. **Remaining:** 5 acceptance criteria require Gemma/Ollama running to validate: `POST /intent`, `POST /build/outcomes`, `POST /build`, `POST /build/{id}/reroll`, `POST /build/{id}/chat`. These endpoints are wired but untested against a live Gemma instance.
| B2 | `profile-service` | New `profile.py` service: three-word name generation (adjective pools + animal emoji set), collision detection against saved profiles, case-insensitive fuzzy lookup for returning users, reroll. | ✅ Complete | B1 |

### Frontend Specs

| # | Spec Name | Screens | Scope | Status | Depends On |
|---|---|---|---|---|---|
| F1 | `screen-landing-profile` | 1, 2 | Landing hero (tagline, pentagon glow, CTA) + profile name generation (auto-assign, reroll button, returning user lookup). First thing the student sees. | ✅ Complete | B1, B2 |
| F2 | `screen-school-major-sliders` | 3, 4 | School search (fuzzy match) + major input (free text → Gemma intent resolution UI → career preview → confirm) + effort slider + loan % slider with live stat preview. The input phase. | ⬜ Not started | B1, F1 |
| F3 | `screen-career-pick-reveal` | 5, 6 | Tiered career picker (Common / Less Common / Stretch) + personalized loading ("Specing dancing happy bear 🐻...") + stat tutorial overlay (first build only) + Gemma's Take narrative + pentagon animation + career detail. | ⬜ Not started | B1, F2 |
| F4 | `screen-boss-gauntlet` | 7 | Sequential boss fights with emoji icons. Reroll flow on loss/draw (skill options → equip → rescore → Gemma narrative). Structural loss messaging when pool exhausted. Next Steps checklist after gauntlet completes. Most interactive screen. | ⬜ Not started | B1, F3 |
| F5 | `screen-branch-tree` | 8 | The signature visualization. Dynamic tree from career center, branches extending outward. Tap nodes to reveal stats + boss fight profiles + unlock requirements. Fallback indicator for careers without pathway data. | ⬜ Not started | B1, F4 |
| F6 | `screen-save-wrapped` | 9 | Save build + Spotify Wrapped share experience. Multi-frame story sequence (identity → pentagon → boss scorecard → comparative insight → risk highlight → CTA). Puppeteer rendering pipeline on backend. Download/share buttons. | ⬜ Not started | B1, F5 |
| F7 | `screen-menu-compare-chat` | 10 | Post-build hub: risk comparison experience (tradeoff-focused, not stat tables), branch detail explorer, Ask Gemma chat panel, report download button (if time permits), new build. | ⬜ Not started | B1, F6 |

### Stretch / Bonus Specs

| # | Spec Name | Scope | Status | Depends On |
|---|---|---|---|---|
| S1 | `gemma-ai-exposure-rescore` | Rebuild Karpathy's scores natively with Gemma using O*NET task-level data. Spec already written at `docs/specs/gemma-ai-exposure-rescore.md`. | ⬜ Not started | All frontend complete |
| S2 | `historical-parallels` | Add curated historical parallel data to boss fight narrative prompts. | ⬜ Not started | F4 |
| S3 | `counselor-report` | "Download report" button in menu. Backend `report_gen.py` already works — needs frontend button + PDF render endpoint. | ⬜ Not started | F7 |

### Completed Specs (Reference)

| Spec | What It Built | Completed |
|---|---|---|
| `spec-0-scaffolding` | React/Vite + FastAPI project structure | Week 1 |
| College Scorecard ingestor | Bronze → Silver → Gold, 69,947 rows | Week 1 |
| BLS OOH ingestor | Bronze → Silver → Gold, 832 occupations | Week 1-2 |
| O*NET ingestor | Bronze → Silver → Gold, 798 occupations, 15,944 transitions | Week 1-2 |
| Karpathy AI exposure ingestor | Bronze → Gold, 389 scores | Week 2 |
| BEA Regional Price Parities | Bronze → Gold, 51 rows | Week 2 |
| CIP-SOC crosswalk | Silver zone, 626K paths | Week 2 |
| `gold-futureproof-engine` | Engine tables with derived stats + boss scores | Week 2 |
| `gold-futureproof-engine-backfill-ai` | RES stat + Fight AI boss backfill | Week 2 |
| `mcp-futureproof-core` | MCP tool-use layer for Gemma | Week 2 |
| Spike backend (`backend/cli.py`) | 16 services, 10 Gemma surfaces, full interactive loop | Week 2-3 |
| `feature-onboarding-screens` | Design mockups for landing, school+major, character select | Week 2 |
| Brightpath design system | CSS tokens, Tailwind config, design philosophy | Week 2 |

-----

## Hi-Fi Mockups

All mockups live in `docs/mockups/`. Created by @fp-design-visionary. These are the pixel-perfect implementation targets for frontend specs — each screen spec should reference its corresponding mockup(s).

### Current Screens (1 per PRD screen)

| File | Screen | Description | Key Interactions |
|---|---|---|---|
| `screen-01-landing.html` | Screen 1 | Hero with pentagon constellation glow, twinkling stars, gradient tagline, CTA | CTA loading state; scenario switcher (default, loading, error) |
| `screen-02-profile.html` | Screen 2 | Auto-generated three-word name + emoji, reroll animation, returning user lookup | Reroll crossfade between names; returning user found/suggestion/not-found states |
| `screen-03-school-major.html` | Screen 3 | School search, Gemma intent resolution, career preview cards, confirm | Autocomplete dropdown, Gemma thinking state, match card, audit rejection |
| `screen-04-effort-loans.html` | Screen 4 | Two sliders (effort + loans), live stat preview, inline stat legend | Sliders update stats in real-time; tappable stat legend; radar/bar toggle |
| `screen-05-career-pick.html` | Screen 5 | Tiered career list — Common / Less Common / Stretch | Accordion tiers, selection glow, receipt links, natural-language stat hints |
| `screen-06-reveal-stats.html` | Screen 6 | Personalized loading, pentagon bloom animation, Gemma's Take | Pentagon draws from center with spring physics; radar/bar toggle; receipt popovers |
| `screen-07-boss-gauntlet.html` | Screen 7 | Sequential boss fights (emoji bosses), WIN/LOSS/DRAW, reroll mechanic, Next Steps | Reroll skill cards with stat deltas, fight rescoring, checkable Next Steps list |
| `screen-08-branch-tree.html` | Screen 8 | Dynamic career tree — the signature visualization | Bezier branches with staggered draw, tap nodes for detail panel, radar/bar toggle |
| `screen-09-save-share.html` | Screen 9 | Save build + Wrapped story sequence (6 frames) | Tap through Wrapped frames in phone mockup, download/share buttons, radar/bar toggle |
| `screen-10-menu.html` | Screen 10 | Hub — compare builds, branch explorer, Ask Gemma chat, new build | Side-by-side compare, multi-turn Gemma chat, action tiles |

### Shared / Reference

| File | Description |
|---|---|
| `chrome-shell.html` | Application shell — header, navigation, profile persistence across all screens. Screen selector to preview chrome state on each of the 10 screens. |
| `brightpath-design-system.html` | Interactive design system reference — all Brightpath tokens rendered (palette, typography, spacing, components) |

### Legacy Explorations (superseded by current screens)

| File | Description |
|---|---|
| `futureproof-landing-v2.html` | Earlier landing page exploration (pre-vision report) |
| `futureproof-profile-v1.html` | Earlier profile screen exploration (pre-vision report) |
| `futureproof-school-major-v2.html` | Earlier school+major exploration (pre-vision report) |

15 mockups total — 10 current screens, 1 chrome shell, 1 design system reference, 3 legacy explorations.

-----

---

## Backlog

### School Location Data in Search Dropdown

**Priority:** Low — polish item, not blocking
**Status:** BACKLOG

Add city and state to each school search result so the dropdown shows the institution name on the left and "City, ST" on the right (e.g. "Indiana State University → Terre Haute, IN"). Matches the autocomplete dropdown spec in DESIGN.md.

**Work required:**

1. **Data:** Ingest the College Scorecard institution-level file (only `unitid`, `INSTNM`, `CITY`, `STABBR` needed). Lightweight reference table — not a full bronze→silver→gold pipeline. Store in `data/reference/` or as a simple DuckDB table the MCP server can join against. Source: `https://collegescorecard.ed.gov/data/` → "Most Recent Institution-Level Data" CSV.

2. **Backend:** Add `city` and `state_abbr` fields to `SchoolMatch` model (`backend/app/models/career.py`). Update `search_schools()` in `school_lookup.py` to join location from the reference table.

3. **Frontend:** Add `city` and `state_abbr` to `SchoolSearchResult` type (`frontend/src/types/buildInput.ts`). Update `SchoolSearch.tsx` dropdown rows to show city/state right-aligned in `font-data text-data-sm text-text-muted` per DESIGN.md autocomplete dropdown spec. Add 3px left border in `accent-thrive` on highlighted rows.

---

*— End of Hackathon PRD v8 —*
