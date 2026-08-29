"""Async database query helpers for the FastAPI routes."""

import json

from sqlalchemy import select, func, text

from app.db.session import AsyncSession
from app.models.alert import Alert
from app.models.demographics import DemographicVulnerability
from app.models.geographic_zone import GeographicZone
from app.models.risk import RiskPrediction
from app.models.thermal import ThermalIndex
from app.models.weather import (
    WeatherForecast,
    WeatherStation,
)

FORECAST_MODEL_VERSION = "v0.1-forecast"


async def list_stations(session: AsyncSession) -> list[WeatherStation]:
    result = await session.execute(
        select(WeatherStation).order_by(WeatherStation.station_code)
    )
    return list(result.scalars().all())


async def list_zones(session: AsyncSession) -> list[GeographicZone]:
    result = await session.execute(
        select(GeographicZone).order_by(GeographicZone.zone_code)
    )
    return list(result.scalars().all())


async def get_zone_by_code(
    session: AsyncSession,
    zone_code: str,
) -> GeographicZone | None:
    result = await session.execute(
        select(GeographicZone).where(
            GeographicZone.zone_code == zone_code
        )
    )
    return result.scalar_one_or_none()


async def latest_forecast_generation(
    session: AsyncSession,
) -> object | None:
    return await session.scalar(
        select(func.max(RiskPrediction.prediction_generated_at)).where(
            RiskPrediction.model_version == FORECAST_MODEL_VERSION
        )
    )


async def get_vulnerability(
    session: AsyncSession,
    zone_id: int,
) -> DemographicVulnerability | None:
    result = await session.execute(
        select(DemographicVulnerability).where(
            DemographicVulnerability.zone_id == zone_id
        )
    )
    return result.scalar_one_or_none()


async def list_vulnerabilities(
    session: AsyncSession,
) -> list[DemographicVulnerability]:
    result = await session.execute(
        select(DemographicVulnerability).order_by(
            DemographicVulnerability.zone_id
        )
    )
    return list(result.scalars().all())


async def latest_forecast_thermal(
    session: AsyncSession,
) -> list[ThermalIndex]:
    """Return the latest forecast thermal index per calculation type."""

    generation = await session.scalar(
        select(func.max(ThermalIndex.calculated_at)).where(
            ThermalIndex.calculation_type.like("forecast_%")
        )
    )

    if generation is None:
        return []

    result = await session.execute(
        select(ThermalIndex)
        .where(ThermalIndex.calculated_at == generation)
        .order_by(ThermalIndex.calculation_type)
    )
    return list(result.scalars().all())


async def thermal_history(
    session: AsyncSession,
    calculation_type: str | None,
    limit: int,
    offset: int,
) -> list[ThermalIndex]:
    statement = select(ThermalIndex)

    if calculation_type:
        statement = statement.where(
            ThermalIndex.calculation_type == calculation_type
        )

    result = await session.execute(
        statement.order_by(
            ThermalIndex.valid_for.desc()
        )
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def zone_forecast_risks(
    session: AsyncSession,
    zone_id: int,
) -> list[RiskPrediction]:
    result = await session.execute(
        select(RiskPrediction)
        .where(
            RiskPrediction.zone_id == zone_id,
            RiskPrediction.model_version
            == FORECAST_MODEL_VERSION,
        )
        .order_by(RiskPrediction.prediction_for)
    )
    return list(result.scalars().all())


async def zone_current_risk(
    session: AsyncSession,
    zone_id: int,
) -> RiskPrediction | None:
    result = await session.execute(
        select(RiskPrediction)
        .where(RiskPrediction.zone_id == zone_id)
        .order_by(
            RiskPrediction.prediction_for.desc(),
            RiskPrediction.prediction_generated_at.desc(),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_forecast_weather(
    session: AsyncSession,
) -> list[WeatherForecast]:
    generation = await session.scalar(
        select(func.max(WeatherForecast.forecast_generated_at))
    )

    if generation is None:
        return []

    result = await session.execute(
        select(WeatherForecast)
        .where(WeatherForecast.forecast_generated_at == generation)
        .order_by(WeatherForecast.forecast_for)
    )
    return list(result.scalars().all())


async def list_alerts(session: AsyncSession) -> list[Alert]:
    result = await session.execute(
        select(Alert).order_by(
            Alert.created_at.desc(),
            Alert.id.desc(),
        )
    )
    return list(result.scalars().all())


async def risk_zones_geojson(
    session: AsyncSession,
    risk_level: str | None,
    forecast_day: str | None = None,
) -> dict:
    """Build a GeoJSON FeatureCollection of ward risk zones.

    One feature per ward for the latest forecast generation. When
    ``forecast_day`` (ISO date, Asia/Kolkata) is provided the features
    reflect that local day instead of the latest forecast day.
    """

    day_filter = ""

    if forecast_day:
        day_filter = (
            "\n              AND (rp.prediction_for AT TIME ZONE "
            "'Asia/Kolkata')::date::text = :forecast_day"
        )

    statement = text(
        f"""
        WITH latest_generation AS (
            SELECT MAX(prediction_generated_at) AS gen
            FROM risk_predictions
            WHERE model_version = :model_version
        ),
        latest_day_per_zone AS (
            SELECT rp.zone_id, MAX(rp.prediction_for) AS day
            FROM risk_predictions rp
            WHERE rp.model_version = :model_version
              AND rp.prediction_generated_at = (
                  SELECT gen FROM latest_generation
              )
              {day_filter}
            GROUP BY rp.zone_id
        )
        SELECT
            z.zone_code,
            z.zone_name,
            z.population,
            dv.population_density_per_km2,
            dv.vulnerability_score,
            rp.thermal_risk_score,
            rp.overall_risk_level,
            rp.prediction_for AS valid_for,
            ST_AsGeoJSON(z.geometry) AS geometry
        FROM geographic_zones z
        LEFT JOIN demographic_vulnerability dv
            ON dv.zone_id = z.id
        LEFT JOIN latest_day_per_zone ld
            ON ld.zone_id = z.id
        LEFT JOIN risk_predictions rp
            ON rp.zone_id = ld.zone_id
           AND rp.model_version = :model_version
           AND rp.prediction_generated_at = (
               SELECT gen FROM latest_generation
           )
           AND rp.prediction_for = ld.day
        WHERE z.zone_type = 'ward'
        """
    )

    params: dict = {"model_version": FORECAST_MODEL_VERSION}

    if forecast_day:
        params["forecast_day"] = forecast_day

    rows = (await session.execute(statement, params)).all()

    features = []

    for row in rows:

        if risk_level and row.overall_risk_level != risk_level:
            continue

        properties = {
            "zone_code": row.zone_code,
            "zone_name": row.zone_name,
            "population": row.population,
            "population_density": row.population_density_per_km2,
            "vulnerability_score": row.vulnerability_score,
            "thermal_risk_score": row.thermal_risk_score,
            "overall_risk_level": row.overall_risk_level,
            "valid_for": (
                row.valid_for.isoformat()
                if hasattr(row.valid_for, "isoformat")
                else row.valid_for
            ),
        }

        geometry = json.loads(row.geometry)

        features.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": properties,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }