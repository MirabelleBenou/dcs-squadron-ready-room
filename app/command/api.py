"""Router `/api/command/*` — Centre de Commandement, socle (lot 3.1) +
routes de lecture (lot 3.2b Volet 3 : /squadrons ; lot 3.2c Volet 3 :
/members) + droits (lot 3.2d Volet 3, premier temps) + l'appel (lot
« L'appel » : /members/appel).

Monté sous `/command` par ce module ; le préfixe `/api` est appliqué par le
router parent (`app/api.py`), même patron que `debrief_router`. Aucune
garde route par route ici -- le verrou est déjà posé au point de montage
unique (`app/api.py`, `Depends(require_command_access)`), cf. spec Socle
v1.1 §11 point 2. Les contrôles d'autorité du Volet 3 (admin, leader d'une
escadrille précise) ne sont PAS des gardes d'accès au module : ce sont des
contrôles métier à l'intérieur d'un module déjà verrouillé -- ils lèvent
403, jamais un `Depends` supplémentaire (Lot 3.2d §7, motif d'arrêt sinon).
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import delete, func, select, text, update
from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from app import agent as agent_mod
from app import appel, connexion_secours, crests, relances, reglages, sauvegardes, sauvegardes_auto
from app.auth import (
    _app_access_role_ids,
    echeance_initiale,
    echeance_prolongee,
    get_current_user,
    has_app_access,
    identifiant_discord_valide,
    invalidate_app_access_cache,
    invitation_active,
)
from app.capabilities import (
    can_admin_squadron,
    can_delete_campaigns,
    can_manage_campaigns,
    is_admin,
)
from app.config import settings
from app.db import get_db
from app.command import acces, journal
from app.debrief import categorize, referentiel
from app.debrief.api import _fiche_publique
from app.debrief_models import (
    Campaign,
    DebriefEvent,
    DebriefFlight,
    DebriefGraveyard,
    DebriefSession,
    DebriefUnitCategory,
    ReferentielArme,
)
from app.discord_rsvp import _bot_request
from app.events import _build_name_strip_regex, _callsign
from app.models import (
    AccountCapability,
    AgentJeton,
    AgentRrlog,
    CommandJournal,
    Invitation,
    Profile,
    Reglage,
    RoleCapability,
    SauvegardeAutoReglage,
    Squadron,
    SquadronMembership,
    Wing,
)

router = APIRouter(prefix="/command")


class ChefRolePayload(BaseModel):
    """Corps de `PUT /command/rights/chef-role` (§7.6). `role_id` nul
    retire la ligne sans en poser d'autre."""

    role_id: Optional[str] = None


class SquadronLeaderPayload(BaseModel):
    """Corps de `PUT /command/squadrons/{id}/leader` (§7.3). `profile_id`
    nul retire le chef sans en poser d'autre."""

    profile_id: Optional[str] = None


class SquadronDeputyPayload(BaseModel):
    """Corps de `PUT /command/squadrons/{id}/deputy` (§7.4). Même forme
    que `SquadronLeaderPayload` -- `profile_id` nul retire l'adjoint sans
    en poser d'autre."""

    profile_id: Optional[str] = None


class EventEditorsPayload(BaseModel):
    """Corps de `PUT /command/rights/event-editors` (§7.5). Remplacement
    COMPLET des deux listes -- pas une modification incrémentale."""

    role_ids: list[str] = []
    profile_ids: list[str] = []


class AppAccessPayload(BaseModel):
    """Corps de `PUT /command/rights/app-access` (Lot 3.2d Volet 3, second
    temps, §6.2). Remplacement COMPLET de la liste -- même patron que
    `EventEditorsPayload`."""

    role_ids: list[str] = []


class DebriefAccessPayload(BaseModel):
    """Corps de `PUT /command/rights/debrief-access` (brief « Accès au
    module Débriefing », 22 août 2026). Remplacement COMPLET de la liste
    -- même patron que `EventEditorsPayload` / `AppAccessPayload`. Route
    dédiée comme `app-access` (une porte de module a sa route, ne rejoint
    pas `PUT /rights/content` qui porte les droits sur les objets) --
    mais SANS ses deux garde-fous (409 sur liste vide, invalidation de
    cache) : vider cette liste ne ferme aucune porte, `debrief.access`
    n'est ni cachée ni lue à chaque requête (§4/§5 du brief)."""

    role_ids: list[str] = []


class RelancesPayload(BaseModel):
    """Corps de `PUT /command/rights/relances` (lot « Les relances », R7 ;
    étendu par le lot « Les relances nominatives », R3). Remplacement COMPLET
    des deux listes -- les rôles destinataires et les comptes destinataires
    --, même patron que `EventEditorsPayload`. Une clé absente vaut une liste
    vide. Deux listes vides sont permises : aucun MP ne part, la liste reste à
    l'écran Membres."""

    role_ids: list[str] = []
    profile_ids: list[str] = []


class ContentRightsPayload(BaseModel):
    """Corps de `PUT /command/rights/content` (Lot 3.3, §3 ; étendu Lot
    3.4, §6). Remplacement COMPLET des quatre listes -- même patron que
    `EventEditorsPayload` / `AppAccessPayload`. Par rôle Discord
    UNIQUEMENT, aucun octroi nominatif (`account_capability` n'est pas
    concernée : elle porte `event.create` et `relances.destinataire`). Pas de 409 sur
    liste vide : vider ces listes ne ferme aucune porte -- les
    administrateurs conservent les quatre droits en dur, et le créateur
    d'un événement peut toujours modifier le sien (§3, différence assumée
    avec `app.access`). `campaign_manage_role_ids`/`campaign_delete_role_ids`
    neufs au Lot 3.4 : un seul droit pour créer ET modifier une campagne
    (même métier, même objet), la suppression en distincte à part
    (arbitrage du porteur du 22 août)."""

    session_edit_role_ids: list[str] = []
    event_edit_any_role_ids: list[str] = []
    campaign_manage_role_ids: list[str] = []
    campaign_delete_role_ids: list[str] = []


class WingUpdatePayload(BaseModel):
    """Corps de `PATCH /command/wing` (lot « L'écran Escadre du Centre »).
    Champs PRÉSENTS seulement -- `model_fields_set` distingue « absent » de
    « remis à vide », même patron que `SquadronUpdatePayload`."""

    designation: Optional[str] = None
    full_name: Optional[str] = None
    period: Optional[str] = None
    sigle: Optional[str] = None
    tag: Optional[str] = None


class SauvegardeAutoPayload(BaseModel):
    """Corps de `PUT /command/archives/automatique` (lot « Les sauvegardes
    automatiques ») : la fréquence en heures et la rétention, les deux requises.
    `sauvegardes_auto.valider_reglage` dit lesquelles sont permises."""

    intervalle_h: int
    garder: int


class SquadronCreatePayload(BaseModel):
    """Corps de `POST /command/squadrons` (Lot 3.2e, volet ①, §Volet C).
    `discord_role_id` nul -> escadrille active sans rattachement (le
    bandeau « partiel » le signale déjà, cf. 3.2b). Lot « L'identité de
    l'escadrille » (R189) : seul l'identifiant est requis ; le callsign et
    le nom complet sont facultatifs."""

    designation: Optional[str] = None
    callsign: Optional[str] = None
    full_name: Optional[str] = None
    discord_role_id: Optional[str] = None


class LiveryPayload(BaseModel):
    """Lot « La config d'escadre de Mission Plan fabriquée par le Centre » -- une
    livrée d'escadrille telle que le PATCH la reçoit. Aucun champ n'est exigé
    ici : c'est `_normaliser_livrees` qui refuse, avec ses messages."""

    name: Optional[str] = None
    aircraft: list[str] = []
    jeu: bool = False


class SquadronUpdatePayload(BaseModel):
    """Corps de `PATCH /command/squadrons/{id}` (§6.1). Champs PRÉSENTS
    seulement -- `model_fields_set` distingue "absent" de "remis à vide",
    même patron que `SessionEditPayload` (app/debrief/schemas.py).
    `discord_role_id` est le SEUL champ réservé à l'administrateur (§6.1) ;
    `designation`/`callsign`/`full_name` sont ouverts au chef et à l'adjoint
    (§5.1, lot « L'identité de l'escadrille »), comme
    `aircraft` (lot « L'appareil de l'escadrille »), normalisé par
    `_normalize_aircraft`. Lot « La config d'escadre de Mission Plan fabriquée
    par le Centre » : `nickname` (60 caractères, comme `full_name` sinon), `liveries` et `default_liveries`, normalisées par
    `_normaliser_livrees` et `_normaliser_defauts`, ouvertes au chef et à
    l'adjoint comme `aircraft`."""

    designation: Optional[str] = None
    callsign: Optional[str] = None
    full_name: Optional[str] = None
    discord_role_id: Optional[str] = None
    aircraft: Optional[list[str]] = None
    nickname: Optional[str] = None
    liveries: Optional[list[LiveryPayload]] = None
    default_liveries: Optional[dict[str, str]] = None


class SquadronWakePayload(BaseModel):
    """Corps de `PUT /command/squadrons/{id}/wake` (§2 point 5, §6.2).
    `discord_role_id` OBLIGATOIRE fonctionnellement -- vérifié en 409, pas
    en 422 de schéma (nul/absent traités identiquement, cf. §Volet C)."""

    discord_role_id: Optional[str] = None


class CampaignUpsertPayload(BaseModel):
    """Corps de `POST /command/campaigns` (Lot 3.4, §3/§6). Une SEULE
    route pour créer ET modifier -- même bloc de formulaire côté écran
    (§3 : « Un seul bloc. Modifier une campagne le bascule en édition »),
    même geste côté route : `id` absent -> création, `id` présent ->
    modification de la campagne désignée. `name` reste le seul champ
    obligatoire dans les deux cas (vérifié dans la route, pas ici -- même
    raison que `SquadronUpdatePayload` : le message d'erreur diffère
    entre absence et valeur vide). `status`/`sim` ont une valeur de repli
    à la création (`en_cours`/`dcs`) appliquée dans la route, jamais ici."""

    id: Optional[str] = None
    name: Optional[str] = None
    sim: Optional[str] = None
    map_name: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


AIRCRAFT_MAX = 4
AIRCRAFT_NAME_MAX = 40


def _normalize_aircraft(values: list[str] | None) -> list[str] | None:
    """Lot « L'appareil de l'escadrille » -- la liste des appareils déclarés au
    Centre, telle qu'elle s'enregistre : chaque nom débarrassé de ses espaces
    de bord, les vides retirés, les doublons retirés sans tenir compte de la
    casse, l'ordre de saisie gardé. Une liste vide s'enregistre `NULL` --
    rien de déclaré. Quatre appareils au plus (arbitrage du porteur), 40
    caractères par nom : au-delà, refus 422, rien n'est écrit."""
    noms: list[str] = []
    for valeur in values or []:
        nom = str(valeur).strip()
        if nom and nom.casefold() not in {n.casefold() for n in noms}:
            noms.append(nom)
    if len(noms) > AIRCRAFT_MAX:
        raise HTTPException(status_code=422, detail=f"{AIRCRAFT_MAX} appareils au plus.")
    if any(len(n) > AIRCRAFT_NAME_MAX for n in noms):
        raise HTTPException(
            status_code=422,
            detail=f"Un nom d'appareil tient en {AIRCRAFT_NAME_MAX} caractères au plus.",
        )
    return noms or None


NICKNAME_MAX = 60
LIVREES_MAX = 30
LIVREE_NOM_MAX = 80


def _ecriture_appareil(valeur: str, appareils: list[str]) -> str | None:
    """L'appareil `valeur` écrit comme l'escadrille l'écrit (comparaison sans
    casse), ou `None` s'il n'en est pas."""
    cle = str(valeur).strip().casefold()
    for appareil in appareils:
        if appareil.casefold() == cle:
            return appareil
    return None


def _normaliser_livrees(values: list[dict] | None, appareils: list[str]) -> list[dict] | None:
    """Lot « La config d'escadre de Mission Plan fabriquée par le Centre » --
    les livrées d'une escadrille, telles qu'elles s'enregistrent. `appareils`
    sont ceux de l'escadrille APRÈS l'écriture en cours. Refus 422, rien n'est
    écrit, sur le premier défaut rencontré : plus de 30 livrées ; puis, livrée
    par livrée dans l'ordre de saisie, un nom vide ou de plus de 80
    caractères, un appareil que l'escadrille ne déclare pas, aucun appareil,
    un nom déjà vu (sans casse). Le nom perd ses espaces de bord ; chaque
    appareil est comparé sans casse et réécrit dans l'écriture de l'escadrille,
    ses doublons retirés ; `jeu` est gardé (faux par défaut) ; l'ordre de saisie
    est gardé ; une liste vide s'enregistre `NULL`."""
    values = list(values or [])
    if len(values) > LIVREES_MAX:
        raise HTTPException(
            status_code=422, detail=f"{LIVREES_MAX} livrées au plus par escadrille."
        )
    livrees: list[dict] = []
    vus: set[str] = set()
    for valeur in values:
        nom = str(valeur.get("name") or "").strip()
        if not nom:
            raise HTTPException(status_code=422, detail="Chaque livrée a un nom.")
        if len(nom) > LIVREE_NOM_MAX:
            raise HTTPException(
                status_code=422,
                detail=f"Le nom d'une livrée tient en {LIVREE_NOM_MAX} caractères.",
            )
        ecrits: list[str] = []
        for brut in valeur.get("aircraft") or []:
            if not str(brut).strip():
                continue
            ecrit = _ecriture_appareil(brut, appareils)
            if ecrit is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"La livrée {nom} porte un appareil que l'escadrille ne déclare pas.",
                )
            if ecrit not in ecrits:
                ecrits.append(ecrit)
        if not ecrits:
            raise HTTPException(status_code=422, detail=f"La livrée {nom} n'a aucun appareil.")
        if nom.casefold() in vus:
            raise HTTPException(status_code=422, detail=f"La livrée {nom} est en double.")
        vus.add(nom.casefold())
        livrees.append({"name": nom, "aircraft": ecrits, "jeu": bool(valeur.get("jeu"))})
    return livrees or None


def _normaliser_defauts(values: dict | None, appareils: list[str]) -> dict | None:
    """Les livrées par défaut d'une escadrille, telles qu'elles s'enregistrent :
    chaque clé comparée sans casse aux appareils de l'escadrille (APRÈS
    l'écriture en cours) et réécrite dans leur écriture -- une clé qu'elle ne
    déclare pas est refusée en 422 ; la valeur perd ses espaces de bord, vide
    la clé part, plus de 80 caractères est refusé en 422. Un objet vide
    s'enregistre `NULL`. La valeur n'est pas confrontée aux livrées."""
    defauts: dict[str, str] = {}
    for cle, valeur in (values or {}).items():
        ecrit = _ecriture_appareil(cle, appareils)
        if ecrit is None:
            raise HTTPException(
                status_code=422,
                detail="La livrée par défaut porte un appareil que l'escadrille ne déclare pas.",
            )
        nom = str(valeur or "").strip()
        if len(nom) > LIVREE_NOM_MAX:
            raise HTTPException(
                status_code=422,
                detail=f"Le nom d'une livrée tient en {LIVREE_NOM_MAX} caractères.",
            )
        if nom:
            defauts[ecrit] = nom
        else:
            defauts.pop(ecrit, None)
    return defauts or None


def _elaguer_livrees(
    liveries: list | None, default_liveries: dict | None, appareils: list[str]
) -> tuple[list | None, dict | None]:
    """Pure. Un PATCH qui change les appareils sans toucher aux livrées élague
    ce qui est en base : un appareil retiré quitte chaque livrée (les autres
    sont réécrits dans la nouvelle écriture de l'escadrille), une livrée qui
    n'a plus d'appareil part, une livrée par défaut d'un appareil retiré part.
    Rend les deux valeurs, `None` quand elles sont vides."""
    livrees: list[dict] = []
    for livree in liveries or []:
        restants: list[str] = []
        for brut in livree.get("aircraft") or []:
            ecrit = _ecriture_appareil(brut, appareils)
            if ecrit is not None and ecrit not in restants:
                restants.append(ecrit)
        if restants:
            livrees.append({**livree, "aircraft": restants})
    defauts: dict[str, str] = {}
    for cle, valeur in (default_liveries or {}).items():
        ecrit = _ecriture_appareil(cle, appareils)
        if ecrit is not None:
            defauts[ecrit] = valeur
    return livrees or None, defauts or None


async def _roles_de(db: AsyncSession, capacite: str) -> list[str]:
    """Lot « Polish du Centre » -- les rôles qui portent `capacite`, triés : l'« avant »
    d'une écriture des écrans Droits, relevé avant que la route ne l'efface."""
    return sorted(
        str(r)
        for r in (
            await db.execute(
                select(RoleCapability.role_id).where(RoleCapability.capability == capacite)
            )
        ).scalars().all()
    )


async def _comptes_de(db: AsyncSession, capacite: str) -> list[str]:
    """Idem pour les comptes (`account_capability`), en texte, triés par identifiant."""
    return [
        str(p)
        for p in (
            await db.execute(
                select(AccountCapability.profile_id)
                .where(AccountCapability.capability == capacite)
                .order_by(AccountCapability.profile_id)
            )
        ).scalars().all()
    ]


