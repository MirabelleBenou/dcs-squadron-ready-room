"""Le socle du Centre de Commandement (Phase 3, lot 3.1) -- crée le type
énuméré `membership_role` et la colonne `squadron_membership.role`
(rattachement de rang, trois valeurs), la table `account_capability`
(octroi nominatif d'une capacité à un compte, indépendant des rôles Discord
de session), et retire `role_capabilities.squadron_id` /
`role_capabilities.squadron_scope`, sans emploi par décision (arbitrage
n°1, spec Socle v1.1 §0/§7) -- la portée d'unité est une appartenance, pas
une capacité. L'activer aurait créé le second mécanisme de droits que la
spec met explicitement en garde de ne pas créer.

Le retrait de `squadron_id` est vérifié AVANT tout geste : si des lignes
portent `squadron_id IS NOT NULL`, la migration s'arrête sans deviner, sans
convertir, sans supprimer -- la colonne est réputée inerte (spec §7), et si
elle porte des données la situation n'est pas celle que la spec décrit.

`account_capability` ne naît d'aucun semis : il n'existe aucune source de
données à reprendre (même situation qu'à la migration `0012`). `ADMIN_IDS`
assure l'amorçage (spec §6.1). `squadron_membership.role` reprend toutes
les lignes existantes à `member` -- il n'existe aucune source pour en
déduire autre chose.

Cf. BRIEF_SONNET_LOT_3_1_Socle_Centre_Commandement.md, §2 et
SPEC_TECHNIQUE_CENTRE_COMMANDEMENT_Socle_v1_1.md §3/§7.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0013'
down_revision: Union[str, None] = '0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- 1. membership_role + squadron_membership.role -----------------------
    # TROIS valeurs, pas plus (spec §3.2 -- la hiérarchie du §10.2 en dépend).
    # Toutes les lignes existantes reprises à 'member' : aucune source pour
    # en déduire autre chose.
    op.execute(
        "CREATE TYPE membership_role AS ENUM ('leader', 'deputy', 'member')"
    )
    op.add_column(
        'squadron_membership',
        sa.Column(
            'role',
            sa.Enum('leader', 'deputy', 'member', name='membership_role'),
            nullable=False,
            server_default='member',
        ),
    )

    # --- 2. account_capability -------------------------------------------------
    # Octroi nominatif d'une capacité à un compte, indépendant des rôles
    # Discord de session (spec §3.1). Aucune colonne de portée -- la portée
    # est une appartenance, pas une capacité (arbitrage n°1). Aucune
    # contrainte CHECK sur `capability` : la restriction à `command.access`
    # est portée par la spec et par l'écran du lot 3.3, pas par la base.
    # Table naît vide, aucun semis -- ADMIN_IDS assure l'amorçage.
    op.create_table(
        'account_capability',
        sa.Column('profile_id', sa.BigInteger(), nullable=False),
        sa.Column('capability', sa.Text(), nullable=False),
        sa.Column('granted_by', sa.BigInteger(), nullable=True),
        sa.Column(
            'granted_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id']),
        sa.ForeignKeyConstraint(['granted_by'], ['profiles.id']),
        sa.PrimaryKeyConstraint('profile_id', 'capability'),
    )

    # --- 3. vérification AVANT le retrait -- obligatoire ----------------------
    # La colonne est réputée inerte (spec §7) ; si elle porte des données,
    # la situation n'est pas celle que la spec décrit et c'est au CdP de
    # trancher. On ne devine pas, on ne convertit pas, on ne supprime pas.
    non_null_count = bind.execute(
        sa.text("SELECT count(*) FROM role_capabilities WHERE squadron_id IS NOT NULL")
    ).scalar_one()
    if non_null_count:
        raise RuntimeError(
            f"Migration 0013 arrêtée : {non_null_count} ligne(s) de "
            "role_capabilities portent squadron_id IS NOT NULL. La colonne "
            "est réputée inerte par la spec Socle v1.1 §7 -- cette donnée "
            "n'est pas prévue et ne doit être ni devinée, ni convertie, ni "
            "supprimée. Décision requise du CdP avant de poursuivre."
        )

    # --- 4. retrait de role_capabilities.squadron_id -- quatre gestes,
    # dans cet ordre imposé. `squadron_scope` est générée à partir de
    # `squadron_id` ET membre de la clé primaire : Postgres refuse de
    # retirer la source avant la générée. Miroir exact du downgrade de la
    # migration 0011 (alembic/versions/0011_squadron_entities.py:188-197).
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


def downgrade() -> None:
    # --- reconstruction des quatre gestes de role_capabilities, en miroir
    # de la migration 0011 (upgrade), ordre inverse du upgrade ci-dessus.
    op.execute("ALTER TABLE role_capabilities DROP CONSTRAINT role_capabilities_pkey")
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
    op.execute(
        "ALTER TABLE role_capabilities "
        "ADD CONSTRAINT role_capabilities_pkey "
        "PRIMARY KEY (role_id, capability, squadron_scope)"
    )

    op.drop_table('account_capability')

    op.drop_column('squadron_membership', 'role')
    op.execute("DROP TYPE membership_role")
