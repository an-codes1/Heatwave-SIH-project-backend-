import asyncio
from datetime import datetime, timezone
from math import isnan

import numpy as np
from pythermalcomfort.models import utci
from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.models.thermal import ThermalIndex
from app.models.weather import WeatherObservation
from thermal.mrt import Scenario, methodology_text, solar_delta_mrt
from thermal.solar_position import solar_positions


LOWER_WIND_APPLICABILITY = 0.5

CALCULATION_TYPES = {
    Scenario.REFERENCE_SHADE: "observed_reference_shade",
    Scenario.SUN_EXPOSED: "observed_sun_exposed",
}

BATCH_SIZE = 10_000


def vector_utci(
    air_temperature,
    mean_radiant_temperature,
    wind_speed,
    relative_humidity,
):
    """Vectorized UTCI calculation; invalid inputs become NaN."""

    result = utci(
        tdb=air_temperature,
        tr=mean_radiant_temperature,
        v=wind_speed,
        rh=relative_humidity,
        units="SI",
        limit_inputs=True,
        round_output=False,
    )

    return (
        np.asarray(result.utci, dtype=float),
        np.asarray(result.stress_category, dtype=object),
    )


async def main() -> None:
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:

        rows = (
            await session.execute(
                select(
                    WeatherObservation.station_id,
                    WeatherObservation.observed_at,
                    WeatherObservation.air_temperature_c,
                    WeatherObservation.relative_humidity_pct,
                    WeatherObservation.wind_speed_ms,
                    WeatherObservation.direct_normal_irradiance_wm2,
                ).order_by(WeatherObservation.observed_at)
            )
        ).all()

        station_ids = np.array(
            [r.station_id for r in rows],
            dtype=np.int64,
        )
        timestamps = [r.observed_at for r in rows]
        temperatures = np.array(
            [r.air_temperature_c for r in rows],
            dtype=float,
        )
        humidities = np.array(
            [r.relative_humidity_pct for r in rows],
            dtype=float,
        )
        winds = np.array(
            [r.wind_speed_ms for r in rows],
            dtype=float,
        )
        dni = np.array(
            [r.direct_normal_irradiance_wm2 for r in rows],
            dtype=float,
        )

        count = len(rows)

        if count == 0:
            print("No weather observations found.")
            return

        print("Computing solar positions...")

        elevations, _ = solar_positions(timestamps)

        print("Estimating sun-exposed radiant load...")

        deltas = np.array(
            [
                solar_delta_mrt(
                    dni[index],
                    elevations[index],
                )
                for index in range(count)
            ],
            dtype=float,
        )

        reference_mrt = temperatures
        sun_exposed_mrt = temperatures + deltas

        wind_used = np.maximum(
            winds,
            LOWER_WIND_APPLICABILITY,
        )

        wind_lower_adjustments = int(
            np.sum(winds < LOWER_WIND_APPLICABILITY)
        )

        print("Calculating UTCI (reference/shade) ...")
        shade_utci, shade_categories = vector_utci(
            temperatures,
            reference_mrt,
            wind_used,
            humidities,
        )

        print("Calculating UTCI (sun-exposed) ...")
        sun_utci, sun_categories = vector_utci(
            temperatures,
            sun_exposed_mrt,
            wind_used,
            humidities,
        )

        print("Checking for already-existing thermal records...")

        existing_result = await session.execute(
            select(
                ThermalIndex.station_id,
                ThermalIndex.valid_for,
                ThermalIndex.calculation_type,
            )
        )

        existing_keys = set(
            (
                row.station_id,
                row.valid_for,
                row.calculation_type,
            )
            for row in existing_result.all()
        )

        scenario_config = [
            (
                Scenario.REFERENCE_SHADE,
                CALCULATION_TYPES[Scenario.REFERENCE_SHADE],
                shade_utci,
                shade_categories,
            ),
            (
                Scenario.SUN_EXPOSED,
                CALCULATION_TYPES[Scenario.SUN_EXPOSED],
                sun_utci,
                sun_categories,
            ),
        ]

        inserted = 0
        already_existing = 0
        invalid = 0
        reference_count = 0
        sun_count = 0

        pending = []

        for scenario, calc_type, utci_values, categories in scenario_config:

            for index in range(count):

                value = float(utci_values[index])

                if isnan(value):
                    invalid += 1
                    continue

                key = (
                    int(station_ids[index]),
                    timestamps[index],
                    calc_type,
                )

                if key in existing_keys:
                    already_existing += 1
                    continue

                if scenario is Scenario.REFERENCE_SHADE:
                    reference_count += 1
                else:
                    sun_count += 1

                pending.append(
                    ThermalIndex(
                        station_id=int(station_ids[index]),
                        calculated_at=now,
                        valid_for=timestamps[index],
                        utci_c=value,
                        thermal_risk_level=str(
                            categories[index]
                        ),
                        calculation_type=calc_type,
                        methodology=methodology_text(
                            scenario,
                            "Observed",
                        ),
                    )
                )

                if len(pending) >= BATCH_SIZE:
                    session.add_all(pending)
                    pending = []
                    await session.commit()

        if pending:
            session.add_all(pending)
            pending = []

        await session.commit()

        inserted = reference_count + sun_count

        await engine.dispose()

    print()
    print("Historical thermal index calculation complete")
    print("---------------------------------------------")
    print(f"Weather observations: {count}")
    print(f"Reference UTCI calculated: {reference_count}")
    print(f"Sun UTCI calculated: {sun_count}")
    print(f"Wind lower-bound adjustments: {wind_lower_adjustments}")
    print(f"Invalid/skipped calculations: {invalid}")
    print(f"Thermal records inserted: {inserted}")
    print(f"Already-existing records: {already_existing}")


if __name__ == "__main__":
    asyncio.run(main())