"""discord digest message singleton -- table discord_digest_message (id=1
unique) pour le digest Discord evergreen : message_id courant, file
pending_delete (retry), fenetre week_monday/window_end. Cf.
BRIEF_SONNET_ReadyRoom_v0.22 §1.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'discord_digest_message',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.Text(), nullable=True),
        sa.Column(
            'pending_delete',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='[]',
        ),
        sa.Column('week_monday', sa.Date(), nullable=True),
        sa.Column('window_end', sa.Date(), nullable=True),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('discord_digest_message')
