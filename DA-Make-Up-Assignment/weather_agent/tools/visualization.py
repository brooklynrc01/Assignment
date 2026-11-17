"""Create a standalone HTML summary with an inline SVG chart and table."""

from __future__ import annotations

import html
from pathlib import Path


def _display(value: float | None, unit: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}{unit}"


def _chart(days: list[dict]) -> str:
    values = [day["maximum_temperature_c"] for day in days if day["maximum_temperature_c"] is not None]
    if not values:
        return "<p>There are no daily high temperatures to chart.</p>"

    low = min(values)
    high = max(values)
    if low == high:
        low -= 1
        high += 1
    left, width = 145, 570
    row_height, top = 42, 38
    height = top * 2 + row_height * len(days)
    parts = [
        f'<svg role="img" aria-labelledby="chart-title chart-desc" viewBox="0 0 760 {height}" xmlns="http://www.w3.org/2000/svg">',
        '<title id="chart-title">Daily high temperatures</title>',
        '<desc id="chart-desc">A horizontal bar chart comparing the forecast high temperature for each day.</desc>',
    ]
    for tick_index in range(5):
        tick = low + (high - low) * tick_index / 4
        x = left + width * tick_index / 4
        parts.append(f'<line x1="{x:.1f}" y1="22" x2="{x:.1f}" y2="{height - 28}" class="grid"/>')
        parts.append(f'<text x="{x:.1f}" y="{height - 8}" class="axis" text-anchor="middle">{tick:.0f} C</text>')

    for index, day in enumerate(days):
        y = top + index * row_height
        value = day["maximum_temperature_c"]
        day_label = html.escape(day["date"])
        parts.append(f'<text x="{left - 12}" y="{y + 5}" class="day" text-anchor="end">{day_label}</text>')
        if value is None:
            parts.append(f'<text x="{left}" y="{y + 5}" class="value">N/A</text>')
            continue
        bar_width = max(2, width * (value - low) / (high - low))
        parts.append(f'<rect x="{left}" y="{y - 12}" width="{bar_width:.1f}" height="22" rx="6" class="bar"/>')
        parts.append(f'<text x="{left + bar_width + 8:.1f}" y="{y + 5}" class="value">{value:.1f} C</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def build_html(processed: dict, output_path: Path) -> Path:
    """Write a self-contained HTML file from the processed weather summary."""
    location = html.escape(str(processed["location"]["name"]))
    period = processed["period"]
    summary = processed["summary"]
    warmest = summary["warmest_day"]
    days = processed["days"]

    table_rows = []
    for day in days:
        table_rows.append(
            "<tr>"
            f"<th scope=\"row\">{html.escape(day['date'])}</th>"
            f"<td>{_display(day['mean_temperature_c'], ' C')}</td>"
            f"<td>{_display(day['minimum_temperature_c'], ' C')}</td>"
            f"<td>{_display(day['maximum_temperature_c'], ' C')}</td>"
            f"<td>{_display(day['precipitation_mm'], ' mm')}</td>"
            "</tr>"
        )

    warnings = processed["data_quality"]["warnings"]
    warning_html = "".join(f"<li>{html.escape(message)}</li>" for message in warnings)
    if not warning_html:
        warning_html = "<li>No missing daily measurements were reported.</li>"

    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Seven-Day Weather Summary - {location}</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, Segoe UI, Arial, sans-serif; color: #18313b; background: #f3f7f8; }}
    body {{ margin: 0; padding: 36px 18px; }}
    main {{ max-width: 1000px; margin: auto; }}
    h1 {{ margin: 0 0 8px; font-size: clamp(1.8rem, 4vw, 2.6rem); }}
    .muted {{ color: #56717a; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 26px 0; }}
    .card, section {{ background: #fff; border: 1px solid #dce7ea; border-radius: 14px; padding: 18px; box-shadow: 0 5px 18px #18313b0c; }}
    .card span {{ display: block; color: #56717a; font-size: .9rem; }}
    .card strong {{ display: block; margin-top: 8px; font-size: 1.35rem; }}
    section {{ margin: 16px 0; }}
    h2 {{ margin: 0 0 16px; font-size: 1.25rem; }}
    svg {{ width: 100%; height: auto; display: block; overflow: visible; }}
    .grid {{ stroke: #e3ecee; stroke-width: 1; }}
    .axis, .day, .value {{ fill: #56717a; font-size: 12px; }}
    .bar {{ fill: #188b92; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ border-collapse: collapse; width: 100%; min-width: 620px; text-align: right; }}
    th, td {{ border-bottom: 1px solid #e7eef0; padding: 11px 8px; }}
    th:first-child, td:first-child {{ text-align: left; }}
    thead th {{ color: #56717a; font-size: .85rem; }}
    .note {{ font-size: .9rem; }}
    @media (max-width: 560px) {{ body {{ padding: 24px 12px; }} section {{ padding: 14px; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class="muted">Open-Meteo seven-day forecast</p>
      <h1>Weather in {location}</h1>
      <p class="muted">{html.escape(period['start_date'])} through {html.escape(period['end_date'])} · {period['days']} days · temperatures in Celsius</p>
    </header>
    <div class="cards" aria-label="Seven-day summary">
      <div class="card"><span>Average of daily means</span><strong>{_display(summary['average_daily_mean_temperature_c'], ' C')}</strong></div>
      <div class="card"><span>Warmest day (daily high)</span><strong>{html.escape(warmest['date'])}</strong><span>{_display(warmest['maximum_temperature_c'], ' C')}</span></div>
      <div class="card"><span>Highest daily high</span><strong>{_display(summary['highest_daily_maximum_c'], ' C')}</strong></div>
      <div class="card"><span>Total precipitation</span><strong>{_display(summary['total_precipitation_mm'], ' mm')}</strong></div>
    </div>
    <section>
      <h2>Daily high temperatures</h2>
      <p class="muted note">The bars compare each day's forecast maximum temperature.</p>
      {_chart(days)}
    </section>
    <section>
      <h2>Daily details</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th scope="col">Date</th><th scope="col">Mean</th><th scope="col">Low</th><th scope="col">High</th><th scope="col">Precipitation</th></tr></thead>
          <tbody>{''.join(table_rows)}</tbody>
        </table>
      </div>
    </section>
    <section>
      <h2>Data quality</h2>
      <ul>{warning_html}</ul>
      <p class="muted note">Forecast values can change as Open-Meteo updates its weather models. Generated at {html.escape(str(processed['retrieved_at_utc']))}.</p>
    </section>
  </main>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path

