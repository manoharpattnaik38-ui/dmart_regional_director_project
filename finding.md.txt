# Store Diagnosis and Premise Test Findings

## 1. Store Performance Summary Table (Cleaned Data, 90 Days per Store)

Note: In accordance with Task 6.i, `revenue_per_footfall` in this summary table is computed as each store's total revenue divided by its total footfall across all 90 days (and across all 450 rows for the `All stores` row).

| Store | Mean Daily Revenue (INR) | Mean Footfall | Mean Stockout Hours | Revenue per Footfall (INR) | Mean Achievement (%) | Poor Days |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Ahmedabad** | 782647.37 | 1922.59 | 3.19 | 407.08 | 92.08 | 1 |
| **Bengaluru** | 931065.68 | 2076.86 | 2.38 | 448.31 | 98.01 | 0 |
| **Hyderabad** | 893233.01 | 2209.51 | 3.85 | 404.27 | 94.02 | 0 |
| **Mumbai** | 1064371.60 | 2391.27 | 1.93 | 445.11 | 101.37 | 0 |
| **Pune** | 636358.55 | 1517.71 | 2.32 | 419.29 | 70.71 | 70 |
| **All stores** | 861535.24 | 2023.59 | 2.74 | 425.75 | 91.24 | 71 |

---

## 2. Premise Test: Does Pune Have More Stockout Hours Than the Other Stores?

**Verdict: The premise "Pune is the lowest-revenue store because it has the most stockouts" is NOT supported by the data.**

### Store Ranking by Mean Daily Stockout Hours (Highest to Lowest)

1. **Hyderabad**: `3.85` hours/day
2. **Ahmedabad**: `3.19` hours/day
3. **Bengaluru**: `2.38` hours/day
4. **Pune**: `2.32` hours/day *(4th of 5 stores; 15.33% below the all-store mean of `2.74` hours/day)*
5. **Mumbai**: `1.93` hours/day

**Answer**: No. Pune does not have more stockout hours than the other stores. Pune ranks **4th out of 5** stores by mean stockout hours (`2.32` hours/day against the all-store average of `2.74` hours/day). Hyderabad (`3.85` hours/day), Ahmedabad (`3.19` hours/day), and Bengaluru (`2.38` hours/day) all experience higher average daily stockout durations than Pune, yet all three generate substantially higher daily revenue (`INR 893233.01`, `INR 782647.37`, and `INR 931065.68` respectively) than Pune (`INR 636358.55`).

---

## 3. Pearson Correlation Analysis

| Scope | Variables Compared | Sample Size ($n$) | Pearson Correlation ($r$) |
| :--- | :--- | :---: | :---: |
| **All stores (Cleaned)** | `revenue_inr` vs `stockout_hours` | 450 | **-0.152** |
| **All stores (Cleaned)** | `revenue_inr` vs `footfall` | 450 | **0.918** |
| **Pune only (Cleaned)** | `revenue_inr` vs `stockout_hours` | 90 | **-0.254** |
| **Pune only (Cleaned)** | `revenue_inr` vs `footfall` | 90 | **0.735** |
| **All stores (Deduplicated Raw, before cleaning)** | `revenue_inr` vs `footfall` *(non-missing rows, with `-150`, `6100`, `9800` still in)* | 446 | **0.548** |

* **Effect of Data Cleaning**: Removing the impossible negative footfall (`-150` in Hyderabad) and capping the two extreme counter spikes (`6100` in Mumbai, `9800` in Ahmedabad) increases the pooled `revenue_inr`–`footfall` correlation from **0.548** (across the 446 non-missing deduplicated raw rows) to **0.918** (across the 450 cleaned rows), revealing the strong linear relationship that raw data errors had obscured.
* **Methodological Note**: Correlation does not establish causation.

---

## 4. Facts, Insights, and Hypotheses

