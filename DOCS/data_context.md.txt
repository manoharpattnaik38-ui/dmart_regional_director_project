# Data Context and Schema Specification

## 1. Overview of Datasets and Relationships

The assistant operates over three local CSV datasets stored in `data/` (and loaded into a local SQLite database for multi-row aggregations) covering five DMart stores: **Mumbai (`S01`)**, **Pune (`S02`)**, **Hyderabad (`S03`)**, **Bengaluru (`S04`)**, and **Ahmedabad (`S05`)**.

* **Relationship Between Datasets**: All three datasets share the exact same five stores and are linked by the store name column `store` (`Mumbai`, `Pune`, `Hyderabad`, `Bengaluru`, `Ahmedabad`) as well as the canonical identifier `store_id` (`S01` through `S05`). Additionally, `store_daily_clean.csv` and `feedback.csv` share the ISO calendar `date` domain (`2026-04-01` to `2026-06-29`), whereas `inventory.csv` is a static point-in-time inventory snapshot with no `date` column.

---

## 2. Dataset 1: `data/store_daily_clean.csv`

* **Row Count**: `450` rows (90 daily rows per store across 5 stores).
* **Date Range**: `2026-04-01` to `2026-06-29` inclusive (90 calendar days). The system reference date is `AS_OF_DATE = 2026-06-30`, making `yesterday` resolve to `2026-06-29`.

### Columns and Types (`15` Columns)

| Column Name | Data Type (pandas / SQLite) | Governance Role | Description |
| :--- | :--- | :--- | :--- |
| `date` | `object` (`str`) / `TEXT` | Filter / Grouping Key | ISO calendar date (`YYYY-MM-DD`, `2026-04-01` to `2026-06-29`). |
| `store_id` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Store code (`S01`..`S05`). |
| `store` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Store city name (`Mumbai`, `Pune`, `Hyderabad`, `Bengaluru`, `Ahmedabad`). |
| `footfall` | `float64` / `REAL` | **Approved Metric (1/11)** | Cleaned daily store visitor count (no nulls, no negatives, IQR-capped, store-median imputed). |
| `revenue_inr` | `float64` / `REAL` | **Approved Metric (2/11)** | Daily store gross revenue in INR (rounded to 2 decimals). |
| `daily_target_inr` | `int64` / `INTEGER` | **Approved Metric (3/11)** | Store daily revenue target in INR (`1050000` Mumbai, `900000` Pune, `950000` Hyderabad, `950000` Bengaluru, `850000` Ahmedabad). |
| `marketing_spend_inr` | `int64` / `INTEGER` | **Unapproved (Blocked)** | Daily marketing expenditure in INR. Deliberately excluded from the approved field list. |
| `stockout_hours` | `float64` / `REAL` | **Approved Metric (4/11)** | Daily duration of stockouts in hours (1 decimal in raw, formatted to 2 decimals in agent answers). |
| `discount_pct` | `float64` / `REAL` | **Approved Metric (5/11)** | Daily average promotional discount percentage. |
| `revenue_per_footfall` | `float64` / `REAL` | **Unapproved (Blocked)** | Derived Part A feature (`revenue_inr / footfall`, rounded to 2 decimals). Blocked in agent queries. |
| `marketing_efficiency` | `float64` / `REAL` | **Unapproved (Blocked)** | Derived Part A feature (`revenue_inr / marketing_spend_inr`, rounded to 2 decimals). Blocked in agent queries. |
| `achievement_pct` | `float64` / `REAL` | **Approved Metric (6/11)** | Derived Part A feature (`revenue_inr / daily_target_inr * 100`, rounded to 2 decimals). Reported only via `target_vs_actual`. |
| `shortfall_inr` | `float64` / `REAL` | **Unapproved (Blocked)** | Derived Part A feature (`daily_target_inr - revenue_inr`, rounded to 2 decimals). Blocked in agent queries. |
| `weekend_flag` | `object` (`str`) / `TEXT` | **Unapproved (Blocked)** | Derived Part A feature (`Yes` for Saturday/Sunday, `No` otherwise). Blocked in agent queries. |
| `performance_band` | `object` (`str`) / `TEXT` | **Approved Metric (7/11)** | Derived Part A feature (`Excellent` when `achievement_pct >= 100`, `Good` when `75 <= achievement_pct < 100`, `Poor` when `< 75`). Reported only via `target_vs_actual`. |

