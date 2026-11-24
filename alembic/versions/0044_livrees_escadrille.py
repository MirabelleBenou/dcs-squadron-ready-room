"""Lot « La config d'escadre de Mission Plan fabriquée par le Centre » (v1.0091) :
les livrées et le surnom d'une escadrille. Trois colonnes ajoutées à `squadron`,
NULLABLES, sans défaut : `liveries` (JSONB, la liste des livrées, chacune avec
ses appareils), `default_liveries` (JSONB, la livrée par défaut, par appareil) et
`nickname` (Text, le surnom). Les escadrilles existantes restent sans valeur.

Additive : aucune autre table, aucune donnée réécrite. Réversible : la
descente retire les trois colonnes.

Revision ID: 0044
Revises: 0043
Create Date: 2026-11-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0044'
down_revision: Union[str, None] = '0043'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'squadron',
        sa.Column('liveries', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'squadron',
        sa.Column('default_liveries', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column('squadron', sa.Column('nickname', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('squadron', 'nickname')
    op.drop_column('squadron', 'default_liveries')
    op.drop_column('squadron', 'liveries')
