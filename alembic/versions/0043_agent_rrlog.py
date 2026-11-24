"""Lot « La réception du .rrlog de l'agent » (v1.0089) : deux tables.
`agent_jeton` porte le jeton de l'agent du serveur DCS (seule l'empreinte sha256
est gardée ; un seul jeton actif) ; `agent_rrlog` est le registre des fichiers
reçus, sans session (`session_id` vide, sans clé étrangère, que posera la lecture
par le Débrief).

Additive : aucune table existante ne change. Réversible : la descente retire
les deux tables, dans l'ordre inverse.

Revision ID: 0043
Revises: 0042
Create Date: 2026-11-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0043'
down_revision: Union[str, None] = '0042'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agent_jeton',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column('empreinte', sa.Text(), nullable=False),
        sa.Column(
            'emis_le',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('emis_par', sa.Text(), nullable=False),
        sa.Column('revoque_le', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dernier_envoi_le', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('empreinte'),
    )
    op.create_table(
        'agent_rrlog',
        sa.Column('id', sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column('sha256', sa.Text(), nullable=False),
        sa.Column('fichier', sa.Text(), nullable=False),
        sa.Column('chemin', sa.Text(), nullable=False),
        sa.Column('taille_gz', sa.BigInteger(), nullable=False),
        sa.Column('taille', sa.BigInteger(), nullable=False),
        sa.Column(
            'recu_le',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('jeton_id', sa.BigInteger(), nullable=False),
        sa.Column('format', sa.Integer(), nullable=True),
        sa.Column('agent_version', sa.Text(), nullable=True),
        sa.Column('mission', sa.Text(), nullable=True),
        sa.Column('theatre', sa.Text(), nullable=True),
        sa.Column('date_mission', sa.Text(), nullable=True),
        sa.Column('depart_reel', sa.Text(), nullable=True),
        sa.Column('etat', sa.Text(), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['jeton_id'], ['agent_jeton.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sha256'),
    )
    op.create_index('ix_agent_rrlog_recu_le', 'agent_rrlog', ['recu_le'])


def downgrade() -> None:
    op.drop_index('ix_agent_rrlog_recu_le', table_name='agent_rrlog')
    op.drop_table('agent_rrlog')
    op.drop_table('agent_jeton')
