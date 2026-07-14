"""
clean_isu_enrollment.py

Cleans an ISU Registrar "Enrollment by Major or Department" Excel file
and extracts headcount (Grand Total) for target programs, organized
into three tiers:

  1. PRIMARY_PROGRAMS   - the AI-adjacent majors central to the hypothesis
  2. CONTROL_PROGRAMS   - unrelated majors used as a comparison baseline
  3. Broad totals        - college-level "Engineering Total" (pulled
                            directly from the file's own subtotal row)
                            and a summed "Computer Science Total" (since
                            CS has no subtotal row of its own within the
                            Liberal Arts and Sciences college) -- these
                            are the only granularity level that lines up
                            with NSC/CERP's national CIP-family data.

Usage:
    python clean_isu_enrollment.py "Enrollment by Major or Department F25 Excel.xlsx" "Fall 2025"

Requires: pandas, openpyxl
    pip install pandas openpyxl --break-system-packages
"""

import sys
import os
import pandas as pd
from project_logger import log_event

# ---------------------------------------------------------------
# TIER 1: AI-adjacent majors central to the hypothesis.
# Matching is case-insensitive "contains", so partial names are
# fine (e.g. "Computer Science" matches both the B.A. and B.S. rows).
# ---------------------------------------------------------------
PRIMARY_PROGRAMS = [
    "Computer Science",
    "Software Engineering",
    "Electrical Engineering",
    "Cyber Security Engineering",
    "Computer Engineering",
]

# ---------------------------------------------------------------
# TIER 2: Control-group majors, unrelated to AI, used to check
# whether any observed shift is specific to AI-adjacent fields or
# just a general engineering-wide trend.
# ---------------------------------------------------------------
CONTROL_PROGRAMS = [
    "Mechanical Engineering",
    "Civil Engineering",
]

ALL_TARGET_PROGRAMS = PRIMARY_PROGRAMS + CONTROL_PROGRAMS

# The exact text of the college-level Engineering subtotal row, used
# for the broad, NSC/CERP-comparable Engineering total.
ENGINEERING_TOTAL_ROW = "Engineering Total"


def find_header_row(raw_df: pd.DataFrame) -> int:
    """Find the row index that contains the column headers.

    Looks for a cell that is exactly "College" (case-insensitive,
    whitespace-trimmed). This is more robust than matching "Program
    of Study" directly, since that header text has been observed to
    contain an embedded line break in some files (similar to how
    "Grand Total" appears as "Grand\\nTotal" in the raw cell)."""
    for i, row in raw_df.iterrows():
        for cell in row:
            if isinstance(cell, str) and cell.strip().lower() == "college":
                return i
    raise ValueError("Could not find the header row (looked for a 'College' "
                      "cell). Run inspect_file.py on this file and check "
                      "the header rows manually.")


def tier_for(program_name: str) -> str:
    # Exclude rows that represent something other than a student's
    # primary declared major -- these use the same program name text
    # but refer to a different category of student, and including
    # them causes double-counting (Additional Major) or mixes in
    # students who haven't formally declared (Pre-Major) or aren't
    # degree-seeking (Non-Degree, Undeclared).
    exclusions = ["additional major", "pre-major", "non-degree", "undeclared"]
    lowered = program_name.lower()
    if any(exclusion in lowered for exclusion in exclusions):
        return None

    for target in PRIMARY_PROGRAMS:
        if target.lower() in program_name.lower():
            return "Primary (AI-adjacent)"
    for target in CONTROL_PROGRAMS:
        if target.lower() in program_name.lower():
            return "Control Group"
    return None


