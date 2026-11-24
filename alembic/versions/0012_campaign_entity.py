"""La campagne en entité (Phase 2, lot 2.3, dernier lot de la phase) -- crée
le type énuméré `campaign_status`, la table `campaign` et son index
fonctionnel d'unicité insensible à la casse (`sim`, `lower(name)`), puis la
colonne `debrief_session.campaign_id` (nullable, sans valeur par défaut).

Sans rapport avec `EventType.campagne` (app/models.py:33, Planification) :
les deux objets « Campagne » coexistent sans parenté (brief §2), la
charnière est en phase 7.

Aucun semis (brief §4.3) : il n'existe aucune source de données à reprendre
-- ni `.env`, ni colonne, ni table. La table naît vide, et c'est correct.

Cf. BRIEF_SONNET_LOT_2_3_Campagne_en_entite.md, §3/§4.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0012'
down_revision: Union[str, None] = '0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 1. campaign ---------------------------------------------------------
    # DEUX statuts seulement (brief §3), `id` en UUID -- contrairement à
    # `squadron` (entier), aucune règle de résolution "première
    # correspondance dans l'ordre de la table" ici : on suit la convention
    # UUID de la couche débrief.
    op.create_table(
        'campaign',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('conflict', sa.Text(), nullable=True),
        sa.Column('map_name', sa.Text(), nullable=True),
        sa.Column('started_on', sa.Date(), nullable=True),
        sa.Column('ended_on', sa.Date(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('en_cours', 'close', name='campaign_status'),
            nullable=False,
        ),
        sa.Column('sim', sa.Text(), nullable=False, server_default='dcs'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    # Fonctionnel, insensible à la casse (brief §3) : deux campagnes de même
    # nom à la casse près, sur le même simulateur, sont refusées ; sur deux
    # simulateurs différents, acceptées.
    op.execute(
        "CREATE UNIQUE INDEX ux_campaign_sim_lower_name "
        "ON campaign (sim, lower(name))"
    )

    # --- 2. debrief_session.campaign_id --------------------------------------
    # Nullable, et c'est un état normal, pas un défaut -- spec Carrière §6 :
    # "sessions hors campagne = état normal". Aucune valeur par défaut,
    # aucun rattachement automatique.
    op.add_column(
        'debrief_session',
        sa.Column('campaign_id', sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        'fk_debrief_session_campaign_id',
        'debrief_session',
        'campaign',
        ['campaign_id'],
        ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_debrief_session_campaign_id', 'debrief_session', type_='foreignkey'
    )
    op.drop_column('debrief_session', 'campaign_id')

    op.execute("DROP INDEX ux_campaign_sim_lower_name")
    op.drop_table('campaign')
    op.execute("DROP TYPE campaign_status")
