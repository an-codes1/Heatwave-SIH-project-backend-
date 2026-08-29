"""Generate heat-health alerts from latest forecast risk predictions."""

from __future__ import annotations

from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.core.logging import get_logger, log_event
from app.models.alert import Alert
from app.models.geographic_zone import GeographicZone
from app.models.risk import RiskPrediction
from risk.alert_rules import (
    ALERT_CHANNEL,
    ALERT_RULES,
    MIN_ALERT_LEVEL,
)
from risk.heat_health_risk import RiskLevel

FORECAST_MODEL_VERSION = "v0.1-forecast"

INDIA_TZ = ZoneInfo("Asia/Kolkata")

logger = get_logger(__name__)


def _level_rank(level: str | None) -> int:
    """Ordered position of a risk level (LOW..EXTREME)."""

    if level is None:
        return -1

    try:
        return list(RiskLevel).index(RiskLevel(level))
    except ValueError:
        return -1


async def latest_forecast_generation(session) -> object | None:
    return await session.scalar(
        select(func.max(RiskPrediction.prediction_generated_at)).where(
            RiskPrediction.model_version == FORECAST_MODEL_VERSION
        )
    )


async def generate_alerts(session) -> tuple[list[Alert], dict[str, int]]:
    """Create one alert per ward whose peak forecast risk triggers.

    Alerts are deduplicated against existing pending/sent alerts that
    reference the same risk prediction, making the operation idempotent.

    Returns (created_alerts, counts) where counts holds
    'generated', 'deduplicated', and 'below_threshold'.
    """

    generation = await latest_forecast_generation(session)

    if generation is None:
        raise RuntimeError("No forecast risk predictions found.")

    rows = (
        await session.execute(
            select(
                RiskPrediction.zone_id,
                RiskPrediction.id,
                RiskPrediction.prediction_for,
                RiskPrediction.thermal_risk_score,
                RiskPrediction.overall_risk_level,
            ).where(
                RiskPrediction.model_version
                == FORECAST_MODEL_VERSION,
                RiskPrediction.prediction_generated_at == generation,
            )
        )
    ).all()

    existing = (
        await session.execute(
            select(Alert.risk_prediction_id).where(
                Alert.status.in_(["pending", "sent"]),
                Alert.risk_prediction_id.is_not(None),
            )
        )
    ).scalars().all()

    alerted_prediction_ids = set(existing)

    zones = (
        await session.execute(
            select(GeographicZone.id, GeographicZone.zone_code)
        )
    ).all()

    zone_code_by_id = {
        zone_id: zone_code for zone_id, zone_code in zones
    }

    by_zone: dict[int, list] = {}

    for row in rows:
        by_zone.setdefault(row.zone_id, []).append(row)

    min_rank = _level_rank(MIN_ALERT_LEVEL.value)

    created: list[Alert] = []
    counts = {"generated": 0, "deduplicated": 0, "below_threshold": 0}

    for zone_id, predictions in by_zone.items():

        peak = max(
            predictions,
            key=lambda r: (
                _level_rank(r.overall_risk_level),
                r.thermal_risk_score or 0.0,
            ),
        )

        level = RiskLevel(peak.overall_risk_level)

        if _level_rank(level.value) < min_rank:
            counts["below_threshold"] += 1
            continue

        if peak.id in alerted_prediction_ids:
            counts["deduplicated"] += 1
            continue

        rule = ALERT_RULES[level]

        peak_date = peak.prediction_for.astimezone(
            INDIA_TZ
        ).date()

        message = rule["message_template"].format(
            zone_code=zone_code_by_id.get(zone_id, str(zone_id)),
            peak_date=peak_date,
            score=peak.thermal_risk_score or 0.0,
        )

        created.append(
            Alert(
                zone_id=zone_id,
                risk_prediction_id=peak.id,
                alert_level=level.value,
                alert_message=message,
                recommended_action=str(
                    rule["recommended_action"]
                ),
                channel=ALERT_CHANNEL,
                status="pending",
            )
        )

    session.add_all(created)
    await session.commit()

    counts["generated"] = len(created)

    log_event(
        logger,
        "INFO",
        "alert generation summary",
        **counts,
    )

    return created, counts