from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RiskPrediction(Base):
    """
    Stores ward/zone-level heat-health risk predictions.
    """

    __tablename__ = "risk_predictions"

    __table_args__ = (
        UniqueConstraint(
            "zone_id",
            "prediction_generated_at",
            "prediction_for",
            "model_version",
            name="uq_risk_prediction_zone_generation_target_model",
        ),
    )

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

    prediction_generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    prediction_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    thermal_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    mortality_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    hospitalization_risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    overall_risk_level: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    model_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    model_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )