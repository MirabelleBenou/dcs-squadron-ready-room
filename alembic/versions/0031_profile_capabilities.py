"""Lot « Les relances nominatives ». La table `profile_capabilities` : une
capacité accordée à un compte précis, par son nom -- le miroir de
`role_capabilities`, où la clé est un profil (`profiles.id`) au lieu d'un rôle
Discord. Elle porte `relances.destinataire` : les comptes qui reçoivent les MP
de relance, en plus des porteurs des rôles choisis à l'écran Droits.

Deux colonnes, clé primaire sur les deux, comme `role_capabilities`. La table
naît vide : aucun semis, aucune source à reprendre.

Réversible : la descente retire la table.

Revision ID: 0031
Revises: 0030
Create Date: 2026-10-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0031'
down_revision: Union[str, None] = '0030'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'profile_capabilities',
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('capability', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('profile_id', 'capability', name='profile_capabilities_pkey'),
    )


def downgrade() -> None:
    op.drop_table('profile_capabilities')
