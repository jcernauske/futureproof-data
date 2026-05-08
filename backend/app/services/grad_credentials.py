"""Graduate-credential feeder lookup service.

Provides:
- lookup_credential_for_soc — find the credential entry for a target SOC
- feeder_majors_at_school — return 3-5 feeders with offered_at_school flags
- lookup_credential_by_pre_x_pattern — regex match for pre-X major patterns

Thread-safe YAML loading uses the double-check lock pattern.
"""

from __future__ import annotations

import logging
import re
import threading
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]

from app.models.api import FeederMajor
from app.services import intent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# YAML loading with double-check lock.
# ---------------------------------------------------------------------------

_YAML_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "reference"
    / "grad_credential_feeders.yaml"
)

_credentials: list[dict[str, Any]] | None = None
_lock = threading.Lock()


def _load_credentials() -> list[dict[str, Any]]:
    """Load and cache the credential YAML. Thread-safe."""
    global _credentials
    if _credentials is not None:
        return _credentials
    with _lock:
        if _credentials is not None:
            return _credentials
        try:
            raw = yaml.safe_load(_YAML_PATH.read_text(encoding="utf-8"))
            _credentials = raw.get("credentials", [])
        except Exception as exc:
            logger.error("Failed to load grad_credential_feeders.yaml: %s", exc)
            _credentials = []
    return _credentials


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------


def lookup_credential_for_soc(soc_code: str) -> dict[str, Any] | None:
    """Return the credential entry whose ``socs`` list contains the SOC code.

    Returns None when no credential maps to this SOC.
    """
    credentials = _load_credentials()
    for cred in credentials:
        if soc_code in cred.get("socs", []):
            return cred
    return None


def feeder_majors_at_school(
    unitid: int, credential_id: str
) -> list[FeederMajor]:
    """Return 3-5 feeder majors for a credential, flagged by school offering.

    Uses ``intent._get_school_cips(unitid)`` to check which CIP-4 codes
    this school reports. Returns all feeders (up to 7), sorted with
    offered-at-school entries first.
    """
    credentials = _load_credentials()
    cred = next(
        (c for c in credentials if c.get("credential_id") == credential_id),
        None,
    )
    if cred is None:
        return []

    school_cips = intent._get_school_cips(unitid)
    school_cip4s: set[str] = {
        c.get("cipcode", "")[:5] for c in school_cips if c.get("cipcode")
    }

    feeders: list[FeederMajor] = []
    for entry in cred.get("feeder_cip4_codes", []):
        cip4 = entry.get("cip4", "")
        note = entry.get("note", "")
        # Derive cip_title from the note (before the dash)
        cip_title = note.split("—")[0].strip() if "—" in note else note
        offered = cip4 in school_cip4s
        feeders.append(
            FeederMajor(
                cip4=cip4,
                cip_title=cip_title,
                note=note,
                offered_at_school=offered,
            )
        )

    # Sort: offered first, then preserve YAML order.
    feeders.sort(key=lambda f: (not f.offered_at_school,))
    return feeders[:7]


# ---------------------------------------------------------------------------
# Pre-X pattern matching.
# ---------------------------------------------------------------------------

# Patterns map pre-X variants AND career-name inputs to credential_id.
# Career names trigger the same flow because a student typing "doctor"
# has the same intent as "pre-med" — neither is an undergrad major.
_PRE_X_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # "physician assistant" must precede "physician" to avoid false md match.
    (re.compile(
        r"\b(?:pre[- ]?pa|prepa|physician[- ]?assistant)\b", re.IGNORECASE,
    ), "ms-pa"),
    (re.compile(
        r"\b(?:pre[- ]?pt|prept|pre[- ]?physical[- ]?therapy|physical[- ]?therapist)\b",
        re.IGNORECASE,
    ), "dpt"),
    (re.compile(
        r"\b(?:pre[- ]?med|premed|doctor|physician)\b", re.IGNORECASE,
    ), "md"),
    (re.compile(
        r"\b(?:pre[- ]?law|prelaw|lawyer|attorney)\b", re.IGNORECASE,
    ), "jd"),
    (re.compile(
        r"\b(?:pre[- ]?vet|prevet|veterinarian)\b", re.IGNORECASE,
    ), "dvm"),
    (re.compile(
        r"\b(?:pre[- ]?dent\w*|predent\w*|dentist)\b", re.IGNORECASE,
    ), "dds"),
    (re.compile(
        r"\b(?:pre[- ]?optom\w*|preoptom\w*|optometrist)\b", re.IGNORECASE,
    ), "od"),
    (re.compile(
        r"\b(?:pre[- ]?pharm\w*|prepharm\w*|pharmacist)\b", re.IGNORECASE,
    ), "pharmd"),
]


def lookup_credential_by_pre_x_pattern(major_text: str) -> str | None:
    """Match a student's major text against pre-X patterns.

    Returns the credential_id if matched, None otherwise.
    """
    for pattern, credential_id in _PRE_X_PATTERNS:
        if pattern.search(major_text):
            return credential_id
    return None
