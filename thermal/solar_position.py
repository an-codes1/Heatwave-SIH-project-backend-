"""
Solar position calculations for the Bhubaneswar weather location.

pvlib is used to compute solar elevation and azimuth for the exact
hourly timestamps of the weather series, at the Bhubaneswar ERA5
grid point used throughout the project. Times stay in Asia/Kolkata.
"""

from pandas import DatetimeIndex

from pvlib.solarposition import get_solarposition


# ERA5 gridded reanalysis point used by the Open-Meteo downloader.
BHUBANESWAR_GRID = {
    "latitude": 20.25,
    "longitude": 85.75,
}

TIMEZONE = "Asia/Kolkata"


def solar_positions(times: list) -> tuple[list[float], list[float]]:
    """
    Compute solar elevation and azimuth for each timestamp.

    Parameters
    ----------
    times:
        A list of timezone-aware datetimes (Asia/Kolkata).

    Returns
    -------
    (elevations, azimuths):
        Solar elevation in degrees above the horizon and solar
        azimuth in degrees from north, one value per input time.
    """

    index = DatetimeIndex(list(times))

    if index.tz is None:
        index = index.tz_localize(TIMEZONE)

    position = get_solarposition(
        time=index,
        latitude=BHUBANESWAR_GRID["latitude"],
        longitude=BHUBANESWAR_GRID["longitude"],
    )

    elevations = position["apparent_elevation"].to_numpy()
    azimuths = position["azimuth"].to_numpy()

    return elevations.tolist(), azimuths.tolist()