import argparse
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
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

MODEL_NAME = "heat_health_risk_proxy"
MODEL_VERSION = "v0.1"

REFERENCE_EVENT = "2023-06-16T12:00:00+05:30"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--valid-for",
        default=REFERENCE_EVENT,
        help=(
            "ISO datetime of the observed thermal event to score "
            "(default: the 2020-2025 historical local UTCI maximum)."
        ),
    )
    args = parser.parse_args()

    valid_for = datetime.fromisoformat(args.valid_for)

    async with AsyncSessionLocal() as session:

        thermal = await session.execute(
            select(ThermalIndex).where(
                ThermalIndex.calculation_type
                == "observed_sun_exposed",
                ThermalIndex.valid_for == valid_for,
            )
        )
        thermal_row = thermal.scalars().first()

        if thermal_row is None:
            raise RuntimeError(
                "No observed sun-exposed thermal index found for "
                f"{args.valid_for}"
            )

        from thermal.risk_classification import heat_severity_score

        thermal_severity = heat_severity_score(thermal_row.utci_c)

        zones = (
            await session.execute(
                select(GeographicZone)
                .where(
                    GeographicZone.zone_type == "ward"
                )
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

        generated_at = datetime.now(timezone.utc)

        inserted = 0
        updated = 0

        for zone in zones:

            vuln = vulnerability_by_zone.get(zone.id)

            if vuln is None or vuln.vulnerability_score is None:
                print(
                    f"WARNING: {zone.zone_code} has no vulnerability "
                    "score; skipping"
                )
                continue

            score, level = heat_health_risk(
                thermal_severity=thermal_severity,
                vulnerability=vuln.vulnerability_score,
            )

            statement = insert(RiskPrediction).values(
                zone_id=zone.id,
                prediction_generated_at=generated_at,
                prediction_for=valid_for,
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
    print("Ward heat-health risk proxy complete")
    print("------------------------------------")
    print(f"Thermal event (valid_for): {args.valid_for}")
    print(f"Sun-exposed UTCI: {thermal_row.utci_c:.2f} °C")
    print(f"Thermal severity (0-100): {thermal_severity:.2f}")
    print(f"Risk predictions inserted: {inserted}")
    print(f"Risk predictions updated: {updated}")
    print(f"Methodology: {RISK_METHODOLOGY}")


if __name__ == "__main__":
    asyncio.run(main())