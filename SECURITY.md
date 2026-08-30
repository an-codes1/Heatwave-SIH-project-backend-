# Security Policy

Security documentation for the **Bhubaneswar Extreme Heatwave Early
Warning System** backend (SIH PS83).

> **Status note:** this repository is a *security-conscious hackathon/
> MVP backend*, not a production system. The controls below describe
> what exists today and the gaps that must be closed before any
> production deployment. Prefer the phrase **"production hardening
> required"** over "production secure" when referring to this codebase.
> No credentials or secret values appear anywhere in this document.

---

## Security Philosophy

- Secrets live **in the environment or a secret manager**, never in
  the repository, code, or documentation.
- The API **validates input** and **sanitizes output**; it never
  returns stack traces or credentials to clients.
- **Dry-run by default** for anything that reaches out to the outside
  world (SMS/WhatsApp) until explicitly configured otherwise.
- **Least privilege** everywhere: DB roles, API access, CORS origins.
- **Honesty about data**: no fabricated, guessed, or private medical
  data is ever stored or served.
- External data (weather, GIS, notification provider responses) is
  treated as **untrusted input** and validated before use.

## Supported Environment

- **Local development / demo**: `scripts/run_dev.py` binds uvicorn to
  `127.0.0.1:8000`; a local PostgreSQL 14+ / PostGIS database
  (project tested on PostgreSQL 18 / PostGIS 3.6).
- **CI / tests**: pytest against the live dev DB with a `NullPool`
  engine (`DB_POOL_SIZE=0`).
- **Not yet supported**: multi-tenant production hosting, public
  infrastructure, real Twilio delivery without explicit operator
  configuration.

## Security Controls Already Implemented

Verified by inspection of the current source:

- **`.env` ignored, secrets env-only.** `.gitignore` excludes `.env`;
  `.env.example` ships placeholders only (e.g. a `DATABASE_URL` with an
  obviously-fake password marker and empty `TWILIO_*` values).
  `app/core/config.py` reads secrets as optional settings
  fields; nothing is hardcoded.
- **Admin API key for state-changing endpoints.** `POST
  /api/v1/alerts/generate` and `POST /api/v1/alerts/{id}/send` require
  the `X-Admin-Key` header (`ADMIN_API_KEY` from the environment, via
  the reusable `require_admin` dependency in `app/core/security.py`).
  Missing key or unconfigured key → 401; wrong key → 403;
  comparison is constant-time (`secrets.compare_digest`); the key is
  never logged or echoed. Read-only GET endpoints stay public.
- **Security headers on every response.** `X-Content-Type-Options:
  nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`,
  and a minimal `Permissions-Policy` are added by a lightweight
  middleware (`app/core/security.py`); the Swagger `/docs` pages are
  not affected (no restrictive CSP).
- **Generic 500 responses.** `app/main.py` registers a catch-all
  exception handler that returns `{"detail": "Internal server error."}`
  — no traceback, no internals.
- **DB-failure 503 handling.** SQL layer failures surface as
  `503 Database query failed.` / `503 Database unavailable.` without
  error details.
- **Input validation.** Pydantic response/request schemas, FastAPI
  `Query` constraints (`limit` in `[1, 500]`, `offset ≥ 0`), and a
  whitelist for `level` (`RISK_LEVELS`) →
  `422 UNPROCESSABLE_CONTENT` for unknown risk levels.
- **Parameterized SQL.** All queries use SQLAlchemy ORM/`select`
  statements or raw `text()` with **bound parameters**
  (`app/services/queries.py`); `forecast_day` is always a bound param.
  No string-built user input reaches SQL.
- **Restricted CORS.** `allow_origins` is the explicit
  `http://localhost:3000 / :5173 / 127.0.0.1:*` list from settings; a
  test asserts `'*'` never appears in `cors_origins`.
- **Dry-run notifications.** `NOTIFICATION_DRY_RUN=true` is the
  default and `get_notification_provider()` returns a `DryRunProvider`
  that only logs. The Twilio provider refuses to construct unless all
  three credentials are present. Real sending additionally requires an
  authenticated admin (valid `X-Admin-Key`).
- **Masked notification recipients.** Dry-run/provider log output masks
  recipient identifiers instead of printing them in full.
- **No patient-level data.** `health_outcomes` is an empty,
  aggregation-only table; mortality/hospitalization risk fields are
  NULL by design; tests assert the API never fabricates them.
- **Secret-leakage regression tests.** `tests/test_polish.py` asserts
  configured secrets never appear in API responses.
- **Safe secrets in structured JSON logging.**
  `app/core/logging.py` emits only the message plus explicitly passed
  `extra_fields`; Twilio tokens/DB URLs are never logged.
- **Alert-send recipient guard.** Real (non-dry-run) delivery without
  `ALERT_RECIPIENT_PHONE` fails with 400 rather than sending anywhere.
