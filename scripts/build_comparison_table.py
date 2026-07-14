"""
build_comparison_table.py

Builds the final comparison view for this project by combining:
  - ISU_combined_broad.csv       (ISU Engineering + CS enrollment)
  - NSC_national_combined.csv    (National Engineering + CS enrollment)

into a single wide table, aligned by semester, with both raw
headcounts and Fall-2019-indexed values (2019 = 100) so ISU's trend
can be visually compared against the national trend regardless of
scale.

CERP completions data is intentionally NOT merged into this table,
since it measures a different thing (degrees awarded, not enrollment)
on a different time axis (calendar year 2011-2024, not Fall semester).
It is instead summarized separately, alongside the CERP Pulse Survey
context, in a second output file.

Usage:
    python build_comparison_table.py

Requires: pandas
"""

import os
import pandas as pd
from project_logger import log_event

CLEANED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")


def load_isu_broad():
    path = os.path.join(CLEANED_DIR, "ISU_combined_broad.csv")
    df = pd.read_csv(path)
    df["Category"] = df["Category"].str.extract(r"^(Engineering|Computer Science)", expand=False)
    df["Year"] = df["Semester"].str.extract(r"(\d{4})", expand=False).astype(int)
    return df[["Year", "Category", "Headcount"]].rename(columns={"Headcount": "ISU"})


def load_nsc_national():
    path = os.path.join(CLEANED_DIR, "NSC_national_combined.csv")
    df = pd.read_csv(path)
    df["Year"] = df["Semester"].str.extract(r"(\d{4})", expand=False).astype(int)
    return df[["Year", "Category", "Headcount"]].rename(columns={"Headcount": "National"})


def add_indexed_columns(wide_df: pd.DataFrame, value_cols: list, base_year: int = 2019) -> pd.DataFrame:
    """Add columns indexed to a specific base_year (default 2019) = 100,
    computed separately per Category. Anchoring to a specific year
    (rather than whichever row happens to be first) matters here since
    CERP's data starts in 2011, not 2019 -- indexing to "the first row"
    would silently use the wrong baseline for that dataset."""
    wide_df = wide_df.sort_values(["Category", "Year"]).copy()

    for col in value_cols:
        indexed_col = f"{col}_indexed_{base_year}"

        def compute_index(group, col=col):
            base_rows = group.loc[group["Year"] == base_year, col]
            if base_rows.empty or pd.isna(base_rows.iloc[0]) or base_rows.iloc[0] == 0:
                return pd.Series([None] * len(group), index=group.index)
            base_value = base_rows.iloc[0]
            return (group[col] / base_value) * 100

        wide_df[indexed_col] = wide_df.groupby("Category", group_keys=False).apply(
            lambda g, col=col: compute_index(g, col)
        )
    return wide_df


def build_enrollment_comparison():
    isu = load_isu_broad()
    nsc = load_nsc_national()

    merged = pd.merge(isu, nsc, on=["Year", "Category"], how="outer")
    merged = add_indexed_columns(merged, ["ISU", "National"])
    merged = merged.sort_values(["Category", "Year"])

    out_path = os.path.join(CLEANED_DIR, "comparison_ISU_vs_National_enrollment.csv")
    merged.to_csv(out_path, index=False)
    log_event(f"Built enrollment comparison table: {len(merged)} rows -> {out_path}")
    return merged


def build_cerp_summary():
    """Load CERP completions and add an indexed view for reference,
    kept as a separate output since it's a different metric/timeframe
    than the enrollment comparison above."""
    path = os.path.join(CLEANED_DIR, "CERP_completions_combined.csv")
    if not os.path.exists(path):
        log_event("CERP_completions_combined.csv not found -- skipping CERP summary.", level="WARNING")
        return None

    df = pd.read_csv(path)
    df = df.rename(columns={"Completions": "CERP_Completions"})
    df = add_indexed_columns(df.rename(columns={"CERP_Completions": "CERP"}), ["CERP"])
    df = df.rename(columns={"CERP": "CERP_Completions", "CERP_indexed_2019": "CERP_Completions_indexed_2019"})

    out_path = os.path.join(CLEANED_DIR, "comparison_CERP_completions.csv")
    df.to_csv(out_path, index=False)
    log_event(f"Built CERP completions summary table: {len(df)} rows -> {out_path}")
    return df


def main():
    log_event("Starting final comparison table build.")

    enrollment = build_enrollment_comparison()
    print("=== ISU vs. National Enrollment (indexed to Fall 2019 = 100) ===")
    print(enrollment.to_string(index=False))

    cerp = build_cerp_summary()
    if cerp is not None:
        print("\n=== CERP Bachelor's Completions (indexed to 2019 = 100) ===")
        print(cerp.to_string(index=False))

    log_event("Finished building comparison tables.")


if __name__ == "__main__":
    main()