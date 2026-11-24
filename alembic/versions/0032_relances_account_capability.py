"""Correctif « Les relances nominatives ». Les comptes destinataires des
relances rejoignent `account_capability`, la table des droits par compte que
portent déjà les éditeurs du planning (`event.create`) ; `profile_capabilities`
(migration 0031), qui la doublait, est reprise puis retirée.

Montée : chaque ligne de `profile_capabilities` passe dans `account_capability`
(même `profile_id`, même `capability`, `granted_by` nul, `granted_at` par
défaut) sans écraser une ligne existante, puis la table est retirée.

Descente : `profile_capabilities` est recréée telle que la crée 0031 ; les
lignes `relances.destinataire` d'`account_capability` y sont reprises, puis
retirées d'`account_capability`. Les lignes `event.create` ne bougent jamais.

Revision ID: 0032
Revises: 0031
Create Date: 2026-10-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0032'
down_revision: Union[str, None] = '0031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "INSERT INTO account_capability (profile_id, capability) "
        "SELECT profile_id, capability FROM profile_capabilities "
        "ON CONFLICT (profile_id, capability) DO NOTHING"
    )
    op.drop_table('profile_capabilities')


def downgrade() -> None:
    op.create_table(
        'profile_capabilities',
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('capability', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('profile_id', 'capability', name='profile_capabilities_pkey'),
    )
    op.execute(
        "INSERT INTO profile_capabilities (profile_id, capability) "
        "SELECT profile_id, capability FROM account_capability "
        "WHERE capability = 'relances.destinataire'"
    )
    op.execute("DELETE FROM account_capability WHERE capability = 'relances.destinataire'")
