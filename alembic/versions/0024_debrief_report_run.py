"""Lot R6 -- « la rédaction en tâche de fond ». Une table neuve, additive
pure :

- `debrief_report_run` : une ligne = une rédaction en vol. `session_id`
  en clé primaire -- l'unicité est la contrainte elle-même, et c'est ce
  qui rend l'atomicité de la pose gratuite (deux rédactions simultanées
  sur une même session deviennent impossibles par contrainte, pas par
  vigilance). La ligne est supprimée à la fin quel que soit le résultat
  (succès ou échec, cf. `finally` de la tâche de fond) ; la péremption
  (`REDACTION_PEREMPTION_MIN`, app/debrief/api.py) n'est qu'un filet pour
  le cas où le processus meurt avant d'atteindre ce `finally`.

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0024'
down_revision: Union[str, None] = '0023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'debrief_report_run',
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('lance_par_profile_id', sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['debrief_session.id']),
        sa.ForeignKeyConstraint(['lance_par_profile_id'], ['profiles.id']),
        sa.PrimaryKeyConstraint('session_id'),
    )


def downgrade() -> None:
    op.drop_table('debrief_report_run')
