# Bugfix Ship Report — Broad-CIP Substitution & Intent Prompt Bias

**Spec:** `docs/specs/completed/bugfix-broad-cip-substitution-and-intent.md`
**Shipped:** 2026-04-18
**Status:** COMPLETE
**Duration:** Single-session end-to-end (architecture review → copywriter → test-writer → code review → builder → environmental cleanup)

---

## What shipped

Two compounding bugs caused a student picking a specific major (e.g. "Marketing") at a broad-CIP school (Indiana University reports all Kelley grads under `52.01 Business/Commerce, General`) to see a hard error instead of marketing-specific careers. Both are now fixed.

### Bug A — Substitution lookup was granularity-fragile

`_build_substituted_rows` exact-matched against `career_outcomes.cipcode`, which is canonically 4-digit. When the intent service handed down `"52.0100"` (6-digit padded), the lookup missed IU's `"52.01"` row and raised, producing a 422 to the frontend. Now canonicalized at every filter and response site via a single `_canonical_cip4` helper applied at four table-filter sites and four response-payload sites inside `futureproof_server.py`.

### Bug B — Intent prompt biased Gemma toward school-reported CIPs

The system prompt framed school-reported CIPs as "these have earnings data" and crosswalk CIPs as "these have career path data," which Gemma read as a ranking signal. For broad-CIP schools, Gemma picked the school's broad CIP instead of the specific cousin from the crosswalk, killing the substitution flow before it ever started. Fixed two ways:

1. **Deterministic YAML short-circuit** in `resolve_intent`. When the student's input is an exact or alias match in `data/reference/major_to_cip.yaml`, return the YAML's `cip4` directly without calling Gemma. Covers every major the YAML knows about — including the Marketing-at-IU case this spec exists to fix — and collapses a hosted-LLM call down to a dict lookup.
2. **Prompt rewrite** by @fp-copywriter. Both CIP lists now labeled "Candidate CIPs" with symmetric framing. Prompt explicitly tells Gemma the backend handles earnings blending automatically. Removed the high-tier school-catalog tiebreaker that reinforced the same bias. Applied to both `backend/app/services/intent.py` and the duplicate in `backend/cli.py` (3303 chars, byte-for-byte identical).

## Files changed

| File | Change |
|------|--------|
| `backend/app/services/major_lookup.py` | NEW. `lookup_major(text) -> MajorEntry \| None` — case-insensitive major + alias match, `@lru_cache`'d YAML loader with cwd-independent path discovery (walks up from `__file__`). |
| `backend/app/services/intent.py` | Added `_derive_parent_cip` helper and the deterministic YAML short-circuit at the top of `resolve_intent`. Short-circuit runs `_promote_to_leaf_cip` using `_get_school_cips(unitid)` for parity with the Gemma path. Prompt body rewritten. Added explicit docstring on post-condition asymmetry (short-circuit can return 4-digit when YAML stores a family and the school has no descendant leaf). |
| `backend/cli.py` | Prompt body rewritten (mirror of `intent.py`). |
| `src/mcp_server/futureproof_server.py` | Added `_canonical_cip4` static helper. Applied at four filter sites (`_build_substituted_rows`, `_fallback_gemma_soc_resolution`, standard-path `CAREER_PATHS_TABLE` filter, Gemma-SOC-fallback program-name lookup). Canonicalized `reported_cipcode` at four response sites. Reordered imports to module top to close E402. |
| `backend/tests/services/test_intent.py` | Appended `TestDeterministicShortCircuit` (8 tests) and `TestPromptCopy` (1 test). |
| `backend/tests/services/test_major_lookup.py` | NEW. `TestLookupMajor` + `TestCrossModuleConsistency` (parametrized across all 204 YAML entry/alias pairs — drift guard between `major_lookup` and `FutureProofMCPServer._find_major_intent`). |
| `tests/mcp/test_cip_substitution.py` | Added `TestCanonicalCip4`, two `TestIntegrationLikePath` cases (padded-broad substitutes / specific-six-digit does not), `TestStandardPath::test_padded_specific_cip_normalizes`. |
| `tests/mcp/test_cip_substitution_integration.py` | Added `TestIUBMarketing52_14_PaddedInput::test_substitution_fires_with_52_0100`. |
| 6 `src/gold/*.py` files | Added `# noqa: F841 (DuckDB auto-registers by local name)` comments on zero-copy Arrow locals. Environmental cleanup, not spec logic. |
| `tests/silver/test_onet_transformer.py` | Replaced string-literal membership checks with `BURNOUT_ELEMENT_IDS.isdisjoint(wrong_ids)` — fixes F841, same invariant. |
| `tests/mcp/test_get_career_paths.py` + `tests/mcp/test_get_school_programs.py` | Added `debt_p25`, `debt_p75` + five AI-composite / ROI-provenance keys to fixture rows. Closes the pre-existing TODO the test authors had left. |
| `frontend/src/screens/ProfileScreen.test.tsx` | Split name+emoji assertions to match the component's post-refactor split-element rendering. |
| `frontend/package.json` + `package-lock.json` | Bumped `vitest@^2.0.0` → `^3.0.0` so the bundled vite matches the root vite@6. Eliminates TS2769 in `npm run build`. |

