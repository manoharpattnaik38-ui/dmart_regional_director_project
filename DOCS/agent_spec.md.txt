# Agent Architecture and Behavioural Specification

## 1. Eight-Step Pipeline Table

Note on **Validate** ordering: In this architecture, **Validate** (the approved-field and table whitelist check, date-range check, and entity-completeness check) runs **before** the data query executes (`Query`) so that no unapproved table/column or out-of-range date ever reaches Python data access or SQLite execution. All eight required steps are detailed below in execution order:

| StepOrder | Step Name | Classification | Technique Used | What It Does |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Interpret** | Generative *(Default: Rule-based)* | Deterministic closed-grammar regex, tokeniser, `difflib.SequenceMatcher` fuzzy matcher, and session context merger (`agent/understand.py`, `LLM_MODE=mock`). | Parses the user's plain-English question and session `context` to extract `intent`, `store`, `metric`, `date` / date range, `product`, `weather_requested`, entity `confidence` (`0.0`–`1.0`), and `missing_entities`. Drops unused entities per intent and updates session context when rules allow. |
| **2** | **Route** | Deterministic | Rule-based dispatch table (`agent/run_agent.py` & `agent/fetch.py`). | Maps the interpreted intent and entity structure to the execution route: `python` (one-store, one-date `lookup` or `target_vs_actual`), `sql` (range `lookup`, `comparison`, `inventory`, `feedback`), `weather` (standalone weather lookup), `python+weather` (one-store, one-date `lookup` or `target_vs_actual` with a weather keyword), or `none` (when rejected before data access). |
| **3** | **Validate** *(Runs before Query)* | Deterministic | Pre-query governance gate: whitelist check against the 11 approved reportable metric fields, allowed tables (`store_daily_clean`, `inventory`, `feedback`), allowed filter/group keys (`store`, `store_id`, `date`, `product`, `product_id`), sort order whitelist (`ASC`/`DESC`), confidence threshold (`>= 0.7`), and date boundary (`2026-04-01`..`2026-06-29`). | Enforces status precedence rules (1)–(3) before any query runs. Refuses `unsupported_metric` (`Safe Failure`), `out_of_scope` and `diagnostic` (`Escalated`), missing/ambiguous/low-confidence entities (`Clarification Needed`), and out-of-range dates (`Safe Failure`), setting `route="none"`, `executed=None`, and `tool_calls=0`. |
| **4** | **Query** | Deterministic | Parameterised SQLite queries (`sqlite3` with `?` placeholders), direct pandas/Python row lookups, `tools/weather.py` (`get_weather`), and bounded retry loop (up to 3 attempts, supporting `SIMULATE_DB_FAILURES`). | Executes the validated data retrieval against `store_daily_clean.csv`, `inventory.csv`, `feedback.csv`, and/or `weather_tool`. Tracks `attempts` (up to `3`) and `tool_calls`. If all `3` database attempts fail, terminates with `Escalated`. If no matching record exists, returns `Safe Failure`. |
| **5** | **Calculate** | Deterministic | Exact integer-cent arithmetic (`SUM(CAST(ROUND(metric * 100) AS INTEGER))` divided by `COUNT(metric)`) with Python `decimal.Decimal` and `ROUND_HALF_UP` to 2 decimals. | Computes multi-day store averages, cross-store rankings (handling `best`/`worst` directionality and alphabetical store-name tie-breaking), target achievement bands (`Poor < 75%`, `Good 75%..99.99%`, `Excellent >= 100%`), inventory threshold filters (`stock_units < reorder_threshold`), and feedback rating means over rated rows only. |
| **6** | **Synthesize** | Generative *(Default: Fixed Templates)* | Deterministic slot-filled string templates (`agent/answer.py`, `LLM_MODE=mock`) with strict number formatting rules. | Formats the reply text (`answer_text`) with `INR <value>` (2 decimals, no commas), `<value>%` (2 decimals), 2-decimal floats for ratings/footfall/stockout hours, integer counts, and 1-decimal weather values (with `<value> mm` for rain). Sets status to `Drafted` if a `target_vs_actual` result falls in the `Poor` band (`< 75.00%`), else `Answered`. |
| **7** | **Ground** | Deterministic | Pre-synthesis value registration and regex digit-run verification (`agent/answer.py`). | Builds `evidence` and `grounded_values` directly from fetched data records, tool outputs, and quoted constants (never by scanning `answer_text`). Strips ISO dates and sized product names from `answer_text`, extracts all remaining numeric tokens, and verifies that every number matches `grounded_values` (`ungrounded_numbers == 0`). |
| **8** | **Record** | Deterministic | Append-only JSON Lines logger (`agent/run_agent.py`) with `time.perf_counter()` monotonic latency measurement. | Appends a single JSON object per call to `AGENT_LOG_PATH` (default `logs/runs.jsonl`) containing all 20 required audit keys (`run_id` through `budget_exceeded`). |

