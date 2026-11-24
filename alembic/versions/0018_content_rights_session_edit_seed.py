"""Les droits sur le contenu (Phase 3, lot 3.3) -- aucune table, aucune
colonne, aucun index : `role_capabilities` porte déjà `(role_id,
capability)` en clé primaire, sans contrainte `CHECK` sur `capability`
(même précédent que la migration 0015 pour `app.access`). Les deux
capacités `session.edit` et `event.edit_any` existent déjà côté
résolution (`app/capabilities.py` : `can_edit_session()`,
`can_edit_event()`) -- ce lot leur donne enfin un écrivain d'interface
(écran Droits, bloc 5) et sème `session.edit` pour le rôle chef.

Semis conditionnel, idiome A-3 (mêmes précédents que les migrations
0011, 0014, 0015) -- exécute un arbitrage du porteur du 13 août resté
sans effet : les chefs d'escadrille font partie du groupe de
management, ils ont tous les droits sur toutes les escadrilles, borné à
la modification d'éléments de missions et de campagnes :

- si `role_capabilities` ne porte AUCUNE ligne `capability='session.edit'`
- et si un rôle chef est désigné (`role_capabilities` porte une ligne
  `capability='command.access'`)
- alors on insère `(rôle chef, 'session.edit')`
- sinon (table déjà non muette, OU aucun rôle chef désigné) : aucune
  insertion, aucune erreur.

AUCUN semis pour `event.edit_any` -- aucun arbitrage ne l'a demandé
(cf. BRIEF_SONNET_ReadyRoom_Lot_3_3.md, §3).

Cf. BRIEF_SONNET_ReadyRoom_Lot_3_3.md, §3.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-21

"""
import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0018'
down_revision: Union[str, None] = '0017'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    bind = op.get_bind()

    # Semis conditionnel (idiome A-3) -- aucun import différé requis ici
    # (contrairement aux migrations 0011/0014/0015) : la source du semis
    # est la base elle-même (`command.access`), jamais `.env`.
    session_edit_muette = bind.execute(
        sa.text(
            "SELECT 1 FROM role_capabilities WHERE capability = 'session.edit' LIMIT 1"
        )
    ).first() is None

    if not session_edit_muette:
        # La table a déjà quelque chose à dire sur `session.edit` : ne
        # rien faire, précédent exact 0011 / 0014 / 0015.
        return

    chef_role_id = bind.execute(
        sa.text(
            "SELECT role_id FROM role_capabilities WHERE capability = 'command.access' LIMIT 1"
        )
    ).scalar_one_or_none()

    if chef_role_id is None:
        logger.warning(
            "Migration 0018 : aucun rôle chef désigné ('command.access' muette) "
            "-- aucune ligne 'session.edit' semée. Comportement attendu, pas une "
            "erreur : le geste est possible plus tard depuis l'écran Droits."
        )
        return

    bind.execute(
        sa.text(
            "INSERT INTO role_capabilities (role_id, capability) "
            "VALUES (:rid, 'session.edit')"
        ),
        {"rid": chef_role_id},
    )


def downgrade() -> None:
    # Aucun DDL à défaire (aucune table, colonne ou index créés à
    # l'upgrade). `downgrade` ne défait PAS le semis -- une migration ne
    # peut pas distinguer une ligne semée d'une ligne saisie par un
    # humain depuis l'écran Droits (même raison qu'aux migrations 0014 et
    # 0015).
    pass
