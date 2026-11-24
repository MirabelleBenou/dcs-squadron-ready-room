"""Lot « L'identité de l'escadrille » (R189). L'identifiant (`designation`)
devient aussi le préfixe retiré des pseudos ; l'ancien indicatif (`tag`),
qui valait l'identifiant pour chaque escadrille, devient le callsign radio :
- `tag` est renommé `callsign`, rendu facultatif et VIDÉ -- ses valeurs
  étaient des identifiants, pas des callsigns ;
- `full_name`, facultatif, est neuf : le nom complet de l'unité.
La descente retire `full_name` et rétablit `tag` obligatoire, égal à
l'identifiant -- sa valeur d'avant ce lot.

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0028'
down_revision: Union[str, None] = '0027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('squadron', 'tag', new_column_name='callsign',
                    existing_type=sa.Text(), nullable=True)
    op.execute("UPDATE squadron SET callsign = NULL")
    op.add_column('squadron', sa.Column('full_name', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('squadron', 'full_name')
    op.execute("UPDATE squadron SET callsign = designation")
    op.alter_column('squadron', 'callsign', new_column_name='tag',
                    existing_type=sa.Text(), nullable=False)