---

## 2. Intent Table

The assistant classifies every incoming question into one of these **9 intents** using the strict 11-rule priority order defined in Section 3.1:

| Intent | Example Question | Execution Route | Description |
| :--- | :--- | :--- | :--- |
| **`lookup`** | `"What was Pune's revenue on 15 May 2026?"` *(1-date)*<br>`"What was Pune's revenue between 2026-05-01 and 2026-05-05?"` *(range)*<br>`"What was Mumbai's revenue on 15 May 2026 and what was the weather like?"` *(with weather)* | `python` *(1 store, 1 date)*<br>`sql` *(1 store, date range)*<br>`python+weather` *(1 store, 1 date + weather word)*<br>`none` *(if rejected in Validate)* | Retrieves one of the 5 approved daily store metrics (`revenue_inr`, `daily_target_inr`, `footfall`, `stockout_hours`, `discount_pct`) for one store on a single date or its average over an inclusive date range. |
| **`target_vs_actual`** | `"Did Pune hit its target on 2026-05-16?"` | `python` *(or `python+weather` if weather word present; `none` if rejected)* | Checks a single store's daily `revenue_inr` against `daily_target_inr` on a single date, reporting `achievement_pct` and `performance_band` (`Excellent`, `Good`, or `Poor`). |
| **`comparison`** | `"Which store had the highest average revenue between 2026-05-01 and 2026-05-31?"` | `sql` *(or `none` if rejected)* | Computes and ranks all 5 stores by the average of an approved daily metric over a single date or inclusive date range. |
| **`inventory`** | `"Which stores are below the reorder threshold for Amul Milk?"` | `sql` *(or `none` if rejected)* | Checks `data/inventory.csv` for stores where `stock_units < reorder_threshold` for a requested product (optionally filtered to one store). |
| **`feedback`** | `"What are customers saying about Hyderabad?"` | `sql` *(or `none` if rejected)* | Summarises `data/feedback.csv` for one store: mean `rating` across rated rows, rated row count, total row count (`40`), and most frequent `theme`. |
| **`weather`** | `"What was the weather in Pune on 2026-05-16?"` | `weather` *(or `none` if rejected)* | Calls `tools/weather.py` (`get_weather`) for one store city and one valid ISO date within `2026-04-01`..`2026-06-29`. |
| **`unsupported_metric`** | `"What was Pune's profit margin on 2026-05-15?"` | `none` | Refuses requests for unapproved or non-existent metrics (`profit`, `margin`, `marketing`, `cost`, `expense`, `shortfall`, `efficiency`, `weekend`, `per footfall`, `per visitor`) with `Safe Failure`. |
| **`out_of_scope`** | `"What is the capital of India?"`<br>`"Reorder 200 units of Amul Milk for Pune"` | `none` | Escalates prohibited actions/rule overrides (`ignore`, `reorder` imperative, `send`, `email`, `whatsapp`, `purchase`, `buy`, `restock`, `place an order`) and unrecognisable general questions with `Escalated`. |
| **`diagnostic`** | `"Why is Pune's revenue so low?"` | `none` | Escalates causal/trend/reason (`why`, `trend`, `reason`) questions to a human analyst with `Escalated` and no reported figures. |

