"""Deterministic natural-language interpreter for the DMart regional analytics assistant."""
import re
from datetime import date as dt_date, timedelta
from difflib import SequenceMatcher

AS_OF_DATE = "2026-06-30"
YESTERDAY_ISO = "2026-06-29"

STORES = ["Mumbai", "Pune", "Hyderabad", "Bengaluru", "Ahmedabad"]
STORE_LOWER_MAP = {s.lower(): s for s in STORES}
STORE_ALIASES = {"bangalore": "Bengaluru"}

PRODUCTS = [
    ("P01", "Amul Milk 1L", "Amul Milk"),
    ("P02", "Toor Dal 1kg", "Toor Dal"),
    ("P03", "Basmati Rice 5kg", "Basmati Rice"),
    ("P04", "Sunflower Oil 1L", "Sunflower Oil"),
    ("P05", "Iodised Salt 1kg", "Iodised Salt"),
    ("P06", "Instant Noodles 4-pack", "Instant Noodles"),
    ("P07", "Glucose Biscuits 200g", "Glucose Biscuits"),
    ("P08", "Detergent Powder 1kg", "Detergent Powder"),
]

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}
ABBR_MONTHS = {"jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"}

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
PLURAL_WEEKDAYS = {
    "mondays", "tuesdays", "wednesdays", "thursdays",
    "fridays", "saturdays", "sundays", "weekdays", "weekends",
}

STOP_WORDS = {
    "hello", "thanks", "thank", "kindly", "please", "display", "compare",
    "which", "what", "whats", "how", "why", "did", "and", "show", "check",
    "report", "where", "would", "could", "can", "will", "give", "tell", "list",
}

BRIEF_PROPER_NOUNS = {
    "dmart", "avenue", "supermarts", "kavita", "rao", "meteo",
    "github", "python", "sqlite", "postgresql", "markdown",
}

BRAND_PERSONA_NOUNS = {"dmart", "avenue", "supermarts", "kavita", "rao"}

WEATHER_WORDS = {"weather", "rain", "rains", "temperature", "temperatures", "humidity", "hot", "cold"}

PROHIBITED_WORDS = {
    "ignore", "ignores", "disregard", "disregards", "override", "overrides",
    "bypass", "bypasses", "forget", "forgets", "send", "sends", "email", "emails",
    "whatsapp", "whatsapps", "purchase", "purchases", "buy", "buys", "restock", "restocks",
}

UNSUPPORTED_WORDS = {
    "profit", "profits", "margin", "margins", "marketing", "cost", "costs",
    "expense", "expenses", "shortfall", "shortfalls", "efficiency", "efficiencies",
    "weekend", "weekends", "spend", "spends",
}

DIAGNOSTIC_WORDS = {"why", "trend", "trends", "reason", "reasons"}

FEEDBACK_WORDS = {"feedback", "feedbacks", "review", "reviews", "rating", "ratings"}

TARGET_PARTNERS = {
    "hit", "hits", "met", "meet", "meets", "miss", "missed", "misses",
    "beat", "beats", "exceed", "exceeded", "exceeds", "achieve", "achieved", "achieves",
    "reach", "reached", "reaches", "below", "above", "against", "versus", "vs",
}

COMPARISON_WORDS = {"which", "highest", "lowest", "best", "worst"}

METRIC_SYNONYMS = {
    "revenue": "revenue_inr",
    "revenues": "revenue_inr",
    "revenue_inr": "revenue_inr",
    "sales": "revenue_inr",
    "sale": "revenue_inr",
    "turnover": "revenue_inr",
    "turnovers": "revenue_inr",
    "earnings": "revenue_inr",
    "earning": "revenue_inr",
    "target": "daily_target_inr",
    "targets": "daily_target_inr",
    "daily_target_inr": "daily_target_inr",
    "footfall": "footfall",
    "footfalls": "footfall",
    "visitor": "footfall",
    "visitors": "footfall",
    "stockout": "stockout_hours",
    "stockouts": "stockout_hours",
    "stockout_hours": "stockout_hours",
    "discount": "discount_pct",
    "discounts": "discount_pct",
    "discount_pct": "discount_pct",
}

