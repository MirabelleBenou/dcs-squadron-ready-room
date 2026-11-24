"""Lot « rr-socle-proprete » (v1.0111) : trois index sur des clés étrangères lues en filtre
(constats ARC-25 et ARC-32 de l'audit du code).

`ix_debrief_flight_pilote_profile_id` (`debrief_flight.pilote_profile_id`),
`ix_debrief_session_campaign_id` (`debrief_session.campaign_id`) et
`ix_relance_envois_pilote_id` (`relance_envois.pilote_id`). Les modèles les déclarent
(`index=True`) : `alembic check` reste propre.

Additive. Réversible : la descente retire les trois index.

Revision ID: 0046
Revises: 0045
Create Date: 2026-11-23
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0046'
down_revision: Union[str, None] = '0045'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_debrief_flight_pilote_profile_id', 'debrief_flight', ['pilote_profile_id']
    )
    op.create_index('ix_debrief_session_campaign_id', 'debrief_session', ['campaign_id'])
    op.create_index('ix_relance_envois_pilote_id', 'relance_envois', ['pilote_id'])


def downgrade() -> None:
    op.drop_index('ix_relance_envois_pilote_id', table_name='relance_envois')
    op.drop_index('ix_debrief_session_campaign_id', table_name='debrief_session')
    op.drop_index('ix_debrief_flight_pilote_profile_id', table_name='debrief_flight')
