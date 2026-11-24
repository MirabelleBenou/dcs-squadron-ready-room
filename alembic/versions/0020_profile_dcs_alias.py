"""profile_dcs_alias -- Lot « Le nom qu'on retient » v0.9917, Geste ①.

Table des noms retenus : rattache un SEGMENT de callsign ACMI (`_extract_
name_segment()`, engine.py) à un profil, de façon durable et automatique.
Alimentée par `POST /sessions/{id}/flights/{flight_id}/identify` (désigner
un membre retient aussi son nom pour ses prochains vols, brief §1/§6),
consultée par `_attach_profiles_by_name()` en premier, avant la règle de
segment existante (brief §4, Geste ②).

`alias_segment` UNIQUE : l'unicité est en base, pas dans le code (brief
§3) -- le jour où deux membres réclament le même nom, la contrainte
refuse le doublon (porte P2), pas une vérification Python. Normalisé en
minuscules à l'écriture (`_record_alias()`, `app/debrief/api.py`),
jamais en base (pas d'index fonctionnel `lower()` ici : la valeur est
déjà stockée normalisée, contrairement à `campaign.name`/migration 0012
qui, elle, indexe `lower(name)` parce que la casse d'origine devait être
préservée pour l'affichage -- ce n'est pas le cas ici, le segment ne
s'affiche jamais tel quel).

`profile_id` : suppression en cascade (brief §3) -- un profil supprimé
n'a plus de sens à retenir un nom, la ligne part avec lui.

Revision ID: 0020
Revises: 0019
Create Date: 2026-08-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0020'
down_revision: Union[str, None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'profile_dcs_alias',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('alias_segment', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['profile_id'], ['profiles.id'], ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alias_segment', name='uq_profile_dcs_alias_segment'),
    )
    op.create_index(
        'ix_profile_dcs_alias_profile_id', 'profile_dcs_alias', ['profile_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_profile_dcs_alias_profile_id', table_name='profile_dcs_alias')
    op.drop_table('profile_dcs_alias')
