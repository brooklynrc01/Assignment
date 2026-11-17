"""Write local JSON outputs and optionally upload them to Google Cloud Storage."""

from __future__ import annotations

import json
from pathlib import Path

from weather_agent.config import WeatherConfig, load_config


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _upload_json_files(config: WeatherConfig, files: dict[str, Path], run_date: str) -> dict:
    if not config.upload_to_gcs:
        return {"status": "disabled", "reason": "UPLOAD_TO_GCS is not enabled."}
    if not config.gcs_bucket:
        return {"status": "skipped", "reason": "GCS_BUCKET is empty."}

    try:
        import google.auth
        from google.auth.exceptions import DefaultCredentialsError, RefreshError
        from google.auth.transport.requests import Request
        from google.cloud import storage

        credentials, project_id = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        # Confirm ADC can obtain a current access token before making any GCS request.
        credentials.refresh(Request())
    except (DefaultCredentialsError, RefreshError):
        return {
            "status": "skipped",
            "reason": "Google Cloud credentials are unavailable or invalid; no GCS request was made.",
        }
    except ImportError:
        return {"status": "skipped", "reason": "Google Cloud libraries are missing."}
    except Exception:
        return {
            "status": "skipped",
            "reason": "Could not validate Application Default Credentials; no GCS request was made.",
        }

    prefix = config.gcs_prefix
    run_folder = f"run_date={run_date}"
    object_names = {}
    try:
        client = storage.Client(project=project_id, credentials=credentials)
        bucket = client.bucket(config.gcs_bucket)
        for label, path in files.items():
            filename = path.name
            object_name = "/".join(
                part for part in [prefix, run_folder, filename] if part
            )
            bucket.blob(object_name).upload_from_filename(
                str(path), content_type="application/json"
            )
            object_names[label] = f"gs://{config.gcs_bucket}/{object_name}"
    except Exception as exc:  # Keep the local pipeline result available on cloud errors.
        return {
            "status": "failed",
            "reason": f"GCS upload did not complete ({type(exc).__name__}); local files are available.",
            "uploaded_objects": object_names,
        }

    return {"status": "uploaded", "uploaded_objects": object_names}


def save_weather_data(payload: dict) -> dict:
    """Persist raw and transformed JSON, then upload only when explicitly enabled."""
    config = load_config()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = config.output_dir / "raw_weather.json"
    processed_path = config.output_dir / "processed_weather.json"
    html_path = config.output_dir / "weather_summary.html"
    manifest_path = config.output_dir / "run_manifest.json"

    _write_json(raw_path, payload["raw"])
    _write_json(processed_path, payload["processed"])

    run_date = payload["raw"]["retrieved_at_utc"][:10]
    gcs_result = _upload_json_files(
        config,
        {"raw": raw_path, "processed": processed_path},
        run_date,
    )
    manifest = {
        "run_date_utc": run_date,
        "local_files": {
            "raw": str(raw_path),
            "processed": str(processed_path),
            "html": str(html_path),
        },
        "gcs": {
            "bucket": config.gcs_bucket or None,
            "prefix": config.gcs_prefix or None,
            **gcs_result,
        },
    }
    _write_json(manifest_path, manifest)

    return {
        "raw": payload["raw"],
        "processed": payload["processed"],
        "manifest": manifest,
        "html_path": str(html_path),
    }

