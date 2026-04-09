"""Create a sample CIP-SOC crosswalk XLSX for testing.

Run this script to generate tests/raw/cip_soc_crosswalk_sample.xlsx.
"""

from pathlib import Path

import openpyxl

SAMPLE_PATH = Path(__file__).parent / "cip_soc_crosswalk_sample.xlsx"

# Sample data matching the real XLSX structure
ROWS = [
    # (CIP2020Code, CIP2020Title, SOC2018Code, SOC2018Title)
    ("52.0201", "Business Administration and Management, General.", "11-1021", "General and Operations Managers"),
    ("52.0201", "Business Administration and Management, General.", "11-2021", "Marketing Managers"),
    ("52.0201", "Business Administration and Management, General.", "13-1111", "Management Analysts"),
    ("11.0101", "Computer and Information Sciences, General.", "15-1252", "Software Developers"),
    ("11.0101", "Computer and Information Sciences, General.", "15-1211", "Computer Systems Analysts"),
    ("51.1201", "Medicine.", "29-1211", "Anesthesiologists"),
    ("51.1201", "Medicine.", "29-1216", "General Internal Medicine Physicians"),
    ("26.0101", "Biology/Biological Sciences, General.", "19-1042", "Medical Scientists, Except Epidemiologists"),
    ("26.0101", "Biology/Biological Sciences, General.", "25-1042", "Biological Science Teachers, Postsecondary"),
    ("13.0101", "Education, General.", "25-2031", "Secondary School Teachers, Except Special and Career/Technical Education"),
    # "No match" sentinel rows (should be filtered in Silver)
    ("36.0115", "Card Games and Card Dealing.", "99-9999", "NO MATCH"),
    ("33.0199", "Citizenship Activities, Other.", "99-9999", "NO MATCH"),
    # Row with a float CIP code (simulates openpyxl numeric parsing)
    # This will be added as a numeric value in the XLSX
]

# Additional rows with CIP as float values
FLOAT_CIP_ROWS = [
    (14.0101, "Engineering, General.", "17-2199", "Engineers, All Other"),
    (1.0000, "Agriculture, General.", "45-2011", "Agricultural Inspectors"),
]


def main():
    wb = openpyxl.Workbook()

    # Create CIP-SOC sheet (primary sheet)
    ws = wb.active
    ws.title = "CIP-SOC"

    # Header row
    ws.append(["CIP2020Code", "CIP2020Title", "SOC2018Code", "SOC2018Title"])

    # String CIP rows
    for row in ROWS:
        ws.append(list(row))

    # Float CIP rows -- write as numeric values to simulate openpyxl behavior
    for cip_float, cip_title, soc_code, soc_title in FLOAT_CIP_ROWS:
        ws.append([cip_float, cip_title, soc_code, soc_title])

    # Add a File Guide sheet (mimics real workbook structure)
    ws2 = wb.create_sheet("File Guide")
    ws2.append(["CIP 2020 to SOC 2018 Crosswalk"])
    ws2.append(["National Center for Education Statistics"])

    wb.save(SAMPLE_PATH)
    print(f"Created {SAMPLE_PATH} with {len(ROWS) + len(FLOAT_CIP_ROWS)} data rows")


if __name__ == "__main__":
    main()
