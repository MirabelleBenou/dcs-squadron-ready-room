"""Lot « L'accès invité » (v1.0070, le porteur, 4 novembre). Une table neuve,
`invitations` : les personnes hors du serveur Discord de l'escadre qu'un
administrateur autorise, par leur identifiant Discord, à voir la Ready Room en
lecture seule, pour trente jours prolongeables.

`discord_id` est la clé primaire, sans clé étrangère (l'invité n'a pas de
profil). `invite_par` suit le profil de l'administrateur qui a invité.
`revoque_le` et `derniere_entree` sont nuls par défaut.

La table naît vide : aucun semis. Additive : aucune table existante ne change.

Réversible : la descente supprime la table.

Revision ID: 0041
Revises: 0040
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0041'
down_revision: Union[str, None] = '0040'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'invitations',
        sa.Column('discord_id', sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column('nom', sa.Text(), nullable=False),
        sa.Column('username', sa.Text(), nullable=False),
        sa.Column('invite_par', sa.BigInteger(), nullable=False),
        sa.Column(
            'cree_le',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('jusqua', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoque_le', sa.DateTime(timezone=True), nullable=True),
        sa.Column('derniere_entree', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['invite_par'], ['profiles.id']),
        sa.PrimaryKeyConstraint('discord_id'),
    )


def downgrade() -> None:
    op.drop_table('invitations')
