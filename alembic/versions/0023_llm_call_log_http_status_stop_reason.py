"""Correctif R2e §3 -- « le journal doit pouvoir expliquer ». Deux colonnes
additives, toutes deux nullables, sur `llm_call_log` :

- `http_status` : le statut HTTP de la réponse, quand une réponse a été
  reçue (`None` si la tentative n'a jamais atteint le réseau, ou si le
  transport a échoué avant réception d'une réponse).
- `stop_reason` : le `stop_reason` rapporté par le fournisseur, quand le
  corps de la réponse a pu être lu comme JSON exploitable.

Objectif : l'ancien verdict unique `echec_http` recouvrait trois causes
distinctes (429/5xx après reprise, statut différent de 200, statut 200
sans texte exploitable) sans que rien ne permette de les distinguer a
posteriori. Ce lot scinde le verdict en `app/llm.py` (renommage pur,
aucune décision changée) et ajoute ces deux colonnes d'observation pour
que la cause soit lisible directement en base, sans script ad hoc.

Aucune clé d'API, aucun en-tête, aucun fragment de requête : uniquement
le statut et la raison d'arrêt.

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0023'
down_revision: Union[str, None] = '0022'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'llm_call_log',
        sa.Column('http_status', sa.Integer(), nullable=True),
    )
    op.add_column(
        'llm_call_log',
        sa.Column('stop_reason', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('llm_call_log', 'stop_reason')
    op.drop_column('llm_call_log', 'http_status')
