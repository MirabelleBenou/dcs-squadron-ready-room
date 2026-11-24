"""Lot « rr-env-epure » (v1.0105) : la table `reglage`, où l'application garde les
réglages qui ne se lisent plus du `.env` (les secrets y sont chiffrés par `app/reglages.py`).

`cle` (texte, clé primaire), `valeur` (texte, non nul), `maj_le` (`timestamptz`, non nul,
`now()` par défaut), `maj_par` (`bigint`, nul, clé étrangère `profiles.id`). Aucune donnée
reprise ici : la reprise du `.env` se joue une fois, au premier démarrage avec la clé
(`app.reglages.charger_au_demarrage`).

Additive. Réversible : la descente retire la table.

Revision ID: 0045
Revises: 0044
Create Date: 2026-11-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0045'
down_revision: Union[str, None] = '0044'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'reglage',
        sa.Column('cle', sa.Text(), nullable=False),
        sa.Column('valeur', sa.Text(), nullable=False),
        sa.Column(
            'maj_le', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False
        ),
        sa.Column('maj_par', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['maj_par'], ['profiles.id']),
        sa.PrimaryKeyConstraint('cle'),
    )


def downgrade() -> None:
    op.drop_table('reglage')
