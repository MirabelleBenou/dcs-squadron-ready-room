"""Lot « Le rattachement des dépôts » (v1.0052, R326). La provenance d'un
fichier déposé : quatre colonnes sur `debrief_upload`, aucune table neuve.

- `rattachement` : texte non nul, `'titre'` par défaut (serveur), contraint à
  `'titre'`, `'contenu'` ou `'manuel'` -- comment le fichier a rejoint sa
  session ;
- `entete_titre` : texte, nul permis -- le titre tiré de l'en-tête au dépôt ;
- `entete_exemple` : booléen non nul, `false` par défaut (serveur) -- l'en-tête
  désigne une mission d'exemple de DCS ;
- `deplace_par_profile_id` : `BIGINT`, clé étrangère `profiles.id`, nul permis
  -- qui l'a déplacé à la main.

Les lignes existantes prennent les défauts ; aucun fichier ne se relit sur
disque.

Réversible : la descente retire la contrainte, la clé étrangère et les quatre
colonnes.

Revision ID: 0039
Revises: 0038
Create Date: 2026-10-27
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0039'
down_revision: Union[str, None] = '0038'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'debrief_upload',
        sa.Column('rattachement', sa.Text(), server_default='titre', nullable=False),
    )
    op.add_column('debrief_upload', sa.Column('entete_titre', sa.Text(), nullable=True))
    op.add_column(
        'debrief_upload',
        sa.Column('entete_exemple', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    )
    op.add_column(
        'debrief_upload', sa.Column('deplace_par_profile_id', sa.BigInteger(), nullable=True)
    )
    op.create_check_constraint(
        'ck_debrief_upload_rattachement',
        'debrief_upload',
        "rattachement IN ('titre','contenu','manuel')",
    )
    op.create_foreign_key(
        'fk_debrief_upload_deplace_par_profile_id',
        'debrief_upload', 'profiles',
        ['deplace_par_profile_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_debrief_upload_deplace_par_profile_id', 'debrief_upload', type_='foreignkey')
    op.drop_constraint('ck_debrief_upload_rattachement', 'debrief_upload', type_='check')
    op.drop_column('debrief_upload', 'deplace_par_profile_id')
    op.drop_column('debrief_upload', 'entete_exemple')
    op.drop_column('debrief_upload', 'entete_titre')
    op.drop_column('debrief_upload', 'rattachement')
