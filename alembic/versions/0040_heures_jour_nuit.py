"""Lot « Les heures de jour et de nuit » (v1.0068, le porteur, 4 novembre). Trois
colonnes, aucune table neuve :

- `debrief_session.horloge_mission_s` : `FLOAT`, nul permis -- l'heure du jour
  de la mission à `t = 0`, en secondes ;
- `debrief_flight.periode` : texte, nul permis, contraint à `'jour'` ou
  `'nuit'` -- la période que calcule le moteur ;
- `debrief_flight.periode_corrigee` : texte, nul permis, mêmes valeurs -- la
  correction à la main, que le moteur ne touche jamais.

Les lignes existantes restent nulles ; le recalcul du démarrage remplit
`horloge_mission_s` et `periode`. Aucune ligne supprimée.

Réversible : la descente retire les deux contraintes et les trois colonnes.

Revision ID: 0040
Revises: 0039
Create Date: 2026-11-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0040'
down_revision: Union[str, None] = '0039'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('debrief_session', sa.Column('horloge_mission_s', sa.Float(), nullable=True))
    op.add_column('debrief_flight', sa.Column('periode', sa.Text(), nullable=True))
    op.add_column('debrief_flight', sa.Column('periode_corrigee', sa.Text(), nullable=True))
    op.create_check_constraint(
        'ck_debrief_flight_periode',
        'debrief_flight',
        "periode IN ('jour','nuit')",
    )
    op.create_check_constraint(
        'ck_debrief_flight_periode_corrigee',
        'debrief_flight',
        "periode_corrigee IN ('jour','nuit')",
    )


def downgrade() -> None:
    op.drop_constraint('ck_debrief_flight_periode_corrigee', 'debrief_flight', type_='check')
    op.drop_constraint('ck_debrief_flight_periode', 'debrief_flight', type_='check')
    op.drop_column('debrief_flight', 'periode_corrigee')
    op.drop_column('debrief_flight', 'periode')
    op.drop_column('debrief_session', 'horloge_mission_s')