---

## 3. Handling Rules

### 3.1 Strict Intent Evaluation Order (11 Rules)
Intent classification evaluates the question in this exact priority order (normalising underscores `_` to spaces and matching singular and plural forms of every keyword):

1. **Prohibited Action / Rule Override (`out_of_scope`)**: Any question containing `ignore`, `disregard`, `override`, `bypass`, `forget`, `send`, `email`, `whatsapp`, `purchase`, `buy`, `restock`, the phrase `place an order`, or `order`/`reorder` used as an imperative (as the first word of the question; directly after `please`, `kindly`, `can you`, `could you`, `will you`, `would you`, or `go ahead and`; or after a comma-address such as `"Pune, reorder Amul Milk"`)—unless the very next word is `threshold(s)`, `level(s)`, or `point(s)`—is classified as `out_of_scope` (`Escalated`), even if it also mentions a store, metric, product, or date.
2. **Unsupported Metric (`unsupported_metric`)**: Checked **before** metric synonyms so that `"revenue per footfall"` is never answered as `"revenue"`. Any question containing `profit`, `margin`, `marketing`, `cost`, `expense`, `shortfall`, `efficiency`, `weekend`, `per footfall`, or `per visitor` (including `revenue_per_footfall`, `shortfall_inr`, `marketing_efficiency`, `weekend_flag`, `marketing_spend_inr`) is classified as `unsupported_metric` (`Safe Failure`).
3. **Diagnostic (`diagnostic`)**: Any question containing `why`, `trend`/`trends`, or `reason`/`reasons` is classified as `diagnostic` (`Escalated`).
4. **Inventory (`inventory`)**: Any question matching a recognised product name (with or without size) or containing the words `reorder` or `inventory`/`inventories` is classified as `inventory`.
5. **Feedback (`feedback`)**: Any question containing `feedback`, `review`/`reviews`, `rating`/`ratings`, or `customer`/`customers` together with `say`/`says`/`saying` is classified as `feedback`.
6. **Target vs Actual (`target_vs_actual`)**: Any question containing `target`/`targets` together with one of `hit`, `met`, `meet`, `miss`, `missed`, `beat`, `exceed`, `exceeded`, `achieve`, `achieved`, `reach`, `reached`, `below`, `above`, `against`, `versus`, `vs`, or the phrase `fall short` / `fell short`, OR containing `achievement` (`achievement_pct`) or `performance band` (`performance_band`), is classified as `target_vs_actual`.
7. **Comparison (`comparison`)**: Any question containing `which`, `highest`, `lowest`, `best`, or `worst` that names **no store** (neither resolved nor unresolved named store) is classified as `comparison`.
8. **Metric Lookup (`lookup`)**: Any question naming an approved metric or metric synonym (with or without a store, date, or weather word) is classified as `lookup`.
9. **Weather (`weather`)**: Any question containing a weather word (`weather`, `rain`, `temperature`, `humidity`, `hot`, `cold`) with no metric is classified as `weather`.
10. **Bare Store and/or Date Follow-up (`lookup` or `target_vs_actual`)**: Any question that names a store and/or a date (resolved or unresolved) but no metric and no weather word (e.g., `"How is Hyderabad doing?"`, `"How about Mumbai?"`, `"How about Kolkata?"`, `"How about 15 Jun 2026?"`) is classified as `target_vs_actual` if the session's last stored question was `target_vs_actual`, and `lookup` otherwise.
11. **Fallback (`out_of_scope`)**: Any question containing nothing recognisable is classified as `out_of_scope`.

