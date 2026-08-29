import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.models.weather import (
    WeatherForecast,
    WeatherStation,
)


INPUT_FILE = Path(
    "data/raw/bhubaneswar_forecast.json"
)

STATION_CODE = "OPENMETEO_BHUBANESWAR_ERA5"

SOURCE_NAME = "Open-Meteo Forecast API"

INDIA_TZ = ZoneInfo("Asia/Kolkata")

UTC = timezone.utc


def valid_value(value, lower, upper):
    return value is not None and lower <= value <= upper


async def get_or_create_station(
    session,
    latitude: float,
    longitude: float,
) -> WeatherStation:
    result = await session.execute(
        select(WeatherStation).where(
            WeatherStation.station_code
            == STATION_CODE
        )
    )

    station = result.scalar_one_or_none()

    if station is not None:
        return station

    station = WeatherStation(
        station_code=STATION_CODE,
        station_name="Bhubaneswar Open-Meteo ERA5 Grid Point",
        latitude=latitude,
        longitude=longitude,
        location=WKTElement(
            f"POINT({longitude} {latitude})",
            srid=4326,
        ),
        source=SOURCE_NAME,
        is_active=True,
    )

    session.add(station)
    await session.flush()
    return station


async def main() -> None:
    print("Loading downloaded Bhubaneswar forecast...")

    data = json.loads(
        INPUT_FILE.read_text(encoding="utf-8")
    )

    latitude = float(data["latitude"])
    longitude = float(data["longitude"])

    generated_at = datetime.fromisoformat(
        data["_generated_at"]
    )

    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=UTC)

    hourly = data["hourly"]

    times = hourly["time"]
    temperatures = hourly["temperature_2m"]
    humidities = hourly["relative_humidity_2m"]
    winds = hourly["wind_speed_10m"]
    radiation = hourly["shortwave_radiation"]
    direct = hourly["direct_radiation"]
    diffuse = hourly["diffuse_radiation"]
    dni = hourly["direct_normal_irradiance"]
    pressures = hourly["surface_pressure"]

    inserted = 0
    skipped_duplicates = 0
    rejected = 0

    async with AsyncSessionLocal() as session:

        station = await get_or_create_station(
            session,
            latitude,
            longitude,
        )

        existing_result = await session.execute(
            select(WeatherForecast.forecast_for).where(
                WeatherForecast.station_id
                == station.id,
                WeatherForecast.forecast_generated_at
                == generated_at,
            )
        )

        existing_times = set(
            existing_result.scalars().all()
        )

        for index, time_string in enumerate(times):

            forecast_for = datetime.fromisoformat(
                time_string
            ).replace(
                tzinfo=INDIA_TZ
            )

            temperature = temperatures[index]
            humidity = humidities[index]
            wind = winds[index]
            solar = radiation[index]
            direct_value = direct[index]
            diffuse_value = diffuse[index]
            dni_value = dni[index]
            pressure = pressures[index]

            valid = all(
                [
                    valid_value(temperature, -20, 60),
                    valid_value(humidity, 0, 100),
                    valid_value(wind, 0, 100),
                    valid_value(solar, 0, 1500),
                    valid_value(direct_value, 0, 1500),
                    valid_value(diffuse_value, 0, 1500),
                    valid_value(dni_value, 0, 1500),
                    valid_value(pressure, 750, 1100),
                ]
            )

            if not valid:
                rejected += 1
                continue

            if forecast_for in existing_times:
                skipped_duplicates += 1
                continue

            session.add(
                WeatherForecast(
                    station_id=station.id,
                    forecast_generated_at=generated_at,
                    forecast_for=forecast_for,
                    air_temperature_c=temperature,
                    relative_humidity_pct=humidity,
                    wind_speed_ms=wind,
                    solar_radiation_wm2=solar,
                    direct_radiation_wm2=direct_value,
                    diffuse_radiation_wm2=diffuse_value,
                    direct_normal_irradiance_wm2=dni_value,
                    atmospheric_pressure_hpa=pressure,
                    source=SOURCE_NAME,
                )
            )

            existing_times.add(forecast_for)

            inserted += 1

        await session.commit()
        await engine.dispose()

    print()
    print("Forecast import complete")
    print("------------------------")
    print(f"Forecast generated at (UTC): {generated_at.isoformat()}")
    print(f"Inserted: {inserted}")
    print(f"Duplicates skipped: {skipped_duplicates}")
    print(f"Rejected: {rejected}")


if __name__ == "__main__":
    asyncio.run(main())