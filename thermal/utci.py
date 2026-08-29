from dataclasses import dataclass
from math import isnan

from pythermalcomfort.models import utci


@dataclass(frozen=True)
class UTCIResult:
    utci_c: float | None
    stress_category: str | None
    valid: bool
    reason: str | None = None


def calculate_utci(
    air_temperature_c: float,
    mean_radiant_temperature_c: float,
    wind_speed_ms: float,
    relative_humidity_pct: float,
) -> UTCIResult:
    """
    Calculate Universal Thermal Climate Index (UTCI).

    Parameters
    ----------
    air_temperature_c:
        Dry-bulb air temperature in degrees Celsius.

    mean_radiant_temperature_c:
        Mean radiant temperature in degrees Celsius.

    wind_speed_ms:
        Wind speed at approximately 10 m above ground in m/s.

    relative_humidity_pct:
        Relative humidity in percent.
    """

    if not -50 < air_temperature_c < 50:
        return UTCIResult(
            None,
            None,
            False,
            "Air temperature outside UTCI applicability range.",
        )

    if not 0 <= relative_humidity_pct <= 100:
        return UTCIResult(
            None,
            None,
            False,
            "Relative humidity must be between 0 and 100 percent.",
        )

    if not 0.5 <= wind_speed_ms <= 17:
        return UTCIResult(
            None,
            None,
            False,
            "Wind speed outside standard UTCI applicability range.",
        )

    delta_tr = (
        mean_radiant_temperature_c
        - air_temperature_c
    )

    if not -30 < delta_tr < 70:
        return UTCIResult(
            None,
            None,
            False,
            "Mean radiant temperature difference outside UTCI applicability range.",
        )

    result = utci(
        tdb=air_temperature_c,
        tr=mean_radiant_temperature_c,
        v=wind_speed_ms,
        rh=relative_humidity_pct,
        units="SI",
        limit_inputs=True,
        round_output=False,
    )

    value = float(result.utci)

    if isnan(value):
        return UTCIResult(
            None,
            None,
            False,
            "pythermalcomfort returned NaN.",
        )

    return UTCIResult(
        utci_c=value,
        stress_category=str(
            result.stress_category
        ),
        valid=True,
    )