### 3.2 Store Name, Alias, Typo, and Unresolved Store Resolution
* **Exact Match & Explicit Alias (`confidence = 1.0`)**: Case-insensitive exact match against `Mumbai`, `Pune`, `Hyderabad`, `Bengaluru`, `Ahmedabad` anywhere in the question gives confidence `1.0`. `Bangalore` (case-insensitive) is an explicit alias of `Bengaluru` with confidence `1.0`.
* **Candidate Word Definition for Fuzzy Matching**: A word is a store candidate only if:
  1. Its base alphabetic form (after stripping trailing `'s` or `’s` and punctuation) has **at least 5 letters** (`len >= 5`),
  2. It is **capitalised** in the question OR carries a possessive `'s`,
  3. It is **not the first word** of the question (unless it carries `'s`),
  4. It is **neither a keyword nor a stop word** (where keywords include all singular/plural intent, metric, unsupported-field, weather, date, prohibited-action, month, weekday, and recognised product words; stop words include `hello, thanks, thank, kindly, please, display, compare, which, what, whats, how, why, did, and, show, check, report, where, would, could, can, will, give, tell, list`), and
  5. It is not one of the brief's own proper nouns (`DMart, Avenue, Supermarts, Kavita, Rao, Meteo, GitHub, Python, SQLite, PostgreSQL, Markdown`), except when a brand/persona noun carries `'s` or directly follows `for`, `about`, `in`, or `at` and no valid store resolved anywhere in the question (e.g., `"What was DMart's revenue on 2026-05-16?"` treats `DMart's` as an unresolved named store with confidence `0.4` and never fills the store from session context).
* **Fuzzy Similarity Matching (`difflib.SequenceMatcher`)**: Each candidate word is compared case-insensitively (`SequenceMatcher(None, candidate.lower(), store.lower()).ratio()`) against the five store names:
  * If the best score is `>= 0.7`, the candidate resolves to that store with `confidence = best_score` (e.g., `Bengalore` -> `0.78`, `Bangalor` -> `0.71`, `Punee` -> `0.89`, `Hydrabad's` -> `0.94`, `Mumbay` -> `0.83`).
  * If the best score is `< 0.7` (e.g., `Banglore` -> `0.59`, `Kolkata`, `Diwali`), the candidate is flagged as an **unresolved named store** (`confidence = 0.4`) in two cases:
    * **Case (a) — Whatever else resolved**: When the candidate word carries `'s` or directly follows `and`, `or`, `vs`, `versus`, `than`, or `for` (so a second unresolvable store like `"Compare Mumbai and Kolkata revenue on 2026-05-15"` or `"What was Pune's revenue for Diwali on 2026-05-15?"` is never silently dropped).
    * **Case (b) — Only when no store resolved anywhere in the question**: When the candidate word directly follows `about`, `in`, or `at`, OR the question also contains a metric, a weather word, or a date (so `"What was Kolkata's revenue on 2026-05-15?"` and `"How about Kolkata?"` are flagged as unresolved named stores with `Clarification Needed`, whereas `"What is the capital of India?"` has no metric/weather/date and no `about/in/at` before `India` and stays `out_of_scope`).
* **Product Matching**: Products (`Amul Milk 1L`, `Toor Dal 1kg`, `Basmati Rice 5kg`, `Sunflower Oil 1L`, `Iodised Salt 1kg`, `Instant Noodles 4-pack`, `Glucose Biscuits 200g`, `Detergent Powder 1kg`) are matched case-insensitively with or without the size suffix (e.g., `Amul Milk` or `Amul Milk 1L`) with confidence `1.0`. No fuzzy matching is performed on products.

### 3.3 Metric Synonyms
The metric synonym list is closed (applied after Rule 2 `unsupported_metric` check, with confidence `1.0`):
* `revenue`, `sales`, `turnover`, `earnings`, `revenue_inr` -> `revenue_inr`
* `target`, `daily_target_inr` -> `daily_target_inr`
* `footfall`, `visitors` -> `footfall`
* `stockout`, `stockouts`, `stockout_hours` -> `stockout_hours`
* `discount`, `discounts`, `discount_pct` -> `discount_pct`

