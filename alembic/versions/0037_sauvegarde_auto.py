"""Lot « Les sauvegardes automatiques ». La table `sauvegarde_auto_reglage` : le
réglage de la sauvegarde que l'application prend elle-même. Une ligne au plus
(`id = 1`, contrainte `ck_sauvegarde_auto_reglage_unique`) : `intervalle_h`, la
fréquence en heures (`0` : désactivée), `garder`, le nombre d'automatiques
gardées, et `modifie_le`, l'heure de PostgreSQL (`now()`) de la dernière
écriture.

La table naît vide : aucun semis. Sans ligne, l'application tient le défaut
(toutes les 24 h, les 7 dernières gardées).

Réversible : la descente retire la table.

Revision ID: 0037
Revises: 0036
Create Date: 2026-10-15
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0037'
down_revision: Union[str, None] = '0036'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sauvegarde_auto_reglage',
        sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
        sa.Column('intervalle_h', sa.Integer(), nullable=False),
        sa.Column('garder', sa.Integer(), nullable=False),
        sa.Column(
            'modifie_le',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.CheckConstraint('id = 1', name='ck_sauvegarde_auto_reglage_unique'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('sauvegarde_auto_reglage')
