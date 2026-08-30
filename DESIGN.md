# System Design

Design rationale for the **Bhubaneswar Extreme Heatwave Early Warning
System** backend (Smart India Hackathon — Problem Statement 83).

This document explains **why** the backend is built the way it is. It
describes only what is actually implemented in this repository. The
companion document [ARCHITECTURE.md](ARCHITECTURE.md) explains *how*
the pieces fit together.

---

## Problem Statement

Severe heat in an urban area like Bhubaneswar (Odisha) is not just a
weather phenomenon — it is a **public-health exposure event**. A
weather forecast answers *"how hot will it be?"*; an early warning
must answer *"which people are at risk, in which wards, on which
days, and what should be done now?"*

The project therefore makes the transition:

```
weather forecasting
        │
        ▼
impact-based heat-health early warning
```

Concretely, the backend combines:

1. **Real weather** — ERA5 reanalysis history (2020–2025) and a real
   Open-Meteo five-day forecast for the Bhubaneswar grid point.
2. **Human thermal stress modelling** — UTCI computed from physically
   modelled mean radiant temperature (MRT) for two exposure scenarios.
3. **Real geography** — official BMC ward boundaries (67 wards) and
   real ward census attributes from the BMC GIS layer.
4. **An explainable risk proxy** — thermal severity combined with ward
   demographic vulnerability, published per ward and per day.
5. **Actionable alerts** — generation of ward-level alerts with
   recommended actions, delivered through a notification abstraction.

## Design Goals

| Goal | What it means here |
| ---- | ------------------ |
| **Real data** | No fabricated weather, GIS, or health labels. Every record carries a `source`. |
| **Explainability** | Every thermal index stores a `methodology` string; risk weights are explicit constants; mortality/hospitalization stay NULL rather than invented. |
| **Reproducibility** | Fixed assumptions (ASHRAE-55 exposure parameters), fixed formula constants, deterministic scripts, and versioned models (`v0.1`, `v0.1-forecast`). |
| **GIS-first architecture** | Wards are real EPSG:4326 MultiPolygons in PostGIS; risk maps are served as GeoJSON. |
| **Scientific traceability** | UTCI bands (Blazejczyk / UTCI standard), `solar_gain` (ASHRAE 55 Effective Radiant Field), pvlib solar geometry, and pythermalcomfort operational code are cited in the methodology of each stored value. |
| **Idempotent ingestion** | Pipelines can be re-run safely: unique constraints, skip-if-exists checks, and `ON CONFLICT` upserts. |
| **Frontend-friendly APIs** | Thin FastAPI routes serve clean schemas, pagination, GeoJSON, and stable enums for dashboards/maps. |
| **Safety** | Dry-run notifications by default, generic error responses, no patient-level data, no secret leakage. |
| **Modularity** | Separate `thermal/`, `risk/`, `scripts/`, and `app/` packages with clear ownership. |

## Core Design Decisions

### FastAPI (async)
Python-native, typed with Pydantic response models, automatic OpenAPI
docs, and clean dependency injection for the async DB session.
Deliberate decision: the whole stack leans on Python's scientific
ecosystem (`pvlib`, `pythermalcomfort`, `pandas`, `geopandas`).

### PostgreSQL + PostGIS
Relational storage with native geospatial types and functions
(`ST_AsGeoJSON`, `ST_Area(::geography)`, GIST spatial indexes). Wards
and stations keep their geometry in `EPSG:4326` so coordinates are
ingested and served without reprojection ambiguity.

### async SQLAlchemy 2.x
Async ORM over `asyncpg`, with `async_sessionmaker` and request-scoped
sessions. Pooling is environment-driven (`DB_POOL_SIZE=0` selects
`NullPool` for the test suite, otherwise a sized pool with
`pool_pre_ping`).

### Alembic
All schema changes are migrations. `alembic/env.py` reads the async
DSN from settings and imports the shared `Base` metadata so
autogenerate stays in sync with `app/models/`.

### ERA5 / Open-Meteo as weather source
Open-Meteo's archive API exposes ERA5 reanalysis for the 0.25° cell
containing Bhubaneswar (the grid point 20.25°N 85.75°E). Reanalysis
gives a **consistent, reproducible 2020–2025 hourly history** that a
single imperfect station time series cannot. The forecast API provides
a fresh five/six-day operational outlook.

**Caveat (documented in Trade-offs):** this is gridded reanalysis, not
an IMD station time series.

### BMC ward GIS
Ward boundaries come from the BhubaneswarOne ("BMC") administrative
GIS service. A validation pipeline enforces W1–W67 uniqueness and
MultiPolygon/4326 integrity before ingestion. Ward census attributes
travel with the geometry, providing the population data used for
vulnerability.

