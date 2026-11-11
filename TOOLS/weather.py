"""Weather tool supporting deterministic stub mode (default) and Open-Meteo live archive mode."""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date as dt_date

CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Hyderabad": (17.3850, 78.4867),
    "Bengaluru": (12.9716, 77.5946),
    "Ahmedabad": (23.0225, 72.5714),
}

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _parse_iso_date(date_str):
    if not isinstance(date_str, str) or not ISO_DATE_RE.match(date_str):
        return None
    try:
        y, m, d = map(int, date_str.split("-"))
        return dt_date(y, m, d)
    except ValueError:
        return None


def get_weather(city, date):
    """Return daily weather dictionary for one of the five store cities and an ISO date."""
    if not isinstance(city, str) or city not in CITY_COORDS:
        return {"ok": False, "error": f"unsupported city: {city}"}

    parsed_date = _parse_iso_date(date)
    if parsed_date is None:
        return {"ok": False, "error": f"invalid ISO date: {date}"}

    mode = os.environ.get("WEATHER_MODE", "stub").strip().lower()
    if mode != "live":
        mode = "stub"

    if mode == "stub":
        doy = parsed_date.timetuple().tm_yday
        n = len(city)
        temperature_c = 20 + (n + doy) % 15
        humidity_pct = 40 + (3 * n + doy) % 50
        wind_kmh = 5 + doy % 10
        rain_mm = 6.5 if doy % 4 == 0 else 0.0
        return {
            "ok": True,
            "city": city,
            "date": date,
            "mode": "stub",
            "temperature_c": temperature_c,
            "humidity_pct": humidity_pct,
            "wind_kmh": wind_kmh,
            "rain_mm": rain_mm,
        }

    # Live mode: Open-Meteo archive API
    lat, lon = CITY_COORDS[city]
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": date,
        "end_date": date,
        "timezone": "Asia/Kolkata",
        "daily": "temperature_2m_mean,relative_humidity_2m_mean,wind_speed_10m_max,precipitation_sum",
    }
    url = f"https://archive-api.open-meteo.com/v1/archive?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.getcode()
            if status_code != 200:
                return {"ok": False, "error": f"HTTP status {status_code}"}
            payload = json.loads(resp.read().decode("utf-8"))
        daily = payload.get("daily", {})
        temp_list = daily.get("temperature_2m_mean") or []
        hum_list = daily.get("relative_humidity_2m_mean") or []
        wind_list = daily.get("wind_speed_10m_max") or []
        rain_list = daily.get("precipitation_sum") or []
        if not (temp_list and hum_list and wind_list and rain_list):
            return {"ok": False, "error": "missing daily weather fields in API response"}
        return {
            "ok": True,
            "city": city,
            "date": date,
            "mode": "live",
            "temperature_c": float(temp_list[0]),
            "humidity_pct": float(hum_list[0]),
            "wind_kmh": float(wind_list[0]),
            "rain_mm": float(rain_list[0]),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}