def clean_isu_file(filepath: str, semester_label: str, sheet_name: str = "UG"):
    # Load without assuming a header row, since the real header is
    # buried a few rows down under a title block. Target the "UG"
    # sheet specifically -- the workbook has multiple sheets (Total,
    # UG, VM, Grad), and the detailed Program of Study table only
    # exists on the UG (undergraduate) sheet.
    raw = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    header_row_idx = find_header_row(raw)

    # "Program of Study" is column index 1; College is column index 0.
    # Grand Total is the LAST column in the sheet.
    program_col = 1
    total_col = raw.shape[1] - 1

    college_col = 0

    records = []
    engineering_total = None
    cs_running_total = 0
    cs_rows_found = False

    for i in range(header_row_idx + 1, len(raw)):
        college_name = raw.iat[i, college_col]
        program_name = raw.iat[i, program_col]
        total_value = raw.iat[i, total_col]

        # College-level subtotal rows (e.g. "Engineering Total",
        # "Grand Total") have their label in the COLLEGE column, with
        # Program of Study left blank. Check for these first, before
        # the blank-Program-of-Study check below would otherwise skip
        # them entirely.
        if pd.notna(college_name):
            normalized_college = " ".join(str(college_name).split()).lower()
            if normalized_college == "engineering total":
                engineering_total = total_value
                continue
            if normalized_college.endswith("total"):
                # Any other college subtotal row (Business Total,
                # Grand Total, etc.) -- not needed, skip.
                continue

        if pd.isna(program_name):
            continue

        program_name = str(program_name).strip()

        matched_tier = tier_for(program_name)
        if matched_tier is None:
            continue

        matched_category = next(
            (t for t in ALL_TARGET_PROGRAMS if t.lower() in program_name.lower()),
            None
        )

        records.append({
            "Program": program_name,
            "Matched_Category": matched_category,
            "Tier": matched_tier,
            "Semester": semester_label,
            "Headcount": total_value,
        })

        # Track a running sum of all Computer Science rows (B.A. + B.S.)
        # to build the broad CS total, since no subtotal row exists for
        # CS alone within the Liberal Arts and Sciences college.
        if "computer science" in program_name.lower() and pd.notna(total_value):
            cs_running_total += total_value
            cs_rows_found = True

    granular_df = pd.DataFrame(records)

    if not granular_df.empty:
        # Some programs are jointly offered across multiple colleges
        # (e.g. Software Engineering appears once under Engineering
        # and once under Liberal Arts and Sciences in earlier report
        # years) and so can appear as more than one row for the same
        # category in the same semester. Sum these into a single
        # headcount per category per semester rather than leaving
        # them as separate, easily-misread rows. The list of distinct
        # source program name(s) is preserved for transparency.
        granular_df = (
            granular_df
            .groupby(["Matched_Category", "Tier", "Semester"], as_index=False)
            .agg(
                Headcount=("Headcount", "sum"),
                Source_Programs=("Program", lambda p: "; ".join(sorted(set(p)))),
            )
        )

    broad_totals = pd.DataFrame([
        {
            "Category": "Engineering (broad, college total)",
            "Semester": semester_label,
            "Headcount": engineering_total,
        },
        {
            "Category": "Computer Science (broad, B.A.+B.S. summed)",
            "Semester": semester_label,
            "Headcount": cs_running_total if cs_rows_found else None,
        },
    ])

    return granular_df, broad_totals


def main():
    if len(sys.argv) != 3:
        print("Usage: python clean_isu_enrollment.py <path_to_xlsx> <semester_label>")
        print('Example: python clean_isu_enrollment.py "F25.xlsx" "Fall 2025"')
        sys.exit(1)

    filepath = sys.argv[1]
    semester_label = sys.argv[2]

    log_event(f"Starting cleaning run for {semester_label} ({filepath})")

    granular_df, broad_df = clean_isu_file(filepath, semester_label)

    if granular_df.empty:
        log_event(f"No matching programs found for {semester_label}. "
                   f"Check PRIMARY_PROGRAMS / CONTROL_PROGRAMS.", level="WARNING")
        return

    print("=== Granular (Tier 1: Primary + Tier 2: Control) ===")
    print(granular_df.to_string(index=False))

    print("\n=== Broad totals (for NSC/CERP national comparison) ===")
    print(broad_df.to_string(index=False))

    # Save directly into data/cleaned/, relative to this script's
    # location in /scripts/, so output lands in the right place
    # regardless of which folder the command is run from.
    cleaned_dir = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
    os.makedirs(cleaned_dir, exist_ok=True)

    granular_out = os.path.join(cleaned_dir, f"ISU_{semester_label.replace(' ', '_')}_granular.csv")
    broad_out = os.path.join(cleaned_dir, f"ISU_{semester_label.replace(' ', '_')}_broad.csv")
    granular_df.to_csv(granular_out, index=False)
    broad_df.to_csv(broad_out, index=False)
    print(f"\nSaved:\n  {granular_out}\n  {broad_out}")

    n_primary = (granular_df["Tier"] == "Primary (AI-adjacent)").sum()
    n_control = (granular_df["Tier"] == "Control Group").sum()
    log_event(
        f"Finished {semester_label}: {n_primary} primary rows, "
        f"{n_control} control rows matched. Saved {granular_out} and {broad_out}."
    )


if __name__ == "__main__":
    main()