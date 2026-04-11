"""Cost tier classifier for consumable.regional_price_parities.

Frozen Gold-layer classification of BEA Regional Price Parity (RPP)
index values into 5 editorial buckets. Breakpoints and enum values are
governance-frozen by BT-106 and the physical model
(governance/models/gold-regional-price-parities-physical.md). Any
change is a breaking change per BT-106 and requires a new spec.

Semantics: left-closed intervals [lo, hi). The CASE is evaluated
top-down so the highest matching bucket wins.

Buckets:
    very_high  rpp_all_items >= 108.0
    high       103.0 <= rpp_all_items < 108.0
    average    97.0  <= rpp_all_items < 103.0
    low        91.0  <= rpp_all_items < 97.0
    very_low   rpp_all_items < 91.0
"""

from __future__ import annotations

from enum import Enum


class CostTier(str, Enum):
    """Five-bucket cost-of-living classification (BT-106).

    String-valued enum so each member is directly comparable to the
    persisted VARCHAR column without coercion.
    """

    VERY_HIGH = "very_high"
    HIGH = "high"
    AVERAGE = "average"
    LOW = "low"
    VERY_LOW = "very_low"


# Frozen breakpoint list in descending order. Do not edit without a new
# spec — changing these values is a BT-106 breaking change.
COST_TIER_BREAKPOINTS: tuple[tuple[float, CostTier], ...] = (
    (108.0, CostTier.VERY_HIGH),
    (103.0, CostTier.HIGH),
    (97.0, CostTier.AVERAGE),
    (91.0, CostTier.LOW),
)


def classify_cost_tier(rpp: float) -> str:
    """Classify an RPP index value into the 5-bucket cost_tier enum.

    Args:
        rpp: Regional Price Parity all-items index on the national=100
            scale. Must be non-null. The Gold transformer guards against
            nulls upstream.

    Returns:
        One of the 5 CostTier string values.
    """
    for threshold, tier in COST_TIER_BREAKPOINTS:
        if rpp >= threshold:
            return tier.value
    return CostTier.VERY_LOW.value
