"""Résolution des capacités (droits) — cf. SPEC_TECHNIQUE_READY_ROOM_Planification_v1
§"Permissions" et brief Lot 2.

MVP :
- `event.create` (v0.77) : réservé — admin (.env) OU capacité `event.create`
  accordée via `role_capabilities` ou `account_capability` (cf.
  `can_create_event`). Base muette : seuls les administrateurs créent
  (lot « rr-socle-proprete », v1.0111 : le repli `.env` est retiré). Avant
  v0.77, ouvert à tout membre authentifié.
- `event.edit_any` : accordé uniquement si `role_capabilities` contient une
  ligne pour un des rôles du profil. Table vide par défaut → seul le
  **créateur** d'un événement peut l'éditer/supprimer.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.models import AccountCapability, RoleCapability, Squadron, SquadronMembership

# Capacités ouvertes à tout membre authentifié, sans passer par la table
# `role_capabilities` (règle MVP explicite de la spec). v0.77 : `event.create`
# retiré (cf. brief chantier A) -- la constante reste, le mécanisme
# `has_capability` reste générique, mais plus aucune capacité n'y est ouverte
# par défaut au MVP actuel.
OPEN_CAPABILITIES: set[str] = set()


def is_admin(user: dict) -> bool:
    """Compte listé dans ADMIN_IDS (.env)."""
    return str(user["id"]) in settings.admin_ids_set


def est_invite(user) -> bool:
    """Lot « L'accès invité » (R5) -- la session d'un invité (`get_current_user`
    pose la clé `invite` à `True`). Un membre n'a jamais cette clé."""
    return bool(user) and user.get("invite") is True


async def has_capability(db: AsyncSession, roles: list[str], capability: str) -> bool:
    """Est-ce qu'un membre portant `roles` (rôles Discord du profil, lus par `get_current_user`) a la
    capacité `capability` ?"""
    if capability in OPEN_CAPABILITIES:
        return True
    if not roles:
        return False
    stmt = select(RoleCapability.role_id).where(
        RoleCapability.capability == capability,
        RoleCapability.role_id.in_(roles),
    )
    result = await db.execute(stmt)
    return result.first() is not None


async def has_account_capability(
    db: AsyncSession, profile_id: int, capability: str
) -> bool:
    """Capacité accordée nominativement à un compte (`account_capability`),
    indépendamment de ses rôles Discord. Fonction sœur de
    `has_capability()` -- cf. spec Socle v1.1 §4.1 (option (b) retenue :
    `has_capability()` conserve sa signature exacte, cette fonction porte
    la branche compte et les deux se composent au point d'appel).

    `profiles.id` est un `BigInteger` ; `is_admin()` compare des chaînes
    (`str(user["id"]) in settings.admin_ids_set`). Le point de conversion
    vers `int` n'est pas fait ici : cette fonction reçoit `profile_id` déjà
    résolu. La conversion est faite par l'appelant, sur `user["id"]`, avant
    l'appel -- c'est l'idiome établi du dépôt (9 occurrences), conséquence
    de l'option (b) de la spec Socle §4.1 : cette fonction est la sœur de
    `has_capability()`, qui reçoit elle aussi des données déjà résolues."""
    stmt = select(AccountCapability.profile_id).where(
        AccountCapability.profile_id == profile_id,
        AccountCapability.capability == capability,
    )
    result = await db.execute(stmt)
    return result.first() is not None


async def can_admin_squadron(db: AsyncSession, user: dict, squadron_id: int) -> bool:
    """Admin (.env) OU appartenance OUVERTE (`ended_at IS NULL`) du compte à
    `squadron_id`, avec un rôle ∈ {leader, deputy} (cf. spec Socle v1.1
    §4.2). L'appartenance ouverte est unique par profil, garanti en base
    par l'index partiel `ux_squadron_membership_open_per_profile`
    (models.py:258) : une seule ligne est lue, jamais un ensemble.

    N'implémente PAS la règle d'attribution des rôles (nul ne modifie le
    rôle d'un membre de rang supérieur ou égal au sien) : elle demande
    deux rangs -- celui de l'agissant, celui de la cible -- là où cette
    fonction n'en lit qu'un. Cette règle est spécifiée au lot 3.2, avec
    l'écran qui l'exerce ; les fondre la ferait mentir."""
    if is_admin(user):
        return True
    stmt = select(SquadronMembership.role).where(
        SquadronMembership.profile_id == int(user["id"]),
        SquadronMembership.squadron_id == squadron_id,
        SquadronMembership.ended_at.is_(None),
    )
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    return role in ("leader", "deputy")


