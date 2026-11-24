"""Lot Fraîcheur v0.9939 -- une colonne nullable sur debrief_session :
stats_engine_rev (TEXT). Additive pure, pas de reprise de données, pas de
valeur par défaut -- même patron que la migration 0010. `NULL` signifie
"calculée avant que l'empreinte du moteur n'existe" : toutes les sessions
déjà en base sont donc périmées au premier démarrage après ce lot, et
c'est exactement voulu (brief §4). Le prédicat de péremption vit dans
`app/debrief/revision.py::is_stale()`, jamais ici.

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0021'
down_revision: Union[str, None] = '0020'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "debrief_session",
        sa.Column("stats_engine_rev", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("debrief_session", "stats_engine_rev")
