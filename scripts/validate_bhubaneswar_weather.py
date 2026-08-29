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


def main() -> None:
    data = json.loads(
        INPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    hourly = data["hourly"]

    times = hourly["time"]
    temperatures = hourly["temperature_2m"]
    humidities = hourly["relative_humidity_2m"]
    winds = hourly["wind_speed_10m"]
    radiation = hourly["shortwave_radiation"]
    pressures = hourly["surface_pressure"]

    lengths = {
        len(times),
        len(temperatures),
        len(humidities),
        len(winds),
        len(radiation),
        len(pressures),
    }

    if len(lengths) != 1:
        raise RuntimeError(
            "Weather arrays have different lengths."
        )

    valid = 0
    invalid = 0

    invalid_rows = []

    for index in range(len(times)):

        checks = [
            valid_temperature(
                temperatures[index]
            ),
            valid_humidity(
                humidities[index]
            ),
            valid_wind(
                winds[index]
            ),
            valid_radiation(
                radiation[index]
            ),
            valid_pressure(
                pressures[index]
            ),
        ]

        if all(checks):
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
    print(
        f"Temperature range: "
        f"{min(temperatures)} to {max(temperatures)} °C"
    )

    print(
        f"Humidity range: "
        f"{min(humidities)} to {max(humidities)} %"
    )

    print(
        f"Wind range: "
        f"{min(winds)} to {max(winds)} m/s"
    )

    print(
        f"Radiation range: "
        f"{min(radiation)} to {max(radiation)} W/m²"
    )

    print(
        f"Pressure range: "
        f"{min(pressures)} to {max(pressures)} hPa"
    )

    if invalid_rows:
        print()
        print("Invalid timestamps:")
        print(invalid_rows)


if __name__ == "__main__":
    main()