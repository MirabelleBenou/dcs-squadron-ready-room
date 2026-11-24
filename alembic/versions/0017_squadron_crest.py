"""Une escadrille reçoit son écusson (Lot 3.2e, volet ②) -- ajoute
`squadron.crest_sha` (`Text NULL`). `NULL` = aucun écusson posé.

Ce n'est pas un booléen : la colonne porte le sha256 du PNG normalisé
effectivement stocké (cf. app/crests.py). Elle sert deux choses à la
fois, et c'est délibéré -- elle dit qu'il y a un écusson, ET elle casse
le cache du navigateur au remplacement. Le fichier vit à un chemin FIXE
(`{squadron_id}.png`, cf. brief §6.5) ; sans cette empreinte dans l'URL de
lecture (`GET /api/squadrons/{id}/crest?v={crest_sha}`), un chef qui
remplace son écusson continuerait à voir l'ancien pendant des jours.

Aucune autre colonne, aucun index : `crest_sha` n'est contrainte par
rien d'autre que sa nullabilité -- deux escadrilles pourraient en théorie
partager le même sha256 (deux chefs déposant le même fichier), ce n'est
pas un conflit.

Cf. BRIEF_SONNET_ReadyRoom_Lot_3_2e_Volet2.md, §5.1.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0017'
down_revision: Union[str, None] = '0016'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "squadron",
        sa.Column("crest_sha", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # La colonne tombe, rien d'autre -- aucune donnée métier détruite (les
    # fichiers PNG restent sur le volume `crests`, orphelins de la base).
    op.drop_column("squadron", "crest_sha")
