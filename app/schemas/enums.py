"""Stable enum values exposed by the API."""

from __future__ import annotations

from enum import Enum


class ThermalScenario(str, Enum):
    OBSERVED_SHADE = "observed_reference_shade"
    OBSERVED_SUN_EXPOSED = "observed_sun_exposed"
    FORECAST_SHADE = "forecast_reference_shade"
    FORECAST_SUN_EXPOSED = "forecast_sun_exposed"


class AlertStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"


class AlertChannel(str, Enum):
    SMS = "sms"
    WHATSAPP = "whatsapp"


RISK_LEVELS = ("LOW", "MODERATE", "HIGH", "VERY_HIGH", "EXTREME")