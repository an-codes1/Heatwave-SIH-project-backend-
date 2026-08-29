import asyncio
from datetime import datetime
from math import isnan

import numpy as np
from pythermalcomfort.models import utci
from sqlalchemy import func, select

from app.db.session import AsyncSessionLocal, engine
from app.models.thermal import ThermalIndex
from app.models.weather import WeatherForecast
from thermal.mrt import Scenario, methodology_text, solar_delta_mrt
from thermal.solar_position import solar_positions


LOWER_WIND_APPLICABILITY = 0.5

CALCULATION_TYPES = {
    Scenario.REFERENCE_SHADE: "forecast_reference_shade",
    Scenario.SUN_EXPOSED: "forecast_sun_exposed",
}

BATCH_SIZE = 5_000


async def main() -> None:
    async with AsyncSessionLocal() as session:

        latest_generation = await session.scalar(
            select(func.max(WeatherForecast.forecast_generated_at))
        )

        if latest_generation is None:
            raise RuntimeError(
                "No weather forecasts found."
            )

        rows = (
            await session.execute(
                select(
                    WeatherForecast.station_id,
                    WeatherForecast.forecast_for,
                    WeatherForecast.air_temperature_c,
                    WeatherForecast.relative_humidity_pct,
                    WeatherForecast.wind_speed_ms,
                    WeatherForecast.direct_normal_irradiance_wm2,
                ).where(
                    WeatherForecast.forecast_generated_at
                    == latest_generation
                ).order_by(WeatherForecast.forecast_for)
            )
        ).all()

        station_ids = np.array(
            [r.station_id for r in rows], dtype=np.int64
        )
        timestamps = [r.forecast_for for r in rows]
        temperatures = np.array(
            [r.air_temperature_c for r in rows], dtype=float
        )
        humidities = np.array(
            [r.relative_humidity_pct for r in rows], dtype=float
        )
        winds = np.array(
            [r.wind_speed_ms for r in rows], dtype=float
        )
        dni = np.array(
            [r.direct_normal_irradiance_wm2 for r in rows],
            dtype=float,
        )

        count = len(rows)

        elevations, _ = solar_positions(timestamps)

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

        wind_used = np.maximum(
            winds,
            LOWER_WIND_APPLICABILITY,
        )

        def vector_utci(mean_radiant_temperature):
            result = utci(
                tdb=temperatures,
                tr=mean_radiant_temperature,
                v=wind_used,
                rh=humidities,
                units="SI",
                limit_inputs=True,
                round_output=False,
            )
            return (
                np.asarray(result.utci, dtype=float),
                np.asarray(result.stress_category, dtype=object),
            )

        shade_utci, shade_categories = vector_utci(temperatures)
        sun_utci, sun_categories = vector_utci(temperatures + deltas)

        existing_result = await session.execute(
            select(
                ThermalIndex.station_id,
                ThermalIndex.valid_for,
                ThermalIndex.calculation_type,
            ).where(
                ThermalIndex.calculation_type.in_(
                    [
                        CALCULATION_TYPES[Scenario.REFERENCE_SHADE],
                        CALCULATION_TYPES[Scenario.SUN_EXPOSED],
                    ]
                )
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

        scenario_data = [
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
        wind_lower_adjustments = int(
            np.sum(winds < LOWER_WIND_APPLICABILITY)
        )

        pending = []

        for scenario, calc_type, utci_values, categories in scenario_data:

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

                pending.append(
                    ThermalIndex(
                        station_id=int(station_ids[index]),
                        calculated_at=latest_generation,
                        valid_for=timestamps[index],
                        utci_c=value,
                        thermal_risk_level=str(categories[index]),
                        calculation_type=calc_type,
                        methodology=methodology_text(
                            scenario,
                            "Forecast",
                        ),
                    )
                )

                inserted += 1

                if len(pending) >= BATCH_SIZE:
                    session.add_all(pending)
                    pending = []
                    await session.commit()

        if pending:
            session.add_all(pending)

        await session.commit()
        await engine.dispose()

    print()
    print("Forecast thermal index calculation complete")
    print("--------------------------------------------")
    print(f"Forecast generation: {latest_generation.isoformat()}")
    print(f"Forecast hours processed: {count}")
    print(f"Thermal records inserted: {inserted}")
    print(f"Already-existing records: {already_existing}")
    print(f"Invalid/skipped calculations: {invalid}")
    print(f"Wind lower-bound adjustments: {wind_lower_adjustments}")


if __name__ == "__main__":
    asyncio.run(main())