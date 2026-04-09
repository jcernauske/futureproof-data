# PII Scanner Skip: gold-onet-profiles

**Agent:** @pii-scanner
**Date:** 2026-04-08
**Spec:** gold-onet-profiles
**Decision:** SKIP CONFIRMED

## Rationale

Both Gold tables contain exclusively occupation-level aggregate data from O*NET (U.S. Department of Labor). No personal identifiers present. No PII detected.

## Tables Scanned

- `consumable.onet_work_profiles` (798 rows)
- `consumable.onet_burnout_elements` (6,984 rows)

## Conclusion

No further PII review required. All data is public, aggregate, occupation-level statistical data with no individual-level records.
