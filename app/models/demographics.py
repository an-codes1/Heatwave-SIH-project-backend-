from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DemographicVulnerability(Base):
    """
    Stores real demographic and vulnerability information
    for a geographic zone such as a BMC ward.
    """

    __tablename__ = "demographic_vulnerability"

    __table_args__ = (
        UniqueConstraint(
            "zone_id",
            "reference_year",
            name="uq_demographic_zone_year",
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

    reference_year: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    total_population: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    elderly_population: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    children_population: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    outdoor_worker_population: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    population_density_per_km2: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    vulnerability_score: Mapped[float | None] = mapped_column(
        Float,
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