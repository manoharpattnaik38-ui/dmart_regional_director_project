# Weather Tool Unit Tests (`tools/weather.py`)

All tests below were executed with `WEATHER_MODE=stub` (the default offline mode) by invoking `get_weather(city, date)` from `tools/weather.py`.

## Test Case 1: Check Value 1 — Mumbai on 2026-05-15
* **Call**: `get_weather("Mumbai", "2026-05-15")`
* **Formula Derivation**: `doy = 135`, `n = len("Mumbai") = 6` -> `temperature_c = 20 + (6 + 135) % 15 = 26`, `humidity_pct = 40 + (18 + 135) % 50 = 43`, `wind_kmh = 5 + 135 % 10 = 10`, `rain_mm = 0.0` (`135 % 4 != 0`).
* **Pasted Output**:
```json
{"ok": true, "city": "Mumbai", "date": "2026-05-15", "mode": "stub", "temperature_c": 26, "humidity_pct": 43, "wind_kmh": 10, "rain_mm": 0.0}