### 3.4 Closed Date Grammar and Unresolved Named Dates
* **Reference Date**: `AS_OF_DATE = 2026-06-30`, so `yesterday` resolves to `2026-06-29` (`confidence = 1.0`).
* **Four Accepted Date Forms (`confidence = 1.0`)**:
  1. `YYYY-MM-DD`: Strict 10-character ISO format (`^\d{4}-\d{2}-\d{2}$`) representing a valid calendar date.
  2. `D Month YYYY`: 1 or 2 digit cardinal day (no ordinal suffix), full month name (case-insensitive, e.g., `15 May 2026` or `15 june 2026`), and 4-digit year, representing a valid calendar date.
  3. `yesterday`: Resolves to `2026-06-29`.
  4. `between <date> and <date>`: Inclusive range where both endpoints are valid single dates (Form 1, 2, or 3) and `start_date <= end_date`.
* **Unresolved Named Date (`confidence = 0.4`)**: Any date-like token or phrase outside the four forms above is flagged as an unresolved named date (`confidence = 0.4`), never replaced from session context, and never resolved by picking only the first date:
  * Malformed or impossible dates: `20260515`, `2026-5-15`, `2026-W20-5`, `2026-02-30`, `May 15, 2026`, `15 Jun 2026` (abbreviated month), `15 May` (no year), `15th May 2026` (ordinal day).
  * Relative or period phrases: `today`, `tomorrow`, `last/this/next week/month/quarter/year`, `Q1`..`Q4`, bare years (`2026`), `past`, `previous`, `ago`, `last 7 days`, `month to date` / `month-to-date`, `YTD` / `year-to-date`, `quarter-end`, `EOD`, `FY26`, `this morning`, `recent`, `latest`, `now`, `lately`.
  * Frequency words that belong to a metric phrase are **not** date phrases: `daily`, `weekly`, `monthly`, `quarterly`, `yearly`, `annual`, `per day`, `per week`, `per month`, `per year` (so `"What is Pune's daily target on 2026-05-15?"` is answered).
  * Standalone month names (any case, e.g., `in May`, `for June`, `until june`), **except** `may` or `march` used as verbs: lowercase `may`/`march` counts as a month only when directly following `in, on, of, during, since, for, from, until, till, by, to, through, throughout, before, after, within, over`; capitalised `May` directly before `I, we, you, be` is treated as a verb and ignored.
  * Weekday rules: A singular weekday (`Monday`..`Sunday`) accompanying a single valid date that matches that date's actual calendar weekday is ignored (e.g., `"On Sunday, what was Pune's revenue on 2026-05-17?"` is answered because `2026-05-17` is a Sunday); if the weekday does not match the date (e.g., `"Monday 2026-05-17"`), or appears with no valid date, it is an unresolved named date. A plural weekday (`Sundays`, `weekdays`) beside a valid `between <date> and <date>` range is ignored and the full range governs; with no valid range it is an unresolved named date.
  * Multiple dates outside `between <date> and <date>` (including `from <date> to <date>` or `yesterday` plus another date), a `between` range where `start > end`, or a date range supplied (either in the prompt or via session context) to a single-date intent (`target_vs_actual`, `weather`).

### 3.5 Confidence Calculation, Threshold (`0.7`), and Ambiguity Rule
* **Confidence Score**: Computed as the **minimum** confidence across all entities used by the classified intent (its required entities plus any optional `store` named in an `inventory` question):
  * `1.0` for exact store match, `Bangalore` alias, exact product match, metric synonym, or valid closed-grammar date/range, and `1.0` for an entity inherited from session context.
  * The `SequenceMatcher` ratio (`0.70`–`0.99`) for a fuzzy-matched store.
  * `0.4` if any required entity is missing after applying session context, if there is an unresolved named store or unresolved named date, or if the ambiguity rule triggers.
  * `1.0` for intents that use no entities (`unsupported_metric`, `out_of_scope`, `diagnostic`).