PRODUCT_WORDS = set()
for _pid, _full, _short in PRODUCTS:
    for _w in re.findall(r"[a-zA-Z0-9]+", _full.lower()):
        PRODUCT_WORDS.add(_w)
        PRODUCT_WORDS.add(_w + "s")

ALL_KEYWORDS = (
    STOP_WORDS
    | WEATHER_WORDS
    | PROHIBITED_WORDS
    | UNSUPPORTED_WORDS
    | DIAGNOSTIC_WORDS
    | FEEDBACK_WORDS
    | TARGET_PARTNERS
    | COMPARISON_WORDS
    | set(METRIC_SYNONYMS.keys())
    | set(MONTHS.keys())
    | ABBR_MONTHS
    | set(WEEKDAYS.keys())
    | PLURAL_WEEKDAYS
    | PRODUCT_WORDS
    | {
        "order", "orders", "reorder", "reorders", "inventory", "inventories",
        "threshold", "thresholds", "level", "levels", "point", "points",
        "stock", "stocks", "unit", "units", "store", "stores",
        "customer", "customers", "say", "says", "saying",
        "achievement", "achievements", "performance", "band", "bands",
        "average", "averages", "mean", "total", "totals", "hour", "hours",
        "daily", "weekly", "monthly", "quarterly", "yearly", "annual",
        "today", "tomorrow", "yesterday", "week", "weeks", "month", "months",
        "quarter", "quarters", "year", "years", "between", "from", "until",
        "till", "during", "since", "through", "throughout", "before", "after",
        "within", "over", "past", "previous", "ago", "recent", "latest",
        "now", "lately", "morning", "rule", "rules", "place", "short", "fall",
    }
)

MONTH_PREPOSITIONS = {
    "in", "on", "of", "during", "since", "for", "from", "until",
    "till", "by", "to", "through", "throughout", "before", "after",
    "within", "over",
}


def _clean_word(token):
    """Strip punctuation and possessive suffix from a raw token."""
    t = token.strip(".,?!:;()[]{}\"'")
    has_possessive = False
    if t.lower().endswith("'s") or t.lower().endswith("’s"):
        has_possessive = True
        t = t[:-2]
    return t, has_possessive


def _detect_products(q_norm):
    """Return list of matched canonical product names."""
    found = []
    q_low = q_norm.lower()
    for _pid, full_name, short_name in PRODUCTS:
        if re.search(r"\b" + re.escape(full_name.lower()) + r"\b", q_low) or re.search(
            r"\b" + re.escape(short_name.lower()) + r"\b", q_low
        ):
            found.append(full_name)
    return found


def _is_prohibited_or_override(q_norm, lower_words):
    """Check Intent Rule 1: request to ignore/override rules or take a prohibited action."""
    if any(w in PROHIBITED_WORDS for w in lower_words):
        return True
    if re.search(r"\bplace\s+an\s+order\b", q_norm, flags=re.IGNORECASE):
        return True

    # Check 'order' or 'reorder' used as an imperative
    # Imperative positions:
    # (a) first word of the question
    # (b) directly after please, kindly, can you, could you, will you, would you, go ahead and
    # (c) after a comma-address at the start such as "Pune, reorder Amul Milk"
    imperative_patterns = [
        r"^\s*(?:re)?order\b(?:\s+(\w+))?",
        r"\b(?:please|kindly|can\s+you|could\s+you|will\s+you|would\s+you|go\s+ahead\s+and)\s+(?:re)?order\b(?:\s+(\w+))?",
        r"^\s*[A-Za-z]+\s*,\s*(?:please\s+|kindly\s+)?(?:re)?order\b(?:\s+(\w+))?",
    ]
    for pat in imperative_patterns:
        for m in re.finditer(pat, q_norm, flags=re.IGNORECASE):
            next_word = (m.group(1) or "").lower().rstrip(".,?!:;")
            if next_word not in {"threshold", "thresholds", "level", "levels", "point", "points"}:
                return True
    return False


