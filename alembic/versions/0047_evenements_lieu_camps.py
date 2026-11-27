"""Lot « La carte des destructions » (v1.1.0+2) : le lieu et les camps des évènements.

Trois colonnes de `debrief_event`, toutes `Text`, nullables, sans index : `place`
(le lieu nommé d'un décollage ou d'un atterrissage, tel que le journal le donne),
`initiator_coalition` et `target_coalition` (le camp de l'initiateur et celui de la
cible, encodage DCS validé par le moteur). Les modèles les déclarent : `alembic check`
reste propre. Les sessions déjà en base les reçoivent au recalcul du moteur.

Additive. Réversible : la descente retire les trois colonnes.

Revision ID: 0047
Revises: 0046
Create Date: 2026-11-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0047'
down_revision: Union[str, None] = '0046'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('debrief_event', sa.Column('place', sa.Text(), nullable=True))
    op.add_column('debrief_event', sa.Column('initiator_coalition', sa.Text(), nullable=True))
    op.add_column('debrief_event', sa.Column('target_coalition', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('debrief_event', 'target_coalition')
    op.drop_column('debrief_event', 'initiator_coalition')
    op.drop_column('debrief_event', 'place')