### UTCI (Universal Thermal Climate Index)
UTCI is the thermo-physiological index chosen because it responds to
air temperature, humidity, wind, **and** mean radiant temperature —
exactly the inputs an early-warning planner cares about under an
Indian sun. The operational `pythermalcomfort` implementation is used
(via `thermal/utci.py`) with wind clamped to its 0.5–17 m/s
applicability domain.

### Reference-shade vs sun-exposed MRT (two scenarios)
MRT is the single largest missing piece of "what it feels like in the
sun". Because a single "the answer" is scientifically misleading, the
project deliberately computes **two labelled scenarios**:

- `reference_shade` — MRT = screen-level air temperature (a documented
  shade reference).
- `sun_exposed` — MRT = air temperature + the physically-modelled
  `solar_gain` (ASHRAE 55 Effective Radiant Field) delta, using ERA5/
  forecast DNI and pvlib solar elevation.

Both are stored as rows of `thermal_indices` with distinct
`calculation_type` values and their own `methodology` text.

### Ward risk proxy
`risk/heat_health_risk.py` combines:

```
composite = 0.70 × thermal severity (0–100)
          + 0.30 × ward vulnerability (0–100)
```

Weights are explicit constants. `thermal_severity` is an
application-specific monotonic transform of UTCI (100 × (UTCI−26)/
(46−26), clamped). Discrete levels (`LOW … EXTREME`) come from bands
at 20/40/60/80.

### Separation of observations and forecasts
Historical risk (`model_version = v0.1`) and forecast risk
(`v0.1-forecast`) live in the same tables but are kept apart by
`model_version` and `generated_at`, so the API can always serve "the
latest forecast generation" without engine-level ambiguity.

