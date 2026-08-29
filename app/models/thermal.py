from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ThermalIndex(Base):
    """
    Stores calculated human thermal stress indices.

    Raw weather data remains stored separately in weather_observations
    and weather_forecasts.
    """

    __tablename__ = "thermal_indices"

    __table_args__ = (
        UniqueConstraint(
            "station_id",
            "valid_for",
            "calculation_type",
            name="uq_thermal_index_station_time_type",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    station_id: Mapped[int | None] = mapped_column(
        ForeignKey("weather_stations.id"),
        nullable=True,
        index=True,
    )

    zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("geographic_zones.id"),
        nullable=True,
        index=True,
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    utci_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    wbgt_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    heat_index_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    thermal_risk_level: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    calculation_type: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    methodology: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )