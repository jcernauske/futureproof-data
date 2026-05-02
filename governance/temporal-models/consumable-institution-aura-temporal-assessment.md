# Temporal Assessment: consumable.institution_aura

**Date:** 2026-04-30
**Agent:** @temporal-modeler
**Status:** NOT APPLICABLE

## Determination

Single-vintage product (FY23 IPEDS / 2022 EADA reporting year). Spec OUT OF SCOPE explicitly forbids multi-year SCD2 history, amendments, or point-in-time queries.

No bitemporal schema, no valid_from/valid_to columns, no Iceberg snapshot strategy beyond default replace-on-rebuild. Vintage tracked as a single static `reporting_year` literal.

Revisit if/when a multi-vintage spec supersedes scope.