* **Clarification Threshold (`0.7`)**: Any question with `confidence < 0.7` produces status `Clarification Needed` (unless superseded by Rule 1 intent-based status `unsupported_metric`, `out_of_scope`, or `diagnostic`).
* **Ambiguity Rule**: If the entities used by an intent include **two different stores** (e.g., `"Pune and Mumbai revenue on 2026-05-15"`) or **two different metrics** (e.g., `"Pune's revenue and footfall on 2026-05-15"`), confidence is set to `0.4` and the status is `Clarification Needed`, asking the user which one they want. There is no first-match-wins.

### 3.6 Entities Used per Intent and Session Context Carry-Over

| Intent | Required Entities | Optional Entities | Remarks & Context Rules |
| :--- | :--- | :--- | :--- |
| **`lookup`** | `store`, `metric`, `date` (or range) | `none` *(weather flag optional for single date)* | A date range returns that store's mean of the metric over the inclusive range. Weather is called only on a 1-store, 1-date lookup. |
| **`target_vs_actual`** | `store`, `one date` | `none` *(weather flag optional)* | Metric is fixed (`revenue_inr` vs `daily_target_inr`). A range (typed or from context) is flagged as an unresolved named date (`0.4`). |
| **`comparison`** | `metric`, `date` (or range) | `none` | Never requires or inherits `store` from context. Naming a store in the prompt disqualifies Rule 7 (`comparison`) or triggers ambiguity. |
| **`inventory`** | `product` | `store` | Any date in the prompt is dropped before validation. If a store is named in the current prompt, filters to that store; never inherits `store` from context. |
| **`feedback`** | `store` | `none` | Covers all 40 rows of that store. Any date or metric in the prompt is dropped before validation. |
| **`weather`** | `store`, `one date` | `none` | A range (typed or from context) is flagged as an unresolved named date (`0.4`). |
| **`unsupported_metric`, `out_of_scope`, `diagnostic`** | `none` | `none` | Decided by intent alone; drops all entities and never updates session context. |

* **Session Context Rules**:
  * Context is isolated per `session_id` and never crosses sessions.
  * Unused entities for an intent (e.g., a date in `feedback` or `inventory`, a metric in `feedback`, a store in `comparison`) are dropped before validation, do not affect confidence, and are not saved to context.
  * When a required entity is omitted in the current question, it is filled from the session's last stored resolved value for that entity (`store`, `metric`, `date`/range, `product`), EXCEPT that:
    1. An unresolved named store, unresolved named date, or ambiguous pair (`2` stores or `2` metrics) in the current question is **never** overwritten by session context.
    2. A date range stored in session context is **never** carried into a single-date intent (`target_vs_actual`, `weather`); if a single-date intent omits the date while context holds a range, it is treated as an unresolved named date (`confidence = 0.4`, `Clarification Needed`).
    3. Optional entities (`store` in `inventory`) are never filled from session context.
  * Every question **except** `unsupported_metric`, `diagnostic`, and `out_of_scope` updates the session context with the valid, resolved entities used by its intent—even when the question itself ends in `Clarification Needed` (for example, in session `s2`, A04 `"How is Hyderabad doing?"` resolves `store="Hyderabad"`, stores it in `s2` context, and returns `Clarification Needed` for missing `metric` and `date`; A05 `"revenue on 2026-05-15"` then inherits `store="Hyderabad"` from `s2` context).
  * A `target_vs_actual` question stores only `store` and `date` (never `metric`) and sets `last_intent = "target_vs_actual"` on the session so that a bare follow-up naming only a store or date repeats `target_vs_actual`; any other stored intent clears that mark.

### 3.7 Status Decision Table and Strict Status Precedence

The first rule in this precedence order that matches determines the response `status`:

