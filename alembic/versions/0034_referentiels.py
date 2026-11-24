"""Lot « Les référentiels : types et armes ». La table des types vus,
`debrief_unit_category`, gagne deux colonnes nullables -- `libelle` (le nom que
la Ready Room affiche à la place de la clé DCS) et `categorie_forcee` (la
catégorie posée à la main ; NULL = automatique, celle de `categorize`). Une
table neuve, `referentiel_arme`, porte le libellé des noms d'arme : les armes
n'ont pas de table de « vues », on ne stocke que celles qui ont un libellé.

Aucun semis : la liste initiale s'importe par l'écran (JSON). Le moteur
n'écrit que les quatre colonnes d'origine de `debrief_unit_category`.

Montée : deux colonnes ajoutées, une table créée.
Descente : la table et les deux colonnes sont retirées.

Revision ID: 0034
Revises: 0033
Create Date: 2026-10-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0034'
down_revision: Union[str, None] = '0033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('debrief_unit_category', sa.Column('libelle', sa.Text(), nullable=True))
    op.add_column('debrief_unit_category', sa.Column('categorie_forcee', sa.Text(), nullable=True))
    op.create_table(
        'referentiel_arme',
        sa.Column('cle', sa.Text(), primary_key=True),
        sa.Column('libelle', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('referentiel_arme')
    op.drop_column('debrief_unit_category', 'categorie_forcee')
    op.drop_column('debrief_unit_category', 'libelle')
