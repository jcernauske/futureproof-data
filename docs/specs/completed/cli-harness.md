# Spec: CLI Harness — FutureProof Interactive Session

*Vet the entire product loop in the terminal before touching React*

**Status:** DEPRECATED — CLI harness no longer needed; product loop vetted in-app
**Owner:** Jeff
**Priority:** P0 — blocks frontend work
**Created:** 2026-04-11
**Last Updated:** 2026-04-11
**Repo:** `~/code/bright/futureproof-data/` (monorepo)

---

## Implementation Notes (2026-04-11)

**Delivered:**
- `backend/app/services/` — `gemma_client`, `mcp_client`, `school_lookup`, `stat_engine`, `boss_fights`, `branch_tree`, `guidance`, `skill_recs`, `builds`
- `backend/app/models/career.py` — Pydantic contracts (`CareerOutcome`, `PentagonStats`, `BossScores`, `GauntletResult`, `Build`, etc.) — the API contract the frontend will consume verbatim.
- `backend/cli.py` — full interactive flow with `rich` formatting (banner, status spinners, pentagon, gauntlet, branches, skill recs, guidance, menu, compare flow, branch explorer).
- 59 hermetic pytest tests in `backend/tests/services/` — no live MCP / Gemma calls; all dependencies stubbed.

**Deviations from spec:**

1. **Data access:** Spec preferred calling `FutureProofMCPServer` handler methods directly; this is what shipped. The spec-referenced `data/warehouse` + `data/catalog/catalog.db` construction still works — the catalog has absolute metadata paths pointing at the real `data/gold/iceberg_warehouse/consumable/*` tables, so `data/warehouse` being empty is irrelevant for reads. `data/futureproof.duckdb` referenced in CLAUDE.md is stale (empty); MCP server is the only working path.

2. **Run command:** Spec says `cd backend && python cli.py`. Actual command is `uv run python backend/cli.py` from project root. Reason: the MCP server imports `brightsmith`, `pyiceberg`, and `pyyaml`, which live only in the root `uv`-managed venv. The `shim` at the top of `cli.py` adds `backend/` to `sys.path` so `app.*` imports resolve from either working directory. A standalone `backend` venv is not required; root venv handles everything. `backend/pyproject.toml` was updated to mirror the CLI deps for users who want `pip install -e backend[dev]` later.

3. **CIP substitution handoff:** The CLI passes the school's REPORTED (broad) cipcode to `stat_engine.compute_pentagon` whenever the YAML lookup flagged substitution, then forwards the typed major as `student_major`. The MCP server's `get_career_paths` handler does the substitution internally and returns the blended row set. Tested end-to-end with IU-B (151351) + "Marketing" → 52.01→52.14 substitution → Fundraisers headline career.

4. **Effort slider:** Spec said "Adjusts ERN/ROI by effort percentile". Implemented as a deterministic ±1 shift (`EFFORT_SHIFT` dict), clamped to [1,10]. Constants are live-tunable from a single module-level dict.

5. **Boss fight thresholds:** Landed as the values in the spec's threshold table. Fight AI uses `RES+HMN`, Fight Burnout inverts `boss_burnout_score` so high-readiness wins, Fight Ceiling falls back to `ERN` when `boss_ceiling_score` is null. `BOSS_SPECS` dict is designed for live tuning during the kid testing session.

6. **Skill recs + guidance:** Gemma parse + deterministic fallback. If Gemma is unreachable (Ollama not running, no OpenRouter key), the CLI renders a static rec set and a template-based "Gemma's Take" rather than crashing. Both use the same prompts the spec specified.

**Verification:**
- `uv run ruff check backend/app backend/cli.py backend/tests/services` → clean
- `uv run mypy backend/app backend/cli.py --config-file backend/pyproject.toml` → clean for everything in this spec (4 pre-existing fastapi errors in `main.py` / `routers/health.py` are untouched)
- `uv run pytest backend/tests/services` → **59 passed**
- `uv run pytest -q` (full pipeline) → **1204 passed, 1 deselected** (zero regression)
- End-to-end smoke: IU-B Marketing → Fundraisers → pentagon + gauntlet + 10 branches + build save/load/list round-trip ✅

**Next actions (not in this spec):**
- Live kid testing session → tune `BOSS_SPECS` thresholds + `EFFORT_SHIFT` values
- Wire the services into FastAPI routers for the frontend
- Function calling agent loop (separate spec) — builds on top of these same services


---

## Why

The product loop — school + major → stats → boss fights → branches → guidance — is entirely data-in, data-out. None of it requires a UI to validate. Building a CLI harness lets us:

1. Put a real high school senior in front of the experience and see if it's valuable
2. Validate Gemma's function calling, guidance quality, and tone before committing to UI
3. Lock in the API contracts that the frontend will consume
4. Find data gaps, bad stat formulas, or weak guidance before they're buried under React components

The CLI IS the backend. When we build the frontend, each screen just calls the same service functions the CLI proved out.

---

## What Ships

A single interactive CLI script at `backend/cli.py` that walks a user through the full FutureProof experience:

```
$ cd backend && python cli.py

═══════════════════════════════════════════════════
  ✦ FutureProof — See Where Every Path Leads ✦
═══════════════════════════════════════════════════

What school are you looking at? > Indiana University Bloomington

Found 3 matches:
  1. Indiana University-Bloomington (151351)
  2. Indiana University-East (151324)
  3. Indiana University-Kokomo (151290)

Which one? [1] > 1

Loading programs for Indiana University-Bloomington...
Found 127 programs. What's your major? > Marketing

Matched: Marketing/Marketing Management (CIP 52.14)
  ℹ IU-B reports under Business/Commerce General (52.01).
    Using Marketing-specific career paths with IU-B's
    business program earnings. [substitution applied]

How much time will you have to focus on school?
  1. Working + school — limited focus (25th percentile)
  2. Balanced — solid effort (50th percentile)
  3. All-in — maximum focus (75th percentile)
[2] > 2

Building your character...

══════════════════════════════════════
  📊 Your Build: IU-B Marketing
══════════════════════════════════════

  Career: Marketing Managers (SOC 11-2021)
  Median Salary: $157,620
  Entry Education: Bachelor's degree

  ┌─────────────────────────┐
  │     ERN ████████░░  8   │
  │     ROI █████████░  9   │
  │     RES ███░░░░░░░  3   │
  │     GRW ██████░░░░  6   │
  │     HMN ███████░░░  7   │
  └─────────────────────────┘

══════════════════════════════════════
  ⚔️  Boss Gauntlet
══════════════════════════════════════

  🤖 Fight AI .............. LOSE (RES 3 + HMN 7 = 10 < threshold)
     "AI is already handling data aggregation, campaign
      analytics, and A/B testing. The strategic and
      relationship side stays human — for now."

  💰 Fight Student Loans ... WIN  (ROI 9)
     "IU-B's in-state tuition keeps debt manageable
      against marketing manager earnings."

  📈 Fight the Market ...... WIN  (GRW 6 + ERN 8)
     "Marketing management is projected to grow 6%
      through 2034. Demand is steady."

  🔥 Fight Burnout ......... DRAW (burnout_score 5)
     "Moderate time pressure, standard hours. Not a
      burnout factory, not a cakewalk."

  📊 Fight the Ceiling ..... WIN  (ERN trajectory 8→9)
     "Marketing managers have a strong earnings
      ceiling — senior roles push past $200K."

  🏆 Fight the Future ...... 3W / 1L / 1D
     Overall: SOLID BUILD with an AI exposure gap.

══════════════════════════════════════
  🌳 Career Branches (Stage 3)
══════════════════════════════════════

  From Marketing Managers (11-2021):

  → Brand Director (11-2021 → 11-2011)
    ERN +1 | HMN +1 | RES -1
    Unlock: 5+ years brand management, MBA preferred

  → VP of Marketing (11-2021 → 11-1021)
    ERN +2 | HMN +2 | RES +1
    Unlock: 8+ years, executive leadership experience

  → Market Research Director (11-2021 → 13-1161)
    ERN -1 | HMN -1 | RES -2 | GRW +1
    Unlock: Analytics skills, data science coursework

  → Sales Director (11-2021 → 11-2022)
    ERN +1 | HMN +2 | RES +2
    Unlock: Sales experience, relationship management

  [Showing 4 of 8 branches. Press Enter for all, or 's' to skip]

══════════════════════════════════════
  🎓 Skill Recommendations
══════════════════════════════════════

  To strengthen your build while still in school:

  • Data Analytics Minor .............. RES +2
    "Learn to direct AI analysis, not compete with it."

  • Digital Marketing Certification ... RES +1
    "Hands-on with the AI tools reshaping marketing."

  • Client Management Internship ...... HMN +2
    "The relationship side is the human edge."

  • Business Strategy Coursework ...... HMN +1
    "Strategic thinking is what AI can't replicate."

══════════════════════════════════════
  💬 Gemma's Take
══════════════════════════════════════

  "IU-Bloomington's Kelley School gives you a strong
   brand and solid earnings — Marketing Managers earn
   a $157K median, and your ROI is excellent at in-state
   tuition. Your main vulnerability is AI: marketing
   analytics, A/B testing, and campaign optimization
   are already being automated. But here's the thing —
   the strategic, creative, relationship-heavy side of
   marketing is exactly what AI can't do. Your playbook:
   learn to direct AI tools (take the data analytics
   minor), but invest heavily in the human skills —
   client management, brand strategy, creative direction.
   The IU marketing grad who uses AI as a force multiplier
   will outcompete peers who either fear it or ignore it."

══════════════════════════════════════
  What next?
══════════════════════════════════════
  [1] Save this build
  [2] Try a different school or major
  [3] Compare saved builds
  [4] Explore a career branch in detail
  [q] Quit

>
```

