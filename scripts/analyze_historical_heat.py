import asyncio
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.thermal import ThermalIndex
from thermal.risk_classification import utci_stress_category

OUTPUT_FILE = Path(
    "data/processed/thermal_analysis.json"
)


def annual_stats(series: pd.DataFrame) -> list:
    """Annual maximum UTCI and annual heat-stress hour counts."""

    by_year = series.groupby(series["valid_for"].dt.year)

    result = []

    for year, group in by_year:
        result.append(
            {
                "year": int(year),
                "annual_max_utci_c": float(
                    group["utci_c"].max()
                ),
                "annual_max_utci_at": group.loc[
                    group["utci_c"].idxmax(),
                    "valid_for",
                ].isoformat(),
                "heat_stress_hours": int(
                    (
                        group["category"]
                        .isin(
                            [
                                "moderate heat stress",
                                "strong heat stress",
                                "very strong heat stress",
                                "extreme heat stress",
                            ]
                        )
                    ).sum()
                ),
            }
        )

    return result


async def main() -> None:
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(
                select(
                    ThermalIndex.calculation_type,
                    ThermalIndex.valid_for,
                    ThermalIndex.utci_c,
                )
            )
        ).all()

    data = pd.DataFrame(
        [
            {
                "calculation_type": r.calculation_type,
                "valid_for": r.valid_for,
                "utci_c": r.utci_c,
            }
            for r in rows
        ]
    )

    data["valid_for"] = data["valid_for"].dt.tz_convert(
        "Asia/Kolkata"
    )

    if data.empty:
        raise RuntimeError("No thermal indices found.")
    else:
        print("NOTE: analysis includes backfilled historical")
        print("      observed thermal indices only.")

    data["category"] = data["utci_c"].map(
        utci_stress_category
    )

    categories = [
        "no thermal stress",
        "moderate heat stress",
        "strong heat stress",
        "very strong heat stress",
        "extreme heat stress",
    ]

    summary = {}

    for calc_type, group in data.groupby("calculation_type"):

        maximum = group.loc[group["utci_c"].idxmax()]

        summary[calc_type] = {
            "max_utci_c": float(maximum["utci_c"]),
            "max_utci_at": maximum["valid_for"].isoformat(),
            "annual": annual_stats(group),
            "category_hours": {
                category: int(
                    (group["category"] == category).sum()
                )
                for category in categories
            },
            "top_20_utci_timestamps": [
                {
                    "utci_c": float(row["utci_c"]),
                    "at": row["valid_for"].isoformat(),
                }
                for _, row in group.nlargest(20, "utci_c")[
                    ["valid_for", "utci_c"]
                ].iterrows()
            ],
        }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print("Historical heat analysis")
    print("------------------------")

    for calc_type, stats in summary.items():
        print()
        print(f"[{calc_type}]")
        print(f"Maximum UTCI: {stats['max_utci_c']:.2f} °C")
        print(f"  at: {stats['max_utci_at']}")
        for category in categories:
            print(
                f"  {category}: "
                f"{stats['category_hours'][category]} hours"
            )

    print()
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())