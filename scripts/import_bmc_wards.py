import asyncio
from pathlib import Path

import geopandas as gpd
from geoalchemy2.elements import WKTElement
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.geographic_zone import GeographicZone


INPUT_FILE = Path(
    "data/processed/bmc_wards_clean.geojson"
)

SOURCE_NAME = (
    "BhubaneswarOne - "
    "BMC Ward Boundary, AdministrativeBoundary MapServer Layer 4"
)


def ward_display_name(ward_code: str) -> str:
    number = ward_code.upper().replace("W", "")
    return f"Ward {number}"


async def main() -> None:
    print("Loading cleaned BMC ward data...")

    gdf = gpd.read_file(INPUT_FILE)

    if gdf.crs is None or gdf.crs.to_epsg() != 4326:
        raise RuntimeError(
            "Input ward data must use EPSG:4326."
        )

    inserted = 0
    skipped = 0

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(GeographicZone.zone_code)
        )

        existing_codes = set(
            result.scalars().all()
        )

        for _, row in gdf.iterrows():

            ward_code = str(row["wardno"]).strip()

            if ward_code in existing_codes:
                skipped += 1
                continue

            geometry = row.geometry

            zone = GeographicZone(
                zone_code=ward_code,
                zone_name=ward_display_name(
                    ward_code
                ),
                zone_type="ward",

                # We will import dated population data
                # separately into the demographic table.
                population=None,

                source=SOURCE_NAME,

                geometry=WKTElement(
                    geometry.wkt,
                    srid=4326,
                ),
            )

            session.add(zone)

            existing_codes.add(ward_code)
            inserted += 1

        await session.commit()

    print()
    print("BMC ward import complete.")
    print(f"Inserted wards: {inserted}")
    print(f"Skipped existing wards: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())