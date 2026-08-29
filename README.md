# Bhubaneswar Extreme Heatwave Early Warning System

Backend for **SIH Problem Statement 83** — Extreme Heatwave Early Warning
and Human Thermal Stress Index.

This MVP computes a ward-level heat-health risk for all 67 Bhubaneswar
Municipal Corporation (BMC) wards using ERA5 reanalysis ground-truth
history, a real 5-day Open-Meteo forecast, and official BMC ward GIS data.
It publishes the resulting thermal stress indices and risk surfaces through
a FastAPI service.

## Project Status

MVP complete (Milestones M1–M11).

- Human thermal stress is modelled with **UTCI** (Universal Thermal
  Climate Index), using the operational **pythermalcomfort** implementation.
- Two exposure scenarios per observation:
  - `reference_shade` — MRT assumed equal to screen-level air temperature.
  - `sun_exposed` — MRT = air temperature + solar radiation gain
    (`thermal/mrt.py`) using pvlib solar geometry.
- Ward heat-health risk is an **explainable proxy**:
  `0.70 × thermal severity + 0.30 × demographic vulnerability`.
- Mortality / hospitalization risk fields are intentionally left **NULL**
  until genuine aggregated health-outcome labels are available.

## Architecture

```
scripts/          one-off data pipelines (ingestion + calculation)
thermal/          UTCI, MRT, solar position, risk classification
risk/             vulnerability, heat-health risk proxy, alert rules
app/
  api/routes.py   FastAPI routes (/api/v1)
  services/       query helpers, alert engine, notification providers
  models/         SQLAlchemy models (PostGIS)
  db/             async engine + session
  core/config.py  pydantic-settings configuration
alembic/          schema migrations
tests/            pytest suite (30 tests)
```

Data flow:

```
ERA5 / Open-Meteo ──► weather_observations / weather_forecasts
        │                       │
        │                       ▼
        │              thermal_indices (UTCI, both scenarios)
        ▼                       │
   SieveNet targets        daily severity per ward
        │                       │
        ▼                       ▼
ward GIS + census ──► demographic_vulnerability ──► risk_predictions
                                                          │
                                                          ▼
                                                     alerts ──► SMS
```

## Quickstart

### 1. Environment

- Python 3.12
- PostgreSQL 14+ with PostGIS (project tested on PostgreSQL 18 / PostGIS 3.6)
- `pvlib`, `pythermalcomfort`, `pandas`, `pydantic`, `fastapi`, `sqlalchemy`,
  `alembic`, `geopandas`, `httpx`, `pytest`

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env   # then set DATABASE_URL
```

### 2. Database

```powershell
.venv\Scripts\alembic upgrade head
```

### 3. Data pipelines (in order)

```powershell
.venv\Scripts\python.exe -m scripts.import_wards_geojson
.venv\Scripts\python.exe -m scripts.download_bhubaneswar_weather
.venv\Scripts\python.exe -m scripts.import_bhubaneswar_weather
.venv\Scripts\python.exe -m scripts.backfill_radiation
.venv\Scripts\python.exe -m scripts.calculate_historical_thermal_indices
.venv\Scripts\python.exe -m scripts.analyze_historical_heat
.venv\Scripts\python.exe -m scripts.populate_ward_vulnerability
.venv\Scripts\python.exe -m scripts.calculate_ward_heat_health_risk
.venv\Scripts\python.exe -m scripts.download_bhubaneswar_forecast
.venv\Scripts\python.exe -m scripts.import_bhubaneswar_forecast
.venv\Scripts\python.exe -m scripts.calculate_forecast_thermal_indices
.venv\Scripts\python.exe -m scripts.calculate_forecast_ward_risk
```

All pipelines are idempotent and may be re-run safely.

### 4. API

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Interactive docs at http://127.0.0.1:8000/docs

## API Routes

| Method | Path                            | Description                              |
| ------ | ------------------------------- | ---------------------------------------- |
| GET    | `/health`                       | Liveness probe                           |
| GET    | `/health/db`                    | Database connectivity probe              |
| GET    | `/api/v1/stations`              | Weather stations                         |
| GET    | `/api/v1/zones`                 | All 67 wards                             |
| GET    | `/api/v1/zones/{code}`          | Single ward                              |
| GET    | `/api/v1/zones/{code}/current-risk` | Latest risk prediction for a ward     |
| GET    | `/api/v1/zones/{code}/forecast` | 5-day ward risk outlook                  |
| GET    | `/api/v1/thermal/latest`        | Latest forecast thermal indices          |
| GET    | `/api/v1/thermal/history`       | Historical thermal indices (paginated)   |
| GET    | `/api/v1/forecast`              | Latest 6-day weather forecast            |
| GET    | `/api/v1/vulnerability`         | Ward vulnerability scores                |
| GET    | `/api/v1/risk-zones`            | GeoJSON FeatureCollection (one per ward, latest forecast day) |
| GET    | `/api/v1/alerts`                | Generated alerts                         |
| POST   | `/api/v1/alerts/generate`       | Create alerts from latest forecast (idempotent) |
| POST   | `/api/v1/alerts/{id}/send`      | Deliver an alert (dry-run by default)    |

## Notifications

SMS alerts default to **dry-run** (`NOTIFICATION_DRY_RUN=true`): messages are
logged, never sent. To enable real delivery, disable dry-run and configure
Twilio credentials via environment variables (see `.env.example`).

## Scientific Notes

- **MRT discipline**: solar radiation is never used directly as mean radiant
  temperature. The shade reference uses air temperature; sun-exposed MRT adds
  the physically-modelled radiative gain (`thermal/mrt.py`).
- **UTCI**: operational implementation with wind clamped to its applicability
  domain (0.5–17 m/s). Categories follow official bands; the 0–100 severity
  score is an application-specific monotonic transform of UTCI (°C).
- **Risk proxy**: composite only; fields named `mortality_risk_score` /
  `hospitalization_risk_score` remain NULL (no real health-outcome labels).

## Tests

```powershell
.venv\Scripts\python.exe -m pytest -v
```

30 tests cover UTCI/MRT physics, severity classification, the risk proxy,
vulnerability scoring, API behaviour, and alert generation/delivery.

## Key Repository Facts

- 52,608 hourly ERA5 observations (2020–2025), 105,216 historical thermal
  indices, 144 forecast hours, 105,504 thermal indices total.
- Peak sun-exposed UTCI in the ERA5 window: **49.70 °C** on 2023-06-16T12:00.
- 402 risk predictions (67 historical peak + 335 forecast), 67 ward alerts
  generated at HIGH/VERY_HIGH from the current forecast.
- Geographic zones are EPSG:4326 with PostGIS geometry (MultiPolygon).