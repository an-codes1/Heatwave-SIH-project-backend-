import json
from pathlib import Path


WARD_FILE = Path("data/raw/bmc_wards.geojson")


def main() -> None:
    data = json.loads(
        WARD_FILE.read_text(encoding="utf-8")
    )

    features = data["features"]

    print(f"Feature count: {len(features)}")
    print()

    ward_numbers = []

    for feature in features:
        properties = feature.get("properties", {})
        ward_number = properties.get("wardno")

        if ward_number is not None:
            ward_numbers.append(str(ward_number))

    print(f"Ward numbers found: {len(ward_numbers)}")
    print("Ward values:")
    print(ward_numbers)

    print()

    if features:
        print("Available property fields:")
        print(
            list(features[0].get("properties", {}).keys())
        )

        print()

        print("First geometry type:")
        print(
            features[0]
            .get("geometry", {})
            .get("type")
        )


if __name__ == "__main__":
    main()