"""Lot « L'écran Escadre du Centre ». La table `wing` gagne l'identité de
l'escadre : nom complet, période, sigle et empreinte de l'emblème. Les quatre
colonnes sont nullables et restent nulles à la montée : l'écran Escadre du
Centre les fait saisir (`emblem_sha` reste NULL : tant qu'aucun emblème n'est
posé, le front garde l'insigne générique).

Montée : quatre colonnes ajoutées, nulles.
Descente : les quatre colonnes sont retirées.

Revision ID: 0033
Revises: 0032
Create Date: 2026-10-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0033'
down_revision: Union[str, None] = '0032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('wing', sa.Column('full_name', sa.Text(), nullable=True))
    op.add_column('wing', sa.Column('period', sa.Text(), nullable=True))
    op.add_column('wing', sa.Column('sigle', sa.Text(), nullable=True))
    op.add_column('wing', sa.Column('emblem_sha', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('wing', 'emblem_sha')
    op.drop_column('wing', 'sigle')
    op.drop_column('wing', 'period')
    op.drop_column('wing', 'full_name')
