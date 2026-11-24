"""profile last_seen -- ajoute profiles.last_seen_at, horodatage de derniere
visite utilise pour le tag "NOUVEAU" (evenements postes depuis la derniere
visite du pilote). Distinct de last_login_at (auth). Cf. POST /api/seen
dans app/api.py et SINCE/isNewOcc dans app/static/app.js (v0.36).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "profiles",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profiles", "last_seen_at")
