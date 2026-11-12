import os
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
from tools.weather import get_weather

DATA_MIN_DATE = "2026-04-01"
DATA_MAX_DATE = "2026-06-29"

# Exactly the 11 reportable metric fields approved in Part B
APPROVED_METRIC_FIELDS = {
    "revenue_inr",
    "daily_target_inr",
    "footfall",
    "stockout_hours",
    "discount_pct",
    "achievement_pct",
    "performance_band",
    "stock_units",
    "reorder_threshold",
    "rating",
    "theme",
}

# Filter and grouping keys allowed in WHERE, GROUP BY, or row labels
ALLOWED_KEY_FIELDS = {"store", "store_id", "date", "product", "product_id"}
ALLOWED_TABLES = {"store_daily_clean", "inventory", "feedback"}
ALLOWED_SORT_DIRS = {"ASC", "DESC"}


def round_half_up_dec(val_cents, count):
    """Divide integer cents by count and round half-up to 2 decimal places."""
    d_sum = Decimal(int(val_cents)) / Decimal(100)
    d_mean = d_sum / Decimal(int(count))
    return float(d_mean.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_2dec(val):
    """Format a numeric value rounded half-up to 2 decimal places as string."""
    d = Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{d:.2f}"


class DataStore:
    """Holds cleaned pandas DataFrames for Python lookups and an in-memory/local SQLite connection."""

    def __init__(self):
        self.store_daily_df = pd.read_csv("data/store_daily_clean.csv")
        self.inventory_df = pd.read_csv("data/inventory.csv")
        self.feedback_df = pd.read_csv("data/feedback.csv")

        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.store_daily_df.to_sql("store_daily_clean", self.conn, index=False, if_exists="replace")
        self.inventory_df.to_sql("inventory", self.conn, index=False, if_exists="replace")
        self.feedback_df.to_sql("feedback", self.conn, index=False, if_exists="replace")


_DATA_STORE = None


def get_datastore():
    global _DATA_STORE
    if _DATA_STORE is None:
        _DATA_STORE = DataStore()
    return _DATA_STORE


def validate_query_request(table, measured_fields, key_fields=None, sort_dir=None):
    """Validate table, reportable metric fields, key columns, and sort direction against whitelists."""
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Unapproved table: {table}")
    for mf in measured_fields:
        if mf not in APPROVED_METRIC_FIELDS:
            raise ValueError(f"Unapproved metric field: {mf}")
    if key_fields:
        for kf in key_fields:
            if kf not in ALLOWED_KEY_FIELDS:
                raise ValueError(f"Unapproved key field: {kf}")
    if sort_dir is not None and sort_dir not in ALLOWED_SORT_DIRS:
        raise ValueError(f"Unapproved sort direction: {sort_dir}")


def check_date_in_range(date_val, is_range):
    """Return True if date or range is within 2026-04-01 to 2026-06-29 inclusive."""
    if is_range:
        d1, d2 = date_val
        return (DATA_MIN_DATE <= d1 <= DATA_MAX_DATE) and (DATA_MIN_DATE <= d2 <= DATA_MAX_DATE)
    return DATA_MIN_DATE <= date_val <= DATA_MAX_DATE


def _run_with_retry(query_fn):
    """Execute a data query function with at most 3 attempts and SIMULATE_DB_FAILURES support."""
    sim_Env = os.environ.get("SIMULATE_DB_FAILURES", "0").strip()
    try:
        sim_failures = int(sim_Env)
    except ValueError:
        sim_failures = 0

    max_attempts = 3
    last_err = None
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt <= sim_failures:
                raise RuntimeError(f"Simulated database failure on attempt {attempt}")
            result = query_fn()
            return True, result, attempt, None
        except Exception as exc:
            last_err = str(exc)
    return False, None, max_attempts, last_err


def fetch(parsed):
    """Run validated data queries and/or weather tool calls according to parsed intent."""
    intent = parsed["intent"]
    store = parsed["store"]
    metric = parsed["metric"]
    date_val = parsed["date"]
    is_range = parsed["is_range"]
    product = parsed["product"]
    weather_req = parsed["weather"]
    direction = parsed.get("direction", "highest")

    # Date range validation for date-using intents (Rule 3 of status precedence)
    if intent in {"lookup", "target_vs_actual", "comparison", "weather"}:
        if not check_date_in_range(date_val, is_range):
            return {
                "ok": False,
                "reason": "out_of_range_date",
                "route": "none",
                "executed": None,
                "attempts": 0,
                "tools_called": [],
                "tool_calls": 0,
                "data": None,
                "weather_data": None,
            }

    ds = get_datastore()

    # 1. Standalone weather intent
    if intent == "weather":
        w_res = get_weather(store, date_val)
        return {
            "ok": w_res.get("ok", False),
            "reason": None if w_res.get("ok") else "weather_error",
            "route": "weather",
            "executed": f"get_weather(city='{store}', date='{date_val}')",
            "attempts": 0,
            "tools_called": ["weather_tool"],
            "tool_calls": 1,
            "data": None,
            "weather_data": w_res,
        }

    # 2. One-store, one-date lookup -> Python function route
    if intent == "lookup" and not is_range:
        validate_query_request("store_daily_clean", [metric], ["store", "date"])
        executed_str = f"python:lookup_single_date(store='{store}', date='{date_val}', metric='{metric}')"

        def _py_lookup():
            df = ds.store_daily_df
            sub = df[(df["store"] == store) & (df["date"] == date_val)]
            if sub.empty:
                return None
            return float(sub.iloc[0][metric])

        ok, val, attempts, _ = _run_with_retry(_py_lookup)
        route = "python+weather" if weather_req else "python"
        tools_called = []
        tool_calls = 1

        if not ok:
            return {
                "ok": False,
                "reason": "db_failure",
                "route": "python",
                "executed": executed_str,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        if val is None:
            return {
                "ok": False,
                "reason": "no_record",
                "route": "python",
                "executed": executed_str,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }

        w_res = None
        if weather_req:
            w_res = get_weather(store, date_val)
            tools_called.append("weather_tool")
            tool_calls += 1

        return {
            "ok": True,
            "reason": None,
            "route": route,
            "executed": executed_str,
            "attempts": attempts,
            "tools_called": tools_called,
            "tool_calls": tool_calls,
            "data": {"store": store, "date": date_val, "metric": metric, "value": val},
            "weather_data": w_res,
        }

    # 3. One-store over a date range lookup -> SQL route
    if intent == "lookup" and is_range:
        validate_query_request("store_daily_clean", [metric], ["store", "date"])
        d1, d2 = date_val
        sql = (
            f"SELECT COUNT({metric}), SUM(CAST(ROUND({metric} * 100) AS INTEGER)) "
            f"FROM store_daily_clean WHERE store = ? AND date BETWEEN ? AND ?"
        )

        def _sql_range_lookup():
            cur = ds.conn.cursor()
            cur.execute(sql, (store, d1, d2))
            row = cur.fetchone()
            if not row or row[0] == 0 or row[1] is None:
                return None
            return round_half_up_dec(row[1], row[0])

        ok, avg_val, attempts, _ = _run_with_retry(_sql_range_lookup)
        if not ok:
            return {
                "ok": False,
                "reason": "db_failure",
                "route": "sql",
                "executed": sql,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        if avg_val is None:
            return {
                "ok": False,
                "reason": "no_record",
                "route": "sql",
                "executed": sql,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        return {
            "ok": True,
            "reason": None,
            "route": "sql",
            "executed": sql,
            "attempts": attempts,
            "tools_called": [],
            "tool_calls": 1,
            "data": {"store": store, "date": f"{d1} to {d2}", "metric": metric, "value": avg_val},
            "weather_data": None,
        }

    # 4. Target vs actual check -> Python function route
    if intent == "target_vs_actual":
        fields = ["revenue_inr", "daily_target_inr", "achievement_pct", "performance_band"]
        validate_query_request("store_daily_clean", fields, ["store", "date"])
        executed_str = f"python:target_vs_actual(store='{store}', date='{date_val}')"

        def _py_tva():
            df = ds.store_daily_df
            sub = df[(df["store"] == store) & (df["date"] == date_val)]
            if sub.empty:
                return None
            r = sub.iloc[0]
            return {
                "store": store,
                "date": date_val,
                "revenue_inr": float(r["revenue_inr"]),
                "daily_target_inr": float(r["daily_target_inr"]),
                "achievement_pct": float(r["achievement_pct"]),
                "performance_band": str(r["performance_band"]),
            }

        ok, tva_data, attempts, _ = _run_with_retry(_py_tva)
        route = "python+weather" if weather_req else "python"
        tools_called = []
        tool_calls = 1

        if not ok:
            return {
                "ok": False,
                "reason": "db_failure",
                "route": "python",
                "executed": executed_str,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        if tva_data is None:
            return {
                "ok": False,
                "reason": "no_record",
                "route": "python",
                "executed": executed_str,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }

        w_res = None
        if weather_req:
            w_res = get_weather(store, date_val)
            tools_called.append("weather_tool")
            tool_calls += 1

        return {
            "ok": True,
            "reason": None,
            "route": route,
            "executed": executed_str,
            "attempts": attempts,
            "tools_called": tools_called,
            "tool_calls": tool_calls,
            "data": tva_data,
            "weather_data": w_res,
        }

    # 5. Cross-store comparison -> SQL route
    if intent == "comparison":
        sort_dir = "ASC" if direction == "lowest" else "DESC"
        validate_query_request("store_daily_clean", [metric], ["store", "date"], sort_dir)
        d1, d2 = date_val if is_range else (date_val, date_val)
        sql = (
            f"SELECT store, COUNT({metric}) AS cnt, "
            f"SUM(CAST(ROUND({metric} * 100) AS INTEGER)) AS sum_cents "
            f"FROM store_daily_clean WHERE date BETWEEN ? AND ? GROUP BY store"
        )

        def _sql_comparison():
            cur = ds.conn.cursor()
            cur.execute(sql, (d1, d2))
            rows = cur.fetchall()
            if not rows:
                return None
            ranked = []
            for st_name, cnt, sum_cents in rows:
                if cnt > 0 and sum_cents is not None:
                    avg_v = round_half_up_dec(sum_cents, cnt)
                    ranked.append({"store": st_name, "value": avg_v})
            if not ranked:
                return None
            # Sort by value rounded at 2 decimals (DESC or ASC), ties broken alphabetically by store name
            if direction == "lowest":
                ranked.sort(key=lambda x: (round(x["value"], 2), x["store"]))
            else:
                ranked.sort(key=lambda x: (-round(x["value"], 2), x["store"]))
            return ranked

        ok, ranked_rows, attempts, _ = _run_with_retry(_sql_comparison)
        if not ok:
            return {
                "ok": False,
                "reason": "db_failure",
                "route": "sql",
                "executed": sql,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        if ranked_rows is None:
            return {
                "ok": False,
                "reason": "no_record",
                "route": "sql",
                "executed": sql,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        return {
            "ok": True,
            "reason": None,
            "route": "sql",
            "executed": sql,
            "attempts": attempts,
            "tools_called": [],
            "tool_calls": 1,
            "data": {
                "metric": metric,
                "date": f"{d1} to {d2}" if is_range else d1,
                "direction": direction,
                "ranked": ranked_rows,
            },
            "weather_data": None,
        }

    # 6. Inventory check -> SQL route
    if intent == "inventory":
        validate_query_request("inventory", ["stock_units", "reorder_threshold"], ["store", "product"])
        if store:
            sql = (
                "SELECT store, stock_units, reorder_threshold FROM inventory "
                "WHERE product = ? AND store = ? ORDER BY stock_units ASC, store ASC"
            )
            params = (product, store)
        else:
            sql = (
                "SELECT store, stock_units, reorder_threshold FROM inventory "
                "WHERE product = ? ORDER BY stock_units ASC, store ASC"
            )
            params = (product,)

        def _sql_inventory():
            cur = ds.conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            if not rows:
                return None
            below = [
                {"store": r[0], "stock_units": int(r[1]), "reorder_threshold": int(r[2])}
                for r in rows
                if int(r[1]) < int(r[2])
            ]
            return {"all_rows": len(rows), "below": below}

        ok, inv_res, attempts, _ = _run_with_retry(_sql_inventory)
        if not ok:
            return {
                "ok": False,
                "reason": "db_failure",
                "route": "sql",
                "executed": sql,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        if inv_res is None:
            return {
                "ok": False,
                "reason": "no_record",
                "route": "sql",
                "executed": sql,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        return {
            "ok": True,
            "reason": None,
            "route": "sql",
            "executed": sql,
            "attempts": attempts,
            "tools_called": [],
            "tool_calls": 1,
            "data": {"product": product, "store": store or "all", "below": inv_res["below"]},
            "weather_data": None,
        }

    # 7. Feedback summary -> SQL route
    if intent == "feedback":
        validate_query_request("feedback", ["rating", "theme"], ["store"])
        sql_stats = (
            "SELECT COUNT(*), COUNT(rating), "
            "SUM(CASE WHEN rating IS NOT NULL AND rating != '' THEN CAST(ROUND(rating * 100) AS INTEGER) ELSE 0 END) "
            "FROM feedback WHERE store = ?"
        )
        sql_theme = (
            "SELECT theme, COUNT(*) AS cnt FROM feedback WHERE store = ? "
            "GROUP BY theme ORDER BY cnt DESC, theme ASC LIMIT 1"
        )

        def _sql_feedback():
            cur = ds.conn.cursor()
            cur.execute(sql_stats, (store,))
            s_row = cur.fetchone()
            if not s_row or s_row[0] == 0:
                return None
            total_rows, rated_rows, sum_cents = int(s_row[0]), int(s_row[1]), int(s_row[2] or 0)
            avg_rating = round_half_up_dec(sum_cents, rated_rows) if rated_rows > 0 else 0.0
            cur.execute(sql_theme, (store,))
            t_row = cur.fetchone()
            top_theme = t_row[0] if t_row else ""
            return {
                "store": store,
                "avg_rating": avg_rating,
                "rated_rows": rated_rows,
                "total_rows": total_rows,
                "top_theme": top_theme,
            }

        ok, fb_res, attempts, _ = _run_with_retry(_sql_feedback)
        if not ok:
            return {
                "ok": False,
                "reason": "db_failure",
                "route": "sql",
                "executed": sql_stats,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        if fb_res is None:
            return {
                "ok": False,
                "reason": "no_record",
                "route": "sql",
                "executed": sql_stats,
                "attempts": attempts,
                "tools_called": [],
                "tool_calls": 1,
                "data": None,
                "weather_data": None,
            }
        return {
            "ok": True,
            "reason": None,
            "route": "sql",
            "executed": f"{sql_stats}; {sql_theme}",
            "attempts": attempts,
            "tools_called": [],
            "tool_calls": 1,
            "data": fb_res,
            "weather_data": None,
        }
