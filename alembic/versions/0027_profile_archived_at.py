"""Lot « L'appel » -- l'effectif suit Discord (R183 à R185). Une colonne
additive pure :
- `archived_at` sur `profiles` : la date à laquelle l'appel a trouvé le
  profil hors de l'effectif -- ni rôle d'escadrille active, ni droit de
  connexion. NULLABLE : un profil de l'effectif n'en porte pas. Archiver,
  c'est dater (R184) : rien d'autre ne bouge, vols, sessions et présences
  restent attachés.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0027'
down_revision: Union[str, None] = '0026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'profiles',
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('profiles', 'archived_at')
