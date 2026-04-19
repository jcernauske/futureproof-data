# CIP Routing Inconsistency in Ask-Gemma Path

Date: 2026-04-19
Author: Codex review

## Executive Summary

The frontend recently fixed the `parentCip` routing regression for the main
career-pick flow: `/build/outcomes`, `/build/tier`, `/career-pick/chips`, and
the final `/build` request now use `major.parentCip || major.cipCode` when the
school reports a broad CIP and intent resolution matched a more specific leaf.

That fix is incomplete.

The actual Ask-Gemma submission path still sends `major.cipCode` instead of the
same lookup CIP. As a result, the visible career cards and preloaded chip row
can be derived from one CIP context, while the follow-up Gemma answer is
generated from another. In broad-CIP substitution cases such as
IU/Kelley/Marketing, this can produce answers that are internally inconsistent
with the screen the student is looking at.

For a live demo, this is higher risk than a normal code review issue because it
can make the product look non-deterministic: the app appears to "change its
mind" between the screen state and the explanation layer.

## What the Intended Contract Is

The new routing rule is documented directly in the frontend type and screen
comments:

- `MajorSelection.parentCip` exists to carry the school's reported broad CIP
  when substitution applies.
- Every backend call that looks up school/program context is supposed to send
  `parentCip || cipCode`.

Evidence:

- [frontend/src/types/buildInput.ts](/Users/jcernauske/code/bright/futureproof-data/frontend/src/types/buildInput.ts:16)
- [frontend/src/screens/CareerPickScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx:56)
- [frontend/src/screens/RevealScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/RevealScreen.tsx:71)

The motivating example is explicit in the code comments:

- school reports broad `52.01`
- intent resolution matched leaf `52.14`
- backend substitution path keys on the broad school-reported CIP

That means the UI and all explanation layers need to agree on the same lookup
identifier.

## Where the Main Flow Is Correct

The current screen does the right thing for the core picker flow:

1. Career outcomes use `lookupCip = currentMajor.parentCip || currentMajor.cipCode`.
   - [CareerPickScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx:62)
2. Tiering uses the same `lookupCip`.
   - [CareerPickScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx:77)
3. Chip prefetch for `GET /career-pick/chips` also uses `major.parentCip || major.cipCode`.
   - [CareerPickScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx:117)
4. Final build creation in the reveal flow also uses `major.parentCip || major.cipCode`.
   - [RevealScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/RevealScreen.tsx:76)

There is already a targeted regression test covering the first three calls:

- [frontend/src/screens/CareerPickScreen.test.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.test.tsx:137)

That test verifies:

- `/build/outcomes` gets `52.01`
- `/build/tier` gets `52.01`
- `/career-pick/chips` gets `52.01`

This is good coverage, but it stops one step too early.

## Where the Ask-Gemma Flow Breaks the Contract

The inconsistency happens when `CareerPickScreen` mounts the lineage sheet.

### Step 1: Screen passes the wrong CIP into Ask context

`CareerPickScreen` builds `askContext` like this:

- [frontend/src/screens/CareerPickScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx:318)

Current code:

```ts
askContext={{
  cipcode: major.cipCode,
  majorText: major.rawText,
  socCodes,
}}
```

This bypasses the new routing rule and hardcodes the matched leaf, even when the
rest of the screen is using `parentCip`.

### Step 2: Lineage sheet forwards that CIP verbatim

`CareerLineageSheet` does not correct the value. It forwards whatever it was
given:

- [frontend/src/components/CareerLineageSheet.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/CareerLineageSheet.tsx:351)

```ts
askCareerPickChip({
  chipId: chip.id,
  cipcode: askContext.cipcode,
  majorText: askContext.majorText,
  socCodes: askContext.socCodes,
  selectedSoc: soc,
  terminalTitle: chip.terminal_title,
})
```

### Step 3: API client sends the stale CIP to the backend

- [frontend/src/api/careerPick.ts](/Users/jcernauske/code/bright/futureproof-data/frontend/src/api/careerPick.ts:43)

```ts
return apiPost("/career-pick/ask", {
  chip_id: args.chipId,
  cipcode: args.cipcode,
  ...
})
```

### Step 4: Backend bakes that CIP into the prompt and logs

The backend does not reinterpret the CIP; it uses the request field directly in
prompt construction and audit logging:

- [backend/app/services/career_pick_qna.py](/Users/jcernauske/code/bright/futureproof-data/backend/app/services/career_pick_qna.py:379)
- [backend/app/services/career_pick_qna.py](/Users/jcernauske/code/bright/futureproof-data/backend/app/services/career_pick_qna.py:410)

So the Ask-Gemma answer is generated against the stale leaf CIP, not the same
lookup context used to assemble the visible screen.

## Why This Matters

