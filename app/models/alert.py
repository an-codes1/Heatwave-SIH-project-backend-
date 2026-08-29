from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Alert(Base):
    """
    Stores generated heat-health alerts.
    """

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    zone_id: Mapped[int] = mapped_column(
        ForeignKey("geographic_zones.id"),
        nullable=False,
        index=True,
    )

    risk_prediction_id: Mapped[int | None] = mapped_column(
        ForeignKey("risk_predictions.id"),
        nullable=True,
        index=True,
    )

    alert_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    alert_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommended_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    channel: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class InterventionRule(Base):
    """
    Stores configurable recommendations for different risk levels.
    """

    __tablename__ = "intervention_rules"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    risk_level: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    trigger_condition: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )