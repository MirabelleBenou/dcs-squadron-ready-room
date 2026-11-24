"""Routes `/api/*`. Lot 1 : `GET /api/me`. Lot 2 : événements/présences/hebdo
(cf. `app/events.py`, moteur de récurrence dans `app/recurrence.py`). Lot 3a :
capacités dans `/api/me` + `GET /api/stream` (cf. `app/realtime.py`). Lot 8 :
`GET /api/version` (versioning exclusif Ready Room, cf. `VERSION` racine)."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crests
from app.auth import get_current_user
from app.capabilities import (
    can_create_event,
    est_invite,
    has_capability,
    has_command_access,
    is_admin,
    require_command_access,
    require_debrief_access,
)
from app.command.api import _wing_to_dict, router as command_router
from app.config import settings
from app.db import get_db
from app.debrief import referentiel
from app.debrief.api import router as debrief_router
from app.events import router as events_router
from app.models import Profile, Squadron, SquadronMembership, Wing
from app.realtime import router as realtime_router
from app.squadron import get_name_strip_tokens

router = APIRouter(prefix="/api")
router.include_router(events_router)
router.include_router(realtime_router)
# Lot D1 -- module Debriefing (backend seul, cf. BRIEF_SONNET_ReadyRoom_
# Debrief_D1_data_engine) : monté sous /api/debrief, aucune route existante
# modifiée.
# v0.76 -- Module "en chantier" : accès réservé (admin ou capacité
# `debrief.access`). Gate posé UNIQUEMENT ici, au point de montage unique
# (cf. brief Lot Chantier Debrief + Avatar §3) -- jamais route par route.
router.include_router(
    debrief_router, dependencies=[Depends(require_debrief_access)]
)
# Phase 3, lot 3.1 -- module Centre de Commandement (socle seul, aucune
# route à ce lot). Gate posé UNIQUEMENT ici, au point de montage unique
# (cf. spec Socle v1.1 §5.1) -- jamais route par route.
router.include_router(
    command_router, dependencies=[Depends(require_command_access)]
)

# `VERSION` (racine du dépôt) est l'unique source de vérité (cf. brief Lot 8).
# Lu UNE SEULE FOIS au démarrage — jamais de re-lecture disque par requête.
# `/api/version` est volontairement SANS `Depends(get_current_user)` :
# le footer doit s'afficher aussi sur l'écran de login (non authentifié).
_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"
_APP_VERSION = _VERSION_FILE.read_text(encoding="utf-8").strip()


@router.get("/version")
async def read_version():
    return {"version": _APP_VERSION}

# Capacités résolues et exposées par `/api/me` (cf. brief Lot 3a §4). Liste
# figée volontairement courte au MVP ; toute nouvelle capacité ajoutée à
# `capabilities.py` doit être ajoutée ici pour être exposée au front.
_EXPOSED_CAPABILITIES = (
    "event.create",
    "event.edit_any",
    "debrief.access",
    "command.access",
    # Lot 3.4, §6 : le front en a besoin pour révéler le formulaire de
    # l'écran Campagnes (`campaign.manage`) et l'action de suppression
    # (`campaign.delete`) -- même patron que `event.edit_any`, jamais
    # `session.edit` (sérialisé session par session, pas ici).
    "campaign.manage",
    "campaign.delete",
)


def _command_rank(lignes):
    """Lot « Le Centre de Commandement dit ce qu'il fait » (R1, R4) -- pure :
    `lignes` = les appartenances du membre, `(role, ended_at, status,
    designation)`. `{"rank": "leader"|"deputy", "squadron": <désignation>}` pour
    une appartenance OUVERTE de rang chef ou adjoint sur une escadrille ACTIVE ;
    `None` sinon (simple membre, rien, appartenance close, escadrille en sommeil)."""
    for role, ended_at, status, designation in lignes:
        if role in ("leader", "deputy") and ended_at is None and status == "actif":
            return {"rank": role, "squadron": designation}
    return None


@router.get("/me")
async def read_me(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Contrat v2 (Lot 3b) + `squadron` (Lot 6) + `is_admin` (correctif
    v0.9913, addendum 1) : `{id, name, avatar_hash, lang, squadron,
    capabilities, is_admin, name_prefixes}`. Lot « Le Centre de Commandement
    dit ce qu'il fait » (R1) : `command_rank`, `null` ou `{rank, squadron}` --
    le rang de chef ou d'adjoint sur une escadrille active, que la station
    lit pour dire à un chef sans le rôle des chefs pourquoi le Centre lui est
    fermé. Lot « L'accès invité » (R7) : `invite`, `null` pour un membre,
    `{jusqua}` (ISO 8601) pour un invité -- qui n'a que `debrief.access` et
    `command.access`, aucun rang, aucune escadrille. `name`/`lang`/`avatar_hash`
    proviennent de la session applicative (posée à `/auth/callback`, cf.
    `app/auth.py`) ; `squadron` et les rôles qui fondent `capabilities` se
    lisent sur le profil depuis le lot « L'appel » (`get_current_user`)."""
    roles = user.get("roles", [])
    invite = est_invite(user)
    capabilities = [
        cap for cap in _EXPOSED_CAPABILITIES if await has_capability(db, roles, cap)
    ]
    if await can_create_event(db, user) and "event.create" not in capabilities:
        capabilities.append("event.create")
    if is_admin(user) and "event.edit_any" not in capabilities:
        capabilities.append("event.edit_any")
    if is_admin(user) and "debrief.access" not in capabilities:
        capabilities.append("debrief.access")
    if await has_command_access(db, user) and "command.access" not in capabilities:
        capabilities.append("command.access")
    # Lot 3.4, §6 : « les administrateurs les ont toujours, en dur » --
    # même patron que event.edit_any/debrief.access ci-dessus. Sans cet
    # ajout, un administrateur sans la capacité par rôle ne verrait ni le
    # formulaire ni l'action de suppression sur l'écran Campagnes, alors
    # que les deux routes le laisseraient passer (is_admin() y est
    # toujours vérifié en premier) -- l'écran mentirait sur ce qu'il
    # autorise réellement.
    if is_admin(user) and "campaign.manage" not in capabilities:
        capabilities.append("campaign.manage")
    if is_admin(user) and "campaign.delete" not in capabilities:
        capabilities.append("campaign.delete")
    if invite:
        # Lot « L'accès invité » (R7) : deux capacités de lecture, dans cet
        # ordre, et rien d'autre -- quoi que les calculs ci-dessus aient dit.
        capabilities = ["debrief.access", "command.access"]

    rank_rows = (
        await db.execute(
            select(
                SquadronMembership.role,
                SquadronMembership.ended_at,
                Squadron.status,
                Squadron.designation,
            )
            .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
            .where(SquadronMembership.profile_id == int(user["id"]))
        )
    ).all()

    return {
        "id": user["id"],
        "name": user.get("name"),
        "avatar_hash": user.get("avatar"),
        "lang": user.get("lang", "fr"),
        "squadron": user.get("squadron"),
        "capabilities": capabilities,
        # Correctif « vérités du roster » v0.9913, addendum 1 : champ
        # DISTINCT de `capabilities` (n'entre pas dans
        # `_EXPOSED_CAPABILITIES`) -- miroir exact du gate serveur de
        # `POST .../identify` (app/debrief/api.py), qui teste is_admin(user)
        # en premier. Un seul point de vérité : le front ne peut plus
        # afficher une action qu'is_admin() rejettera.
        "is_admin": is_admin(user),
        # Lot 2.2b : lu en base (wing + escadrilles), plus depuis
        # `Settings` -- même contrat exact (cf. app/squadron.py, porte P4).
        "name_prefixes": await get_name_strip_tokens(db),
        # Lot « L'écran Escadre du Centre » : l'identité de l'escadre
        # (`_wing_to_dict`, six clés), SEULE source du front ; `null` sans
        # ligne `wing`.
        "wing": await _read_wing_dict(db),
        # Lot « Le Centre de Commandement dit ce qu'il fait » (R1).
        "command_rank": None if invite else _command_rank(rank_rows),
        # Lot « L'accès invité » (R7) : `null` pour un membre ; pour un invité,
        # l'échéance de son invitation (ISO 8601), que le bandeau affiche.
        "invite": {"jusqua": user["invite_jusqua"]} if invite else None,
        # Lot « rr-fuseau-reglage » (v1.0120) : le fuseau réglé de l'escadre, que le front lit.
        "fuseau": settings.REFERENCE_TZ,
    }


