# AI Development Context

Concise, safe context for future AI coding assistants working in this
repository. **This file deliberately contains no passwords, tokens,
DATABASE_URL values, Twilio credentials, or personal data.** Do not
add them to it.

---

## Project Identity

- **Bhubaneswar Extreme Heatwave Early Warning System** — backend for
  Smart India Hackathon Problem Statement 83 (SIH PS83).
- Target: Bhubaneswar, Odisha, India.
- Goal: ward-level impact-based heat-health early warning from real
  weather + real GIS + an explainable thermal/risk proxy.

## Current Status

Polished MVP (milestones M1–M11 + hardening pass P1–P20). Completed:

- ERA5 historical ingestion (2020–2025), radiation backfill.
- Open-Meteo 5-day forecast pipeline.
- UTCI/MRT thermal engine with shade + sun-exposed scenarios.
- Real BMC ward GIS (67 wards) + provisional vulnerability.
- Explainable ward heat-health risk proxy (0.70 thermal + 0.30
  vulnerability).
- FastAPI surface, GeoJSON risk map, alerts, dry-run notifications,
  structured logging, CORS, pooling, pagination, error handling.
- 48-test pytest suite. Git history is clean, commits are meaningful.

## Technology Stack

- Python 3.12, FastAPI, Uvicorn, Pydantic v2 / pydantic-settings.
- PostgreSQL + PostGIS (tested on PG 18 / PostGIS 3.6).
- async SQLAlchemy 2.x (asyncpg), Alembic, GeoAlchemy2.
- pvlib, pythermalcomfort, pandas, numpy.
- geopandas / shapely / pyogrio for GIS processing.
- httpx, pytest.

## Key Data Facts (verified against the live DB)

- 67 BMC wards (`geographic_zones`, `W1`–`W67`).
- 52,608 hourly weather observations, 2020–2025 (ERA5 via Open-Meteo).
- 144 forecast hours in the latest generation.
- 105,504 thermal indices (each hour × 2 scenarios).
- 402 risk predictions (67 historical peak + 335 forecast).
- 67 alerts; 67 demographic vulnerability rows.
- `health_outcomes` table exists but is **empty** (do not fill with
  fabricated data).
- Ward GIS + weather are EPSG:4326; model versions `v0.1` (historical)
  and `v0.1-forecast`.
- Peak 2020–2025 sun-exposed UTCI: 49.70 °C (2023-06-16T12:00 IST).

## Scientific Rules (do not break)

- **Solar radiation ≠ MRT.** Radiation (W/m²) is only converted into a
  delta MRT via `pythermalcomfort.models.solar_gain` (ASHRAE 55
  Effective Radiant Field), added to the air-temperature reference.
  There is a regression test enforcing this.
- Two scenarios must stay separate: `*_reference_shade`
  (MRT = air temperature) and `*_sun_exposed` (MRT = air + solar-gain
  delta). At night (solar elevation ≤ 0) sun-exposed equals shade.
- UTCI is computed with the operational `pythermalcomfort` package;
  wind is clamped to the 0.5–17 m/s applicability domain. Every stored
  index row carries a documented `methodology` string.
- Risk proxy: `0.70 × severity(UTCI) + 0.30 × vulnerability`,
  levels via bands at 20/40/60/80.
- Mortality/hospitalization scores must stay **NULL** — no real
  aggregated health labels exist. Never invent them.

## Important Architectural Rules

- Reuse the existing SQLAlchemy `Base` (`app.db.base`) for models;
  register new models in `app/models/__init__.py`.
- Schema changes go through **Alembic** migrations, never raw DDL.
- DB access is **async** (`AsyncSessionLocal`, `get_db()`); keep the
  `DB_POOL_SIZE=0` (NullPool) switch for tests.
- Routes stay thin: parse/validate → call a service/query → return a
  schema. Business logic lives in `app/services/` and `thermal/` /
  `risk/` packages.
- Preserve PostGIS: EPSG:4326, spatial indexes, `ST_*` helpers.
- Pipelines are **idempotent** (unique constraints + skip-if-exists +
  `ON CONFLICT ... DO UPDATE`) — keep them that way.
- `thermal/` and `risk/` must stay pure (no DB, no I/O) so tests and
  scripts can use them without an app import.
- Never rewrite completed features or change API behavior without an
  explicit request.

## Security Rules for AI Assistants

- **Never read, print, or commit `.env`.** It is gitignored. Secrets
  (Twilio SID/token, DATABASE_URL, recipient phone) stay in the
  environment.
- Never put real credentials in code, docs, README, or this file.
- Do not weaken CORS, remove validation, or widen pagination limits to
  make a test pass.
- Notifications must remain **dry-run by default**
  (`NOTIFICATION_DRY_RUN=true`). Never enable real SMS sending by
  default.
- Do not fabricate weather, GIS, mortality, or health data.
- Do not store patient-level health information; `health_outcomes` is
  aggregation-only.
- External API data (Open-Meteo, BMC GIS, Twilio responses) is
  untrusted input — validate it.
- API layers: generic 500 / 503 responses only; never leak
  stack traces or credentials.

## Git Rules

- Check `git status` before editing; target only intended files.
- Run tests before committing anything.
- Keep commits meaningful and scoped to one concern.
- Never rewrite shared history (no force-push, no interactive rebase
  on public branches).

## Current Main Commands

```powershell
# run the API (dev, auto-reload, 127.0.0.1:8000)
.venv\Scripts\python.exe -m scripts.run_dev

# run the test suite (48 tests; requires DB; NullPool)
.venv\Scripts\python.exe -m pytest -v

# database connectivity check
.venv\Scripts\python.exe -m scripts.test_db

# UTCI sanity check
.venv\Scripts\python.exe -m scripts.test_utci

# current migration head (expect 9c5f7e2a1b3d)
.venv\Scripts\alembic.exe current
```

## What NOT to Redo

- ERA5 / forecast ingestion and radiation backfill
- Solar position + MRT + UTCI modules and their physical constants
- Ward GIS validation/import and vulnerability scoring
- Risk proxy maths and risk-level bands
- Alert generation + notification provider abstraction
- FastAPI routes, schemas, CORS, error handling, logging
- Alembic schema and migrations
- The regression/scientific test suite

## Recommended Next Work

Single-change, additive items only (see TODO.md for the full backlog):

- Authentication/RBAC for alert and administrative endpoints.
- Rate limiting, TLS, security headers, secret manager.
- Forecast refresh scheduler / background jobs.
- IMD station validation; finer-resolution weather; MRT validation.
- Vulnerability enrichment and, later, real aggregated health labels.