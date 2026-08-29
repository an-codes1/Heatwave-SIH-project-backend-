"""
Mean radiant temperature (MRT) estimation.

Two clearly separated scenarios are implemented:

REFERENCE_SHADE:
    A documented reference/shade approximation in which MRT is set
    equal to the dry-bulb air temperature. This is NOT a direct-sun
    MRT and is only a shade reference.

SUN_EXPOSED:
    Sun-exposed MRT = reference MRT + solar_gain delta_mrt.
    The radiant load is estimated with pythermalcomfort's
    `solar_gain` model (ASHRAE 55 Effective Radiant Field method)
    using the direct-normal shortwave irradiance (DNI), the solar
    elevation computed with pvlib, and standardized exposure
    parameters.

Solar radiation is NEVER assigned directly to MRT. solar_gain
converts irradiance into a delta mean radiant temperature which is
then added to the air-temperature reference.
"""

from dataclasses import dataclass
from enum import Enum

from pythermalcomfort.models import solar_gain


class Scenario(str, Enum):
    REFERENCE_SHADE = "REFERENCE_SHADE"
    SUN_EXPOSED = "SUN_EXPOSED"


# ---------------------------------------------------------------------
# Standardized sun-exposure configuration constants.
#
# These describe a hypothetical, standardized outdoor person
# ("exposed palm orientation") so that results are reproducible.
# They are NOT measurements of any specific person. All assumptions
# are documented in the methodology string of every stored index.
# ---------------------------------------------------------------------

# Direct-beam radiation relative to the front of the person (SHARP).
# 90 degrees = radiation from the side; a neutral, standardized
# orientation that avoids claiming any person-specific facing.
SHARP = 90.0

# Fraction of the model body surface exposed to the sun.
# ASHRAE 55 Table C2-2 style standing-person fraction (0.224).
FRACTION_BODY_EXPOSED = 0.224

# Sky-vault view fraction (ASHRAE 55 style reference value).
SKY_VAULT_VIEW_FRACTION = 0.696

# Total solar transmittance. 1.0 = unobstructed outdoor exposure
# (no window glazing/blind filtration).
SOLAR_TRANSMITTANCE = 1.0

# Average short-wave absorptivity of the occupant (skin + clothing).
SHORTWAVE_ABSORPTIVITY = 0.7

# Floor/ground reflectance (ASHRAE default).
FLOOR_REFLECTANCE = 0.6

# Posture of the standardized person.
POSTURE = "standing"

# Maximum solar elevation accepted by solar_gain (0-90 deg).
SOLAR_ALTITUDE_LIMIT = 89.9


EXPOSURE_ASSUMPTIONS = {
    "sharp_deg": SHARP,
    "fraction_body_exposed_sun": FRACTION_BODY_EXPOSED,
    "sky_vault_view_fraction": SKY_VAULT_VIEW_FRACTION,
    "solar_transmittance": SOLAR_TRANSMITTANCE,
    "shortwave_absorptivity": SHORTWAVE_ABSORPTIVITY,
    "floor_reflectance": FLOOR_REFLECTANCE,
    "posture": POSTURE,
}


@dataclass(frozen=True)
class MRTResult:
    scenario: Scenario
    mean_radiant_temperature_c: float
    delta_mrt_c: float


def methodology_text(scenario: Scenario, category: str) -> str:
    """Build a documented methodology description string."""

    base = (
        f"{category} thermal index. MRT scenario={scenario.value}. "
    )

    if scenario is Scenario.REFERENCE_SHADE:
        base += (
            "REFERENCE_SHADE: MRT assumed equal to dry-bulb air "
            "temperature as an explicitly labelled shade reference. "
            "This is NOT a direct-sun MRT."
        )
    else:
        base += (
            "SUN_EXPOSED: MRT = air temperature + delta MRT from "
            "pythermalcomfort.models.solar_gain (ASHRAE 55 Effective "
            "Radiant Field method) using ERA5 DNI and pvlib solar "
            "elevation. Standardized exposure assumptions: "
            + "; ".join(
                f"{key}={value}"
                for key, value in EXPOSURE_ASSUMPTIONS.items()
            )
            + ". At night or when solar elevation <= 0 the solar gain "
              "is zero and sun-exposed MRT equals the shade reference. "
              "The parameters describe a standardized scenario, not "
              "a measured individual."
        )

    return base


def reference_shade_mrt(air_temperature_c: float) -> MRTResult:
    """MRT for the reference/shade scenario (MRT = air temperature)."""

    return MRTResult(
        scenario=Scenario.REFERENCE_SHADE,
        mean_radiant_temperature_c=air_temperature_c,
        delta_mrt_c=0.0,
    )


def solar_delta_mrt(
    direct_normal_irradiance_wm2: float,
    solar_elevation_deg: float,
) -> float:
    """
    Estimate the delta MRT caused by direct-beam solar exposure.

    Zero at night or below/near the horizon, where no meaningful
    direct-beam solar exposure exists.
    """

    if solar_elevation_deg is None:
        return 0.0

    if solar_elevation_deg <= 0.0:
        return 0.0

    if direct_normal_irradiance_wm2 is None:
        return 0.0

    if direct_normal_irradiance_wm2 <= 0.0:
        return 0.0

    altitude = min(
        float(solar_elevation_deg),
        SOLAR_ALTITUDE_LIMIT,
    )

    result = solar_gain(
        sol_altitude=altitude,
        sharp=SHARP,
        sol_radiation_dir=float(direct_normal_irradiance_wm2),
        sol_transmittance=SOLAR_TRANSMITTANCE,
        f_svv=SKY_VAULT_VIEW_FRACTION,
        f_bes=FRACTION_BODY_EXPOSED,
        asw=SHORTWAVE_ABSORPTIVITY,
        posture=POSTURE,
        floor_reflectance=FLOOR_REFLECTANCE,
        round_output=False,
    )

    return max(0.0, float(result.delta_mrt))


def sun_exposed_mrt(
    air_temperature_c: float,
    direct_normal_irradiance_wm2: float,
    solar_elevation_deg: float,
) -> MRTResult:
    """MRT for the sun-exposed scenario."""

    delta = solar_delta_mrt(
        direct_normal_irradiance_wm2,
        solar_elevation_deg,
    )

    return MRTResult(
        scenario=Scenario.SUN_EXPOSED,
        mean_radiant_temperature_c=air_temperature_c + delta,
        delta_mrt_c=delta,
    )