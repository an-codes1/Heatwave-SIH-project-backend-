"""add performance indexes for API query paths

Revision ID: 9c5f7e2a1b3d
Revises: 1f3a8c2e9b00
Create Date: 2026-08-30 11:00:00.000000

Adds compound indexes that serve the most common API lookup patterns.
Previously only single-column indexes existed on these tables.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c5f7e2a1b3d'
down_revision: Union[str, Sequence[str], None] = '1f3a8c2e9b00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'ix_risk_predictions_zone_id_prediction_for',
        'risk_predictions',
        ['zone_id', 'prediction_for'],
        unique=False,
    )
    op.create_index(
        'ix_thermal_indices_calculation_type',
        'thermal_indices',
        ['calculation_type'],
        unique=False,
    )
    op.create_index(
        'ix_weather_forecasts_station_id_forecast_for',
        'weather_forecasts',
        ['station_id', 'forecast_for'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_weather_forecasts_station_id_forecast_for',
        table_name='weather_forecasts',
    )
    op.drop_index(
        'ix_thermal_indices_calculation_type',
        table_name='thermal_indices',
    )
    op.drop_index(
        'ix_risk_predictions_zone_id_prediction_for',
        table_name='risk_predictions',
    )