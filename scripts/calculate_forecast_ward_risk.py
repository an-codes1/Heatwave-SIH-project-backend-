import asyncio
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.db.session import AsyncSessionLocal, engine
from app.models.demographics import DemographicVulnerability
from app.models.geographic_zone import GeographicZone
from app.models.risk import RiskPrediction
from app.models.thermal import ThermalIndex
from risk.heat_health_risk import (
    RISK_METHODOLOGY,
    heat_health_risk,
)
from thermal.risk_classification import heat_severity_score


INDIA_TZ = ZoneInfo("Asia/Kolkata")

MODEL_NAME = "heat_health_risk_proxy"
MODEL_VERSION = "v0.1-forecast"

TARGET_DAYS = 5

DAILY_RISK_METHODOLOGY = (
    "Daily ward heat-health risk from the Open-Meteo five-day "
    "forecast. The daily thermal severity is the maximum sun-exposed "
    "UTCI severity across all hours of that local day. Combine with "
    + RISK_METHODOLOGY
)


async def latest_forecast_generation(session) -> datetime:
    return await session.scalar(
        select(func.max(ThermalIndex.calculated_at)).where(
            ThermalIndex.calculation_type
            == "forecast_sun_exposed"
        )
    )


async def main() -> None:
    async with AsyncSessionLocal() as session:

        generation = await latest_forecast_generation(session)

        if generation is None:
            raise RuntimeError(
                "No forecast sun-exposed thermal indices found."
            )

        rows = (
            await session.execute(
                select(
                    ThermalIndex.valid_for,
                    ThermalIndex.utci_c,
                ).where(
                    ThermalIndex.calculation_type
                    == "forecast_sun_exposed",
                    ThermalIndex.calculated_at == generation,
                )
            )
        ).all()

        indices = pd.DataFrame(
            [
                {"valid_for": r.valid_for, "utci_c": r.utci_c}
                for r in rows
            ]
        )

        indices["local_date"] = indices["valid_for"].dt.tz_convert(
            INDIA_TZ
        ).dt.normalize()

        indices["severity"] = indices["utci_c"].map(
            heat_severity_score
        )

        daily = (
            indices.groupby("local_date")["severity"]
            .max()
            .sort_index()
        )

        generation_local_date = generation.astimezone(
            INDIA_TZ
        ).date()

        target_dates = [
            generation_local_date + timedelta(days=offset)
            for offset in range(1, TARGET_DAYS + 1)
        ]

        zones = (
            await session.execute(
                select(GeographicZone)
                .where(GeographicZone.zone_type == "ward")
                .order_by(GeographicZone.zone_code)
            )
        ).scalars().all()

        vulnerabilities = (
            await session.execute(
                select(DemographicVulnerability)
            )
        ).scalars().all()

        vulnerability_by_zone = {
            row.zone_id: row
            for row in vulnerabilities
        }

        inserted = 0
        updated = 0
        skipped_missing_vulnerability = 0
        missing_forecast_day = False

        for target_date in target_dates:

            local_midnight = datetime.combine(
                target_date,
                time.min,
                tzinfo=INDIA_TZ,
            )

            daily_severity = daily.get(
                local_midnight
            )

            if daily_severity is None or pd.isna(daily_severity):
                print(
                    "WARNING: no forecast coverage for local date "
                    f"{target_date}; missing forecast day."
                )
                daily_severity = 0.0
                missing_forecast_day = True

            for zone in zones:

                vuln = vulnerability_by_zone.get(zone.id)

                if vuln is None or vuln.vulnerability_score is None:
                    skipped_missing_vulnerability += 1
                    continue

                score, level = heat_health_risk(
                    thermal_severity=float(daily_severity),
                    vulnerability=vuln.vulnerability_score,
                )

                statement = insert(RiskPrediction).values(
                    zone_id=zone.id,
                    prediction_generated_at=generation,
                    prediction_for=local_midnight,
                    thermal_risk_score=score,
                    mortality_risk_score=None,
                    hospitalization_risk_score=None,
                    overall_risk_level=level.value,
                    model_name=MODEL_NAME,
                    model_version=MODEL_VERSION,
                    confidence_score=None,
                )

                statement = statement.on_conflict_do_update(
                    constraint=(
                        "uq_risk_prediction_zone_generation_target_model"
                    ),
                    set_={
                        "thermal_risk_score": score,
                        "overall_risk_level": level.value,
                    },
                )

                result = await session.execute(statement)

                if result.rowcount == 1:
                    inserted += 1
                else:
                    updated += 1

        await session.commit()
        await engine.dispose()

    print()
    print("Forecast ward/daily risk complete")
    print("---------------------------------")
    print(f"Forecast generation: {generation.isoformat()}")
    print(f"Target days (T+1..T+{TARGET_DAYS}): {target_dates[0]} .. {target_dates[-1]}")
    print(f"Wards: {len(zones)}")
    print(f"Risk predictions inserted: {inserted}")
    print(f"Risk predictions updated: {updated}")
    print(f"Skipped (no vulnerability): {skipped_missing_vulnerability}")
    print(f"Missing forecast coverage: {missing_forecast_day}")
    print(f"Methodology: {DAILY_RISK_METHODOLOGY}")


if __name__ == "__main__":
    asyncio.run(main())