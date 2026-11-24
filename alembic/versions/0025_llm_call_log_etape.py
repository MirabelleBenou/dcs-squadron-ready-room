"""Lot « Le français source unique » §2⑥ (brief, cadrage R125) -- « le
journal des appels distingue rédaction et traduction ». Une colonne
additive pure :

- `etape` sur `llm_call_log` : 'redaction' | 'traduction', NULLABLE. Les
  40 lignes déjà écrites au 10 septembre 2026 restent sans valeur --
  honnête, on ne sait pas rétroactivement ce qu'elles étaient.

Sans ce geste, une traduction à ~1500 jetons et une rédaction à ~15000
portent la même étiquette `langue = 'en'`, et toute moyenne tirée de ce
journal serait fausse.

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0025'
down_revision: Union[str, None] = '0024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'llm_call_log',
        sa.Column('etape', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('llm_call_log', 'etape')
