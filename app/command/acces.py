"""Lot « Polish du Centre » -- le diagnostic d'accès : pour un membre, chacun
des neuf droits de l'écran Droits, s'il l'a et ce qui le lui ouvre.

`diagnostic` est PURE et ne fait que rejouer, dans le même ordre, les chemins
des vrais résolveurs (`app/capabilities.py`, `app/auth.py`, `app/relances.py`),
qui ne se touchent pas : elle lit un `etat` que `lire_etat` relève en base une
seule fois par appel. L'équivalence avec les résolveurs est un critère du lot
(contrôle de bout en bout, profil par profil, droit par droit)."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import _app_access_role_ids
from app.config import settings
from app.models import AccountCapability, RoleCapability, Squadron, SquadronMembership

# Les neuf droits de l'écran Droits, dans l'ordre où l'écran les dit.
DROITS = (
    "app.access",
    "command.access",
    "debrief.access",
    "event.create",
    "event.edit_any",
    "session.edit",
    "campaign.manage",
    "campaign.delete",
    "relances.destinataire",
)


def diagnostic(pid: int, roles: list[str], archive: bool, etat: dict) -> list[dict]:
    """Pour le profil `pid`, de rôles `roles` (ceux qu'il porte, `roles_snapshot`),
    `archive` s'il est archivé : `[{"cle", "accorde", "source"}]` dans l'ordre de
    `DROITS`. Pure. `source` est le PREMIER chemin qui ouvre le droit, ou `None` ;
    `accorde` vaut `source is not None`. « Rôle » veut dire le premier rôle de
    `sorted(roles)` qui ouvre le droit.

    `etat` : `admins` (ensemble de textes) · `app_roles` (le résolveur
    `_app_access_role_ids`) · `roles_par_droit` (droit -> ensemble de
    rôles, `role_capabilities`) · `comptes_par_droit` (droit -> ensemble de
    profils, `account_capability`) · `adjoint_de` (la désignation de l'escadrille
    où le profil est adjoint ouvert, ou `None`).

    Lot « rr-socle-proprete » (v1.0111) : plus de repli `.env` -- la base fait
    autorité ; muette, l'accès et la création d'évènements ne s'ouvrent à personne
    (hors administrateur)."""
    admin = str(pid) in {str(a) for a in etat["admins"]}
    portes = sorted(str(r) for r in roles)

    def un_role(ouverts) -> Optional[str]:
        ouverts = {str(r) for r in ouverts}
        return next((r for r in portes if r in ouverts), None)

    def role_par_droit(droit: str) -> Optional[str]:
        return un_role(etat["roles_par_droit"].get(droit, ()))

    def compte(droit: str) -> bool:
        return str(pid) in {str(p) for p in etat["comptes_par_droit"].get(droit, ())}

    def source(droit: str) -> Optional[dict]:
        if droit == "relances.destinataire":
            # Pas d'administrateur : l'administrateur ne reçoit pas les MP de relance
            # par son seul statut ; un archivé n'est jamais destinataire.
            if archive:
                return None
            r = role_par_droit(droit)
            if r is not None:
                return {"type": "role", "role_id": r}
            return {"type": "compte"} if compte(droit) else None
        if admin:
            return {"type": "admin"}
        if droit == "app.access":
            r = un_role(etat["app_roles"])
            if r is None:
                return None
            return {"type": "role", "role_id": r}
        if droit == "command.access":
            r = role_par_droit(droit)
            if r is not None:
                return {"type": "role", "role_id": r}
            if etat["adjoint_de"] is not None:
                return {"type": "adjoint", "escadrille": etat["adjoint_de"]}
            return None
        if droit == "event.create":
            # La base fait autorité SEULE ; muette, personne (hors administrateur).
            r = role_par_droit(droit)
            if r is not None:
                return {"type": "role", "role_id": r}
            return {"type": "compte"} if compte(droit) else None
        r = role_par_droit(droit)
        return {"type": "role", "role_id": r} if r is not None else None

    out = []
    for droit in DROITS:
        s = source(droit)
        out.append({"cle": droit, "accorde": s is not None, "source": s})
    return out


async def lire_etat(db: AsyncSession, pid: int) -> dict:
    """L'`etat` de `diagnostic`, relevé en base -- une fois par appel, par les
    mêmes lectures que les résolveurs."""
    app_roles = await _app_access_role_ids(db)
    roles_par_droit: dict[str, set] = {}
    for role_id, capability in (
        await db.execute(
            select(RoleCapability.role_id, RoleCapability.capability).where(
                RoleCapability.capability.in_(DROITS)
            )
        )
    ).all():
        roles_par_droit.setdefault(capability, set()).add(str(role_id))
    comptes_par_droit: dict[str, set] = {}
    for profile_id, capability in (
        await db.execute(
            select(AccountCapability.profile_id, AccountCapability.capability).where(
                AccountCapability.capability.in_(DROITS)
            )
        )
    ).all():
        comptes_par_droit.setdefault(capability, set()).add(profile_id)
    adjoint_de = (
        await db.execute(
            select(Squadron.designation)
            .join(SquadronMembership, SquadronMembership.squadron_id == Squadron.id)
            .where(
                SquadronMembership.profile_id == pid,
                SquadronMembership.role == "deputy",
                SquadronMembership.ended_at.is_(None),
                # Lot « Le Centre côté serveur » : l'adjoint suit le statut de son escadrille.
                Squadron.status == "actif",
            )
            .order_by(Squadron.id)
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "admins": settings.admin_ids_set,
        "app_roles": set(app_roles),
        "roles_par_droit": roles_par_droit,
        "comptes_par_droit": comptes_par_droit,
        "adjoint_de": adjoint_de,
    }
