import json
from pathlib import Path

import httpx


BMC_WARD_QUERY_URL = (
    "https://bhubaneswarone.in/arcgis/rest/services/"
    "BhubaneswarOne/AdministrativeBoundary/MapServer/4/query"
)

OUTPUT_FILE = Path("data/raw/bmc_wards.geojson")


def main() -> None:
    print("Downloading real BMC ward boundaries...")

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        response = client.get(
            BMC_WARD_QUERY_URL,
            params=params,
        )

        response.raise_for_status()

    data = response.json()

    if data.get("type") != "FeatureCollection":
        raise RuntimeError(
            "The server response is not a GeoJSON FeatureCollection."
        )

    features = data.get("features", [])

    if not features:
        raise RuntimeError(
            "The BMC GIS service returned zero ward features."
        )

    OUTPUT_FILE.write_text(
        json.dumps(data, indent=2),
        encoding="utf-8",
    )

    print()
    print("Download successful!")
    print(f"Features received: {len(features)}")
    print(f"Saved to: {OUTPUT_FILE}")

    if len(features) == 67:
        print("Ward count check: PASS (67 wards)")
    else:
        print(
            "Ward count check: REVIEW "
            f"(expected 67, received {len(features)})"
        )


if __name__ == "__main__":
    main()