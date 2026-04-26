# Spike: Analyze Orphan API Endpoints (Decide Keep vs. Remove)

## Claude Code Prompt

```
Read the spec at docs/specs/spike-analyze-orphan-api-endpoints.md in its entirety.

This is an ANALYSIS spike — output is a written recommendation, NOT a code change.
Do NOT delete or modify any router, service, model, or test as part of executing this spec.

Execute the following workflow:

1. INVESTIGATION
   - For each endpoint listed in §4 "Endpoints Under Review":
     a. Confirm zero frontend callers (re-grep at execution time, not relying on prior audit).
     b. Search `archive/spikes/cli/` for callers (the archived CLI may still consume them).
     c. Search `scripts/` for callers (one-off operational scripts).
     d. Search `docs/`, `README.md`, `docs/specs/completed/`, `docs/futureproof_vision_roadmap.md`,
        and the Kaggle submission materials for documented promises that the endpoint exists.
     e. Search the OpenAPI surface (`backend/app/main.py` registration + any generated `openapi.json`)
        to confirm the endpoint is publicly exposed.
     f. Check git history (`git log --all -p -- backend/app/routers/<file>.py`) for any indication
        the endpoint is used by an external system Jeff mentioned (demo script, beta-tester landing,
        Kaggle reviewer instructions).
   - For each endpoint, fill in §6 "Per-Endpoint Findings" with the data above and a recommendation.

2. RECOMMENDATION
   - Write §7 "Final Recommendation" — for each endpoint, one of:
     * REMOVE — no callers, no documented promise, no demo dependency. Cleanup goes in spec
       `refactor-remove-dead-frontend-code.md` (CONDITIONAL items there are gated on this verdict).
     * KEEP — has a real consumer or a documented external promise. Justify.
     * KEEP-AND-DOCUMENT — endpoint is intentionally public surface (e.g., MCP-callable, demo URL)
       but undocumented. File a follow-up to add docs.
   - Surface any second-order cleanup the recommendation enables or blocks.

3. HUMAN REVIEW
   - Set status to AWAITING HUMAN REVIEW.
   - Do NOT proceed to deletion. Jeff makes the call.

4. HAND-OFF (only after Jeff approves)
   - For each REMOVE verdict, file the deletion items in spec `refactor-remove-dead-frontend-code.md`'s
     §4 (or open a new spec if the deletions are large enough to warrant it).
   - Mark this spec COMPLETE.

NO CODE CHANGES IN THIS SPEC. If you catch yourself editing a router, stop.
```

---

## Status: DRAFT

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-26 |
| Author | Jeff + Claude (staff-engineer audit + Codex verification) |
| Spec Version | 1.0 |
| Last Updated | 2026-04-26 |
| Blocked By | — |
| Related Specs | `refactor-remove-dead-frontend-code.md` (gates CONDITIONAL items there) |

---

## §1 Feature Description

### Overview
Investigate seven backend HTTP endpoints that have **zero callers from the live frontend** but are **still registered in `backend/app/main.py`** and therefore present on the public OpenAPI surface. Decide for each: REMOVE, KEEP, or KEEP-AND-DOCUMENT.

### Problem Statement
A staff-engineer audit (verified by Codex) flagged these endpoints as having no frontend caller:

1. `POST /intent/` (legacy) — `backend/app/routers/intent.py`
2. `POST /intent/confirm` (legacy) — `backend/app/routers/intent.py`
3. `GET /build/{id}/report` — `backend/app/routers/reports.py`
4. `GET /builds/compare/report` — `backend/app/routers/reports.py`
5. `POST /profile/lookup` — `backend/app/routers/profile.py`
6. `POST /build/{id}/rescore` — `backend/app/routers/gauntlet.py`
7. `POST /build/{id}/gauntlet` — `backend/app/routers/gauntlet.py`

