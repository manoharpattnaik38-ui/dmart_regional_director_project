"""Clean store_daily.csv in strict sequence, write cleaning_log.csv and store_daily_clean.csv."""
import os
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pandas as pd


def round_half_up(val, decimals=2):
    """Round half-up to the specified number of decimal places."""
    d = Decimal(str(val))
    fmt = "0." + "0" * decimals if decimals > 0 else "0"
    return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))


def format_val(val):
    """Format footfall values cleanly for logging and output."""
    if pd.isna(val) or val == "":
        return ""
    f = float(val)
    if f.is_integer():
        return str(int(f))
    return f"{round_half_up(f, 2):.2f}"


def main():
    os.makedirs("analysis", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    df = pd.read_csv("data/store_daily.csv")

    # Step i: Remove exact duplicate rows, keeping the first occurrence
    df = df.drop_duplicates(keep="first").copy().reset_index(drop=True)

    cleaning_log = []

    # Step ii: Treat any negative footfall as a data error: set it to missing
    for idx, row in df.iterrows():
        val = row["footfall"]
        if pd.notna(val) and float(val) < 0:
            cleaning_log.append({
                "store": row["store"],
                "date": row["date"],
                "old_footfall": int(round(float(val))),
                "new_footfall": "",
                "rule": "negative_to_missing",
            })
            df.loc[idx, "footfall"] = np.nan

    # Step iii: Per-store Q1/Q3 bounds (linear interpolation on non-missing values) and IQR capping
    for store in df["store"].unique():
        store_mask = df["store"] == store
        valid_ff = df.loc[store_mask & df["footfall"].notna(), "footfall"].astype(float)
        q1 = np.percentile(valid_ff, 25, method="linear")
        q3 = np.percentile(valid_ff, 75, method="linear")
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        for idx in df[store_mask & df["footfall"].notna()].index:
            val = float(df.loc[idx, "footfall"])
            if val < lower_bound:
                capped = round_half_up(lower_bound, 2)
                cleaning_log.append({
                    "store": store,
                    "date": df.loc[idx, "date"],
                    "old_footfall": int(round(val)),
                    "new_footfall": f"{capped:.2f}",
                    "rule": "iqr_cap",
                })
                df.loc[idx, "footfall"] = capped
            elif val > upper_bound:
                capped = round_half_up(upper_bound, 2)
                cleaning_log.append({
                    "store": store,
                    "date": df.loc[idx, "date"],
                    "old_footfall": int(round(val)),
                    "new_footfall": f"{capped:.2f}",
                    "rule": "iqr_cap",
                })
                df.loc[idx, "footfall"] = capped

    # Step iv: Per-store median imputation on remaining missing footfall values
    for store in df["store"].unique():
        store_mask = df["store"] == store
        valid_ff = df.loc[store_mask & df["footfall"].notna(), "footfall"].astype(float)
        median_val = float(np.median(valid_ff))
        for idx in df[store_mask & df["footfall"].isna()].index:
            cleaning_log.append({
                "store": store,
                "date": df.loc[idx, "date"],
                "old_footfall": "",
                "new_footfall": round_half_up(median_val, 2),
                "rule": "median_impute",
            })
            df.loc[idx, "footfall"] = round_half_up(median_val, 2)

    # Save cleaning_log.csv
    log_df = pd.DataFrame(
        cleaning_log,
        columns=["store", "date", "old_footfall", "new_footfall", "rule"]
    )
    log_df.to_csv("analysis/cleaning_log.csv", index=False)

    # Step v & Task 4: Leave revenue_inr and other base columns untouched; add 6 feature columns
    df["revenue_per_footfall"] = (df["revenue_inr"] / df["footfall"]).apply(lambda x: round_half_up(x, 2))
    df["marketing_efficiency"] = (df["revenue_inr"] / df["marketing_spend_inr"]).apply(lambda x: round_half_up(x, 2))
    df["achievement_pct"] = (df["revenue_inr"] / df["daily_target_inr"] * 100.0).apply(lambda x: round_half_up(x, 2))
    df["shortfall_inr"] = (df["daily_target_inr"] - df["revenue_inr"]).apply(lambda x: round_half_up(x, 2))

    dt_col = pd.to_datetime(df["date"])
    df["weekend_flag"] = np.where(dt_col.dt.dayofweek >= 5, "Yes", "No")

    def assign_band(ach):
        if ach >= 100.0:
            return "Excellent"
        elif ach >= 75.0:
            return "Good"
        return "Poor"

    df["performance_band"] = df["achievement_pct"].apply(assign_band)

    df.to_csv("data/store_daily_clean.csv", index=False)
    print(f"Cleaned dataset written: {df.shape[0]} rows, {df.shape[1]} columns.")
    print(f"Cleaning log written: {len(log_df)} entries.")


if __name__ == "__main__":
    main()