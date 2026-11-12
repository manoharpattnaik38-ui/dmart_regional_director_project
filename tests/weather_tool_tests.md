# Weather Tool Unit Tests (`tools/weather.py`)

All tests below were executed with `WEATHER_MODE=stub` (the default offline mode) by invoking `get_weather(city, date)` from `tools/weather.py`.

---

## Test Case 1: Check Value 1 — Mumbai on 2026-05-15
* **Call**: `get_weather("Mumbai", "2026-05-15")`
* **Formula Derivation**: `doy = 135`, `n = len("Mumbai") = 6` -> `temperature_c = 20 + (6 + 135) % 15 = 26`, `humidity_pct = 40 + (18 + 135) % 50 = 43`, `wind_kmh = 5 + 135 % 10 = 10`, `rain_mm = 0.0` (`135 % 4 != 0`).
* **Pasted Output**:

    {"ok": true, "city": "Mumbai", "date": "2026-05-15", "mode": "stub", "temperature_c": 26, "humidity_pct": 43, "wind_kmh": 10, "rain_mm": 0.0, "summary": "Stub weather for Mumbai on 2026-05-15: 26 C, humidity 43%, wind 10 km/h, rain 0.0 mm."}

---

## Test Case 2: Check Value 2 — Pune on 2026-05-16
* **Call**: `get_weather("Pune", "2026-05-16")`
* **Formula Derivation**: `doy = 136`, `n = len("Pune") = 4` -> `temperature_c = 20 + (4 + 136) % 15 = 25`, `humidity_pct = 40 + (12 + 136) % 50 = 88`, `wind_kmh = 5 + 136 % 10 = 11`, `rain_mm = round(1.5 + (136 % 7), 1) = 6.5` (`136 % 4 == 0`).
* **Pasted Output**:

    {"ok": true, "city": "Pune", "date": "2026-05-16", "mode": "stub", "temperature_c": 25, "humidity_pct": 88, "wind_kmh": 11, "rain_mm": 6.5, "summary": "Stub weather for Pune on 2026-05-16: 25 C, humidity 88%, wind 11 km/h, rain 6.5 mm."}

---

## Test Case 3: Validation Guard — Unsupported City & Malformed Date
* **Calls**: `get_weather("Kolkata", "2026-05-15")` and `get_weather("Mumbai", "15-05-2026")`
* **Pasted Outputs**:

    {"ok": false, "error": "Unsupported city 'Kolkata'. Allowed cities: Ahmedabad, Bengaluru, Hyderabad, Mumbai, Pune."}
    {"ok": false, "error": "Invalid date format '15-05-2026'. Expected YYYY-MM-DD."}
