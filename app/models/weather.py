from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WeatherStation(Base):
    __tablename__ = "weather_stations"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    station_code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    station_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    location: Mapped[Any] = mapped_column(
        Geometry(
            geometry_type="POINT",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class WeatherObservation(Base):
    __tablename__ = "weather_observations"

    __table_args__ = (
        UniqueConstraint(
            "station_id",
            "observed_at",
            name="uq_weather_observation_station_time",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    station_id: Mapped[int] = mapped_column(
        ForeignKey("weather_stations.id"),
        nullable=False,
        index=True,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    air_temperature_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    relative_humidity_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    wind_speed_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    solar_radiation_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    direct_radiation_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    diffuse_radiation_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    direct_normal_irradiance_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    atmospheric_pressure_hpa: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"

    __table_args__ = (
        UniqueConstraint(
            "station_id",
            "forecast_generated_at",
            "forecast_for",
            name="uq_weather_forecast_station_generation_target",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    station_id: Mapped[int] = mapped_column(
        ForeignKey("weather_stations.id"),
        nullable=False,
        index=True,
    )

    forecast_generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    forecast_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    air_temperature_c: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    relative_humidity_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    wind_speed_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    solar_radiation_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    direct_radiation_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    diffuse_radiation_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    direct_normal_irradiance_wm2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    atmospheric_pressure_hpa: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
