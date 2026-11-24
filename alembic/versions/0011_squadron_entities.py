"""L'escadrille en donnée (Phase 2, lot 2.2b) -- crée l'escadre (`wing`),
l'escadrille (`squadron`) et l'appartenance datée (`squadron_membership`),
sème la seule ligne `wing` depuis `WING_TAG`, et pose
`role_capabilities.squadron_id` (nullable, inerte -- `has_capability()` n'est
PAS modifiée, la phase 3 l'active). Les semis des escadrilles et des
appartenances sont retirés au v1.0111 (la variable n'est plus lue depuis le
v1.0105).

`role_capabilities` porte aujourd'hui une clé primaire composite
`(role_id, capability)`. PostgreSQL n'acceptant pas de colonne nullable
dans une clé primaire, `squadron_id` est intégré à la clé via une clé
primaire de SUBSTITUTION : `squadron_scope`, colonne générée
(`COALESCE(squadron_id, 0)`, jamais 0 en pratique -- `squadron.id`
démarre à 1), qui remplace `squadron_id` dans la PK
`(role_id, capability, squadron_scope)`. Justification détaillée dans la
docstring de `RoleCapability` (app/models.py).

Cf. BRIEF_SONNET_LOT_2_2b_Escadrille_en_donnee.md, §3/§4.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0011'
down_revision: Union[str, None] = '0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- 1. wing -----------------------------------------------------------
    op.create_table(
        'wing',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('designation', sa.Text(), nullable=False),
        sa.Column('tag', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- 2. squadron ---------------------------------------------------------
    # DEUX statuts seulement -- "fermé" est un synonyme de "en sommeil"
    # (arbitrage du porteur du 11 août, cf. brief §3). `id` entier
    # auto-incrémenté (pas UUID) : la résolution exige la PREMIÈRE
    # correspondance "dans l'ordre de la table" (brief §5), qu'un entier
    # croissant garantit seul de façon déterministe (cf. app/models.py).
    op.create_table(
        'squadron',
        sa.Column('id', sa.Integer(), sa.Identity(), nullable=False),
        sa.Column('designation', sa.Text(), nullable=False),
        sa.Column('tag', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('actif', 'sommeil', name='squadron_status'),
            nullable=False,
        ),
        sa.Column('discord_role_id', sa.Text(), nullable=True),
        sa.Column('wing_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['wing_id'], ['wing.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- 3. squadron_membership ---------------------------------------------
    op.create_table(
        'squadron_membership',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('squadron_id', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id']),
        sa.ForeignKeyConstraint(['squadron_id'], ['squadron.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    # Au plus UNE appartenance ouverte par profil -- en base, pas
    # seulement dans le code (cf. brief §3).
    op.create_index(
        'ux_squadron_membership_open_per_profile',
        'squadron_membership',
        ['profile_id'],
        unique=True,
        postgresql_where=sa.text('ended_at IS NULL'),
    )

    # --- 4. role_capabilities : squadron_id + nouvelle PK -------------------
    op.add_column(
        'role_capabilities',
        sa.Column('squadron_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_role_capabilities_squadron_id',
        'role_capabilities',
        'squadron',
        ['squadron_id'],
        ['id'],
    )
    op.execute(
        "ALTER TABLE role_capabilities ADD COLUMN squadron_scope integer "
        "GENERATED ALWAYS AS (COALESCE(squadron_id, 0)) STORED"
    )
    op.execute("ALTER TABLE role_capabilities DROP CONSTRAINT role_capabilities_pkey")
    op.execute(
        "ALTER TABLE role_capabilities "
        "ADD CONSTRAINT role_capabilities_pkey "
        "PRIMARY KEY (role_id, capability, squadron_scope)"
    )

    # --- 5. semis : wing (une ligne, depuis WING_TAG) -----------------------
    # Import différé : évite tout effet de bord de `app.config` au chargement
    # d'Alembic lui-même (cohérent avec alembic/env.py qui importe déjà
    # `app.config.settings` au niveau module -- mais l'isolement reste plus
    # sûr pour une migration qui ne s'exécute qu'une fois).
    from app.config import settings

    wing_tag = (settings.WING_TAG or "").strip() or "Ready Room"
    # (v1.0111 : l'identifiant de la ligne n'est plus relu -- il ne servait qu'aux semis 6 et 7.)
    bind.execute(
        sa.text("INSERT INTO wing (designation, tag) VALUES (:d, :t)"),
        {"d": wing_tag, "t": wing_tag},
    )

    # --- 6 et 7. semis des escadrilles : retirés au v1.0111 (la variable n'est plus lue
    # depuis le v1.0105).


def downgrade() -> None:
    op.execute("ALTER TABLE role_capabilities DROP CONSTRAINT role_capabilities_pkey")
    op.drop_column('role_capabilities', 'squadron_scope')
    op.drop_constraint(
        'fk_role_capabilities_squadron_id', 'role_capabilities', type_='foreignkey'
    )
    op.drop_column('role_capabilities', 'squadron_id')
    op.execute(
        "ALTER TABLE role_capabilities "
        "ADD CONSTRAINT role_capabilities_pkey PRIMARY KEY (role_id, capability)"
    )

    op.drop_index('ux_squadron_membership_open_per_profile', table_name='squadron_membership')
    op.drop_table('squadron_membership')
    op.drop_table('squadron')
    op.execute("DROP TYPE squadron_status")
    op.drop_table('wing')
