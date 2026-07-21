"""
train_test_model.py

Trains a simple linear regression model per (Category, Source) pair
on the ISU-vs-National enrollment comparison data, using EARLIER years
as the training set and the MOST RECENT years as a held-out test set.

Why linear regression, and why this train/test split:
This project has only 7 data points per series (Fall 2019-2025), which
is far too small for complex models -- a Random Forest or neural
network would overfit meaninglessly on this little data. Linear
regression is used here not as a high-accuracy forecasting tool, but
as a way to quantitatively test the project's central hypothesis: if
a model trained ONLY on pre-2024 data (assuming enrollment continues
its earlier trend) predicts 2024-2025 accurately, that supports a
"steady trend" story. If it predicts poorly -- especially in one
direction (over-predicting) -- that is quantitative evidence of a real
structural break in the trend, consistent with something (e.g. AI
adoption) disrupting the pattern that existed before.

Usage:
    python train_test_model.py

Requires: pandas, scikit-learn
    pip install pandas scikit-learn --break-system-packages
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from project_logger import log_event

CLEANED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
TEST_YEARS = [2024, 2025]


def load_data() -> pd.DataFrame:
    path = os.path.join(CLEANED_DIR, "comparison_ISU_vs_National_enrollment.csv")
    return pd.read_csv(path)


def build_actual_vs_predicted_chart(df: pd.DataFrame, out_path: str):
    """Builds a 2x2 grid of actual-vs-predicted charts, one per
    (Category, Source) combination, each showing the full actual
    trend line alongside the model's predicted line (fit on
    pre-2024 data only) and a shaded region marking the held-out
    test period."""
    categories = df["Category"].unique()
    sources = ["ISU", "National"]

    fig, axes = plt.subplots(len(categories), len(sources), figsize=(12, 9))

    for i, category in enumerate(categories):
        for j, source in enumerate(sources):
            ax = axes[i, j]
            sub = df[df["Category"] == category][["Year", source]].dropna()
            sub = sub.rename(columns={source: "Value"}).sort_values("Year")

            train = sub[~sub["Year"].isin(TEST_YEARS)]
            if len(train) < 2:
                continue

            model = LinearRegression().fit(train[["Year"]], train["Value"])
            pred_line = model.predict(sub[["Year"]])

            ax.plot(sub["Year"], sub["Value"], marker="o", label="Actual", linewidth=2, color="tab:blue")
            ax.plot(sub["Year"], pred_line, linestyle="--", label="Predicted (trained pre-2024)", color="tab:red")
            ax.axvspan(2023.5, sub["Year"].max() + 0.5, alpha=0.1, color="gray")
            ax.set_title(f"{category} -- {source}")
            ax.set_xlabel("Year")
            ax.set_ylabel("Enrollment")
            ax.legend(fontsize=8)
            ax.grid(alpha=0.3)

    plt.suptitle("Actual vs. Predicted Enrollment (Linear Regression, Trained on Pre-2024 Data)", fontsize=13)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def train_and_evaluate(df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for category in df["Category"].unique():
        for source in ["ISU", "National"]:
            sub = df[df["Category"] == category][["Year", source]].dropna()
            sub = sub.rename(columns={source: "Value"})

            train = sub[~sub["Year"].isin(TEST_YEARS)]
            test = sub[sub["Year"].isin(TEST_YEARS)]

            if len(train) < 2 or test.empty:
                continue

            X_train = train[["Year"]].values
            y_train = train["Value"].values
            X_test = test[["Year"]].values
            y_test = test["Value"].values

            model = LinearRegression()
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))

            for year, actual, predicted in zip(test["Year"], y_test, y_pred):
                pct_error = ((predicted - actual) / actual) * 100
                results.append({
                    "Category": category,
                    "Source": source,
                    "Test_Year": int(year),
                    "Actual": round(actual, 1),
                    "Predicted": round(predicted, 1),
                    "Error": round(predicted - actual, 1),
                    "Pct_Error": round(pct_error, 2),
                    "Train_MAE": round(mae, 1),
                    "Train_RMSE": round(rmse, 1),
                    "Model_Slope_per_Year": round(model.coef_[0], 2),
                })

    return pd.DataFrame(results)


def main():
    log_event("Starting train/test linear regression modeling.")

    df = load_data()
    results = train_and_evaluate(df)

    print("=== Train/Test Results (trained on years excluding 2024-2025) ===")
    print(results.to_string(index=False))

    out_path = os.path.join(CLEANED_DIR, "model_train_test_results.csv")
    results.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    chart_path = os.path.join(CLEANED_DIR, "model_actual_vs_predicted.png")
    build_actual_vs_predicted_chart(df, chart_path)
    print(f"Saved: {chart_path}")

    log_event(f"Finished train/test modeling. {len(results)} test predictions saved to {out_path}. "
              f"Chart saved to {chart_path}.")


if __name__ == "__main__":
    main()