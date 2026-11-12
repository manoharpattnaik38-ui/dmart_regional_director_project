
import numpy as np
import pandas as pd


def main():
    clean_df = pd.read_csv("data/store_daily_clean.csv")
    raw_df = pd.read_csv("data/store_daily.csv")

    stores_order = ["Ahmedabad", "Bengaluru", "Hyderabad", "Mumbai", "Pune"]
    rows = []

    for store in stores_order:
        sub = clean_df[clean_df["store"] == store]
        rows.append({
            "Store": store,
            "mean_daily_revenue": round(sub["revenue_inr"].mean(), 2),
            "mean_footfall": round(sub["footfall"].mean(), 2),
            "mean_stockout_hours": round(sub["stockout_hours"].mean(), 2),
            "revenue_per_footfall": round(sub["revenue_inr"].sum() / sub["footfall"].sum(), 2),
            "mean_achievement_pct": round(sub["achievement_pct"].mean(), 2),
            "poor_days": int((sub["performance_band"] == "Poor").sum()),
        })

    rows.append({
        "Store": "All stores",
        "mean_daily_revenue": round(clean_df["revenue_inr"].mean(), 2),
        "mean_footfall": round(clean_df["footfall"].mean(), 2),
        "mean_stockout_hours": round(clean_df["stockout_hours"].mean(), 2),
        "revenue_per_footfall": round(clean_df["revenue_inr"].sum() / clean_df["footfall"].sum(), 2),
        "mean_achievement_pct": round(clean_df["achievement_pct"].mean(), 2),
        "poor_days": int((clean_df["performance_band"] == "Poor").sum()),
    })

    summary_df = pd.DataFrame(rows)
    print("=== Store Summary Table ===")
    print(summary_df.to_string(index=False))

    # Correlations on cleaned data (450 rows)
    corr_all_rev_so = np.corrcoef(clean_df["revenue_inr"], clean_df["stockout_hours"])[0, 1]
    corr_all_rev_ff = np.corrcoef(clean_df["revenue_inr"], clean_df["footfall"])[0, 1]

    # Correlations on Pune rows only (90 rows)
    pune_df = clean_df[clean_df["store"] == "Pune"]
    corr_pune_rev_so = np.corrcoef(pune_df["revenue_inr"], pune_df["stockout_hours"])[0, 1]
    corr_pune_rev_ff = np.corrcoef(pune_df["revenue_inr"], pune_df["footfall"])[0, 1]

    # Before-cleaning correlation on deduplicated raw data with non-missing footfall (446 rows)
    raw_dedup = raw_df.drop_duplicates(keep="first")
    raw_valid = raw_dedup[raw_dedup["footfall"].notna()].copy()
    corr_raw_rev_ff = np.corrcoef(raw_valid["revenue_inr"], raw_valid["footfall"].astype(float))[0, 1]

    print("\n=== Pearson Correlations ===")
    print(f"All rows (n=450) revenue vs stockout_hours : {corr_all_rev_so:.3f}")
    print(f"All rows (n=450) revenue vs footfall       : {corr_all_rev_ff:.3f}")
    print(f"Pune rows (n=90) revenue vs stockout_hours : {corr_pune_rev_so:.3f}")
    print(f"Pune rows (n=90) revenue vs footfall       : {corr_pune_rev_ff:.3f}")
    print(f"Raw deduplicated non-missing (n={len(raw_valid)}) revenue vs footfall: {corr_raw_rev_ff:.3f}")


if __name__ == "__main__":
    main()
