"""Lot « Les cartes DCS de chaque pilote » (v1.0085, R640) : deux colonnes sur
`profiles`. `cartes_dcs` (JSONB) porte les cartes que le pilote déclare
posséder, dans l'ordre de la liste officielle ; `cartes_dcs_le` date la
déclaration.

NULL = non déclaré ; `[]` = déclaré sans carte. Aucun semis : toutes les
colonnes naissent NULL. Additive : aucune colonne existante ne change.

Réversible : la descente retire les deux colonnes, dans l'ordre inverse.

Revision ID: 0042
Revises: 0041
Create Date: 2026-11-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0042'
down_revision: Union[str, None] = '0041'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column('cartes_dcs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'profiles',
        sa.Column('cartes_dcs_le', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('profiles', 'cartes_dcs_le')
    op.drop_column('profiles', 'cartes_dcs')
