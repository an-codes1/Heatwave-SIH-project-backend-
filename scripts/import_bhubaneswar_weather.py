import asyncio
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.weather import (
    WeatherObservation,
    WeatherStation,
)


INPUT_FILE = Path(
    "data/raw/bhubaneswar_weather.json"
)

STATION_CODE = "OPENMETEO_BHUBANESWAR_ERA5"

SOURCE_NAME = "Open-Meteo ERA5 reanalysis"

INDIA_TZ = ZoneInfo("Asia/Kolkata")


def valid_row(
    temperature,
    humidity,
    wind,
    radiation,
    direct_radiation,
    diffuse_radiation,
    dni,
    pressure,
) -> bool:
    """Check whether all required weather values are usable."""

    return all(
        [
            temperature is not None
            and -20 <= temperature <= 60,

            humidity is not None
            and 0 <= humidity <= 100,

            wind is not None
            and 0 <= wind <= 100,

            radiation is not None
            and 0 <= radiation <= 1500,

            direct_radiation is not None
            and 0 <= direct_radiation <= 1500,

            diffuse_radiation is not None
            and 0 <= diffuse_radiation <= 1500,

            dni is not None
            and 0 <= dni <= 1500,

            pressure is not None
            and 750 <= pressure <= 1100,
        ]
    )


async def get_or_create_station(
    session,
    latitude: float,
    longitude: float,
) -> WeatherStation:
    """Get the ERA5 Bhubaneswar grid point or create it."""

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
        station_name=(
            "Bhubaneswar Open-Meteo ERA5 Grid Point"
        ),
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
    print("Loading downloaded Bhubaneswar weather...")

    data = json.loads(
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    latitude = float(data["latitude"])
    longitude = float(data["longitude"])

    hourly = data["hourly"]

    times = hourly["time"]
    temperatures = hourly["temperature_2m"]
    humidities = hourly["relative_humidity_2m"]
    winds = hourly["wind_speed_10m"]
    radiation = hourly["shortwave_radiation"]
    direct_radiation = hourly["direct_radiation"]
    diffuse_radiation = hourly["diffuse_radiation"]
    dni = hourly["direct_normal_irradiance"]
    pressures = hourly["surface_pressure"]

    inserted = 0
    skipped_duplicates = 0
    rejected = 0

    async with AsyncSessionLocal() as session:

        station = await get_or_create_station(
            session=session,
            latitude=latitude,
            longitude=longitude,
        )

        existing_result = await session.execute(
            select(
                WeatherObservation.observed_at
            ).where(
                WeatherObservation.station_id
                == station.id
            )
        )

        existing_times = set(
            existing_result.scalars().all()
        )

        for index, time_string in enumerate(times):

            timestamp = datetime.fromisoformat(
                time_string
            ).replace(
                tzinfo=INDIA_TZ
            )

            temperature = temperatures[index]
            humidity = humidities[index]
            wind = winds[index]
            solar = radiation[index]
            direct = direct_radiation[index]
            diffuse = diffuse_radiation[index]
            dni_value = dni[index]
            pressure = pressures[index]

            if not valid_row(
                temperature,
                humidity,
                wind,
                solar,
                direct,
                diffuse,
                dni_value,
                pressure,
            ):
                rejected += 1
                continue

            if timestamp in existing_times:
                skipped_duplicates += 1
                continue

            observation = WeatherObservation(
                station_id=station.id,
                observed_at=timestamp,
                air_temperature_c=temperature,
                relative_humidity_pct=humidity,
                wind_speed_ms=wind,
                solar_radiation_wm2=solar,
                direct_radiation_wm2=direct,
                diffuse_radiation_wm2=diffuse,
                direct_normal_irradiance_wm2=dni_value,
                atmospheric_pressure_hpa=pressure,
                source=SOURCE_NAME,
            )

            session.add(observation)

            existing_times.add(timestamp)

            inserted += 1

        await session.commit()

    print()
    print("Weather import complete")
    print("-----------------------")
    print(f"Inserted: {inserted}")
    print(
        f"Duplicates skipped: "
        f"{skipped_duplicates}"
    )
    print(f"Rejected: {rejected}")


if __name__ == "__main__":
    asyncio.run(main())