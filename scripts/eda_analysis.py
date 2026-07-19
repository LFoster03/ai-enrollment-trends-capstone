"""
eda_analysis.py

Performs exploratory data analysis on the final ISU-vs-National
enrollment comparison table, and saves the results as reusable output
files (rather than one-off analysis) so the analysis can be
regenerated any time the underlying data changes.

Techniques used:
  - Descriptive statistics (mean, std, min, max) per category
  - Year-over-year percent change (ISU and National)
  - Correlation between ISU and National trends, per category
  - Indexed trend visualization (Fall 2019 = 100), ISU vs. National

Usage:
    python eda_analysis.py

Requires: pandas, matplotlib
    pip install pandas matplotlib --break-system-packages
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from project_logger import log_event

CLEANED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")


def load_comparison_data() -> pd.DataFrame:
    path = os.path.join(CLEANED_DIR, "comparison_ISU_vs_National_enrollment.csv")
    return pd.read_csv(path)


def compute_descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for cat in df["Category"].unique():
        sub = df[df["Category"] == cat]
        for source in ["ISU", "National"]:
            desc = sub[source].describe()
            records.append({
                "Category": cat,
                "Source": source,
                "count": int(desc["count"]),
                "mean": round(desc["mean"], 2),
                "std": round(desc["std"], 2),
                "min": desc["min"],
                "25%": desc["25%"],
                "50%": desc["50%"],
                "75%": desc["75%"],
                "max": desc["max"],
            })
    return pd.DataFrame(records)


def compute_yoy_change(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["Category", "Year"]).copy()
    df["ISU_pct_change"] = (df.groupby("Category")["ISU"].pct_change() * 100).round(2)
    df["National_pct_change"] = (df.groupby("Category")["National"].pct_change() * 100).round(2)
    return df[["Year", "Category", "ISU", "ISU_pct_change", "National", "National_pct_change"]]


def compute_correlations(df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for cat in df["Category"].unique():
        sub = df[df["Category"] == cat]
        corr = sub["ISU"].corr(sub["National"])
        records.append({"Category": cat, "Correlation_ISU_vs_National": round(corr, 3)})
    return pd.DataFrame(records)


def build_trend_chart(df: pd.DataFrame, out_path: str):
    categories = df["Category"].unique()
    fig, axes = plt.subplots(1, len(categories), figsize=(6 * len(categories), 5))
    if len(categories) == 1:
        axes = [axes]

    for ax, cat in zip(axes, categories):
        sub = df[df["Category"] == cat].sort_values("Year")
        isu_idx = sub["ISU"] / sub["ISU"].iloc[0] * 100
        nat_idx = sub["National"] / sub["National"].iloc[0] * 100
        ax.plot(sub["Year"], isu_idx, marker="o", label="ISU", linewidth=2)
        ax.plot(sub["Year"], nat_idx, marker="s", label="National", linewidth=2)
        ax.axvline(2022, color="gray", linestyle="--", alpha=0.6, label="ChatGPT launch (late 2022)")
        ax.set_title(cat)
        ax.set_xlabel("Year")
        ax.set_ylabel("Enrollment (Indexed, 2019=100)")
        ax.legend()
        ax.grid(alpha=0.3)

    plt.suptitle("ISU vs. National Enrollment Trends, Indexed to Fall 2019 = 100", fontsize=13)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main():
    log_event("Starting EDA analysis on comparison_ISU_vs_National_enrollment.csv")

    df = load_comparison_data()

    # 1. Descriptive statistics
    desc_stats = compute_descriptive_stats(df)
    print("=== Descriptive Statistics ===")
    print(desc_stats.to_string())
    desc_out = os.path.join(OUTPUT_DIR, "eda_descriptive_stats.csv")
    desc_stats.to_csv(desc_out, index=False)

    # 2. Year-over-year percent change
    yoy = compute_yoy_change(df)
    print("\n=== Year-over-Year Percent Change ===")
    print(yoy.to_string(index=False))
    yoy_out = os.path.join(OUTPUT_DIR, "eda_yoy_change.csv")
    yoy.to_csv(yoy_out, index=False)

    # 3. Correlation
    corr = compute_correlations(df)
    print("\n=== Correlation: ISU vs. National ===")
    print(corr.to_string(index=False))
    corr_out = os.path.join(OUTPUT_DIR, "eda_correlations.csv")
    corr.to_csv(corr_out, index=False)

    # 4. Trend chart
    chart_out = os.path.join(OUTPUT_DIR, "eda_trend_comparison.png")
    build_trend_chart(df, chart_out)
    print(f"\nSaved chart: {chart_out}")

    log_event(
        f"Finished EDA analysis. Saved {desc_out}, {yoy_out}, {corr_out}, and {chart_out}."
    )


if __name__ == "__main__":
    main()