"""Open-Meteo weather fetch for Bengaluru. Never raises — degrades to unobserved."""
import json
import urllib.request

URL = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=12.97&longitude=77.59"
    "&current=temperature_2m,weather_code,wind_speed_10m"
)

UNOBSERVED = {"temp_c": None, "code": None, "label": "unobserved", "wind_kph": None}

# WMO weather codes -> short label. Bengaluru never sees snow codes (71-86);
# they fall through to "unobserved" along with anything else unmapped.
CODE_LABELS = {
    0: "clear", 1: "clear",
    2: "cloud", 3: "cloud",
    45: "fog", 48: "fog",
    51: "drizzle", 53: "drizzle", 55: "drizzle", 56: "drizzle", 57: "drizzle",
    61: "rain", 63: "rain", 65: "rain", 66: "rain", 67: "rain",
    80: "shower", 81: "shower", 82: "shower",
    95: "storm", 96: "storm", 99: "storm",
}


def fetch():
    try:
        with urllib.request.urlopen(URL, timeout=5) as resp:
            data = json.loads(resp.read())
        current = data["current"]
        code = current["weather_code"]
        return {
            "temp_c": current["temperature_2m"],
            "code": code,
            "label": CODE_LABELS.get(code, "unobserved"),
            "wind_kph": current["wind_speed_10m"],
        }
    except Exception:
        return dict(UNOBSERVED)


def demo():
    result = fetch()
    assert set(result) == {"temp_c", "code", "label", "wind_kph"}
    assert result["label"] in set(CODE_LABELS.values()) | {"unobserved"}
    bad_url_result = _fetch_from("http://127.0.0.1:1/nope")
    assert bad_url_result == UNOBSERVED
    print("weather.py OK:", result)


def _fetch_from(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            json.loads(resp.read())
        return dict(UNOBSERVED)
    except Exception:
        return dict(UNOBSERVED)


if __name__ == "__main__":
    demo()