def _etat_escadrille(sq: Squadron) -> dict:
    """Lot « Polish du Centre » -- les champs que `squadron.edit` compare. Lot « La
    config d'escadre de Mission Plan fabriquée par le Centre » : deux listes de
    textes de plus, pour que le journal écrive ce qui est ajouté et retiré --
    `liveries` (« Nom (Mi-24P, Mi-8) ») et `default_liveries` (« Mi-24P : Nom »)."""
    return {
        "designation": sq.designation,
        "callsign": sq.callsign,
        "full_name": sq.full_name,
        "nickname": sq.nickname,
        "discord_role_id": sq.discord_role_id,
        "aircraft": list(sq.aircraft or []),
        "liveries": [
            f"{l.get('name')} ({', '.join(l.get('aircraft') or [])})"
            for l in (sq.liveries or [])
        ],
        "default_liveries": [
            f"{appareil} : {nom}" for appareil, nom in (sq.default_liveries or {}).items()
        ],
    }


_CHAMPS_CAMPAGNE = ("name", "sim", "map_name", "status", "description")


def _etat_campagne(c: Campaign) -> dict:
    """Lot « Polish du Centre » -- les champs que `campaign.edit` compare."""
    return {k: getattr(c, k) for k in _CHAMPS_CAMPAGNE}


_CHAMPS_ESCADRE = ("designation", "full_name", "period", "sigle", "tag")


def _squadron_to_dict(sq: Squadron) -> dict:
    """Patron de `_campaign_to_dict` (`app/debrief/api.py`). Champs rendus :
    id, designation, callsign, full_name, status, discord_role_id, crest_sha,
    aircraft, nickname, liveries, default_liveries -- rien
    d'autre, pas de wing_id (colonne non affichée à ce lot, cf. brief
    §Volet 3). `crest_sha` ajouté au Lot 3.2e, volet ② (§5.2) ; `aircraft` au
    lot « L'appareil de l'escadrille », toujours une liste -- vide si rien
    n'est déclaré ; `callsign` et `full_name` au lot « L'identité de
    l'escadrille », `None` quand ils sont vides."""
    return {
        "id": sq.id,
        "designation": sq.designation,
        "callsign": sq.callsign,
        "full_name": sq.full_name,
        "nickname": sq.nickname,
        "status": sq.status,
        "discord_role_id": sq.discord_role_id,
        "crest_sha": sq.crest_sha,
        "aircraft": sq.aircraft or [],
        "liveries": sq.liveries or [],
        "default_liveries": sq.default_liveries or {},
    }


def _campaign_full_dict(c: Campaign, mission_count: int) -> dict:
    """Forme complète pour l'écran Campagnes du Centre de Commandement
    (Lot 3.4, §3/§8 P5) -- distincte de `_campaign_to_dict()`
    (`app/debrief/api.py`), qui sert les sélecteurs du Débriefing et ne
    rend que `{id, name, status, sim}`. Celle-ci ajoute `map_name`
    (« Théâtre » à l'écran, le nom interne ne change pas, brief §3),
    `description` (saisie mais affichée nulle part dans ce lot -- doit
    tout de même revenir ici pour que le formulaire d'édition puisse la
    restituer) et `mission_count` (le compte du serveur, jamais déduit
    côté client, §7)."""
    return {
        "id": str(c.id),
        "name": c.name,
        "sim": c.sim,
        "map_name": c.map_name,
        "status": c.status,
        "description": c.description,
        "mission_count": mission_count,
    }


