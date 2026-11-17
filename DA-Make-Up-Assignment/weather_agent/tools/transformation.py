"""Turn raw daily forecast arrays into a checked seven-day summary."""

from __future__ import annotations

from datetime import date
from statistics import mean


def _number(value: object) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 1)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected a number or null in Open-Meteo data; got {value!r}.") from exc


def transform_weather(raw_envelope: dict) -> dict:
    """Calculate per-day values, period statistics, and basic quality checks."""
    response = raw_envelope.get("response", {})
    daily = response.get("daily")
    if not isinstance(daily, dict):
        raise ValueError("Open-Meteo response is missing the 'daily' section.")

    fields = {
        "date": daily.get("time"),
        "mean": daily.get("temperature_2m_mean"),
        "minimum": daily.get("temperature_2m_min"),
        "maximum": daily.get("temperature_2m_max"),
        "precipitation": daily.get("precipitation_sum"),
        "weather_code": daily.get("weather_code"),
    }
    if not isinstance(fields["date"], list) or not fields["date"]:
        raise ValueError("Open-Meteo returned no forecast dates.")

    dates = fields["date"]
    for name, values in fields.items():
        if name != "date" and (not isinstance(values, list) or len(values) != len(dates)):
            raise ValueError(f"Open-Meteo daily field '{name}' does not match the date count.")

    if len(dates) != 7:
        raise ValueError(f"Expected 7 forecast days, but Open-Meteo returned {len(dates)}.")

    days = []
    missing_value_count = 0
    for index, day in enumerate(dates):
        # Fail early on a malformed date rather than writing an ambiguous report.
        date.fromisoformat(day)
        day_mean = _number(fields["mean"][index])
        day_minimum = _number(fields["minimum"][index])
        day_maximum = _number(fields["maximum"][index])
        precipitation = _number(fields["precipitation"][index])
        code = fields["weather_code"][index]
        if code is not None:
            code = int(code)

        missing_value_count += sum(
            value is None for value in [day_mean, day_minimum, day_maximum, precipitation]
        )
        days.append(
            {
                "date": day,
                "mean_temperature_c": day_mean,
                "minimum_temperature_c": day_minimum,
                "maximum_temperature_c": day_maximum,
                "precipitation_mm": precipitation,
                "weather_code": code,
            }
        )

    means = [day["mean_temperature_c"] for day in days if day["mean_temperature_c"] is not None]
    minimums = [
        day["minimum_temperature_c"]
        for day in days
        if day["minimum_temperature_c"] is not None
    ]
    maximums = [
        day["maximum_temperature_c"]
        for day in days
        if day["maximum_temperature_c"] is not None
    ]
    precipitation_values = [
        day["precipitation_mm"] for day in days if day["precipitation_mm"] is not None
    ]
    if not means or not minimums or not maximums:
        raise ValueError("The forecast does not contain enough temperature values to summarize.")

    warmest_day = max(
        (day for day in days if day["maximum_temperature_c"] is not None),
        key=lambda day: day["maximum_temperature_c"],
    )
    warnings = []
    if missing_value_count:
        warnings.append(f"{missing_value_count} daily measurement(s) were missing and excluded.")

    return {
        "source": raw_envelope.get("source"),
        "retrieved_at_utc": raw_envelope.get("retrieved_at_utc"),
        "location": {
            "name": raw_envelope.get("location_name", "Configured location"),
            "latitude": response.get("latitude"),
            "longitude": response.get("longitude"),
            "timezone": response.get("timezone", "unknown"),
        },
        "period": {"start_date": dates[0], "end_date": dates[-1], "days": len(days)},
        "units": {
            "temperature": "C",
            "precipitation": "mm",
            **response.get("daily_units", {}),
        },
        "summary": {
            "average_daily_mean_temperature_c": round(mean(means), 1),
            "lowest_daily_minimum_c": round(min(minimums), 1),
            "highest_daily_maximum_c": round(max(maximums), 1),
            "total_precipitation_mm": round(sum(precipitation_values), 1),
            "warmest_day": {
                "date": warmest_day["date"],
                "maximum_temperature_c": warmest_day["maximum_temperature_c"],
            },
        },
        "data_quality": {
            "expected_days": 7,
            "days_returned": len(days),
            "missing_measurements": missing_value_count,
            "warnings": warnings,
        },
        "days": days,
    }

