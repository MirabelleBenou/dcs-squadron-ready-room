"""campagne + backfill -- ajoute 'campagne' a l'enum event_type et
backfill game_label='DCS' pour les mission/entrainement existants sans
plateforme renseignee (v0.26 : plateforme unifiee, cf. app/schemas.py
STRUCTURED_GAMES et app/events.py _enforce_game_map_rules).

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE event_type ADD VALUE IF NOT EXISTS 'campagne'")
    op.execute(
        "UPDATE events SET game_label='DCS' "
        "WHERE type IN ('mission', 'entrainement') AND game_label IS NULL"
    )


def downgrade() -> None:
    pass  # retrait d'une valeur d'enum PG non supporte ; backfill non reversible
