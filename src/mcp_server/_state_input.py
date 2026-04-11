"""State input normalization for MCP tools.

MCP tools accept US state identifiers from LLM-facing callers in any of
three forms:

    * 2-digit FIPS code (e.g. ``"06"``)
    * 2-letter USPS abbreviation (e.g. ``"CA"``, case insensitive)
    * Full state name (e.g. ``"California"``, case insensitive, including
      District of Columbia)

``normalize_state_input(raw)`` is the single chokepoint that accepts any
of those forms and returns the canonical 2-digit FIPS code, or ``None``
when the input cannot be recognized.  It is a pure function and never
raises on well-formed string input.

This module imports its 51-entry canonical dicts from
``silver._us_state_reference`` — the Silver module remains the single
source of truth for the 50-state + DC closed set, and this module only
adds MCP-specific reverse lookups.  A ``_self_check()`` runs at import
time to verify that:

    * ``USPS_TO_FIPS`` is the exact inverse of ``FIPS_TO_USPS``
    * ``STATE_NAME_TO_FIPS`` has 51 lowercase keys, all mapping to
      valid FIPS codes in ``FIPS_TO_USPS``
    * Every FIPS code in ``FIPS_TO_USPS`` has a corresponding entry in
      both reverse lookups (bidirectional completeness)
"""

from __future__ import annotations

from silver._us_state_reference import FIPS_TO_USPS

# ---------------------------------------------------------------------------
# FIPS -> canonical state name (51 entries, matches Gold state_name column)
# ---------------------------------------------------------------------------

FIPS_TO_STATE_NAME: dict[str, str] = {
    "01": "Alabama",
    "02": "Alaska",
    "04": "Arizona",
    "05": "Arkansas",
    "06": "California",
    "08": "Colorado",
    "09": "Connecticut",
    "10": "Delaware",
    "11": "District of Columbia",
    "12": "Florida",
    "13": "Georgia",
    "15": "Hawaii",
    "16": "Idaho",
    "17": "Illinois",
    "18": "Indiana",
    "19": "Iowa",
    "20": "Kansas",
    "21": "Kentucky",
    "22": "Louisiana",
    "23": "Maine",
    "24": "Maryland",
    "25": "Massachusetts",
    "26": "Michigan",
    "27": "Minnesota",
    "28": "Mississippi",
    "29": "Missouri",
    "30": "Montana",
    "31": "Nebraska",
    "32": "Nevada",
    "33": "New Hampshire",
    "34": "New Jersey",
    "35": "New Mexico",
    "36": "New York",
    "37": "North Carolina",
    "38": "North Dakota",
    "39": "Ohio",
    "40": "Oklahoma",
    "41": "Oregon",
    "42": "Pennsylvania",
    "44": "Rhode Island",
    "45": "South Carolina",
    "46": "South Dakota",
    "47": "Tennessee",
    "48": "Texas",
    "49": "Utah",
    "50": "Vermont",
    "51": "Virginia",
    "53": "Washington",
    "54": "West Virginia",
    "55": "Wisconsin",
    "56": "Wyoming",
}


# ---------------------------------------------------------------------------
# Reverse lookups (derived — built once at module load)
# ---------------------------------------------------------------------------

USPS_TO_FIPS: dict[str, str] = {usps: fips for fips, usps in FIPS_TO_USPS.items()}
"""Inverse of ``FIPS_TO_USPS``.  51 entries, upper-case USPS keys."""

STATE_NAME_TO_FIPS: dict[str, str] = {
    name.lower(): fips for fips, name in FIPS_TO_STATE_NAME.items()
}
"""Case-insensitive full-name -> FIPS lookup.  51 entries, lowercase keys."""


# ---------------------------------------------------------------------------
# Normalizer (pure function)
# ---------------------------------------------------------------------------