This is not just a cosmetic mismatch.

In substitution scenarios, the product depends on the broad school-reported CIP
to land on the correct row set before downstream logic narrows or substitutes.
When Ask-Gemma uses the leaf instead:

1. The student may see one set of careers on screen and receive an answer whose
   framing comes from a different major/program context.
2. The elevated chip logic and visible chip row may appear coherent, but the
   answer can drift because the actual `POST /career-pick/ask` request is not
   using the same CIP.
3. Logging and audit trails for the Ask-Gemma call become misleading, because
   they record a CIP that did not produce the current screen state.

For a hackathon demo, this is exactly the kind of bug that makes judges lose
trust quickly: the app looks polished, then one follow-up question exposes that
the explanation layer is not actually grounded in the same state as the UI.

## Concrete Failure Mode

Representative case from the recent regression notes:

- student types `marketing`
- intent match resolves to leaf `52.14`
- school reports broad `52.01`
- `parentCip` is set to `52.01`

Observed intended behavior:

- outcomes/tiering/chips/build all use `52.01`
- backend substitution branch returns the relevant marketing-aligned row set

Broken Ask-Gemma behavior:

- lineage sheet asks with `52.14`
- backend prompt now references a different CIP context than the one used to
  build the visible screen

Even if the answer is not obviously wrong every time, it is now dependent on a
different routing path. That is enough to create intermittent demo-only failures.

## Test Gap

There is good regression coverage for the screen-level routing, but no test that
asserts the Ask-Gemma submit path uses the same lookup CIP.

Existing tests:

- `CareerPickScreen` verifies the screen-level calls use `parentCip`.
  - [frontend/src/screens/CareerPickScreen.test.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.test.tsx:137)
- `CareerLineageSheet` verifies that a chip click forwards whatever `askContext`
  contains.
  - [frontend/src/components/CareerLineageSheet.test.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/components/CareerLineageSheet.test.tsx:715)

What is missing is the integration point between those tests:

- no test mounts `CareerPickScreen` in a substitution case
- opens the lineage sheet
- clicks a chip
- asserts `askCareerPickChip` receives `parentCip`, not `cipCode`

Because that end-to-end assertion is missing, the code regressed while still
leaving the visible regression tests green.

## Root Cause

The recent fix was applied to the obvious data-fetching paths but not to the
sheet-local Ask-Gemma context object.

In other words:

- the screen-level fetch code was updated
- the sheet input contract was left behind

This is a classic state-duplication bug. The lookup CIP is computed in one place
for some calls, but not elevated to a single shared value that all downstream
consumers must use.

## Recommended Fix

### Minimum fix

In `CareerPickScreen`, change the lineage sheet's `askContext.cipcode` from
`major.cipCode` to the same lookup CIP already used elsewhere:

```ts
const lookupCip = currentMajor.parentCip || currentMajor.cipCode;
```

and later:

```ts
askContext={{
  cipcode: major.parentCip || major.cipCode,
  majorText: major.rawText,
  socCodes,
}}
```

Relevant site:

- [frontend/src/screens/CareerPickScreen.tsx](/Users/jcernauske/code/bright/futureproof-data/frontend/src/screens/CareerPickScreen.tsx:318)

### Better fix

Avoid recomputing this rule ad hoc. Centralize it in one small helper so every
consumer uses the same contract:

```ts
function lookupCipForMajor(major: MajorSelection): string {
  return major.parentCip || major.cipCode;
}
```

Use that helper in:

- `/build/outcomes`
- `/build/tier`
- `/career-pick/chips`
- `CareerLineageSheet.askContext`
- `/build`

That reduces the chance of this exact class of regression returning.

## Recommended Tests

Add one integration-style frontend test at the `CareerPickScreen` level:

1. seed store with a substitution case (`cipCode="52.14"`, `parentCip="52.01"`)
2. mock outcomes, tiering, chips, and `askCareerPickChip`
3. render `CareerPickScreen`
4. open a career card / lineage sheet
5. click a chip
6. assert `askCareerPickChip` was called with `cipcode: "52.01"`

Also consider a narrower unit test that documents the shared routing rule, so
future edits cannot quietly split screen state from Ask-Gemma state.

## Severity

Severity: Medium-High

Reasoning:

- not a crash
- not universal
- but it creates user-visible inconsistency in the most judge-sensitive path:
  "ask a follow-up question about what I am seeing on this screen"

For production software this is a correctness bug. For a judged live demo it is
closer to a credibility bug, which is why it deserves priority.

## Bottom Line

The repo has already done most of the hard work to fix broad-CIP substitution.
The remaining bug is that Ask-Gemma still uses a stale CIP source.

Until the lineage sheet uses the same `parentCip || cipCode` rule as the rest of
the flow, the product can show one career context and explain another.
