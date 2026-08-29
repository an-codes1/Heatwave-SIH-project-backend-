"""Alert rule definitions for heat-health notifications.

Rules are keyed by risk level and provide the default notification
message, recommended action, and priority. In production these can
also be maintained in the intervention_rules table.
"""

from __future__ import annotations

from risk.heat_health_risk import RiskLevel

ALERT_CHANNEL = "sms"

MIN_ALERT_LEVEL = RiskLevel.HIGH

ALERT_RULES: dict[RiskLevel, dict[str, object]] = {
    RiskLevel.LOW: {
        "priority": 0,
        "message_template": (
            "Heat conditions for ward {zone_code} on {peak_date} "
            "remain LOW risk. Routine precautions only."
        ),
        "recommended_action": "Continue routine heat precautions.",
    },
    RiskLevel.MODERATE: {
        "priority": 1,
        "message_template": (
            "MODERATE heat-health risk for ward {zone_code} on "
            "{peak_date}. Peak risk score {score:.0f}/100."
        ),
        "recommended_action": (
            "Stay hydrated and limit strenuous outdoor activity "
            "during peak heat hours (11:00-16:00)."
        ),
    },
    RiskLevel.HIGH: {
        "priority": 2,
        "message_template": (
            "HIGH heat-health risk for ward {zone_code} on "
            "{peak_date}. Peak risk score {score:.0f}/100."
        ),
        "recommended_action": (
            "Avoid mid-day sun exposure, drink water regularly, "
            "and check on vulnerable residents."
        ),
    },
    RiskLevel.VERY_HIGH: {
        "priority": 3,
        "message_template": (
            "VERY HIGH heat-health risk for ward {zone_code} on "
            "{peak_date}. Peak risk score {score:.0f}/100."
        ),
        "recommended_action": (
            "Limit non-essential outdoor activity, use shaded "
            "cooling points, and prioritize vulnerable groups."
        ),
    },
    RiskLevel.EXTREME: {
        "priority": 4,
        "message_template": (
            "EXTREME heat-health warning for ward {zone_code} on "
            "{peak_date}. Peak risk score {score:.0f}/100."
        ),
        "recommended_action": (
            "Activate cooling shelters, reschedule outdoor work, "
            "and issue public health advisory."
        ),
    },
}


def alert_rule(level: RiskLevel | str) -> dict[str, object]:
    """Return the rule for a given risk level."""

    key = RiskLevel(level) if not isinstance(level, RiskLevel) else level
    return ALERT_RULES[key]