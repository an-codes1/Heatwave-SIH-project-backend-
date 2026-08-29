"""Explainable Heat-Health Risk Proxy.

Combines a thermal severity term (0-100) with a ward vulnerability
term (0-100). The thermal component dominates the composite.

Weights are explicit and documented:

    composite risk = 0.70 * thermal_severity
                   + 0.30 * ward_vulnerability

The result is an application risk proxy, NOT a mortality or
hospitalization probability. Those fields stay NULL until legitimate
aggregated health-outcome labels are available.
"""

from __future__ import annotations

from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    EXTREME = "EXTREME"


THERMAL_WEIGHT = 0.70
VULNERABILITY_WEIGHT = 0.30

RISK_METHODOLOGY = (
    "Explainable Heat-Health Risk Proxy. "
    f"Score = {THERMAL_WEIGHT:.2f} * thermal_severity "
    f"(sun-exposed UTCI severity 0-100) + "
    f"{VULNERABILITY_WEIGHT:.2f} * demographic vulnerability "
    "(provisional 0-100). Thermal component dominates. This is a "
    "risk proxy for planning; it is NOT a prediction of mortality "
    "or hospitalization."
)

LEVEL_BANDS = [
    (80.0, RiskLevel.EXTREME),
    (60.0, RiskLevel.VERY_HIGH),
    (40.0, RiskLevel.HIGH),
    (20.0, RiskLevel.MODERATE),
]


def risk_level(score: float) -> RiskLevel:
    """Map a 0-100 risk score to a discrete risk level."""

    for threshold, level in LEVEL_BANDS:
        if score >= threshold:
            return level

    return RiskLevel.LOW


def heat_health_risk(
    thermal_severity: float,
    vulnerability: float,
) -> tuple[float, RiskLevel]:
    """Combine thermal severity and ward vulnerability into a risk proxy."""

    bounded_thermal = max(0.0, min(100.0, thermal_severity))
    bounded_vulnerability = max(0.0, min(100.0, vulnerability))

    score = (
        THERMAL_WEIGHT * bounded_thermal
        + VULNERABILITY_WEIGHT * bounded_vulnerability
    )

    return score, risk_level(score)