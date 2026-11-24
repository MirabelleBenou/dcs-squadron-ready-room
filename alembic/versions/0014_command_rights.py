"""Les droits de commandement (Phase 3, lot 3.2d, premier temps) -- pose
les deux index uniques partiels garantissant au plus un `leader` et un
`deputy` OUVERTS par escadrille (idiome exact de
`ux_squadron_membership_open_per_profile`, migration 0011), la
traçabilité du rang (`role_granted_by`/`role_granted_at`, sémantique
NULL = « écrit par le système », même patron que
`account_capability.granted_by`). Elle semait aussi, conditionnellement,
les éditeurs nominatifs/par rôle du planning depuis `.env`
(`EVENT_EDITOR_ROLE_IDS`/`EVENT_EDITOR_IDS`) : semis retiré au v1.0111 :
la variable n'est plus lue depuis le v1.0105.

Vérification AVANT les index, obligatoire (§5.1, idiome de la 0013) :
compte, pour chaque escadrille, les appartenances OUVERTES de rang
`leader` puis `deputy`. Si l'une dépasse 1, la migration s'arrête sans
deviner, sans corriger d'office -- décision requise du CdP. Le compte est
nécessairement 0 partout à ce jour (aucune valeur autre que `member` n'a
jamais pu entrer en base), mais la vérification doit exister avant de
poser une contrainte qui la rendrait irréversible sans purge manuelle.

`account_capability` n'est PAS retirée ici (le cadrage v2 annexe A3
l'annonçait à tort) : elle change d'emploi, de `command.access` à
`event.create` (§5.6, cf. docstring `AccountCapability`, app/models.py).

Cf. BRIEF_SONNET_ReadyRoom_Lot_3_2d_Les_Droits.md, §5.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0014'
down_revision: Union[str, None] = '0013'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # --- 1. Vérification AVANT les index -- obligatoire (§5.1) -------------
    # Idiome de la 0013 (contrôle avant retrait, alembic/versions/
    # 0013_command_center_socle.py) : on compte, on ne devine pas, on ne
    # corrige pas d'office.
    for rang in ("leader", "deputy"):
        lignes = bind.execute(
            sa.text(
                "SELECT squadron_id, count(*) AS n FROM squadron_membership "
                "WHERE role = :rang AND ended_at IS NULL "
                "GROUP BY squadron_id HAVING count(*) > 1"
            ),
            {"rang": rang},
        ).all()
        if lignes:
            detail = ", ".join(f"escadrille {sid} : {n} lignes" for sid, n in lignes)
            raise RuntimeError(
                f"Migration 0014 arrêtée : au moins une escadrille porte plus "
                f"d'une appartenance ouverte de rang '{rang}' -- {detail}. "
                "Cette situation n'est pas prévue -- décision requise du CdP "
                "avant de poursuivre, aucune correction automatique."
            )

    # --- 2. Deux index uniques partiels (§5.2) ------------------------------
    # Idiome exact de `ux_squadron_membership_open_per_profile`
    # (app/models.py:258-266) -- portée par escadrille plutôt que par
    # profil, un seul rang à la fois.
    op.create_index(
        "ux_squadron_leader_per_squadron",
        "squadron_membership",
        ["squadron_id"],
        unique=True,
        postgresql_where=sa.text("role = 'leader' AND ended_at IS NULL"),
    )
    op.create_index(
        "ux_squadron_deputy_per_squadron",
        "squadron_membership",
        ["squadron_id"],
        unique=True,
        postgresql_where=sa.text("role = 'deputy' AND ended_at IS NULL"),
    )

    # --- 3. Traçabilité du rang (§5.3) --------------------------------------
    # NULL = écrit par le système -- c'est exactement le cas d'un rang
    # REPORTÉ par `sync_squadron_membership()` (app/squadron.py:120-140) à
    # la réouverture d'une appartenance sur la même escadrille. Même
    # sémantique que `account_capability.granted_by`.
    op.add_column(
        "squadron_membership",
        sa.Column("role_granted_by", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_squadron_membership_role_granted_by",
        "squadron_membership",
        "profiles",
        ["role_granted_by"],
        ["id"],
    )
    op.add_column(
        "squadron_membership",
        sa.Column("role_granted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Retire les deux index et les deux colonnes.
    op.drop_constraint(
        "fk_squadron_membership_role_granted_by",
        "squadron_membership",
        type_="foreignkey",
    )
    op.drop_column("squadron_membership", "role_granted_at")
    op.drop_column("squadron_membership", "role_granted_by")
    op.drop_index("ux_squadron_deputy_per_squadron", table_name="squadron_membership")
    op.drop_index("ux_squadron_leader_per_squadron", table_name="squadron_membership")
