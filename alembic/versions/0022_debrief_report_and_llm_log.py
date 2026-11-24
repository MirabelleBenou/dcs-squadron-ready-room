"""Lot R2 -- « la porte, la rédaction, le rendu » (brief §4, cadrage
R78-R81). Deux tables neuves, additives pures, aucune reprise de données :

- `debrief_report` : UN rapport par session (session_id en clé primaire --
  l'unicité est la contrainte elle-même), remplacé à la réécriture, jamais
  d'historique (R81). `texte_fr`/`texte_en` nullables indépendamment tant
  qu'ils n'ont jamais été rédigés avec succès. `report_facts_sha` capturé
  au moment de la rédaction (cadrage §6) -- le prédicat de divergence
  n'est PAS stocké, recalculé à la lecture.

- `llm_call_log` : journal d'appel de la porte unique (app/llm.py) --
  une ligne par appel TENTÉ, y compris échecs et refus de plafond (brief
  §3). Sert aussi de compteur en base pour les deux plafonds (mensuel,
  par session) -- jamais de compteur en mémoire de processus.

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0022'
down_revision: Union[str, None] = '0021'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'debrief_report',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('texte_fr', sa.Text(), nullable=True),
        sa.Column('texte_en', sa.Text(), nullable=True),
        sa.Column('report_facts_sha', sa.Text(), nullable=False),
        sa.Column('redige_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('auteur_profile_id', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['debrief_session.id']),
        sa.ForeignKeyConstraint(['auteur_profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('session_id'),
    )

    op.create_table(
        'llm_call_log',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('called_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('langue', sa.Text(), nullable=True),
        sa.Column('model', sa.Text(), nullable=True),
        sa.Column('tokens_in', sa.Integer(), nullable=True),
        sa.Column('tokens_out', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('verdict', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['debrief_session.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_llm_call_log_session_id', 'llm_call_log', ['session_id'], unique=False
    )
    op.create_index(
        'ix_llm_call_log_called_at', 'llm_call_log', ['called_at'], unique=False
    )


def downgrade() -> None:
    op.drop_index('ix_llm_call_log_called_at', table_name='llm_call_log')
    op.drop_index('ix_llm_call_log_session_id', table_name='llm_call_log')
    op.drop_table('llm_call_log')
    op.drop_table('debrief_report')
