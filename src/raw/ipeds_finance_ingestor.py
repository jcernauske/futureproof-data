"""Ingestor for the IPEDS Finance Survey (F1A / F2 / F3 + EFIA + HD).

Lands the IPEDS Finance Survey into Iceberg as ``raw.ipeds_finance``
(~6,500 rows after the 4-year-bachelor's-or-above HD filter, one row per
institution per fiscal year).

Source: National Center for Education Statistics (NCES), IPEDS, Compare
Institutions → Finance.  IPEDS publishes finance data on three separate
forms keyed by institutional control (GASB / FASB / for-profit), and
publishes 12-Month Instructional Activity FTE on a parallel survey
component (EFIA).  The raw zone unions all three finance forms and
LEFT JOINs the FTE component on UNITID.  Institution name + the
4-year-bachelor's-or-above filter columns come from IPEDS HD (Header).

Five inputs:
  1. F1A — Public institutions (GASB), Part C functional expenses
  2. F2  — Private nonprofits (FASB), Section E functional expenses
  3. F3  — Private for-profits (post-2014-15 schedule)
  4. EFIA — 12-Month Instructional Activity, directly-reported FTE.
     This is the SOURCE OF TRUTH for ``total_fte_enrollment`` (computed
     as a NULL-safe sum of FTEUG + FTEGD + FTEDPP).  EF Part A's
     ``EFTOTLT`` is a fall-snapshot HEADCOUNT and EFFY is a 12-month
     unduplicated HEADCOUNT — neither is FTE; do NOT use either.
  5. HD  — Header file, supplies institution_name + ICLEVEL/HLOFFER for
     the IPEDS-native 4-year-bachelor's-or-above filter
     (``ICLEVEL = 1 AND HLOFFER >= 5``).

Spec: ``docs/specs/full-pipeline-ipeds-finance.md`` §3 + §4 (v1.3).
Pre-flight (column-code lock-down):
``governance/eda/raw-ingest-ipeds-finance-preflight.md``.
Full EDA (post-raw-land): ``governance/eda/raw-ingest-ipeds-finance-eda.md``.

Cache + fallback path:
    The orchestrator workflow caches the five source ZIPs at
    ``data/raw/ipeds_finance_cache/`` keyed by fiscal year.  The
    ingestor reads the cache by default; the bulk-download URLs below
    are the refresh path for future cycles.

Manual refresh (the IPEDS Data Center wraps each CSV in a per-file zip):
    https://nces.ed.gov/ipeds/datacenter/data/F{YY1}{YY2}_F1A.zip
    https://nces.ed.gov/ipeds/datacenter/data/F{YY1}{YY2}_F2.zip
    https://nces.ed.gov/ipeds/datacenter/data/F{YY1}{YY2}_F3.zip
    https://nces.ed.gov/ipeds/datacenter/data/EFIA{YYYY}.zip
    https://nces.ed.gov/ipeds/datacenter/data/HD{YYYY}.zip

  ``YY1YY2`` is the academic-year suffix; FY24 → ``2324`` →
  ``F2324_F1A.zip``.  EFIA and HD use the calendar year ending the
  12-month window (``EFIA2024.zip`` for the period ending June 2024).
"""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from pathlib import Path
from typing import Any, Iterable

import requests
from pyiceberg.schema import Schema
from pyiceberg.types import (
    DateType,
    DoubleType,
    IntegerType,
    LongType,
    NestedField,
    StringType,
    TimestampType,
)

from brightsmith.bronze.base_ingestor import BaseIngestor
from brightsmith.domain_loader import DomainManifest, SourceConfig

logger = logging.getLogger(__name__)


