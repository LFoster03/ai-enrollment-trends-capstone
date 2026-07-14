"""
clean_nsc_national.py

Cleans the NSC Research Center's "Final Fall Enrollment Trends" Data
Appendix and extracts national undergraduate 4-year enrollment totals
for Computer Science (CIP 11) and Engineering (CIP 14), summed across
all states.

The appendix file conveniently contains multiple years side-by-side
as columns (e.g. the Fall 2025 appendix covers 2020-2025 in one file),
so in most cases a single downloaded file covers several years at once
-- check the "Sheet names" / column headers of whichever appendix you
download to see its actual year range.

Fall 2019 has no NSC Data Appendix at all (only a PDF report existed
that year). Those figures were extracted manually from the PDF earlier
in this project and are hardcoded in FALL_2019_MANUAL below, sourced
from Table 11 (four-year institutions) of CTEE_Report_Fall_2019.pdf.

Usage:
    python clean_nsc_national.py "data\\raw\\NSC_Fall2025_Appendix.xlsx"

Requires: pandas, openpyxl
"""

import sys
import os
import pandas as pd
from project_logger import log_event

SHEET_NAME = "Major Field Family"
AWARD_LEVEL_FILTER = "Undergraduate 4-year"
TARGET_CIPS = {
    "11": "Computer Science",
    "14": "Engineering",
}

# Manually extracted from CTEE_Report_Fall_2019.pdf, Table 11
# (four-year institutions), since no downloadable Data Appendix exists
# for Fall 2019.
FALL_2019_MANUAL = {
    "Computer Science": 474573,
    "Engineering": 595142,
}


def clean_nsc_file(filepath: str) -> pd.DataFrame:
    full = pd.read_excel(filepath, sheet_name=SHEET_NAME, header=1)

    # Year columns are the numeric-looking column headers (2020, 2021,
    # etc.) -- detect them dynamically rather than hardcoding, since
    # different appendix downloads cover different year ranges.
    year_cols = [c for c in full.columns if isinstance(c, int)]

    target = full[
        (full["Award Level and Institution Type"] == AWARD_LEVEL_FILTER) &
        (full["Major Field Family (2-digit CIP)"].isin(TARGET_CIPS.keys()))
    ].copy()

    # "*" marks a suppressed (small) value in NSC's data. Coerce to
    # numeric so these become NaN and are excluded from the sum,
    # rather than crashing the aggregation.
    for col in year_cols:
        target[col] = pd.to_numeric(target[col], errors="coerce")

    national_totals = (
        target.groupby("Major Field Family (2-digit CIP)")[year_cols]
        .sum(min_count=1)
    )

    # Reshape into long format: one row per (Category, Year, Enrollment)
    records = []
    for cip, category in TARGET_CIPS.items():
        if cip not in national_totals.index:
            continue
        for year in year_cols:
            records.append({
                "Category": category,
                "Semester": f"Fall {year}",
                "Headcount": national_totals.loc[cip, year],
            })

    return pd.DataFrame(records)


def main():
    if len(sys.argv) != 2:
        print("Usage: python clean_nsc_national.py <path_to_appendix.xlsx>")
        sys.exit(1)

    filepath = sys.argv[1]
    log_event(f"Starting NSC cleaning run for {filepath}")

    df = clean_nsc_file(filepath)

    # Add the manually-extracted Fall 2019 figures, since no Data
    # Appendix exists for that year.
    manual_rows = pd.DataFrame([
        {"Category": category, "Semester": "Fall 2019", "Headcount": headcount}
        for category, headcount in FALL_2019_MANUAL.items()
    ])
    df = pd.concat([manual_rows, df], ignore_index=True)

    # NSC's underlying totals are non-integer estimates; round to
    # whole people for readability.
    df["Headcount"] = df["Headcount"].round(0).astype("Int64")

    # Sort chronologically
    df["_year"] = df["Semester"].str.extract(r"(\d{4})").astype(int)
    df = df.sort_values(["_year", "Category"]).drop(columns="_year")

    print(df.to_string(index=False))

    cleaned_dir = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
    os.makedirs(cleaned_dir, exist_ok=True)
    out_path = os.path.join(cleaned_dir, "NSC_national_combined.csv")
    df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    log_event(f"Finished NSC cleaning: {len(df)} rows (including manually "
              f"entered Fall 2019) saved to {out_path}.")


if __name__ == "__main__":
    main()