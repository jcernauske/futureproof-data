## Temporal Assessment: crosswalk-cip-soc
**Date:** 2026-04-08
**Agent:** @temporal-modeler
**Spec:** docs/specs/crosswalk-cip-soc.md
**Decision:** SKIP CONFIRMED -- no temporal modeling required

### Assessment

The CIP-SOC crosswalk is a static reference mapping published jointly by NCES and BLS. It maps CIP 2020 program codes to SOC 2018 occupation codes. This dataset has no temporal dimension requiring bitemporal modeling.

### Why No Valid Time Is Needed

1. **No effective dates.** The crosswalk does not carry valid_from/valid_to columns. A CIP-SOC pairing is either present in the crosswalk or it is not. There is no concept of a mapping being "valid during" a particular period.

2. **No versioning within a release.** Each crosswalk release (CIP 2020 x SOC 2018) is a single, complete mapping. There are no amendments, corrections, or mid-cycle updates. The file is published once and remains unchanged until the next taxonomy revision.

3. **Taxonomy revision cycle is approximately 10 years.** CIP was last revised in 2020 (prior: 2010). SOC was last revised in 2018 (prior: 2010). The next crosswalk version will correspond to a future CIP/SOC revision, which would be an entirely new dataset, not an amendment to the current one.

4. **No SCD patterns apply.** The crosswalk is not a dimension table that changes over time. It is a reference table that is replaced wholesale when taxonomies are updated. SCD Type 1 (overwrite) or Type 2 (history tracking) patterns are not applicable for the current MVP scope.

### Why No Transaction Time Strategy Is Needed

1. **Single load, no corrections.** The crosswalk is ingested once from an authoritative government source. There is no expectation of corrections, restatements, or amendments.

2. **Iceberg snapshot sufficiency.** The standard Iceberg snapshot created at ingest time is sufficient. No special snapshot strategy is needed because there will be no correction events that require point-in-time recovery.

3. **No "what did we know on date X?" queries.** The crosswalk mappings are static facts from an authoritative taxonomy. There is no business need to ask how the mappings have changed over time within a single release.

### Future Consideration

If futureproof-data eventually ingests multiple crosswalk versions (e.g., a future CIP 2030 x SOC 2028 crosswalk), temporal modeling would become relevant. At that point, a `taxonomy_version` or `crosswalk_edition` column would be more appropriate than bitemporal valid_from/valid_to columns, since entire crosswalk releases are replaced atomically rather than individual rows changing over time. This is noted for future specs and is out of scope for the current implementation.

### Conclusion

The spec's recommendation to SKIP the @temporal-modeler step is correct. The CIP-SOC crosswalk is a static, authoritative reference table with no temporal dimension, no amendment/correction lifecycle, and no need for point-in-time query support.
