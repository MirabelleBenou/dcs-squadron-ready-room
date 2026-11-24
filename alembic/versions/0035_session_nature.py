"""Lot « Mission ou training » : une session porte une nature. La table
`debrief_session` gagne la colonne `nature`, un type énuméré PostgreSQL
`session_nature` (`mission` · `training`), NOT NULL, de valeur par défaut
`mission` : toutes les sessions existantes sont des missions.

Le moteur ne change pas (`ENGINE_REVISION` inchangée) : aucune session ne se
recalcule, la nature se pose dans la route de dépôt, après l'ingestion.

Montée : le type est créé, la colonne ajoutée.
Descente : la colonne est retirée, puis le type.

Revision ID: 0035
Revises: 0034
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0035'
down_revision: Union[str, None] = '0034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    nature = postgresql.ENUM('mission', 'training', name='session_nature')
    nature.create(op.get_bind(), checkfirst=False)
    op.add_column(
        'debrief_session',
        sa.Column(
            'nature',
            postgresql.ENUM('mission', 'training', name='session_nature', create_type=False),
            nullable=False,
            server_default='mission',
        ),
    )


def downgrade() -> None:
    op.drop_column('debrief_session', 'nature')
    op.execute("DROP TYPE session_nature")