def _is_unsupported_metric(q_norm, lower_words):
    """Check Intent Rule 2: column outside the approved 11 fields."""
    if any(w in UNSUPPORTED_WORDS for w in lower_words):
        return True
    if re.search(r"\bper\s+(?:footfall|falls|visitor|visitors)\b", q_norm, flags=re.IGNORECASE):
        return True
    if re.search(r"\b(?:revenue_per_footfall|marketing_efficiency|shortfall_inr|weekend_flag|marketing_spend_inr)\b", q_norm, flags=re.IGNORECASE):
        return True
    return False


def _extract_metrics(q_norm, lower_words):
    """Return ordered list of distinct canonical metrics mentioned in the question."""
    metrics = []
    # Check phrase "daily target" first so it maps cleanly to daily_target_inr
    for w in lower_words:
        if w in METRIC_SYNONYMS:
            m = METRIC_SYNONYMS[w]
            if m not in metrics:
                metrics.append(m)
    return metrics


def _parse_single_date_token(text):
    """Parse a single valid date string in ISO YYYY-MM-DD, D Month YYYY, or yesterday."""
    s = text.strip()
    if s.lower() == "yesterday":
        return YESTERDAY_ISO, True
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        try:
            y, m, d = map(int, s.split("-"))
            dt_date(y, m, d)
            return s, True
        except ValueError:
            return None, False
    m_dmy = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", s)
    if m_dmy:
        day_str, mon_str, yr_str = m_dmy.groups()
        mon_low = mon_str.lower()
        if mon_low in MONTHS:
            try:
                dt_obj = dt_date(int(yr_str), MONTHS[mon_low], int(day_str))
                return dt_obj.isoformat(), True
            except ValueError:
                return None, False
    return None, False


