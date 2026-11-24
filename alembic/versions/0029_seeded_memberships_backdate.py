"""Lot « L'identité de l'escadrille » (R188). Correction de données, une
fois : les appartenances semées ensemble par la migration 0011 à son
déploiement -- le 13 août 2026 en production, 14 lignes à la même heure --
prennent pour entrée le jour de la première mission. Elles valaient depuis
le début de l'historique : sans cette correction, la moitié des vols
identifiés tombait hors de toute escadrille (sonde du 30 septembre).

Le lot semé se reconnaît sans date écrite en dur : le PREMIER groupe d'au
moins deux appartenances insérées à la même heure exacte -- 0011 les a
toutes écrites avec un seul `now()`. Sans mission déposée, ou si la
première mission ne précède pas ce groupe, rien ne bouge.

Non réversible : la descente ne fait rien. L'heure du semis n'était pas
une date d'entrée, et elle n'est pas conservée.

Revision ID: 0029
Revises: 0028
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0029'
down_revision: Union[str, None] = '0028'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH graine AS (
            SELECT started_at FROM squadron_membership
            GROUP BY started_at HAVING count(*) >= 2
            ORDER BY started_at LIMIT 1
        ), debut AS (
            SELECT min(mission_date) AS d FROM debrief_session
        )
        UPDATE squadron_membership AS m
        SET started_at = debut.d::timestamptz
        FROM graine, debut
        WHERE m.started_at = graine.started_at
          AND debut.d IS NOT NULL
          AND debut.d < graine.started_at::date
        """
    )


def downgrade() -> None:
    # Correction de données non réversible -- voir la docstring.
    pass
