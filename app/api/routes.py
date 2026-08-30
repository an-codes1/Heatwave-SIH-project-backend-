"""FastAPI routes for the SIH PS83 heat-health platform."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger, log_event
from app.core.security import require_admin
from app.db.session import get_db
from app.models.alert import Alert
from app.schemas.api import (
    AlertGenerationOut,
    AlertOut,
    ForecastOut,
    RiskPredictionOut,
    RiskZonesResponse,
    StationOut,
    ThermalIndexOut,
    VulnerabilityOut,
    ZoneOut,
)
from app.schemas.enums import RISK_LEVELS
from app.services import queries
from app.services.alert_engine import generate_alerts
from app.services.notifications import get_notification_provider
from app.services.notifications.base import DryRunProvider

router = APIRouter(prefix="/api/v1")

logger = get_logger(__name__)


def _db_error() -> None:
    log_event(logger, "ERROR", "database query failed")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database query failed.",
    )


def _risk_out(risk, zone_code: str) -> dict:
    return {
        "zone_code": zone_code,
        "prediction_for": risk.prediction_for,
        "generated_at": risk.prediction_generated_at,
        "thermal_risk_score": risk.thermal_risk_score,
        "mortality_risk_score": risk.mortality_risk_score,
        "hospitalization_risk_score": risk.hospitalization_risk_score,
        "overall_risk_level": risk.overall_risk_level,
        "model_name": risk.model_name,
        "model_version": risk.model_version,
    }


def _thermal_out(index) -> dict:
    return {
        "utci_c": index.utci_c,
        "wbgt_c": index.wbgt_c,
        "heat_index_c": index.heat_index_c,
        "thermal_risk_level": index.thermal_risk_level,
        "scenario": index.calculation_type,
        "calculation_type": index.calculation_type,
        "valid_for": index.valid_for,
        "generated_at": index.calculated_at,
        "methodology": index.methodology,
    }


def _forecast_out(forecast) -> dict:
    return {
        "forecast_for": forecast.forecast_for,
        "generated_at": forecast.forecast_generated_at,
        "air_temperature_c": forecast.air_temperature_c,
        "relative_humidity_pct": forecast.relative_humidity_pct,
        "wind_speed_ms": forecast.wind_speed_ms,
        "solar_radiation_wm2": forecast.solar_radiation_wm2,
        "direct_radiation_wm2": forecast.direct_radiation_wm2,
        "diffuse_radiation_wm2": forecast.diffuse_radiation_wm2,
        "direct_normal_irradiance_wm2": (
            forecast.direct_normal_irradiance_wm2
        ),
        "atmospheric_pressure_hpa": forecast.atmospheric_pressure_hpa,
        "source": forecast.source,
    }


def _alert_out(
    alert: Alert,
    zone_by_id: dict[int, str | None],
    dry_run: bool,
) -> dict:
    return {
        "id": alert.id,
        "zone_code": zone_by_id.get(alert.zone_id),
        "alert_level": alert.alert_level,
        "alert_message": alert.alert_message,
        "recommended_action": alert.recommended_action,
        "status": alert.status,
        "channel": alert.channel,
        "created_at": alert.created_at,
        "sent_at": alert.sent_at,
        "dry_run": dry_run,
    }


@router.get(
    "/stations",
    response_model=list[StationOut],
    tags=["Stations"],
    summary="List weather stations",
    description="Weather stations used to drive the thermal pipeline.",
)
async def get_stations(
    session: AsyncSession = Depends(get_db),
):
    try:
        stations = await queries.list_stations(session)
    except SQLAlchemyError:
        _db_error()

    return stations


@router.get(
    "/zones",
    response_model=list[ZoneOut],
    tags=["Zones"],
    summary="List all BMC wards",
    description="Returns the 67 Bhubaneswar Municipal Corporation wards.",
)
async def get_zones(
    session: AsyncSession = Depends(get_db),
):
    try:
        zones = await queries.list_zones(session)
    except SQLAlchemyError:
        _db_error()

    return zones


@router.get(
    "/zones/{zone_code}",
    response_model=ZoneOut,
    tags=["Zones"],
    summary="Get a single ward",
)
async def get_zone(
    zone_code: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        zone = await queries.get_zone_by_code(session, zone_code)
    except SQLAlchemyError:
        _db_error()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_code} not found.",
        )

    return zone


@router.get(
    "/zones/{zone_code}/current-risk",
    response_model=RiskPredictionOut,
    tags=["Risk"],
    summary="Latest risk for a ward",
    description=(
        "Latest heat-health risk proxy for a ward. mortality and "
        "hospitalization scores are NULL unless a real health model exists."
    ),
)
async def get_zone_current_risk(
    zone_code: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        zone = await queries.get_zone_by_code(session, zone_code)
    except SQLAlchemyError:
        _db_error()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_code} not found.",
        )

    try:
        risk = await queries.zone_current_risk(session, zone.id)
    except SQLAlchemyError:
        _db_error()

    if risk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current risk prediction available.",
        )

    return _risk_out(risk, zone_code)


@router.get(
    "/zones/{zone_code}/forecast",
    response_model=list[RiskPredictionOut],
    tags=["Forecast"],
    summary="Five-day ward risk outlook",
    description=(
        "Daily heat-health risk for one ward across the five-day "
        "forecast window, oldest to newest."
    ),
)
async def get_zone_forecast(
    zone_code: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        zone = await queries.get_zone_by_code(session, zone_code)
    except SQLAlchemyError:
        _db_error()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_code} not found.",
        )

    try:
        predictions = await queries.zone_forecast_risks(
            session, zone.id
        )
    except SQLAlchemyError:
        _db_error()

    return [_risk_out(risk, zone_code) for risk in predictions]


@router.get(
    "/thermal/latest",
    response_model=list[ThermalIndexOut],
    tags=["Thermal"],
    summary="Latest city thermal state",
    description=(
        "Most recent forecast thermal indices (shade and sun-exposed "
        "scenarios) for the city station."
    ),
)
async def get_thermal_latest(
    session: AsyncSession = Depends(get_db),
):
    try:
        indices = await queries.latest_forecast_thermal(session)
    except SQLAlchemyError:
        _db_error()

    return [_thermal_out(index) for index in indices]


@router.get(
    "/thermal/history",
    response_model=list[ThermalIndexOut],
    tags=["Thermal"],
    summary="Historical thermal indices",
    description=(
        "Paginated historical thermal indices (ERA5 reprocessed, "
        "2020-2025). Use limit/offset; maximum limit is 500."
    ),
)
async def get_thermal_history(
    calculation_type: str | None = Query(
        default=None,
        description="Filter by calculation type, e.g. "
        "observed_reference_shade or observed_sun_exposed.",
    ),
    limit: int = Query(
        default=48, ge=1, le=500, description="Page size (max 500)."
    ),
    offset: int = Query(
        default=0, ge=0, description="Rows to skip (0-based)."
    ),
    session: AsyncSession = Depends(get_db),
):
    try:
        indices = await queries.thermal_history(
            session,
            calculation_type,
            limit,
            offset,
        )
    except SQLAlchemyError:
        _db_error()

    return [_thermal_out(index) for index in indices]


@router.get(
    "/forecast",
    response_model=list[ForecastOut],
    tags=["Forecast"],
    summary="Latest six-day weather forecast",
    description=(
        "Hourly Open-Meteo forecast (144 rows) for the current "
        "generation. Radiation units are W/m^2."
    ),
)
async def get_forecast(
    session: AsyncSession = Depends(get_db),
):
    try:
        forecasts = await queries.list_forecast_weather(session)
    except SQLAlchemyError:
        _db_error()

    return [_forecast_out(item) for item in forecasts]


@router.get(
    "/vulnerability",
    response_model=list[VulnerabilityOut],
    tags=["Risk"],
    summary="Ward vulnerability scores",
    description=(
        "Provisional 0-100 demographic vulnerability per ward, computed "
        "from real BMC census attributes in the ward GIS data."
    ),
)
async def get_vulnerability(
    session: AsyncSession = Depends(get_db),
):
    try:
        zones = await queries.list_zones(session)
        vulnerabilities = await queries.list_vulnerabilities(session)
    except SQLAlchemyError:
        _db_error()

    vulnerability_by_zone = {
        row.zone_id: row for row in vulnerabilities
    }

    output = []

    for zone in zones:
        vuln = vulnerability_by_zone.get(zone.id)

        output.append(
            {
                "zone_code": zone.zone_code,
                "zone_name": zone.zone_name,
                "total_population": (
                    vuln.total_population if vuln else None
                ),
                "population_density_per_km2": (
                    vuln.population_density_per_km2
                    if vuln
                    else None
                ),
                "vulnerability_score": (
                    vuln.vulnerability_score if vuln else None
                ),
                "reference_year": (
                    vuln.reference_year if vuln else None
                ),
                "source": vuln.source if vuln else None,
            }
        )

    return output


@router.get(
    "/risk-zones",
    response_model=RiskZonesResponse,
    tags=["Risk"],
    summary="GeoJSON ward risk map",
    description=(
        "One GeoJSON Feature per ward (67 unfiltered). Geometry is real "
        "BMC boundary data in EPSG:4326. Filter by risk level or local "
        "forecast day (ISO date, Asia/Kolkata)."
    ),
)
async def get_risk_zones(
    level: str | None = Query(
        default=None,
        description="Filter features by overall risk level.",
    ),
    forecast_day: str | None = Query(
        default=None,
        description=(
            "Filter features by local forecast day (ISO date e.g. "
            "2026-09-02, Asia/Kolkata)."
        ),
    ),
    session: AsyncSession = Depends(get_db),
):
    if level is not None and level not in RISK_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid risk level '{level}'. "
            f"Allowed: {', '.join(RISK_LEVELS)}.",
        )

    try:
        collection = await queries.risk_zones_geojson(
            session,
            level,
            forecast_day,
        )
    except SQLAlchemyError:
        _db_error()

    return collection


@router.get(
    "/alerts",
    response_model=list[AlertOut],
    tags=["Alerts"],
    summary="List generated alerts",
    description="All generated heat-health alerts, newest first.",
)
async def get_alerts(
    session: AsyncSession = Depends(get_db),
):
    try:
        alerts = await queries.list_alerts(session)
        zones = await queries.list_zones(session)
    except SQLAlchemyError:
        _db_error()

    zone_by_id = {zone.id: zone.zone_code for zone in zones}

    return [
        _alert_out(
            alert,
            zone_by_id,
            dry_run=settings.notification_dry_run,
        )
        for alert in alerts
    ]


@router.post(
    "/alerts/generate",
    response_model=AlertGenerationOut,
    tags=["Alerts"],
    summary="Generate alerts from latest forecast",
    description=(
        "Creates one alert per ward whose peak five-day risk reaches "
        "HIGH or above. Idempotent: re-running deduplicates existing "
        "pending/sent alerts."
    ),
)
async def generate_zone_alerts(
    _admin: None = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    try:
        created, counts = await generate_alerts(session)
        zones = await queries.list_zones(session)
    except RuntimeError as exc:
        log_event(logger, "WARNING", "alert generation failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except SQLAlchemyError:
        _db_error()

    zone_by_id = {zone.id: zone.zone_code for zone in zones}

    log_event(
        logger,
        "INFO",
        "alerts generated",
        generated=counts["generated"],
        deduplicated=counts["deduplicated"],
        below_threshold=counts["below_threshold"],
        dry_run=settings.notification_dry_run,
    )

    return {
        "generated": counts["generated"],
        "deduplicated": counts["deduplicated"],
        "below_threshold": counts["below_threshold"],
        "dry_run_default": settings.notification_dry_run,
        "alerts": [
            _alert_out(
                alert,
                zone_by_id,
                dry_run=settings.notification_dry_run,
            )
            for alert in created
        ],
    }


@router.post(
    "/alerts/{alert_id}/send",
    response_model=AlertOut,
    tags=["Alerts"],
    summary="Send an alert notification",
    description=(
        "Delivers an alert through the configured provider. Dry-run is "
        "the default: the message is logged and the alert is marked "
        "status=sent with dry_run=true. Real SMS requires Twilio "
        "credentials and NOTIFICATION_DRY_RUN=false."
    ),
)
async def send_alert(
    alert_id: int,
    _admin: None = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
):
    alert = await session.get(Alert, alert_id)

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found.",
        )

    try:
        provider = get_notification_provider()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    recipient = settings.alert_recipient_phone
    dry_run = isinstance(provider, DryRunProvider)

    if not recipient:
        if dry_run:
            recipient = "dry-run-recipient"
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ALERT_RECIPIENT_PHONE is not configured.",
            )

    message = f"[{alert.alert_level}] {alert.alert_message}"

    try:
        reference = provider.send(recipient, message)
    except Exception as exc:
        log_event(logger, "ERROR", "notification delivery failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Notification delivery failed.",
        )

    alert.status = "sent"
    alert.sent_at = datetime.now(timezone.utc)

    try:
        await session.commit()
        zones = await queries.list_zones(session)
    except SQLAlchemyError:
        _db_error()

    zone_by_id = {zone.id: zone.zone_code for zone in zones}

    log_event(
        logger,
        "INFO",
        "alert sent",
        alert_id=alert.id,
        dry_run=dry_run,
        reference=reference,
    )

    return _alert_out(alert, zone_by_id, dry_run=dry_run)