def _extract_dates(question):
    """Parse dates according to the strict closed grammar and detect unresolved named dates."""
    q = question
    unresolved_date = False
    resolved_date = None
    is_range = False

    # Mask out sized product names so numbers like 1L, 1kg, 5kg, 200g, 4-pack don't trigger date patterns
    q_masked = q
    for _pid, full_name, _short in PRODUCTS:
        q_masked = re.sub(re.escape(full_name), " ", q_masked, flags=re.IGNORECASE)

    # Remove frequency phrases that belong to a metric phrase
    q_masked = re.sub(
        r"\b(?:daily|weekly|monthly|quarterly|yearly|annual)\b",
        " ",
        q_masked,
        flags=re.IGNORECASE,
    )
    q_masked = re.sub(
        r"\bper\s+(?:day|week|month|year)\b",
        " ",
        q_masked,
        flags=re.IGNORECASE,
    )

    # Check explicit invalid date forms:
    # 1. Ordinal day dates like 15th May 2026 or 1st June
    if re.search(r"\b\d{1,2}(?:st|nd|rd|th)\s+[A-Za-z]+", q_masked, flags=re.IGNORECASE):
        unresolved_date = True

    # 2. Month D, YYYY or Month D YYYY (e.g., May 15, 2026)
    month_names_pat = "|".join(list(MONTHS.keys()) + list(ABBR_MONTHS))
    if re.search(rf"\b(?:{month_names_pat})\s+\d{{1,2}}(?:st|nd|rd|th)?(?:\s*,\s*|\s+)\d{{4}}\b", q_masked, flags=re.IGNORECASE):
        unresolved_date = True

    # 3. D AbbrMonth YYYY or D AbbrMonth (e.g., 15 Jun 2026)
    abbr_pat = "|".join(ABBR_MONTHS)
    if re.search(rf"\b\d{{1,2}}\s+(?:{abbr_pat})\b", q_masked, flags=re.IGNORECASE):
        unresolved_date = True
    if re.search(rf"\b(?:{abbr_pat})\s+\d{{1,2}}\b", q_masked, flags=re.IGNORECASE):
        unresolved_date = True

    # 4. Malformed ISO-like dates: YYYY-M-D (not 2-digit month/day), YYYYMMDD (8 digits), YYYY-Wxx
    for m_hyph in re.finditer(r"\b\d{4}-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?\b", q_masked):
        tok = m_hyph.group(0)
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", tok):
            unresolved_date = True
        else:
            _, ok = _parse_single_date_token(tok)
            if not ok:
                unresolved_date = True

    if re.search(r"\b20\d{6}\b", q_masked):
        unresolved_date = True

    # 5. Relative / period phrases outside the grammar
    relative_patterns = [
        r"\btoday\b",
        r"\btomorrow\b",
        r"\b(?:last|this|next|past|previous)\s+(?:\d+\s+)?(?:day|days|week|weeks|month|months|quarter|quarters|year|years|morning|evening|night)\b",
        r"\b(?:week|month|quarter|year)[\s-]+to[\s-]+date\b",
        r"\b(?:quarter|month|year)[\s-]+end\b",
        r"\b(?:ytd|mtd|qtd|eod|fy\d{2,4}|q[1-4])\b",
        r"\b(?:ago|recent|recently|latest|now|lately|this\s+morning)\b",
        r"\bfrom\s+\S+(?:\s+[A-Za-z]+\s+\d{4})?\s+to\s+\S+",
    ]
    for pat in relative_patterns:
        if re.search(pat, q_masked, flags=re.IGNORECASE):
            unresolved_date = True

    # Check valid `between <date> and <date>` first
    single_date_pat = r"(?:\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4}|yesterday)"
    between_re = re.compile(
        rf"\bbetween\s+({single_date_pat})\s+and\s+({single_date_pat})\b",
        flags=re.IGNORECASE,
    )
    between_matches = list(between_re.finditer(q_masked))
    q_rem = q_masked

    if len(between_matches) > 1:
        unresolved_date = True
    elif len(between_matches) == 1:
        bm = between_matches[0]
        d1_str, d2_str = bm.group(1), bm.group(2)
        d1, ok1 = _parse_single_date_token(d1_str)
        d2, ok2 = _parse_single_date_token(d2_str)
        if not (ok1 and ok2) or d1 > d2:
            unresolved_date = True
        else:
            resolved_date = (d1, d2)
            is_range = True
        # Blank out the matched between phrase from q_rem
        q_rem = q_masked[: bm.start()] + " " + q_masked[bm.end() :]

    # Find any remaining single dates in q_rem
    rem_single_matches = list(re.finditer(rf"\b({single_date_pat})\b", q_rem, flags=re.IGNORECASE))
    parsed_singles = []
    for sm in rem_single_matches:
        d_val, ok = _parse_single_date_token(sm.group(1))
        if not ok:
            unresolved_date = True
        else:
            parsed_singles.append((d_val, sm.start(), sm.end()))

    if is_range and parsed_singles:
        # A second date outside between <date> and <date>
        unresolved_date = True
    elif not is_range:
        if len(parsed_singles) > 1:
            unresolved_date = True
        elif len(parsed_singles) == 1:
            resolved_date = parsed_singles[0][0]
            # Blank out the valid single date from q_rem
            s_start, s_end = parsed_singles[0][1], parsed_singles[0][2]
            q_rem = q_rem[:s_start] + " " + q_rem[s_end:]

    # Check bare years (e.g. 2026, 2025) remaining in q_rem
    if re.search(r"\b(?:19|20)\d{2}\b", q_rem):
        unresolved_date = True

    # Check D Month (with no year, e.g., 15 May) remaining in q_rem
    full_months_pat = "|".join(MONTHS.keys())
    if re.search(rf"\b\d{{1,2}}\s+(?:{full_months_pat})\b", q_rem, flags=re.IGNORECASE):
        unresolved_date = True
    if re.search(rf"\b(?:{full_months_pat})\s+\d{{1,2}}\b", q_rem, flags=re.IGNORECASE):
        unresolved_date = True

    # Check standalone month names in q_rem (handling 'may' and 'march' verb exceptions)
    rem_tokens = re.findall(r"[A-Za-z]+", q_rem)
    for idx, tok in enumerate(rem_tokens):
        t_low = tok.lower()
        if t_low in MONTHS:
            prev_low = rem_tokens[idx - 1].lower() if idx > 0 else ""
            next_low = rem_tokens[idx + 1].lower() if idx + 1 < len(rem_tokens) else ""
            if t_low in {"may", "march"}:
                if tok == "May" and next_low in {"i", "we", "you", "be"}:
                    continue
                if tok.islower():
                    if prev_low in MONTH_PREPOSITIONS:
                        unresolved_date = True
                    continue
                # Capitalised May/March not before I/we/you/be: counts as month name
                unresolved_date = True
            else:
                unresolved_date = True
        elif t_low in ABBR_MONTHS:
            unresolved_date = True

    # Check weekday words in q_rem
    for idx, tok in enumerate(rem_tokens):
        t_low = tok.lower()
        if t_low in PLURAL_WEEKDAYS:
            if not (is_range and resolved_date and not unresolved_date):
                unresolved_date = True
        elif t_low in WEEKDAYS:
            if is_range or resolved_date is None or unresolved_date:
                unresolved_date = True
            else:
                # Must match the weekday of the single valid date
                y, m, d = map(int, resolved_date.split("-"))
                actual_wd = dt_date(y, m, d).weekday()
                if actual_wd != WEEKDAYS[t_low]:
                    unresolved_date = True

    if unresolved_date:
        return None, False, True
    return resolved_date, is_range, False


