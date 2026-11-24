"""Lot « L'appareil de l'escadrille » -- l'escadrille déclare ses appareils au
Centre de Commandement. Une colonne additive pure :
- `aircraft` sur `squadron` : la liste ordonnée des appareils déclarés
  (« Mi-24P », « Mi-8 »), en JSONB, NULLABLE. Les escadrilles existantes
  restent sans valeur : c'est à leurs chefs de la déclarer.

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0026'
down_revision: Union[str, None] = '0025'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'squadron',
        sa.Column('aircraft', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('squadron', 'aircraft')
