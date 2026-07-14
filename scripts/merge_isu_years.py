"""
merge_isu_years.py

Combines all per-semester ISU cleaned CSVs in data/cleaned/ into two
single time-series files:

  - ISU_combined_granular.csv  (all Primary + Control program rows,
                                 all semesters, one table)
  - ISU_combined_broad.csv     (Engineering + Computer Science broad
                                 totals, all semesters, one table)

Run this AFTER you've generated individual semester files with
clean_isu_enrollment.py for every Fall 2019-2025 semester.

Usage:
    python merge_isu_years.py
"""

import os
import glob
import pandas as pd
from project_logger import log_event

CLEANED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")

# A rough chronological order to sort semesters correctly, since
# alphabetical sorting would put "Fall 2020" before "Fall 2019" is
# fine, but mixing Fall/Spring later would not sort correctly by
# string alone. Extend this if Spring/Summer semesters are added later.
SEMESTER_ORDER = [
    "Fall 2019", "Fall 2020", "Fall 2021", "Fall 2022",
    "Fall 2023", "Fall 2024", "Fall 2025",
]


def sort_key(semester_label: str) -> int:
    try:
        return SEMESTER_ORDER.index(semester_label)
    except ValueError:
        # Unknown semester label -- push to the end rather than crash
        return len(SEMESTER_ORDER)


def merge_granular():
    all_matches = glob.glob(os.path.join(CLEANED_DIR, "ISU_*_granular.csv"))
    # Exclude this script's own output file, so re-running the merge
    # never picks up a previously-combined file as an input (which
    # would double every row).
    files = sorted(f for f in all_matches if "combined" not in os.path.basename(f).lower())
    if not files:
        log_event("No granular CSVs found in data/cleaned/. Nothing to merge.", level="WARNING")
        return None

    dfs = [pd.read_csv(f) for f in files]
    combined = pd.concat(dfs, ignore_index=True)
    combined["_sort"] = combined["Semester"].apply(sort_key)
    combined = combined.sort_values(["_sort", "Tier", "Matched_Category"]).drop(columns="_sort")

    out_path = os.path.join(CLEANED_DIR, "ISU_combined_granular.csv")
    combined.to_csv(out_path, index=False)
    log_event(f"Merged {len(files)} granular files into {out_path} "
              f"({len(combined)} total rows).")
    return combined


def merge_broad():
    all_matches = glob.glob(os.path.join(CLEANED_DIR, "ISU_*_broad.csv"))
    files = sorted(f for f in all_matches if "combined" not in os.path.basename(f).lower())
    if not files:
        log_event("No broad CSVs found in data/cleaned/. Nothing to merge.", level="WARNING")
        return None

    dfs = [pd.read_csv(f) for f in files]
    combined = pd.concat(dfs, ignore_index=True)
    combined["_sort"] = combined["Semester"].apply(sort_key)
    combined = combined.sort_values(["_sort", "Category"]).drop(columns="_sort")

    out_path = os.path.join(CLEANED_DIR, "ISU_combined_broad.csv")
    combined.to_csv(out_path, index=False)
    log_event(f"Merged {len(files)} broad files into {out_path} "
              f"({len(combined)} total rows).")
    return combined


def main():
    log_event("Starting merge of all ISU cleaned semester files.")

    granular = merge_granular()
    broad = merge_broad()

    if granular is not None:
        print("=== Combined granular data (first/last few rows) ===")
        print(granular.head(10).to_string(index=False))
        print("...")
        print(granular.tail(5).to_string(index=False))
        semesters_found = sorted(granular["Semester"].unique(), key=sort_key)
        print(f"\nSemesters included: {semesters_found}")

    if broad is not None:
        print("\n=== Combined broad totals (all semesters) ===")
        print(broad.to_string(index=False))

    log_event("Finished merging ISU cleaned files.")


if __name__ == "__main__":
    main()