# Seven-Day Weather Batch Pipeline with Google ADK

This beginner project fetches a seven-day Open-Meteo forecast, calculates daily and period-level statistics, saves raw and processed JSON, and creates a self-contained HTML report. Google ADK's deterministic graph workflow runs four separate function nodes in order: ingestion, transformation, storage, and visualization. The workflow does not call a language model, so a Gemini key is not needed.

## Architecture and execution flow

```text
python -m weather_agent
        |
        v
ADK Workflow graph
  1. ingestion_tool       -> Open-Meteo daily forecast
  2. transformation_tool  -> seven daily rows + period summary
  3. storage_tool         -> local JSON, optional GCS upload
  4. visualization_tool   -> standalone HTML with inline SVG and table
```

The graph passes each stage's output to the next. Each stage implementation lives in its own file under `weather_agent/tools/`, which makes it easy to explain and replace one step at a time.

## Project structure

```text
.
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── output/
│   └── pdf/
│       └── future_improvements.pdf
└── weather_agent/
    ├── __main__.py
    ├── agent.py
    ├── config.py
    └── tools/
        ├── ingestion.py
        ├── storage.py
        ├── transformation.py
        └── visualization.py
```

## Prerequisites

- Python 3.10 or later
- `pip`
- Internet access to `api.open-meteo.com`
- Optional for uploads: a Google Cloud project, a Cloud Storage bucket, and Google Cloud Application Default Credentials (ADC)

Open-Meteo's public forecast endpoint does not require an API key. The ADK graph is deterministic and has no Gemini API key requirement.

## Install and configure

From the project folder, create and activate a virtual environment.

**Windows PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**macOS or Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then edit the location name and coordinates. For example, the sample values use Indianapolis. Relative `OUTPUT_DIR` values are resolved from the project folder. The Open-Meteo API accepts latitude, longitude, daily variables, forecast length, and timezone; this project requests seven days in the configured timezone.

## Google Cloud authentication and bucket setup

Cloud upload is off by default. The pipeline always writes its local files first. It attempts an upload only when `UPLOAD_TO_GCS=true`, `GCS_BUCKET` is non-empty, and ADC can obtain an access token.

1. Create or select a Google Cloud project and enable the Cloud Storage API.
2. Create a bucket in the Google Cloud Console or with `gcloud storage buckets create gs://YOUR_BUCKET --location=US --uniform-bucket-level-access`.
3. For local development, install the Google Cloud CLI and run `gcloud auth application-default login`. ADC keeps credentials outside this repository. Avoid downloading service-account keys for local development.
4. Grant the identity used by ADC the **Storage Object User** role (`roles/storage.objectUser`) on the bucket. It permits object creation and updates needed when a daily object is replaced.
5. In `.env`, set:

```dotenv
UPLOAD_TO_GCS=true
GCS_BUCKET=your-bucket-name
GCS_PREFIX=weather
```

The project never makes objects public. Keep `.env` and credential files out of Git.

## Run the agent

```bash
python -m weather_agent
```

The command runs the ADK workflow once and prints the location, warmest day, local output paths, and GCS status. For an ordinary local run, leave `UPLOAD_TO_GCS=false` and `GCS_BUCKET` blank. No cloud upload is attempted in that configuration.

## Expected outputs

By default, the pipeline writes these files under `artifacts/`:

- `raw_weather.json`: request metadata and the original Open-Meteo response
- `processed_weather.json`: seven daily averages, lows, highs and precipitation values, plus the period average, precipitation total, and warmest day
- `weather_summary.html`: a standalone page with an inline SVG chart and summary table; it works offline after it is generated
- `run_manifest.json`: local output paths and the cloud upload status

With upload enabled, the raw and processed JSON files are uploaded to `gs://BUCKET/PREFIX/run_date=YYYY-MM-DD/`. A rerun on the same UTC date replaces those object names.

## Verify GCS objects

After a run reports `GCS status: uploaded`, use the paths printed by the command or run:

```bash
gcloud storage ls --recursive gs://YOUR_BUCKET/weather/run_date=YYYY-MM-DD/
gcloud storage cat gs://YOUR_BUCKET/weather/run_date=YYYY-MM-DD/processed_weather.json
```

Use the UTC run date recorded in `artifacts/run_manifest.json`. If you rerun a date, replacing an existing object requires `storage.objects.create` and `storage.objects.delete`; the bucket-level Storage Object User role includes the needed permissions.

## Create a public Git repository and push

The project does not publish itself. To publish it:

1. Create a new **public** repository in GitHub. Leave it empty so its generated README does not conflict with this project.
2. Review `git status --short` and confirm `.env`, `.venv/`, and `artifacts/` are not staged. `.gitignore` excludes those paths and common credential files.
3. Commit the project, add the repository as `origin`, and push your branch. For example:

```bash
git add .
git commit -m "Add ADK weather batch pipeline"
git remote add origin https://github.com/YOUR-USER/YOUR-REPOSITORY.git
git branch -M main
git push -u origin main
```

If `origin` already exists, use `git remote set-url origin ...` instead of adding it again. After pushing, open the repository page and verify that the README and source files are present and that `.env`, credential files, and local output JSON are absent.

## Troubleshooting

- **Open-Meteo request fails:** check internet access, latitude/longitude ranges, and the Open-Meteo status page. The client uses a 30-second timeout and reports HTTP or network failures.
- **No `.env` values seem to apply:** make sure the file is named `.env` in the project root and that each variable uses `NAME=value` syntax.
- **ADK or imports are missing:** activate `.venv` and reinstall with `pip install -r requirements.txt`.
- **GCS reports skipped:** confirm both `UPLOAD_TO_GCS=true` and `GCS_BUCKET` are set. If credentials are not configured, run `gcloud auth application-default login`.
- **GCS upload fails:** check the bucket name, Cloud Storage API, active ADC identity, and its bucket-level IAM permissions. Local output files are kept when an upload fails.
- **A rerun cannot replace today's objects:** grant the identity permissions to create and delete objects, or choose a new `GCS_PREFIX`.
- **The report is not current:** rerun the pipeline; Open-Meteo serves a forecast that may change as its weather models update.

## Official references

- [ADK Python quickstart](https://adk.dev/get-started/python/)
- [ADK graph workflows](https://adk.dev/graphs/routes/)
- [ADK workflow data handling](https://adk.dev/graphs/data-handling/)
- [Open-Meteo Forecast API](https://open-meteo.com/en/docs)
- [Google Cloud Storage Python client](https://cloud.google.com/python/docs/reference/storage/latest)
- [Upload objects to Cloud Storage](https://docs.cloud.google.com/storage/docs/uploading-objects)
- [Application Default Credentials](https://docs.cloud.google.com/docs/authentication/application-default-credentials)

