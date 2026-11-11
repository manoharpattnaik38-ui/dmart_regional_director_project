# Data Quality Report: `data/store_daily.csv`

## 1. Raw Dataset Inspection

* **Shape**: 453 rows by 9 columns (`453 x 9`)
* **Exact duplicate rows**: 3 exact duplicate rows appended at the end of the file:
  * `S01` (Mumbai) on `2026-05-11`
  * `S03` (Hyderabad) on `2026-05-31`
  * `S05` (Ahmedabad) on `2026-04-16`
* **Footfall range (raw)**:
  * **Minimum**: `-150` (Hyderabad, `2026-04-21`)
  * **Maximum**: `9800` (Ahmedabad, `2026-05-26`)

### Column Data Types and Null Counts

| Column | Data Type (pandas 2 / pandas 3) | Null Count |
| :--- | :--- | :--- |
| `date` | `object` / `str` | 0 |
| `store_id` | `object` / `str` | 0 |
| `store` | `object` / `str` | 0 |
| `footfall` | `float64` | 4 |
| `revenue_inr` | `float64` | 0 |
| `daily_target_inr` | `int64` | 0 |
| `marketing_spend_inr` | `int64` | 0 |
| `stockout_hours` | `float64` | 0 |
| `discount_pct` | `float64` | 0 |

The 4 missing (`null`) values in the raw `footfall` column occur at:
1. `Pune` (`S02`) on `2026-04-12`
2. `Pune` (`S02`) on `2026-05-17`
3. `Mumbai` (`S01`) on `2026-04-30`
4. `Bengaluru` (`S04`) on `2026-06-10`

---

## 2. Per-Store Footfall Quartiles and IQR Bounds

Computed after removing the 3 exact duplicate rows (leaving 450 rows, 90 per store) and treating the 1 negative footfall value (`-150` at Hyderabad on `2026-04-21`) as missing, using linear interpolation (`np.percentile(..., method="linear")` / `df.describe()`) over non-missing values:

| Store | Non-Missing Count | Q1 (25th Percentile) | Q3 (75th Percentile) | IQR (`Q3 - Q1`) | Lower Bound (`Q1 - 1.5 * IQR`) | Upper Bound (`Q3 + 1.5 * IQR`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ahmedabad** | 90 | 1844.50 | 2019.25 | 174.75 | 1582.375 (`1582.38`) | 2281.375 (`2281.38`) |
| **Bengaluru** | 89 | 1952.00 | 2211.00 | 259.00 | 1563.50 | 2599.50 |
| **Hyderabad** | 89 | 2053.00 | 2356.00 | 303.00 | 1598.50 | 2810.50 |
| **Mumbai** | 89 | 2246.00 | 2542.00 | 296.00 | 1802.00 | 2986.00 |
| **Pune** | 88 | 1434.00 | 1593.50 | 159.50 | 1194.75 | 1832.75 |

### Rows Outside the Per-Store IQR Bounds

Exactly **2 rows** fall outside their store's `[Lower Bound, Upper Bound]` interval:
1. **Mumbai (`S01`) on `2026-04-09`**: `footfall = 6100` (exceeds Mumbai's upper bound of `2986.00`; capped at `2986.00`).
2. **Ahmedabad (`S05`) on `2026-05-26`**: `footfall = 9800` (exceeds Ahmedabad's upper bound of `2281.375`; capped at `2281.38`).

---

## 3. Decisions

### 1. Exact Duplicate Rows (`drop_duplicates(keep="first")`)
* **What we did**: Removed the 3 exact duplicate rows at the end of the dataset (`Mumbai 2026-05-11`, `Hyderabad 2026-05-31`, `Ahmedabad 2026-04-16`), keeping the first occurrence of each `(store_id, date)` record so every store has exactly 90 daily observations from `2026-04-01` to `2026-06-29`.
* **Why that choice rather than the alternative**: Keeping duplicate records double-counts specific days in store-level sums, means, and quantile calculations, biasing the store averages and distorting time-series length across stores. Deleting both occurrences would create artificial gaps in the 90-day calendar.
* **What the raw file still contains**: `data/store_daily.csv` remains unmodified on disk with all 453 rows, including the 3 trailing duplicate rows at lines 452–454.

### 2. Negative Footfall Values (`negative_to_missing`)
* **What we did**: Treated Hyderabad's footfall of `-150` on `2026-04-21` as an impossible sensor/entry error and converted it to missing (`NaN`) prior to computing IQR bounds and store medians.
* **Why that choice rather than the alternative**: Customer footfall is a non-negative physical count; a negative number is impossible. Leaving `-150` in the data or capping it at the lower IQR bound (`1598.50`) would treat a corrupted data entry as if it were a genuine low-traffic day, distorting both quartiles and the revenue-footfall correlation (`0.548` raw vs `0.918` cleaned). Taking the absolute value (`+150`) would still be an arbitrary, unverified number far below Hyderabad's operational range. Converting it to missing allows it to be imputed cleanly via Hyderabad's store median (`2216.0`).
* **What the raw file still contains**: `data/store_daily.csv` still holds `-150` in the `footfall` column for `S03` (`Hyderabad`) on `2026-04-21`.

### 3. Extreme High Values (`iqr_cap`)
* **What we did**: Computed per-store `Q1 - 1.5 * IQR` and `Q3 + 1.5 * IQR` bounds on deduplicated, non-missing, non-negative footfall values and capped the two extreme values—Mumbai (`6100` on `2026-04-09`) and Ahmedabad (`9800` on `2026-05-26`)—at their respective store upper bounds (`2986.00` and `2281.38`, rounded half-up to 2 decimals).
* **Why that choice rather than the alternative (why cap not delete)**: Deleting the entire row would discard valid, untouched financial and operational measurements (`revenue_inr`, `marketing_spend_inr`, `stockout_hours`, `discount_pct`) for those dates and break the complete 90-day panel structure required by downstream SQL comparisons and date lookups. Capping (Winsorizing) at the store-specific upper IQR bound preserves the observation as a genuine busy day while preventing extreme counter spikes from skewing store mean footfall, `revenue_per_footfall`, and Pearson correlation coefficients.
* **What the raw file still contains**: `data/store_daily.csv` still holds `6100` for `S01` (`Mumbai`, `2026-04-09`) and `9800` for `S05` (`Ahmedabad`, `2026-05-26`).

### 4. Missing Footfall Values (`median_impute`)
* **What we did**: Filled the 5 missing footfall entries (4 originally blank plus 1 converted from `-150`) using each store's own post-capping median footfall: Mumbai `2386.0` (`2026-04-30`), Pune `1509.5` (`2026-04-12` and `2026-05-17`), Hyderabad `2216.0` (`2026-04-21`), and Bengaluru `2065.0` (`2026-06-10`).
* **Why that choice rather than the alternative (why not zero, why store median not mean or all-store median)**:
  * *Why not zero*: The stores were open and generated full daily revenue on those 5 dates (e.g., Pune generated `INR 601205.23` on `2026-04-12`); setting footfall to `0` is factually false, causes division-by-zero in `revenue_per_footfall`, and artificially depresses store average footfall.
  * *Why store-specific median rather than all-store median/mean*: Footfall scales differ structurally across stores (Pune's baseline is ~1,518 visitors/day whereas Mumbai's is ~2,391 visitors/day). Imputing an all-store average (~2,024) into Pune would inflate Pune's footfall by ~33% on imputed days and obscure the true store-level footfall gap.
  * *Why median rather than mean*: The median is robust to skewness and capped tail values at the upper boundary, providing a more representative central value for typical daily store traffic.
* **What the raw file still contains**: `data/store_daily.csv` still contains empty strings (`""`) for footfall in the 4 originally missing rows (`S02` on `2026-04-12` and `2026-05-17`, `S01` on `2026-04-30`, `S04` on `2026-06-10`) and `-150` for `S03` on `2026-04-21`.