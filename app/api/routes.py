from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.schemas.api import (
    AlertOut,
    ForecastOut,
    RiskPredictionOut,
    RiskZonesResponse,
    StationOut,
    ThermalIndexOut,
    VulnerabilityOut,
    ZoneOut,
)
from app.services import queries
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1")


def db_error_handler() -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database query failed.",
    )


@router.get("/stations", response_model=list[StationOut])
async def get_stations(
    session: AsyncSession = Depends(get_db),
):
    try:
        stations = await queries.list_stations(session)
    except SQLAlchemyError:
        db_error_handler()

    return stations


@router.get("/zones", response_model=list[ZoneOut])
async def get_zones(
    session: AsyncSession = Depends(get_db),
):
    try:
        zones = await queries.list_zones(session)
    except SQLAlchemyError:
        db_error_handler()

    return zones


@router.get(
    "/zones/{zone_code}",
    response_model=ZoneOut,
)
async def get_zone(
    zone_code: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        zone = await queries.get_zone_by_code(session, zone_code)
    except SQLAlchemyError:
        db_error_handler()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_code} not found.",
        )

    return zone


@router.get(
    "/zones/{zone_code}/current-risk",
    response_model=RiskPredictionOut,
)
async def get_zone_current_risk(
    zone_code: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        zone = await queries.get_zone_by_code(session, zone_code)
    except SQLAlchemyError:
        db_error_handler()

    if zone is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone {zone_code} not found.",
        )

    try:
        risk = await queries.zone_current_risk(session, zone.id)
    except SQLAlchemyError:
        db_error_handler()

    if risk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No current risk prediction available.",
        )

    return {
        "zone_code": zone_code,
        "prediction_for": risk.prediction_for,
        "thermal_risk_score": risk.thermal_risk_score,
        "mortality_risk_score": risk.mortality_risk_score,
        "hospitalization_risk_score": (
            risk.hospitalization_risk_score
        ),
        "overall_risk_level": risk.overall_risk_level,
        "model_name": risk.model_name,
        "model_version": risk.model_version,
    }


@router.get(
    "/zones/{zone_code}/forecast",
    response_model=list[RiskPredictionOut],
)
async def get_zone_forecast(
    zone_code: str,
    session: AsyncSession = Depends(get_db),
):
    try:
        zone = await queries.get_zone_by_code(session, zone_code)
    except SQLAlchemyError:
        db_error_handler()

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
        db_error_handler()

    return [
        {
            "zone_code": zone_code,
            "prediction_for": risk.prediction_for,
            "thermal_risk_score": risk.thermal_risk_score,
            "mortality_risk_score": risk.mortality_risk_score,
            "hospitalization_risk_score": (
                risk.hospitalization_risk_score
            ),
            "overall_risk_level": risk.overall_risk_level,
            "model_name": risk.model_name,
            "model_version": risk.model_version,
        }
        for risk in predictions
    ]


@router.get(
    "/thermal/latest",
    response_model=list[ThermalIndexOut],
)
async def get_thermal_latest(
    session: AsyncSession = Depends(get_db),
):
    try:
        indices = await queries.latest_forecast_thermal(session)
    except SQLAlchemyError:
        db_error_handler()

    return indices


@router.get(
    "/thermal/history",
    response_model=list[ThermalIndexOut],
)
async def get_thermal_history(
    calculation_type: str | None = Query(default=None),
    limit: int = Query(default=48, ge=1, le=2000),
    session: AsyncSession = Depends(get_db),
):
    try:
        indices = await queries.thermal_history(
            session,
            calculation_type,
            limit,
        )
    except SQLAlchemyError:
        db_error_handler()

    return indices


@router.get("/forecast", response_model=list[ForecastOut])
async def get_forecast(
    session: AsyncSession = Depends(get_db),
):
    try:
        forecasts = await queries.list_forecast_weather(session)
    except SQLAlchemyError:
        db_error_handler()

    return forecasts


@router.get(
    "/vulnerability",
    response_model=list[VulnerabilityOut],
)
async def get_vulnerability(
    session: AsyncSession = Depends(get_db),
):
    try:
        zones = await queries.list_zones(session)
        vulnerabilities = await queries.list_vulnerabilities(session)
    except SQLAlchemyError:
        db_error_handler()

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
)
async def get_risk_zones(
    level: str | None = Query(
        default=None,
        description="Filter features by overall risk level.",
    ),
    session: AsyncSession = Depends(get_db),
):
    try:
        collection = await queries.risk_zones_geojson(
            session,
            level,
        )
    except SQLAlchemyError:
        db_error_handler()

    return collection


@router.get("/alerts", response_model=list[AlertOut])
async def get_alerts(
    session: AsyncSession = Depends(get_db),
):
    try:
        alerts = await queries.list_alerts(session)
    except SQLAlchemyError:
        db_error_handler()

    zone_by_id = {zone.id: zone.zone_code for zone in await queries.list_zones(session)}

    return [
        {
            "id": alert.id,
            "zone_code": zone_by_id.get(alert.zone_id),
            "alert_level": alert.alert_level,
            "alert_message": alert.alert_message,
            "recommended_action": alert.recommended_action,
            "status": alert.status,
            "channel": alert.channel,
            "created_at": alert.created_at,
            "sent_at": alert.sent_at,
        }
        for alert in alerts
    ]