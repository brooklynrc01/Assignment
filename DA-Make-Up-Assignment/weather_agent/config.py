"""Environment-backed settings for the weather pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class WeatherConfig:
    location_name: str
    latitude: float
    longitude: float
    timezone: str
    output_dir: Path
    upload_to_gcs: bool
    gcs_bucket: str
    gcs_prefix: str


def load_config() -> WeatherConfig:
    """Read settings from the project .env file and environment variables."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    try:
        latitude = float(os.getenv("LATITUDE", "39.7684"))
        longitude = float(os.getenv("LONGITUDE", "-86.1584"))
    except ValueError as exc:
        raise ValueError("LATITUDE and LONGITUDE must be numbers.") from exc

    if not -90 <= latitude <= 90:
        raise ValueError("LATITUDE must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError("LONGITUDE must be between -180 and 180.")

    output_dir = Path(os.getenv("OUTPUT_DIR", "artifacts")).expanduser()
    if not output_dir.is_absolute():
        output_dir = PROJECT_ROOT / output_dir

    upload_setting = os.getenv("UPLOAD_TO_GCS", "false").strip().lower()
    prefix = os.getenv("GCS_PREFIX", "weather").strip().strip("/")

    return WeatherConfig(
        location_name=os.getenv("LOCATION_NAME", "Indianapolis, IN").strip(),
        latitude=latitude,
        longitude=longitude,
        timezone=os.getenv("TIMEZONE", "auto").strip() or "auto",
        output_dir=output_dir,
        upload_to_gcs=upload_setting in {"1", "true", "yes", "on"},
        gcs_bucket=os.getenv("GCS_BUCKET", "").strip(),
        gcs_prefix=prefix,
    )

