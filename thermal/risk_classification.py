"""
UTCI thermal-stress classification and application severity score.

The UTCI stress categories use the official, documented UTCI
equivalent-temperature bands (Blazejczyk et al. 2012 / UTCI standard
categories). They are NOT invented here.

The 0-100 heat severity score is an APPLICATION-SPECIFIC mapping:
it is proportional to how far UTCI sits above the "no thermal
stress" heat threshold (26 degC) and is capped at 100 at the
"extreme heat stress" boundary (46 degC). It is a convenience for
combining with vulnerability and is not a mortality probability.
"""

from dataclasses import dataclass


# Official UTCI equivalent-temperature categories.
# Boundaries follow the documented UTCI classification.
HEAT_CATEGORY_BANDS = [
    # (utci_lower_exclusive, minima, category)
    (46.0, "extreme heat stress"),
    (38.0, "very strong heat stress"),
    (32.0, "strong heat stress"),
    (26.0, "moderate heat stress"),
]

NO_STRESS_LOWER = 9.0
NO_STRESS_UPPER = 26.0

HEAT_NO_STRESS_THRESHOLD_C = 26.0
EXTREME_C = 46.0

SEVERITY_SCALE = 100.0


@dataclass(frozen=True)
class ThermalClassification:
    utci_c: float
    stress_category: str
    severity_score: float


def utci_stress_category(utci_c: float) -> str:
    """Return the official UTCI stress category for a UTCI value."""

    if utci_c > 46.0:
        return "extreme heat stress"

    if utci_c > 38.0:
        return "very strong heat stress"

    if utci_c > 32.0:
        return "strong heat stress"

    if utci_c > 26.0:
        return "moderate heat stress"

    if utci_c >= 9.0:
        return "no thermal stress"

    if utci_c >= 0.0:
        return "slight cold stress"

    if utci_c >= -13.0:
        return "moderate cold stress"

    if utci_c >= -27.0:
        return "strong cold stress"

    if utci_c >= -40.0:
        return "very strong cold stress"

    return "extreme cold stress"


def heat_severity_score(utci_c: float) -> float:
    """
    Application-specific 0-100 heat severity score.

    Score = 100 * (UTCI - 26) / (46 - 26), clamped to [0, 100].
    """

    if utci_c <= HEAT_NO_STRESS_THRESHOLD_C:
        return 0.0

    score = (
        (utci_c - HEAT_NO_STRESS_THRESHOLD_C)
        / (EXTREME_C - HEAT_NO_STRESS_THRESHOLD_C)
        * SEVERITY_SCALE
    )

    return max(0.0, min(SEVERITY_SCALE, score))


def classify(utci_c: float | None) -> ThermalClassification | None:
    """Classify a UTCI value into category + severity. None if None."""

    if utci_c is None:
        return None

    return ThermalClassification(
        utci_c=utci_c,
        stress_category=utci_stress_category(utci_c),
        severity_score=heat_severity_score(utci_c),
    )