class IpedsFinanceIngestor(BaseIngestor):
    """Ingests the IPEDS Finance Survey into the bronze zone.

    Five-source ingestor: UNIONs F1A/F2/F3 finance forms, LEFT JOINs
    EFIA for 12-month FTE, and LEFT JOINs HD for institution_name + the
    ICLEVEL/HLOFFER filter columns.

    Grain: institution (UNITID), one row per institution per fiscal
    year.  Single-vintage scope per spec §2 Decision #6 — dedup grain
    is ``[unitid]``; promote multi-vintage requires the SCD2 spec.

    Key considerations (v1.3, post pre-flight lock-down):

    - **Column codes are LOCKED v1.3** by the pre-flight report at
      ``governance/eda/raw-ingest-ipeds-finance-preflight.md``.  All
      codes are still overrideable via class constants and ``__init__``
      arguments (defense-in-depth for future cycle drift), but the
      defaults match the verified 2021-22 IPEDS dictionary.

    - **EFIA, NOT EFFY.**  The 12-month FTE source is the *EFIA*
      ("12-Month Instructional Activity") survey, file
      ``EFIA{YYYY}.zip``.  EFIA is published one row per UNITID; no
      dedup filter required (verified 6,036 rows / 6,036 distinct
      UNITIDs on FY2022).  EFFY is the unduplicated headcount file
      (broken out by ``EFFYALEV``), wrong source — joining to it would
      fan out finance rows by student-level breakdown and inflate
      per-FTE values.

    - **Total FTE = NULL-safe sum.**
      ``COALESCE(FTEUG, 0) + COALESCE(FTEGD, 0) + COALESCE(FTEDPP, 0)``,
      returning NULL only when all three components are NULL.  Uses
      *reported* FTE (defaults to NCES *estimated* values per dictionary
      when the institution did not provide a reported figure), so the
      reported variants preserve institution-confirmed values where
      present.

    - **F3 institutional support IS reported.**  Pre-2014-15, F3 omitted
      institutional support; the 2014-15 schedule revision added the
      same six functional categories as F1A/F2.  Locked column is
      ``F3E03C1``, 100% non-null on FY2022 (2,120/2,120 rows).

    - **F3 endowment is genuinely N/A.**  No ``F3H`` family on the F3
      schedule — for-profits do not maintain endowments.  Coalesces to
      NULL (never imputed to 0).

    - **Imputation handling.**  Per spec §2 Decision #8, bureau-imputed
      values are accepted as raw values.  The parallel ``X*`` flag
      columns (``XF1C011``, ``XF1H02``, …) are NOT stored in v1.3.
      EDA Requirement 7 measures imputation prevalence; the policy
      may flip in a future revision, in which case both the raw schema
      and §2 Decision #8 must be revisited.

      **v1.4 amendment** (`docs/specs/ipeds-finance-v1.4.md`): the
      "X* prefix columns are stripped at bronze" policy is amended for
      ``XF1H02`` and ``XF2H02`` ONLY.  These two columns are captured
      as ``endowment_value_flag`` (string, nullable) so that downstream
      consumers can distinguish institution-reported (`R`) endowment
      values from NCES-imputed (`A`/`P`/`Z`/`N`) values.  All other X*
      flag columns remain unstored.  F3 has no ``F3H`` family on the
      F3 schedule (for-profits do not maintain endowments), so the
      flag is structurally NULL on F3 rows.

    - **Sentinel handling.**  IPEDS sentinels ``-1``, ``-2``, ``"."``
      (single period — legacy "not applicable" marker still appearing
      in modern releases), blank, and ``"PrivacySuppressed"`` map to
      NULL across all numeric fields BEFORE type coercion.

    - **UNITID coercion is `long`.**  Handles int, plain string,
      quoted string, and leading-zero string variants.  Rows with an
      unparseable UNITID are dropped with a warning, not silently
      ignored.

    - **HD filter is IPEDS-native.**  ``ICLEVEL = 1 AND HLOFFER >= 5``
      uses only IPEDS HD fields — no College Scorecard ``PREDDEG``
      dependency.  See spec §3 row "Filter".

    - **One row per UNITID across forms (invariant).**  Each
      institution's accounting basis (GASB / FASB / for-profit)
      determines a single finance form, so an institution should appear
      in exactly ONE of F1A/F2/F3.  If a UNITID appears in more than
      one form after the HD filter, log a warning — that's a data
      anomaly worth surfacing in EDA (and `RAW-IPF-003 unitid
      uniqueness` will flag it as a P0 DQ failure).

    - **Chunked reads.**  Project rule: read CSVs in 50,000-row
      chunks.  Finance CSVs are small (~6.5K rows) but the pattern
      keeps the chunk-yield bookkeeping in place for future use.

    - **User-Agent** on every download:
      ``FutureProof/0.1 (jeff@hyenastudios.com)``.

    - **Cache-first.**  The ingestor reads
      ``data/raw/ipeds_finance_cache/<file>.zip`` by default and
      reports ``source_method = "csv_cache"``.  Bulk-download URLs
      enable the refresh path when needed.
    """

    # ------------------------------------------------------------------
    # Source / cache / headers
    # ------------------------------------------------------------------
    # Stable lineage URL — actual download paths are the per-file zip
    # URLs computed below.  The data-center landing page is stamped on
    # every row so audit trails survive year-suffix drifts.
    LANDING_URL = "https://nces.ed.gov/ipeds/datacenter/"
    BULK_ZIP_URL_TEMPLATE = "https://nces.ed.gov/ipeds/datacenter/data/{filename}.zip"
    FALLBACK_CSV_DIR = "data/raw/ipeds_finance_cache"
    USER_AGENT = "FutureProof/0.1 (jeff@hyenastudios.com)"
    CSV_CHUNK_SIZE = 50_000

    # Default fiscal year — 2023 (FY23, academic year 2022-23).  The
    # full EDA at ``governance/eda/full-pipeline-ipeds-finance-raw-eda.md``
    # confirmed FY24 (`F2324_*.zip`) is NOT yet released by NCES (HTTP
    # 404 on the bulk URLs as of 2026-04-30; local cache zips for FY24
    # are 1.2KB 404-error HTML pages).  FY23 is the most-recent
    # fully-published cycle and the operative promote target.  Locked
    # column codes were verified against the FY23 dictionary varlists
    # at byte level (see EDA §2).  Promote to FY24 once NCES publishes
    # is a parameter change (`fiscal_year=2024`), not a code change.
    DEFAULT_FISCAL_YEAR = 2023

    # ------------------------------------------------------------------
    # LOCKED column codes (v1.3 pre-flight report)
    # ------------------------------------------------------------------
    # All codes below are LOCKED by the pre-flight report at
    # ``governance/eda/raw-ingest-ipeds-finance-preflight.md`` against
    # the FY2022 IPEDS dictionary.  They remain overrideable via
    # ``__init__`` arguments so a future cycle's revision can be tuned
    # without a code change.

    # F1A (public, GASB) — Part C functional expenses + Part H endowment.
    DEFAULT_F1A_INSTRUCTION_COL = "F1C011"
    DEFAULT_F1A_INSTITUTIONAL_SUPPORT_COL = "F1C071"
    DEFAULT_F1A_ENDOWMENT_EOY_COL = "F1H02"
    # v1.4: IPEDS imputation flag for F1A endowment (XF1H02).
    DEFAULT_F1A_ENDOWMENT_FLAG_COL = "XF1H02"

    # F2 (private nonprofit, FASB) — Section E functional expenses + H endowment.
    DEFAULT_F2_INSTRUCTION_COL = "F2E011"
    DEFAULT_F2_INSTITUTIONAL_SUPPORT_COL = "F2E061"
    DEFAULT_F2_ENDOWMENT_EOY_COL = "F2H02"
    # v1.4: IPEDS imputation flag for F2 endowment (XF2H02).
    DEFAULT_F2_ENDOWMENT_FLAG_COL = "XF2H02"

    # F3 (private for-profit) — post-2014-15 schedule has the same six
    # functional categories as F1A/F2.  Endowment is genuinely N/A
    # (no F3H family on the F3 form) and stays NULL.  By extension,
    # there is no F3 endowment-flag column either: ``endowment_value_flag``
    # is structurally NULL on every F3 row.  v1.4 §3 / §4 confirm.
    DEFAULT_F3_INSTRUCTION_COL: str = "F3E011"
    DEFAULT_F3_INSTITUTIONAL_SUPPORT_COL: str | None = "F3E03C1"
    DEFAULT_F3_ENDOWMENT_EOY_COL: str | None = None  # N/A for for-profits

    # EFIA (12-Month Instructional Activity) FTE columns.  Compute total
    # FTE as the NULL-safe sum below; EFIA is one row per UNITID so no
    # dedup filter is required.  Do NOT use EFFY (12-month headcount,
    # broken by EFFYALEV) or EF Part A EFTOTLT (fall headcount).
    DEFAULT_EFIA_FTE_UG_COL = "FTEUG"     # reported undergraduate FTE
    DEFAULT_EFIA_FTE_GD_COL = "FTEGD"     # reported graduate FTE
    DEFAULT_EFIA_FTE_DPP_COL = "FTEDPP"   # doctor's-professional-practice FTE

    # IPEDS HD (Header) file — institution_name + filter columns.
    # ``HD{YYYY}`` is the typical filename; column headers are stable
    # across recent IPEDS revisions.
    HD_INSTNM_COL = "INSTNM"
    HD_ICLEVEL_COL = "ICLEVEL"
    HD_HLOFFER_COL = "HLOFFER"
    HD_FILTER_ICLEVEL_VALUE = 1   # 4 or more years
    HD_FILTER_HLOFFER_MIN = 5     # bachelor's, post-bacc cert, master's, post-master's, doctorate

    # UNITID column header — uppercase across all five IPEDS files.
    UNITID_COLUMN = "UNITID"

    # IPEDS suppression sentinels per spec §4.  Treated as NULL across
    # all numeric fields BEFORE type coercion.
    SUPPRESSION_SENTINELS: frozenset[str] = frozenset(
        {"", "-1", "-2", ".", "PrivacySuppressed"}
    )

    # v1.4: sentinel set for the string flag column.  IPEDS does not
    # publish ``-1``/``-2`` on the X* flag columns (those are numeric
    # sentinels for value columns).  The flag-column sentinel set
    # therefore drops the numeric sentinels and keeps only the
    # blank-and-textual markers.  See `docs/specs/ipeds-finance-v1.4.md`
    # §4 ("the flag column does NOT take ``-1``/``-2``").
    FLAG_SUPPRESSION_SENTINELS: frozenset[str] = frozenset(
        {"", ".", "PrivacySuppressed"}
    )

    # Row-source tags written into the ``report_form`` column.
    REPORT_FORM_F1A = "F1A"
    REPORT_FORM_F2 = "F2"
    REPORT_FORM_F3 = "F3"

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    def __init__(
        self,
        source_config: SourceConfig,
        manifest: DomainManifest,
        *,
        fiscal_year: int | None = None,
        # F1A overrides
        f1a_instruction_col: str | None = None,
        f1a_institutional_support_col: str | None = None,
        f1a_endowment_eoy_col: str | None = None,
        f1a_endowment_flag_col: str | None = None,
        # F2 overrides
        f2_instruction_col: str | None = None,
        f2_institutional_support_col: str | None = None,
        f2_endowment_eoy_col: str | None = None,
        f2_endowment_flag_col: str | None = None,
        # F3 overrides — Ellipsis sentinel so callers can pass None
        # explicitly to mean "column does not exist on F3".
        f3_instruction_col: str | None | object = ...,
        f3_institutional_support_col: str | None | object = ...,
        f3_endowment_eoy_col: str | None | object = ...,
        # EFIA overrides — Ellipsis sentinel for the same reason; passing
        # None disables that component of the FTE sum.
        efia_fte_ug_col: str | None | object = ...,
        efia_fte_gd_col: str | None | object = ...,
        efia_fte_dpp_col: str | None | object = ...,
    ) -> None:
        """Construct an IpedsFinanceIngestor.

        Every column-name parameter exists so that a future IPEDS cycle
        revision can be tuned without a code change.  Defaults are LOCKED
        v1.3 by the pre-flight report — see the class docstring.

        Args:
            source_config: Brightsmith source config.
            manifest: Brightsmith domain manifest.
            fiscal_year: Override for the IPEDS fiscal year stamped on
                every row.  Default is ``DEFAULT_FISCAL_YEAR`` (2023 —
                FY23, academic year 2022-23, the most-recent
                fully-published Finance cycle as of 2026-04-30).
            f1a_instruction_col: F1A instruction-expenses column.
                Default ``F1C011``.
            f1a_institutional_support_col: F1A institutional-support
                column.  Default ``F1C071``.
            f1a_endowment_eoy_col: F1A end-of-year endowment column.
                Default ``F1H02``.
            f1a_endowment_flag_col: F1A IPEDS imputation flag column for
                ``endowment_value`` (v1.4 addition).  Default ``XF1H02``.
                String enum: ``{R, A, P, Z, N}`` per IPEDS dictionary;
                NULL after sentinel scrub on blank / ``.`` /
                ``PrivacySuppressed``.
            f2_instruction_col: F2 instruction-expenses column.
                Default ``F2E011``.
            f2_institutional_support_col: F2 institutional-support
                column.  Default ``F2E061``.
            f2_endowment_eoy_col: F2 end-of-year endowment column.
                Default ``F2H02``.
            f2_endowment_flag_col: F2 IPEDS imputation flag column for
                ``endowment_value`` (v1.4 addition).  Default ``XF2H02``.
                String enum: ``{R, A, P, Z, N}`` per IPEDS dictionary;
                NULL after sentinel scrub.
            f3_instruction_col: F3 instruction-expenses column.
                Default ``F3E011``.  Pass ``None`` to suppress the F3
                lookup.  Pass the literal sentinel ``...`` (Ellipsis,
                the default) to keep the class default.
            f3_institutional_support_col: F3 institutional-support
                column.  Default ``F3E03C1`` (post-2014-15 schedule).
                Pass ``None`` to coalesce to NULL (legacy pre-2015
                schedule behavior).
            f3_endowment_eoy_col: F3 end-of-year endowment column.
                Default ``None`` (for-profits do not maintain
                endowments — N/A → NULL).
            efia_fte_ug_col: EFIA reported undergraduate FTE column.
                Default ``FTEUG``.  Pass ``None`` to omit from the sum.
            efia_fte_gd_col: EFIA reported graduate FTE column.
                Default ``FTEGD``.  Pass ``None`` to omit from the sum.
            efia_fte_dpp_col: EFIA reported doctor's-professional-
                practice FTE column.  Default ``FTEDPP``.  Pass ``None``
                to omit from the sum (degrades total FTE for medical /
                law / dental / veterinary schools by 5–15%).
        """
        super().__init__(source_config, manifest)

        self.fiscal_year: int = (
            fiscal_year if fiscal_year is not None else self.DEFAULT_FISCAL_YEAR
        )

        # F1A
        self.f1a_instruction_col: str = (
            f1a_instruction_col or self.DEFAULT_F1A_INSTRUCTION_COL
        )
        self.f1a_institutional_support_col: str = (
            f1a_institutional_support_col
            or self.DEFAULT_F1A_INSTITUTIONAL_SUPPORT_COL
        )
        self.f1a_endowment_eoy_col: str = (
            f1a_endowment_eoy_col or self.DEFAULT_F1A_ENDOWMENT_EOY_COL
        )
        # v1.4: F1A imputation flag (XF1H02).  String column; required
        # (mirrors instruction/institutional_support default-or-override
        # resolution, NOT the F3 Ellipsis-sentinel pattern).
        self.f1a_endowment_flag_col: str = (
            f1a_endowment_flag_col or self.DEFAULT_F1A_ENDOWMENT_FLAG_COL
        )

        # F2
        self.f2_instruction_col: str = (
            f2_instruction_col or self.DEFAULT_F2_INSTRUCTION_COL
        )
        self.f2_institutional_support_col: str = (
            f2_institutional_support_col
            or self.DEFAULT_F2_INSTITUTIONAL_SUPPORT_COL
        )
        self.f2_endowment_eoy_col: str = (
            f2_endowment_eoy_col or self.DEFAULT_F2_ENDOWMENT_EOY_COL
        )
        # v1.4: F2 imputation flag (XF2H02).
        self.f2_endowment_flag_col: str = (
            f2_endowment_flag_col or self.DEFAULT_F2_ENDOWMENT_FLAG_COL
        )

        # F3 — Ellipsis sentinel handling so None means "not present".
        self.f3_instruction_col: str | None = self._resolve_optional_override(
            f3_instruction_col, self.DEFAULT_F3_INSTRUCTION_COL
        )
        self.f3_institutional_support_col: str | None = (
            self._resolve_optional_override(
                f3_institutional_support_col,
                self.DEFAULT_F3_INSTITUTIONAL_SUPPORT_COL,
            )
        )
        self.f3_endowment_eoy_col: str | None = self._resolve_optional_override(
            f3_endowment_eoy_col, self.DEFAULT_F3_ENDOWMENT_EOY_COL
        )

        # EFIA — three FTE-component columns; sum is NULL-safe.
        self.efia_fte_ug_col: str | None = self._resolve_optional_override(
            efia_fte_ug_col, self.DEFAULT_EFIA_FTE_UG_COL
        )
        self.efia_fte_gd_col: str | None = self._resolve_optional_override(
            efia_fte_gd_col, self.DEFAULT_EFIA_FTE_GD_COL
        )
        self.efia_fte_dpp_col: str | None = self._resolve_optional_override(
            efia_fte_dpp_col, self.DEFAULT_EFIA_FTE_DPP_COL
        )

        # Stash so ingest()/fetch() can avoid double-fetching.
        self._prefetched: dict[Any, Any] | None = None

    @staticmethod
    def _resolve_optional_override(
        override: str | None | object, default: str | None
    ) -> str | None:
        """Resolve an Ellipsis-sentinel override to ``str | None``.

        ``...`` (Ellipsis) means "use class default"; an explicit
        ``None`` means "the column does not exist / disable lookup".
        """
        if override is ...:
            return default
        assert override is None or isinstance(override, str), (
            "override must be str | None"
        )
        return override

    # ------------------------------------------------------------------
    # Ingest override (capture true source_method, mirrors EADA/BEA)
    # ------------------------------------------------------------------
    def ingest(self, *args: Any, **kwargs: Any) -> dict:
        """Run the BaseIngestor pipeline, fixing source_method post-hoc.

        Mirrors the EADA/BEA RPP pattern so the row-level
        ``source_method`` reflects whether we actually pulled from the
        bulk URLs or fell back to the CSV cache.
        """
        entities = kwargs.pop("entities", None) or self.source.entities
        warehouse_path = kwargs.pop("warehouse_path", None)
        catalog_path = kwargs.pop("catalog_path", None)
        kwargs.pop("method", None)

        raw_data = self.fetch(entities, method="ipeds_finance", **kwargs)
        sample = next(iter(raw_data.values())) if raw_data else {}
        effective_method: str = sample.get("source_method", "csv_cache")
        self._prefetched = raw_data

        try:
            return super().ingest(
                entities=entities,
                method=effective_method,
                warehouse_path=warehouse_path,
                catalog_path=catalog_path,
                **kwargs,
            )
        finally:
            self._prefetched = None

    # ------------------------------------------------------------------
    # Fetch — five-source orchestration
    # ------------------------------------------------------------------
    def fetch(self, entities: dict, method: str, **kwargs: Any) -> dict:
        """Fetch and assemble the joined raw payload.

        Pulls F1A, F2, F3 finance forms, EFIA FTE, and HD institution
        metadata.  Returns a single dict per entity carrying:

        - ``f1a_rows`` / ``f2_rows`` / ``f3_rows`` — finance-form rows
        - ``efia_by_unitid`` — UNITID → total_fte_enrollment (NULL-safe sum)
        - ``hd_by_unitid`` — UNITID → {institution_name, iclevel, hloffer}
        - ``source_method`` — ``"bulk_csv_download"`` or ``"csv_cache"``

        Args:
            entities: ``{entity_id: label}`` from source config.
            method: Fetch method name (informational).
            **kwargs: Supports:
                - ``f1a_csv_path`` / ``f2_csv_path`` / ``f3_csv_path``
                  / ``efia_csv_path`` / ``hd_csv_path``: explicit
                  per-file overrides (skip network, used in tests).
                - ``cache_dir``: override default cache directory.
                - ``force_fallback``: True to skip the network entirely.
                - ``fiscal_year``: override the cached files' year suffix.

        Returns:
            ``{entity_id: payload}`` for each entity.
        """
        prefetched = self._prefetched
        if prefetched:
            return prefetched

        cache_dir_kw = kwargs.get("cache_dir")
        force_fallback = bool(kwargs.get("force_fallback"))
        fiscal_year = int(kwargs.get("fiscal_year") or self.fiscal_year)
        cache_dir = Path(cache_dir_kw) if cache_dir_kw else Path(self.FALLBACK_CSV_DIR)

        # Per-file resolution: explicit path → bulk URL → cache.  Each
        # file stamps its own source_method; the row-level value is the
        # max-precedence over all five inputs (bulk wins over cache).
        f1a_rows, f1a_method = self._fetch_one(
            kwargs.get("f1a_csv_path"),
            self._fy_filename("F1A", fiscal_year),
            cache_dir,
            force_fallback,
        )
        f2_rows, f2_method = self._fetch_one(
            kwargs.get("f2_csv_path"),
            self._fy_filename("F2", fiscal_year),
            cache_dir,
            force_fallback,
        )
        f3_rows, f3_method = self._fetch_one(
            kwargs.get("f3_csv_path"),
            self._fy_filename("F3", fiscal_year),
            cache_dir,
            force_fallback,
        )
        efia_rows, efia_method = self._fetch_one(
            kwargs.get("efia_csv_path"),
            self._efia_filename(fiscal_year),
            cache_dir,
            force_fallback,
        )
        hd_rows, hd_method = self._fetch_one(
            kwargs.get("hd_csv_path"),
            self._hd_filename(fiscal_year),
            cache_dir,
            force_fallback,
        )

        # Aggregate source_method: any bulk download wins.
        all_methods = {f1a_method, f2_method, f3_method, efia_method, hd_method}
        source_method = (
            "bulk_csv_download" if "bulk_csv_download" in all_methods else "csv_cache"
        )

        efia_by_unitid = self._build_efia_lookup(efia_rows)
        hd_by_unitid = self._build_hd_lookup(hd_rows)

        payload = {
            "f1a_rows": f1a_rows,
            "f2_rows": f2_rows,
            "f3_rows": f3_rows,
            "efia_by_unitid": efia_by_unitid,
            "hd_by_unitid": hd_by_unitid,
            "source_method": source_method,
        }
        return {entity_id: payload for entity_id in entities}

    def _fy_filename(self, form_suffix: str, fiscal_year: int) -> str:
        """Return the IPEDS finance-form filename for a fiscal year.

        IPEDS finance-form file pattern: ``F{YY1}{YY2}_F{1A|2|3}``.
        FY24 (academic year 2023-24) → ``F2324_F1A`` /
        ``F2324_F2`` / ``F2324_F3``.  The leading ``F{YY1}{YY2}`` is the
        finance-survey cycle prefix; the ``_F{1A|2|3}`` is the form.
        """
        yy1 = (fiscal_year - 1) % 100
        yy2 = fiscal_year % 100
        return f"F{yy1:02d}{yy2:02d}_{form_suffix}"

    def _efia_filename(self, fiscal_year: int) -> str:
        """Return the EFIA filename for a fiscal year.

        EFIA file pattern: ``EFIA{YYYY}`` where YYYY is the calendar
        year ending the 12-month window (FY24 → ``EFIA2024``).
        """
        return f"EFIA{fiscal_year}"

    def _hd_filename(self, fiscal_year: int) -> str:
        """Return the HD (Header) filename — calendar year matching fiscal_year."""
        return f"HD{fiscal_year}"

    # ------------------------------------------------------------------
    # Per-file fetch (path → bulk → cache)
    # ------------------------------------------------------------------
    def _fetch_one(
        self,
        explicit_path: str | None,
        cache_basename: str,
        cache_dir: Path,
        force_fallback: bool,
    ) -> tuple[list[dict], str]:
        """Resolve one IPEDS file to (rows, source_method).

        Resolution order:
          1. ``explicit_path`` (test override) — reads the local CSV.
          2. Local cache zip at ``cache_dir/<cache_basename>.zip`` (if
             present and not ``force_fallback``-bypassed).  This wins
             over the bulk URL because operators stage the zips locally
             during refresh and we should not re-download them on every
             ingest.
          3. Local cache CSV at ``cache_dir/<cache_basename>.csv``.
          4. Bulk download from
             ``BULK_ZIP_URL_TEMPLATE.format(filename=cache_basename)``
             unless ``force_fallback`` is set.
        """
        if explicit_path:
            rows = self._read_csv_file(Path(explicit_path))
            return rows, "csv_cache"

        # Prefer locally-staged zips and CSVs over re-downloading.
        cache_zip = cache_dir / f"{cache_basename}.zip"
        cache_csv = cache_dir / f"{cache_basename}.csv"
        if cache_zip.exists():
            rows = self._read_zip_file(cache_zip)
            return rows, "csv_cache"
        if cache_csv.exists():
            rows = self._read_csv_file(cache_csv)
            return rows, "csv_cache"

        if force_fallback:
            raise FileNotFoundError(
                f"IPEDS cache miss for {cache_basename} (looked in "
                f"{cache_zip} and {cache_csv}) and force_fallback=True"
            )

        try:
            rows = self._fetch_from_bulk(cache_basename)
            return rows, "bulk_csv_download"
        except Exception as exc:
            logger.warning(
                "IPEDS bulk fetch failed for %s (%s); no cache available",
                cache_basename,
                exc,
            )
            raise

    def _fetch_from_bulk(self, filename: str) -> list[dict]:
        """Download an IPEDS per-file zip and parse the inner CSV.

        IPEDS Data Center wraps every CSV in a per-file zip.  Single
        attempt — caller raises on failure.
        """
        url = self.BULK_ZIP_URL_TEMPLATE.format(filename=filename)
        headers = {"User-Agent": self.USER_AGENT}
        response = requests.get(url, headers=headers, timeout=180)
        response.raise_for_status()
        content = response.content

        if content[:4] != b"PK\x03\x04":
            raise ValueError(
                f"IPEDS bulk download for {filename} is not a zip "
                f"(first bytes: {content[:8]!r})"
            )
        rows = self._parse_zip_bytes(content, filename)
        logger.info("Downloaded %d rows from IPEDS bulk %s", len(rows), filename)
        return rows

    def _read_zip_file(self, path: Path) -> list[dict]:
        """Read a local IPEDS per-file zip and parse the inner CSV."""
        with open(path, "rb") as f:
            content = f.read()
        rows = self._parse_zip_bytes(content, path.name)
        logger.info("Read %d rows from IPEDS zip cache %s", len(rows), path)
        return rows

    def _parse_zip_bytes(self, content: bytes, label: str) -> list[dict]:
        """Extract the inner CSV from an IPEDS zip and parse it."""
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError(f"IPEDS zip {label} contains no CSV files")
            # IPEDS occasionally ships a "_rv" revised-data CSV alongside
            # the original; prefer the revised file when present (it
            # supersedes the original per NCES revision policy).
            csv_names.sort(key=lambda n: ("_rv" not in n.lower(), n))
            raw = zf.read(csv_names[0])

        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        # IPEDS CSVs occasionally include non-UTF8 bytes in institution
        # names (Latin-1 punctuation, etc.); decode permissively.
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
        return self._parse_csv_text(text)

    def _read_csv_file(self, path: Path) -> list[dict]:
        """Read a local IPEDS CSV cache file (chunked, 50K rows)."""
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                rows = list(self._iter_csv_chunks(f))
        except UnicodeDecodeError:
            with open(path, newline="", encoding="latin-1") as f:
                rows = list(self._iter_csv_chunks(f))
        logger.info("Read %d rows from IPEDS CSV cache %s", len(rows), path)
        return rows

    def _parse_csv_text(self, text: str) -> list[dict]:
        """Parse CSV text via the chunked iterator (in-memory)."""
        return list(self._iter_csv_chunks(io.StringIO(text)))

    def _iter_csv_chunks(self, fh: Iterable[str]) -> Iterable[dict]:
        """Yield CSV rows in 50,000-row chunks per CLAUDE.md.

        The chunk size doesn't change the in-memory cost for this
        callsite (we materialize to a list above), but it keeps the
        chunked-read convention in place.  Chunking is a yield-cadence
        bookkeeping step so log lines and any future streaming
        consumers can checkpoint mid-file.
        """
        reader = csv.DictReader(fh)
        chunk: list[dict] = []
        total = 0
        for row in reader:
            chunk.append(row)
            if len(chunk) >= self.CSV_CHUNK_SIZE:
                total += len(chunk)
                logger.debug("CSV chunk yielded; running total=%d", total)
                yield from chunk
                chunk = []
        if chunk:
            total += len(chunk)
            yield from chunk

    # ------------------------------------------------------------------
    # Lookups (EFIA NULL-safe FTE sum + HD index)
    # ------------------------------------------------------------------
    def _build_efia_lookup(
        self, rows: list[dict]
    ) -> dict[int, float | None]:
        """Build {UNITID → total_fte_enrollment} from EFIA rows.

        EFIA is published one row per UNITID (verified 6,036 rows /
        6,036 distinct UNITIDs on FY2022, per pre-flight) so no dedup
        filter is required — if a duplicate UNITID is observed we log
        a warning (data anomaly) and keep the first occurrence.

        Total FTE is the NULL-safe sum:
            ``COALESCE(FTEUG, 0) + COALESCE(FTEGD, 0) + COALESCE(FTEDPP, 0)``
        returning NULL only when all three components are NULL.
        """
        lookup: dict[int, float | None] = {}
        skipped_unitid = 0
        duplicate_unitid = 0
        for row in rows:
            unitid = self._coerce_long(row.get(self.UNITID_COLUMN))
            if unitid is None:
                skipped_unitid += 1
                continue
            ug = self._coerce_double(
                self._strip_sentinel(row.get(self.efia_fte_ug_col))
                if self.efia_fte_ug_col
                else None
            )
            gd = self._coerce_double(
                self._strip_sentinel(row.get(self.efia_fte_gd_col))
                if self.efia_fte_gd_col
                else None
            )
            dpp = self._coerce_double(
                self._strip_sentinel(row.get(self.efia_fte_dpp_col))
                if self.efia_fte_dpp_col
                else None
            )
            if ug is None and gd is None and dpp is None:
                total_fte: float | None = None
            else:
                total_fte = (ug or 0.0) + (gd or 0.0) + (dpp or 0.0)
            if unitid in lookup:
                duplicate_unitid += 1
                continue
            lookup[unitid] = total_fte

        if skipped_unitid:
            logger.warning(
                "Dropped %d EFIA rows with unparseable UNITID", skipped_unitid
            )
        if duplicate_unitid:
            logger.warning(
                "EFIA observed %d duplicate UNITIDs (expected one row per "
                "UNITID per pre-flight) — data anomaly, kept first occurrence",
                duplicate_unitid,
            )
        logger.info("Built EFIA FTE lookup for %d UNITIDs", len(lookup))
        return lookup

    def _build_hd_lookup(
        self, rows: list[dict]
    ) -> dict[int, dict[str, Any]]:
        """Build {UNITID → {institution_name, iclevel, hloffer}} from HD."""
        lookup: dict[int, dict[str, Any]] = {}
        skipped_unitid = 0
        for row in rows:
            unitid = self._coerce_long(row.get(self.UNITID_COLUMN))
            if unitid is None:
                skipped_unitid += 1
                continue
            institution_name = self._coerce_string(row.get(self.HD_INSTNM_COL))
            iclevel = self._coerce_int(row.get(self.HD_ICLEVEL_COL))
            hloffer = self._coerce_int(row.get(self.HD_HLOFFER_COL))
            lookup[unitid] = {
                "institution_name": institution_name,
                "iclevel": iclevel,
                "hloffer": hloffer,
            }
        if skipped_unitid:
            logger.warning(
                "Dropped %d IPEDS HD rows with unparseable UNITID", skipped_unitid
            )
        logger.info("Built HD lookup for %d UNITIDs", len(lookup))
        return lookup

    # ------------------------------------------------------------------
    # Flatten — UNION the three forms, attach FTE + HD, apply HD filter
    # ------------------------------------------------------------------
    def flatten(self, raw_data: Any, entity_id: Any) -> list[dict]:
        """Flatten raw IPEDS Finance into Iceberg-ready dicts.

        Pipeline per row, in order:
          1. UNITID coercion (drop rows with unparseable UNITID).
          2. HD lookup — if UNITID is not in HD, drop row (no
             institution_name + no filter columns means we can't
             promote it).
          3. HD filter: ``ICLEVEL == 1 AND HLOFFER >= 5``.  Drop rows
             that fail the filter.
          4. Per-form column resolution — coalesce form-specific
             column codes into the canonical raw fields.  Missing F3
             columns map to NULL (never 0).
          5. Sentinel scrub on every numeric value BEFORE coercion.
          6. Coerce numeric fields to ``double``.
          7. EFIA LEFT JOIN on UNITID for ``total_fte_enrollment``.
          8. Stamp ``report_form`` and ``fiscal_year``.

        Cross-form invariant: each institution's accounting basis fixes
        a single finance form, so a UNITID should appear in exactly ONE
        of F1A/F2/F3.  Cross-form duplicates are logged as a warning
        (the dedup-grain mechanism in BaseIngestor will collapse them
        and ``RAW-IPF-003`` will surface the anomaly as a P0 DQ
        failure).

        Framework metadata (``ingested_at``, ``source_url``,
        ``source_method``, ``load_date``) is added by
        ``BaseIngestor.ingest()`` after this method returns.

        Args:
            raw_data: dict from ``fetch()`` carrying f1a/f2/f3/efia/hd.
            entity_id: logical entity id (unused — single entity).

        Returns:
            List of flat dicts ready for Iceberg append.
        """
        f1a_rows: list[dict] = raw_data["f1a_rows"]
        f2_rows: list[dict] = raw_data["f2_rows"]
        f3_rows: list[dict] = raw_data["f3_rows"]
        efia_by_unitid: dict[int, float | None] = raw_data["efia_by_unitid"]
        hd_by_unitid: dict[int, dict[str, Any]] = raw_data["hd_by_unitid"]

        flat_rows: list[dict] = []
        seen_unitids: dict[int, str] = {}
        cross_form_duplicates = 0
        stats = {
            "unparseable_unitid": 0,
            "hd_miss": 0,
            "hd_filter_rejected": 0,
        }

        def process(rows: list[dict], form: str, instr: str | None,
                    inst_supp: str | None, endow: str | None,
                    endow_flag: str | None) -> None:
            nonlocal cross_form_duplicates
            for row in rows:
                record = self._flatten_one(
                    row,
                    form,
                    instr,
                    inst_supp,
                    endow,
                    endow_flag,
                    efia_by_unitid,
                    hd_by_unitid,
                    stats,
                )
                if record is None:
                    continue
                unitid = record["unitid"]
                if unitid in seen_unitids:
                    cross_form_duplicates += 1
                    logger.warning(
                        "UNITID %d appears in multiple finance forms (%s and %s) — "
                        "expected exactly one form per institution",
                        unitid,
                        seen_unitids[unitid],
                        form,
                    )
                else:
                    seen_unitids[unitid] = form
                flat_rows.append(record)

        process(
            f1a_rows,
            self.REPORT_FORM_F1A,
            self.f1a_instruction_col,
            self.f1a_institutional_support_col,
            self.f1a_endowment_eoy_col,
            self.f1a_endowment_flag_col,
        )
        process(
            f2_rows,
            self.REPORT_FORM_F2,
            self.f2_instruction_col,
            self.f2_institutional_support_col,
            self.f2_endowment_eoy_col,
            self.f2_endowment_flag_col,
        )
        # F3 has no F3H endowment family (per v1.3 §3); the v1.4
        # endowment_value_flag is therefore structurally NULL on every
        # F3 row.  Pass ``None`` for ``endow_flag``.
        process(
            f3_rows,
            self.REPORT_FORM_F3,
            self.f3_instruction_col,
            self.f3_institutional_support_col,
            self.f3_endowment_eoy_col,
            None,
        )

        if stats["unparseable_unitid"]:
            logger.warning(
                "Dropped %d IPEDS Finance rows with unparseable UNITID",
                stats["unparseable_unitid"],
            )
        if stats["hd_miss"]:
            logger.info(
                "Dropped %d IPEDS Finance rows with no HD record (no name/filter columns)",
                stats["hd_miss"],
            )
        if stats["hd_filter_rejected"]:
            logger.info(
                "Filtered %d IPEDS Finance rows failing HD filter "
                "(ICLEVEL=%d AND HLOFFER>=%d)",
                stats["hd_filter_rejected"],
                self.HD_FILTER_ICLEVEL_VALUE,
                self.HD_FILTER_HLOFFER_MIN,
            )
        if cross_form_duplicates:
            logger.warning(
                "Observed %d UNITIDs reported on more than one finance form "
                "(F1A/F2/F3) — data anomaly, will fail RAW-IPF-003 unless "
                "BaseIngestor dedup collapses them",
                cross_form_duplicates,
            )
        logger.info(
            "Flattened %d IPEDS Finance rows (4-year filter applied)", len(flat_rows)
        )
        return flat_rows

    def _flatten_one(
        self,
        row: dict,
        report_form: str,
        instruction_col: str | None,
        institutional_support_col: str | None,
        endowment_col: str | None,
        endowment_flag_col: str | None,
        efia_by_unitid: dict[int, float | None],
        hd_by_unitid: dict[int, dict[str, Any]],
        stats: dict[str, int],
    ) -> dict | None:
        """Flatten one finance-form row into the canonical raw record.

        Returns ``None`` to indicate a drop (unparseable UNITID, HD
        miss, or HD filter reject).

        v1.4 adds the ``endowment_flag_col`` parameter — when ``None``
        (F3) or absent from the input row, ``endowment_value_flag`` is
        emitted as NULL.  When present, the value is sentinel-scrubbed
        (blank / ``.`` / ``PrivacySuppressed`` → NULL) and emitted
        verbatim as a string (NO numeric coercion — the column is a
        small enumerated string domain ``{R, A, P, Z, N}`` per the
        IPEDS Finance dictionary).
        """
        unitid = self._coerce_long(row.get(self.UNITID_COLUMN))
        if unitid is None:
            stats["unparseable_unitid"] += 1
            return None

        hd = hd_by_unitid.get(unitid)
        if hd is None:
            stats["hd_miss"] += 1
            return None

        iclevel = hd.get("iclevel")
        hloffer = hd.get("hloffer")
        if not (
            iclevel == self.HD_FILTER_ICLEVEL_VALUE
            and isinstance(hloffer, int)
            and hloffer >= self.HD_FILTER_HLOFFER_MIN
        ):
            stats["hd_filter_rejected"] += 1
            return None

        institutional_support = self._coerce_double(
            self._strip_sentinel(row.get(institutional_support_col))
            if institutional_support_col
            else None
        )
        instruction = self._coerce_double(
            self._strip_sentinel(row.get(instruction_col))
            if instruction_col
            else None
        )
        endowment = self._coerce_double(
            self._strip_sentinel(row.get(endowment_col))
            if endowment_col
            else None
        )
        # v1.4: endowment_value_flag — string passthrough, sentinel-
        # scrubbed but NOT numeric-coerced.  ``None`` flag column means
        # "structurally N/A on this form" (F3); a missing value on a
        # form that does carry the flag falls through to NULL via the
        # sentinel scrub on blank.
        endowment_flag = self._strip_flag_sentinel(
            row.get(endowment_flag_col)
            if endowment_flag_col
            else None
        )
        total_fte = efia_by_unitid.get(unitid)

        return {
            "unitid": unitid,
            "institution_name": hd.get("institution_name") or "",
            "report_form": report_form,
            "fiscal_year": int(self.fiscal_year),
            "institutional_support_expenses": institutional_support,
            "instruction_expenses": instruction,
            "endowment_value": endowment,
            "endowment_value_flag": endowment_flag,
            "total_fte_enrollment": total_fte,
        }

    def get_source_url(self, entity_id: Any, method: str) -> str:
        """Stable lineage URL for every row.

        Per spec §4 the row-level ``source_url`` is a pipe-delimited
        list of the five per-file source URLs (F1A, F2, F3, EFIA, HD).
        Filenames are fiscal-year-specific so the list reflects the
        actual files consumed.
        """
        fy = int(self.fiscal_year)
        files = [
            self._fy_filename("F1A", fy),
            self._fy_filename("F2", fy),
            self._fy_filename("F3", fy),
            self._efia_filename(fy),
            self._hd_filename(fy),
        ]
        return "|".join(
            self.BULK_ZIP_URL_TEMPLATE.format(filename=name) for name in files
        )

    # ------------------------------------------------------------------
    # Sentinel + coercion helpers
    # ------------------------------------------------------------------
    @classmethod
    def _strip_sentinel(cls, value: Any) -> Any:
        """Replace IPEDS suppression sentinels with ``None``.

        Applied BEFORE numeric coercion per spec §4.  Sentinels are
        compared as stripped strings.  Non-string values pass through.
        """
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped in cls.SUPPRESSION_SENTINELS:
                return None
            return stripped
        return value

    @classmethod
    def _strip_flag_sentinel(cls, value: Any) -> str | None:
        """Replace IPEDS string-flag sentinels with ``None`` (v1.4).

        The flag column ``endowment_value_flag`` (sourced from F1A
        ``XF1H02`` / F2 ``XF2H02``) is a small enumerated string
        domain (``{R, A, P, Z, N}`` per IPEDS dictionary).  Unlike the
        numeric value columns, the flag does NOT take ``-1``/``-2``
        sentinels — those are numeric markers reserved for value
        columns.  This helper applies only the blank-and-textual
        sentinels (``''`` / ``'.'`` / ``'PrivacySuppressed'``) and
        returns the stripped string verbatim otherwise (no numeric
        coercion, no upper-casing — preserve source fidelity).

        ``None`` returns ``None`` (e.g., F3 rows where the flag column
        does not exist on the schedule).
        """
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            if stripped in cls.FLAG_SUPPRESSION_SENTINELS:
                return None
            return stripped
        # Defensive: a non-string value is unexpected on a flag column
        # but coerce to string for downstream consumers — mirrors the
        # passthrough semantics on the numeric SUPPRESSION_SENTINELS
        # path which lets non-strings flow through.
        return str(value)

    @staticmethod
    def _coerce_long(value: Any) -> int | None:
        """Coerce UNITID to ``int`` (Iceberg ``long``)."""
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value != value:  # NaN
                return None
            return int(value)
        if isinstance(value, str):
            s = value.strip().strip('"').strip("'")
            if not s:
                return None
            try:
                return int(s)
            except ValueError:
                try:
                    return int(float(s))
                except (ValueError, TypeError):
                    return None
        return None

    @staticmethod
    def _coerce_double(value: Any) -> float | None:
        """Coerce a sentinel-stripped value to ``float`` (Iceberg ``double``)."""
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            f = float(value)
            if f != f:  # NaN
                return None
            return f
        if isinstance(value, str):
            s = value.strip().replace(",", "").replace("$", "")
            if not s:
                return None
            try:
                return float(s)
            except (ValueError, TypeError):
                return None
        return None

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        """Coerce to ``int`` for HD ICLEVEL / HLOFFER lookups."""
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            if value != value:  # NaN
                return None
            return int(value)
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            try:
                return int(s)
            except ValueError:
                try:
                    return int(float(s))
                except (ValueError, TypeError):
                    return None
        return None

    @staticmethod
    def _coerce_string(value: Any) -> str | None:
        if value is None:
            return None
        s = str(value).strip()
        return s if s else None

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def get_schema(self) -> Schema:
        """Define the Iceberg table schema for ``raw.ipeds_finance``.

        Matches the spec §4 Raw Schema exactly.  Field IDs 1-8 are the
        IPEDS Finance payload; 9-12 are framework metadata stamped by
        ``BaseIngestor.ingest()``; field id 13 is the v1.4 additive
        ``endowment_value_flag`` column (string, nullable; sourced from
        ``XF1H02`` / ``XF2H02`` on F1A / F2; NULL on F3 — no ``F3H``
        family).
        """
        return Schema(
            # Grain field
            NestedField(1, "unitid", LongType(), required=True),
            # Data fields
            NestedField(2, "institution_name", StringType(), required=True),
            NestedField(3, "report_form", StringType(), required=True),
            NestedField(4, "fiscal_year", IntegerType(), required=True),
            NestedField(
                5, "institutional_support_expenses", DoubleType(), required=False
            ),
            NestedField(6, "instruction_expenses", DoubleType(), required=False),
            NestedField(7, "endowment_value", DoubleType(), required=False),
            NestedField(8, "total_fte_enrollment", DoubleType(), required=False),
            # Framework metadata
            NestedField(9, "source_url", StringType(), required=True),
            NestedField(10, "source_method", StringType(), required=True),
            NestedField(11, "ingested_at", TimestampType(), required=True),
            NestedField(12, "load_date", DateType(), required=True),
            # v1.4 additive — IPEDS imputation flag for endowment_value.
            NestedField(13, "endowment_value_flag", StringType(), required=False),
        )
