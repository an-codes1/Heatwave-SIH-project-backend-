import json
from pathlib import Path


INPUT_FILE = Path(
    "data/raw/bhubaneswar_weather.json"
)


def valid_temperature(value):
    return value is not None and -20 <= value <= 60


def valid_humidity(value):
    return value is not None and 0 <= value <= 100


def valid_wind(value):
    return value is not None and 0 <= value <= 100


def valid_radiation(value):
    return value is not None and 0 <= value <= 1500


def valid_pressure(value):
    return value is not None and 750 <= value <= 1100


VARIABLES = [
    ("temperature_2m", "Temperature", valid_temperature),
    ("relative_humidity_2m", "Humidity", valid_humidity),
    ("wind_speed_10m", "Wind", valid_wind),
    ("shortwave_radiation", "Shortwave radiation", valid_radiation),
    ("direct_radiation", "Direct radiation", valid_radiation),
    ("diffuse_radiation", "Diffuse radiation", valid_radiation),
    ("direct_normal_irradiance", "DNI", valid_radiation),
    ("surface_pressure", "Pressure", valid_pressure),
]


def main() -> None:
    data = json.loads(
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    hourly = data["hourly"]

    times = hourly["time"]

    missing_keys = [
        key for key, _, _ in VARIABLES
        if key not in hourly
    ]

    if missing_keys:
        raise RuntimeError(
            "The weather file is missing variables: "
            + ", ".join(missing_keys)
        )

    arrays = [hourly[key] for key, _, _ in VARIABLES]

    lengths = {len(times), *(len(array) for array in arrays)}

    if len(lengths) != 1:
        raise RuntimeError(
            "Weather arrays have different lengths."
        )

    missing_counts = {key: 0 for key, _, _ in VARIABLES}

    valid = 0
    invalid = 0

    invalid_rows = []

    for index in range(len(times)):

        row_valid = True

        for key, _, check in VARIABLES:
            value = hourly[key][index]

            if value is None:
                row_valid = False
                missing_counts[key] += 1
                continue

            if not check(value):
                row_valid = False

        if row_valid:
            valid += 1
        else:
            invalid += 1
            invalid_rows.append(
                times[index]
            )

    print("Weather validation report")
    print("-------------------------")
    print(f"Total records: {len(times)}")
    print(f"Valid records: {valid}")
    print(f"Invalid records: {invalid}")

    print()
    print("Missing values:")
    for key, label, _ in VARIABLES:
        print(f"{label} missing: {missing_counts[key]}")

    print()
    print("Value ranges (non-null values only):")

    for key, label, _ in VARIABLES:
        values = [
            value for value in hourly[key]
            if value is not None
        ]

        if not values:
            print(f"{label}: no values available")
            continue

        print(f"{label}: {min(values)} to {max(values)}")

    if invalid_rows:
        print()
        print("Invalid timestamps:")
        print(invalid_rows)


if __name__ == "__main__":
    main()