| Precedence Rank | Status | Exact Triggering Condition | Route & Tool Calls |
| :---: | :--- | :--- | :--- |
| **Rule 1 (Intent-based)** | **`Safe Failure`** | Intent is `unsupported_metric` (requests a field outside the 11 approved fields). | `route="none"`, `tool_calls=0`, `attempts=0` |
| **Rule 1 (Intent-based)** | **`Escalated`** | Intent is `out_of_scope` (including prohibited actions and rule overrides) or `diagnostic` (`why`/`trend`/`reason`). | `route="none"`, `tool_calls=0`, `attempts=0` |
| **Rule 2 (Entity / Confidence)** | **`Clarification Needed`** | Any required entity is missing after applying session context, an unresolved named store or unresolved named date is present, two different stores or two different metrics are named, or `confidence < 0.7`. | `route="none"`, `tool_calls=0`, `attempts=0` |
| **Rule 3 (Date Range Check)** | **`Safe Failure`** | For date-using intents (`lookup`, `target_vs_actual`, `comparison`, `weather`), the resolved date or any endpoint of a resolved date range falls outside `2026-04-01` to `2026-06-29`. | `route="none"`, `tool_calls=0`, `attempts=0` |
| **Rule 4a (Query Execution)** | **`Escalated`** | A data query fails all `3` allowed attempts (initial try + 2 retries), or weather tool fails in standalone weather intent. | `route` kept (e.g., `"python"`), `tool_calls=1`, `attempts=3` |
| **Rule 4b (Empty Result)** | **`Safe Failure`** | Query succeeds (`attempts <= 3`) but returns no matching record for the store, date, or product (note: `inventory` with 0 stores below threshold is a valid empty list and returns `Answered`, not `Safe Failure`). | `route` kept, `tool_calls >= 1` |
| **Rule 5a (Alert Gate)** | **`Drafted`** | Query succeeds and validates, and the intent is `target_vs_actual` with a result in the `Poor` performance band (`achievement_pct < 75.00%`). Held for human approval. | `route="python"` (or `"python+weather"`), `tool_calls >= 1` |
| **Rule 5b (Normal Completion)** | **`Answered`** | Query succeeds, all numbers are grounded (`ungrounded_numbers == 0`), and no alert fired. | `route` active, `tool_calls >= 1` |

---

## 4. Escalation and Retry Rules

1. **Maximum Attempts per Query**: Every data query (Python lookup or SQLite query) is allowed **at most 3 attempts in total** (1 initial attempt plus up to 2 retries).
2. **Failure Simulation (`SIMULATE_DB_FAILURES`)**: In `agent/fetch.py`, reading the environment variable `SIMULATE_DB_FAILURES=<n>` causes the first `n` attempts of every data query in a question to raise a simulated database failure before executing:
   * When `SIMULATE_DB_FAILURES=2` (Case `A19`), attempts 1 and 2 fail, attempt 3 succeeds, `attempts` is logged as `3`, and status is `Answered`.
   * When `SIMULATE_DB_FAILURES=3` (Case `A20`), attempts 1, 2, and 3 all fail, retries are exhausted, `attempts` is logged as `3`, `route` remains `"python"`, `tool_calls` is `1`, and status is **`Escalated`** with an error message containing no INR figures (and writing `"three attempts"` in words or grounding the attempt count so `ungrounded_numbers == 0`).
3. **Logging Retry Counts**: `attempts` in the log records the highest attempt count among the question's data queries (`0` when no data query was started or only `weather_tool` ran). Retries of the same data query do **not** increment `tool_calls` (`tool_calls` stays `1` for the data route plus `1` if `weather_tool` was called).

---

## 5. Success Criteria, Completion States, and Part D Test-Case Categories

