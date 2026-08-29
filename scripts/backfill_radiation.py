import argparse
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import select, update

from app.db.session import AsyncSessionLocal
from app.models.weather import (
    WeatherObservation,
    WeatherStation,
)
from scripts.download_bhubaneswar_weather import (
    ARCHIVE_URL,
    find_bhubaneswar,
)


STATION_CODE = "OPENMETEO_BHUBANESWAR_ERA5"

INDIA_TZ = ZoneInfo("Asia/Kolkata")

UTC = timezone.utc

RADIATION_VARIABLES = [
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
]

RADIATION_COLUMNS = [
    WeatherObservation.direct_radiation_wm2,
    WeatherObservation.diffuse_radiation_wm2,
    WeatherObservation.direct_normal_irradiance_wm2,
]


def download_radiation(
    client: httpx.Client,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict:
    """Download ERA5 radiation data for the given local date range."""

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(RADIATION_VARIABLES),
        "timezone": "Asia/Kolkata",
        "models": "era5",
    }

    response = client.get(
        ARCHIVE_URL,
        params=params,
    )
    response.raise_for_status()

    return response.json()


def to_utc(time_string: str) -> datetime:
    """Convert an Open-Meteo local timestamp to an aware UTC datetime.

    Open-Meteo returns naive local timestamps in the requested
    timezone (Asia/Kolkata). We frame them exactly like the normal
    importer does, then normalize to UTC so they can be matched
    against the database's timezone-aware values.
    """

    local_time = datetime.fromisoformat(
        time_string
    ).replace(
        tzinfo=INDIA_TZ
    )

    return local_time.astimezone(UTC)


def valid_radiation_value(value) -> bool:
    return value is not None and value >= 0


async def get_station(session) -> WeatherStation | None:
    result = await session.execute(
        select(WeatherStation).where(
            WeatherStation.station_code
            == STATION_CODE
        )
    )
    return result.scalar_one_or_none()


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Safely backfill solar radiation components "
            "into existing weather observations."
        )
    )

    parser.add_argument(
        "--start",
        required=True,
        help="Start date in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--end",
        required=True,
        help="End date in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Download, match and validate without changing the database.",
    )

    args = parser.parse_args()

    print("Finding Bhubaneswar coordinates...")

    with httpx.Client(
        timeout=60.0,
        follow_redirects=True,
    ) as client:

        latitude, longitude = find_bhubaneswar(client)

        print()
        print("Downloading ERA5 radiation data...")

        payload = download_radiation(
            client=client,
            latitude=latitude,
            longitude=longitude,
            start_date=args.start,
            end_date=args.end,
        )

    hourly = payload.get("hourly", {})

    times = hourly.get("time", [])

    if not times:
        raise RuntimeError(
            "The weather API returned no hourly data."
        )

    source_arrays = {
        variable: hourly[variable]
        for variable in RADIATION_VARIABLES
    }

    downloaded = len(times)

    matched = 0
    updated = 0
    already_populated = 0
    missing_matches = 0
    rejected = 0

    async with AsyncSessionLocal() as session:

        station = await get_station(session)

        if station is None:
            raise RuntimeError(
                f"Station {STATION_CODE} was not found in the database."
            )

        result = await session.execute(
            select(
                WeatherObservation.id,
                WeatherObservation.observed_at,
                *RADIATION_COLUMNS,
            ).where(
                WeatherObservation.station_id
                == station.id
            )
        )

        existing_rows = {}

        for row in result.all():
            row_time = row.observed_at

            if row_time.tzinfo is None:
                row_time = row_time.replace(
                    tzinfo=UTC
                )
            else:
                row_time = row_time.astimezone(UTC)

            existing_rows[row_time] = row

        for index, time_string in enumerate(times):

            row_time = to_utc(time_string)

            existing = existing_rows.get(row_time)

            if existing is None:
                missing_matches += 1
                continue

            matched += 1

            source_values = [
                source_arrays[variable][index]
                for variable in RADIATION_VARIABLES
            ]

            if not all(
                valid_radiation_value(value)
                for value in source_values
            ):
                rejected += 1
                continue

            row_values = [
                existing.direct_radiation_wm2,
                existing.diffuse_radiation_wm2,
                existing.direct_normal_irradiance_wm2,
            ]

            if all(
                value is not None
                for value in row_values
            ):
                already_populated += 1
                continue

            if not args.dry_run:
                await session.execute(
                    update(WeatherObservation)
                    .where(
                        WeatherObservation.id
                        == existing.id
                    )
                    .values(
                        direct_radiation_wm2=source_values[0],
                        diffuse_radiation_wm2=source_values[1],
                        direct_normal_irradiance_wm2=source_values[2],
                    )
                    .execution_options(
                        synchronize_session=False
                    )
                )

            updated += 1

        if not args.dry_run:
            await session.commit()

    mode = "Dry run" if args.dry_run else "Backfill complete"

    print()
    print(f"{mode}")
    print("-----------------------------")
    print(f"Downloaded source rows: {downloaded}")
    print(f"Matched database rows: {matched}")

    if args.dry_run:
        print(f"Would update: {updated}")
    else:
        print(f"Updated: {updated}")

    print(f"Already populated: {already_populated}")
    print(f"Missing DB matches: {missing_matches}")
    print(f"Rejected source rows: {rejected}")


if __name__ == "__main__":
    asyncio.run(main())