"""La liste des rôles Discord qui ouvrent la connexion passe sous
l'autorité de l'application (Phase 3, lot 3.2d, second temps) -- une
seule capacité neuve, `app.access`, dans `role_capabilities`. Aucune
table, aucune colonne, aucun index : `role_capabilities` porte déjà
`(role_id, capability)` en clé primaire, sans contrainte `CHECK` sur
`capability` (en poser une est une condition d'arrêt du brief, cf.
§4).

Elle semait aussi, conditionnellement (idiome A-3), une ligne `(role_id, 'app.access')`
pour chaque identifiant de `ALLOWED_ROLE_IDS` : semis retiré au v1.0111 : la variable
n'est plus lue depuis le v1.0105. La migration ne change plus rien aux données ; base
muette sur `app.access` = personne hors administrateurs (`app/auth.py`).

Cf. BRIEF_SONNET_ReadyRoom_Lot_3_2d_Second_Temps.md, §4.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-19

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '0015'
down_revision: Union[str, None] = '0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Aucun DDL, aucune donnée : le semis depuis `ALLOWED_ROLE_IDS` est retiré (v1.0111).
    pass


def downgrade() -> None:
    # Aucun DDL à défaire (aucune table, colonne ou index créés à l'upgrade).
    pass