### Facts (Directly from Cleaned Data)
1. **Fact 1 (Revenue Gap)**: Pune's mean daily revenue is `INR 636358.55`, which is `26.14%` (`INR 225176.69`) below the all-store mean daily revenue of `INR 861535.24`.
2. **Fact 2 (Footfall Gap)**: Pune's mean daily footfall is `1517.71` visitors, which is `25.00%` (`505.88` visitors/day) below the all-store mean footfall of `2023.59` visitors.
3. **Fact 3 (In-Store Monetisation Parity)**: Pune's ratio of total revenue to total footfall (`revenue_per_footfall`) is `INR 419.29`, which is only `1.52%` (`INR 6.46`) below the all-store figure of `INR 425.75` and exceeds both Ahmedabad (`INR 407.08`) and Hyderabad (`INR 404.27`).
4. **Fact 4 (Stockout Ranking)**: Pune averages `2.32` stockout hours per day (ranking 4th of 5 stores and below the `2.74` all-store mean), whereas Hyderabad averages the highest stockout hours at `3.85` hours per day while achieving `94.02%` of its daily target (`INR 893233.01` mean daily revenue).
5. **Fact 5 (Target Achievement & Poor Band Concentration)**: Pune's mean target achievement is `70.71%` against its `INR 900000` daily target, accounting for `70` of the `71` total `Poor` performance band days (`achievement_pct < 75%`) across all five stores over the 90-day period.
6. **Fact 6 (Customer Feedback Themes)**: In `data/feedback.csv`, `Pricing` is Pune's most frequent feedback theme (`19` of `40` reviews, `47.5%`), whereas `Stock availability` accounts for only `3` of `40` reviews (`7.5%`) in Pune compared to `28` of `40` reviews (`70.0%`) in Hyderabad.

### Insights (Interpretations Drawn from Facts)
1. **Insight 1 (Pune Has a Traffic Problem, Not an Availability or Conversion Problem)**: Because Pune's `26.14%` revenue deficit is almost entirely mirrored by its `25.00%` footfall deficit—while its revenue per visitor (`INR 419.29`) sits within `1.52%` of the regional benchmark (`INR 425.75`) and its stockout hours (`2.32`) are the second-lowest in the region—customers who enter the Pune store spend at normal regional levels. Funding a stock-availability programme in Pune addresses a problem Pune does not have (Hyderabad is the store with the `3.85` hr/day stockout issue and `70%` stock-availability complaints).
2. **Insight 2 (Target Misalignment Amplifies Pune's Alert Frequency)**: Pune's daily revenue target (`INR 900000`) requires roughly `2146` visitors/day at Pune's current `INR 419.29` revenue per visitor—an expectation aligned with Bengaluru (`2076.86`) and Hyderabad (`2209.51`) rather than Pune's actual catchment footfall (`1517.71`). This structural gap between catchment traffic and target setting causes Pune to fall into the `Poor` band (`<75%` achievement) on `77.8%` of operating days (`70/90` days).

### Hypotheses (Unconfirmed — Extra Data Needed to Test)
1. **Hypothesis 1 [Unconfirmed — Catchment Competition & Local Marketing Reach]**: Pune's `25.00%` lower daily footfall is caused by trade-area cannibalisation from competing hypermarkets/quick-commerce dark stores or inefficient local marketing channel allocation in Pune's catchment area.
   * *Extra data needed to test*: Trade-area household population density within a 5 km radius, competitor store opening dates and proximity, channel-level marketing reach/impressions data, and loyalty-card repeat-visit frequency for Pune vs other cities.
2. **Hypothesis 2 [Unconfirmed — Perceived Price Competitiveness in Pune]**: Local perception of uncompetitive everyday pricing in Pune (evidenced by `Pricing` representing `19/40` of Pune's customer feedback items) is deterring routine weekly grocery trips and reducing store entry frequency.
   * *Extra data needed to test*: SKU-level competitor price benchmark audits in Pune, category-level basket penetration data, and pre/post promotional footfall elasticity records.