Per **CLAUDE.md "no path is out of scope" rule**, registered API endpoints are public surface. They could be consumed by:
- The archived CLI (`archive/spikes/cli/`)
- One-off scripts under `scripts/`
- External demo flows pointed at by the Kaggle submission, the README, or the marketing landing
- Beta testers probing the API directly
- MCP-server or Gemma function-calling integrations that bypass the frontend
- Future planned features documented in `docs/specs/` or the vision roadmap

A "delete because the React app doesn't call it" decision is wrong if any of the above is true. This spike collects the evidence to make the call rigorously.

### Success Criteria
- [ ] §6 "Per-Endpoint Findings" is filled in for all 7 endpoints with caller search results across:
  - frontend (`frontend/src/`)
  - archived CLI (`archive/spikes/cli/`)
  - scripts (`scripts/`)
  - docs (`docs/`, `README.md`, vision roadmap, Kaggle materials)
  - git history (last 90 days)
- [ ] §7 "Final Recommendation" gives a one-word verdict (REMOVE / KEEP / KEEP-AND-DOCUMENT) per endpoint with justification
- [ ] No code is changed by this spec
- [ ] Status set to AWAITING HUMAN REVIEW when investigation is complete

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Analysis-only spec, no code changes | Removing public API surface without explicit human approval violates the "no path is out of scope" rule. Different risk profile than pure-dead-code deletion. | Bundle into `refactor-remove-dead-frontend-code.md` — rejected, conflates risk classes. |
| 2 | Investigate all 7 endpoints in one spec | They share the same risk profile (registered-but-uncalled-by-frontend). One investigation, one decision pass. | Seven separate specs — rejected, ceremony overhead. |
| 3 | Search the archived CLI for callers | Per CLAUDE.md, the CLI is archived but `archive/spikes/cli/cli.py` still imports backend services. It may also call HTTP endpoints. | Treat archived = dead — rejected, would miss the case where the CLI is the only consumer. |
| 4 | Search `docs/`, README, Kaggle materials for documented promises | Removing an endpoint a judge or external user has been told about is a footgun. | Trust the import graph alone — rejected. |
| 5 | Output classification: REMOVE / KEEP / KEEP-AND-DOCUMENT (no fourth option) | Forces a clean decision. KEEP-AND-DOCUMENT covers the case where the endpoint is real public API but the docs lie. | Add MAYBE / DEFER — rejected, defers the decision. |

### Constraints
- This spec **must not modify any code under `backend/app/routers/`, `backend/app/services/`, or `backend/app/models/`**.
- It may modify only this spec file (filling in §6 and §7) and `docs/sessions/` (logging).
- Investigation must use the working tree at execution time, not the audit snapshot. Codebases drift.

---

## §3 UI/UX Design

**SKIPPED** — backend analysis only.

---

## §4 Technical Specification

### Endpoints Under Review

| # | Method | Path | Router File | Status from Audit | Why Suspected Dead |
|---|--------|------|-------------|-------------------|--------------------|
| 1 | POST | `/intent/` | `backend/app/routers/intent.py` | No frontend caller | Replaced by `/intent/stream` + `/intent/chip` + `/intent/commit` in `routers/set_your_course.py` |
| 2 | POST | `/intent/confirm` | `backend/app/routers/intent.py` | No frontend caller | Same — superseded by the `set_your_course` family |
| 3 | GET | `/build/{id}/report` | `backend/app/routers/reports.py` | No frontend caller | No `getBuildReport`-shaped function in `frontend/src/api/` |
| 4 | GET | `/builds/compare/report` | `backend/app/routers/reports.py` | No frontend caller | Frontend has `compareBuilds` (`POST /builds/compare`) but no caller for the markdown-report variant |
| 5 | POST | `/profile/lookup` | `backend/app/routers/profile.py` | No frontend caller | Frontend uses `POST /profile` and `POST /profile/reroll` only |
| 6 | POST | `/build/{id}/rescore` | `backend/app/routers/gauntlet.py` | No frontend caller | Frontend `rescoreBuild` export exists but is itself dead (zero callers) |
| 7 | POST | `/build/{id}/gauntlet` | `backend/app/routers/gauntlet.py` | No frontend caller | The build orchestration runs the gauntlet inline; the standalone endpoint is unused |