def _extract_stores(question, has_metric_or_weather_or_date):
    """Extract resolved stores (with confidence) and check for unresolved named stores."""
    raw_tokens = question.split()
    resolved_stores = []  # list of (store_name, confidence)
    unresolved_store = False

    # Build cleaned token list with position metadata
    cleaned_tokens = []
    for idx, raw_tok in enumerate(raw_tokens):
        base, has_poss = _clean_word(raw_tok)
        cleaned_tokens.append((idx, raw_tok, base, has_poss))

    # First pass: check exact store matches and explicit alias 'Bangalore'
    matched_indices = set()
    for idx, raw_tok, base, has_poss in cleaned_tokens:
        b_low = base.lower()
        if b_low in STORE_LOWER_MAP:
            store_canon = STORE_LOWER_MAP[b_low]
            resolved_stores.append((store_canon, 1.0))
            matched_indices.add(idx)
        elif b_low in STORE_ALIASES:
            store_canon = STORE_ALIASES[b_low]
            resolved_stores.append((store_canon, 1.0))
            matched_indices.add(idx)

    # Second pass: evaluate candidate words for fuzzy matching or unresolved named store
    for idx, raw_tok, base, has_poss in cleaned_tokens:
        if idx in matched_indices:
            continue
        if not base or not base.isalpha():
            continue
        b_low = base.lower()
        prev_low = cleaned_tokens[idx - 1][2].lower() if idx > 0 else ""

        # Check brand/persona nouns (DMart, Avenue, Supermarts, Kavita, Rao)
        if b_low in BRIEF_PROPER_NOUNS:
            if b_low in BRAND_PERSONA_NOUNS:
                # If no store resolved yet, wait until after fuzzy matching to check if any store resolved
                pass
            continue

        # Candidate word rules:
        # - at least 5 letters
        # - capitalised in the question or carries possessive 's
        # - not the first word of the question (unless it carries 's)
        # - neither a keyword nor a stop word
        if len(base) < 5:
            continue
        is_cap = base[0].isupper()
        if not (is_cap or has_poss):
            continue
        if idx == 0 and not has_poss:
            continue
        if b_low in ALL_KEYWORDS:
            continue

        # Compute best fuzzy score against the 5 store names
        best_store = None
        best_score = 0.0
        for s in STORES:
            score = SequenceMatcher(None, b_low, s.lower()).ratio()
            if score > best_score:
                best_score = score
                best_store = s

        if best_score >= 0.7:
            resolved_stores.append((best_store, round(best_score, 4)))
            matched_indices.add(idx)
        else:
            # Candidate word with best score < 0.7: check Case (a) and Case (b)
            # Case (a): Whatever else resolved, carries 's or directly follows and, or, vs, versus, than, for
            if has_poss or prev_low in {"and", "or", "vs", "versus", "than", "for"}:
                unresolved_store = True

    # Deduplicate resolved stores preserving order (keep minimum confidence if repeated)
    unique_stores = []
    seen_s = {}
    for s_name, conf in resolved_stores:
        if s_name not in seen_s:
            seen_s[s_name] = conf
            unique_stores.append(s_name)
        else:
            seen_s[s_name] = min(seen_s[s_name], conf)

    # Now check Case (b) and the brand/persona noun rule when NO store resolved anywhere in the question
    if len(unique_stores) == 0:
        for idx, raw_tok, base, has_poss in cleaned_tokens:
            if idx in matched_indices or not base or not base.isalpha():
                continue
            b_low = base.lower()
            prev_low = cleaned_tokens[idx - 1][2].lower() if idx > 0 else ""

            # Brand/persona noun rule: carries 's or directly follows for, about, in, at
            if b_low in BRAND_PERSONA_NOUNS:
                if has_poss or prev_low in {"for", "about", "in", "at"}:
                    unresolved_store = True
                continue

            if b_low in BRIEF_PROPER_NOUNS or len(base) < 5:
                continue
            is_cap = base[0].isupper()
            if not (is_cap or has_poss):
                continue
            if idx == 0 and not has_poss:
                continue
            if b_low in ALL_KEYWORDS:
                continue

            # Case (b): when no store resolved anywhere in the question,
            # directly follows about, in, or at, OR question contains metric, weather word, or date
            if prev_low in {"about", "in", "at"} or has_metric_or_weather_or_date:
                unresolved_store = True

    store_confs = [seen_s[s] for s in unique_stores]
    return unique_stores, store_confs, unresolved_store