@router.get("/squadrons")
async def list_command_squadrons(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Patron de route de lecture : `list_campaigns`
    (`app/debrief/api.py`). Tri `Squadron.id` croissant -- l'ordre de
    résolution de `_resolve_squadron_id()` (`app/squadron.py`), pas un
    ordre alphabétique flatteur.

    Lot 3.2e, volet ① : ajoute `you` -- `is_admin` et l'appartenance
    OUVERTE de l'agissant (`squadron_id`, `role`). Le serveur reste seul
    juge à l'écriture (`can_admin_squadron()`, §6) ; ce bloc sert
    uniquement à l'écran à savoir quelles lignes proposer en édition, sans
    dupliquer la règle d'autorité côté client."""
    result = await db.execute(select(Squadron).order_by(Squadron.id.asc()))
    squadrons = result.scalars().all()

    # Effectif courant par escadrille (appartenances OUVERTES) -- annonce
    # de la conséquence d'un endormissement (§7.3, cc_sqn_sleep_confirm).
    counts = dict(
        (
            await db.execute(
                select(SquadronMembership.squadron_id, func.count())
                .where(SquadronMembership.ended_at.is_(None))
                .group_by(SquadronMembership.squadron_id)
            )
        ).all()
    )

    squadrons_payload = []
    for sq in squadrons:
        entry = _squadron_to_dict(sq)
        entry["member_count"] = counts.get(sq.id, 0)
        squadrons_payload.append(entry)

    actor_id = int(user["id"])
    own_stmt = select(SquadronMembership.squadron_id, SquadronMembership.role).where(
        SquadronMembership.profile_id == actor_id,
        SquadronMembership.ended_at.is_(None),
    )
    own = (await db.execute(own_stmt)).first()

    return {
        "squadrons": squadrons_payload,
        "you": {
            "is_admin": is_admin(user),
            "squadron_id": own[0] if own else None,
            "role": own[1] if own else None,
        },
    }


# =========================================================================
# Lot 3.2e « Les Escadrilles », volet ① -- les quatre routes d'écriture.
# =========================================================================


async def _active_squadron_holding_role(
    db: AsyncSession, discord_role_id: str, exclude_id: int | None = None
) -> Squadron | None:
    """Escadrille ACTIVE portant déjà `discord_role_id`, hors `exclude_id`
    (§6.1/§6.2). Filet applicatif AVANT écriture -- l'index unique partiel
    (migration 0016) reste le juge final en base, cf. `IntegrityError`
    attrapée à chaque commit d'écriture du rôle."""
    stmt = select(Squadron).where(
        Squadron.discord_role_id == discord_role_id,
        Squadron.status == "actif",
    )
    if exclude_id is not None:
        stmt = stmt.where(Squadron.id != exclude_id)
    return (await db.execute(stmt)).scalar_one_or_none()


# Lot « Le Centre côté serveur » : les bornes de l'identité d'une escadrille.
# Un refus est un `HTTPException` de la route, jamais une borne Pydantic
# (`max_length` rendrait un `detail` en liste, que l'écran afficherait mal).
_DESIGNATION_MAX = 24
_CALLSIGN_MAX = 32
_FULL_NAME_MAX = 100


def _bornes_escadrille(designation, callsign, full_name) -> Optional[str]:
    """Lot « Le Centre côté serveur » : le texte du PREMIER refus de longueur,
    ou `None`. Chaque argument est une chaîne déjà `strip()`-ée, ou `None`
    (champ absent ou vide) ; la longueur est celle de `len()`, borne comprise
    (24 passe, 25 est refusé). Ordre : identifiant, callsign, nom complet.
    Fonction PURE : testée hors ligne (tests/test_centre_serveur.py)."""
    if designation is not None and len(designation) > _DESIGNATION_MAX:
        return f"L'identifiant dépasse {_DESIGNATION_MAX} caractères."
    if callsign is not None and len(callsign) > _CALLSIGN_MAX:
        return f"Le callsign dépasse {_CALLSIGN_MAX} caractères."
    if full_name is not None and len(full_name) > _FULL_NAME_MAX:
        return f"Le nom complet dépasse {_FULL_NAME_MAX} caractères."
    return None


def _identifiant_pris(designation, escadrilles, sauf_id=None) -> Optional[str]:
    """Lot « Le Centre côté serveur » : la désignation de la première AUTRE
    escadrille (par `id` croissant, `id != sauf_id`) dont la désignation, sans
    espaces de bord ni casse, égale celle demandée ; `None` sinon.
    `escadrilles` : des couples `(id, désignation)`, TOUTES, en sommeil
    comprises. Fonction PURE."""
    voulue = designation.strip().lower()
    for sid, nom in sorted(escadrilles, key=lambda c: c[0]):
        if sid != sauf_id and (nom or "").strip().lower() == voulue:
            return nom
    return None


async def _toutes_escadrilles(db: AsyncSession) -> list:
    """Les couples `(id, désignation)` de toutes les escadrilles, en sommeil
    comprises -- l'entrée de `_identifiant_pris`."""
    return [
        (sid, nom)
        for sid, nom in (
            await db.execute(select(Squadron.id, Squadron.designation))
        ).all()
    ]


@router.post("/squadrons")
async def create_squadron(
    payload: SquadronCreatePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Créer une escadrille (§2 point 1) -- administrateur seul, patron de
    `POST /api/debrief/campaigns`. Toujours créée `actif` : une escadrille
    en sommeil n'aurait jamais eu de rôle à perdre. Rattachée à l'unique
    `wing` du dépôt (Lot 2.2b)."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    designation = (payload.designation or "").strip()
    if not designation:
        raise HTTPException(status_code=422, detail="Identifiant requis.")
    # Lot « L'identité de l'escadrille » : facultatifs, vides -> NULL.
    callsign = (payload.callsign or "").strip() or None
    full_name = (payload.full_name or "").strip() or None
    # Lot « Le Centre côté serveur » : les bornes (422), puis l'unicité (409).
    refus = _bornes_escadrille(designation, callsign, full_name)
    if refus is not None:
        raise HTTPException(status_code=422, detail=refus)
    pris = _identifiant_pris(designation, await _toutes_escadrilles(db))
    if pris is not None:
        raise HTTPException(
            status_code=409, detail=f"Cet identifiant est déjà celui de {pris}."
        )

    role_id = str(payload.discord_role_id) if payload.discord_role_id else None
    if role_id:
        holder = await _active_squadron_holding_role(db, role_id)
        if holder is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Ce rôle Discord rattache déjà {holder.designation}.",
            )

    wing_id = (
        await db.execute(select(Wing.id).order_by(Wing.id.asc()).limit(1))
    ).scalar_one_or_none()
    if wing_id is None:
        raise HTTPException(
            status_code=500, detail="Aucune escadre en base -- incident à signaler."
        )

    squadron = Squadron(
        designation=designation,
        callsign=callsign,
        full_name=full_name,
        status="actif",
        discord_role_id=role_id,
        wing_id=wing_id,
    )
    db.add(squadron)
    # Lot « Polish du Centre » : le journal, dans la transaction de la route.
    journal.consigner(
        db, user, "squadron.create", objet=designation,
        lignes=journal.ecarts({}, {
            "designation": designation, "callsign": callsign,
            "full_name": full_name, "discord_role_id": role_id,
        }),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ce rôle Discord rattache déjà une escadrille active.",
        )
    await db.refresh(squadron)
    return _squadron_to_dict(squadron)


@router.patch("/squadrons/{squadron_id}")
async def update_squadron(
    squadron_id: int,
    payload: SquadronUpdatePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renommer / changer le callsign ou le nom complet / re-router le rôle
    Discord (§5.3, §5.4, §6.1). ⚠⚠ DEUX gardes dans une route :
    `can_admin_squadron()` (admin, chef ou adjoint DE CETTE escadrille) ouvre
    l'entrée et autorise `designation`/`callsign`/`full_name` ; SEUL un
    administrateur peut toucher
    `discord_role_id`. Refus GLOBAL, jamais partiel -- si le corps porte
    `discord_role_id` et que l'agissant n'est pas administrateur, RIEN
    n'est écrit, pas même la désignation."""
    squadron = await db.get(Squadron, squadron_id)
    if squadron is None:
        raise HTTPException(status_code=404, detail="Escadrille introuvable.")

    if not await can_admin_squadron(db, user, squadron_id):
        raise HTTPException(
            status_code=403,
            detail="Réservé à l'administrateur, au chef ou à l'adjoint de cette escadrille.",
        )

    fields = payload.model_fields_set

    if "discord_role_id" in fields and not is_admin(user):
        raise HTTPException(
            status_code=403,
            detail="Le rôle Discord de rattachement est réservé à l'administrateur.",
        )

    new_designation = squadron.designation
    if "designation" in fields:
        new_designation = (payload.designation or "").strip()
        if not new_designation:
            raise HTTPException(status_code=422, detail="Identifiant requis.")

    # Lot « Le Centre côté serveur » : les bornes seulement sur les champs
    # PRÉSENTS au corps (une valeur déjà en base au-delà d'une borne n'est
    # refusée que si le corps la renvoie) ; l'unicité seulement si
    # `designation` y est, hors l'escadrille elle-même.
    refus = _bornes_escadrille(
        new_designation if "designation" in fields else None,
        ((payload.callsign or "").strip() or None) if "callsign" in fields else None,
        ((payload.full_name or "").strip() or None) if "full_name" in fields else None,
    )
    if refus is not None:
        raise HTTPException(status_code=422, detail=refus)
    if "designation" in fields:
        pris = _identifiant_pris(
            new_designation, await _toutes_escadrilles(db), sauf_id=squadron_id
        )
        if pris is not None:
            raise HTTPException(
                status_code=409, detail=f"Cet identifiant est déjà celui de {pris}."
            )

    new_aircraft = squadron.aircraft
    if "aircraft" in fields:
        new_aircraft = _normalize_aircraft(payload.aircraft)

    # Lot « La config d'escadre de Mission Plan fabriquée par le Centre » : les
    # appareils de référence des livrées sont ceux de l'escadrille APRÈS ce
    # PATCH. Un PATCH qui change les appareils élague d'abord ce qui est en
    # base, puis ce que le corps porte l'emporte (et se normalise).
    appareils_ref = list(new_aircraft or [])
    new_liveries = squadron.liveries
    new_default_liveries = squadron.default_liveries
    if "aircraft" in fields:
        new_liveries, new_default_liveries = _elaguer_livrees(
            new_liveries, new_default_liveries, appareils_ref
        )
    if "liveries" in fields:
        new_liveries = _normaliser_livrees(
            [l.model_dump() for l in (payload.liveries or [])], appareils_ref
        )
    if "default_liveries" in fields:
        new_default_liveries = _normaliser_defauts(payload.default_liveries, appareils_ref)

    new_nickname = squadron.nickname
    if "nickname" in fields:
        new_nickname = (payload.nickname or "").strip() or None
        if new_nickname and len(new_nickname) > NICKNAME_MAX:
            raise HTTPException(
                status_code=422, detail=f"Le surnom tient en {NICKNAME_MAX} caractères."
            )

    new_role_id = squadron.discord_role_id
    if "discord_role_id" in fields:
        new_role_id = str(payload.discord_role_id) if payload.discord_role_id else None
        if new_role_id and squadron.status == "actif":
            holder = await _active_squadron_holding_role(
                db, new_role_id, exclude_id=squadron_id
            )
            if holder is not None:
                raise HTTPException(
                    status_code=409,
                    detail=f"Ce rôle Discord rattache déjà {holder.designation}.",
                )

    renamed = "designation" in fields and new_designation != squadron.designation

    avant_journal = _etat_escadrille(squadron)   # lot « Polish du Centre »
    squadron.designation = new_designation
    # Lot « L'identité de l'escadrille » : facultatifs, vides -> NULL.
    if "callsign" in fields:
        squadron.callsign = (payload.callsign or "").strip() or None
    if "full_name" in fields:
        squadron.full_name = (payload.full_name or "").strip() or None
    if "nickname" in fields:
        squadron.nickname = new_nickname
    if "discord_role_id" in fields:
        squadron.discord_role_id = new_role_id
    if "aircraft" in fields:
        squadron.aircraft = new_aircraft
    if "aircraft" in fields or "liveries" in fields or "default_liveries" in fields:
        squadron.liveries = new_liveries
        squadron.default_liveries = new_default_liveries

    if renamed:
        # ⚠⚠ dette 16 (§5.3) -- `Profile.squadron` recopie la désignation
        # EN TOUTES LETTRES, lue par le Planning (app/events.py ~L1063).
        # MÊME transaction. Appartenances OUVERTES seulement -- le champ
        # décrit où est le membre AUJOURD'HUI, pas où il était ; les
        # appartenances closes ne sont jamais touchées.
        await db.execute(
            update(Profile)
            .where(
                Profile.id.in_(
                    select(SquadronMembership.profile_id).where(
                        SquadronMembership.squadron_id == squadron_id,
                        SquadronMembership.ended_at.is_(None),
                    )
                )
            )
            .values(squadron=new_designation)
        )

    journal.consigner(
        db, user, "squadron.edit", objet=squadron.designation,
        lignes=journal.ecarts(avant_journal, _etat_escadrille(squadron)),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ce rôle Discord rattache déjà une escadrille active.",
        )
    await db.refresh(squadron)
    return _squadron_to_dict(squadron)


@router.put("/squadrons/{squadron_id}/crest")
async def put_squadron_crest(
    squadron_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Téléverser/remplacer l'écusson d'une escadrille (Lot 3.2e, volet ②,
    §7.1). Multipart, un seul champ fichier. **13 → 14 routes du module.**

    ⚠⚠ Route séparée de `PATCH /squadrons/{id}` -- ne JAMAIS les fondre
    (motif d'arrêt du brief sinon). Ce `PATCH` porte déjà deux gardes dans
    une route et est éprouvé par trois portes ; le passer en multipart
    pour y loger un fichier rouvrirait tout ce contrôle, et un envoi à
    moitié réussi laisserait la rangée à moitié écrite.

    **Autorité : `can_admin_squadron()`** -- administrateur, chef ou
    adjoint DE CETTE escadrille précise. Même autorité que le nom (le
    cadrage 3.2e §3 range l'écusson avec la désignation) -- réemployée
    telle quelle, jamais réécrite.

    **Ordre imposé, non négociable (§7.1) :**
    1. escadrille existe -> sinon 404 ;
    2. autorité -> sinon 403 (AVANT la lecture du fichier -- un refus ne
       doit jamais coûter le décodage d'une image de 2 Mo, sans quoi la
       route deviendrait un levier de charge accessible à tout compte du
       module, cf. P23) ;
    3. lecture bornée, reconnaissance, décodage, normalisation (`app.crests`) ;
    4. écriture du temporaire (pas encore visible) ;
    5. `crest_sha` en base, commit ;
    6. remplacement atomique (APRÈS le commit -- si le commit échoue, le
       fichier live n'a jamais été touché).
    """
    squadron = await db.get(Squadron, squadron_id)
    if squadron is None:
        raise HTTPException(status_code=404, detail="Escadrille introuvable.")

    if not await can_admin_squadron(db, user, squadron_id):
        raise HTTPException(
            status_code=403,
            detail="Réservé à l'administrateur, au chef ou à l'adjoint de cette escadrille.",
        )

    try:
        raw_bytes = await crests.read_bounded(file)
    except crests.CrestTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    try:
        png_bytes, report = crests.normalize_crest(raw_bytes)
    except crests.CrestInvalidFormat as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    tmp_path = crests.write_temp(squadron_id, png_bytes)
    try:
        squadron.crest_sha = hashlib.sha256(png_bytes).hexdigest()
        journal.consigner(db, user, "squadron.crest", objet=squadron.designation, toujours=True)
        await db.commit()
        await db.refresh(squadron)
        crests.finalize_crest(tmp_path, squadron_id)
    finally:
        # P21 -- aucun temporaire résiduel après un téléversement réussi
        # (déjà déplacé par finalize_crest, donc n'existe plus) NI après un
        # refus (le commit a levé avant finalize_crest -- idempotent.
        crests.discard_temp(tmp_path)

    payload = _squadron_to_dict(squadron)
    payload["crest_report"] = {
        "source_format": report.source_format,
        "source_width": report.source_width,
        "source_height": report.source_height,
        "source_bytes": report.source_bytes,
        "stored_side": report.stored_side,
        "stored_bytes": report.stored_bytes,
        "first_frame_retained": report.first_frame_retained,
    }
    return payload


@router.put("/squadrons/{squadron_id}/sleep")
async def sleep_squadron(
    squadron_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Endormir (§5.2, §6) -- administrateur seul. `status` -> 'sommeil' ET
    `discord_role_id` -> NULL, dans la MÊME transaction (§2 point 6 :
    aucune escadrille ne disparaît, elle dort). Aucun geste sur les
    appartenances -- `_resolve_squadron_id()` filtre déjà `status ==
    'actif'` ; `sync_squadron_membership()` clôt l'appartenance ouverte à
    la connexion suivante. Le produit fait déjà ce que la réalité impose."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    squadron = await db.get(Squadron, squadron_id)
    if squadron is None:
        raise HTTPException(status_code=404, detail="Escadrille introuvable.")

    squadron.status = "sommeil"
    squadron.discord_role_id = None
    journal.consigner(db, user, "squadron.sleep", objet=squadron.designation, toujours=True)
    await db.commit()
    await db.refresh(squadron)
    return _squadron_to_dict(squadron)


@router.put("/squadrons/{squadron_id}/wake")
async def wake_squadron(
    squadron_id: int,
    payload: SquadronWakePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Réveiller (§2 point 5, §6.2) -- administrateur seul, `discord_role_id`
    OBLIGATOIRE au corps. Réveiller n'est pas un interrupteur : un réveil
    sans rôle produirait une escadrille active qui ne rattache personne,
    en silence -- refusé en 409, jamais un 422 de schéma."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    squadron = await db.get(Squadron, squadron_id)
    if squadron is None:
        raise HTTPException(status_code=404, detail="Escadrille introuvable.")

    role_id = str(payload.discord_role_id) if payload.discord_role_id else None
    if not role_id:
        raise HTTPException(
            status_code=409,
            detail="Le réveil exige un rôle Discord de rattachement.",
        )

    holder = await _active_squadron_holding_role(db, role_id, exclude_id=squadron_id)
    if holder is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Ce rôle Discord rattache déjà {holder.designation}.",
        )

    ancien_role = squadron.discord_role_id
    squadron.status = "actif"
    squadron.discord_role_id = role_id
    journal.consigner(
        db, user, "squadron.wake", objet=squadron.designation, toujours=True,
        lignes=journal.ecarts({"discord_role_id": ancien_role}, {"discord_role_id": role_id}),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ce rôle Discord rattache déjà une escadrille active.",
        )
    await db.refresh(squadron)
    return _squadron_to_dict(squadron)


# --- Campagnes (Lot 3.4, §3/§6/§7) -------------------------------------------
#
# Trois routes neuves (brief §8 P5) : liste (tous simulateurs confondus,
# une campagne close reste dans la liste -- §11, pas d'écran Archives à ce
# lot), création ET modification réunies dans une seule route (même bloc
# de formulaire côté écran, §3), suppression sous garde (§7). Distinctes
# des routes `/api/debrief/campaigns` (`app/debrief/api.py`, lot 2.3) --
# celles-ci restent administrées à l'API, filtrées par simulateur, et
# continuent de servir les deux sélecteurs du Débriefing (dépôt, édition
# de session) ; ce lot ne les touche que sur les trois colonnes retirées
# (§4) et ne leur ajoute ni garde ni verrou nouveaux.


async def _campaign_mission_count(db: AsyncSession, campaign_id: uuid.UUID) -> int:
    """Le compte qui gouverne le verrou simulateur (§5) ET le refus de
    suppression (§7) -- UNE fonction, deux appelants, jamais recalculé
    différemment. Le compte vient toujours du serveur (§7, dernier
    avertissement) : cette fonction est le seul endroit qui l'interroge."""
    return (
        await db.scalar(
            select(func.count(DebriefSession.id)).where(
                DebriefSession.campaign_id == campaign_id
            )
        )
    ) or 0


@router.get("/campaigns")
async def list_command_campaigns(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """La liste, lisible par tout compte admis dans le module (§3 légende
    maquette : « reste lisible par tous ceux qui entrent dans le module »)
    -- aucune garde de capacité ici, à la différence des deux routes
    suivantes. Tous simulateurs confondus (colonne « Simulateur » de
    l'écran) ; le compte de missions par campagne est calculé en une seule
    requête agrégée, jamais en N+1."""
    stmt = (
        select(Campaign, func.count(DebriefSession.id))
        .outerjoin(DebriefSession, DebriefSession.campaign_id == Campaign.id)
        .group_by(Campaign.id)
        .order_by(Campaign.name)
    )
    rows = (await db.execute(stmt)).all()
    return {"campaigns": [_campaign_full_dict(c, n) for c, n in rows]}


@router.post("/campaigns")
async def upsert_command_campaign(
    payload: CampaignUpsertPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Création ET modification (§3/§6) -- `id` absent crée, `id` présent
    modifie la campagne désignée. Capacité `campaign.manage`, admin
    toujours passant (§6, garde-fou anti-lock-out, même patron que
    `can_edit_session`). `name` reste seul obligatoire dans les deux cas.

    Verrou simulateur (§5) : une modification qui changerait `sim` est
    refusée en 409, avec le compte, DÈS QU'AU MOINS UNE mission est
    rattachée -- déplacer une campagne rendrait ses missions invisibles
    dans des sélecteurs filtrés par simulateur. Le champ désactivé côté
    écran n'est qu'une commodité : cette route revérifie, elle ne fait
    jamais confiance à un champ simplement absent du corps."""
    if not (is_admin(user) or await can_manage_campaigns(db, user)):
        raise HTTPException(
            status_code=403,
            detail="Réservé aux porteurs du droit de gestion des campagnes.",
        )

    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nom de campagne requis.")
    if len(name) > 80:
        raise HTTPException(
            status_code=422, detail="Nom de campagne trop long (80 caractères max)."
        )
    map_name = (payload.map_name or "").strip() or None
    description = (payload.description or "").strip() or None
    status = payload.status or "en_cours"
    if status not in ("en_cours", "close"):
        raise HTTPException(
            status_code=422, detail="status doit être 'en_cours' ou 'close'."
        )

    if payload.id:
        try:
            campaign_id = uuid.UUID(payload.id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Campagne introuvable.")
        campaign = await db.get(Campaign, campaign_id)
        if campaign is None:
            raise HTTPException(status_code=404, detail="Campagne introuvable.")

        new_sim = (payload.sim or campaign.sim or "dcs").strip() or "dcs"
        mission_count = await _campaign_mission_count(db, campaign.id)
        if new_sim != campaign.sim and mission_count > 0:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Le simulateur ne peut plus être changé : {mission_count} "
                    "missions sont rattachées à cette campagne."
                ),
            )
        avant_journal = _etat_campagne(campaign)   # lot « Polish du Centre »
        campaign.name = name
        campaign.sim = new_sim
        campaign.map_name = map_name
        campaign.status = status
        campaign.description = description
        journal.consigner(
            db, user, "campaign.edit", objet=campaign.name,
            lignes=journal.ecarts(avant_journal, _etat_campagne(campaign)),
        )
    else:
        mission_count = 0
        campaign = Campaign(
            name=name,
            sim=(payload.sim or "dcs").strip() or "dcs",
            map_name=map_name,
            status=status,
            description=description,
        )
        db.add(campaign)
        journal.consigner(
            db, user, "campaign.create", objet=name,
            lignes=journal.ecarts({}, {
                "name": name, "sim": campaign.sim, "map_name": map_name,
                "status": status, "description": description,
            }),
        )

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Une campagne de ce nom existe déjà pour ce simulateur.",
        )
    await db.refresh(campaign)
    return _campaign_full_dict(campaign, mission_count)


@router.delete("/campaigns/{campaign_id}")
async def delete_command_campaign(
    campaign_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Suppression sous garde (§7) -- capacité `campaign.delete`, distincte
    de `campaign.manage` (arbitrage du porteur du 22 août). Refusée en 409 dès
    qu'au moins une mission est rattachée, AVEC le nombre : le besoin visé
    est l'erreur de saisie, pas l'histoire (§5.7 du cadrage CC, « on ne
    supprime rien » pour ce qui a servi). La clé étrangère l'imposerait de
    toute façon -- ce contrôle refuse proprement plutôt que de laisser
    remonter une erreur d'intégrité technique."""
    if not (is_admin(user) or await can_delete_campaigns(db, user)):
        raise HTTPException(
            status_code=403,
            detail="Réservé aux porteurs du droit de suppression des campagnes.",
        )
    campaign = await db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campagne introuvable.")

    mission_count = await _campaign_mission_count(db, campaign.id)
    if mission_count > 0:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{mission_count} missions sont rattachées à cette campagne : "
                "détache-les d'abord depuis l'édition de session."
            ),
        )
    journal.consigner(db, user, "campaign.delete", objet=campaign.name, toujours=True)
    await db.delete(campaign)
    await db.commit()
    return {"deleted": True}


@router.get("/members")
async def list_command_members(db: AsyncSession = Depends(get_db)):
    """Annuaire des membres (lot 3.2c, Volet 3). `Profile` LEFT JOIN
    l'appartenance OUVERTE (`ended_at IS NULL`) LEFT JOIN `Squadron` : les
    deux jointures sont externes, un Free Agent (aucune appartenance
    ouverte) reste dans le résultat. Tri serveur `global_name, username`
    -- miroir de `app/events.py:1055`, base stable ; le tri d'affichage
    (groupé par escadrille) est fait côté front.

    Lot « L'appel » (R184, R185) : sans les profils archivés, et avec le
    compte rendu du dernier appel (`appel`), que l'écran montre en tête.
    L'annuaire de l'écran Droits lit aussi cette route : un archivé qui y
    détient un droit nominatif s'affiche par son identifiant, avec la
    mention d'absence -- le repli existant."""
    result = await db.execute(
        select(Profile, SquadronMembership.role, Squadron.designation)
        .select_from(Profile)
        .outerjoin(
            SquadronMembership,
            and_(
                SquadronMembership.profile_id == Profile.id,
                SquadronMembership.ended_at.is_(None),
            ),
        )
        .outerjoin(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .where(Profile.archived_at.is_(None))
        .order_by(Profile.global_name, Profile.username)
    )
    rows = result.all()
    return {
        "appel": appel.dernier_appel(),
        "members": [
            {
                # ⚠ str() impératif : snowflake Discord (BigInteger, 19
                # chiffres) au-delà de Number.MAX_SAFE_INTEGER -- idiome
                # repris de `app/events.py:1059`.
                "id": str(p.id),
                "name": p.global_name or p.username,
                "avatar_hash": p.avatar_hash,
                "squadron": designation,
                "rank": role,
                "is_admin": str(p.id) in settings.admin_ids_set,
                "last_login_at": p.last_login_at.isoformat() if p.last_login_at else None,
            }
            for p, role, designation in rows
        ]
    }


@router.post("/members/appel")
async def post_members_appel(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « L'appel » (R185) -- le bouton « Faire l'appel » de l'écran
    Membres. Ouvert à quiconque entre au Centre (arbitrage du porteur, 30/09) :
    la garde est celle du point de montage. Un appel déjà en cours n'en lance
    pas un second (`appel.faire_appel`). Rend la charge de `GET /members`,
    lue après l'appel : l'écran se redessine d'un seul aller-retour.

    Lot « Polish du Centre » : l'appel au bouton se consigne (qui, combien sont
    entrés -- arrivés ou revenus --, combien sont sortis) ; un appel qui rend une
    `erreur` se consigne sans lignes. L'appel automatique quotidien ne se consigne
    pas. La réponse ne change pas."""
    cr = await appel.faire_appel("bouton")
    lignes = [] if cr.get("erreur") else journal.ecarts({}, {
        # `arrivent` est groupé par destination (`{"vers", "noms"}`) : on compte les noms.
        "entres": sum(len(g["noms"]) for g in cr.get("arrivent") or []) + len(cr.get("reviennent") or []),
        "sortis": len(cr.get("sortent") or []),
    })
    journal.consigner(db, user, "members.appel", lignes=lignes, toujours=True)
    await db.commit()
    return await list_command_members(db)


@router.get("/relances")
async def get_relances(db: AsyncSession = Depends(get_db)):
    """Lot « Les relances » (R8, R9) -- la liste de l'écran Membres : les
    pilotes d'escadrille en retard de planning, par escadrille, les
    destinataires des MP et ceux dont le dernier envoi est refusé. Calculée à
    la demande ; la garde est celle du point de montage du Centre, comme
    `GET /members`. La forme est lue par le banc : ne la changez pas."""
    return await relances.etat(db)


# =========================================================================
# Lot 3.2d « Les Droits », premier temps -- Volet 3 : les six routes.
# =========================================================================

_DISCORD_ROLES_CACHE: dict = {"roles": None, "fetched_at": 0.0}
_DISCORD_ROLES_TTL_SECONDS = 300


@router.get("/discord-roles")
async def get_discord_roles():
    """Rôles du serveur Discord, triés par nom (§7.1). Réemploi du client
    bot existant (`_bot_request`, app/discord_rsvp.py:241-269), qui porte
    déjà le retry 429 et NE PROPAGE JAMAIS d'exception. Cache en mémoire de
    processus, 5 minutes, avec conservation de la DERNIÈRE VALEUR BONNE :
    si Discord est injoignable et que le cache porte une valeur, la
    renvoyer avec `available:true` ; s'il est vide, `{"roles": [],
    "available": false}`. Ne jamais lever. Filtre `@everyone` (son `id`
    vaut celui du guild)."""
    now = time.monotonic()
    if (
        _DISCORD_ROLES_CACHE["roles"] is not None
        and (now - _DISCORD_ROLES_CACHE["fetched_at"]) < _DISCORD_ROLES_TTL_SECONDS
    ):
        return {"roles": _DISCORD_ROLES_CACHE["roles"], "available": True}

    response = await _bot_request("GET", f"guilds/{settings.DISCORD_GUILD_ID}/roles")
    if response is not None and response.status_code == 200:
        try:
            raw = response.json()
        except ValueError:
            raw = None
        if isinstance(raw, list):
            roles = sorted(
                (
                    {"id": str(r.get("id")), "name": str(r.get("name"))}
                    for r in raw
                    if str(r.get("id")) != str(settings.DISCORD_GUILD_ID)
                ),
                key=lambda r: r["name"],
            )
            _DISCORD_ROLES_CACHE["roles"] = roles
            _DISCORD_ROLES_CACHE["fetched_at"] = now
            return {"roles": roles, "available": True}

    # Discord injoignable ou réponse invalide -- dernière valeur bonne.
    if _DISCORD_ROLES_CACHE["roles"] is not None:
        return {"roles": _DISCORD_ROLES_CACHE["roles"], "available": True}
    return {"roles": [], "available": False}


def _chef_a_le_centre(profile_id, roles_snapshot, chef_role_id, admin_ids) -> bool:
    """Lot « Le Centre de Commandement dit ce qu'il fait » (R3, R4) -- pure : la
    réponse de `has_command_access` pour un CHEF (la branche adjoint ne le
    concerne pas). Vrai si le compte est administrateur (`ADMIN_IDS`), ou si le
    rôle des chefs est configuré et figure dans les rôles relevés ; faux sinon."""
    if str(profile_id) in admin_ids:
        return True
    if not chef_role_id:
        return False
    return str(chef_role_id) in {str(r) for r in (roles_snapshot or [])}


def _deputy_squadron_id(lignes):
    """Lot « Le Centre de Commandement dit ce qu'il fait » (R2, R4) -- pure :
    `lignes` = les appartenances du membre, `(role, ended_at, status,
    squadron_id)`. L'identifiant de l'escadrille ACTIVE dont il est adjoint
    (appartenance ouverte de rang `deputy`), sinon `None`."""
    for role, ended_at, status, squadron_id in lignes:
        if role == "deputy" and ended_at is None and status == "actif":
            return squadron_id
    return None


@router.get("/rights")
async def get_rights(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Tout ce que l'écran Droits affiche, en un appel (§7.2). Escadrilles
    `status = 'actif'` uniquement, triées par `Squadron.id` croissant --
    l'ordre de résolution, pas un ordre alphabétique flatteur. `candidates`
    = membres à appartenance OUVERTE sur CETTE escadrille dont
    `roles_snapshot` (JSONB, photo des rôles prise à la connexion, au clic RSVP,
    au lien de secours et à chaque appel -- PAS Discord en direct) contient
    `chef_role_id` -- vide si `chef_role_id` est nul. `str(...)` sur tout identifiant Discord (idiome
    `app/events.py:1059`).

    Lot « Le Centre de Commandement dit ce qu'il fait » : `you` gagne
    `deputy_squadron_id` (R2) et chaque `leader` non nul gagne `centre` (R3)."""
    is_user_admin = is_admin(user)
    actor_id = int(user["id"])

    leads_stmt = (
        select(SquadronMembership.squadron_id)
        .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .where(
            SquadronMembership.profile_id == actor_id,
            SquadronMembership.role == "leader",
            SquadronMembership.ended_at.is_(None),
            Squadron.status == "actif",
        )
    )
    leads_squadron_id = (await db.execute(leads_stmt)).scalar_one_or_none()

    # Lot « Le Centre de Commandement dit ce qu'il fait » (R2) : l'escadrille
    # active dont le membre est adjoint -- l'écran Droits lui montre son rang.
    deputy_rows = (
        await db.execute(
            select(
                SquadronMembership.role,
                SquadronMembership.ended_at,
                Squadron.status,
                SquadronMembership.squadron_id,
            )
            .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
            .where(SquadronMembership.profile_id == actor_id)
        )
    ).all()
    deputy_squadron_id = _deputy_squadron_id(deputy_rows)

    chef_role_stmt = (
        select(RoleCapability.role_id)
        .where(RoleCapability.capability == "command.access")
        .limit(1)
    )
    chef_role_id = (await db.execute(chef_role_stmt)).scalar_one_or_none()

    squadrons_result = await db.execute(
        select(Squadron).where(Squadron.status == "actif").order_by(Squadron.id.asc())
    )
    squadrons = squadrons_result.scalars().all()
    squadron_ids = [sq.id for sq in squadrons]

    members_by_squadron: dict[int, list] = {sid: [] for sid in squadron_ids}
    if squadron_ids:
        members_stmt = (
            select(Profile, SquadronMembership.role, SquadronMembership.squadron_id)
            .join(SquadronMembership, SquadronMembership.profile_id == Profile.id)
            .where(
                SquadronMembership.squadron_id.in_(squadron_ids),
                SquadronMembership.ended_at.is_(None),
            )
            .order_by(Profile.global_name, Profile.username)
        )
        for profile, role, sid in (await db.execute(members_stmt)).all():
            members_by_squadron[sid].append((profile, role))

    squadrons_payload = []
    for sq in squadrons:
        leader = None
        deputy = None
        members = []
        candidates = []
        for profile, role in members_by_squadron[sq.id]:
            entry = {"id": str(profile.id), "name": profile.global_name or profile.username}
            members.append(entry)
            if role == "leader":
                # Lot « Le Centre de Commandement dit ce qu'il fait » (R3) : une
                # COPIE de l'entrée -- `members` et `candidates` ne gagnent pas `centre`.
                leader = {
                    **entry,
                    "centre": _chef_a_le_centre(
                        profile.id, profile.roles_snapshot, chef_role_id,
                        settings.admin_ids_set,
                    ),
                }
            elif role == "deputy":
                deputy = entry
            snapshot = profile.roles_snapshot or []
            if chef_role_id and chef_role_id in snapshot:
                candidates.append(entry)
        squadrons_payload.append({
            "id": sq.id,
            "designation": sq.designation,
            "leader": leader,
            "deputy": deputy,
            "candidates": candidates,
            "members": members,
            # Lot 3.2d Volet 3, second temps (§6.1) : qualifie chaque rôle
            # d'accès de son rattachement d'escadrille (décision 3, écran
            # Droits). Aucune requête supplémentaire -- déjà chargé sur `sq`.
            "discord_role_id": sq.discord_role_id,
        })

    role_ids = list(
        (
            await db.execute(
                select(RoleCapability.role_id)
                .where(RoleCapability.capability == "event.create")
                .order_by(RoleCapability.role_id)
            )
        ).scalars().all()
    )
    profile_ids = [
        str(pid)
        for pid in (
            await db.execute(
                select(AccountCapability.profile_id)
                .where(AccountCapability.capability == "event.create")
                .order_by(AccountCapability.profile_id)
            )
        ).scalars().all()
    ]

    # Lot 3.2d Volet 3, second temps (§6.1) : accès à l'application, résolu
    # par la même fonction que le login (`auth.py`) et le miroir bot
    # (`discord_rsvp.py`) -- un seul point de vérité.
    app_access_role_ids = await _app_access_role_ids(db)

    # Lot 3.3, §3 -- les deux droits sur le contenu, PAR RÔLE UNIQUEMENT
    # (aucun octroi nominatif, `account_capability` conservée pour
    # `event.create` et `relances.destinataire`). Même patron de requête que `role_ids`
    # ci-dessus (event.create).
    session_edit_role_ids = list(
        (
            await db.execute(
                select(RoleCapability.role_id)
                .where(RoleCapability.capability == "session.edit")
                .order_by(RoleCapability.role_id)
            )
        ).scalars().all()
    )
    event_edit_any_role_ids = list(
        (
            await db.execute(
                select(RoleCapability.role_id)
                .where(RoleCapability.capability == "event.edit_any")
                .order_by(RoleCapability.role_id)
            )
        ).scalars().all()
    )

    # Lot 3.4, §6 -- les deux droits sur les campagnes, MÊME patron de
    # requête que `session_edit_role_ids`/`event_edit_any_role_ids`
    # ci-dessus. `campaign.manage` gouverne création ET modification (un
    # seul droit, même métier) ; `campaign.delete` est distinct
    # (arbitrage du porteur du 22 août).
    campaign_manage_role_ids = list(
        (
            await db.execute(
                select(RoleCapability.role_id)
                .where(RoleCapability.capability == "campaign.manage")
                .order_by(RoleCapability.role_id)
            )
        ).scalars().all()
    )
    campaign_delete_role_ids = list(
        (
            await db.execute(
                select(RoleCapability.role_id)
                .where(RoleCapability.capability == "campaign.delete")
                .order_by(RoleCapability.role_id)
            )
        ).scalars().all()
    )

    # Brief « Accès au module Débriefing », 22 août 2026 -- porte de
    # module, PAS un droit sur le contenu : forme réduite, `role_ids`
    # seulement (§4). Pas d'`impact` ni `from_env` : ces deux champs
    # répondent à des problèmes que `app_access` a et que ce droit n'a
    # pas (aucun garde-fou anti-verrouillage, aucune résolution par
    # variable d'environnement).
    debrief_access_role_ids = list(
        (
            await db.execute(
                select(RoleCapability.role_id)
                .where(RoleCapability.capability == "debrief.access")
                .order_by(RoleCapability.role_id)
            )
        ).scalars().all()
    )

    # Lot « Les relances » (R7) : les rôles dont les porteurs reçoivent les MP
    # de relance. Lot « Les relances nominatives » (R3) : et les comptes
    # choisis par leur nom (`account_capability`), en texte -- snowflake
    # Discord, au-delà de Number.MAX_SAFE_INTEGER.
    relances_role_ids = list(
        (
            await db.execute(
                select(RoleCapability.role_id)
                .where(RoleCapability.capability == "relances.destinataire")
                .order_by(RoleCapability.role_id)
            )
        ).scalars().all()
    )
    relances_profile_ids = [
        str(pid)
        for pid in (
            await db.execute(
                select(AccountCapability.profile_id)
                .where(AccountCapability.capability == "relances.destinataire")
                .order_by(AccountCapability.profile_id)
            )
        ).scalars().all()
    ]

    # Lot 3.3, §4 -- UNE SEULE requête pour tout ce qui suit (impact du
    # bloc 4 ET compte du tableau de référence, bloc 6) : id + snapshot de
    # TOUS les profils. Jamais envoyé au front tel quel -- seuls des
    # agrégats (compte par rôle) en sortent (§4④ : « le compte ne se
    # déduit jamais côté client, le front n'a pas les rôles des membres et
    # ne doit pas les recevoir »).
    all_profiles_snapshots = (
        await db.execute(select(Profile.id, Profile.roles_snapshot))
    ).all()

    # --- §4③/§4④ : impact d'un retrait, PAR rôle de la liste d'accès ---
    # impact(R) = nombre de profils NON ADMINISTRATEURS dont
    # roles_snapshot ∩ app_access_role_ids == {R} exactement. L'exclusion
    # des administrateurs n'est pas un détail (§4③) : un administrateur
    # entre toujours, quels que soient ses rôles -- l'inclure ferait
    # sur-affirmer la phrase, exactement la faute que ce lot répare.
    impact_by_role: dict[str, int] = {rid: 0 for rid in app_access_role_ids}
    if app_access_role_ids:
        for pid, snapshot in all_profiles_snapshots:
            if str(pid) in settings.admin_ids_set:
                continue
            snap = {str(r) for r in (snapshot or [])}
            inter = snap & app_access_role_ids
            if len(inter) == 1:
                (only_role,) = inter
                impact_by_role[only_role] += 1

    # --- §4⑤ : le tableau de référence -- périmètre des rôles que
    # l'application référence, ET EUX SEULS (pas le catalogue complet du
    # serveur Discord) : accès, rattachement d'escadrille, désignation des
    # chefs, édition du planning, plus les deux droits neufs. Ordre
    # déterministe, dédoublonné -- un rôle qui cumule plusieurs offices
    # (ex. rattache une escadrille ET édite le planning) n'apparaît
    # qu'une fois.
    role_reference_perimeter: list[str] = []

    def _add_ref_role(rid: str | None) -> None:
        if rid and rid not in role_reference_perimeter:
            role_reference_perimeter.append(rid)

    for rid in sorted(app_access_role_ids):
        _add_ref_role(rid)
    for sq in squadrons:
        _add_ref_role(sq.discord_role_id)
    _add_ref_role(chef_role_id)
    for rid in role_ids:  # event.create
        _add_ref_role(rid)
    for rid in session_edit_role_ids:
        _add_ref_role(rid)
    for rid in event_edit_any_role_ids:
        _add_ref_role(rid)
    for rid in campaign_manage_role_ids:
        _add_ref_role(rid)
    for rid in campaign_delete_role_ids:
        _add_ref_role(rid)
    for rid in debrief_access_role_ids:
        _add_ref_role(rid)

    # Compte simple par rôle référencé -- TOUS les profils (aucune
    # exclusion d'administrateur ici, à la différence de l'impact
    # ci-dessus : §4⑤ ne le demande pas, c'est un décompte de lecture, pas
    # une conséquence de retrait). Une seule passe sur les données déjà
    # récupérées -- « une seule requête pour tous les rôles » (§4⑤).
    ref_perimeter_set = set(role_reference_perimeter)
    counts_by_role: dict[str, int] = {rid: 0 for rid in role_reference_perimeter}
    for _pid, snapshot in all_profiles_snapshots:
        for rid in (snapshot or []):
            rid = str(rid)
            if rid in ref_perimeter_set:
                counts_by_role[rid] += 1

    role_reference = [
        {"role_id": rid, "count": counts_by_role[rid]}
        for rid in role_reference_perimeter
    ]

    return {
        "you": {
            "is_admin": is_user_admin,
            "leads_squadron_id": leads_squadron_id,
            "deputy_squadron_id": deputy_squadron_id,
        },
        "chef_role_id": chef_role_id,
        "squadrons": squadrons_payload,
        "event_editors": {
            "role_ids": role_ids,
            "profile_ids": profile_ids,
        },
        "content_rights": {
            "session_edit": {"role_ids": session_edit_role_ids},
            "event_edit_any": {"role_ids": event_edit_any_role_ids},
            "campaign_manage": {"role_ids": campaign_manage_role_ids},
            "campaign_delete": {"role_ids": campaign_delete_role_ids},
        },
        "role_reference": role_reference,
        "app_access": {
            "role_ids": sorted(app_access_role_ids),
            "impact": impact_by_role,
        },
        "debrief_access": {
            "role_ids": debrief_access_role_ids,
        },
        "relances": {
            "role_ids": relances_role_ids,
            "profile_ids": relances_profile_ids,
        },
    }


@router.put("/rights/chef-role")
async def put_chef_role(
    payload: ChefRolePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Écrit l'UNIQUE ligne `role_capabilities(role_id, 'command.access')`
    (§7.6) : supprime les lignes existantes de cette capacité, insère la
    nouvelle. `role_id` nul -> aucune ligne. Ce geste peut fermer le
    module à des gens -- il ne peut pas le fermer à l'agissant, admin par
    construction (branche 1 du §6.1). Aucun garde-fou supplémentaire
    requis."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    ancien_role = next(iter(await _roles_de(db, "command.access")), None)   # lot « Polish du Centre »
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "command.access")
    )
    role_id = str(payload.role_id) if payload.role_id else None
    if role_id:
        db.add(RoleCapability(role_id=role_id, capability="command.access"))
    journal.consigner(
        db, user, "rights.chef_role",
        lignes=journal.ecarts({"role_id": ancien_role}, {"role_id": role_id}),
    )
    await db.commit()

    return {"chef_role_id": role_id}


@router.put("/squadrons/{squadron_id}/leader")
async def put_squadron_leader(
    squadron_id: int,
    payload: SquadronLeaderPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Le geste atomique de désignation du chef (§7.3) : abaisser le
    titulaire à `member` s'il existe, `flush()`, PUIS promouvoir -- l'ordre
    et le `flush()` sont impératifs, l'index unique partiel rejetterait
    sinon un instant deux `leader` ouverts (idiome exact de
    `app/squadron.py:104-106`). Si le nouveau chef était `deputy` de cette
    escadrille, son poste d'adjoint est libéré (même ligne, changement de
    rang -- il ne peut pas être les deux)."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    squadron = await db.get(Squadron, squadron_id)
    if squadron is None or squadron.status != "actif":
        raise HTTPException(
            status_code=404, detail="Escadrille introuvable ou non active."
        )

    actor_id = int(user["id"])
    now = datetime.now(timezone.utc)

    target_membership = None
    if payload.profile_id is not None:
        target_id = int(payload.profile_id)
        stmt = select(SquadronMembership).where(
            SquadronMembership.profile_id == target_id,
            SquadronMembership.squadron_id == squadron_id,
            SquadronMembership.ended_at.is_(None),
        )
        target_membership = (await db.execute(stmt)).scalar_one_or_none()
        if target_membership is None:
            raise HTTPException(
                status_code=422,
                detail="Ce compte ne porte pas d'appartenance ouverte sur cette escadrille.",
            )
        chef_role_stmt = (
            select(RoleCapability.role_id)
            .where(RoleCapability.capability == "command.access")
            .limit(1)
        )
        chef_role_id = (await db.execute(chef_role_stmt)).scalar_one_or_none()
        target_profile = await db.get(Profile, target_id)
        snapshot = (target_profile.roles_snapshot if target_profile else None) or []
        if not chef_role_id or chef_role_id not in snapshot:
            raise HTTPException(
                status_code=422,
                detail="Ce membre ne porte pas le rôle Discord des chefs au dernier relevé (connexion ou appel).",
            )

    current_leader_stmt = select(SquadronMembership).where(
        SquadronMembership.squadron_id == squadron_id,
        SquadronMembership.role == "leader",
        SquadronMembership.ended_at.is_(None),
    )
    current_leader = (await db.execute(current_leader_stmt)).scalar_one_or_none()
    ancien_chef = str(current_leader.profile_id) if current_leader is not None else None   # lot « Polish du Centre »
    if current_leader is not None and (
        target_membership is None or current_leader.id != target_membership.id
    ):
        current_leader.role = "member"
        current_leader.role_granted_by = actor_id
        current_leader.role_granted_at = now
        await db.flush()  # impératif -- l'index unique partiel rejetterait sinon un instant deux 'leader' ouverts

    if target_membership is not None:
        target_membership.role = "leader"  # libère aussi le poste d'adjoint : même ligne
        target_membership.role_granted_by = actor_id
        target_membership.role_granted_at = now

    journal.consigner(
        db, user, "squadron.leader", objet=squadron.designation,
        lignes=journal.ecarts(
            {"profile_id": ancien_chef},
            {"profile_id": str(target_membership.profile_id) if target_membership is not None else None},
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Conflit lors de la désignation du chef -- réessayez."
        )

    leader_out = None
    if target_membership is not None:
        promoted = await db.get(Profile, target_membership.profile_id)
        leader_out = {
            "id": str(promoted.id),
            "name": promoted.global_name or promoted.username,
        }
    return {"leader": leader_out}


@router.put("/squadrons/{squadron_id}/deputy")
async def put_squadron_deputy(
    squadron_id: int,
    payload: SquadronDeputyPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Désignation/révocation de l'adjoint (§7.4). Même geste atomique que
    le chef (§7.3), SANS la condition de rôle Discord -- l'adjoint se
    choisit parmi TOUS les membres de l'escadrille. Autorité : admin OU
    `leader` DE CETTE ESCADRILLE PRÉCISE (jamais un leader d'une autre).
    422 si la cible est le `leader` en poste."""
    squadron = await db.get(Squadron, squadron_id)
    if squadron is None or squadron.status != "actif":
        raise HTTPException(
            status_code=404, detail="Escadrille introuvable ou non active."
        )

    actor_id = int(user["id"])
    if not is_admin(user):
        leader_here_stmt = select(SquadronMembership.id).where(
            SquadronMembership.profile_id == actor_id,
            SquadronMembership.squadron_id == squadron_id,
            SquadronMembership.role == "leader",
            SquadronMembership.ended_at.is_(None),
        )
        is_leader_here = (await db.execute(leader_here_stmt)).first() is not None
        if not is_leader_here:
            raise HTTPException(
                status_code=403,
                detail="Réservé à l'administrateur ou au chef de cette escadrille.",
            )

    now = datetime.now(timezone.utc)

    target_membership = None
    if payload.profile_id is not None:
        target_id = int(payload.profile_id)
        stmt = select(SquadronMembership).where(
            SquadronMembership.profile_id == target_id,
            SquadronMembership.squadron_id == squadron_id,
            SquadronMembership.ended_at.is_(None),
        )
        target_membership = (await db.execute(stmt)).scalar_one_or_none()
        if target_membership is None:
            raise HTTPException(
                status_code=422,
                detail="Ce compte ne porte pas d'appartenance ouverte sur cette escadrille.",
            )
        if target_membership.role == "leader":
            raise HTTPException(
                status_code=422, detail="Le chef en poste ne peut pas être aussi adjoint."
            )

    current_deputy_stmt = select(SquadronMembership).where(
        SquadronMembership.squadron_id == squadron_id,
        SquadronMembership.role == "deputy",
        SquadronMembership.ended_at.is_(None),
    )
    current_deputy = (await db.execute(current_deputy_stmt)).scalar_one_or_none()
    ancien_adjoint = str(current_deputy.profile_id) if current_deputy is not None else None   # lot « Polish du Centre »
    if current_deputy is not None and (
        target_membership is None or current_deputy.id != target_membership.id
    ):
        current_deputy.role = "member"
        current_deputy.role_granted_by = actor_id
        current_deputy.role_granted_at = now
        await db.flush()  # impératif -- même contrainte que le chef

    if target_membership is not None:
        target_membership.role = "deputy"
        target_membership.role_granted_by = actor_id
        target_membership.role_granted_at = now

    journal.consigner(
        db, user, "squadron.deputy", objet=squadron.designation,
        lignes=journal.ecarts(
            {"profile_id": ancien_adjoint},
            {"profile_id": str(target_membership.profile_id) if target_membership is not None else None},
        ),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Conflit lors de la désignation de l'adjoint -- réessayez."
        )

    deputy_out = None
    if target_membership is not None:
        promoted = await db.get(Profile, target_membership.profile_id)
        deputy_out = {
            "id": str(promoted.id),
            "name": promoted.global_name or promoted.username,
        }
    return {"deputy": deputy_out}


@router.put("/rights/event-editors")
async def put_event_editors(
    payload: EventEditorsPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remplacement COMPLET des deux listes d'éditeurs du planning (§7.5).
    409 si les deux sont vides -- « au moins un éditeur du planning doit
    subsister ». Les `profile_ids` doivent exister dans `profiles` -> 422
    sinon."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    role_ids = [str(r) for r in payload.role_ids]
    profile_ids_raw = [str(p) for p in payload.profile_ids]

    if not role_ids and not profile_ids_raw:
        raise HTTPException(
            status_code=409, detail="Au moins un éditeur du planning doit subsister."
        )

    profile_ids_int = []
    for pid in profile_ids_raw:
        try:
            profile_ids_int.append(int(pid))
        except ValueError:
            raise HTTPException(
                status_code=422, detail=f"Identifiant de compte invalide : {pid}"
            )

    if profile_ids_int:
        existing_stmt = select(Profile.id).where(Profile.id.in_(profile_ids_int))
        existing_ids = set((await db.execute(existing_stmt)).scalars().all())
        missing = [str(pid) for pid in profile_ids_int if pid not in existing_ids]
        if missing:
            raise HTTPException(
                status_code=422, detail=f"Compte(s) inconnu(s) : {', '.join(missing)}"
            )

    avant_roles = await _roles_de(db, "event.create")   # lot « Polish du Centre »
    avant_comptes = await _comptes_de(db, "event.create")
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "event.create")
    )
    await db.execute(
        delete(AccountCapability).where(AccountCapability.capability == "event.create")
    )
    for rid in role_ids:
        db.add(RoleCapability(role_id=rid, capability="event.create"))
    for pid in profile_ids_int:
        db.add(
            AccountCapability(
                profile_id=pid, capability="event.create", granted_by=int(user["id"])
            )
        )
    journal.consigner(
        db, user, "rights.event_editors",
        lignes=journal.ecarts(
            {"role_ids": avant_roles, "profile_ids": avant_comptes},
            {"role_ids": role_ids, "profile_ids": [str(p) for p in profile_ids_int]},
        ),
    )
    await db.commit()

    return {
        "event_editors": {
            "role_ids": role_ids,
            "profile_ids": [str(p) for p in profile_ids_int],
        }
    }


@router.put("/rights/app-access")
async def put_app_access(
    payload: AppAccessPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remplacement COMPLET de la liste des rôles qui ouvrent la connexion
    (Lot 3.2d Volet 3, second temps, §6.2) -- même patron que
    `PUT /rights/event-editors`. Administrateur seul -> 403 sinon.
    409 si la liste est vide -- « au moins un rôle doit ouvrir la
    connexion ». AUCUN garde-fou serveur sur le rôle que l'agissant porte
    lui-même : l'administrateur entre inconditionnellement (§5.1), il ne
    peut pas se verrouiller dehors -- le garde-fou est une confirmation
    d'écran, pas une règle serveur. AUCUNE validation contre la liste des
    rôles du serveur Discord : un rôle référencé mais absent du serveur
    reste conservable et retirable, le signaler est le travail de l'écran.
    """
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    role_ids = [str(r) for r in payload.role_ids]

    if not role_ids:
        raise HTTPException(
            status_code=409, detail="Au moins un rôle doit ouvrir la connexion."
        )

    avant_roles = await _roles_de(db, "app.access")   # lot « Polish du Centre »
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "app.access")
    )
    for rid in role_ids:
        db.add(RoleCapability(role_id=rid, capability="app.access"))
    journal.consigner(
        db, user, "rights.app_access",
        lignes=journal.ecarts({"role_ids": avant_roles}, {"role_ids": role_ids}),
    )
    await db.commit()

    # Sans quoi l'effet immédiat promis par l'écran Droits n'existe pas
    # (§6.2) -- après commit, jamais avant.
    invalidate_app_access_cache()

    return {
        "app_access": {
            "role_ids": role_ids,
        }
    }


@router.put("/rights/debrief-access")
async def put_debrief_access(
    payload: DebriefAccessPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remplacement COMPLET de la liste des rôles qui ouvrent le module
    Débriefing (brief « Accès au module Débriefing », 22 août 2026) --
    une porte de module a sa route, même patron structurel que
    `PUT /rights/app-access`. Administrateur seul -> 403 sinon.

    **Aucun 409 sur liste vide** (à la différence de `app-access`) :
    vider cette liste est un geste légitime et sans danger -- le module
    redevient réservé aux administrateurs, exactement son état
    d'aujourd'hui ; personne ne perd un accès qu'il ne peut pas
    récupérer (§5 du brief).

    **Aucune invalidation de cache** (à la différence de `app-access`) :
    `app.access` en a un parce qu'il est lu à chaque requête pour garder
    la porte d'entrée. `debrief.access` passe par `has_capability()`,
    lu à chaque requête via `require_debrief_access` -- rien à invalider
    ici (§4 du brief).

    **Aucun compte d'impact** (à la différence de `app_access`) : ce
    champ répond à un problème d'anti-verrouillage que cette porte n'a
    pas."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    role_ids = [str(r) for r in payload.role_ids]

    avant_roles = await _roles_de(db, "debrief.access")   # lot « Polish du Centre »
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "debrief.access")
    )
    for rid in role_ids:
        db.add(RoleCapability(role_id=rid, capability="debrief.access"))
    journal.consigner(
        db, user, "rights.debrief_access",
        lignes=journal.ecarts({"role_ids": avant_roles}, {"role_ids": role_ids}),
    )
    await db.commit()

    return {
        "debrief_access": {
            "role_ids": role_ids,
        }
    }


@router.put("/rights/relances")
async def put_relances(
    payload: RelancesPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les relances » (R7) -- remplacement COMPLET des rôles dont les
    porteurs reçoivent un MP quand un pilote d'escadrille n'a répondu à aucune
    occurrence de la fenêtre de `relances.en_retard` (R1). Administrateur seul -> 403
    sinon. Même patron que `PUT /rights/debrief-access` : aucune 409 sur
    liste vide (sans destinataire, aucun MP ne part) et aucun cache à
    invalider.

    Lot « Les relances nominatives » (R3, R5) : la route remplace aussi, dans
    la même écriture, les COMPTES destinataires (`account_capability`, la
    capacité `relances.destinataire`) ; une clé absente vaut une liste vide.
    Un identifiant de profil inconnu ou non numérique -> 422, avant toute
    écriture : rien ne s'écrit. Un compte archivé est accepté et gardé (il
    n'est jamais destinataire, cf. `relances.retenir_destinataires`) ;
    `granted_by` est l'administrateur qui enregistre, comme pour
    `PUT /rights/event-editors`. Après l'enregistrement, la passe des relances tourne sous
    le verrou de l'appel (`appel.passe_apres_reglage`) et se termine avant la
    réponse : un destinataire ajouté reçoit aussitôt la liste en cours. Une
    erreur de la passe se journalise, la route répond 200."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    role_ids = [str(r) for r in payload.role_ids]

    profile_ids_int: list[int] = []
    for pid in payload.profile_ids:
        try:
            pid_int = int(pid)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail=f"Compte inconnu : {pid}")
        if pid_int not in profile_ids_int:
            profile_ids_int.append(pid_int)

    if profile_ids_int:
        valides = set(
            (
                await db.execute(
                    select(Profile.id).where(Profile.id.in_(profile_ids_int))
                )
            ).scalars().all()
        )
        refuses = [str(pid) for pid in profile_ids_int if pid not in valides]
        if refuses:
            raise HTTPException(
                status_code=422, detail=f"Compte inconnu : {', '.join(refuses)}"
            )

    avant_roles = await _roles_de(db, "relances.destinataire")   # lot « Polish du Centre »
    avant_comptes = await _comptes_de(db, "relances.destinataire")
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "relances.destinataire")
    )
    await db.execute(
        delete(AccountCapability).where(AccountCapability.capability == "relances.destinataire")
    )
    for rid in role_ids:
        db.add(RoleCapability(role_id=rid, capability="relances.destinataire"))
    for pid in profile_ids_int:
        db.add(
            AccountCapability(
                profile_id=pid, capability="relances.destinataire", granted_by=int(user["id"])
            )
        )
    journal.consigner(
        db, user, "rights.relances",
        lignes=journal.ecarts(
            {"role_ids": avant_roles, "profile_ids": avant_comptes},
            {"role_ids": role_ids, "profile_ids": [str(p) for p in profile_ids_int]},
        ),
    )
    await db.commit()

    await appel.passe_apres_reglage()

    return {
        "relances": {
            "role_ids": role_ids,
            "profile_ids": [str(p) for p in profile_ids_int],
        }
    }


@router.put("/rights/content")
async def put_content_rights(
    payload: ContentRightsPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remplacement COMPLET des quatre listes de rôles du bloc « Droits sur
    le contenu » (Lot 3.3, §3 ; étendu Lot 3.4, §6) -- `session.edit`,
    `event.edit_any`, `campaign.manage`, `campaign.delete` -- même patron
    que `PUT /rights/event-editors` / `PUT /rights/app-access`.
    Administrateur seul. **Refus global, jamais partiel** : la seule
    garde de cette route est `is_admin`, testée avant toute écriture --
    un refus ne touche rien, une acceptation écrit les quatre listes dans
    la même transaction. Aucune route neuve pour les deux droits
    campagne (§6) : ils entrent dans le payload de cette route existante.

    **Aucun 409 sur liste vide** (à la différence de `app-access`) :
    vider ces listes ne ferme aucune porte, les administrateurs
    conservent les quatre droits en dur et le créateur d'un événement peut
    toujours modifier le sien (§3)."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    session_edit_role_ids = [str(r) for r in payload.session_edit_role_ids]
    event_edit_any_role_ids = [str(r) for r in payload.event_edit_any_role_ids]
    campaign_manage_role_ids = [str(r) for r in payload.campaign_manage_role_ids]
    campaign_delete_role_ids = [str(r) for r in payload.campaign_delete_role_ids]

    avant_journal = {   # lot « Polish du Centre »
        "session_edit_role_ids": await _roles_de(db, "session.edit"),
        "event_edit_any_role_ids": await _roles_de(db, "event.edit_any"),
        "campaign_manage_role_ids": await _roles_de(db, "campaign.manage"),
        "campaign_delete_role_ids": await _roles_de(db, "campaign.delete"),
    }
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "session.edit")
    )
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "event.edit_any")
    )
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "campaign.manage")
    )
    await db.execute(
        delete(RoleCapability).where(RoleCapability.capability == "campaign.delete")
    )
    for rid in session_edit_role_ids:
        db.add(RoleCapability(role_id=rid, capability="session.edit"))
    for rid in event_edit_any_role_ids:
        db.add(RoleCapability(role_id=rid, capability="event.edit_any"))
    for rid in campaign_manage_role_ids:
        db.add(RoleCapability(role_id=rid, capability="campaign.manage"))
    for rid in campaign_delete_role_ids:
        db.add(RoleCapability(role_id=rid, capability="campaign.delete"))
    journal.consigner(
        db, user, "rights.content",
        lignes=journal.ecarts(avant_journal, {
            "session_edit_role_ids": session_edit_role_ids,
            "event_edit_any_role_ids": event_edit_any_role_ids,
            "campaign_manage_role_ids": campaign_manage_role_ids,
            "campaign_delete_role_ids": campaign_delete_role_ids,
        }),
    )
    await db.commit()

    return {
        "content_rights": {
            "session_edit": {"role_ids": session_edit_role_ids},
            "event_edit_any": {"role_ids": event_edit_any_role_ids},
            "campaign_manage": {"role_ids": campaign_manage_role_ids},
            "campaign_delete": {"role_ids": campaign_delete_role_ids},
        }
    }


# --- Lot « L'écran Escadre du Centre » : l'identité de l'escadre -------------

_SIGLE_RE = re.compile(r"^[A-Z0-9-]{1,12}$")

# Libellé du champ et plafond de caractères, pour « {Champ} : {n} caractères au plus. »
_WING_LIMITS = {
    "designation": ("Désignation", 40),
    "tag": ("Tag", 40),
    "full_name": ("Nom complet", 120),
    "period": ("Période", 60),
}


def _valider_identite_escadre(champs: dict) -> dict:
    """Valide et normalise les SEULS champs présents dans le corps de
    `PATCH /command/wing`. Fonction pure : rend les valeurs normalisées, lève
    `ValueError(message)` -- la route en fait un 422 portant ce message en
    `detail`.

    - `designation`, `tag` : rognés, ni vides ni au-delà de 40 caractères ;
    - `full_name`, `period` : rognés, vide -> `None`, 120 / 60 caractères au
      plus ;
    - `sigle` : rogné et mis en capitales, vide -> `None`, sinon
      `^[A-Z0-9-]{1,12}$`."""
    out: dict = {}
    for cle, valeur in champs.items():
        texte = (valeur or "").strip()
        if cle in ("designation", "tag"):
            libelle, plafond = _WING_LIMITS[cle]
            if not texte:
                article = "La désignation" if cle == "designation" else "Le tag"
                raise ValueError(f"{article} ne peut pas être vide.")
            if len(texte) > plafond:
                raise ValueError(f"{libelle} : {plafond} caractères au plus.")
            out[cle] = texte
        elif cle in ("full_name", "period"):
            libelle, plafond = _WING_LIMITS[cle]
            if len(texte) > plafond:
                raise ValueError(f"{libelle} : {plafond} caractères au plus.")
            out[cle] = texte or None
        elif cle == "sigle":
            texte = texte.upper()
            if texte and not _SIGLE_RE.match(texte):
                raise ValueError(
                    "Le sigle ne prend que des lettres, des chiffres et le tiret, douze au plus."
                )
            out[cle] = texte or None
    return out


def _wing_to_dict(wing: Wing) -> dict:
    """L'identité de l'escadre, EXACTEMENT ces six clés -- `NULL` compris.
    Aussi la clé `wing` de `/api/me`, seule source du front."""
    return {
        "designation": wing.designation,
        "full_name": wing.full_name,
        "period": wing.period,
        "sigle": wing.sigle,
        "tag": wing.tag,
        "emblem_sha": wing.emblem_sha,
    }


async def _load_wing(db: AsyncSession) -> Wing:
    wing = (
        await db.execute(select(Wing).order_by(Wing.id.asc()).limit(1))
    ).scalar_one_or_none()
    if wing is None:
        raise HTTPException(status_code=404, detail="Escadre introuvable.")
    return wing


@router.get("/wing")
async def get_wing(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """L'identité de l'escadre + `you: {is_admin}` -- le front choisit la vue
    administrateur ou la lecture seule. Garde : celle du module (accès au
    Centre), posée au point de montage."""
    wing = await _load_wing(db)
    payload = _wing_to_dict(wing)
    payload["you"] = {"is_admin": is_admin(user)}
    return payload


@router.patch("/wing")
async def patch_wing(
    payload: WingUpdatePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Écrire l'identité de l'escadre -- administrateur seul (403 sinon, rien
    d'écrit). Les champs présents sont validés par `_valider_identite_escadre`
    (422 avec son message). Le tag ne sert qu'à l'affichage (retrait des
    préfixes à la lecture) : rien de stocké n'est réécrit."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    wing = await _load_wing(db)
    champs = {k: getattr(payload, k) for k in payload.model_fields_set}
    try:
        valeurs = _valider_identite_escadre(champs)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    avant_journal = {c: getattr(wing, c) for c in _CHAMPS_ESCADRE}   # lot « Polish du Centre »
    for cle, valeur in valeurs.items():
        setattr(wing, cle, valeur)
    journal.consigner(
        db, user, "wing.edit",
        lignes=journal.ecarts(avant_journal, {c: getattr(wing, c) for c in _CHAMPS_ESCADRE}),
    )
    await db.commit()
    await db.refresh(wing)
    return _wing_to_dict(wing)


@router.put("/wing/emblem")
async def put_wing_emblem(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Téléverser/remplacer l'emblème de l'escadre -- administrateur seul.
    Le circuit exact de `PUT /squadrons/{id}/crest` : autorité d'abord (un
    refus ne coûte jamais le décodage d'une image), lecture bornée (413),
    normalisation (422), temporaire, `emblem_sha` au commit, remplacement
    atomique APRÈS le commit."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    wing = await _load_wing(db)

    try:
        raw_bytes = await crests.read_bounded(file)
    except crests.CrestTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    try:
        png_bytes, report = crests.normalize_crest(raw_bytes)
    except crests.CrestInvalidFormat as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    tmp_path = crests.write_temp_wing(png_bytes)
    try:
        wing.emblem_sha = hashlib.sha256(png_bytes).hexdigest()
        journal.consigner(db, user, "wing.emblem", toujours=True)
        await db.commit()
        await db.refresh(wing)
        crests.finalize_wing_emblem(tmp_path)
    finally:
        crests.discard_temp(tmp_path)

    payload = _wing_to_dict(wing)
    payload["crest_report"] = {
        "source_format": report.source_format,
        "source_width": report.source_width,
        "source_height": report.source_height,
        "source_bytes": report.source_bytes,
        "stored_side": report.stored_side,
        "stored_bytes": report.stored_bytes,
        "first_frame_retained": report.first_frame_retained,
    }
    return payload


# --- Lot « Les référentiels : types et armes » ------------------------------
# L'onglet Référentiels du Centre : à chaque clé DCS d'unité ou d'arme, un
# libellé ; à chaque type, sa catégorie (automatique, ou forcée). Lire est
# ouvert aux porteurs de l'accès au Centre (la garde du module) ; écrire est
# réservé aux administrateurs. Le référentiel ne change que l'AFFICHAGE et la
# catégorie des bilans -- jamais un décompte.

_REF_CONTRAT = "readyroom_referentiel_types_armes"
_REF_CLE_MAX = 120
_REF_LIBELLE_MAX = 60


class ReferentielTypePayload(BaseModel):
    """Corps de `PATCH /command/referentiels/types`. Champs PRÉSENTS seulement
    (`model_fields_set`) : `libelle` absent ne change rien, vide l'efface ;
    `categorie` absente ne change rien, `null` remet l'automatique."""

    cle: str
    libelle: Optional[str] = None
    categorie: Optional[str] = None


class ReferentielArmePayload(BaseModel):
    """Corps de `PATCH /command/referentiels/armes`."""

    cle: str
    libelle: Optional[str] = None


def _ref_libelle(valeur) -> Optional[str]:
    """Un libellé saisi à l'écran : rogné, vide -> `None`, 60 caractères au
    plus (`ValueError` sinon -> 422)."""
    texte = (valeur or "").strip()
    if len(texte) > _REF_LIBELLE_MAX:
        raise ValueError(f"Libellé : {_REF_LIBELLE_MAX} caractères au plus.")
    return texte or None


def _type_ref_to_dict(cle: str, row: Optional[DebriefUnitCategory]) -> dict:
    """Un type du référentiel : `categorie` = la catégorie sous laquelle ses
    destructions se rangent (`categorie_cible`), `categorie_auto` = celle de
    `categorize`, `forcee` = vrai si l'écran en a posé une."""
    return {
        "cle": cle,
        "libelle": row.libelle if row is not None else None,
        "categorie": referentiel.categorie_cible(cle),
        "categorie_auto": categorize.categorize(cle)[1],
        "forcee": bool(row is not None and row.categorie_forcee is not None),
    }


def _cle_tri(cle: str) -> tuple[str, str]:
    return (cle.casefold(), cle)


def _lire_entree_import(entree, vues: set, liste: str, avec_categorie: bool):
    """Lit UNE entrée d'un fichier importé. Rend `(cle, libelle, categorie,
    None)` ou `(cle, None, None, raison)` si l'entrée est refusée.

    `libelle` : `None` = ne change rien (absent, `null`, vide). `categorie` :
    `"absente"` (ne change rien), `None` (remet l'automatique) ou une valeur de
    `CATEGORIES`. Une clé n'entre dans `vues` que si elle est lisible : la
    seconde occurrence d'une même clé est refusée (par liste : une clé peut
    être à la fois un type et une arme)."""
    if not isinstance(entree, dict):
        return ("", None, None, f"{liste} : entrée illisible")
    cle = entree.get("cle")
    if not isinstance(cle, str) or not cle.strip():
        return ("", None, None, f"{liste} : clé absente ou vide")
    affichee = cle if len(cle) <= 40 else cle[:40] + "…"
    if len(cle) > _REF_CLE_MAX:
        return (affichee, None, None, f"{liste} : clé de plus de {_REF_CLE_MAX} caractères")
    if cle in vues:
        return (cle, None, None, f"{liste} : clé en double dans le fichier")
    vues.add(cle)

    libelle = None
    brut = entree.get("libelle")
    if brut is not None:
        if not isinstance(brut, str):
            return (cle, None, None, f"{liste} : libellé illisible")
        libelle = brut.strip() or None
        if libelle is not None and len(libelle) > _REF_LIBELLE_MAX:
            return (
                cle, None, None,
                f"{liste} : libellé de plus de {_REF_LIBELLE_MAX} caractères",
            )

    categorie = "absente"
    if avec_categorie and "categorie" in entree:
        brut = entree["categorie"]
        if brut is None:
            categorie = None
        elif not isinstance(brut, str) or brut not in referentiel.CATEGORIES:
            return (cle, None, None, f"{liste} : catégorie « {brut} » inconnue")
        else:
            categorie = brut
    return (cle, libelle, categorie, None)


def _analyser_import(contenu: dict, types_existants: dict, armes_existantes: dict) -> dict:
    """Analyse un fichier de référentiel (contrat `readyroom_referentiel_types_
    armes`, version 1). Fonction PURE : n'écrit rien, ne lit pas la base.

    - `types_existants` : `{cle: {"libelle": str | None, "categorie_forcee":
      str | None}}` (les lignes de `debrief_unit_category`) ;
    - `armes_existantes` : `{cle: libelle | None}` (les lignes de
      `referentiel_arme`).

    Rend `{"bilan": ..., "ecritures": {"types": [...], "armes": [...]}}`.
    `ValueError(message)` si le fichier est illisible (contrat ou version
    différents, `types` ou `armes` absents ou qui ne sont pas des listes) --
    la route en fait un 422.

    Les règles : une entrée refusée (clé vide ou de plus de 120 caractères,
    libellé de plus de 60, catégorie hors `CATEGORIES`, clé en double) va au
    bilan avec sa raison, le reste passe. Un libellé absent, `null` ou vide ne
    change RIEN ; une catégorie absente non plus, une catégorie `null` remet
    l'automatique. Rien n'est jamais supprimé. Un type que la table n'a pas
    encore vu est inséré avec le `display_name`, la `category` et le
    `resolved_from` de `categorize` -- s'il y a quelque chose à poser : une
    entrée qui ne changerait rien n'écrit pas de ligne."""
    if not isinstance(contenu, dict):
        raise ValueError("le fichier n'est pas un objet JSON")
    if contenu.get("contrat") != _REF_CONTRAT:
        raise ValueError(f"le contrat doit être « {_REF_CONTRAT} »")
    version = contenu.get("version")
    if type(version) is not int or version != 1:
        raise ValueError("la version du contrat doit être 1")
    for nom in ("types", "armes"):
        if not isinstance(contenu.get(nom), list):
            raise ValueError(f"« {nom} » est absent ou n'est pas une liste")

    refuses: list[dict] = []
    ecr_types: list[dict] = []
    ecr_armes: list[dict] = []
    t_poses = t_inchanges = t_forcees = 0
    a_poses = a_inchanges = 0

    vues: set = set()
    for entree in contenu["types"]:
        cle, libelle, categorie, raison = _lire_entree_import(entree, vues, "types", True)
        if raison is not None:
            refuses.append({"cle": cle, "raison": raison})
            continue
        ex = types_existants.get(cle)
        ex_libelle = ex.get("libelle") if ex else None
        ex_forcee = ex.get("categorie_forcee") if ex else None
        libelle_change = libelle is not None and libelle != ex_libelle
        if categorie == "absente":
            categorie_change = False
        elif categorie is None:
            categorie_change = ex_forcee is not None
        else:
            categorie_change = categorie != ex_forcee
        if libelle_change:
            t_poses += 1
        else:
            t_inchanges += 1
        if categorie_change:
            t_forcees += 1
        if not (libelle_change or categorie_change):
            continue
        ecriture: dict = {"cle": cle, "nouveau": ex is None}
        if libelle_change:
            ecriture["libelle"] = libelle
        if categorie_change:
            ecriture["categorie_forcee"] = categorie
        if ex is None:
            display_name, category, resolved_from = categorize.categorize(cle)
            ecriture.update(
                display_name=display_name, category=category, resolved_from=resolved_from
            )
        ecr_types.append(ecriture)

    vues = set()
    for entree in contenu["armes"]:
        cle, libelle, _, raison = _lire_entree_import(entree, vues, "armes", False)
        if raison is not None:
            refuses.append({"cle": cle, "raison": raison})
            continue
        if libelle is not None and libelle != armes_existantes.get(cle):
            a_poses += 1
            ecr_armes.append({"cle": cle, "libelle": libelle})
        else:
            a_inchanges += 1

    return {
        "bilan": {
            "contrat": contenu["contrat"],
            "version": version,
            "types": {"poses": t_poses, "inchanges": t_inchanges, "forcees": t_forcees},
            "armes": {"poses": a_poses, "inchanges": a_inchanges},
            "refuses": refuses,
        },
        "ecritures": {"types": ecr_types, "armes": ecr_armes},
    }


def _types_affiches(lignes, cles_vues: set) -> list:
    """Lot « Les référentiels n'affichent que les types vus » : filtre les
    lignes de `debrief_unit_category` pour l'écran Référentiels. Fonction
    PURE : n'écrit rien, ne lit pas la base.

    Garde une ligne si sa clé est vue par les écrans (`cles_vues`), ou si elle
    porte un libellé ou une catégorie forcée -- rien de ce qu'un
    administrateur a posé ne disparaît. Écarte le reste (les missiles, bombes,
    obus et leurres que le moteur recense aussi, et que les écrans n'affichent
    jamais). La table n'est pas touchée."""
    return [
        r for r in lignes
        if r.unit_type in cles_vues or r.libelle or r.categorie_forcee
    ]


@router.get("/referentiels")
async def get_referentiels(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Le référentiel entier, pour l'écran : les types vus (les lignes de
    `debrief_unit_category` que les écrans affichent -- évènements, cimetière,
    vols -- ou qui portent un libellé ou une catégorie forcée), les armes (les clés de `referentiel_arme` UNION
    les armes distinctes des évènements), les catégories admises et
    `you: {is_admin}`. Tri sans casse sur la clé. Garde : celle du module."""
    lignes = (await db.execute(select(DebriefUnitCategory))).scalars().all()
    # Lot « Les référentiels n'affichent que les types vus » : les clés que les
    # écrans affichent.
    cles_vues: set = set()
    for colonne in (
        DebriefEvent.initiator_unit_type,
        DebriefEvent.target_unit_type,
        DebriefGraveyard.unit_type,
        DebriefFlight.aircraft_type,
    ):
        cles_vues.update(
            (await db.execute(select(colonne).where(colonne.is_not(None)).distinct()))
            .scalars().all()
        )
    types = [_type_ref_to_dict(r.unit_type, r) for r in _types_affiches(lignes, cles_vues)]
    types.sort(key=lambda t: _cle_tri(t["cle"]))

    libelles = {
        cle: libelle
        for cle, libelle in (
            await db.execute(select(ReferentielArme.cle, ReferentielArme.libelle))
        ).all()
    }
    vues = (
        await db.execute(
            select(DebriefEvent.weapon).where(DebriefEvent.weapon.is_not(None)).distinct()
        )
    ).scalars().all()
    cles_armes = set(libelles) | set(vues)
    armes = [{"cle": cle, "libelle": libelles.get(cle)} for cle in cles_armes]
    armes.sort(key=lambda a: _cle_tri(a["cle"]))

    return {
        "types": types,
        "armes": armes,
        "categories": list(referentiel.CATEGORIES),
        "you": {"is_admin": is_admin(user)},
    }


@router.patch("/referentiels/types")
async def patch_referentiel_type(
    payload: ReferentielTypePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Écrire le libellé et/ou la catégorie d'un type -- administrateur seul
    (403 sinon, rien d'écrit). Champs présents seulement : `libelle` vide ->
    `NULL` ; `categorie` `null` -> automatique, sinon dans `CATEGORIES` (422).
    404 pour une clé absente de la table. Le dictionnaire des catégories
    forcées est relu après l'écriture : les bilans la suivent sans
    redémarrage."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    ligne = await db.get(DebriefUnitCategory, payload.cle)
    if ligne is None:
        raise HTTPException(status_code=404, detail="Type introuvable.")

    champs = payload.model_fields_set
    avant_journal = {"libelle": ligne.libelle, "categorie": ligne.categorie_forcee}   # lot « Polish du Centre »
    if "libelle" in champs:
        try:
            ligne.libelle = _ref_libelle(payload.libelle)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if "categorie" in champs:
        if payload.categorie is not None and payload.categorie not in referentiel.CATEGORIES:
            raise HTTPException(status_code=422, detail="Catégorie inconnue.")
        ligne.categorie_forcee = payload.categorie

    journal.consigner(
        db, user, "ref.type", objet=ligne.unit_type,
        lignes=journal.ecarts(
            avant_journal, {"libelle": ligne.libelle, "categorie": ligne.categorie_forcee}
        ),
    )
    await db.commit()
    await referentiel.charger(db)
    return _type_ref_to_dict(ligne.unit_type, ligne)


@router.patch("/referentiels/armes")
async def patch_referentiel_arme(
    payload: ReferentielArmePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Écrire le libellé d'une arme -- administrateur seul. Upsert dans
    `referentiel_arme` ; libellé vide -> `NULL`."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    cle = payload.cle
    if not cle.strip() or len(cle) > _REF_CLE_MAX:
        raise HTTPException(status_code=422, detail="Clé d'arme invalide.")
    try:
        libelle = _ref_libelle(payload.libelle)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    ligne = await db.get(ReferentielArme, cle)
    ancien_libelle = ligne.libelle if ligne is not None else None   # lot « Polish du Centre »
    if ligne is None:
        ligne = ReferentielArme(cle=cle, libelle=libelle)
        db.add(ligne)
    else:
        ligne.libelle = libelle
    journal.consigner(
        db, user, "ref.arme", objet=cle,
        lignes=journal.ecarts({"libelle": ancien_libelle}, {"libelle": libelle}),
    )
    await db.commit()
    return {"cle": ligne.cle, "libelle": ligne.libelle}


def _insertion_type(w: dict):
    """Lot « Le Centre côté serveur » : l'instruction qui insère un type
    NEUF du référentiel importé. Fonction PURE : construit l'instruction, ne
    l'exécute pas. Les six colonnes sont celles qu'écrivait `db.add`. Si un
    dépôt a créé la même clé au même instant, l'instruction ne tombe plus
    (`ON CONFLICT`) : elle ne pose que `libelle` et `categorie_forcee`, et
    seulement celles que l'écriture `w` porte ; `display_name`, `category` et
    `resolved_from` d'une ligne que le dépôt vient de créer ne sont jamais
    écrasés. Sans `libelle` ni `categorie_forcee`, `DO NOTHING`."""
    stmt = pg_insert(DebriefUnitCategory).values(
        unit_type=w["cle"],
        display_name=w["display_name"],
        category=w["category"],
        resolved_from=w["resolved_from"],
        libelle=w.get("libelle"),
        categorie_forcee=w.get("categorie_forcee"),
    )
    cles = [c for c in ("libelle", "categorie_forcee") if c in w]
    if cles:
        return stmt.on_conflict_do_update(
            index_elements=["unit_type"],
            set_={c: getattr(stmt.excluded, c) for c in cles},
        )
    return stmt.on_conflict_do_nothing(index_elements=["unit_type"])


def _insertion_arme(w: dict):
    """Lot « Le Centre côté serveur » : l'instruction qui insère une arme
    NEUVE du référentiel importé -- même patron que `_insertion_type`. Un
    conflit sur `cle` pose le libellé importé. Fonction PURE."""
    stmt = pg_insert(ReferentielArme).values(cle=w["cle"], libelle=w["libelle"])
    return stmt.on_conflict_do_update(
        index_elements=["cle"], set_={"libelle": stmt.excluded.libelle}
    )


@router.post("/referentiels/import")
async def post_referentiels_import(
    contenu: dict = Body(...),
    appliquer: int = Query(0, ge=0, le=1),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Importer un fichier de référentiel -- administrateur seul. `appliquer=0` :
    RIEN n'est écrit, la route rend le bilan ; `appliquer=1` : écrit, relit les
    catégories forcées, rend le même bilan. Fichier illisible -> 422
    (`_analyser_import`)."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    lignes = (await db.execute(select(DebriefUnitCategory))).scalars().all()
    par_cle = {r.unit_type: r for r in lignes}
    types_existants = {
        cle: {"libelle": r.libelle, "categorie_forcee": r.categorie_forcee}
        for cle, r in par_cle.items()
    }
    armes_lignes = (await db.execute(select(ReferentielArme))).scalars().all()
    armes_par_cle = {r.cle: r for r in armes_lignes}
    armes_existantes = {cle: r.libelle for cle, r in armes_par_cle.items()}

    try:
        analyse = _analyser_import(contenu, types_existants, armes_existantes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if appliquer == 1:
        for w in analyse["ecritures"]["types"]:
            if w["nouveau"]:
                # Lot « Le Centre côté serveur » : sans heurt si un dépôt a
                # créé le même type entre la lecture et l'écriture.
                await db.execute(_insertion_type(w))
                continue
            ligne = par_cle[w["cle"]]
            if "libelle" in w:
                ligne.libelle = w["libelle"]
            if "categorie_forcee" in w:
                ligne.categorie_forcee = w["categorie_forcee"]
        for w in analyse["ecritures"]["armes"]:
            ligne = armes_par_cle.get(w["cle"])
            if ligne is None:
                await db.execute(_insertion_arme(w))   # lot « Le Centre côté serveur »
            else:
                ligne.libelle = w["libelle"]
        bilan = analyse["bilan"]   # lot « Polish du Centre »
        journal.consigner(
            db, user, "ref.import", toujours=True,
            lignes=journal.ecarts({}, {
                "poses": bilan["types"]["poses"] + bilan["armes"]["poses"],
                "refuses": len(bilan["refuses"]),
            }),
        )
        await db.commit()
        await referentiel.charger(db)

    return analyse["bilan"]


# ---------------------------------------------------------------------------
# Lot « L'écran Archives du Centre » -- les membres archivés et les
# sauvegardes. Le verrou d'accès au Centre est posé au point de montage ;
# les sauvegardes sont réservées à l'administrateur (403 sinon, comme
# `PATCH /command/wing`) et la liste n'est même pas rendue aux autres.
# ---------------------------------------------------------------------------


def _derniere_escadrille(appartenances) -> Optional[str]:
    """La désignation de l'escadrille de l'appartenance close la plus récente
    (`ended_at` le plus grand), quel que soit le statut de l'escadrille.
    `appartenances` : des couples `(ended_at, désignation)` ; une appartenance
    sans `ended_at` (ouverte) n'est pas une sortie et ne compte pas. `None`
    sans appartenance. Pure : testée hors ligne (tests/test_archives.py)."""
    closes = [(fin, nom) for fin, nom in appartenances if fin is not None]
    if not closes:
        return None
    return max(closes, key=lambda c: c[0])[1]


@router.get("/archives")
async def get_archives(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """L'écran Archives : les membres archivés (`archived_at` posé), du plus
    récent au plus ancien puis par nom, et -- pour un administrateur seul --
    les sauvegardes. Les missions et les heures sont la `participation` de
    `_fiche_publique`, la source de F et de A : l'écran dit le même chiffre
    que F, rien n'est recompté ici."""
    profils = (
        await db.execute(
            select(Profile)
            .where(Profile.archived_at.is_not(None))
            .order_by(Profile.archived_at.desc(), func.coalesce(Profile.global_name, Profile.username))
        )
    ).scalars().all()
    appartenances: dict = {p.id: [] for p in profils}
    if profils:
        lignes = (
            await db.execute(
                select(SquadronMembership.profile_id, SquadronMembership.ended_at, Squadron.designation)
                .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
                .where(
                    SquadronMembership.profile_id.in_(list(appartenances)),
                    SquadronMembership.ended_at.is_not(None),
                )
            )
        ).all()
        for profile_id, fin, designation in lignes:
            appartenances[profile_id].append((fin, designation))
    membres = []
    for p in profils:
        publique = await _fiche_publique(db, p.id)
        participation = publique[0]["participation"] if publique is not None else {}
        membres.append(
            {
                # str() impératif : snowflake Discord au-delà de Number.MAX_SAFE_INTEGER.
                "id": str(p.id),
                "name": p.global_name or p.username,
                "avatar_hash": p.avatar_hash,
                "archived_at": p.archived_at.isoformat(),
                "escadrille": _derniere_escadrille(appartenances[p.id]),
                "missions": participation.get("missions", 0),
                "heures": participation.get("heures", 0.0),
            }
        )
    admin = is_admin(user)
    return {
        "you": {"is_admin": admin},
        "membres": membres,
        "sauvegardes": sauvegardes.lister(settings.BACKUP_DIR) if admin else None,
        # Lot « Les sauvegardes automatiques » : le réglage, pour l'administrateur seul.
        "automatique": await _archives_automatique(db) if admin else None,
    }


async def _archives_automatique(db: AsyncSession) -> dict:
    """Lot « Les sauvegardes automatiques » : l'objet `automatique` de l'écran
    Archives -- le réglage effectif et l'échec de la dernière tentative
    (`{"date", "raison"}`, ou `null`)."""
    reglage = await sauvegardes_auto.lire_reglage(db)
    return {**reglage, "echec": sauvegardes_auto.dernier_echec()}


@router.put("/archives/automatique")
async def put_archives_automatique(
    payload: SauvegardeAutoPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les sauvegardes automatiques » : régler la sauvegarde automatique
    -- administrateur seul (403 sinon, avant toute lecture). La fréquence et la
    rétention sont validées par `sauvegardes_auto.valider_reglage` (422 avec son
    message). Écrit la ligne `id = 1`, créée si elle manque, et consigne le
    changement au journal. Aucune purge ici : une rétention réduite ne purge
    qu'à la sauvegarde automatique réussie suivante. Rend le même objet que
    `GET /command/archives`."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")
    try:
        apres = sauvegardes_auto.valider_reglage(payload.intervalle_h, payload.garder)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    avant = await sauvegardes_auto.lire_reglage(db)
    ligne = (
        await db.execute(select(SauvegardeAutoReglage).where(SauvegardeAutoReglage.id == 1))
    ).scalars().first()
    if ligne is None:
        db.add(SauvegardeAutoReglage(id=1, **apres))
    else:
        ligne.intervalle_h = apres["intervalle_h"]
        ligne.garder = apres["garder"]
        ligne.modifie_le = func.now()
    journal.consigner(
        db, user, "archives.automatique", lignes=journal.ecarts(avant, apres)
    )
    await db.commit()
    return await _archives_automatique(db)


@router.post("/archives/sauvegarde")
async def post_archives_sauvegarde(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """La sauvegarde manuelle -- administrateur seul (403 sinon). La base
    (`pg_dump`) et les écussons (une archive du volume `crests`) s'écrivent
    dans `BACKUP_DIR`, sous la révision Alembic en cours. Rend l'entrée neuve.
    409 si une sauvegarde est déjà en cours ; 500 si elle échoue -- rien n'est
    alors gardé. La restauration ne se fait jamais d'ici."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")
    version = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalars().first()
    revision = sauvegardes.etiquette_revision(version)
    try:
        entree = await sauvegardes.sauvegarder(
            settings.BACKUP_DIR, settings.DATABASE_URL, settings.CREST_STORAGE_DIR, revision
        )
        # Lot « Polish du Centre » : la sauvegarde réussie se consigne.
        journal.consigner(
            db, user, "archives.sauvegarde", toujours=True,
            lignes=journal.ecarts({}, {"fichier": entree["fichier_base"]}),
        )
        await db.commit()
        return entree
    except sauvegardes.SauvegardeEnCours as exc:
        raise HTTPException(status_code=409, detail="Une sauvegarde est déjà en cours.") from exc
    except sauvegardes.SauvegardeEchec as exc:
        raise HTTPException(
            status_code=500,
            detail=f"La sauvegarde a échoué : {exc}. Rien n'a été gardé.",
        ) from exc


@router.get("/archives/sauvegardes/{fichier}")
async def get_archives_sauvegarde(
    fichier: str,
    user: dict = Depends(get_current_user),
):
    """Le téléchargement d'une sauvegarde -- administrateur seul (403 sinon).
    404 si le nom n'est pas l'une des sept formes reconnues
    (`sauvegardes.nom_valide`) ou si le fichier manque dans `BACKUP_DIR`."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")
    if not sauvegardes.nom_valide(fichier):
        raise HTTPException(status_code=404, detail="Sauvegarde introuvable.")
    dossier = Path(settings.BACKUP_DIR).resolve()
    chemin = (dossier / fichier).resolve()
    if chemin.parent != dossier or not chemin.is_file():
        raise HTTPException(status_code=404, detail="Sauvegarde introuvable.")
    media = "application/gzip" if fichier.endswith(".tar.gz") else "application/octet-stream"
    return FileResponse(chemin, media_type=media, filename=fichier)


# ---------------------------------------------------------------------------
# Lot « La réception du .rrlog de l'agent » (v1.0089) -- le bloc « Serveur DCS »
# de l'écran Archives : le jeton de l'agent et les derniers fichiers reçus.
# Trois routes, administrateur seul (403 avant toute lecture en base). Le jeton
# en clair n'est rendu qu'à la réponse de l'émission ; le journal ne le porte
# jamais, ni son empreinte.
# ---------------------------------------------------------------------------

AGENT_RECUS_PAGE = 20


@router.get("/agent")
async def get_agent(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """L'état du jeton de l'agent et les 20 derniers fichiers reçus (le plus récent
    d'abord). Administrateur seul."""
    _admin_seul(user)
    actifs = await agent_mod._jetons_actifs(db)
    jeton = None
    if actifs:
        actif = actifs[0]
        nom = actif.emis_par
        try:
            profil = await db.get(Profile, int(actif.emis_par))
        except ValueError:
            profil = None
        if profil is not None:
            nom = profil.global_name or profil.username
        jeton = {
            "emis_le": actif.emis_le.astimezone(timezone.utc).isoformat(),
            "emis_par": {"id": actif.emis_par, "nom": nom},
            "dernier_envoi_le": (
                actif.dernier_envoi_le.astimezone(timezone.utc).isoformat()
                if actif.dernier_envoi_le is not None
                else None
            ),
        }
    recus = (
        await db.execute(
            select(AgentRrlog).order_by(AgentRrlog.recu_le.desc(), AgentRrlog.id.desc()).limit(AGENT_RECUS_PAGE)
        )
    ).scalars().all()
    return {
        "jeton": jeton,
        "recus": [
            {
                "recu_le": r.recu_le.astimezone(timezone.utc).isoformat(),
                "fichier": r.fichier,
                "mission": r.mission,
                "theatre": r.theatre,
                "date_mission": r.date_mission,
                "taille": r.taille,
                "etat": r.etat,
            }
            for r in recus
        ],
    }


@router.post("/agent/jeton", status_code=201)
async def post_agent_jeton(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Émet le jeton de l'agent et révoque l'actif, dans la même transaction. La seule
    réponse qui porte le jeton en clair. Administrateur seul."""
    _admin_seul(user)
    maintenant = datetime.now(timezone.utc)
    clair, empreinte = agent_mod.nouveau_jeton()
    # Addendum 2 (A5) : un seul jeton actif, même en concurrence -- le verrou de transaction se prend avant
    # de révoquer l'actif et d'insérer le neuf.
    await agent_mod.verrouiller_emission(db)
    await db.execute(
        update(AgentJeton).where(AgentJeton.revoque_le.is_(None)).values(revoque_le=maintenant)
    )
    db.add(AgentJeton(empreinte=empreinte, emis_le=maintenant, emis_par=str(user["id"])))
    journal.consigner(db, user, "agent.jeton.emis", toujours=True)
    await db.commit()
    return {"jeton": clair, "emis_le": maintenant.isoformat()}


@router.delete("/agent/jeton", status_code=204)
async def delete_agent_jeton(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Révoque le jeton actif de l'agent ; 409 s'il n'y en a pas. Administrateur seul."""
    _admin_seul(user)
    if not await agent_mod._jetons_actifs(db):
        raise HTTPException(status_code=409, detail="Aucun jeton actif.")
    await db.execute(
        update(AgentJeton)
        .where(AgentJeton.revoque_le.is_(None))
        .values(revoque_le=datetime.now(timezone.utc))
    )
    journal.consigner(db, user, "agent.jeton.revoque", toujours=True)
    await db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Lot « Polish du Centre » -- le journal des modifications et le diagnostic
# d'accès. Deux routes de lecture, réservées à l'administrateur (403 sinon).
# ---------------------------------------------------------------------------

JOURNAL_PAGE = 50


@router.get("/journal")
async def get_journal(
    avant: Optional[int] = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Le journal des modifications -- administrateur seul. Les 50 entrées
    d'identifiant inférieur à `avant` (toutes sans `avant`), de la plus récente à
    la plus ancienne ; `suite` est vrai s'il en reste d'autres. `par.nom` est le
    nom brut du profil (l'écran applique `callsign()`) ; les comptes des lignes
    passent par `_callsign`, comme les destinataires des relances."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")

    stmt = select(CommandJournal).order_by(CommandJournal.id.desc()).limit(JOURNAL_PAGE + 1)
    if avant is not None:
        stmt = stmt.where(CommandJournal.id < avant)
    rows = list((await db.execute(stmt)).scalars().all())
    suite = len(rows) > JOURNAL_PAGE
    rows = rows[:JOURNAL_PAGE]

    ids: set[int] = {r.par_id for r in rows}
    for r in rows:
        for ligne in r.lignes:
            if ligne.get("champ") in ("profile_id", "profile_ids"):
                for cle in ("avant", "apres", "ajoutes", "retires"):
                    v = ligne.get(cle)
                    for x in v if isinstance(v, list) else [v]:
                        try:
                            if x is not None:
                                ids.add(int(x))
                        except (TypeError, ValueError):
                            pass
    profils = {}
    if ids:
        profils = {
            p.id: p
            for p in (
                await db.execute(select(Profile).where(Profile.id.in_(ids)))
            ).scalars().all()
        }
    rx = await _build_name_strip_regex(db)
    noms = {str(i): _callsign(p.global_name or p.username, rx) for i, p in profils.items()}

    return {
        "entrees": [
            {
                "id": r.id,
                "fait_le": r.fait_le.isoformat(),
                "par": {
                    "id": str(r.par_id),
                    "nom": (
                        (profils[r.par_id].global_name or profils[r.par_id].username)
                        if r.par_id in profils else str(r.par_id)
                    ),
                },
                "action": r.action,
                "objet": r.objet,
                "lignes": journal.lisibles(r.lignes, noms),
            }
            for r in rows
        ],
        "suite": suite,
    }


@router.get("/members/{profile_id}/acces")
async def get_member_acces(
    profile_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Le diagnostic d'accès d'un membre -- administrateur seul (403 sinon) ; 404
    si le profil n'existe pas. Ses rôles relevés (`roles_snapshot`) et, pour chacun
    des neuf droits de l'écran Droits, s'il l'a et ce qui le lui ouvre : le
    verdict des vrais résolveurs, rejoué par `app.command.acces.diagnostic` sur un
    état lu en base une fois par appel."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")
    profil = await db.get(Profile, profile_id)
    if profil is None:
        raise HTTPException(status_code=404, detail="Profil introuvable.")
    roles = sorted(str(r) for r in (profil.roles_snapshot or []))
    etat = await acces.lire_etat(db, profil.id)
    return {
        "profil": {"id": str(profil.id), "nom": profil.global_name or profil.username},
        "roles": roles,
        "droits": acces.diagnostic(profil.id, roles, profil.archived_at is not None, etat),
    }


@router.post("/members/{profile_id}/lien-secours")
async def post_member_lien_secours(
    profile_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « La connexion de secours » (R325) -- émet un lien de connexion de
    secours pour un membre : administrateur seul (403 avant toute lecture en
    base), 404 si le profil n'existe pas, 409 si le membre n'a pas le droit de
    connexion (archivé, ou ni administrateur ni porteur d'un rôle d'accès sur
    `roles_snapshot` -- un lien ne lui ouvrirait rien). Valable 24 heures, une
    seule fois ; en émettre un nouveau annule le précédent. Une ligne au
    journal du Centre ; le lien n'est rendu qu'ici, jamais conservé."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")
    profil = await db.get(Profile, profile_id)
    if profil is None:
        raise HTTPException(status_code=404, detail="Profil introuvable.")
    droit = profil.archived_at is None and (
        str(profil.id) in settings.admin_ids_set
        or await has_app_access(db, {"id": profil.id, "roles": profil.roles_snapshot})
    )
    if not droit:
        raise HTTPException(
            status_code=409,
            detail="Ce membre n'a pas le droit de connexion : un lien ne lui ouvrirait rien.",
        )
    url, expire = await connexion_secours.emettre_lien(
        db, profil.id, "admin", int(user["id"])
    )
    journal.consigner(
        db, user, "members.lien_secours",
        objet=profil.global_name or profil.username, toujours=True,
    )
    await db.commit()
    return {"url": url, "expires_at": expire.isoformat()}


# --- Lot « L'accès invité » (v1.0070) : les invités de la démonstration ------
#
# Une personne hors du serveur Discord de l'escadre, autorisée par son
# identifiant Discord, voit la Ready Room en lecture seule (R1 à R9). Cinq
# routes, administrateur seul : 403 avant toute lecture en base, comme
# `put_app_access`. L'invité n'a pas de profil : la table `invitations` est
# sa seule trace, et le journal se signe de l'administrateur (`par_id` est
# une clé étrangère vers `profiles`).

_BIGINT_MAX = 2**63 - 1


class InvitationPayload(BaseModel):
    """Corps de `POST /command/invites`."""

    discord_id: str


def _admin_seul(user: dict) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé à l'administrateur.")


def _jour_utc(dt: datetime) -> str:
    """La date (AAAA-MM-JJ) d'un horodatage, en UTC -- pour le journal."""
    return dt.astimezone(timezone.utc).date().isoformat()


async def _entree_invite(db: AsyncSession, inv: Invitation) -> dict:
    """L'invitation telle que la lit l'écran Droits (`GET /invites`)."""
    par = await db.get(Profile, inv.invite_par)
    return {
        "discord_id": str(inv.discord_id),
        "nom": inv.nom,
        "username": inv.username,
        "invite_par": (par.global_name or par.username) if par is not None else "",
        "jusqua": inv.jusqua.astimezone(timezone.utc).isoformat(),
        "derniere_entree": (
            inv.derniere_entree.astimezone(timezone.utc).isoformat()
            if inv.derniere_entree is not None
            else None
        ),
    }


async def _verifier_compte_discord(db: AsyncSession, brut: str) -> tuple[int, str, str]:
    """Les contrôles communs à `GET /invites/verifier` et à `POST /invites`,
    dans l'ordre : forme de l'identifiant (422), compte déjà connu de la Ready
    Room (409), lecture du compte par le bot (503 / 404). Rend
    `(identifiant, nom, username)`."""
    if not identifiant_discord_valide(brut):
        raise HTTPException(
            status_code=422, detail="Identifiant Discord invalide : 17 à 20 chiffres."
        )
    discord_id = int(brut.strip())
    # Au-delà de 2^63 - 1 (hors d'un BigInteger) aucun profil ne peut le porter.
    if discord_id <= _BIGINT_MAX and await db.get(Profile, discord_id) is not None:
        raise HTTPException(
            status_code=409,
            detail="Ce compte est déjà connu de la Ready Room : c'est un membre, pas un invité.",
        )
    reponse = (
        await _bot_request("GET", f"/users/{discord_id}")
        if settings.bot_token_present
        else None
    )
    if reponse is None or reponse.status_code not in (200, 404):
        raise HTTPException(
            status_code=503, detail="Discord ne répond pas : réessaie dans un instant."
        )
    if reponse.status_code == 404 or discord_id > _BIGINT_MAX:
        raise HTTPException(
            status_code=404, detail="Aucun compte Discord ne porte cet identifiant."
        )
    try:
        compte = reponse.json()
        username = str(compte["username"])
    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=503, detail="Discord ne répond pas : réessaie dans un instant."
        )
    nom = compte.get("global_name") or username
    return discord_id, nom, username


@router.get("/invites")
async def get_invites(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Les invitations ACTIVES, triées par échéance croissante. Administrateur
    seul."""
    _admin_seul(user)
    maintenant = datetime.now(timezone.utc)
    lignes = (
        await db.execute(
            select(Invitation)
            .where(Invitation.revoque_le.is_(None), Invitation.jusqua > maintenant)
            .order_by(Invitation.jusqua.asc())
        )
    ).scalars().all()
    return {"invites": [await _entree_invite(db, inv) for inv in lignes]}


@router.get("/invites/verifier")
async def verifier_invite(
    discord_id: str = Query(""),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lit le compte Discord avant d'inviter : `{discord_id, nom, username}`.
    Administrateur seul."""
    _admin_seul(user)
    identifiant, nom, username = await _verifier_compte_discord(db, discord_id)
    return {"discord_id": str(identifiant), "nom": nom, "username": username}


@router.post("/invites", status_code=201)
async def post_invite(
    payload: InvitationPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite pour 30 jours. Mêmes contrôles que `verifier`, puis : une
    invitation active existe -> 409 ; une ligne échue ou révoquée se réécrit.
    Administrateur seul."""
    _admin_seul(user)
    identifiant, nom, username = await _verifier_compte_discord(db, payload.discord_id)
    maintenant = datetime.now(timezone.utc)
    inv = await db.get(Invitation, identifiant)
    if invitation_active(inv, maintenant):
        raise HTTPException(
            status_code=409,
            detail="Cette personne est déjà invitée : prolonge son invitation.",
        )
    jusqua = echeance_initiale(maintenant)
    if inv is None:
        inv = Invitation(
            discord_id=identifiant, nom=nom, username=username,
            invite_par=int(user["id"]), cree_le=maintenant, jusqua=jusqua,
        )
        db.add(inv)
    else:
        inv.nom = nom
        inv.username = username
        inv.invite_par = int(user["id"])
        inv.cree_le = maintenant
        inv.jusqua = jusqua
        inv.revoque_le = None
        inv.derniere_entree = None
    journal.consigner(
        db, user, "invites.ajout", objet=nom,
        lignes=[{"champ": "jusqua", "avant": None, "apres": _jour_utc(jusqua)}],
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Cette personne est déjà invitée : prolonge son invitation.",
        )
    return await _entree_invite(db, inv)


async def _invitation_active_ou_404(db: AsyncSession, brut: str) -> Invitation:
    """L'invitation active de ce compte, sinon 404 « introuvable ou échue »."""
    inv = None
    if identifiant_discord_valide(brut) and int(brut.strip()) <= _BIGINT_MAX:
        inv = await db.get(Invitation, int(brut.strip()))
    if not invitation_active(inv, datetime.now(timezone.utc)):
        raise HTTPException(status_code=404, detail="Invitation introuvable ou échue.")
    return inv


@router.post("/invites/{discord_id}/prolonger")
async def prolonger_invite(
    discord_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Prolonge l'invitation de 30 jours (`jusqua` + 30 jours). Administrateur
    seul."""
    _admin_seul(user)
    inv = await _invitation_active_ou_404(db, discord_id)
    avant = inv.jusqua
    inv.jusqua = echeance_prolongee(avant)
    journal.consigner(
        db, user, "invites.prolongation", objet=inv.nom,
        lignes=[{"champ": "jusqua", "avant": _jour_utc(avant), "apres": _jour_utc(inv.jusqua)}],
    )
    await db.commit()
    return await _entree_invite(db, inv)


@router.delete("/invites/{discord_id}", status_code=204)
async def revoquer_invite(
    discord_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Révoque l'invitation : `revoque_le` = maintenant. Administrateur seul."""
    _admin_seul(user)
    inv = await _invitation_active_ou_404(db, discord_id)
    inv.revoque_le = datetime.now(timezone.utc)
    journal.consigner(
        db, user, "invites.revocation", objet=inv.nom, lignes=[], toujours=True
    )
    await db.commit()
    return Response(status_code=204)


# --- Lot « rr-env-epure » (v1.0105) : les réglages en base et les administrateurs nommés ---
# Les routes de la future page « Configuration » du Centre (chantier `rr-centre-reglages`).
# Chacune est réservée à l'administrateur (`_admin_seul`), comme `POST /squadrons`.


class ReglagePayload(BaseModel):
    """Corps de `PUT /command/reglages/{cle}` : toute valeur JSON ; vide ou `null`, le
    réglage reprend son défaut."""

    valeur: Any


async def _element_reglage(db: AsyncSession, definition: reglages.Definition) -> dict:
    """L'élément servi pour un réglage : `rempli` = la ligne existe ; `lisible` d'un
    secret = la clé est valide et le jeton se déchiffre ; la valeur d'un réglage en clair
    est celle en vigueur sur `settings`."""
    ligne = await db.get(Reglage, definition.cle, populate_existing=True)
    cle_ok = reglages.cle_valide(settings.CONFIG_KEY)
    lisible = cle_ok and (
        ligne is None or reglages.dechiffrer(settings.CONFIG_KEY, ligne.valeur) is not None
    )
    return reglages.element(
        definition,
        None if definition.secret else getattr(settings, definition.cle),
        ligne is not None,
        lisible,
        ligne.maj_le if ligne is not None else None,
        ligne.maj_par if ligne is not None else None,
    )


@router.get("/reglages")
async def lire_reglages(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Les quatorze réglages en base, dans l'ordre des définitions ; jamais un secret en
    clair. Administrateur seul."""
    _admin_seul(user)
    return {
        "cle_presente": reglages.cle_valide(settings.CONFIG_KEY),
        "reglages": [await _element_reglage(db, d) for d in reglages.DEFINITIONS],
    }


@router.get("/reglages/modeles")
async def lister_modeles_recit(user: dict = Depends(get_current_user)):
    """Les modèles actifs d'Anthropic qui conviennent au Récit (`reglages.lister_modeles`) ;
    toujours 200 pour un administrateur, `disponible` dit si la liste est là. Administrateur seul."""
    _admin_seul(user)
    return await reglages.lister_modeles()


@router.get("/reglages/dossiers")
async def lister_dossiers_montes(user: dict = Depends(get_current_user)):
    """Les trois dossiers branchés par Docker (suites, tuiles, tuiles gardées) : présent ou non, nombre de fichiers
    (`reglages.etat_dossiers`). Lecture seule, en tâche de fond : le compte touche au disque. Administrateur seul."""
    _admin_seul(user)
    return {"dossiers": await asyncio.to_thread(reglages.etat_dossiers, settings)}


@router.put("/reglages/{cle}")
async def ecrire_reglage(
    cle: str,
    payload: ReglagePayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Écrit un réglage (`reglages.ecrire`) et rend son élément. 404 réglage inconnu ;
    422 `valeur_invalide` ; 409 `cle_absente` (un secret sans `CONFIG_KEY` valide).
    Administrateur seul."""
    _admin_seul(user)
    definition = reglages.PAR_CLE.get(cle)
    if definition is None:
        raise HTTPException(status_code=404, detail="Réglage inconnu.")
    try:
        await reglages.ecrire(db, definition, payload.valeur, user)
    except ValueError:
        raise HTTPException(
            status_code=422, detail={"code": "valeur_invalide", "cle": definition.cle}
        )
    except reglages.CleAbsente:
        raise HTTPException(status_code=409, detail={"code": "cle_absente"})
    return await _element_reglage(db, definition)


def _fondateurs() -> list[str]:
    """Les administrateurs fondateurs (`ADMIN_IDS`), identifiants faits de chiffres,
    triés par identifiant."""
    ids = {i.strip() for i in settings.ADMIN_IDS.split(",") if re.fullmatch(r"[0-9]+", i.strip())}
    return sorted(ids, key=int)


def _nom_profil(profil: Profile | None) -> str | None:
    """`global_name`, sinon `username`, sinon `None` (un fondateur peut n'avoir jamais
    ouvert de session)."""
    if profil is None:
        return None
    return profil.global_name or profil.username or None


async def _administrateurs(db: AsyncSession) -> dict:
    """La forme commune du `GET`, du `PUT` et du `DELETE` de `/administrateurs`."""
    nommes = (
        await db.execute(
            select(AccountCapability)
            .where(AccountCapability.capability == "admin")
            .order_by(AccountCapability.profile_id.asc())
        )
    ).scalars().all()
    fondateurs = _fondateurs()
    ids = {int(i) for i in fondateurs if int(i) <= _BIGINT_MAX} | {n.profile_id for n in nommes}
    profils = {
        p.id: p
        for p in (await db.execute(select(Profile).where(Profile.id.in_(ids)))).scalars().all()
    } if ids else {}
    return {
        "fondateurs": [
            {"id": i, "nom": _nom_profil(profils.get(int(i)))} for i in fondateurs
        ],
        "nommes": [
            {
                "id": str(n.profile_id),
                "nom": _nom_profil(profils.get(n.profile_id)),
                "nomme_le": n.granted_at.isoformat() if n.granted_at else None,
                "nomme_par": str(n.granted_by) if n.granted_by is not None else None,
            }
            for n in nommes
        ],
    }


def _refuser_fondateur(profile_id: str) -> None:
    """Un fondateur ne se nomme ni ne se retire : 409 `fondateur`. Il se reconnaît en entier
    (`0123` est le fondateur `123`)."""
    brut = profile_id.strip()
    if re.fullmatch(r"[0-9]+", brut) and int(brut) in {int(f) for f in _fondateurs()}:
        raise HTTPException(status_code=409, detail={"code": "fondateur"})


@router.get("/administrateurs")
async def lire_administrateurs(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Les administrateurs fondateurs (`ADMIN_IDS`) et les administrateurs nommés dans
    l'application. Administrateur seul."""
    _admin_seul(user)
    return await _administrateurs(db)


@router.put("/administrateurs/{profile_id}")
async def nommer_administrateur(
    profile_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Nomme un administrateur : la ligne `account_capability(profile_id, "admin")`.
    Un fondateur : 409 `fondateur` ; un profil absent : 404 ; déjà nommé : 200 sans
    écriture. Administrateur seul."""
    _admin_seul(user)
    _refuser_fondateur(profile_id)
    brut = profile_id.strip()
    profil = (
        await db.get(Profile, int(brut))
        if re.fullmatch(r"[0-9]+", brut) and int(brut) <= _BIGINT_MAX
        else None
    )
    if profil is None:
        raise HTTPException(status_code=404, detail="Profil inconnu.")
    if await db.get(AccountCapability, (profil.id, "admin")) is None:
        db.add(AccountCapability(profile_id=profil.id, capability="admin", granted_by=int(user["id"])))
        journal.consigner(db, user, "admin.nommer", objet=str(profil.id), lignes=[], toujours=True)
        await db.commit()
        settings.ADMINS_NOMMES = settings.ADMINS_NOMMES | {str(profil.id)}
    return await _administrateurs(db)


@router.delete("/administrateurs/{profile_id}")
async def retirer_administrateur(
    profile_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retire un administrateur nommé. Un fondateur : 409 `fondateur` ; pas nommé : 404.
    Administrateur seul."""
    _admin_seul(user)
    _refuser_fondateur(profile_id)
    brut = profile_id.strip()
    ligne = (
        await db.get(AccountCapability, (int(brut), "admin"))
        if re.fullmatch(r"[0-9]+", brut) and int(brut) <= _BIGINT_MAX
        else None
    )
    if ligne is None:
        raise HTTPException(status_code=404, detail="Administrateur nommé inconnu.")
    retire = str(ligne.profile_id)
    await db.delete(ligne)
    journal.consigner(db, user, "admin.retirer", objet=retire, lignes=[], toujours=True)
    await db.commit()
    settings.ADMINS_NOMMES = settings.ADMINS_NOMMES - {retire}
    return await _administrateurs(db)
