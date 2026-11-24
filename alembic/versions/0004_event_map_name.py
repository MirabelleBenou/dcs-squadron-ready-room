"""event map_name -- events.map_name (text, nullable), liste fermee MAPS
(12) miroir front/backend. Exclusivite mutuelle game_label/map_name selon
le type de l'evenement geree cote application (app/events.py), pas en
base. Cf. BRIEF_SONNET_ReadyRoom_v0.23 §1.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('map_name', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('events', 'map_name')
