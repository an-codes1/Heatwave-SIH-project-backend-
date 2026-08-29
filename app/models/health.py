from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HealthOutcome(Base):
    """
    Stores aggregated public-health outcomes.

    This table must never contain individual patient records.
    """

    __tablename__ = "health_outcomes"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("geographic_zones.id"),
        nullable=True,
        index=True,
    )

    observation_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    geographic_resolution: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    total_deaths: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    heat_related_deaths: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_hospitalizations: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    heat_related_hospitalizations: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )