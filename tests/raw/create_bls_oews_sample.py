"""Generate a sample BLS OEWS XLSX file for testing.

The sample mirrors the real OEWS national workbook layout — a couple of
metadata rows on top, then a header row, then OCC_GROUP rollups mixed with
``detailed`` rows.  The ingestor must filter to ``detailed`` only.
"""

from pathlib import Path

import openpyxl


def create_sample() -> None:
    """Write tests/raw/bls_oews_sample.xlsx with a minimal but realistic layout."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "National_dataset"

    # Row 1: title row (would-be metadata)
    ws.append(
        [
            "May 2024 National Occupational Employment and Wage Estimates",
        ]
    )
    # Row 2: blank spacer
    ws.append([])

    # Row 3: header row.  Real OEWS columns; we only declare the ones the
    # ingestor cares about (the rest are ignored by COLUMN_MAP).
    headers = [
        "OCC_CODE",
        "OCC_TITLE",
        "OCC_GROUP",
        "TOT_EMP",
        "H_MEDIAN",
        "A_PCT10",
        "A_PCT25",
        "A_MEDIAN",
        "A_PCT75",
        "A_PCT90",
        "A_MEAN",
    ]
    ws.append(headers)

    # Body rows -- mix of detailed + summary rollups + edge cases.
    rows = [
        # major-group rollup; must be filtered out
        [
            "11-0000",
            "Management Occupations",
            "major",
            10000000,
            "*",
            45000,
            70000,
            105000,
            155000,
            225000,
            120000,
        ],
        # broad-group rollup; must be filtered out
        [
            "11-1000",
            "Top Executives",
            "broad",
            3000000,
            "*",
            55000,
            85000,
            130000,
            190000,
            "#",
            150000,
        ],
        # Chief Executives -- detailed; p90 top-coded
        [
            "11-1011",
            "Chief Executives",
            "detailed",
            211230,
            58.50,
            74000,
            131000,
            206000,
            "#",
            "#",
            246440,
        ],
        # Software Developers -- detailed; clean monotonic distribution
        [
            "15-1252",
            "Software Developers",
            "detailed",
            1656880,
            62.50,
            78000,
            98000,
            130000,
            168000,
            204000,
            138110,
        ],
        # Registered Nurses -- detailed; commas in TOT_EMP
        [
            "29-1141",
            "Registered Nurses",
            "detailed",
            "3,175,390",
            41.40,
            61000,
            75000,
            86000,
            101000,
            132000,
            93600,
        ],
        # Nurse Practitioners -- detailed; second high earner
        [
            "29-1171",
            "Nurse Practitioners",
            "detailed",
            280140,
            60.50,
            89000,
            105000,
            126000,
            148000,
            172000,
            128490,
        ],
        # Maids and Housekeeping Cleaners -- detailed; fully suppressed wages
        [
            "37-2012",
            "Maids and Housekeeping Cleaners",
            "detailed",
            900000,
            "*",
            "*",
            "*",
            "*",
            "*",
            "*",
            "*",
        ],
        # minor-group rollup; must be filtered out
        [
            "29-1100",
            "Health Diagnosing and Treating Practitioners",
            "minor",
            5000000,
            "*",
            55000,
            75000,
            105000,
            150000,
            200000,
            115000,
        ],
        # Total all-occupations rollup; must be filtered out
        [
            "00-0000",
            "All Occupations",
            "total",
            150000000,
            "*",
            25000,
            35000,
            50000,
            80000,
            115000,
            65000,
        ],
    ]

    for row in rows:
        ws.append(row)

    output_path = Path(__file__).parent / "bls_oews_sample.xlsx"
    wb.save(output_path)
    print(f"Created {output_path}")


if __name__ == "__main__":
    create_sample()