---

## Architecture

The CLI is a thin interactive wrapper around service functions that become the FastAPI endpoints later.

```
cli.py (interactive prompts + display formatting)
  │
  ├── services/school_lookup.py    → search schools, list programs
  ├── services/stat_engine.py      → compute 5-stat pentagon from MCP data
  ├── services/boss_fights.py      → win/lose/draw + narrative generation
  ├── services/branch_tree.py      → Stage 3 career branches
  ├── services/skill_recs.py       → Gemma-generated skill recommendations
  ├── services/guidance.py         → Gemma career guidance narrative
  ├── services/builds.py           → save/load/compare builds
  └── services/gemma_client.py     → unified inference client (Ollama / OpenRouter)
```

When the frontend ships, `routers/career.py` calls the same service functions. The CLI and the API share 100% of the business logic.

### Data Access

Services can either query the DuckDB directly at `data/futureproof.duckdb` or import from `src/mcp_server/futureproof_server.py` — both are in the same repo and venv now.

Preferred approach: **import `FutureProofMCPServer` directly** and call its handler methods. This avoids duplicating SQL queries and ensures the CLI exercises the exact same code paths that Gemma's function calling will use in production.

```python
import sys
sys.path.insert(0, "src")
from mcp_server.futureproof_server import FutureProofMCPServer

server = FutureProofMCPServer(
    warehouse_path="data/warehouse",
    catalog_path="data/catalog/catalog.db",
    server_name="futureproof-cli",
)

# Call MCP tools directly
result = server.call_tool("get_career_paths", {
    "unitid": 151351,
    "cipcode": "52.01",
    "student_major": "Marketing"
})
```

### Gemma Integration

`services/gemma_client.py` reads `INFERENCE_BACKEND` and `OPENROUTER_API_KEY` from `.env` (already configured). Uses the OpenAI SDK pointed at either Ollama or OpenRouter. Same code from the cloud-gemma-deployment spec.

Gemma is called for:
- **School name resolution** (fuzzy match disambiguation — "IU" → which campus?)
- **Major-to-CIP resolution** (when the YAML lookup misses — Spike E/F validated this)
- **Boss fight narratives** (1-2 sentence contextual explanation per fight)
- **Skill recommendations** (generated from O*NET task data for the career)
- **Career guidance synthesis** (the "Gemma's Take" block — the core value prop)

Gemma is NOT called for:
- Stat computation (deterministic from data)
- Boss fight win/lose determination (deterministic threshold logic)
- Branch tree generation (deterministic from career_transitions data)
- School/program lookup (DuckDB query)

### Function Calling vs Direct Query

For the CLI, Gemma does NOT use function calling to retrieve data. The CLI calls the service functions directly (they query DuckDB), assembles the data, then passes the assembled data to Gemma as context for narrative generation. This is simpler, faster, and more reliable than a multi-hop function calling loop.

Function calling is for the production agent layer where Gemma needs to autonomously decide what to query. For the CLI, we already know the query flow — it's the same every time.

The function calling agent loop is a separate spec (Gemma Agent Integration) that builds on top of these same services.

---

## Implementation Details

### School Lookup (`services/school_lookup.py`)