- **External data validation.** Weather import enforces physical
  ranges; GIS import enforces EPSG:4326 + W1–W67 + MultiPolygon and
  repairs invalid geometry; radiation backfill validates non-negative
  irradiance and supports `--dry-run`.
- **Bounded external HTTP.** httpx calls have 20–60 s timeouts.

## Secrets Management

**Never commit:**

- `.env`
- API keys (Twilio SID / auth token / sender numbers)
- database credentials or `DATABASE_URL` values
- recipient phone numbers / private contact lists
- any authentication token

`.env.example` exists for reference and contains **placeholders only**.
It is tracked on purpose; `.env` and everything credential-bearing is
not.

**Recommendations (not yet implemented in this MVP):**

- Load production secrets from a secret manager (e.g. cloud KMS /
  secrets service); keep environment variables as the injection point.
- Rotate Twilio credentials and DB passwords periodically.
- Never log, print, or embed secret values — including in debugging
  sessions and Demo walkthroughs.

## API Security

Current behavior:

- Types and bounds are validated by FastAPI/Pydantic; page sizes are
  capped; unknown enum values are rejected.
- `send_alert` returns 404 for unknown alert IDs, 503 if the provider
  cannot be built, 502 on delivery failure — all with generic messages.
- DB/API errors never leak stack traces or parameter values.
- The raw GeoJSON query is invoked **only** with bound parameters.
- State-changing admin actions require a valid admin key via the
  reusable `require_admin` dependency (`X-Admin-Key` header):
  401 when the header or `ADMIN_API_KEY` is missing, 403 for a wrong
  key. Constant-time comparison; the key is never logged or echoed.

Admin-protected endpoints:

- `POST /api/v1/alerts/generate` — creates mass alerts (67-ward blast
  surface); requires a valid `X-Admin-Key`.
- `POST /api/v1/alerts/{id}/send` — the only path that can trigger
  real message transmission; requires a valid `X-Admin-Key` and, for
  real delivery, `NOTIFICATION_DRY_RUN=false` plus configured
  credentials.

**Still open before a public deployment:** per-user authentication and
RBAC (the shared API key is not user-level auth), API-key rotation/token
expiry, and rate limiting. Tracked in [TODO.md](TODO.md).

## Database Security

Current:

- Schema is controlled exclusively via **Alembic migrations**; the app
  never mutates schema at runtime.
- Connections are async over `asyncpg` with `pool_pre_ping`.

Recommendations (production):

- Run PostgreSQL with **acquire-only (least-privileged) DB roles**: the
  API user gets `SELECT`/`INSERT`/`UPDATE` on application tables, not
  `SUPERUSER` or schema ownership.
- Deploy a **separate migration role**; app runtime never holds it.
- Enable **encrypted connections** (TLS/`sslmode=require`) in any
  non-local deployment; never transmit DB credentials in plaintext.
- Document and test a **backup policy** (PostGIS-aware); restore drills.
- PostGIS considerations: accept geometry only from the validated BIM
  (BMC) pipeline; never ingest untrusted geometries through the API;
  keep GIST indexes sized and maintained after bulk loads (`VACUUM
  ANALYZE`).

## Data Privacy

- This project **must not store personally identifiable patient
  records** — there is no authN/authZ model and no legal basis in the
  MVP.
- The `health_outcomes` table is intentionally **aggregation-only**
  (zone + date + geographic_resolution + counts). When it is populated
  in the future, data must be:
  1. **Aggregated** to a legitimate geographic/temporal resolution
     (wards/days, not individuals).
  2. **Sourced** and attributed, never estimated or invented.
  3. Handled under the appropriate data-sharing agreement before
     ingestion.
- Aggregate ward population/density from BMC census is the only
  demographic data currently stored.

## External Service Security

- **Open-Meteo (ERA5 archive, forecast):** public data service. Data is
  validated on import (physical value ranges); timestamps are framed in
  Asia/Kolkata and normalized to UTC. Treat responses as untrusted
  (missing keys, `None` values, out-of-range values are all handled).
- **BMC GIS (BhubaneswarOne):** public administrative boundaries. The
  validator enforces expected ward set, CRS 4326, MultiPolygon, and
  geometry validity, and *fails* rather than importing bad data.
- **Twilio:** credentials come from the environment; requests use
  HTTPS with `httpx` (20 s timeout) and HTTP Basic auth. The provider
  validates response status and returns the message SID. Never place
  Twilio credentials in any file that could be committed.

## Notification Safety

- **Dry-run is the default.** `NOTIFICATION_DRY_RUN=true` →
  `DryRunProvider` logs the intended message and returns a marker SID,
  transmitting nothing. Tests assert the `dry_run` field is `true`.
- **Recipient validation.** A single configured recipient
  (`ALERT_RECIPIENT_PHONE`) is used today; no bulk/private lists are
  stored. Real delivery without a recipient configured is refused
  (400). Recipient identifiers are masked in dry-run/provider output.
- **Admin gate before any send.** The `generate` and `send` endpoints
  require a valid `X-Admin-Key`; dry-run remains the default and real
  delivery additionally requires `NOTIFICATION_DRY_RUN=false`.
