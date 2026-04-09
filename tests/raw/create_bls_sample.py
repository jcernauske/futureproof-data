"""Generate a sample BLS OOH XLSX file for testing."""

from pathlib import Path

import openpyxl


def create_sample():
    """Create tests/raw/bls_ooh_sample.xlsx with realistic BLS occupation data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Table 1.7"

    # Row 1: title row (should be skipped by the ingestor)
    ws.append(["Table 1.7 Occupational projections, 2023-33, and worker characteristics"])

    # Row 2: blank row
    ws.append([])

    # Row 3: header row
    headers = [
        "2023 National Employment Matrix title",
        "2023 National Employment Matrix code",
        "Employment, 2023",
        "Employment, 2033",
        "Employment change, numeric, 2023-33",
        "Employment change, percent, 2023-33",
        "Occupational openings, 2023-33 annual average",
        "Median annual wage, 2024",
        "Typical education needed for entry",
        "Education code",
        "Work experience in a related occupation",
        "Work experience code",
        "Typical on-the-job training needed to attain competency in the occupation",
        "Training code",
    ]
    ws.append(headers)

    # Data rows -- employment figures are in thousands
    data = [
        # Normal detailed occupations
        [
            "Software developers",
            "15-1252",
            1795.5,
            2057.2,
            261.7,
            14.6,
            153.9,
            "$130,160",
            "Bachelor's degree",
            6,
            "None",
            1,
            "None",
            1,
        ],
        [
            "Registered nurses",
            "29-1141",
            3175.4,
            3337.1,
            161.7,
            5.1,
            193.1,
            "$86,070",
            "Bachelor's degree",
            6,
            "None",
            1,
            "None",
            1,
        ],
        [
            "General and operations managers",
            "11-1021",
            3052.4,
            3210.6,
            158.2,
            5.2,
            326.9,
            "$101,280",
            "Bachelor's degree",
            6,
            "5 years or more",
            3,
            "None",
            1,
        ],
        [
            "Accountants and auditors",
            "13-2011",
            1538.4,
            1597.3,
            58.9,
            3.8,
            130.0,
            "$79,880",
            "Bachelor's degree",
            6,
            "None",
            1,
            "None",
            1,
        ],
        # Top-coded wage
        [
            "Surgeons, except ophthalmologists",
            "29-1248",
            36.6,
            38.5,
            1.9,
            5.2,
            2.1,
            ">=239,200",
            "Doctoral or professional degree",
            8,
            "None",
            1,
            "Internship/residency",
            3,
        ],
        # N/A wage
        [
            "Legislators",
            "11-1031",
            44.4,
            44.8,
            0.4,
            0.9,
            6.8,
            "N/A",
            "Bachelor's degree",
            6,
            "5 years or more",
            3,
            "None",
            1,
        ],
        # More normal occupations
        [
            "Electricians",
            "47-2111",
            761.5,
            849.7,
            88.2,
            11.6,
            73.5,
            "$61,590",
            "High school diploma or equivalent",
            3,
            "None",
            1,
            "Apprenticeship",
            4,
        ],
        [
            "Market research analysts and marketing specialists",
            "13-1161",
            965.0,
            1073.7,
            108.7,
            11.3,
            94.0,
            "$74,680",
            "Bachelor's degree",
            6,
            "None",
            1,
            "None",
            1,
        ],
        [
            "Home health and personal care aides",
            "31-1120",
            3747.5,
            4373.1,
            625.6,
            16.7,
            684.1,
            "$33,530",
            "High school diploma or equivalent",
            3,
            "None",
            1,
            "Short-term on-the-job training",
            2,
        ],
        [
            "Financial managers",
            "11-3031",
            757.2,
            824.2,
            67.0,
            8.8,
            72.3,
            "$156,100",
            "Bachelor's degree",
            6,
            "5 years or more",
            3,
            "None",
            1,
        ],
        # Summary row -- should be filtered out (SOC ends in 0000)
        [
            "Management occupations",
            "11-0000",
            11079.2,
            11612.4,
            533.2,
            4.8,
            1165.5,
            "$116,880",
            "See summary",
            0,
            "See summary",
            0,
            "See summary",
            0,
        ],
    ]

    for row in data:
        ws.append(row)

    output_path = Path(__file__).parent / "bls_ooh_sample.xlsx"
    wb.save(output_path)
    print(f"Created {output_path}")


if __name__ == "__main__":
    create_sample()