```python
def search_schools(query: str) -> list[SchoolMatch]:
    """Fuzzy search by institution name. Returns up to 10 matches."""
    # SQL: SELECT DISTINCT unitid, institution_name
    #      FROM consumable.career_outcomes
    #      WHERE LOWER(institution_name) LIKE '%{query}%'
    #      ORDER BY institution_name LIMIT 10

def get_programs(unitid: int, min_confidence: str = "low") -> list[Program]:
    """All programs at a school with earnings/debt summary."""
    # SQL: SELECT DISTINCT cipcode, program_name, median_earnings_2yr,
    #             median_debt, confidence_tier
    #      FROM consumable.career_outcomes
    #      WHERE unitid = ? ORDER BY program_name

def resolve_major(major_text: str, programs: list[Program]) -> MajorMatch:
    """Match student's typed major to a program.
    
    Flow:
    1. Exact match against program_name (case-insensitive)
    2. Substring match
    3. YAML lookup table (data/reference/major_to_cip.yaml via symlink)
    4. Gemma intent resolution (Spike E/F validated, ~5s via OpenRouter)
    
    Returns the matched cipcode + whether substitution is needed.
    """
```

### Stat Engine (`services/stat_engine.py`)

```python
def compute_pentagon(
    unitid: int,
    cipcode: str,
    student_major: str | None,
    effort: float,  # 0.0 = 25th pctl, 0.5 = 50th, 1.0 = 75th
) -> list[CareerOutcome]:
    """The core query. Returns career outcomes with full pentagon stats.
    
    Mirrors get_career_paths MCP tool logic:
    - Pulls from program_career_paths (the 626K row core table)
    - Applies CIP substitution when needed
    - Adjusts ERN/ROI by effort percentile
    - Returns sorted by stats_available_count DESC
    """
```

### Boss Fights (`services/boss_fights.py`)

```python
@dataclass
class BossFightResult:
    boss: str           # "ai", "loans", "market", "burnout", "ceiling"
    result: str         # "win", "lose", "draw"
    score: float        # raw score used for determination
    narrative: str      # Gemma-generated 1-2 sentence explanation
    historical: str     # historical parallel (on loss only)

def run_gauntlet(career: CareerOutcome) -> list[BossFightResult]:
    """Run all 5 boss fights + Final Boss against a career outcome.
    
    Thresholds (from PRD):
    - Fight AI: RES + HMN >= threshold → win
    - Fight Loans: ROI >= threshold → win  
    - Fight Market: GRW + ERN >= threshold → win
    - Fight Burnout: burnout_score <= threshold → win
    - Fight Ceiling: ceiling trajectory → win
    - Fight the Future: composite scorecard
    
    Narratives generated by Gemma with career context.
    """
```

### Boss Fight Thresholds

These need to be tuned during CLI testing. Start with:

| Boss | Win Condition | Draw | Lose |
|---|---|---|---|
| Fight AI | RES + HMN >= 14 | 10-13 | < 10 |
| Fight Loans | ROI >= 7 | 5-6 | < 5 |
| Fight Market | GRW >= 6 | 4-5 | < 4 |
| Fight Burnout | burnout_score <= 4 | 5-6 | >= 7 |
| Fight Ceiling | ceiling_score >= 7 | 5-6 | < 5 |

Expose these as constants so they're easy to adjust after the high-schooler testing session.

### Branch Tree (`services/branch_tree.py`)

```python
def get_branches(soc_code: str) -> list[CareerBranch]:
    """Stage 3 branches from career_transitions + career_branches.
    
    Returns related occupations with stat deltas, sorted by
    relatedness. Primary branches only by default.
    """
```

### Guidance Generation (`services/guidance.py`)

```python
def generate_guidance(
    school_name: str,
    major: str,
    career: CareerOutcome,
    boss_results: list[BossFightResult],
    branches: list[CareerBranch],
) -> str:
    """Gemma generates the 'Gemma's Take' career guidance narrative.
    
    Prompt includes:
    - School + major context
    - Full stat pentagon
    - Boss fight results (especially losses)
    - Available branches
    - Empowerment framing instructions
    
    Tone: coaching, not doom. "Here's your playbook" not "you're screwed."
    """
```

### Gemma Prompt for Guidance

```
You are a career coach helping a high school student evaluate their
college and major choice. You are direct, specific, and empowering.
You never tell a student their path is doomed — you tell them what
to do about their weaknesses.

The student is considering {school_name}, majoring in {major}.

Their post-graduation career profile:
- Primary career: {career_title} ({soc_code})
- Median salary: ${median_wage}
- Stats: ERN {ern}/10, ROI {roi}/10, RES {res}/10, GRW {grw}/10, HMN {hmn}/10

Boss fight results:
{boss_results_formatted}

Career branches available:
{branches_formatted}

Write 4-6 sentences of career guidance for this student. Be specific
to their school and major — not generic advice. Reference their stats
and boss fight results. If they lost a boss fight, explain what they
can do about it. Mention 1-2 specific actions they can take while
still in school.

Do NOT use bullet points. Write in a conversational, direct tone.
Do NOT start with "Great choice" or similar platitudes.
```

