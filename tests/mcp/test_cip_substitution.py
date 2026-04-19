"""Unit tests for CIP intent substitution in get_career_paths.

Covers the product decisions described in
``docs/specs/cip-intent-substitution.md``:

  * Substitution fires only when all four gates pass (student_major
    provided, reported cipcode is broad, major matches, family matches)
  * Lookup is case- and alias-insensitive
  * Family-mismatch and unrecognized-major fall back to the standard
    path with a ``substitution_note``
  * Blended ERN/ROI use the Gold engine formula
  * ``data_caveat`` metadata is attached to every substituted row set
    and absent on non-substituted results
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from mcp_server.futureproof_server import (
    CAREER_OUTCOMES_TABLE,
    CAREER_PATHS_TABLE,
    FutureProofMCPServer,
)


# Sample lookup that mirrors the shape of major_to_cip.yaml.
FAKE_LOOKUP = [
    {
        "major": "Marketing",
        "cip4": "52.14",
        "cip_family": "52",
        "aliases": ["marketing management", "mktg", "digital marketing"],
    },
    {
        "major": "Accounting",
        "cip4": "52.03",
        "cip_family": "52",
        "aliases": ["accountancy", "acct"],
    },
    {
        "major": "Finance",
        "cip4": "52.08",
        "cip_family": "52",
        "aliases": ["financial management"],
    },
    {
        "major": "Nursing",
        "cip4": "51.38",
        "cip_family": "51",
        "aliases": ["registered nurse", "RN"],
    },
]


# IU-B broad-CIP row used as the substitution earnings basis.
IUB_CO_ROW = {
    "unitid": 151351,
    "institution_name": "Indiana University-Bloomington",
    "cipcode": "52.01",
    "program_name": "Business/Commerce, General.",
    "cip_family_name": "Business, Management, Marketing",
    "earnings_1yr_median": 63371.0,
    "earnings_1yr_p25": 38515.0,
    "earnings_1yr_p75": 49674.0,
    "debt_median": 19500.0,
    "debt_to_earnings_annual": 0.3077,
    "cip_family_earnings_rank": 0.9558,
    "confidence_tier": "high",
}


def _make_server() -> FutureProofMCPServer:
    server = FutureProofMCPServer.__new__(FutureProofMCPServer)
    server.warehouse_path = "/tmp/fake"
    server.catalog_path = "/tmp/fake.db"
    server.grounding_docs_path = None
    server.server_name = "test"
    server.formatter = None
    server.anomaly_checker = None
    server.system_prompt = None
    server._catalog = MagicMock()
    # Pre-populate the lookup cache so we don't hit the filesystem.
    server._major_to_cip_cache = FAKE_LOOKUP
    return server


def _fake_query_simple(table_name, filters=None, columns=None, limit=None):
    """Mock dispatch for query_iceberg_simple across the 4 tables used.

    Returns (table, filters) → rows. The marketing SOCs 11-2021 and
    13-1161 get representative occupation/onet/ai rows; others return
    empty lists so the handler produces a sparse pentagon for them.
    """
    filters = filters or {}
    if table_name == CAREER_OUTCOMES_TABLE:
        if filters.get("unitid") == 151351 and filters.get("cipcode") == "52.01":
            return [IUB_CO_ROW]
        return []
    if table_name == "consumable.occupation_profiles":
        soc = filters.get("soc_code")
        if soc == "11-2021":
            return [
                {
                    "soc_code": "11-2021",
                    "occupation_title": "Marketing Managers",
                    "soc_major_group_name": "Management",
                    "median_annual_wage": 161030.0,
                    "wage_percentile_overall": 0.95,
                    "grw_score_rounded": 7,
                    "market_score_rounded": 8,
                    "growth_category": "Faster than average",
                    "employment_current": 400000,
                    "education_level_name": "Bachelor's degree",
                }
            ]
        if soc == "13-1161":
            return [
                {
                    "soc_code": "13-1161",
                    "occupation_title": "Market Research Analysts",
                    "soc_major_group_name": "Business and Financial Operations",
                    "median_annual_wage": 76950.0,
                    "wage_percentile_overall": 0.72,
                    "grw_score_rounded": 7,
                    "market_score_rounded": 8,
                    "growth_category": "Faster than average",
                    "employment_current": 900000,
                    "education_level_name": "Bachelor's degree",
                }
            ]
        return []
    if table_name == "consumable.onet_work_profiles":
        soc = filters.get("bls_soc_code")
        if soc == "11-2021":
            return [
                {
                    "bls_soc_code": "11-2021",
                    "primary_title": "Marketing Managers",
                    "hmn_score_rounded": 6,
                    "burnout_score_rounded": 6,
                    "top_5_activities": "[]",
                    "top_human_activities": "[]",
                    "burnout_drivers": "[]",
                }
            ]
        if soc == "13-1161":
            return [
                {
                    "bls_soc_code": "13-1161",
                    "primary_title": "Market Research Analysts",
                    "hmn_score_rounded": 3,
                    "burnout_score_rounded": 5,
                    "top_5_activities": "[]",
                    "top_human_activities": "[]",
                    "burnout_drivers": "[]",
                }
            ]
        return []
    if table_name == "consumable.ai_exposure":
        soc = filters.get("soc_code")
        if soc == "11-2021":
            return [
                {
                    "soc_code": "11-2021",
                    "stat_res": 3,
                    "boss_ai_score": 8,
                }
            ]
        if soc == "13-1161":
            return [
                {
                    "soc_code": "13-1161",
                    "stat_res": 2,
                    "boss_ai_score": 9,
                }
            ]
        return []
    return []


def _patch_substitution(server, cip4_socs: list[str]):
    """Patch the crosswalk + query_iceberg_simple for a substitution flow."""
    return (
        patch.object(
            server,
            "_fetch_crosswalk_socs",
            return_value=cip4_socs,
        ),
        patch.object(
            server,
            "query_iceberg_simple",
            side_effect=_fake_query_simple,
        ),
    )


class TestSubstitutionFires:
    """Substitution happens for a broad-CIP school + matched major."""

    def test_iub_marketing_substitution_fires(self):
        server = _make_server()
        xw_patch, q_patch = _patch_substitution(
            server, ["11-2021", "13-1161"]
        )
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        assert result["substitution_applied"] is True
        assert result["reported_cipcode"] == "52.01"
        assert result["substituted_cipcode"] == "52.14"
        assert result["row_count"] == 2
        socs = [r["soc_code"] for r in result["data"]]
        assert set(socs) == {"11-2021", "13-1161"}
        # All substituted rows use the substituted cipcode and the
        # school's broad-program earnings.
        for row in result["data"]:
            assert row["cipcode"] == "52.14"
            assert row["unitid"] == 151351
            assert row["earnings_1yr_median"] == 63371.0
            assert row["debt_to_earnings_annual"] == 0.3077
            assert row["match_quality"] == "substituted_cip"

    def test_no_substitution_when_major_omitted(self):
        """No student_major → standard path, no substitution."""
        server = _make_server()
        with patch.object(
            server,
            "query_iceberg_simple",
            return_value=[
                {
                    f: None
                    for f in (
                        "unitid",
                        "cipcode",
                        "soc_code",
                        "occupation_title",
                        "stats_available_count",
                    )
                }
                | {"stats_available_count": 5, "soc_code": "11-9021"}
            ],
        ):
            result = server._handle_get_career_paths(
                {"unitid": 151351, "cipcode": "52.01"}
            )
        assert result["substitution_applied"] is False
        assert "data_caveat" not in result

    def test_no_substitution_when_specific_cip(self):
        """ISU reports 52.14 directly → student_major is ignored."""
        server = _make_server()
        with patch.object(
            server,
            "query_iceberg_simple",
            return_value=[{"stats_available_count": 5, "soc_code": "11-2021"}],
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 145813,
                    "cipcode": "52.14",
                    "student_major": "Marketing",
                }
            )
        assert result["substitution_applied"] is False
        assert "substitution_note" in result
        assert "specific" in result["substitution_note"]


class TestAliasMatching:
    """Case-insensitive alias matching against major names + aliases."""

    def test_uppercase_marketing(self):
        server = _make_server()
        entry = server._find_major_intent("MARKETING")
        assert entry is not None
        assert entry["cip4"] == "52.14"

    def test_alias_mktg(self):
        server = _make_server()
        entry = server._find_major_intent("mktg")
        assert entry is not None
        assert entry["cip4"] == "52.14"

    def test_alias_phrase_marketing_management(self):
        server = _make_server()
        entry = server._find_major_intent("marketing management")
        assert entry is not None
        assert entry["cip4"] == "52.14"

    def test_unknown_major_returns_none(self):
        server = _make_server()
        assert server._find_major_intent("Underwater Basket Weaving") is None

    def test_empty_major_returns_none(self):
        server = _make_server()
        assert server._find_major_intent("") is None
        assert server._find_major_intent("   ") is None


class TestFamilyMismatchAndUnknown:
    """Invalid substitutions fall back to the standard path."""

    def test_family_mismatch_falls_back(self):
        """Student says 'Nursing' (51.xx) at a 52.01 school → standard path."""
        server = _make_server()
        standard_rows = [
            {"stats_available_count": 5, "soc_code": "11-9021"}
        ]
        with patch.object(
            server, "query_iceberg_simple", return_value=standard_rows
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Nursing",
                }
            )
        assert result["substitution_applied"] is False
        assert "substitution_note" in result
        assert "family" in result["substitution_note"]
        assert "data_caveat" not in result

    def test_unrecognized_major_falls_back(self):
        server = _make_server()
        standard_rows = [
            {"stats_available_count": 5, "soc_code": "11-9021"}
        ]
        with patch.object(
            server, "query_iceberg_simple", return_value=standard_rows
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Underwater Basket Weaving",
                }
            )
        assert result["substitution_applied"] is False
        assert "substitution_note" in result
        assert "Could not map" in result["substitution_note"]
        assert "data_caveat" not in result


class TestBroadCipDetection:
    def test_broad_cip_detection(self):
        assert FutureProofMCPServer._is_broad_cip("52.01") is True
        assert FutureProofMCPServer._is_broad_cip("52.0100") is True
        assert FutureProofMCPServer._is_broad_cip("13.01") is True
        assert FutureProofMCPServer._is_broad_cip("52.14") is False
        assert FutureProofMCPServer._is_broad_cip("52.0101") is False
        assert FutureProofMCPServer._is_broad_cip("52.02") is False

    def test_cip_family_extraction(self):
        assert FutureProofMCPServer._cip_family("52.01") == "52"
        assert FutureProofMCPServer._cip_family("51.38") == "51"
        assert FutureProofMCPServer._cip_family("52.1401") == "52"


class TestBlendedStats:
    """ERN and ROI match the Gold engine formula."""

    def test_ern_and_roi_match_engine_formula(self):
        """Blended ERN = round(1 + 9*(0.6*rank + 0.4*wpo)).

        With IU-B rank = 0.9558 and 13-1161 wpo = 0.72:
            raw = 0.6*0.9558 + 0.4*0.72 = 0.85348
            1 + 9*0.85348 = 8.68
            round half-up → 9
        ROI with dte = 0.3077 → piecewise linear from Gold engine.
        We just assert the values match the engine, not a specific int,
        to avoid duplicating the breakpoint table here.
        """
        from gold.futureproof_engine import compute_stat_ern, compute_stat_roi

        expected_ern = compute_stat_ern(0.9558, 0.72)
        expected_roi = compute_stat_roi(0.3077)

        server = _make_server()
        xw_patch, q_patch = _patch_substitution(server, ["13-1161"])
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        row = result["data"][0]
        assert row["stat_ern"] == expected_ern
        assert row["stat_roi"] == expected_roi

    def test_same_school_same_ern_roi_across_substitutions(self):
        """ERN/ROI depend only on school-level inputs + SOC wpo.

        Across two different student majors at the same school, the ROI
        for any given SOC remains identical (since ROI depends only on
        the school's debt-to-earnings ratio, not the SOC).
        """
        server = _make_server()

        def _all_missing(*a, **kw):
            # Return empty op/onet/ai but the IU-B CO row.
            return _fake_query_simple(*a, **kw)

        xw_patch, q_patch = _patch_substitution(server, ["13-1161"])
        with xw_patch, q_patch:
            r1 = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        xw_patch2, q_patch2 = _patch_substitution(server, ["13-1161"])
        with xw_patch2, q_patch2:
            r2 = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Accounting",
                }
            )
        assert r1["data"][0]["stat_roi"] == r2["data"][0]["stat_roi"]


class TestCaveatMetadata:
    def test_data_caveat_present_on_substituted(self):
        server = _make_server()
        xw_patch, q_patch = _patch_substitution(server, ["11-2021"])
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        caveat = result["data_caveat"]
        assert caveat["type"] == "blended_substitution"
        assert caveat["reported_cipcode"] == "52.01"
        assert caveat["substituted_cipcode"] == "52.14"
        assert caveat["substituted_program"] == "Marketing"
        assert caveat["earnings_specificity"] == "school_broad"
        assert caveat["career_path_specificity"] == "national_major_specific"
        assert "Marketing" in caveat["message"]

    def test_data_caveat_absent_on_standard(self):
        server = _make_server()
        with patch.object(
            server,
            "query_iceberg_simple",
            return_value=[{"stats_available_count": 5, "soc_code": "11-9021"}],
        ):
            result = server._handle_get_career_paths(
                {"unitid": 151351, "cipcode": "52.01"}
            )
        assert "data_caveat" not in result


class TestCanonicalCip4:
    """The 4-digit projection that Bug A's fix is built on.

    ``_canonical_cip4`` is called at every ``cipcode=`` filter site in
    ``futureproof_server.py``. If any of these cases regress, the
    substitution lookup silently returns zero rows for a padded-6-digit
    input again, which is exactly Bug A.
    """

    def test_strips_padding(self):
        # Bare 4-digit passes through unchanged (len == 5).
        assert FutureProofMCPServer._canonical_cip4("52.01") == "52.01"
        # Zero-padded 6-digit broad CIP → 4-digit prefix (the Bug A path).
        assert FutureProofMCPServer._canonical_cip4("52.0100") == "52.01"
        # Specific 6-digit → 4-digit prefix (standard-path normalization).
        assert FutureProofMCPServer._canonical_cip4("52.0101") == "52.01"
        # Specific leaf in a non-broad family → 4-digit prefix.
        assert FutureProofMCPServer._canonical_cip4("52.1401") == "52.14"
        # Already 4-digit in a non-broad family — identity.
        assert FutureProofMCPServer._canonical_cip4("52.14") == "52.14"
        # Empty input: early-return branch at the top of the helper.
        # If this ever returns anything other than "", the filter sites
        # would hand a truthy-but-garbage value to Iceberg and either
        # raise or silently return []. "" is the only safe outcome.
        assert FutureProofMCPServer._canonical_cip4("") == ""


class TestIntegrationLikePath:
    """Full ``_handle_get_career_paths`` exercises for the new CIP
    granularities the bugfix has to cover."""

    def test_padded_broad_cip_still_substitutes(self):
        """cipcode='52.0100' + Marketing at IU → same substituted payload
        as the bare '52.01' case. Every response site must canonicalize
        ``reported_cipcode`` to the 4-digit form so a future UI consumer
        sees the same value regardless of input granularity.
        """
        server = _make_server()
        xw_patch, q_patch = _patch_substitution(
            server, ["11-2021", "13-1161"]
        )
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.0100",  # padded broad — this is Bug A
                    "student_major": "Marketing",
                }
            )
        assert result["substitution_applied"] is True
        # The root canonicalizes the reported CIP — this is the signal
        # downstream UI consumers will branch on. If anything other than
        # "52.01" lands here, Bug A's "reported_cipcode echoes caller
        # input verbatim" regression is back.
        assert result["reported_cipcode"] == "52.01"
        # The caveat must agree with the root — dual-location fix.
        assert result["data_caveat"]["reported_cipcode"] == "52.01"
        # Substitution target unchanged.
        assert result["substituted_cipcode"] == "52.14"
        # Caveat type and row count unchanged from the bare-4-digit case.
        assert result["data_caveat"]["type"] == "blended_substitution"
        assert result["row_count"] == 2
        socs = [r["soc_code"] for r in result["data"]]
        assert set(socs) == {"11-2021", "13-1161"}
        for row in result["data"]:
            # Substituted rows continue to carry the specific substituted
            # CIP (52.14), not the broadened reported CIP.
            assert row["cipcode"] == "52.14"
            assert row["unitid"] == 151351
            # Blended earnings come from IU's 52.01 row — Bug A's
            # canonicalization lookup is what makes this possible. If
            # the lookup missed, err would have been returned and we'd
            # be looking at a ``data: None`` response instead.
            assert row["earnings_1yr_median"] == 63371.0

    def test_specific_six_digit_does_not_substitute(self):
        """cipcode='52.0101' is a SPECIFIC 6-digit CIP (Business/Commerce,
        General) — ``_is_broad_cip`` returns False. Substitution does NOT
        fire. The request falls through the standard path, which
        canonicalizes to '52.01' and then routes through the deterministic
        broadening fallback (``_fallback_broaden_cip``) because IU has no
        row at exactly 52.01 in ``program_career_paths``.

        The response must be shaped by the broadening fallback — caveat
        type 'cip_broadened', NOT 'blended_substitution'. This is the
        explicit design decision at §1 Success Criterion 4: widening
        ``_BROAD_CIP_PATTERN`` was rejected; specific-CIP inputs stay
        on the standard/broadening path.
        """
        server = _make_server()

        # Standard path → canonical_cipcode='52.01'. The exact-filter
        # query for cipcode='52.01' returns [], so the handler falls
        # through to _fallback_broaden_cip, which issues an
        # unfiltered-by-cipcode query for all rows at this unitid. We
        # return one row at '52.14' (family-match) so Attempt 3 fires
        # (family-wide match) and we land in the cip_broadened branch.
        #
        # NOTE: we explicitly DO NOT return a row at '52.01', because
        # the point of this test is that 52.0101 does NOT substitute
        # — it broadens. If we planted a 52.01 row the exact filter
        # would hit before the fallback ran.
        family_rows = [
            {
                "unitid": 151351,
                "cipcode": "52.14",
                "program_name": "Marketing",
                "soc_code": "11-2021",
                "occupation_title": "Marketing Managers",
                "stats_available_count": 5,
            }
        ]

        def _fake_query(table_name, filters=None, columns=None, limit=None):
            filters = filters or {}
            # Standard-path filter site: unitid + canonical cipcode.
            if (
                table_name == CAREER_PATHS_TABLE
                and filters.get("cipcode") == "52.01"
            ):
                # Empty — forces fallback.
                return []
            # _fallback_broaden_cip unfiltered-by-cipcode query: we
            # detect it by absence of the cipcode filter key.
            if (
                table_name == CAREER_PATHS_TABLE
                and "cipcode" not in filters
                and filters.get("unitid") == 151351
            ):
                return list(family_rows)
            return []

        with patch.object(
            server, "query_iceberg_simple", side_effect=_fake_query
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.0101",  # specific — NOT broad
                    "student_major": "Marketing",
                }
            )

        # Substitution did not fire — no blended_substitution caveat.
        # The broadening fallback sets substitution_applied=True but
        # the caveat type differentiates the two paths.
        assert result["substitution_applied"] is True, (
            "broadening fallback still toggles substitution_applied=True"
        )
        assert result["data_caveat"]["type"] == "cip_broadened", (
            "specific 6-digit CIP must NOT hit the blended_substitution "
            "path — widening _BROAD_CIP_PATTERN was rejected in Decision "
            "#1 Alt (b)"
        )
        # The root reported_cipcode must reflect the canonical form the
        # handler actually queried against (§4 L2202 — canonicalize at
        # the broadened-rows response site too).
        assert result["reported_cipcode"] == "52.01"


class TestStandardPath:
    """P1 coverage: the standard-path filter site canonicalizes too."""

    def test_padded_specific_cip_normalizes(self):
        """cipcode='52.1000' (HR padded to 6 digits) with no student_major
        returns IU's HR program_career_paths rows. Validates Bug A's fix
        at the standard-path filter site (the caller hands in a padded
        specific CIP; the filter must strip to '52.10' to hit IU's row).
        """
        server = _make_server()

        iu_hr_row = {
            "unitid": 151351,
            "cipcode": "52.10",
            "program_name": "Human Resources Management/Personnel Admin",
            "soc_code": "13-1071",
            "occupation_title": "Human Resources Specialists",
            "stats_available_count": 5,
        }

        def _fake_query(table_name, filters=None, columns=None, limit=None):
            filters = filters or {}
            # Standard path passes the canonicalized CIP ('52.10') — if
            # the fix regresses and hands in '52.1000' verbatim, this
            # branch never matches and we fall into the broadening
            # fallback instead. That would be the Bug A regression.
            if (
                table_name == CAREER_PATHS_TABLE
                and filters.get("cipcode") == "52.10"
            ):
                return [iu_hr_row]
            return []

        with patch.object(
            server, "query_iceberg_simple", side_effect=_fake_query
        ):
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.1000",  # padded specific — Bug A target
                }
            )

        assert result["substitution_applied"] is False, (
            "No substitution: student_major not provided and the school "
            "reports this program directly"
        )
        # The school's HR row comes back through the standard path.
        assert result["row_count"] == 1
        assert result["data"][0]["cipcode"] == "52.10"
        assert result["data"][0]["soc_code"] == "13-1071"


class TestErrorHandling:
    def test_missing_school_row_returns_null(self):
        """If the school's broad-CIP row is missing, substitution fails."""
        server = _make_server()
        empty_query = patch.object(
            server, "query_iceberg_simple", return_value=[]
        )
        xw_patch = patch.object(
            server, "_fetch_crosswalk_socs", return_value=["11-2021"]
        )
        with xw_patch, empty_query:
            result = server._handle_get_career_paths(
                {
                    "unitid": 999999,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        assert result["data"] is None
        assert "cannot substitute" in result["message"]

    def test_empty_crosswalk_returns_null(self):
        server = _make_server()
        xw_patch = patch.object(
            server, "_fetch_crosswalk_socs", return_value=[]
        )
        q_patch = patch.object(
            server, "query_iceberg_simple", side_effect=_fake_query_simple
        )
        with xw_patch, q_patch:
            result = server._handle_get_career_paths(
                {
                    "unitid": 151351,
                    "cipcode": "52.01",
                    "student_major": "Marketing",
                }
            )
        assert result["data"] is None
        assert "crosswalk" in result["message"].lower()
