"""widen calculation_type and deduplicate thermal indices

Revision ID: 1f3a8c2e9b00
Revises: 90e07dff9b52
Create Date: 2026-08-30 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f3a8c2e9b00'
down_revision: Union[str, Sequence[str], None] = '90e07dff9b52'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'thermal_indices',
        'calculation_type',
        existing_type=sa.String(length=20),
        type_=sa.String(length=40),
        existing_nullable=False,
    )
    op.create_unique_constraint(
        'uq_thermal_index_station_time_type',
        'thermal_indices',
        ['station_id', 'valid_for', 'calculation_type'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'uq_thermal_index_station_time_type',
        'thermal_indices',
        type_='unique',
    )
    op.alter_column(
        'thermal_indices',
        'calculation_type',
        existing_type=sa.String(length=40),
        type_=sa.String(length=20),
        existing_nullable=False,
    )