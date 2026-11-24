"""debrief session sim -- dimension simulateur (D2 lot 1) : colonne sim
sur debrief_session, defaut 'dcs', backfill des lignes existantes.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0008'
down_revision: Union[str, None] = '0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "debrief_session",
        sa.Column("sim", sa.Text(), nullable=False, server_default="dcs"),
    )


def downgrade() -> None:
    op.drop_column("debrief_session", "sim")