### Separation of thermal risk and health-outcome prediction
The code computes a thermal/planning proxy only. `mortality_risk_score`
and `hospitalization_risk_score` columns exist in the schema but stay
NULL — see [Risk Design](#risk-design).

## Data Integrity Design

- **No fabricated weather.** Every observation/forecast row is
  validated (physical value ranges) and stamped with `source`
  (`"Open-Meteo ERA5 reanalysis"`, `"Open-Meteo Forecast API"`).
- **No fabricated GIS.** Wards come from a real public GIS service;
  the importer refuses non-4326 data and the validator repairs and
  re-checks geometry with `shapely.make_valid`.
- **No fabricated mortality labels.** Health-outcome fields are NULL
  (see Risk Design).
- **Source attribution.** `source` columns on stations, zones,
  observations, forecasts, and vulnerability rows identify the exact
  upstream dataset.
- **Timestamp preservation.** Local Asia/Kolkata timestamps from
  Open-Meteo are framed with `tzinfo=Asia/Kolkata` and normalized to
  UTC in the DB; APIs return ISO-8601 aware datetimes.
- **CRS preservation.** Geometry is stored and served in EPSG:4326.
- **Idempotent ingestion.** Unique constraints
  (`uq_weather_observation_station_time`,
  `uq_weather_forecast_station_generation_target`,
  `uq_thermal_index_station_time_type`,
  `uq_risk_prediction_zone_generation_target_model`,
  `uq_demographic_zone_year`) plus explicit skip-if-exists and
  `ON CONFLICT DO UPDATE` make every pipeline safe to re-run.

## Scientific Design

Inputs to the thermal engine (per hour): air temperature, relative
humidity, wind speed, and radiation components (shortwave, direct,
diffuse, DNI). Solar position (elevation/azimuth) is computed with
pvlib for the Bhubaneswar grid point in Asia/Kolkata.

```
air temperature ─┐
humidity        ─┼─► UTCI (pythermalcomfort, wind 0.5–17 m/s)
wind            ─┘            │
                               ▼
MRT (shade or sun) ─────► UTCI (°C) ─► stress category ─► severity 0–100
```

### Solar radiation ≠ MRT (important)

Solar radiation (W/m²) is **never used directly as a temperature**.
Irradiance is converted by the ASHRAE 55 Effective Radiant Field
`pythermalcomfort.models.solar_gain` into a **delta MRT (°C)**, which
is then *added to the air-temperature reference*. This is enforced by
design in `thermal/mrt.py` and locked by regression test
`test_radiation_never_used_directly_as_mrt`.

### The two thermal scenarios

| Scenario | MRT | `calculation_type` |
| -------- | --- | ------------------- |
| Reference/shade | MRT = air temperature (labelled shade reference, not direct-sun) | `observed_reference_shade` / `forecast_reference_shade` |
| Sun-exposed | MRT = air temperature + `solar_gain` delta (standardized standing person, SHARP 90°, f_bes 0.224, α 0.7) | `observed_sun_exposed` / `forecast_sun_exposed` |

At night (solar elevation ≤ 0) the sun-exposed scenario collapses to
the shade reference — a useful, physically expected property.

## Risk Design

```
thermal severity (0–100)        ward vulnerability (0–100)
      └─────────── 0.70 ────┐       0.30 ────┘
                             ▼
                    composite risk 0–100
                             │  (bands 20/40/60/80)
                             ▼
                 LOW │ MODERATE │ HIGH │ VERY_HIGH │ EXTREME
```

Vulnerability (0–100) is a provisional equal-weight combine of a ward's
percentile rank of population and of population density within the 67
wards, from real BMC census attributes. Elderly/child/outdoor-worker
terms are intentionally omitted until reliable ward-level values exist.

**Explicit non-claim:** this is a planning/exposure proxy. It is NOT a
probability of mortality or hospitalization. Without genuine aggregated
health-outcome labels, `mortality_risk_score` and
`hospitalization_risk_score` are always NULL — never filled with
heuristics.

## Alert Design

1. Forecast thermal indices are computed from the latest Open-Meteo
   forecast (`calculate_forecast_thermal_indices.py`).
2. Daily ward risk is computed from the peak sun-exposed UTCI severity
   of each local day, T+1…T+5 (`calculate_forecast_ward_risk.py`).
3. `POST /api/v1/alerts/generate` calls `generate_alerts`, which takes
   the **peak** five-day risk per ward and creates one `Alert` row for
   every ward reaching `HIGH` or above (`MIN_ALERT_LEVEL`), with a
   message and recommended action from `risk/alert_rules.py`.
4. Generation is idempotent (deduplicates against existing
   pending/sent alerts referencing the same risk prediction).
5. `POST /api/v1/alerts/{id}/send` routes through a provider
   abstraction (`DryRunProvider` by default, `TwilioSmsProvider` when
   explicitly configured). Dry-run logs the message and marks the
   alert `sent` without transmitting anything.

## Security-by-Design

Already present:

- Secrets come from the environment only (`.env` gitignored);
  `.env.example` holds placeholders.
- Generic 500 responses and 503 DB errors never leak stack traces.
- Pydantic/Query validation, bounded pagination, and a risk-level
  whitelist reject malformed input.
- SQL is parametrized (ORM plus bound-parameter raw SQL).
- CORS is restricted to an explicit localhost origin list.
- Notifications default to **dry-run**.
- Structured JSON logging that excludes secrets; regression tests
  assert no secret leakage in API bodies.
- No patient-level data stored (`health_outcomes` is an empty,
  aggregation-only table).

Remaining production hardening (not implemented yet): authentication
and authorization on API endpoints (especially `alerts/generate` and
`alerts/{id}/send`), rate limiting, HTTPS/TLS termination, security
headers, request-size limits, secret manager integration, and audit
logging. See [SECURITY.md](SECURITY.md) and [TODO.md](TODO.md).

## Trade-offs

- **ERA5 spatial resolution.** ERA5 is gridded reanalysis (0.25°); it
  is not a point measurement at an IMD station. It is the most
  reproducible public history available, but ground-truth station
  validation is future work.
- **Ward-level downscaling.** A single city grid point feeds every
  ward; heat islands and microclimates inside Bhubaneswar are not
  resolved. Ward differentiation comes from exposure scenarios and
  vulnerability, not spatial weather variation.
- **MRT assumptions.** The sun-exposed scenario uses a *standardized*
  standing person (ASHRAE-style constants) — not measurements of any
  real person. The shade reference is a deliberate simplification
  labeled as such.
- **Provisional demographic vulnerability.** Population/density
  percentile ranks are a defensible but coarse proxy until
  age/occupation-disaggregated ward data is available.
- **Lack of real health-outcome labels.** Without aggregated
  mortality/hospitalization data, the mortality/hospitalization
  fields remain NULL and no disease-intensity claim is made.

## Future Design Evolution

Safe, additive directions (no core rebuild; see TODO.md for the
ordered backlog):

- IMD / AWS station validation and blending.
- Higher-resolution weather or local downscaling.
- MRT/UTCI validation against field observations (e.g. globe
  thermometers).
- Ward vulnerability enrichment (age, outdoor workers, cooling access).
- Integrated aggregated health-outcome datasets for genuine
  mortality/hospitalization modelling.
- Authentication/RBAC, rate limiting, scheduled forecast refresh, and
  production deployment hardening.