"""Lot « La connexion de secours » (R325). La table `login_links` : les liens
d'entrée à usage unique qui ouvrent une session quand la connexion par Discord
ne passe pas -- émis par la commande `/readyroom` (`source = 'discord'`, 5
minutes) ou par un administrateur au Centre de Commandement (`source =
'admin'`, 24 heures).

`token_hash` est le SHA-256 hexadécimal du jeton, unique : le jeton lui-même
n'est jamais stocké. `profile_id` suit le profil (`ON DELETE CASCADE`),
`created_by` l'administrateur émetteur (`ON DELETE SET NULL`, nul pour
`discord`). `expires_at` et `used_at` se posent en Python.

La table naît vide : aucun semis.

Réversible : la descente retire l'index, la table, puis le type énuméré.

Revision ID: 0038
Revises: 0037
Create Date: 2026-10-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0038'
down_revision: Union[str, None] = '0037'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'login_links',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column(
            'source',
            sa.Enum('discord', 'admin', name='login_link_source'),
            nullable=False,
        ),
        sa.Column('created_by', sa.BigInteger(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['profile_id'], ['profiles.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['created_by'], ['profiles.id'], ondelete='SET NULL'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash', name='uq_login_links_token_hash'),
    )
    op.create_index('ix_login_links_profile_id', 'login_links', ['profile_id'])


def downgrade() -> None:
    op.drop_index('ix_login_links_profile_id', table_name='login_links')
    op.drop_table('login_links')
    op.execute('DROP TYPE login_link_source')