### Investigation Procedure (per endpoint)

For each endpoint, run these checks and record results in §6:

1. **Frontend callers** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" frontend/`
2. **Archived CLI callers** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" archive/`
3. **Scripts callers** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" scripts/`
4. **Documentation references** — `rg -nS "<endpoint-path>" docs/ README.md` plus a search of `docs/futureproof_vision_roadmap.md` and `docs/futureproof_hackathon_prd.md`
5. **OpenAPI surface** — confirm registration in `backend/app/main.py`; if a generated `openapi.json` is committed, confirm presence
6. **Git history** — `git log --all --oneline --since="90 days ago" -- <router-file>` to spot recent activity
7. **Tests** — `rg -nS "<endpoint-path-fragment>|<route-handler-name>" backend/tests/` to know what test cleanup follows
8. **External integrations** — check `src/mcp_server/` and any Gemma function-calling configs for indirect callers

### File Changes
**None.** This spec writes only to itself.

### Data Model Changes
None.

### Service Changes
None.

### Testing Impact Analysis
**N/A** — analysis only. Any tests touched by the eventual deletion will be tracked in the spec that does the deletion.

---

## §5 Architecture Review

**Status:** SKIPPED (analysis spike, no architectural change)

---

## §6 Per-Endpoint Findings

**Status:** PENDING

### Endpoint 1: `POST /intent/`
- **Router:** `backend/app/routers/intent.py`
- **Frontend callers:** [TBD]
- **Archived CLI callers:** [TBD]
- **Scripts callers:** [TBD]
- **Documentation references:** [TBD]
- **OpenAPI surface:** [TBD]
- **Git history (last 90d):** [TBD]
- **Tests:** [TBD]
- **External integrations:** [TBD]
- **Notes:** [TBD]
- **Recommendation:** [TBD]

### Endpoint 2: `POST /intent/confirm`
- **Router:** `backend/app/routers/intent.py`
- **Frontend callers:** [TBD]
- **Archived CLI callers:** [TBD]
- **Scripts callers:** [TBD]
- **Documentation references:** [TBD]
- **OpenAPI surface:** [TBD]
- **Git history (last 90d):** [TBD]
- **Tests:** [TBD]
- **External integrations:** [TBD]
- **Notes:** [TBD]
- **Recommendation:** [TBD]

### Endpoint 3: `GET /build/{id}/report`
- **Router:** `backend/app/routers/reports.py`
- **Frontend callers:** [TBD]
- **Archived CLI callers:** [TBD]
- **Scripts callers:** [TBD]
- **Documentation references:** [TBD]
- **OpenAPI surface:** [TBD]
- **Git history (last 90d):** [TBD]
- **Tests:** [TBD]
- **External integrations:** [TBD]
- **Notes:** [TBD]
- **Recommendation:** [TBD]

### Endpoint 4: `GET /builds/compare/report`
- **Router:** `backend/app/routers/reports.py`
- **Frontend callers:** [TBD]
- **Archived CLI callers:** [TBD]
- **Scripts callers:** [TBD]
- **Documentation references:** [TBD]
- **OpenAPI surface:** [TBD]
- **Git history (last 90d):** [TBD]
- **Tests:** [TBD]
- **External integrations:** [TBD]
- **Notes:** [TBD]
- **Recommendation:** [TBD]

### Endpoint 5: `POST /profile/lookup`
- **Router:** `backend/app/routers/profile.py`
- **Frontend callers:** [TBD]
- **Archived CLI callers:** [TBD]
- **Scripts callers:** [TBD]
- **Documentation references:** [TBD]
- **OpenAPI surface:** [TBD]
- **Git history (last 90d):** [TBD]
- **Tests:** [TBD]
- **External integrations:** [TBD]
- **Notes:** [TBD]
- **Recommendation:** [TBD]