def understand(question, context=None):
    """Parse question and session context into intent, entities, confidence, and missing_entities."""
    if context is None:
        context = {}

    # Normalise underscores to spaces for keyword matching while keeping original case
    q_norm = question.replace("_", " ").strip()
    raw_words = re.findall(r"[A-Za-z0-9']+", q_norm)
    lower_words = [w.lower().rstrip("'s") for w in raw_words]

    # Detect weather keyword
    weather_requested = any(w in WEATHER_WORDS for w in lower_words)

    # Detect products
    products = _detect_products(q_norm)
    product = products[0] if products else None

    # Detect metrics
    metrics = _extract_metrics(q_norm, lower_words)

    # Detect dates
    resolved_date, is_range, unresolved_date = _extract_dates(q_norm)
    has_any_date = (resolved_date is not None) or unresolved_date

    # Detect stores
    has_m_w_d = bool(metrics) or weather_requested or has_any_date
    stores, store_confs, unresolved_store = _extract_stores(q_norm, has_m_w_d)
    has_any_store = bool(stores) or unresolved_store

    # Decide Intent in strict 11-rule order:
    # (1) Prohibited action or rule override -> out_of_scope
    if _is_prohibited_or_override(q_norm, lower_words):
        intent = "out_of_scope"
    # (2) Column outside approved 11 fields -> unsupported_metric
    elif _is_unsupported_metric(q_norm, lower_words):
        intent = "unsupported_metric"
    # (3) Why / trend / reason -> diagnostic
    elif any(w in DIAGNOSTIC_WORDS for w in lower_words):
        intent = "diagnostic"
    # (4) Product name or 'reorder' or 'inventory' -> inventory
    elif product is not None or any(w in {"reorder", "reorders", "inventory", "inventories"} for w in lower_words):
        intent = "inventory"
    # (5) Feedback, reviews, ratings, or customers saying/say/says -> feedback
    elif any(w in FEEDBACK_WORDS for w in lower_words) or (
        any(w in {"customer", "customers"} for w in lower_words)
        and any(w in {"say", "says", "saying"} for w in lower_words)
    ):
        intent = "feedback"
    # (6) target + partner word, or achievement, or performance band -> target_vs_actual
    elif (
        (
            any(w in {"target", "targets", "daily_target_inr"} for w in lower_words)
            and (
                any(w in TARGET_PARTNERS for w in lower_words)
                or re.search(r"\bfall\s+short\b|\bfell\s+short\b", q_norm, flags=re.IGNORECASE)
            )
        )
        or any(w in {"achievement", "achievements"} for w in lower_words)
        or re.search(r"\bperformance\s+band\b", q_norm, flags=re.IGNORECASE)
    ):
        intent = "target_vs_actual"
        # In target_vs_actual, the metric is fixed (revenue against target); remove target/revenue from metrics list
        metrics = []
    # (7) which/highest/lowest/best/worst that names no store -> comparison
    elif any(w in COMPARISON_WORDS for w in lower_words) and not has_any_store:
        intent = "comparison"
    # (8) A metric (with or without store and date) -> lookup
    elif bool(metrics):
        intent = "lookup"
    # (9) A weather word with no metric -> weather
    elif weather_requested:
        intent = "weather"
    # (10) Names a store and/or a date (resolved or unresolved), no metric and no weather word
    elif has_any_store or has_any_date:
        if context.get("last_intent") == "target_vs_actual":
            intent = "target_vs_actual"
        else:
            intent = "lookup"
    # (11) Nothing recognisable -> out_of_scope
    else:
        intent = "out_of_scope"

    # Entities used per intent & dropping unused entities BEFORE validation
    if intent in {"unsupported_metric", "out_of_scope", "diagnostic"}:
        return {
            "intent": intent,
            "store": None,
            "metric": None,
            "date": None,
            "is_range": False,
            "product": None,
            "weather": False,
            "confidence": 1.0,
            "missing_entities": [],
            "ambiguous": False,
            "unresolved_store": False,
            "unresolved_date": False,
            "direction": None,
        }

    # Drop unused entities based on intent table
    if intent == "feedback":
        # Feedback uses store only; drop dates, metrics, products, weather
        resolved_date = None
        is_range = False
        unresolved_date = False
        metrics = []
        product = None
        weather_requested = False
    elif intent == "inventory":
        # Inventory uses product (required) and store (optional); drop dates, metrics, weather
        resolved_date = None
        is_range = False
        unresolved_date = False
        metrics = []
        weather_requested = False
    elif intent == "comparison":
        # Comparison uses metric and date/range only; no store is ever required or taken from context, weather ignored
        weather_requested = False
    elif intent == "target_vs_actual":
        # Target vs actual uses store and one date; metric is fixed
        metrics = []
    elif intent == "weather":
        # Weather uses store and one date; no metric
        metrics = []
    elif intent == "lookup":
        # If lookup is a date range, weather word is ignored
        pass

    # Check ambiguity on used entities: two different stores or two different metrics
    ambiguous = False
    ambiguous_type = None
    if intent in {"lookup", "target_vs_actual", "inventory", "feedback", "weather"} and len(stores) > 1:
        ambiguous = True
        ambiguous_type = "store"
    if intent in {"lookup", "comparison"} and len(metrics) > 1:
        ambiguous = True
        ambiguous_type = "metric" if ambiguous_type is None else "both"

    store_val = stores[0] if len(stores) == 1 else None
    store_conf = store_confs[0] if len(stores) == 1 else (0.4 if (unresolved_store or len(stores) > 1) else None)

    metric_val = metrics[0] if len(metrics) == 1 else None
    metric_conf = 1.0 if len(metrics) == 1 else (0.4 if len(metrics) > 1 else None)

    date_val = resolved_date
    date_conf = 1.0 if (resolved_date is not None and not unresolved_date) else (0.4 if unresolved_date else None)

    product_val = product
    product_conf = 1.0 if product is not None else None

    # Apply session context for required entities that were left out
    # Never replace an unresolved named store/date or an ambiguous pair from context
    if intent in {"lookup", "target_vs_actual", "feedback", "weather"}:
        if store_val is None and not unresolved_store and len(stores) == 0:
            if context.get("store"):
                store_val = context["store"]
                store_conf = 1.0

    if intent in {"lookup", "comparison"}:
        if metric_val is None and len(metrics) == 0:
            if context.get("metric"):
                metric_val = context["metric"]
                metric_conf = 1.0

    if intent in {"lookup", "target_vs_actual", "comparison", "weather"}:
        if date_val is None and not unresolved_date:
            if context.get("date") is not None:
                ctx_date = context["date"]
                ctx_is_range = isinstance(ctx_date, tuple)
                # A range held in context is an unresolved named date for single-date intents
                if intent in {"target_vs_actual", "weather"} and ctx_is_range:
                    unresolved_date = True
                    date_conf = 0.4
                else:
                    date_val = ctx_date
                    is_range = ctx_is_range
                    date_conf = 1.0

    if intent == "inventory":
        if product_val is None and context.get("product"):
            product_val = context["product"]
            product_conf = 1.0

    # Single-date intents (target_vs_actual, weather) given a range in the question -> unresolved named date
    if intent in {"target_vs_actual", "weather"} and is_range:
        unresolved_date = True
        date_val = None
        is_range = False
        date_conf = 0.4

    # For lookup over a date range, ignore weather word
    if intent == "lookup" and is_range:
        weather_requested = False

    # Determine missing / unresolved required entities
    missing_entities = []
    entity_confidences = []

    if intent == "lookup":
        if store_val is None or unresolved_store or (ambiguous and ambiguous_type in {"store", "both"}):
            missing_entities.append("store")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(store_conf)

        if metric_val is None or (ambiguous and ambiguous_type in {"metric", "both"}):
            missing_entities.append("metric")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(metric_conf)

        if date_val is None or unresolved_date:
            missing_entities.append("date")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(date_conf)

    elif intent in {"target_vs_actual", "weather"}:
        if store_val is None or unresolved_store or (ambiguous and ambiguous_type in {"store", "both"}):
            missing_entities.append("store")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(store_conf)

        if date_val is None or unresolved_date:
            missing_entities.append("date")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(date_conf)

    elif intent == "comparison":
        if metric_val is None or (ambiguous and ambiguous_type in {"metric", "both"}):
            missing_entities.append("metric")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(metric_conf)

        if date_val is None or unresolved_date:
            missing_entities.append("date")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(date_conf)

    elif intent == "inventory":
        if product_val is None:
            missing_entities.append("product")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(product_conf)

        # Optional store if named in the question
        if unresolved_store or len(stores) > 1:
            missing_entities.append("store")
            entity_confidences.append(0.4)
        elif store_val is not None:
            entity_confidences.append(store_conf)

    elif intent == "feedback":
        if store_val is None or unresolved_store or len(stores) > 1:
            missing_entities.append("store")
            entity_confidences.append(0.4)
        else:
            entity_confidences.append(store_conf)

    confidence = min(entity_confidences) if entity_confidences else 1.0
    if ambiguous or unresolved_store or unresolved_date or missing_entities:
        confidence = min(confidence, 0.4)

    # Update session context with resolved used entities
    if intent == "target_vs_actual":
        if store_val is not None and not unresolved_store and len(stores) <= 1 and store_conf >= 0.7:
            context["store"] = store_val
        if date_val is not None and not unresolved_date:
            context["date"] = date_val
        context["last_intent"] = "target_vs_actual"
    else:
        context["last_intent"] = intent
        if intent in {"lookup", "feedback", "weather"}:
            if store_val is not None and not unresolved_store and len(stores) <= 1 and store_conf >= 0.7:
                context["store"] = store_val
        if intent in {"lookup", "comparison"}:
            if metric_val is not None and len(metrics) <= 1:
                context["metric"] = metric_val
        if intent in {"lookup", "comparison", "weather"}:
            if date_val is not None and not unresolved_date:
                context["date"] = date_val
        if intent == "inventory":
            if product_val is not None:
                context["product"] = product_val

    # Determine comparison direction
    direction = "highest"
    if intent == "comparison":
        if "lowest" in lower_words:
            direction = "lowest"
        elif "highest" in lower_words:
            direction = "highest"
        elif "best" in lower_words:
            direction = "lowest" if metric_val == "stockout_hours" else "highest"
        elif "worst" in lower_words:
            direction = "highest" if metric_val == "stockout_hours" else "lowest"

    return {
        "intent": intent,
        "store": store_val if (store_conf is not None and store_conf >= 0.7) else None,
        "metric": metric_val,
        "date": date_val,
        "is_range": is_range,
        "product": product_val,
        "weather": weather_requested,
        "confidence": round(confidence, 2),
        "missing_entities": missing_entities,
        "ambiguous": ambiguous,
        "ambiguous_type": ambiguous_type,
        "unresolved_store": unresolved_store or (store_conf is not None and store_conf < 0.7),
        "unresolved_date": unresolved_date,
        "direction": direction,
    }