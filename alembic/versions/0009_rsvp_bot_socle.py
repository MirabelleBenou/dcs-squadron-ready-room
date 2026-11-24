"""RSVP bot socle (Phase 2b, lot 2b-1) -- ajoute presences.created_at
(backfille = updated_at) et la table occurrence_messages (suivi des
messages Discord postes par occurrence).

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0009'
down_revision: Union[str, None] = '0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- presences.created_at (ordre d'inscription reel, dette (2), cf.
    # brief etape 5) -- additive, backfillee depuis updated_at pour les
    # lignes existantes (pas de "vrai" instant de creation connu avant ce
    # lot, updated_at est la meilleure approximation disponible).
    op.add_column(
        "presences",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute("UPDATE presences SET created_at = updated_at")

    # --- occurrence_messages (suivi message Discord <-> occurrence, cf.
    # brief etape 4.2). Pas de closed_at (D7 : fin de vie = suppression,
    # jamais de cloture conservee). channel_id/message_id en TEXT (cf.
    # DiscordDigestMessage.message_id, meme convention).
    op.create_table(
        "occurrence_messages",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occ_date", sa.Date(), nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("message_id", sa.Text(), nullable=False),
        sa.Column(
            "posted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("event_id", "occ_date"),
    )


def downgrade() -> None:
    op.drop_table("occurrence_messages")
    op.drop_column("presences", "created_at")
