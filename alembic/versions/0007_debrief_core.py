"""debrief core -- module Debriefing (Lot D1) : debrief_session,
debrief_upload, debrief_flight, debrief_event, debrief_graveyard,
debrief_unit_category. Cf. SPEC_READY_ROOM_Debrief_Fusion_v1 (v1.1) et
BRIEF_SONNET_ReadyRoom_Debrief_D1_data_engine §1.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0007'
down_revision: Union[str, None] = '0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'debrief_session',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('mission_date', sa.Date(), nullable=True),
        sa.Column('reference_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_s', sa.Integer(), nullable=True),
        sa.Column('acmi_present', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'debrief_upload',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('kind', sa.Text(), nullable=False),
        sa.Column('depositor_profile_id', sa.BigInteger(), nullable=True),
        sa.Column('filename', sa.Text(), nullable=False),
        sa.Column('sha256', sa.Text(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('raw_stored_path', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['debrief_session.id']),
        sa.ForeignKeyConstraint(['depositor_profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sha256', name='uq_debrief_upload_sha256'),
    )
    op.create_index(
        'ix_debrief_upload_session_id', 'debrief_upload', ['session_id'], unique=False
    )

    op.create_table(
        'debrief_flight',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('object_id', sa.Text(), nullable=True),
        sa.Column('acmi_track_id', sa.Text(), nullable=True),
        sa.Column('aircraft_type', sa.Text(), nullable=False),
        sa.Column('coalition', sa.Text(), nullable=True),
        sa.Column('pilote_profile_id', sa.BigInteger(), nullable=True),
        sa.Column('pilot_callsign', sa.Text(), nullable=True),
        sa.Column('identity_state', sa.Text(), nullable=False),
        sa.Column('identity_source', sa.Text(), nullable=True),
        sa.Column('t_start', sa.Float(), nullable=True),
        sa.Column('t_end', sa.Float(), nullable=True),
        sa.Column('slot_mission', sa.Text(), nullable=True),
        sa.Column('mission_id_dcs', sa.Text(), nullable=True),
        sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['debrief_session.id']),
        sa.ForeignKeyConstraint(['pilote_profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_debrief_flight_session_id', 'debrief_flight', ['session_id'], unique=False
    )
    op.create_index(
        'ix_debrief_flight_session_object',
        'debrief_flight',
        ['session_id', 'object_id'],
        unique=False,
    )

    op.create_table(
        'debrief_event',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('type', sa.Text(), nullable=False),
        sa.Column('t', sa.Float(), nullable=False),
        sa.Column('initiator_object_id', sa.Text(), nullable=True),
        sa.Column('target_object_id', sa.Text(), nullable=True),
        sa.Column('initiator_unit_type', sa.Text(), nullable=True),
        sa.Column('target_unit_type', sa.Text(), nullable=True),
        sa.Column('weapon', sa.Text(), nullable=True),
        sa.Column('seen_in', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('event_id_by_upload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('linked_event_id_by_upload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['debrief_session.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_debrief_event_session_initiator',
        'debrief_event',
        ['session_id', 'initiator_object_id'],
        unique=False,
    )
    op.create_index(
        'ix_debrief_event_session_target',
        'debrief_event',
        ['session_id', 'target_object_id'],
        unique=False,
    )
    op.create_index(
        'ix_debrief_event_session_type', 'debrief_event', ['session_id', 'type'], unique=False
    )

    op.create_table(
        'debrief_graveyard',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('unit_type', sa.Text(), nullable=False),
        sa.Column('coalition', sa.Text(), nullable=True),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('alt', sa.Float(), nullable=True),
        sa.Column('heading', sa.Float(), nullable=True),
        sa.Column('seen_in', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['debrief_session.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_debrief_graveyard_session_id', 'debrief_graveyard', ['session_id'], unique=False
    )

    op.create_table(
        'debrief_unit_category',
        sa.Column('unit_type', sa.Text(), nullable=False),
        sa.Column('display_name', sa.Text(), nullable=True),
        sa.Column('category', sa.Text(), nullable=False),
        sa.Column('resolved_from', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('unit_type'),
    )


def downgrade() -> None:
    op.drop_table('debrief_unit_category')

    op.drop_index('ix_debrief_graveyard_session_id', table_name='debrief_graveyard')
    op.drop_table('debrief_graveyard')

    op.drop_index('ix_debrief_event_session_type', table_name='debrief_event')
    op.drop_index('ix_debrief_event_session_target', table_name='debrief_event')
    op.drop_index('ix_debrief_event_session_initiator', table_name='debrief_event')
    op.drop_table('debrief_event')

    op.drop_index('ix_debrief_flight_session_object', table_name='debrief_flight')
    op.drop_index('ix_debrief_flight_session_id', table_name='debrief_flight')
    op.drop_table('debrief_flight')

    op.drop_index('ix_debrief_upload_session_id', table_name='debrief_upload')
    op.drop_table('debrief_upload')

    op.drop_table('debrief_session')
