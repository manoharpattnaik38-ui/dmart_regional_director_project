# DMart Regional Director Assistant: Store Diagnosis and Grounded Conversational Analytics Agent

## 1. Purpose
This repository delivers two connected artefacts for **Kavita Rao**, Regional Operations Director for DMart (Avenue Supermarts) across five stores (**Mumbai, Pune, Hyderabad, Bengaluru, and Ahmedabad**):
1. **Part A — Data Foundation & Premise Test**: Cleans the synthetic regional store dataset (`453` raw rows -> `450` cleaned rows) and tests the working hypothesis that stockouts are driving Pune's low daily revenue. The analysis proves that Pune ranks **4th of 5** in stockout hours (`2.32` hrs/day vs `2.74` all-store mean) while its revenue deficit (`-26.14%`) is explained by a structural **footfall deficit (`-25.00%`)**, with revenue per visitor (`INR 419.29`) within `1.52%` of the regional figure (`INR 425.75`).
2. **Parts B, C & D — Grounded Conversational Analytics Agent, Weather Tool & Evaluation**: Specifies, implements, and evaluates a deterministic, SQLite- and Python-backed conversational assistant that answers routine store operations questions with 100% numerical grounding (`ungrounded_numbers == 0`), strict 11-field governance, bounded 3-attempt query retries, weather integration, and a verified **GO** release gate decision (`38/38` golden set cases passing).

---

## 2. Free Offline Setup and Execution Order

Everything graded runs 100% offline using Python 3.9+, `pandas`, `numpy`, and the Python standard library (`sqlite3`, `decimal`, `difflib`, `time`, `json`, `csv`), with no external accounts or API keys required. Default settings are `LLM_MODE=mock` and `WEATHER_MODE=stub`.

### Install Dependencies
```bash
pip install -r requirements.txt
