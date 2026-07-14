"""
clean_cerp_completions.py

Cleans CERP's IPEDS-derived national degree completions datasets
(computing and engineering) and extracts Bachelor's-level completions
for Computer Science (CIP 11.x) and Engineering (CIP 14.x), summed
across gender and race/ethnicity.

NOTE: This is DEGREE COMPLETIONS data (degrees awarded per year), not
enrollment. It is a different metric than the ISU and NSC datasets
used elsewhere in this project and is kept in a separate output file
rather than merged into the same enrollment time series.

The "computing" source file includes multiple CIP families beyond just
Computer Science (e.g. CIP 10.x, Communications Technologies) -- this
script filters specifically to CIP codes starting with "11." to stay
consistent with how Computer Science is defined elsewhere in this
project (matching NSC's CIP 11 category).

Usage:
    python clean_cerp_completions.py <computing_csv> <engineering_csv>

Requires: pandas
"""

import sys
import os
import pandas as pd
from project_logger import log_event

AWARD_LEVEL_FILTER = "bachelor"  # matched case-insensitively, substring


def clean_cerp_file(filepath: str, cip_prefix: str, category_name: str) -> pd.DataFrame:
    # Auto-detect delimiter (tab or comma) rather than assuming, since
    # the file extension alone doesn't guarantee which was used.
    df = pd.read_csv(filepath, sep=None, engine="python")

    # Filter to Bachelor's-level awards only
    df = df[df["awardLevel"].astype(str).str.lower().str.contains(AWARD_LEVEL_FILTER, na=False)]

    # Filter to the target CIP family (e.g. "11." for Computer Science,
    # "14." for Engineering) -- cipCode includes the code AND a text
    # description in one field (e.g. "11.0101 Computer and Information
    # Sciences, General"), so match on the numeric prefix.
    df = df[df["cipCode"].astype(str).str.startswith(cip_prefix)]

    if df.empty:
        log_event(f"No rows matched award level '{AWARD_LEVEL_FILTER}' and "
                  f"CIP prefix '{cip_prefix}' in {filepath}.", level="WARNING")
        return pd.DataFrame()

    # Identify year columns (numeric-looking column headers)
    year_cols = [c for c in df.columns if str(c).isdigit()]

    # Sum across all CIP codes within the family, all genders, and all
    # race/ethnicity categories, to get one national total per year.
    yearly_totals = df[year_cols].sum(numeric_only=True)

    records = [
        {"Category": category_name, "Year": int(year), "Completions": int(count)}
        for year, count in yearly_totals.items()
    ]
    return pd.DataFrame(records)


def main():
    if len(sys.argv) != 3:
        print("Usage: python clean_cerp_completions.py <computing_csv> <engineering_csv>")
        sys.exit(1)

    computing_path = sys.argv[1]
    engineering_path = sys.argv[2]

    log_event(f"Starting CERP cleaning run: {computing_path}, {engineering_path}")

    cs_df = clean_cerp_file(computing_path, "11.", "Computer Science")
    eng_df = clean_cerp_file(engineering_path, "14.", "Engineering")

    combined = pd.concat([cs_df, eng_df], ignore_index=True)
    combined = combined.sort_values(["Year", "Category"])

    print(combined.to_string(index=False))

    cleaned_dir = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
    os.makedirs(cleaned_dir, exist_ok=True)
    out_path = os.path.join(cleaned_dir, "CERP_completions_combined.csv")
    combined.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    log_event(f"Finished CERP cleaning: {len(combined)} rows saved to {out_path}.")


if __name__ == "__main__":
    main()