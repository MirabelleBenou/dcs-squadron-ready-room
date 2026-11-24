"""Une escadrille administrable (lot 3.2e, volet ①) -- pose un index
unique PARTIEL sur `squadron.discord_role_id`, restreint aux escadrilles
ACTIVES : `UNIQUE (discord_role_id) WHERE discord_role_id IS NOT NULL AND
status = 'actif'`. Idiome existant : `ux_squadron_membership_open_per_
profile` (migration 0011), même construction (`postgresql_where`).

Sans lui, deux escadrilles actives pourraient porter le même rôle
Discord et le rattachement des membres deviendrait silencieusement
arbitraire -- `_resolve_squadron_id()` (app/squadron.py) prend la
PREMIÈRE dans l'ordre des `id`, et personne ne s'en apercevrait avant de
compter un effectif. Deux escadrilles peuvent partager un rôle SI l'une
des deux est en sommeil (`discord_role_id IS NULL` dans ce cas, donc
hors index de toute façon) -- seule la coexistence de deux ACTIVES sur
le même rôle est rejetée.

Aucune colonne neuve : le modèle `Squadron` reste à six colonnes (cf.
brief §4.1).

Cf. BRIEF_SONNET_ReadyRoom_Lot_3_2e_Volet1.md, §4.1.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0016'
down_revision: Union[str, None] = '0015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ux_squadron_discord_role_id_actif',
        'squadron',
        ['discord_role_id'],
        unique=True,
        postgresql_where=sa.text(
            "discord_role_id IS NOT NULL AND status = 'actif'"
        ),
    )


def downgrade() -> None:
    # L'index tombe, rien d'autre -- aucune donnée détruite.
    op.drop_index('ux_squadron_discord_role_id_actif', table_name='squadron')