### Endpoint 6: `POST /build/{id}/rescore`
- **Router:** `backend/app/routers/gauntlet.py`
- **Frontend callers:** [TBD]
- **Archived CLI callers:** [TBD]
- **Scripts callers:** [TBD]
- **Documentation references:** [TBD]
- **OpenAPI surface:** [TBD]
- **Git history (last 90d):** [TBD]
- **Tests:** [TBD]
- **External integrations:** [TBD]
- **Notes:** [TBD]
- **Recommendation:** [TBD]

### Endpoint 7: `POST /build/{id}/gauntlet`
- **Router:** `backend/app/routers/gauntlet.py`
- **Frontend callers:** [TBD]
- **Archived CLI callers:** [TBD]
- **Scripts callers:** [TBD]
- **Documentation references:** [TBD]
- **OpenAPI surface:** [TBD]
- **Git history (last 90d):** [TBD]
- **Tests:** [TBD]
- **External integrations:** [TBD]
- **Notes:** [TBD]
- **Recommendation:** [TBD]

---

## §7 Final Recommendation

**Status:** PENDING

### Summary Table

| # | Endpoint | Verdict | One-Line Justification |
|---|----------|---------|------------------------|
| 1 | `POST /intent/` | [REMOVE / KEEP / KEEP-AND-DOCUMENT] | |
| 2 | `POST /intent/confirm` | [REMOVE / KEEP / KEEP-AND-DOCUMENT] | |
| 3 | `GET /build/{id}/report` | [REMOVE / KEEP / KEEP-AND-DOCUMENT] | |
| 4 | `GET /builds/compare/report` | [REMOVE / KEEP / KEEP-AND-DOCUMENT] | |
| 5 | `POST /profile/lookup` | [REMOVE / KEEP / KEEP-AND-DOCUMENT] | |
| 6 | `POST /build/{id}/rescore` | [REMOVE / KEEP / KEEP-AND-DOCUMENT] | |
| 7 | `POST /build/{id}/gauntlet` | [REMOVE / KEEP / KEEP-AND-DOCUMENT] | |

### Second-Order Effects

For any REMOVE verdict, list the downstream cleanup it enables (e.g., "Removing `/intent/` unblocks deletion of `services/intent.resolve_intent`, `models/api.IntentRequest`, and `tests/services/test_intent.py` per `refactor-remove-dead-frontend-code.md` CONDITIONAL items").

For any KEEP verdict, list any documentation, test, or instrumentation gap to file a follow-up for.

---

## §8 Reviews

### Code Review
**Status:** SKIPPED (no code changes)

### Human Review
**Status:** AWAITING HUMAN REVIEW (Jeff)

Jeff makes the final call on each endpoint's verdict. The investigation produces evidence; Jeff produces the decision. After approval, the REMOVE verdicts feed into the deletion spec.

---

## §9 Verification

**Status:** SKIPPED (no code changes — nothing to build)

---

## §10 Discussion

```
[2026-04-26] Spec author → reader
This spec assumes the audit's caller analysis was right about the frontend (Codex re-verified).
The investigation re-runs the search from scratch on every surface (frontend, CLI, scripts, docs,
git, MCP) to catch anything the audit missed.

If, during investigation, you find an endpoint has callers we didn't know about — DO NOT DELETE.
Document the finding in §6 and recommend KEEP. The audit was wrong about that one.
```

---

## §11 Final Notes

**Human Review:** PENDING

This spec is intentionally the "slow path." The fast path (`refactor-remove-dead-frontend-code.md`) handles
~95% of the cleanup in one pass with low risk. This spike handles the remaining ~5% — public API surface —
with deliberate caution because the cost of removing an endpoint a judge or beta tester depends on is high.