- **Recommendations before enabling real delivery:**
  - Cap and rate-limit the `send` endpoint (batch limits, per-window
    quotas).
  - Add per-user authorization (the shared admin key is not
    per-operator auth).
  - Validate/normalize recipient phone numbers (E.164) and maintain a
    confirmed opt-in list.
  - Add operator confirmation for anything that could become mass
    messaging.
  - Audit-log each send (target, time, SID), excluding private content.

## Logging Security

`app/core/logging.py` emits single-line JSON to stdout. Observable and
enforced convention: **the following are never logged**:

- passwords / tokens
- `DATABASE_URL` or its credentials
- Twilio SID / auth token
- private phone lists / personal recipient details
- full inbound request bodies on error paths

Structured fields are limited to those explicitly passed via
`log_event(..., **fields)`; keep it that way when adding logs.

## CORS

Current configuration (`app/core/config.py`):

```text
allow_origins  = settings.cors_origins   # explicit localhost list, no wildcard
allow_credentials = True
allow_methods  = ["*"]
allow_headers  = ["*"]
```

Production recommendations:

- Replace the allow-methods/headers wildcards with the minimal set the
  frontend actually uses.
- Keep origins explicit (already the case); add production origin(s)
  to the env list, never to the default.
- If credentials cookies are introduced later, keep `allow_credentials`
  consistent with the origin list (no wildcard origins with
  credentials — already enforced).

## Dependency Security

- `requirements.txt` pins exact versions (`==`), which aids
  reproducible installs and verifiable updates.
- **Run vulnerability scans** before adopting new dependencies and on
  a maintenance cadence, e.g. `pip-audit requirements.txt` (or the
  equivalent of your choice). Fix or document any high-severity
  findings before deployment.
- Keep `pvlib`, `pythermalcomfort`, `fastapi`, `sqlalchemy`,
  `asyncpg`, `uvicorn`, and `pydantic` updated deliberately, with
  regression tests (58-test suite) run after each bump.

## Git Security Checklist

Run before any commit and especially before sharing the repo:

```powershell
git status                              # confirm intended scope
git ls-files | Select-String "\.env$"   # .env must never be tracked
git diff --cached --stat                # review staged files
```

Then scan the tree for secret-looking values (report the **file and
kind** of any hit; never print the match):

```powershell
# e.g. ripgrep for common credential shapes
rg -n "sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|TWILIO_AUTH_TOKEN=|password\s*=" .
```

If a secret is found in history, treat it as compromised: rotate it and
rewrite/trim history (only on private branches, with owner approval).

## Production Security Checklist

- [ ] HTTPS/TLS termination and forced redirect
- [ ] Per-user authentication (shared `X-Admin-Key` is not user auth)
- [ ] Authorization (RBAC) for alert/admin endpoints
- [ ] Rate limiting (all endpoints; stricter on send)
- [ ] Secret manager for Twilio + DB credentials (no `.env` on servers)
- [ ] Least-privileged database user for the API
- [ ] Encrypted database connections
- [ ] Dependency vulnerability scanning integrated (pip-audit or equiv.)
- [ ] Scheduled / verified database backups (PostGIS aware)
- [ ] Monitoring + alerting on failures and send actions
- [ ] Audit logging of alert/admin actions
- [ ] Request/body size limits
- [x] Admin-key gate on state-changing alert endpoints (`require_admin`)
- [x] Security headers on responses (nosniff, frame DENY, no-referrer)

## Reporting a Vulnerability

This is a hackathon/MVP project. If you find a security issue, please
report it **privately** to the repository owner through an appropriate
private channel (GitHub private vulnerability report, or a direct
private message to the maintainer) — do **not** open a public issue
that describes the exploit.

Include, when possible:

1. A clear description of the issue and its impact.
2. Steps to reproduce (without leaking credentials or real data).
3. Suggested fix, if you have one.

The maintainer will acknowledge, fix, and (following the repo's
history rules) release the remediation without revealing any
credentials in the process.

## Known Security Limitations

Be aware — these are **honest, current gaps**, not claims of
production readiness:

- **No per-user authentication or RBAC** — the shared `X-Admin-Key` on
  alert endpoints is single-secret auth, not operator-level control.
- **No rate limiting and no request-size limits** are configured.
- **No audit logging** of admin/alert actions yet.
- **Twilio integration is intended for dry-run/demo operation** unless
  an operator explicitly configures credentials and disables dry-run;
  bulk broadcasting is neither implemented nor safe to enable casually.
- **Local development defaults** (`DEBUG=true`, wide CORS methods,
  bind-to-localhost) are not production configuration.
- The `risk_zones_geojson` raw SQL interpolates a fixed literal SQL
  fragment while keeping user values bound — acceptable now, but
  prefer fully-parameterized statements if the query grows.
- `.env` hygiene depends on contributor discipline; the Git checks
  above are manual, not enforced by CI.