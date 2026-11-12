# Golden Set Expected Value Derivations (`eval/golden_set_derivation.md`)

This document provides the independent pandas expressions, SQL queries, and hand calculations used to derive the expected figures for custom cases in `eval/golden_set.csv` (as well as the full-period reconciliation case `R01`), computed directly from `data/store_daily_clean.csv`.

---

## 1. Custom Case `C01` (`typo` — Pune footfall on `2026-05-16`)
* **Question**: `"What was Punee's footfall on 2026-05-16?"`
* **Fuzzy Store Resolution**: `SequenceMatcher(None, "punee", "pune").ratio() = 8 / 9 = 0.8889 >= 0.7` -> Resolves to `Pune`.
* **Pandas Expression**:
    import pandas as pd
    df = pd.read_csv("data/store_daily_clean.csv")
    val = df.loc[(df["store"] == "Pune") & (df["date"] == "2026-05-16"), "footfall"].iloc[0]
    print(f"{val:.2f}")
* **SQL Equivalent**: `SELECT footfall FROM store_daily_clean WHERE store = 'Pune' AND date = '2026-05-16';`
* **Hand Verification from `store_daily_clean.csv`**: On `2026-05-16`, `Pune` (`S02`) has `revenue_inr = 671332.65` and `footfall = 1692.0` (`671332.65 / 1692.0 = 396.7687 -> 396.77`, matching the Part A check row `revenue_per_footfall = 396.77`).
* **Formatted Agent Output Value**: `1692.00` (footfall formatted to 2 decimal places).

---

## 2. Custom Case `C02` (`synonym` — Bengaluru visitors/footfall on `2026-06-10`)
* **Question**: `"What were Bengaluru's visitors on 2026-06-10?"`
* **Synonym Resolution**: `visitors` -> `footfall`.
* **Pandas Expression**:
    import pandas as pd
    df = pd.read_csv("data/store_daily_clean.csv")
    val = df.loc[(df["store"] == "Bengaluru") & (df["date"] == "2026-06-10"), "footfall"].iloc[0]
    print(f"{val:.2f}")
* **SQL Equivalent**: `SELECT footfall FROM store_daily_clean WHERE store = 'Bengaluru' AND date = '2026-06-10';`
* **Hand Verification from Part A Cleaning Log (`analysis/cleaning_log.csv`)**: In `data/store_daily.csv`, `Bengaluru` (`S04`, day offset `70` = `2026-06-10`) was one of the 4 originally missing footfall rows and was imputed via `median_impute` with Bengaluru's store median footfall of `2065.0`.
* **Formatted Agent Output Value**: `2065.00`.

---

## 3. Custom Case `C03` (`synonym` — Ahmedabad sales/revenue on `2026-05-26`)
* **Question**: `"What was Ahmedabad's sales on 2026-05-26?"`
* **Synonym Resolution**: `sales` -> `revenue_inr`.
* **Pandas Expression**:
    import pandas as pd
    df = pd.read_csv("data/store_daily_clean.csv")
    val = df.loc[(df["store"] == "Ahmedabad") & (df["date"] == "2026-05-26"), "revenue_inr"].iloc[0]
    print(f"INR {val:.2f}")
* **SQL Equivalent**: `SELECT revenue_inr FROM store_daily_clean WHERE store = 'Ahmedabad' AND date = '2026-05-26';`
* **Hand Verification from `store_daily_clean.csv`**: Row for `S05` (`Ahmedabad`) on `2026-05-26` (day offset `55`, where footfall was capped from `9800` to `2281.38` while leaving `revenue_inr` untouched per Part A Task 3.v) has `revenue_inr = 806538.94`.
* **Formatted Agent Output Value**: `INR 806538.94`.

---

## 4. Custom Case `C10` (Session `s26` Setup Lookup for `C11`–`C14` Context Isolation Tests)
* **Question**: `"What was Pune's revenue on 2026-05-15?"`
* **Purpose**: Establishes `store = 'Pune'`, `metric = 'revenue_inr'`, and `date = '2026-05-15'` in session `s26` immediately before testing `unresolved_store` (`C11`, `C12`) and `unresolved_date` (`C13`, `C14`) in the same session `s26`.
* **Pandas Expression**:
    import pandas as pd
    df = pd.read_csv("data/store_daily_clean.csv")
    val = df.loc[(df["store"] == "Pune") & (df["date"] == "2026-05-15"), "revenue_inr"].iloc[0]
    print(f"INR {val:.2f}")
* **Value**: `INR 623845.00`.

---

## 5. Reconciliation Case `R01` (Full 90-Day Store Mean Daily Revenue Ranking)
* **Question**: `"Which store had the lowest average revenue between 2026-04-01 and 2026-06-29?"`
* **SQL Expression**:
    SELECT store,
           COUNT(revenue_inr) AS cnt,
           SUM(CAST(ROUND(revenue_inr * 100) AS INTEGER)) AS sum_cents
    FROM store_daily_clean
    WHERE date BETWEEN '2026-04-01' AND '2026-06-29'
    GROUP BY store;
* **Exact Integer-Cent Division (`ROUND_HALF_UP` to 2 decimals)**:
  * **Pune**: `sum_cents = 5727226950 / 90` cents = `INR 636358.55`
  * **Ahmedabad**: `sum_cents = 7043826330 / 90` cents = `INR 782647.37`
  * **Hyderabad**: `sum_cents = 8039097090 / 90` cents = `INR 893233.01`
  * **Bengaluru**: `sum_cents = 8379591120 / 90` cents = `INR 931065.68`
  * **Mumbai**: `sum_cents = 9579344400 / 90` cents = `INR 1064371.60`
  * Matches the `mean_daily_revenue` column of `analysis/findings.md` identically.