def normalize_state_input(raw: object) -> str | None:
    """Normalize any accepted state identifier to a 2-digit FIPS code.

    Accepts:
        * 2-digit FIPS code — any of the 51 valid codes in ``FIPS_TO_USPS``
        * 2-letter USPS abbreviation (case insensitive)
        * Full state name (case insensitive, incl. "District of Columbia")

    Whitespace is stripped from string input.  Non-string and empty
    input returns ``None``.  The function never raises.

    Args:
        raw: A user-supplied state identifier.  Typically a ``str`` but
             any type is accepted (non-strings return ``None``).

    Returns:
        2-digit FIPS string if the input is recognized; otherwise ``None``.
    """
    if not isinstance(raw, str):
        return None

    stripped = raw.strip()
    if not stripped:
        return None

    # Case 1: already a FIPS code (2 digits, in the valid set)
    if stripped in FIPS_TO_USPS:
        return stripped

    upper = stripped.upper()

    # Case 2: 2-letter USPS abbreviation (case insensitive)
    if len(upper) == 2 and upper in USPS_TO_FIPS:
        return USPS_TO_FIPS[upper]

    # Case 3: full state name (case insensitive)
    lower = stripped.lower()
    if lower in STATE_NAME_TO_FIPS:
        return STATE_NAME_TO_FIPS[lower]

    return None


# ---------------------------------------------------------------------------
# Self-check (runs at import time)
# ---------------------------------------------------------------------------


def _self_check() -> None:
    """Structural consistency check for the reverse lookups.

    Verifies at import time that:
        1. ``USPS_TO_FIPS`` has exactly 51 entries
        2. ``USPS_TO_FIPS`` is the exact inverse of ``FIPS_TO_USPS``
           (bidirectional consistency)
        3. ``FIPS_TO_STATE_NAME`` has exactly 51 entries and its key set
           matches ``FIPS_TO_USPS``
        4. ``STATE_NAME_TO_FIPS`` has exactly 51 entries and every value
           is a valid FIPS code in ``FIPS_TO_USPS``
        5. All keys in ``STATE_NAME_TO_FIPS`` are lowercase
    """
    if len(USPS_TO_FIPS) != 51:
        raise AssertionError(
            f"USPS_TO_FIPS must have exactly 51 entries, got {len(USPS_TO_FIPS)}"
        )

    # Bidirectional consistency with FIPS_TO_USPS
    for fips, usps in FIPS_TO_USPS.items():
        if USPS_TO_FIPS.get(usps) != fips:
            raise AssertionError(
                f"USPS_TO_FIPS inconsistency for {usps!r}: "
                f"expected {fips!r}, got {USPS_TO_FIPS.get(usps)!r}"
            )
    for usps, fips in USPS_TO_FIPS.items():
        if FIPS_TO_USPS.get(fips) != usps:
            raise AssertionError(
                f"FIPS_TO_USPS inconsistency for {fips!r}: "
                f"expected {usps!r}, got {FIPS_TO_USPS.get(fips)!r}"
            )

    if len(FIPS_TO_STATE_NAME) != 51:
        raise AssertionError(
            f"FIPS_TO_STATE_NAME must have exactly 51 entries, "
            f"got {len(FIPS_TO_STATE_NAME)}"
        )
    if set(FIPS_TO_STATE_NAME.keys()) != set(FIPS_TO_USPS.keys()):
        raise AssertionError(
            "FIPS_TO_STATE_NAME key set does not match FIPS_TO_USPS"
        )

    if len(STATE_NAME_TO_FIPS) != 51:
        raise AssertionError(
            f"STATE_NAME_TO_FIPS must have exactly 51 entries, "
            f"got {len(STATE_NAME_TO_FIPS)}"
        )
    for name, fips in STATE_NAME_TO_FIPS.items():
        if name != name.lower():
            raise AssertionError(
                f"STATE_NAME_TO_FIPS key {name!r} must be lowercase"
            )
        if fips not in FIPS_TO_USPS:
            raise AssertionError(
                f"STATE_NAME_TO_FIPS maps {name!r} to invalid FIPS {fips!r}"
            )


_self_check()
