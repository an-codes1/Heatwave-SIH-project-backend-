from pathlib import Path

import geopandas as gpd
from shapely import make_valid
from shapely.geometry import MultiPolygon, Polygon


INPUT_FILE = Path("data/raw/bmc_wards.geojson")
OUTPUT_FILE = Path("data/processed/bmc_wards_clean.geojson")


def to_multipolygon(geometry):
    if geometry is None:
        return None

    if isinstance(geometry, MultiPolygon):
        return geometry

    if isinstance(geometry, Polygon):
        return MultiPolygon([geometry])

    return geometry


def main() -> None:
    print("Loading BMC ward GIS data...")

    gdf = gpd.read_file(INPUT_FILE)

    print(f"Features loaded: {len(gdf)}")
    print(f"Source CRS: {gdf.crs}")

    required_columns = {
        "wardno",
        "geometry",
    }

    missing_columns = required_columns - set(gdf.columns)

    if missing_columns:
        raise RuntimeError(
            f"Required columns missing: {sorted(missing_columns)}"
        )

    # Ensure WGS84 / latitude-longitude coordinates.
    if gdf.crs is None:
        raise RuntimeError("The GIS file has no CRS information.")

    if gdf.crs.to_epsg() != 4326:
        print("Reprojecting to EPSG:4326...")
        gdf = gdf.to_crs(epsg=4326)

    # Check ward identifiers.
    if gdf["wardno"].isna().any():
        raise RuntimeError("One or more wards have no ward number.")

    duplicate_wards = gdf[gdf["wardno"].duplicated(keep=False)]

    if not duplicate_wards.empty:
        raise RuntimeError(
            "Duplicate ward numbers found:\n"
            + str(duplicate_wards["wardno"].tolist())
        )

    expected_wards = {f"W{i}" for i in range(1, 68)}
    actual_wards = set(gdf["wardno"].astype(str))

    missing_wards = sorted(expected_wards - actual_wards)
    unexpected_wards = sorted(actual_wards - expected_wards)

    print(f"Unique wards: {len(actual_wards)}")
    print(f"Missing wards: {missing_wards}")
    print(f"Unexpected wards: {unexpected_wards}")

    if missing_wards or unexpected_wards:
        raise RuntimeError(
            "Ward identifiers do not match expected W1-W67."
        )

    # Geometry validation.
    invalid_before = (~gdf.geometry.is_valid).sum()

    print(f"Invalid geometries before repair: {invalid_before}")

    if invalid_before:
        gdf["geometry"] = gdf.geometry.apply(make_valid)

    invalid_after = (~gdf.geometry.is_valid).sum()

    print(f"Invalid geometries after repair: {invalid_after}")

    if invalid_after:
        raise RuntimeError(
            "Some geometries remain invalid after repair."
        )

    # Our database column expects MULTIPOLYGON.
    gdf["geometry"] = gdf.geometry.apply(to_multipolygon)

    geometry_types = sorted(gdf.geometry.geom_type.unique())

    print(f"Geometry types after conversion: {geometry_types}")

    if geometry_types != ["MultiPolygon"]:
        raise RuntimeError(
            "All ward geometries must be MultiPolygon."
        )

    # Basic geographic sanity check.
    bounds = gdf.total_bounds

    print()
    print("Dataset bounds:")
    print(f"Minimum longitude: {bounds[0]}")
    print(f"Minimum latitude:  {bounds[1]}")
    print(f"Maximum longitude: {bounds[2]}")
    print(f"Maximum latitude:  {bounds[3]}")

    # Show useful source attributes without interpreting them yet.
    preview_columns = [
        column
        for column in [
            "wardno",
            "municipalz",
            "nameofthec",
            "totalwardp",
        ]
        if column in gdf.columns
    ]

    print()
    print("First five source records:")
    print(gdf[preview_columns].head().to_string(index=False))

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    gdf.to_file(
        OUTPUT_FILE,
        driver="GeoJSON",
    )

    print()
    print("Validation successful.")
    print(f"Clean GIS file saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()