async def has_command_access(db: AsyncSession, user: dict) -> bool:
    """Résolution de l'accès au module Centre de Commandement (Lot 3.2d,
    Volet 2, §6.1). Trois branches, dans cet ordre :

    1. `is_admin(user)` -- testée en premier, avant toute lecture de table
       (garde-fou d'amorçage, §6.1).
    2. `has_capability(db, roles, "command.access")` -- le rôle Discord des
       chefs, qui est la ligne `role_capabilities(role_id, 'command.access')`
       écrite par `PUT /command/rights/chef-role` (écran Droits, bloc 1).
       Aucun mécanisme neuf : c'est la branche rôle existante de
       `require_command_access`, à laquelle l'écran Droits donne enfin un
       écrivain.
    3. Appartenance OUVERTE de rang `deputy`, sur une escadrille ACTIVE
       (`Squadron.status == "actif"`, lot « Le Centre côté serveur ») -- un
       adjoint entre dans le module même s'il ne porte pas le rôle Discord
       des chefs ; celui d'une escadrille en sommeil n'entre plus, et
       retrouve la porte au réveil de son escadrille.

    Appelée par `require_command_access` (ci-dessous) ET par `read_me`
    (`app/api.py`) -- sinon la tuile d'accueil et la porte du module
    divergeraient (§6.1)."""
    if is_admin(user):
        return True
    # Lot « L'accès invité » (R5) : l'invité entre au Centre, en lecture seule
    # (le mur de `app/main.py` refuse ses écritures) -- avant toute lecture en
    # base : il n'a pas de profil.
    if est_invite(user):
        return True
    if await has_capability(db, user.get("roles", []), "command.access"):
        return True
    # Lot « Le Centre côté serveur » : l'adjoint suit le statut de son escadrille.
    stmt = (
        select(SquadronMembership.id)
        .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .where(
            SquadronMembership.profile_id == int(user["id"]),
            SquadronMembership.role == "deputy",
            SquadronMembership.ended_at.is_(None),
            Squadron.status == "actif",
        )
    )
    result = await db.execute(stmt)
    return result.first() is not None


async def _event_create_base_authoritative(db: AsyncSession) -> bool:
    """La base a-t-elle quelque chose à dire sur `event.create` (§6.3,
    Lot 3.2d) ? Au moins une ligne dans `role_capabilities` OU dans
    `account_capability` pour cette capacité précise -- pas la capacité de
    CET utilisateur, celle de la table entière. Si oui, la base fait
    autorité SEULE ; sinon (base muette), personne ne crée hors administrateur
    (cf. Patron n°4 de la spec Socle §11)."""
    role_stmt = (
        select(RoleCapability.role_id)
        .where(RoleCapability.capability == "event.create")
        .limit(1)
    )
    if (await db.execute(role_stmt)).first() is not None:
        return True
    account_stmt = (
        select(AccountCapability.profile_id)
        .where(AccountCapability.capability == "event.create")
        .limit(1)
    )
    return (await db.execute(account_stmt)).first() is not None


async def can_create_event(db: AsyncSession, user: dict) -> bool:
    """Admin (.env) OU la base, qui fait autorité (lot « rr-socle-proprete »,
    v1.0111 : plus de repli `.env`) :

    1. `is_admin(user)` -- vrai ;
    2. si la base a quelque chose à dire sur `event.create`
       (`_event_create_base_authoritative`) : elle fait autorité SEULE
       (`has_capability()` OU `has_account_capability()`) ;
    3. sinon, base muette : faux."""
    if is_admin(user):  # GARDE-FOU anti-lock-out : jamais retirable.
        return True
    roles = {str(r) for r in user.get("roles", [])}
    if await _event_create_base_authoritative(db):
        # La base fait autorité, seule, même si elle ne mentionne pas CET utilisateur.
        if await has_capability(db, list(roles), "event.create"):
            return True
        return await has_account_capability(db, int(user["id"]), "event.create")
    # La base est muette : personne, hors administrateur.
    return False