@router.get("/referentiels/libelles")
async def read_referentiel_libelles(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les référentiels : types et armes » : les libellés que l'écran
    Référentiels du Centre a posés, pour TOUS les écrans du front --
    `{types: {cle: libelle}, armes: {cle: libelle}}`, les seules clés qui ont
    un libellé. Authentifié seulement (comme `/api/me`) : un libellé n'est
    qu'un nom d'affichage, sans le droit d'accès au Centre ni au Débrief.

    Lot « La plume » §3.1 -- la lecture vit dans `referentiel.lire_libelles`,
    la même que celle qui nourrit la fiche du récit."""
    return await referentiel.lire_libelles(db)


async def _read_wing_dict(db: AsyncSession):
    wing = (
        await db.execute(select(Wing).order_by(Wing.id.asc()).limit(1))
    ).scalar_one_or_none()
    return _wing_to_dict(wing) if wing is not None else None


@router.post("/seen")
async def mark_seen(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Horodatage de visite (v0.36, tag "NOUVEAU"). Renvoie l'ancien
    `last_seen_at` (avant mise à jour) : le front compare `Event.created_at`
    à cette valeur pour déterminer quels événements sont nouveaux depuis la
    dernière visite. `previous=null` en 1ère visite (aucun tag)."""
    profile = await db.get(Profile, int(user["id"]))
    if profile is None:
        return {"previous": None}
    old = profile.last_seen_at
    profile.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return {"previous": old.isoformat() if old else None}


# Lot 3.2e, volet ② -- lecture de l'écusson d'une escadrille (§7.2). 3 -> 4
# routes directes. C'est le point dur du lot : le produit n'avait jamais
# renvoyé au navigateur un binaire déposé par un utilisateur (aucun
# `FileResponse` ailleurs dans `app/`, le seul flux existant est le bus
# temps réel de `app/realtime.py`).
#
# Garde : `Depends(get_current_user)` SEUL -- PAS la garde du module
# Centre de Commandement (`require_command_access`). Ce n'est pas un
# relâchement, c'est la bonne portée : *voir* l'écusson de son escadrille
# n'est pas un acte de commandement, *l'écrire* en est un (cf.
# `PUT /command/squadrons/{id}/crest`, gardée par `can_admin_squadron`).
# Placer la lecture derrière la garde du module obligerait à créer une
# seconde route le jour où le Débriefing s'habillera par escadrille --
# l'usage futur pour lequel le porteur fait poser cet écusson.
#
# Aucune garde route par route ailleurs : la règle « garde au point de
# montage unique » (spec Socle §11.2) concerne les ROUTEURS de module ;
# elle reste intacte, `/api/me` et `/api/seen` ci-dessus sont déjà écrites
# exactement ainsi.
#
# Un second montage `StaticFiles` sur le volume est REFUSÉ (cf. brief
# §7.2) : il exposerait le volume sans aucun contrôle d'accès.
@router.get("/squadrons/{squadron_id}/crest")
async def read_squadron_crest(
    squadron_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """`crest_sha` à NULL (ou escadrille introuvable) -> 404. `crest_sha`
    renseigné mais fichier absent du disque -> 404, JAMAIS une erreur
    serveur : ce cas arrivera (une base restaurée depuis `pg_dump` sans le
    volume des écussons dit qu'il y a un écusson là où il n'y a plus de
    fichier ; l'écran doit retomber sur l'emplacement vide, pas sur une
    image cassée, cf. app.js). Sinon, le PNG, `Cache-Control: private,
    max-age=31536000, immutable` -- `private` parce que la ressource est
    derrière une authentification, `immutable` légitime parce que l'URL
    porte l'empreinte (`?v={crest_sha}`, §5.2) : le contenu d'une URL
    donnée ne change jamais."""
    squadron = await db.get(Squadron, squadron_id)
    if squadron is None or not squadron.crest_sha:
        raise HTTPException(status_code=404, detail="Aucun écusson.")

    path = crests.crest_path(squadron_id)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Écusson absent du volume.")

    return Response(
        content=path.read_bytes(),
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )


# Lot « L'écran Escadre du Centre » -- lecture de l'emblème de l'escadre.
# AUCUNE garde : l'emblème est public, la page de connexion l'affiche avant
# toute authentification. `emblem_sha` NULL ou fichier absent du volume ->
# 404, JAMAIS une erreur serveur (le front retombe sur le logo statique).
# `public` + `immutable` : l'URL porte l'empreinte (`?v={emblem_sha}`), le
# contenu d'une URL donnée ne change jamais.
@router.get("/wing/emblem")
async def read_wing_emblem(db: AsyncSession = Depends(get_db)):
    wing = (
        await db.execute(select(Wing).order_by(Wing.id.asc()).limit(1))
    ).scalar_one_or_none()
    if wing is None or not wing.emblem_sha:
        raise HTTPException(status_code=404, detail="Aucun emblème.")

    path = crests.wing_emblem_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Emblème absent du volume.")

    return Response(
        content=path.read_bytes(),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