## Key decisions & deviations

- **Short-circuit calls `_promote_to_leaf_cip`.** The spec's proposed block returned the YAML's `cip4` unpromoted, which regressed a pre-existing test (`test_resolve_intent_falls_back_to_school_catalog_descendant`) because several YAML entries — most notably "Special Education" → `13.10` — store a 4-digit family code. The Gemma path promotes those to a 6-digit leaf via the school's catalog; the short-circuit now does the same, preserving parity.
- **`_derive_parent_cip(cip4, programs: Sequence[Mapping[str, Any]])`** instead of `list[dict]`. Covariant type that accepts the caller's `list[dict]` without forcing a signature change to `resolve_intent`. Net-reduced backend mypy from 47 → 46.
- **Fifth filter site at `_fallback_broaden_cip` L1749 intentionally left alone.** Comparison against `f"{family}.0100"` against 4-digit-stored rows is known-dead — noted inline, deferred by design. Staff engineer verified.
- **Cache-write invariant on short-circuit.** The short-circuit deliberately does NOT write to `_intent_cache`. Writes are owned by `confirm_intent`. Executable via `test_short_circuit_does_not_write_cache`.

## Verification

| Suite | Result |
|-------|--------|
| Pipeline ruff | 0 errors (was 23 pre-existing — cleaned up as part of this spec per owner request) |
| Backend ruff | clean |
| Backend mypy | 46 errors (unchanged baseline; this spec net-reduced by 1) |
| Backend pytest | 606/606 |
| Pipeline pytest | 1676/1676 (was 1674 / 2 `debt_p25` fail — fixtures updated) |
| TypeScript (`tsc --noEmit`) | clean |
| Frontend vitest | 445 pass + 1 skip (was 443 / 2 ProfileScreen fail — tests updated) |
| `npm run build` | clean, 739 KB JS / 226 KB gzip (was TS2769 on vitest.config.ts — vitest bumped to 3) |

Every `tests/mcp/test_cip_substitution*.py` test in the "Confirmed Safe" classification from §4 Testing Impact Analysis passed without modification. The one authorized test-message update (`TestSchoolRowMissing::test_missing_school_row_returns_null`) used a substring match, so the canonicalized error-message change didn't require touching the test.

## Review trail

- **@fp-architect v1.0:** CHANGES REQUESTED (8 conditions — load-bearing frontend contract drift on `parent_cip`, unsatisfiable success criterion 2 on `52.0101`, canonicalization completeness, test_intent.py mislabeled Create→Modify, cwd-independent path resolution, cross-module consistency test, cache-write invariant made explicit).
- **@fp-architect v1.1:** APPROVED. All 8 conditions verified in spec text. Explicit trace of `_derive_parent_cip` against Marketing-at-IU, Marketing-at-school-reporting-52.14-directly, and same-family-different-family scenarios.
- **@fp-copywriter:** Prompt rewritten in both `intent.py` and the CLI mirror. 21/21 intent tests still green post-rewrite.
- **@test-writer:** Added 20 new tests across 4 files (backend + pipeline). All P0/P1/P2 cases from §4. 604/604 backend green post-add.
- **@faang-staff-engineer:** APPROVED with four nits — all addressed (post-condition docstring asymmetry, non-dict `Mapping` guard, `logger.warning` on missing YAML, docstring note on two-layer `lru_cache` for test authors).
- **@fp-builder:** Initial run surfaced one spec-owned fix (test_major_lookup.py ruff I001 — builder mislabeled it as pre-existing). Fixed. Subsequent environmental cleanup closed three pre-existing suites so the §1 "Full build green" criterion terminates truthfully.

## Follow-ups (explicitly out of scope)

- **Short-circuit audit still pays a Gemma round-trip.** Staff engineer finding 1 — the audit step runs for YAML hits, so a degraded-Gemma scenario drags the "deterministic" path down to Gemma's latency floor. `gemma_client.generate` has no timeout. Worth a separate spec: either add a client-level timeout or make the audit fire-and-forget for short-circuit hits (YAML is high-confidence by construction).
- **Short-lived cache for short-circuit hits.** Staff engineer finding 2 — repeat POSTs for the same `(normalized_major, unitid)` pre-confirm re-run everything. A 60s TTL cache alongside `_intent_cache` (keeping confirm-cache invariant pristine) would close it.
- **`_fallback_broaden_cip` L1749 dead-branch cleanup.** Called out as known-dead in §4, staff engineer finding 4 confirmed.
- **`original_cipcode` vs `reported_cipcode` dual semantics.** Staff engineer finding 5 observed: caveats carry `original_cipcode` separately — different semantic ("what the user asked for") from `reported_cipcode` ("what we looked up"). Whether the frontend should consume either is a UX decision tracked separately.

## Human review

Spec file archived to `docs/specs/completed/bugfix-broad-cip-substitution-and-intent.md` — the full 1000+ line audit trail (architecture review v1.0 + v1.1 findings, code review findings, builder logs, copywriter diff, all test-writer decisions) lives there.
