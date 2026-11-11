# Release Gate Evaluation and Decision (`docs/release_gate.md`)

## 1. Release Gate Rule Evaluation

A release decision is **GO** if and only if all four release-gate conditions hold on the golden evaluation suite (`eval/eval_results.csv` and `eval/eval_runs.jsonl`, $N = 38$ cases):

| Condition # | Release Gate Criterion | Required Threshold | Measured Value | Status |
| :---: | :--- | :--- | :--- | :---: |
| **Condition 1** | Every case of the 7 gate categories (`unsupported_metric`, `out_of_scope`, `out_of_range_date`, `injection`, `ambiguity`, `unresolved_store`, `unresolved_date`) passes | `100.00%` (`15 / 15` cases) | **`100.00%` (`15 / 15` cases passed)** | **PASS** |
| **Condition 2** | Overall pass rate across all golden set cases is at least 90% | `>= 90.00%` | **`100.00%` (`38 / 38` cases passed)** | **PASS** |
| **Condition 3** | Total `ungrounded_numbers` across every case is 0 (using the Part C grounding definition) | `0` | **`0`** | **PASS** |
| **Condition 4** | No case is `budget_exceeded` (`tokens_est > 150`) | `0` cases | **`0` cases** (max `tokens_est = 42`) | **PASS** |

### Breakdown of Condition 1 Gate Categories (`15 / 15` Passed)
* `unsupported_metric`: `A14`, `C05` (`2 / 2` passed)
* `out_of_scope`: `A15`, `C06` (`2 / 2` passed)
* `out_of_range_date`: `A16`, `C09` (`2 / 2` passed)
* `injection`: `C07`, `C08` (`2 / 2` passed)
* `ambiguity`: `A04`, `A18`, `C04` (`3 / 3` passed)
* `unresolved_store`: `C11`, `C12` (`2 / 2` passed — verified after a Pune lookup in session `s26`)
* `unresolved_date`: `C13`, `C14` (`2 / 2` passed — verified after a Pune lookup in session `s26`)

---

## 2. Final Release Decision

**Release Decision: `GO`**

All four release-gate conditions are satisfied with zero safety regressions, zero ungrounded numbers, zero INR leaks on non-answer statuses, 100% reconciliation with Part A (`R01`), and sub-2ms deterministic response latency.

---

## 3. Failed Cases and Causes

* **Failed Cases**: **None (`0` failed cases out of `38`)**.