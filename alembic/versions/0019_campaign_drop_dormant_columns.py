"""Lot 3.4 « Campagnes », §4 -- SUPPRIME trois colonnes dormantes de
`campaign` : `conflict`, `started_on`, `ended_on`. Elles n'ont jamais été
saisies, affichées, ni validées au-delà de leur type depuis leur création
(migration 0012, lot 2.3) -- posées à l'époque parce que le cadrage CC
§5.5 exigeait que l'entité soit conçue en les sachant possibles. Le lot
3.4 tranche : cinq champs devient deux, dans les DEUX sens (formulaire ET
base). `description` et `map_name` sont CONSERVÉES -- seules trois des
cinq colonnes dormantes du lot 2.3 partent ici.

Arbitrage du porteur du 22 août, dans ses termes : « ça sera propre et
évitera les quiproquos ». Précédent direct : la migration 0013 avait déjà
retiré une colonne sans emploi.

Sans rapport avec l'indicateur de conflit de rattachement du pipeline de
dépôt (`debrief/engine.py` + `app.js`, nom de variable distinct portant
"campaign" et "conflict" accolés) ni avec la clause SQL d'upsert Postgres
(quatre fichiers) -- deux homonymes de surface qui ne portent AUCUNE des
trois colonnes supprimées ici. Cf. BRIEF_SONNET_ReadyRoom_Lot_3_4.md, §4.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0019'
down_revision: Union[str, None] = '0018'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ordre alphabétique arbitraire, sans portée fonctionnelle -- les
    # trois colonnes sont indépendantes, aucune contrainte ne les lie
    # entre elles ni à un index (l'index d'unicité ne porte que sur
    # `sim`/`lower(name)`, migration 0012, non concerné).
    op.drop_column('campaign', 'conflict')
    op.drop_column('campaign', 'started_on')
    op.drop_column('campaign', 'ended_on')


def downgrade() -> None:
    # Réversible SEULEMENT au sens du schéma -- les trois colonnes
    # redeviennent NULL partout, aucune donnée n'est restituée (elle a
    # été détruite à l'upgrade). Mêmes types exacts qu'à la création
    # (migration 0012) : Text/Date, nullable, sans défaut.
    op.add_column('campaign', sa.Column('conflict', sa.Text(), nullable=True))
    op.add_column('campaign', sa.Column('started_on', sa.Date(), nullable=True))
    op.add_column('campaign', sa.Column('ended_on', sa.Date(), nullable=True))
