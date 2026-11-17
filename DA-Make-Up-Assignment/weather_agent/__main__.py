"""Run the ADK weather workflow from the project root."""

from __future__ import annotations

import asyncio
import json
import sys

from weather_agent.config import load_config


async def _run() -> int:
    from google.adk.runners import InMemoryRunner
    from weather_agent.agent import app

    runner = InMemoryRunner(app=app)
    try:
        await runner.run_debug("Run the configured seven-day weather batch pipeline.")
    except Exception as exc:
        print(f"Pipeline failed: {exc}", file=sys.stderr)
        return 1

    config = load_config()
    expected_files = [
        config.output_dir / "raw_weather.json",
        config.output_dir / "processed_weather.json",
        config.output_dir / "weather_summary.html",
        config.output_dir / "run_manifest.json",
    ]
    missing = [path for path in expected_files if not path.is_file()]
    if missing:
        print("The agent finished without creating every expected file:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 1

    processed = json.loads(expected_files[1].read_text(encoding="utf-8"))
    manifest = json.loads(expected_files[3].read_text(encoding="utf-8"))
    warmest = processed["summary"]["warmest_day"]
    print("Weather pipeline completed.")
    print(f"Location: {processed['location']['name']}")
    print(f"Warmest day: {warmest['date']} ({warmest['maximum_temperature_c']:.1f} C)")
    print("Files:")
    for path in expected_files:
        print(f"  - {path}")
    gcs = manifest["gcs"]
    print(f"GCS status: {gcs['status']} - {gcs.get('reason', 'see uploaded object paths in run_manifest.json')}")
    for object_path in gcs.get("uploaded_objects", {}).values():
        print(f"  - {object_path}")
    return 0


def main() -> None:
    load_config()  # Load .env before ADK builds the workflow app.
    raise SystemExit(asyncio.run(_run()))


if __name__ == "__main__":
    main()