async def can_edit_event(db: AsyncSession, user: dict, event_creator_id: int) -> bool:
    """Admin (.env) OU créateur de l'événement OU capacité `event.edit_any`."""
    if is_admin(user):
        return True
    if int(user["id"]) == event_creator_id:
        return True
    return await has_capability(db, user.get("roles", []), "event.edit_any")


async def can_edit_session(db: AsyncSession, user: dict) -> bool:
    """Nommage/renommage de mission + note d'escadre (Lot 2.1, §4.6).
    Portée globale, non restreinte à l'escadrille -- les sessions sont
    multi-escadrilles (ex. BRAVO-22 et CHARLIE-33 volant ensemble). Capacité
    `session.edit` (et non `session.rename` : le cadrage l'avait nommée
    ainsi quand seul le nom existait, la note l'élargit -- un seul nom, un
    seul libellé qui reste vrai)."""
    if is_admin(user):  # garde-fou anti-lock-out : jamais retirable.
        return True
    return await has_capability(db, user.get("roles", []), "session.edit")


async def can_manage_campaigns(db: AsyncSession, user: dict) -> bool:
    """Création et modification d'une campagne (Lot 3.4, §6) -- un seul
    droit pour les deux gestes, même métier sur le même objet, capacité
    `campaign.manage`. Portée globale (pas de notion d'escadrille sur une
    campagne). Même patron que `can_edit_session()` : admin (garde-fou
    anti-lock-out) OU capacité accordée par rôle Discord."""
    if is_admin(user):
        return True
    return await has_capability(db, user.get("roles", []), "campaign.manage")


async def can_delete_campaigns(db: AsyncSession, user: dict) -> bool:
    """Suppression d'une campagne (Lot 3.4, §6/§7) -- capacité distincte
    `campaign.delete`, volontairement séparée de `campaign.manage` (le
    geste destructeur se distribue à part, arbitrage du porteur du 22 août).
    Le refus si des missions sont rattachées est un contrôle métier
    supplémentaire, appliqué par la route -- pas ici (cette fonction ne
    porte que la question du droit, pas celle de l'état de la campagne)."""
    if is_admin(user):
        return True
    return await has_capability(db, user.get("roles", []), "campaign.delete")


async def require_debrief_access(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Gate du module Debriefing (v0.76) : réservé aux admins, ou aux rôles
    dotés de la capacité `debrief.access` via `role_capabilities` (non
    ajoutée à `OPEN_CAPABILITIES` — accès fermé par défaut). Appliqué au
    point de montage unique (`router.include_router(debrief_router, ...)`
    dans `app/api.py`), jamais route par route."""
    if is_admin(user):
        return user
    # Lot « L'accès invité » (R5) : lecture seule, avant toute lecture en base.
    if est_invite(user):
        return user
    if await has_capability(db, user.get("roles", []), "debrief.access"):
        return user
    raise HTTPException(status_code=403, detail="Module Escadre — accès réservé.")


async def require_command_access(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Gate du module Centre de Commandement (Phase 3, lot 3.1 ; résolution
    remaniée au Lot 3.2d Volet 2, §6.1/§6.2) : réservé aux admins, au rôle
    Discord des chefs (`command.access` via `role_capabilities`, écrit par
    l'écran Droits) ou aux adjoints (appartenance ouverte `deputy`).
    Toute la résolution vit désormais dans `has_command_access()` -- la
    branche compte (`has_account_capability(..., "command.access")`) est
    RETIRÉE (Lot 3.2d §6.2) : `account_capability` ne porte plus cette
    capacité, elle porte `event.create` et `relances.destinataire`. Appliqué au point de montage
    unique (`router.include_router(command_router, ...)` dans
    `app/api.py`), jamais route par route."""
    if await has_command_access(db, user):
        return user
    raise HTTPException(
        status_code=403, detail="Centre de Commandement — accès réservé."
    )
