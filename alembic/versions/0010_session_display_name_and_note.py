"""Nommage des missions et note pour l'escadre (Phase 2, lot 2.1) -- deux
colonnes nullables sur debrief_session : display_name (nom saisi au dépôt,
modifiable ensuite) et wing_note (note libre pour l'escadre). Additive pure,
pas de reprise de données, pas de valeur par défaut. `title` (technique,
dérivé, rattachement des dépôts) n'est pas touché -- cf. brief §2/§4.1.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0010'
down_revision: Union[str, None] = '0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "debrief_session",
        sa.Column("display_name", sa.Text(), nullable=True),
    )
    op.add_column(
        "debrief_session",
        sa.Column("wing_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("debrief_session", "wing_note")
    op.drop_column("debrief_session", "display_name")
