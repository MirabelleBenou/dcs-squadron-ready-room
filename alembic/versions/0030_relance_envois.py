"""Lot « Les relances » (R6). La table `relance_envois` : chaque MP de
relance se note, un envoi par couple (destinataire, pilote signalé) avec le
statut du MP -- `envoye`, `refuse` (Discord 403, code 50007) ou `echec`. Elle
sert à ne signaler un pilote qu'une fois à chacun (R4).

`envoye_le` n'a AUCUN défaut SQL : il se pose en Python, parce que le banc
fige l'heure de Python alors que celle de PostgreSQL avance.

Le réglage des rôles destinataires, lui, ne demande aucune migration : il
vit dans `role_capabilities` (capacité `relances.destinataire`).

Réversible : la descente retire l'index, la table, puis le type énuméré.

Revision ID: 0030
Revises: 0029
Create Date: 2026-10-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0030'
down_revision: Union[str, None] = '0029'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'relance_envois',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('destinataire_id', sa.BigInteger(), nullable=False),
        sa.Column('pilote_id', sa.BigInteger(), nullable=False),
        sa.Column('envoye_le', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'statut',
            sa.Enum('envoye', 'refuse', 'echec', name='relance_statut'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['destinataire_id'], ['profiles.id']),
        sa.ForeignKeyConstraint(['pilote_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_relance_envois_dest_pilote',
        'relance_envois',
        ['destinataire_id', 'pilote_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_relance_envois_dest_pilote', table_name='relance_envois')
    op.drop_table('relance_envois')
    op.execute('DROP TYPE relance_statut')
