# Golden Set Expected Value Derivations (`eval/golden_set_derivation.md`)

This document provides the independent pandas expressions, SQL queries, and hand calculations used to derive the expected figures for custom cases in `eval/golden_set.csv` (as well as the full-period reconciliation case `R01`), computed directly from `data/store_daily_clean.csv`.

---

## 1. Custom Case `C01` (`typo` — Pune footfall on `2026-05-16`)
* **Question**: `"What was Punee's footfall on 2026-05-16?"`
* **Fuzzy Store Resolution**: `SequenceMatcher(None, "punee", "pune").ratio() = 8 / 9 = 0.8889 >= 0.7` -> Resolves to `Pune`.
* **Pandas Expression**:
  ```python
  import pandas as pd
  df = pd.read_csv("data/store_daily_clean.csv")
  val = df.loc[(df["store"] == "Pune") & (df["date"] == "2026-05-16"), "footfall"].iloc[0]
  print(f"{val:.2f}")