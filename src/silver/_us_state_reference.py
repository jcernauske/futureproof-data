"""Structural U.S. state reference lookups for the Silver zone.

This module contains three static constants that are structural properties
of U.S. geography (FIPS code space + USPS abbreviations + Census regions)
and the current BEA RPP verification state:

    FIPS_TO_USPS            51-entry dict: state FIPS -> USPS abbreviation
    FIPS_TO_CENSUS_REGION   51-entry dict: state FIPS -> Census region
    BEA_VERIFIED_FIPS       8-entry frozenset of BEA-verified state FIPS codes

These are NOT business-managed entity data — they are a closed set of 50
U.S. states plus the District of Columbia, with mappings that do not drift.
Per the Brightsmith framework rule, such structural reference data is
allowed to live in code.  The ``_self_check()`` function that runs at
import time is the structural proof: it asserts both dicts have exactly
51 keys, share the same key set, and agree with the ``VALID_STATE_FIPS``
constant exported by the Bronze BEA RPP ingestor (cross-validation per
pre-review Advisory #5).  Any drift between the Silver lookups and the
Bronze ingestor will fail at import time, not silently at runtime.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# FIPS -> USPS two-letter abbreviation (51 entries: 50 states + DC)
# ---------------------------------------------------------------------------

FIPS_TO_USPS: dict[str, str] = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}


# ---------------------------------------------------------------------------
# FIPS -> U.S. Census Bureau region (51 entries: 50 states + DC)
#
# Canonical four-region assignment.  DC is placed in ``South`` per Census
# convention (documented quirk, not a bug).
# ---------------------------------------------------------------------------

FIPS_TO_CENSUS_REGION: dict[str, str] = {
    # Northeast (9)
    "09": "Northeast", "23": "Northeast", "25": "Northeast", "33": "Northeast",
    "44": "Northeast", "50": "Northeast", "34": "Northeast", "36": "Northeast",
    "42": "Northeast",
    # Midwest (12)
    "17": "Midwest", "18": "Midwest", "26": "Midwest", "39": "Midwest",
    "55": "Midwest", "19": "Midwest", "20": "Midwest", "27": "Midwest",
    "29": "Midwest", "31": "Midwest", "38": "Midwest", "46": "Midwest",
    # South (17) -- includes DC per Census convention
    "10": "South", "11": "South", "12": "South", "13": "South", "24": "South",
    "37": "South", "45": "South", "51": "South", "54": "South",
    "01": "South", "21": "South", "28": "South", "47": "South",
    "05": "South", "22": "South", "40": "South", "48": "South",
    # West (13)
    "04": "West", "08": "West", "16": "West", "30": "West", "32": "West",
    "35": "West", "49": "West", "56": "West", "02": "West", "06": "West",
    "15": "West", "41": "West", "53": "West",
}


# ---------------------------------------------------------------------------
# BEA-verified state FIPS codes (8 entries)
#
# The subset of state_fips codes whose BEA RPP values were sourced from a
# BEA publication.  Closes Bronze HIGH-3 / staff-review Condition 6.
# When the live BEA API refresh lands, this set expands to all 51 codes.
# ---------------------------------------------------------------------------

BEA_VERIFIED_FIPS: frozenset[str] = frozenset({
    "05",  # AR
    "06",  # CA
    "11",  # DC
    "15",  # HI
    "19",  # IA
    "28",  # MS
    "34",  # NJ
    "40",  # OK
})


# ---------------------------------------------------------------------------
# Self-check (runs at import time)
# ---------------------------------------------------------------------------


def _self_check() -> None:
    """Structural cross-validation of the lookup constants.

    Asserts:
      1. Both dicts have exactly 51 entries
      2. Both dicts share the same key set
      3. The key set matches ``VALID_STATE_FIPS`` exported by the Bronze
         BEA RPP ingestor (pre-review Advisory #5)
      4. ``BEA_VERIFIED_FIPS`` is a subset of the FIPS dict keys

    Any drift between Silver lookups and the Bronze ingestor will fail
    the import, not silently at runtime.
    """
    if len(FIPS_TO_USPS) != 51:
        raise AssertionError(
            f"FIPS_TO_USPS must have exactly 51 entries, got {len(FIPS_TO_USPS)}"
        )
    if len(FIPS_TO_CENSUS_REGION) != 51:
        raise AssertionError(
            f"FIPS_TO_CENSUS_REGION must have exactly 51 entries, "
            f"got {len(FIPS_TO_CENSUS_REGION)}"
        )

    usps_keys = set(FIPS_TO_USPS.keys())
    region_keys = set(FIPS_TO_CENSUS_REGION.keys())
    if usps_keys != region_keys:
        missing_in_regions = usps_keys - region_keys
        missing_in_usps = region_keys - usps_keys
        raise AssertionError(
            "FIPS_TO_USPS and FIPS_TO_CENSUS_REGION key sets differ. "
            f"Missing in regions: {sorted(missing_in_regions)}. "
            f"Missing in USPS: {sorted(missing_in_usps)}."
        )

    # Cross-validate against the Bronze ingestor (pre-review Advisory #5).
    # Import is deferred to avoid circular imports at package load time.
    from raw.bea_rpp_ingestor import BeaRppIngestor

    bronze_keys = set(BeaRppIngestor.VALID_STATE_FIPS)
    if usps_keys != bronze_keys:
        only_silver = sorted(usps_keys - bronze_keys)
        only_bronze = sorted(bronze_keys - usps_keys)
        raise AssertionError(
            "Silver FIPS lookup keys do not match "
            "BeaRppIngestor.VALID_STATE_FIPS. "
            f"Only in Silver: {only_silver}. "
            f"Only in Bronze: {only_bronze}."
        )

    # All BEA-verified FIPS codes must be valid state FIPS codes.
    if not BEA_VERIFIED_FIPS.issubset(usps_keys):
        stray = sorted(BEA_VERIFIED_FIPS - usps_keys)
        raise AssertionError(
            f"BEA_VERIFIED_FIPS contains codes not in FIPS_TO_USPS: {stray}"
        )


_self_check()
