import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from scripts.download_bhubaneswar_weather import (
    find_bhubaneswar,
)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

OUTPUT_FILE = Path(
    "data/raw/bhubaneswar_forecast.json"
)

FORECAST_DAYS = 6


def download_forecast(
    client: httpx.Client,
    latitude: float,
    longitude: float,
) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
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
        "forecast_days": FORECAST_DAYS,
    }

    response = client.get(
        FORECAST_URL,
        params=params,
    )
    response.raise_for_status()

    return response.json()


def main() -> None:
    print("Finding Bhubaneswar coordinates...")

    with httpx.Client(
        timeout=60.0,
        follow_redirects=True,
    ) as client:

        latitude, longitude = find_bhubaneswar(client)

        print()
        print("Downloading five-day forecast...")

        forecast = download_forecast(
            client,
            latitude,
            longitude,
        )

    hourly = forecast.get("hourly", {})

    if not hourly.get("time"):
        raise RuntimeError(
            "The forecast API returned no hourly data."
        )

    # Stored generation stamp for deterministic idempotent imports.
    forecast["_generated_at"] = (
        datetime.now(timezone.utc).isoformat()
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(forecast, indent=2),
        encoding="utf-8",
    )

    print()
    print("Forecast download successful!")
    print(f"Hourly records: {len(hourly['time'])}")
    print(f"First hour: {hourly['time'][0]}")
    print(f"Last hour: {hourly['time'][-1]}")
    print(f"Generated at (UTC): {forecast['_generated_at']}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()