### Build Management (`services/builds.py`)

```python
def save_build(build: Build) -> str:
    """Save to a local JSON file at backend/data/builds/{build_id}.json"""

def load_build(build_id: str) -> Build:
    """Load a saved build."""

def list_builds() -> list[BuildSummary]:
    """List all saved builds."""

def compare_builds(build_ids: list[str]) -> ComparisonResult:
    """Side-by-side comparison of 2-3 builds."""
```

Builds are saved as JSON files for the CLI. The frontend will use DuckDB or an API endpoint, but for CLI testing JSON files are simpler and human-readable.

---

## CLI Interaction Flow

### Main Loop

```
1. Search school (fuzzy text input)
2. Disambiguate if multiple matches
3. Show programs, student types their major
4. Resolve major → cipcode (lookup table → Gemma fallback)
5. Effort slider (1/2/3 choice)
6. Compute pentagon + boss fights + branches + guidance (loading spinner)
7. Display results (formatted text output)
8. Menu: save / new build / compare / explore branch / quit
```

### Compare Flow

```
1. List saved builds (name, school, major, headline stats)
2. Pick 2-3 to compare
3. Side-by-side stat pentagons
4. Boss fight scorecard comparison
5. Branch availability comparison
6. Gemma comparison summary ("Build A wins on ceiling but loses on AI resilience...")
```

### Branch Exploration

```
1. Pick a branch from the Stage 3 list
2. Show full stat pentagon for that branch endpoint
3. Run boss fights against branch stats
4. Show what's needed to unlock (education, experience, certs)
5. Gemma generates branch-specific guidance
```

---

## What Does NOT Ship in the CLI

- Character creation (species/accessories) — purely visual, no data impact
- Character card image generation — needs server-side rendering
- Animations / transitions — it's a terminal
- Mobile responsiveness — it's a terminal
- The effort slider is a 1/2/3 choice, not a smooth slider

These are all frontend concerns. The CLI validates the data and guidance layer.

---

## Dependencies

```
# Already in backend/pyproject.toml or add:
duckdb
openai          # for Gemma client (Ollama + OpenRouter)
python-dotenv   # for .env loading
pydantic        # for data models
pyyaml          # for major_to_cip.yaml loading
rich            # for terminal formatting (tables, panels, colors)
```

`rich` is the one new dependency — it gives us formatted tables, colored output, panels, and progress spinners in the terminal without any complexity. Makes the CLI output actually readable for a high schooler.

---

## Testing

### Automated Tests

- `tests/services/test_school_lookup.py` — school search, program listing, major resolution
- `tests/services/test_stat_engine.py` — pentagon computation, effort adjustment, substitution
- `tests/services/test_boss_fights.py` — threshold logic, all win/lose/draw paths
- `tests/services/test_branch_tree.py` — branch retrieval, stat deltas
- `tests/services/test_builds.py` — save/load/compare round-trip

### Manual Testing (the real test)

Put the high schooler in front of `python cli.py` and observe:
- Do they understand the stats?
- Do the boss fight results make sense to them?
- Is Gemma's guidance specific and useful, or generic?
- Do they want to try a different school/major after seeing results? (good sign)
- Do they understand the branches?
- What questions do they ask that the CLI can't answer? (scope for next spec)

Record their session — the observations feed directly into the frontend spec and possibly into the demo video.

---

## After This Spec

The CLI harness produces:
1. **Validated service layer** — same functions the FastAPI routers will call
2. **Tuned boss fight thresholds** — calibrated from real testing
3. **Validated Gemma prompts** — guidance quality confirmed with a real user
4. **API contracts** — Pydantic models that become the OpenAPI schema
5. **User feedback** — what a real student cares about, what's confusing, what's missing

The frontend spec can then be written with confidence: "render what the CLI already proves works."

---

## Estimated Effort

| Step | Estimate |
|------|----------|
| gemma_client.py (reuse from deployment spec) | 30 min |
| school_lookup.py + tests | 2 hrs |
| stat_engine.py + tests | 3 hrs |
| boss_fights.py + tests | 2 hrs |
| branch_tree.py + tests | 1 hr |
| guidance.py (Gemma prompts) | 2 hrs |
| builds.py (save/compare) | 1 hr |
| cli.py (interactive wrapper + rich formatting) | 3 hrs |
| Prompt tuning + threshold calibration | 2 hrs |
| **Total** | **~16-20 hrs** |

---

*— End of Spec —*
