from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GeographicZone(Base):
    """
    Represents a geographic administrative zone such as a BMC ward.

    Real Bhubaneswar ward polygons will eventually be stored here.
    """

    __tablename__ = "geographic_zones"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )

    zone_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    zone_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    zone_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    population: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    source: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    geometry: Mapped[Any] = mapped_column(
        Geometry(
            geometry_type="MULTIPOLYGON",
            srid=4326,
            spatial_index=True,
        ),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )