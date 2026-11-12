import re
from agent.fetch import format_2dec
from agent.understand import PRODUCTS, STORES

ISO_DATE_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
NUMBER_TOKEN_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")

METRIC_LABELS = {
    "revenue_inr": "revenue",
    "daily_target_inr": "daily target",
    "footfall": "footfall",
    "stockout_hours": "stockout hours",
    "discount_pct": "discount",
}


def format_metric_value(metric, val):
    """Format a metric value for answer_text and return (formatted_in_text, raw_grounded_str)."""
    s = format_2dec(val)
    if metric in {"revenue_inr", "daily_target_inr"}:
        return f"INR {s}", s
    if metric in {"discount_pct", "achievement_pct"}:
        return f"{s}%", s
    if metric == "stockout_hours":
        return f"{s} hours", s
    return s, s


def format_weather_clause(w_data):
    """Format weather tool output with 1 decimal place and return (text, grounded_list)."""
    t_str = f"{float(w_data['temperature_c']):.1f}"
    h_str = f"{float(w_data['humidity_pct']):.1f}"
    w_str = f"{float(w_data['wind_kmh']):.1f}"
    r_str = f"{float(w_data['rain_mm']):.1f}"
    text = (
        f"Weather in {w_data['city']} on {w_data['date']}: temperature {t_str} C, "
        f"humidity {h_str}%, wind {w_str} km/h, rain {r_str} mm."
    )
    return text, [t_str, h_str, w_str, r_str]


def compute_ungrounded_numbers(answer_text, grounded_values):
    """Count digit runs in answer_text (after removing ISO dates and sized product names) not in grounded_values."""
    cleaned = ISO_DATE_PATTERN.sub(" ", answer_text)
    for _pid, full_name, _short in PRODUCTS:
        cleaned = re.sub(re.escape(full_name), " ", cleaned, flags=re.IGNORECASE)
    found_numbers = NUMBER_TOKEN_PATTERN.findall(cleaned)
    grounded_set = set(grounded_values)
    ungrounded = sum(1 for num in found_numbers if num not in grounded_set)
    return ungrounded


