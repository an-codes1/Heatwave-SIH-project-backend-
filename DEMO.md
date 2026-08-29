# Demo — SIH PS83 Heat-Health Early Warning Backend

End-to-end walkthrough against a running local instance. PowerShell uses
`Invoke-RestMethod`; the outputs shown are from a live run of this project.

## 0. Start the API

```powershell
.venv\Scripts\python.exe -m scripts.run_dev
```

(equivalent: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`)

Interactive Swagger UI: http://127.0.0.1:8000/docs

## 1. Health checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/health/db
```

```json
{"status": "healthy"}
{"status": "healthy", "database": "ok", "test": 1, "latency_ms": 2.3}
```

## 2. Ward catalogue

```powershell
(Invoke-RestMethod http://127.0.0.1:8000/api/v1/zones).Count   # 67
```

## 3. Current risk for a ward (explainable proxy)

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/zones/W1/current-risk
```

```json
{
  "zone_code": "W1",
  "prediction_for": "2026-09-03T18:30:00+00:00",
  "thermal_risk_score": 59.30,
  "mortality_risk_score": null,
  "hospitalization_risk_score": null,
  "overall_risk_level": "HIGH",
  "model_name": "heat_health_risk_proxy",
  "model_version": "v0.1-forecast"
}
```

Note: `mortality_risk_score` / `hospitalization_risk_score` are **NULL** by
design — no aggregated health-outcome labels exist, so we never fabricate them.

## 4. Five-day ward outlook

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/zones/W1/forecast
```

Returns one prediction per forecast day (5 entries, ascending),
`overall_risk_level` varies LOW..EXTREME.

## 5. GeoJSON risk surface

```powershell
$fc = Invoke-RestMethod http://127.0.0.1:8000/api/v1/risk-zones
$fc.features.Count           # 67 (one per ward, latest forecast day)
$fc.features[0].properties
```

```json
{
  "zone_code": "W1",
  "zone_name": "Ward 1",
  "population": 12378,
  "population_density": 4785.1,
  "vulnerability_score": 40.3,
  "thermal_risk_score": 59.30,
  "overall_risk_level": "HIGH",
  "valid_for": "2026-09-03T18:30:00+00:00"
}
```

Filter by level:

```powershell
$fc = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/risk-zones?level=VERY_HIGH"
$fc.features.Count   # wards peaking at VERY_HIGH on the latest forecast day
```

In the current forecast the peak (latest-day) ward distribution is
HIGH / VERY_HIGH / MODERATE; the peak-day filter never returns EXTREME
until a hotter generation exists.

## 6. Historical heat stress (ERA5, 2020–2025)

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/v1/thermal/history?calculation_type=observed_sun_exposed&limit=3"
```

Peak in the window: **sun-exposed UTCI 49.70 °C** at
2023-06-16T12:00+05:30 (reference-shade 42.44 °C). Annual maxima and
heat-stress hour counts are in `data/processed/thermal_analysis.json`.

## 7. Vulnerability

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/vulnerability
```

67 wards with provisional 0–100 vulnerability scores (population + density),
drawn from real BMC census attributes in the ward GIS data.

## 8. Alerts

Generate alerts idempotently (deduplicates previously created alerts):

On the first run 67 alerts are created (one per ward whose peak 5-day risk
reaches HIGH or above). Re-running just deduplicates:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/v1/alerts/generate   # 2nd run
```

```json
{
  "generated": 0,
  "deduplicated": 67,
  "below_threshold": 0,
  "alerts": []
}
```

List alerts:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/alerts
```

Sample alert:

```json
{
  "id": 67,
  "zone_code": "W9",
  "alert_level": "VERY_HIGH",
  "alert_message": "VERY HIGH heat-health risk for ward W9 on 2026-09-04. Peak risk score 65/100.",
  "recommended_action": "Limit non-essential outdoor activity, use shaded cooling points, and prioritize vulnerable groups.",
  "status": "sent",
  "channel": "sms",
  "dry_run": true,
  "created_at": "...",
  "sent_at": "..."
}
```

### Send an alert (dry-run by default)

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/alerts/1/send"
```

With `NOTIFICATION_DRY_RUN=true` the message is logged to the server console,
never transmitted, and the alert is marked `sent` with a `sent_at` timestamp.
To deliver real SMS, set the Twilio variables in `.env` and
`NOTIFICATION_DRY_RUN=false`.

## 9. Reproducing the forecast

```powershell
.venv\Scripts\python.exe -m scripts.download_bhubaneswar_forecast
.venv\Scripts\python.exe -m scripts.import_bhubaneswar_forecast
.venv\Scripts\python.exe -m scripts.calculate_forecast_thermal_indices
.venv\Scripts\python.exe -m scripts.calculate_forecast_ward_risk
```

## 10. Tests

```powershell
.venv\Scripts\python.exe -m pytest -v      # 48 passed
.venv\Scripts\python.exe -m scripts.test_db
.venv\Scripts\python.exe -m scripts.test_utci
.venv\Scripts\alembic.exe current          # 9c5f7e2a1b3d (head)
```

## Warranty / Limitations

- Heat-health risk is a planning **proxy**, not a disease forecast.
- ERA5 is gridded reanalysis for the 0.25° cell containing Bhubaneswar;
  it is not an IMD station time series.
- Notifications are dry-run unless Twilio credentials are configured.