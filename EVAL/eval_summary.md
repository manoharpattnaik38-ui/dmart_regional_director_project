# Evaluation Summary (`eval/eval_summary.md`)

Computed across all **38 golden evaluation cases** in `eval/eval_results.csv` and `eval/eval_runs.jsonl` (`WEATHER_MODE=stub`, `LLM_MODE=mock`).

---

## 1. Cost Metrics
* **Mean `tokens_est`**: `25.37` tokens (`964` total tokens across `38` cases)
* **Maximum `tokens_est`**: `42` tokens (Case `C05`, well below the `150`-token budget ceiling)
* **Total `tool_calls`**: `21` tool calls (`20` Python/SQL data queries + `2` `weather_tool` calls across `W01` and `W02`, with `W01` making `2` tool calls and `19` single-tool queries)
* **Number of `budget_exceeded` cases**: `0` (out of `38`)

---

## 2. Latency Metrics
* **Mean `latency_ms`**: `0.78` ms
* **90th Percentile (`P90`) `latency_ms` (linear interpolation)**: `1.32` ms
* **Maximum `latency_ms`**: `1.62` ms (Case `R01`, 90-day SQLite aggregation across 450 rows)

---

## 3. Quality Metrics
* **Overall Pass Rate**: **`100.00%`** (`38 / 38` cases passed)
* **Total `ungrounded_numbers`**: **`0`** across all `38` cases

### Pass Count per Category

| Category | Passed Cases | Total Cases | Pass Rate |
| :--- | :---: | :---: | :---: |
| `lookup` | 6 | 6 | 100.00% |
| `target_vs_actual` | 3 | 3 | 100.00% |
| `comparison` | 3 | 3 | 100.00% |
| `inventory` | 1 | 1 | 100.00% |
| `feedback` | 1 | 1 | 100.00% |
| `weather` | 2 | 2 | 100.00% |
| `retry` | 2 | 2 | 100.00% |
| `diagnostic` | 1 | 1 | 100.00% |
| `typo` | 2 | 2 | 100.00% |
| `synonym` | 2 | 2 | 100.00% |
| `ambiguity` | 3 | 3 | 100.00% |
| `unsupported_metric` | 2 | 2 | 100.00% |
| `out_of_scope` | 2 | 2 | 100.00% |
| `injection` | 2 | 2 | 100.00% |
| `out_of_range_date` | 2 | 2 | 100.00% |
| `unresolved_store` | 2 | 2 | 100.00% |
| `unresolved_date` | 2 | 2 | 100.00% |
| **Total** | **38** | **38** | **100.00%** |

---

## 4. Safety Metrics
* **Pass rate of `injection`, `unsupported_metric`, and `out_of_scope`**: **`100.00%`** (`6 / 6` cases passed: `A14`, `C05`, `A15`, `C06`, `C07`, `C08`)
* **Non-answer replies (`Safe Failure`, `Escalated`, `Clarification Needed`) stating an `INR` figure in `answer_text` (from `eval/eval_runs.jsonl`)**: **`0`** (out of `19` non-answer replies)
* **`.gitignore` lists `.env`**: **`Yes`** (`True`)