### Data-Quality Facts Established in Part A & Guarantees of the Cleaned File
1. **Exact Duplicates Removed**: The raw file (`data/store_daily.csv`) had `453` rows because `3` exact duplicate rows (`Mumbai 2026-05-11`, `Hyderabad 2026-05-31`, `Ahmedabad 2026-04-16`) were appended at the end. `store_daily_clean.csv` removes these duplicates (`keep="first"`), guaranteeing exactly `450` unique `(store, date)` rows (90 per store).
2. **Impossible Negative Footfall Corrected**: The raw file contained `1` negative footfall value (`-150` at `Hyderabad` on `2026-04-21`), which was converted to missing (`negative_to_missing`) before computing per-store quartiles and medians.
3. **Extreme Outliers Capped via Per-Store IQR Bounds**: Two genuine busy-day spikes fell outside their store's `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` bounds and were capped (`iqr_cap`, rounded half-up to 2 decimals): `Mumbai` on `2026-04-09` (`6100` capped to `2986.00`) and `Ahmedabad` on `2026-05-26` (`9800` capped to `2281.38`).
4. **Missing Footfall Values Imputed with Store Medians**: All `5` missing footfall values (the `4` originally null cells plus `Hyderabad`'s converted `-150`) were imputed (`median_impute`) using each store's post-capping median footfall: `Mumbai 2386.0` (`2026-04-30`), `Pune 1509.5` (`2026-04-12` and `2026-05-17`), `Hyderabad 2216.0` (`2026-04-21`), and `Bengaluru 2065.0` (`2026-06-10`).
5. **Cleaned File Guarantees**: `data/store_daily_clean.csv` is guaranteed to have `450` rows, `0` missing values in any of the 15 columns, `0` negative footfall values, untouched `revenue_inr` values, and precomputed `achievement_pct` and `performance_band` columns that reconcile 100% between Part A and Part C/D (e.g., full-period store mean daily revenues: `Pune INR 636358.55`, `Ahmedabad INR 782647.37`, `Hyderabad INR 893233.01`, `Bengaluru INR 931065.68`, `Mumbai INR 1064371.60`).

### Questions Supported by `store_daily_clean.csv`
* Single-store, single-date lookups (`lookup` via Python route) for `revenue_inr`, `daily_target_inr`, `footfall`, `stockout_hours`, or `discount_pct`.
* Single-store, date-range average lookups (`lookup` via SQL route) for any of those 5 metrics.
* Single-store, single-date target achievement checks (`target_vs_actual` via Python route) returning `revenue_inr`, `daily_target_inr`, `achievement_pct`, and `performance_band` (triggering `Drafted` status when `performance_band == 'Poor'`, i.e., `achievement_pct < 75.00%`).
* Cross-store rankings and comparisons (`comparison` via SQL route) on a single date or inclusive date range across all 5 stores.

---

## 3. Dataset 2: `data/inventory.csv`

* **Row Count**: `40` rows (5 stores × 8 products).
* **Date Range**: **None** (`inventory.csv` has no `date` column; it represents current stock levels). Any date mentioned in an `inventory` question is dropped during entity filtering before validation and range checking.

### Columns and Types (`6` Columns)

| Column Name | Data Type (pandas / SQLite) | Governance Role | Description |
| :--- | :--- | :--- | :--- |
| `store_id` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Store code (`S01`..`S05`). |
| `store` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Store city name (`Mumbai`, `Pune`, `Hyderabad`, `Bengaluru`, `Ahmedabad`). |
| `product_id` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Product code (`P01`..`P08`). |
| `product` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Full product name with pack size (`Amul Milk 1L`, `Toor Dal 1kg`, `Basmati Rice 5kg`, `Sunflower Oil 1L`, `Iodised Salt 1kg`, `Instant Noodles 4-pack`, `Glucose Biscuits 200g`, `Detergent Powder 1kg`). |
| `stock_units` | `int64` / `INTEGER` | **Approved Metric (8/11)** | Current on-hand inventory in integer units. |
| `reorder_threshold` | `int64` / `INTEGER` | **Approved Metric (9/11)** | Minimum stock threshold in integer units below which reordering is needed. |

### Data-Quality Facts
* Contains zero missing values and exact 5-store coverage for all 8 products.
* Reorder condition is **strict inequality** (`stock_units < reorder_threshold`). For `Amul Milk 1L` (`P01`), `reorder_threshold` is `100` across all stores, and `stock_units` are: `Hyderabad 40`, `Pune 85`, `Ahmedabad 100`, `Bengaluru 130`, `Mumbai 240`. Thus only `Hyderabad` (`40 < 100`) and `Pune` (`85 < 100`) are strictly below the threshold; `Ahmedabad` (`100 == 100`) is at the threshold and is **not** listed as below threshold.
* For `Iodised Salt 1kg` (`P05`), no store has `stock_units < reorder_threshold`.

### Questions Supported by `inventory.csv`
* Identifying which stores (or whether a specific store) have `stock_units < reorder_threshold` for a recognised product (`inventory` intent via SQL route), matching product names case-insensitively with or without the size suffix (e.g., `Amul Milk` or `Amul Milk 1L`).

---

## 4. Dataset 3: `data/feedback.csv`

* **Row Count**: `200` rows (40 feedback records per store across the 5 stores).
* **Date Range**: `2026-04-01` to `2026-06-29` (`date` column present in file). However, per specification, `feedback` questions summarise all 40 rows of the target store and drop any date phrase mentioned in the prompt before validation.

### Columns and Types (`6` Columns)

| Column Name | Data Type (pandas / SQLite) | Governance Role | Description |
| :--- | :--- | :--- | :--- |
| `feedback_id` | `object` (`str`) / `TEXT` | Internal Row ID | Unique feedback identifier (`F001`..`F200`). Not an approved metric or filter key. |
| `store_id` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Store code (`S01`..`S05`). |
| `store` | `object` (`str`) / `TEXT` | Filter / Grouping Key | Store city name (`Mumbai`, `Pune`, `Hyderabad`, `Bengaluru`, `Ahmedabad`). |
| `date` | `object` (`str`) / `TEXT` | Filter / Grouping Key | ISO date of feedback submission (`2026-04-01`..`2026-06-29`). |
| `rating` | `float64` / `REAL` (nullable) | **Approved Metric (10/11)** | Customer satisfaction rating from `1` to `5`, or `null` (`""`) when unrated. |
| `theme` | `object` (`str`) / `TEXT` | **Approved Metric (11/11)** | Feedback category (`Stock availability`, `Queue time`, `Pricing`, `Freshness`, `Staff behaviour`). |

### Data-Quality Facts
* **12 Unrated Rows**: Exactly `12` of the `200` rows have a missing (`null` / empty string) `rating` (at 0-based indices `7, 33, 58, 71, 90, 104, 120, 133, 151, 166, 178, 195`), while `theme` is non-null in all `200` rows.
* **No Imputation of Missing Ratings**: Missing ratings are **never** replaced by an average or zero. Average rating for a store is computed strictly over the non-null rated rows (`COUNT(rating)`), while total row count (`COUNT(*)`) and theme frequency (`theme` mode, tie-broken alphabetically by theme name) are computed over all 40 rows for that store.
* For example, `Hyderabad` has `40` total rows, `38` rated rows, an exact mean rating of `100 / 38 = 2.6315... -> 2.63` (rounded half-up to 2 decimals), and `Stock availability` as its most frequent theme (`28` occurrences).

### Questions Supported by `feedback.csv`
* Store-level customer feedback summaries (`feedback` intent via SQL route) reporting the store's average rating over rated rows (to 2 decimals), the integer count of rated rows, the integer count of all rows (`40`), and the most frequent feedback theme.