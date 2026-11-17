"""Fetch the seven-day daily forecast from Open-Meteo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from weather_agent.config import load_config


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
DAILY_FIELDS = ",".join(
    [
        "temperature_2m_mean",
        "temperature_2m_min",
        "temperature_2m_max",
        "precipitation_sum",
        "weather_code",
    ]
)


def fetch_weather() -> dict:
    """Fetch and preserve the raw API response plus request metadata."""
    config = load_config()
    query = {
        "latitude": config.latitude,
        "longitude": config.longitude,
        "daily": DAILY_FIELDS,
        "forecast_days": 7,
        "timezone": config.timezone,
        "temperature_unit": "celsius",
    }
    url = f"{OPEN_METEO_URL}?{urlencode(query)}"
    request = Request(url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Open-Meteo returned HTTP {exc.code}.") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Could not reach Open-Meteo: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Open-Meteo returned a response that was not valid JSON.") from exc

    if body.get("error"):
        raise RuntimeError(f"Open-Meteo error: {body.get('reason', 'request rejected')}")

    return {
        "source": "Open-Meteo Forecast API",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "request": {
            "latitude": config.latitude,
            "longitude": config.longitude,
            "daily_fields": DAILY_FIELDS.split(","),
            "forecast_days": 7,
            "timezone": config.timezone,
        },
        "location_name": config.location_name,
        "response": body,
    }

