"""squadron + rsvp prefs -- profiles.squadron (text, nullable),
presences.aircraft (jsonb, nullable), presences.mission_types (jsonb,
nullable). Cf. SPEC_READY_ROOM_Escadrilles_et_RSVP_v1 (recapitulatif migration
0002) et BRIEF_SONNET_ReadyRoom_Lot6_Escadrilles_RSVP.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('profiles', sa.Column('squadron', sa.Text(), nullable=True))
    op.add_column(
        'presences',
        sa.Column('aircraft', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        'presences',
        sa.Column(
            'mission_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column('presences', 'mission_types')
    op.drop_column('presences', 'aircraft')
    op.drop_column('profiles', 'squadron')
