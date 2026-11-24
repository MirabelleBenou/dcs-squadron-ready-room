"""Lot « Polish du Centre ». La table `command_journal` : le journal des
modifications du Centre de Commandement. Une ligne par écriture du Centre qui
a changé quelque chose : qui (`par_id`), quand (`fait_le`), quoi (`action`),
sur quel objet (`objet`, nul quand l'écriture n'en a pas) et le détail, l'avant
et l'après (`lignes`, une liste JSON). Lue par l'écran Archives, pour un
administrateur seul.

`fait_le` prend l'heure de PostgreSQL (`now()`) ; `lignes` vaut `[]` par défaut.
La table naît vide : aucun semis, rien à reprendre.

Réversible : la descente retire la table.

Revision ID: 0036
Revises: 0035
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0036'
down_revision: Union[str, None] = '0035'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'command_journal',
        sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            'fait_le',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('par_id', sa.BigInteger(), nullable=False),
        sa.Column('action', sa.Text(), nullable=False),
        sa.Column('objet', sa.Text(), nullable=True),
        sa.Column(
            'lignes',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['par_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('command_journal')
