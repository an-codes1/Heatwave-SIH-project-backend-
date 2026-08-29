import argparse
import json
from pathlib import Path

import httpx


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

OUTPUT_FILE = Path("data/raw/bhubaneswar_weather.json")


def find_bhubaneswar(client: httpx.Client) -> tuple[float, float]:
    params = {
        "name": "Bhubaneswar",
        "count": 10,
        "language": "en",
        "format": "json",
        "countryCode": "IN",
    }

    response = client.get(
        GEOCODING_URL,
        params=params,
    )
    response.raise_for_status()

    data = response.json()

    results = data.get("results", [])

    if not results:
        raise RuntimeError(
            "Bhubaneswar was not found by the geocoding API."
        )

    for result in results:
        name = str(result.get("name", "")).lower()
        admin1 = str(result.get("admin1", "")).lower()

        if name == "bhubaneswar" and "odisha" in admin1:
            latitude = float(result["latitude"])
            longitude = float(result["longitude"])

            print("Location selected:")
            print(f"Name: {result.get('name')}")
            print(f"State: {result.get('admin1')}")
            print(f"Country: {result.get('country')}")
            print(f"Latitude: {latitude}")
            print(f"Longitude: {longitude}")

            return latitude, longitude

    raise RuntimeError(
        "Could not identify Bhubaneswar, Odisha "
        "from the geocoding results."
    )


def download_weather(
    client: httpx.Client,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
) -> dict:

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(
            [
                "temperature_2m",
                "relative_humidity_2m",
                "wind_speed_10m",
                "shortwave_radiation",
                "direct_radiation",
                "diffuse_radiation",
                "direct_normal_irradiance",
                "surface_pressure",
            ]
        ),
        "wind_speed_unit": "ms",
        "timezone": "Asia/Kolkata",
        "models": "era5",
    }

    response = client.get(
        ARCHIVE_URL,
        params=params,
    )

    response.raise_for_status()

    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start",
        required=True,
        help="Start date in YYYY-MM-DD format",
    )

    parser.add_argument(
        "--end",
        required=True,
        help="End date in YYYY-MM-DD format",
    )

    args = parser.parse_args()

    print("Finding Bhubaneswar coordinates...")

    with httpx.Client(
        timeout=60.0,
        follow_redirects=True,
    ) as client:

        latitude, longitude = find_bhubaneswar(client)

        print()
        print("Downloading historical weather...")

        weather = download_weather(
            client=client,
            latitude=latitude,
            longitude=longitude,
            start_date=args.start,
            end_date=args.end,
        )

    hourly = weather.get("hourly", {})
    times = hourly.get("time", [])

    if not times:
        raise RuntimeError(
            "The weather API returned no hourly data."
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(weather, indent=2),
        encoding="utf-8",
    )

    print()
    print("Weather download successful!")
    print(f"Requested period: {args.start} to {args.end}")
    print(f"Hourly records: {len(times)}")
    print(f"Timezone: {weather.get('timezone')}")
    print(f"Latitude used: {weather.get('latitude')}")
    print(f"Longitude used: {weather.get('longitude')}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()