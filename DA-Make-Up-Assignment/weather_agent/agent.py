"""ADK graph workflow that runs the weather pipeline's four focused tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from google.adk import Event, Workflow
from google.adk.apps import App

from weather_agent.tools.ingestion import fetch_weather
from weather_agent.tools.storage import save_weather_data
from weather_agent.tools.transformation import transform_weather
from weather_agent.tools.visualization import build_html


def ingestion_tool(node_input: Any = None) -> Event:
    """Fetch the configured seven-day forecast from Open-Meteo."""
    return Event(output=fetch_weather())


def transformation_tool(node_input: dict) -> Event:
    """Calculate daily temperature and precipitation summaries."""
    processed = transform_weather(node_input)
    return Event(output={"raw": node_input, "processed": processed})


def storage_tool(node_input: dict) -> Event:
    """Write raw and processed JSON locally and optionally to GCS."""
    return Event(output=save_weather_data(node_input))


def visualization_tool(node_input: dict) -> Event:
    """Create the standalone HTML chart and summary table."""
    storage_result = node_input
    processed = storage_result["processed"]
    html_path = build_html(processed, Path(storage_result["html_path"]))
    message = (
        f"Created the seven-day summary for {processed['location']['name']}. "
        f"Warmest day: {processed['summary']['warmest_day']['date']} "
        f"({processed['summary']['warmest_day']['maximum_temperature_c']:.1f} C). "
        f"HTML: {html_path}"
    )
    return Event(
        output={"html_path": str(html_path), "manifest": storage_result["manifest"]},
        message=message,
    )


root_agent = Workflow(
    name="weather_batch_pipeline",
    description="Fetches, transforms, stores, and visualizes seven days of weather data.",
    edges=[
        (
            "START",
            ingestion_tool,
            transformation_tool,
            storage_tool,
            visualization_tool,
        )
    ],
)

app = App(name="weather_batch_pipeline", root_agent=root_agent)