def build_answer(parsed, fetched=None):
    """Construct status, answer_text, evidence, grounded_values, and ungrounded_numbers."""
    intent = parsed["intent"]
    confidence = parsed["confidence"]
    missing = parsed["missing_entities"]

    # Precedence Rule 1: Intent itself (unsupported_metric -> Safe Failure; out_of_scope/diagnostic -> Escalated)
    if intent == "unsupported_metric":
        text = (
            "The requested metric field is not available in the approved field list. "
            "Approved store metrics are revenue, daily target, footfall, stockout hours, "
            "discount percentage, target achievement, inventory stock units, and customer feedback ratings."
        )
        return {
            "status": "Safe Failure",
            "answer_text": text,
            "evidence": [],
            "grounded_values": [],
            "ungrounded_numbers": compute_ungrounded_numbers(text, []),
        }

    if intent == "out_of_scope":
        text = (
            "This request is out of scope for the regional store analytics assistant. "
            "I can only answer read-only questions about approved store metrics, inventory thresholds, "
            "customer feedback, and store weather."
        )
        return {
            "status": "Escalated",
            "answer_text": text,
            "evidence": [],
            "grounded_values": [],
            "ungrounded_numbers": compute_ungrounded_numbers(text, []),
        }

    if intent == "diagnostic":
        text = (
            "Diagnostic and causal questions about why performance changed cannot be answered "
            "automatically; a human analyst is needed to investigate root causes."
        )
        return {
            "status": "Escalated",
            "answer_text": text,
            "evidence": [],
            "grounded_values": [],
            "ungrounded_numbers": compute_ungrounded_numbers(text, []),
        }

    # Precedence Rule 2: Missing required entity, unresolved store/date, ambiguity, or confidence < 0.7 -> Clarification Needed
    if (
        missing
        or parsed.get("ambiguous")
        or parsed.get("unresolved_store")
        or parsed.get("unresolved_date")
        or confidence < 0.7
    ):
        parts = []
        if "store" in missing or parsed.get("unresolved_store") or parsed.get("ambiguous_type") in {"store", "both"}:
            stores_str = ", ".join(STORES)
            parts.append(f"which store you want ({stores_str})")
        if "metric" in missing or parsed.get("ambiguous_type") in {"metric", "both"}:
            parts.append("which metric you want (revenue, daily target, footfall, stockout hours, or discount)")
        if "date" in missing or parsed.get("unresolved_date"):
            parts.append("which date or date range you want (in YYYY-MM-DD or D Month YYYY format, or between <date> and <date>)")
        if "product" in missing:
            parts.append("which product you want to check")
        if not parts:
            parts.append("your store, metric, and date")
        text = f"Clarification needed: please specify {' and '.join(parts)}."
        return {
            "status": "Clarification Needed",
            "answer_text": text,
            "evidence": [],
            "grounded_values": [],
            "ungrounded_numbers": compute_ungrounded_numbers(text, []),
        }

    # Precedence Rule 3: Date or range outside 2026-04-01 to 2026-06-29 -> Safe Failure
    if fetched and fetched.get("reason") == "out_of_range_date":
        text = (
            "The requested date is outside the available data range. "
            "Data is only available from 2026-04-01 to 2026-06-29."
        )
        return {
            "status": "Safe Failure",
            "answer_text": text,
            "evidence": [],
            "grounded_values": [],
            "ungrounded_numbers": compute_ungrounded_numbers(text, []),
        }

    # Precedence Rule 4: Data query failures (3 failed attempts -> Escalated; no record found -> Safe Failure)
    if fetched and not fetched.get("ok"):
        reason = fetched.get("reason")
        if reason in {"db_failure", "weather_error"}:
            text = (
                "The data query failed after three attempts due to a database or tool error. "
                "This request has been escalated."
            )
            return {
                "status": "Escalated",
                "answer_text": text,
                "evidence": [],
                "grounded_values": [],
                "ungrounded_numbers": compute_ungrounded_numbers(text, []),
            }
        text = "No matching record was found for the specified store, product, or date."
        return {
            "status": "Safe Failure",
            "answer_text": text,
            "evidence": [],
            "grounded_values": [],
            "ungrounded_numbers": compute_ungrounded_numbers(text, []),
        }

    # Precedence Rule 5: Drafted (when alert fires in target_vs_actual Poor band) else Answered
    data = fetched["data"]
    w_data = fetched.get("weather_data")
    evidence = []
    grounded_values = []

    if intent == "weather":
        w_text, w_vals = format_weather_clause(w_data)
        grounded_values.extend(w_vals)
        evidence.append({
            "source": "weather_tool",
            "fields": ["temperature_c", "humidity_pct", "wind_kmh", "rain_mm"],
            "store": w_data["city"],
            "date": w_data["date"],
        })
        return {
            "status": "Answered",
            "answer_text": w_text,
            "evidence": evidence,
            "grounded_values": grounded_values,
            "ungrounded_numbers": compute_ungrounded_numbers(w_text, grounded_values),
        }

    if intent == "lookup":
        metric = data["metric"]
        m_label = METRIC_LABELS.get(metric, metric)
        fmt_val, raw_str = format_metric_value(metric, data["value"])
        grounded_values.append(raw_str)
        evidence.append({
            "source": "store_daily_clean.csv",
            "fields": [metric],
            "store": data["store"],
            "date": data["date"],
        })
        if parsed["is_range"]:
            d1, d2 = parsed["date"]
            ans_text = f"{data['store']}'s average {m_label} between {d1} and {d2} was {fmt_val}."
        else:
            ans_text = f"{data['store']}'s {m_label} on {data['date']} was {fmt_val}."

        if w_data and w_data.get("ok"):
            w_text, w_vals = format_weather_clause(w_data)
            grounded_values.extend(w_vals)
            evidence.append({
                "source": "weather_tool",
                "fields": ["temperature_c", "humidity_pct", "wind_kmh", "rain_mm"],
                "store": w_data["city"],
                "date": w_data["date"],
            })
            ans_text = f"{ans_text} {w_text}"

        return {
            "status": "Answered",
            "answer_text": ans_text,
            "evidence": evidence,
            "grounded_values": grounded_values,
            "ungrounded_numbers": compute_ungrounded_numbers(ans_text, grounded_values),
        }

    if intent == "target_vs_actual":
        rev_fmt, rev_raw = format_metric_value("revenue_inr", data["revenue_inr"])
        tgt_fmt, tgt_raw = format_metric_value("daily_target_inr", data["daily_target_inr"])
        ach_fmt, ach_raw = format_metric_value("achievement_pct", data["achievement_pct"])
        band = data["performance_band"]

        grounded_values.extend([rev_raw, tgt_raw, ach_raw])
        evidence.append({
            "source": "store_daily_clean.csv",
            "fields": ["revenue_inr", "daily_target_inr", "achievement_pct", "performance_band"],
            "store": data["store"],
            "date": data["date"],
        })

        hit_word = "hit" if data["achievement_pct"] >= 100.0 else "did not hit"
        ans_text = (
            f"On {data['date']}, {data['store']} {hit_word} its target: actual revenue was {rev_fmt} "
            f"against a target of {tgt_fmt} ({ach_fmt} achievement, {band} band)."
        )
        if w_data and w_data.get("ok"):
            w_text, w_vals = format_weather_clause(w_data)
            grounded_values.extend(w_vals)
            evidence.append({
                "source": "weather_tool",
                "fields": ["temperature_c", "humidity_pct", "wind_kmh", "rain_mm"],
                "store": w_data["city"],
                "date": w_data["date"],
            })
            ans_text = f"{ans_text} {w_text}"

        status = "Drafted" if band == "Poor" else "Answered"
        return {
            "status": status,
            "answer_text": ans_text,
            "evidence": evidence,
            "grounded_values": grounded_values,
            "ungrounded_numbers": compute_ungrounded_numbers(ans_text, grounded_values),
        }

    if intent == "comparison":
        metric = data["metric"]
        m_label = METRIC_LABELS.get(metric, metric)
        direction = data["direction"]
        ranked = data["ranked"]
        item_strs = []
        for item in ranked:
            fmt_v, raw_v = format_metric_value(metric, item["value"])
            grounded_values.append(raw_v)
            item_strs.append(f"{item['store']} {fmt_v}")

        evidence.append({
            "source": "store_daily_clean.csv",
            "fields": [metric],
            "store": "all",
            "date": data["date"],
        })
        top_store = ranked[0]["store"]
        top_fmt, _ = format_metric_value(metric, ranked[0]["value"])
        ans_text = (
            f"The store with the {direction} {m_label} ({data['date']}) was {top_store} ({top_fmt}). "
            f"Full ranking: {'; '.join(item_strs)}."
        )
        return {
            "status": "Answered",
            "answer_text": ans_text,
            "evidence": evidence,
            "grounded_values": grounded_values,
            "ungrounded_numbers": compute_ungrounded_numbers(ans_text, grounded_values),
        }

    if intent == "inventory":
        product = data["product"]
        below = data["below"]
        evidence.append({
            "source": "inventory.csv",
            "fields": ["stock_units", "reorder_threshold"],
            "store": data["store"],
            "date": None,
        })
        if not below:
            ans_text = f"No store is below its reorder threshold for {product}."
        else:
            parts = []
            for row in below:
                su_str = str(int(row["stock_units"]))
                rt_str = str(int(row["reorder_threshold"]))
                grounded_values.extend([su_str, rt_str])
                parts.append(f"{row['store']} ({su_str} units against threshold {rt_str})")
            ans_text = f"Stores strictly below the reorder threshold for {product}: {', '.join(parts)}."
        return {
            "status": "Answered",
            "answer_text": ans_text,
            "evidence": evidence,
            "grounded_values": grounded_values,
            "ungrounded_numbers": compute_ungrounded_numbers(ans_text, grounded_values),
        }

    if intent == "feedback":
        avg_r_str = format_2dec(data["avg_rating"])
        rated_str = str(int(data["rated_rows"]))
        total_str = str(int(data["total_rows"]))
        top_theme = data["top_theme"]

        grounded_values.extend([avg_r_str, rated_str, total_str])
        evidence.append({
            "source": "feedback.csv",
            "fields": ["rating", "theme"],
            "store": data["store"],
            "date": None,
        })
        ans_text = (
            f"Customer feedback for {data['store']}: average rating {avg_r_str} "
            f"({rated_str} rated of {total_str} total reviews), most frequent theme is {top_theme}."
        )
        return {
            "status": "Answered",
            "answer_text": ans_text,
            "evidence": evidence,
            "grounded_values": grounded_values,
            "ungrounded_numbers": compute_ungrounded_numbers(ans_text, grounded_values),
        }