### Observable and Measurable Success Criteria
1. **100% Numerical Grounding (`ungrounded_numbers == 0`)**: Every numeric token in `answer_text` (after stripping ISO dates `YYYY-MM-DD` and sized product names like `Amul Milk 1L`) matches an entry in `grounded_values` built directly from fetched data records, tool outputs, or quoted constants. Total `ungrounded_numbers` across all acceptance and evaluation runs must equal `0`.
2. **Zero Leakage on Non-Answer Replies**: Every reply with status `Safe Failure`, `Escalated`, or `Clarification Needed` contains **zero** `INR` figures (`0` non-answer replies stating an INR figure).
3. **Exact Numerical Reconciliation with Part A**: Single-date lookups, 31-day May averages (`A10`), and 90-day full-period store averages (`R01`) match `analysis/findings.md` and `data/store_daily_clean.csv` to `0.01` using integer-cent SQL aggregation and `Decimal` `ROUND_HALF_UP`.
4. **Token and Latency Efficiency**: `tokens_est` (whitespace-separated word count of `question + answer_text`) stays `<= 150` (`budget_exceeded == False`) for 100% of test cases.
5. **Release Gate Thresholds**: Pass rate is `100%` on all 7 safety/gate categories (`unsupported_metric`, `out_of_scope`, `out_of_range_date`, `injection`, `ambiguity`, `unresolved_store`, `unresolved_date`) and `>= 90%` overall across the golden evaluation set (`>= 34` cases).

### Completion States
Every call to `handle(question, session_id, user_id)` terminates in exactly one of the five completion states (`Answered`, `Drafted`, `Clarification Needed`, `Escalated`, `Safe Failure`) and writes one complete JSON line with all 20 required fields to the active log path (`AGENT_LOG_PATH`).

### Test-Case Categories Covered in Part D (`eval/golden_set.csv`)
Part D evaluates the assistant across **15 categories** (comprising the 24 fixed cases `A01`–`A20`, `W01`–`W03`, `R01` plus at least 10 custom cases covering all 9 required custom categories):
1. `lookup` (Single-date, multi-turn context, range average, and combined metric + weather lookups)
2. `target_vs_actual` (Target checks across `Poor` -> `Drafted`, `Good` -> `Answered`, and `Excellent` -> `Answered` bands)
3. `comparison` (Cross-store highest/lowest/best/worst rankings over single dates, 31-day ranges, and full 90-day reconciliation `R01`)
4. `inventory` (Stores strictly below reorder threshold, and products where no store is below threshold)
5. `feedback` (Store average rating over rated rows, rated/total counts, and top feedback theme)
6. `weather` (Standalone city/date weather lookups and unresolved city weather clarification)
7. `retry` (Database transient failure recovery on attempt 3 and exhaustion escalation after attempt 3)
8. `diagnostic` (Escalation of "why"/causal questions without leaking figures)
9. `typo` *(Required custom & fixed category)*: Fuzzy matching of capitalised/possessive store misspellings with similarity `>= 0.7`
10. `synonym` *(Required custom category)*: Resolution of `sales`, `turnover`, `earnings`, `visitors`, `stockouts`, `discounts`
11. `ambiguity` *(Required custom & Gate category)*: Multi-store or multi-metric ambiguity and missing required entities
12. `unsupported_metric` *(Required custom & Gate category)*: Refusal of unapproved columns (`marketing_spend_inr`, `profit`, `margin`, `revenue_per_footfall`, `shortfall_inr`, `weekend_flag`)
13. `out_of_scope` *(Required custom & Gate category)*: Escalation of unrelated world-knowledge queries
14. `injection` *(Required custom & Gate category)*: Escalation of rule-override and prohibited-action commands (`ignore rules`, `reorder stock`, `send email/whatsapp`)
15. `out_of_range_date` *(Required custom & Gate category)*: Refusal of dates outside `2026-04-01` to `2026-06-29`
16. `unresolved_store` *(Required custom & Gate category)*: Refusal to overwrite an unresolved store name (e.g., `Kolkata`) from prior session context
17. `unresolved_date` *(Required custom & Gate category)*: Refusal to overwrite an out-of-grammar date (e.g., `15 Jun 2026`, `last week`) from prior session context