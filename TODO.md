# Project Backlog

Prioritized engineering backlog for the **Bhubaneswar Extreme
Heatwave Early Warning System** backend (SIH PS83). This is a
realistic, hackathon-scoped list — nothing below represents a rebuild
of completed, working functionality. Completed major features are
tracked in [Completed](#completed).

Legend: `[ ]` = open, `[x]` = done.

---

## P0 — Security / Critical

Gaps confirmed by inspection of the current repository:

- [x] **Authentication on the API.** Admin-key gate (DONE on alert
      POST endpoints via `X-Admin-Key` / `ADMIN_API_KEY`,
      `app/core/security.py::require_admin`). Per-user auth (OIDC/JWT)
      and coverage beyond the two alert endpoints remain open.
- [x] **Authorization / RBAC for administrative endpoints.** Protected
      `POST /api/v1/alerts/generate` (401 missing / 403 invalid key).
      `POST /api/v1/alerts/{id}/send` (same gate; real delivery also
      requires dry-run disabled + credentials). Full RBAC per operator
      still open.
- [ ] **Rate limiting** on the whole API, with stricter limits on
      notification-only actions.
- [ ] **TLS / HTTPS** termination (reverse proxy or managed LB) for any
      non-local deployment.
- [x] **Security headers.** `X-Content-Type-Options: nosniff`,
      `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer` added on
      all responses (`SecurityHeadersMiddleware`). HSTS first needs
      HTTPS; CSP only if a strict policy fits `/docs`.
- [ ] **Request-size / body limits** middleware.
- [ ] **Audit logging** of alert generation, send, and any future
      admin action (who/what/when, excluding private recipient lists).
- [ ] **Secret management**: move Twilio credentials and `DATABASE_URL`
      into a secret manager in production (never `.env` on servers).

## P1 — Reliability

- [ ] **Scheduled forecast refresh** (background job / cron) that
      re-runs download → import → thermal → risk → alert pipelines on a
      cadence (e.g. daily).
- [ ] **External API resilience**: retries with backoff and bounded
      timeouts for Open-Meteo calls; alert on provider failure.
- [ ] **Component-level health checks** (weather provider reachability,
      PostGIS extension check) beyond the current `/health/db`.
- [ ] **Database backup + restore procedure** documented and tested.
- [ ] **Monitoring / metrics** (request counts, latency, DB pool
      saturation, last successful forecast refresh).

## P2 — Scientific Improvements

- [ ] **IMD / AWS station validation** of the ERA5-derived city series.
- [ ] **Finer-resolution weather** or documented microclimate
      downscaling for the ward layer.
- [ ] **MRT/UTCI field validation** (e.g. globe-thermometer
      measurements) to ground the sun-exposed scenario assumptions.
- [ ] **Vulnerability enrichment**: ward-level age structure,
      outdoor-worker share, cooling access; replace provisional
      population/density percentile proxy.
- [ ] **Health-outcome dataset integration** (aggregated only) so that
      `mortality_risk_score` / `hospitalization_risk_score` can be
      legitimately populated and validated.

## P3 — API Improvements

- [ ] **Cursor-based pagination** as an alternative to
      limit/offset on `/api/v1/thermal/history`.
- [ ] **Response caching headers** (e.g. `Last-Modified` / `ETag`) for
      stable GeoJSON and latest-forecast responses.
- [ ] **Forecast-day enumeration** helper (which local dates are
      covered by the current generation).
- [ ] Optional **summary endpoint** (counts per risk level) to
      lighten dashboard work.

## P4 — Performance

- [ ] **Materialized view / caching** for the `/api/v1/risk-zones`
      query (currently a multi-table PostGIS join per request).
- [ ] `VACUUM ANALYZE` / maintenance routine after ingestion spikes.
- [ ] Profile the thermal-history query under offset depth; add an
      index or keyset strategy if needed.

## P5 — Testing

- [ ] **Continuous integration** (GitHub Actions): lint, unit tests,
      and a dockerized PostGIS run for reproducibility.
- [ ] **Property/fuzz tests** for classification, severity, and risk
      band boundaries.
- [ ] **Golden-data UTCI cases** (published UTCI reference points)
      rather than self-consistency checks only.
- [ ] Test coverage for the Twilio path (mocked HTTP), not only
      dry-run.

## P6 — Deployment

- [ ] **Dockerfile + docker-compose** (API, PostgreSQL/PostGIS) for
      consistent local and CI environments.
- [ ] **Reverse-proxy config** (TLS, rate limits, header hardening) for
      a production topology.
- [ ] Managed PostgreSQL (+ backups, TLS) and a hardened DB role
      (least privilege — see SECURITY.md).

## P7 — Frontend Integration

Backend contract already exists for these UX pieces (no backend
changes required to build them):

- [ ] **Ward risk map** consuming `GET /api/v1/risk-zones`
      (GeoJSON, `?level=` and `?forecast_day=` filters).
- [ ] **Ward detail** dashboard using `/api/v1/zones/{code}`,
      `/current-risk`, and `/forecast` (5-day outlook).
- [ ] **City thermal strip** from `/api/v1/thermal/latest` (both
      scenarios) and `/api/v1/thermal/history`.
- [ ] **Alerts admin panel** wired to `/api/v1/alerts`,
      `/alerts/generate`, and `/alerts/{id}/send` (dry-run indicator;
      requires the P0 auth/RBAC items before it can be open).

---

## Completed

Already implemented and working — do not rebuild. Verified in the live
DB / test suite:

- [x] ERA5 Bhubaneswar historical weather ingestion (52,608 hourly
      records, 2020–2025) with range validation and source attribution.
- [x] Solar radiation component backfill (direct, diffuse, DNI) with
      `--dry-run` safety.
- [x] Open-Meteo five-day forecast download + idempotent import
      (144 hourly rows).
- [x] pvlib solar position, ASHRAE-55 `solar_gain` MRT (shade +
      sun-exposed scenarios), `pythermalcomfort` UTCI with wind-domain
      clamping.
- [x] 105,504 historical+forecast thermal indices with per-row
      methodology documentation.
- [x] Real BMC ward GIS (67 wards, validated W1–W67, EPSG:4326,
      MultiPolygon) and provisional ward vulnerability from real census
      attributes.
- [x] Explainable heat-health risk proxy (`0.70×severity +
      0.30×vulnerability`), 402 predictions.
- [x] Idempotent alert generation + dry-run notification provider
      abstraction (67 alerts).
- [x] FastAPI surface: zones, thermal (latest/history, paginated),
      forecast, vulnerability, GeoJSON risk map, alerts.
- [x] Structured JSON logging, environment-driven pooling, CORS,
      generic 500 / 503 error handling, secret-hygiene tests.
- [x] Alembic schema (10 tables, head `9c5f7e2a1b3d`).
- [x] 48-test pytest suite + `scripts/test_db.py` + `scripts/test_utci.py`.