"""Router `/api/debrief/*` — spec §4 / brief §4.

Monté sous `/debrief` par ce module ; le préfixe `/api` est appliqué par le
router parent (`app/api.py`), même pattern que `events_router`/`realtime_router`.
Auth : mêmes dépendances que l'existant (`get_current_user`), gating admin
via `is_admin` pour l'override manuel d'identité — copié du pattern
`app/events.py`.

Lot « Le nom qu'on retient » v0.9917 : deux routes neuves (`GET /members`,
`DELETE .../flights/{id}/alias`) ; `POST .../identify` gagne l'écriture de
l'alias retenu (`_record_alias`, brief §1/§5) sans changer de contrat ;
`DELETE .../identify` change de sémantique -- détachement définitif au lieu
d'une simple annulation (brief §5). Le reste du fichier (upload, sessions,
campagnes) n'est pas touché.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import and_, delete, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import crests, llm, taches
from app.auth import get_current_user
from app.capabilities import can_edit_session, is_admin
from app.command import journal
from app.db import AsyncSessionLocal, get_db
from app.debrief import categorize, referentiel
from app.debrief import engine
from app.debrief import rattachement
from app.debrief import report_facts
from app.debrief import revision
from app.debrief.acmi import AcmiParseError, parse_acmi
from app.debrief.debriefer import DebrieferParseError, parse_debrief_log
from app.debrief.display import beautify_mission_title
from app.debrief.schemas import (
    CartesDcsPayload,
    DeplacerPayload,
    FusionnerPayload,
    IdentifyOverride,
    PeriodeVolPayload,
    SessionEditPayload,
)
from app.debrief_models import (
    Campaign,
    DebriefEvent,
    DebriefFlight,
    DebriefGraveyard,
    DebriefReport,
    DebriefReportRun,
    DebriefSession,
    DebriefUpload,
    LlmCallLog,
    ProfileDcsAlias,
)
from app.models import Profile, Squadron, SquadronMembership, Wing
from app.realtime import publish_invalidate
from app.recurrence import fuseau_reference

router = APIRouter(prefix="/debrief")

# Lot « Finitions du Débrief » (ARC-04) : plafonds du dépôt, un par type de
# fichier (R5) -- la lecture s'arrête au dépassement, avant toute ingestion.
# v1.0096 (rr-debrief-plafond-depot) : 128 Mio pour un debrief.log, le plus gros
# déposé en production pesant 25,2 Mio (mesure du 18 novembre).
PLAFOND_ACMI = 256 * 1024 * 1024
PLAFOND_DEBRIEF = 128 * 1024 * 1024
logger = logging.getLogger(__name__)


# --- Lot « Filtrage des vols vides » v0.9934 --------------------------------
#
# Un vol de pure mécanique (connexion, démarrage, décollage éventuel,
# déconnexion sans rien apprendre) encombre l'écran sans rien apprendre
# (brief §2). Rien n'est supprimé ni marqué en base : le verdict se
# recalcule à chaque lecture, si bien qu'un vol réapparaît de lui-même dès
# qu'un dépôt lui apporte de la matière -- aucun drapeau n'est jamais écrit.
#
# Liste NÉGATIVE, jamais positive (brief §3) : un type d'évènement inconnu
# rend le vol visible -- mieux vaut un vol montré à tort qu'un vol perdu,
# exigence explicite du commanditaire. Les six types ne sont écrits qu'ici,
# nulle part ailleurs dans le dépôt.
_MECHANICAL_EVENT_TYPES = (
    "under control",
    "relinquished",
    "engine startup",
    "engine shutdown",
    "takeoff",
    "ai abort mission",
)


async def _significant_object_ids_par_session(db: AsyncSession, session_ids=None) -> dict:
    """Lot « Correctifs de B » -- le verdict des vols vides, pour plusieurs
    sessions en UNE requête : par session, l'ensemble des `object_id` porteurs
    d'au moins un évènement non mécanique, en initiateur ou en cible. C'est
    la seule requête du dépôt sur `_MECHANICAL_EVENT_TYPES` : l'écran de
    session, la liste des missions, et désormais l'accueil, l'escadre, les
    écrans E et F jugent un vol de la même façon. `session_ids` à `None` :
    toutes les sessions."""
    q = select(
        DebriefEvent.session_id, DebriefEvent.initiator_object_id, DebriefEvent.target_object_id
    ).where(DebriefEvent.type.notin_(_MECHANICAL_EVENT_TYPES))
    if session_ids is not None:
        q = q.where(DebriefEvent.session_id.in_(list(session_ids)))
    ids: dict = defaultdict(set)
    for session_id, initiator_id, target_id in (await db.execute(q)).all():
        if initiator_id:
            ids[session_id].add(initiator_id)
        if target_id:
            ids[session_id].add(target_id)
    return ids


async def _significant_object_ids(db: AsyncSession, session_id: uuid.UUID) -> set[str]:
    """Ensemble des `object_id` (debrief) porteurs d'au moins un évènement
    non mécanique pour `session_id`, en INITIATEUR OU en CIBLE (brief §4.1) :
    un pilote abattu au décollage sans avoir tiré n'est initiateur d'aucun
    évènement significatif -- ne retenir que l'initiateur masquerait ce vol
    à tort. Fonction unique : les deux points de chargement (`list_sessions`,
    `get_session`) l'appellent tous deux, aucun n'a sa propre requête.
    Réutilise les index existants `ix_debrief_event_session_initiator` /
    `ix_debrief_event_session_target` -- aucun index neuf. Lot « Correctifs
    de B » : la requête vit dans `_significant_object_ids_par_session`."""
    return set((await _significant_object_ids_par_session(db, [session_id])).get(session_id, set()))


def _est_significatif(vol, significatifs: dict) -> bool:
    """Lot « Correctifs de B » -- le verdict de l'écran de session sur un vol :
    réel s'il porte au moins un évènement non mécanique. `significatifs` : la
    sortie de `_significant_object_ids_par_session`. Pure."""
    return bool(vol.object_id) and vol.object_id in significatifs.get(vol.session_id, ())


def _est_vol_escadre(vol, significatifs: dict | None) -> bool:
    """Lot « Le Débrief n'est plus en chantier, et l'escadre compte les siens » --
    la règle des chiffres « de l'escadre » : un vol compte s'il est RÉEL
    (`_est_significatif`) ET rattaché à un membre (`pilote_profile_id` non nul) ;
    un invité ou une IA n'y entre pas. C'est la règle des heures de `get_escadre`
    et du compte des pilotes. Posée ici, une seule fois : l'Accueil
    (`_accueil_payload`) et la fiche d'une campagne (`_fiche_campagne`) la
    partagent. `significatifs` à `None` : tous les vols sont réels (comme dans
    `_accueil_payload`). Pure."""
    if vol.pilote_profile_id is None:
        return False
    return significatifs is None or _est_significatif(vol, significatifs)


# --- Sérialisation ----------------------------------------------------------


def _periode_effective(vol) -> str | None:
    """Lot « Les heures de jour et de nuit » (v1.0068, le porteur, 4 novembre) :
    la période d'un vol -- la correction à la main si elle existe, sinon celle
    que calcule le moteur. Lecture tolérante (`getattr`) : les doubles des
    tests et les lignes d'avant le recalcul n'ont pas ces attributs. Pure."""
    corrigee = getattr(vol, "periode_corrigee", None)
    if corrigee is not None:
        return corrigee
    return getattr(vol, "periode", None)


def _heures_de_mission(vols) -> tuple[float, float]:
    """Lot « Les heures comptées par mission » (v1.0069, le porteur, 4 novembre) :
    `(secondes, secondes_nuit)` -- par session, la longueur de la réunion des
    intervalles des vols (le temps où au moins un pilote est en l'air), puis
    la somme des sessions ; la nuit, la même réunion sur les seuls vols de
    nuit. Un intervalle vide ou inversé est ignoré. Pure."""

    def _reunion(intervalles: list) -> float:
        total, fin_courante = 0.0, None
        for debut, fin in sorted(intervalles):
            if fin_courante is None or debut > fin_courante:
                total += fin - debut
                fin_courante = fin
            elif fin > fin_courante:
                total += fin - fin_courante
                fin_courante = fin
        return float(total)

    par_session: dict = defaultdict(lambda: ([], []))
    for v in vols:
        debut, fin = (v.t_start or 0), (v.t_end or 0)
        if fin <= debut:
            continue
        tous, nuit = par_session[v.session_id]
        tous.append((debut, fin))
        if _periode_effective(v) == "nuit":
            nuit.append((debut, fin))
    secondes = sum(_reunion(t) for t, _n in par_session.values())
    secondes_nuit = sum(_reunion(n) for _t, n in par_session.values())
    return float(secondes), float(secondes_nuit)


def _correction_periode(calculee: str | None, demandee: str) -> str | None:
    """Lot « Les heures de jour et de nuit » : la correction à poser pour la
    période `demandee` -- `None` (pas de correction) quand elle égale celle
    que calcule le moteur. Pure."""
    return None if demandee == calculee else demandee


def _peut_corriger_periode(pilote_profile_id, user_id, peut_editer: bool) -> bool:
    """Lot « Les heures de jour et de nuit » : la période d'un vol se corrige
    par son pilote, et par quiconque peut modifier une session. Pure."""
    if peut_editer:
        return True
    return pilote_profile_id is not None and int(pilote_profile_id) == int(user_id)


def _flight_to_dict(
    f: DebriefFlight, crest: dict | None = None, nom: str | None = None
) -> dict:
    # Correctif « Le nom du membre » v1.0021 (R1) : `pilote_nom` = nom brut du
    # membre rattaché (`global_name or username`, résolu à la lecture par
    # l'appelant), None sans profil. L'indicatif observé garde la priorité
    # côté lecteur (écran, fiche) ; ce nom ne le remplace jamais en base.
    return {
        "id": str(f.id),
        "session_id": str(f.session_id),
        "object_id": f.object_id,
        "acmi_track_id": f.acmi_track_id,
        "aircraft_type": f.aircraft_type,
        "coalition": f.coalition,
        "pilote_profile_id": str(f.pilote_profile_id) if f.pilote_profile_id else None,
        "pilot_callsign": f.pilot_callsign,
        "pilote_nom": nom,
        "identity_state": f.identity_state,
        "identity_source": f.identity_source,
        "t_start": f.t_start,
        "t_end": f.t_end,
        "slot_mission": f.slot_mission,
        "mission_id_dcs": f.mission_id_dcs,
        "stats": f.stats,
        "crest": crest,
        # Lot « Les heures de jour et de nuit » : la période (corrigée ou
        # calculée) et si elle a été corrigée à la main.
        "periode": _periode_effective(f),
        "periode_corrigee": getattr(f, "periode_corrigee", None) is not None,
    }


async def _crest_ref(db: AsyncSession, profile_id) -> dict | None:
    """Lot D — coordonnées de l'écusson à poser sur la fiche de vol :
    l'escadrille du PILOTE, via son appartenance OUVERTE. None si le vol
    est anonyme, si le pilote n'a pas d'escadrille, ou si l'escadrille
    n'a pas d'écusson -- l'écran retombe alors sur l'emplacement vide.

    Même jointure que list_debrief_members / list_command_members
    (appartenance ouverte puis Squadron), mais SANS leurs gardes : cette
    résolution accompagne une fiche que tout membre a le droit de lire.
    """
    if not profile_id:
        return None
    row = (await db.execute(
        select(Squadron.id, Squadron.crest_sha)
        .select_from(SquadronMembership)
        .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .where(
            SquadronMembership.profile_id == int(profile_id),
            SquadronMembership.ended_at.is_(None),
        )
    )).first()
    if row is None or not row[1]:
        return None
    return {"squadron_id": row[0], "crest_sha": row[1]}


async def _crest_refs_bulk(db: AsyncSession, profile_ids: set) -> dict:
    """Version groupée de _crest_ref, pour la liste de vols d'une session
    (§8.2, appelant ~594) : UNE requête pour tous les pilote_profile_id de
    la liste, jamais une requête par vol -- même discipline que squad_map
    déjà présent dans ce fichier."""
    ids = {int(pid) for pid in profile_ids if pid}
    if not ids:
        return {}
    rows = (await db.execute(
        select(SquadronMembership.profile_id, Squadron.id, Squadron.crest_sha)
        .select_from(SquadronMembership)
        .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .where(
            SquadronMembership.profile_id.in_(ids),
            SquadronMembership.ended_at.is_(None),
        )
    )).all()
    out = {}
    for profile_id, squadron_id, crest_sha in rows:
        if crest_sha:
            out[profile_id] = {"squadron_id": squadron_id, "crest_sha": crest_sha}
    return out


async def _noms_membres_bulk(db: AsyncSession, profile_ids: set) -> dict:
    """Correctif « Le nom du membre » v1.0021 (R1) -- `profile_id -> nom` de
    l'annuaire (`global_name or username`, la règle de `GET /members` et de
    `_redaction_en_cours_et_par`), en UNE requête pour tous les identifiants
    d'une réponse, jamais une requête par vol -- même patron que
    `_crest_refs_bulk`. Un profil sans nom n'a pas d'entrée."""
    ids = {int(pid) for pid in profile_ids if pid}
    if not ids:
        return {}
    rows = (await db.execute(
        select(Profile.id, Profile.global_name, Profile.username)
        .where(Profile.id.in_(ids))
    )).all()
    return {pid: (gname or uname) for pid, gname, uname in rows if (gname or uname)}


def _graveyard_to_dict(g: DebriefGraveyard) -> dict:
    display_name, _, _ = categorize.categorize(g.unit_type)
    # Lot « Les référentiels » : la catégorie se lit à l'affichage, forcée par
    # l'écran Référentiels si elle l'est ; le `display_name` reste celui de
    # `categorize`.
    category = referentiel.categorie_cible(g.unit_type)
    return {
        "id": str(g.id),
        "unit_type": g.unit_type,
        "display_name": display_name,
        "category": category,
        "coalition": g.coalition,
        "x": g.x,
        "y": g.y,
        "alt": g.alt,
        "heading": g.heading,
        "seen_in": g.seen_in,
    }


async def _session_or_404(db: AsyncSession, session_id: uuid.UUID) -> DebriefSession:
    session = await db.get(DebriefSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return session


def _campaign_to_dict(c: Campaign) -> dict:
    """Forme complète (routes `/campaigns`, Lot 2.3 §4.4)."""
    return {"id": str(c.id), "name": c.name, "status": c.status, "sim": c.sim}


def _campaign_ref(campaign_id: uuid.UUID | None, name_by_id: dict[uuid.UUID, str]) -> dict | None:
    """Forme réduite embarquée sur une session (brief §4.7) :
    `None | {"id": str, "name": str}`."""
    if campaign_id is None:
        return None
    name = name_by_id.get(campaign_id)
    if name is None:
        return None
    return {"id": str(campaign_id), "name": name}


def _nature_depot(valeur: str | None) -> str | None:
    """Lot « Mission ou training » -- la nature choisie dans « Déposer ».
    Pure : testée hors ligne (tests/test_mission_training.py). `None` ou chaîne
    vide : aucun choix (`None`) ; `mission` ou `training` : la valeur, telle
    quelle ; toute autre chose : `ValueError`, que la route rend en 422 avant
    l'ingestion, comme `campaign_id`."""
    if valeur is None or valeur == "":
        return None
    if valeur in ("mission", "training"):
        return valeur
    raise ValueError("nature invalide")


# --- POST /upload ------------------------------------------------------------


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    kind: str = Form(...),
    depositor: str | None = Form(None),
    mission_name: str | None = Form(None),
    wing_note: str | None = Form(None),
    campaign_id: str | None = Form(None),
    nature: str | None = Form(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if kind not in ("acmi", "debrief"):
        raise HTTPException(status_code=422, detail="kind doit être 'acmi' ou 'debrief'")

    depositor_id: int | None = None
    if depositor:
        try:
            depositor_id = int(depositor)
        except ValueError:
            raise HTTPException(status_code=422, detail="depositor invalide")

    if kind == "debrief" and depositor_id is None:
        raise HTTPException(
            status_code=422, detail="depositor (profile_id) requis pour un upload 'debrief'"
        )

    # Lot 2.1 §4.4 : strip(), chaîne vide traitée comme None, bornes de
    # longueur -- appliqué si et seulement si le champ de la session est
    # vide (idempotence multi-fichiers), cf. engine._apply_optional_deposit_fields.
    mission_name_clean = (mission_name or "").strip() or None
    if mission_name_clean is not None and len(mission_name_clean) > 80:
        raise HTTPException(
            status_code=422, detail="Nom de mission trop long (80 caractères max)"
        )
    wing_note_clean = (wing_note or "").strip() or None
    if wing_note_clean is not None and len(wing_note_clean) > 2000:
        raise HTTPException(status_code=422, detail="Note trop longue (2000 caractères max)")

    # Lot 2.3 §4.5 : format seulement ici (-> 422 immédiat, avant tout
    # effet de bord) ; l'existence en base est vérifiée par
    # `engine.ingest_file` (-> IngestError -> 422, jamais une clé
    # étrangère qui casse au commit).
    campaign_uuid: uuid.UUID | None = None
    if campaign_id:
        try:
            campaign_uuid = uuid.UUID(campaign_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="campaign_id invalide")

    # Lot « Mission ou training » : format seulement ici (-> 422 avant
    # l'ingestion) ; la nature se pose plus bas, après l'ingestion, et
    # `engine.py` n'est pas touché.
    try:
        nature_choisie = _nature_depot(nature)
    except ValueError:
        raise HTTPException(status_code=422, detail="nature invalide")

    # Lot « Finitions du Débrief » (ARC-04) : lecture bornée au plafond du
    # type ; au dépassement, 413 avant toute ingestion ni écriture.
    plafond = PLAFOND_ACMI if kind == "acmi" else PLAFOND_DEBRIEF
    try:
        raw_bytes = await crests.read_bounded(file, plafond)
    except crests.CrestTooLarge:
        nom = "un ACMI" if kind == "acmi" else "un debrief.log"
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop lourd : {nom} fait {plafond // (1024 * 1024)} Mio au plus.",
        )

    try:
        summary = await engine.ingest_file(
            db,
            kind=kind,
            depositor_profile_id=depositor_id,
            filename=file.filename or "upload",
            raw_bytes=raw_bytes,
            mission_name=mission_name_clean,
            wing_note=wing_note_clean,
            campaign_id=campaign_uuid,
        )
    except engine.IngestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (AcmiParseError, DebrieferParseError) as exc:
        raise HTTPException(status_code=422, detail=f"Parsing impossible : {exc}") from exc

    # Lot 2.1, addendum A2 : troisième point de sérialisation exposant un
    # titre (le moteur ne renvoie que du brut, cf. engine.ingest_file). La
    # résolution d'affichage se fait ici, jamais dans engine.py.
    summary["display_title"] = summary.get("display_name") or beautify_mission_title(
        summary.get("title")
    )

    # Lot « Mission ou training » : le choix du déposant ne vaut que si ce
    # dépôt CRÉE la session ; un dépôt qui en rejoint une ne change rien. Dans
    # tous les cas, le résumé porte la nature de la session.
    session_nature = await db.get(DebriefSession, uuid.UUID(summary["session_id"]))
    if summary.get("session_created") and nature_choisie is not None and session_nature is not None:
        session_nature.nature = nature_choisie
        await db.commit()
    summary["nature"] = session_nature.nature if session_nature is not None else "mission"

    return summary


# --- GET /sessions ------------------------------------------------------------


@router.get("/sessions")
async def list_sessions(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(DebriefSession).order_by(DebriefSession.created_at.desc()))
    sessions = result.scalars().all()

    # Passe 1 (inchangée dans son principe) : n_uploads + flights par session.
    # On collecte au passage l'ensemble global des pilotes identifiés, pour
    # la résolution batchée des escadrilles (Volet A) -- jamais par session.
    per_session: list[dict] = []
    all_pids: set[int] = set()
    # Correctif « Le nom du membre » v1.0021 (R2) : les identifiants dont on
    # résout le nom se collectent sur `flights_all` (`n_deposited` la lit),
    # pas seulement sur `flights`.
    noms_pids: set[int] = set()
    # Lot « La liste des missions en requêtes groupées » (v1.0090) : le compte
    # des dépôts, les vols et les objets significatifs se lisent en UNE
    # requête chacun pour toute la liste, jamais par session. Sans aucune
    # session, aucune de ces trois requêtes.
    ids_sessions = [s.id for s in sessions]
    n_uploads_par_session: dict = {}
    vols_par_session: dict = defaultdict(list)
    significatifs: dict = {}
    if ids_sessions:
        n_uploads_par_session = {
            sid: n
            for sid, n in (
                await db.execute(
                    select(DebriefUpload.session_id, func.count())
                    .where(DebriefUpload.session_id.in_(ids_sessions))
                    .group_by(DebriefUpload.session_id)
                )
            ).all()
        }
        for vol in (
            await db.execute(select(DebriefFlight).where(DebriefFlight.session_id.in_(ids_sessions)))
        ).scalars().all():
            vols_par_session[vol.session_id].append(vol)
        significatifs = await _significant_object_ids_par_session(db, ids_sessions)
    for s in sessions:
        n_uploads = n_uploads_par_session.get(s.id, 0)
        flights_all = vols_par_session.get(s.id, [])
        # Lot « Filtrage des vols vides » v0.9934 (brief §4.2) : filtre
        # appliqué juste après le chargement -- tout ce qui en dérive
        # ci-dessous (n_kills, session_pids, n_flights) hérite du filtre.
        # `flights_all` (non filtrée) reste disponible pour `_named_pilots`
        # (brief §4.3, exception `n_deposited`).
        significant_ids = significatifs.get(s.id, set())
        flights = [f for f in flights_all if f.object_id and f.object_id in significant_ids]
        n_kills = sum(len(f.stats.get("kills", [])) for f in flights)
        session_pids = {f.pilote_profile_id for f in flights if f.pilote_profile_id}
        all_pids.update(session_pids)
        noms_pids.update(f.pilote_profile_id for f in flights_all if f.pilote_profile_id)
        per_session.append(
            {
                "s": s,
                "n_uploads": n_uploads,
                "flights": flights,
                "flights_all": flights_all,
                "n_kills": n_kills,
                "session_pids": session_pids,
            }
        )

    # Résolution batchée escadrilles -- 1 seule requête pour toute la liste
    # (pas de N+1 par session). Si aucun pilote identifié : pas de requête.
    squad_map: dict[int, str] = {}
    noms_map: dict[int, str] = {}
    if all_pids or noms_pids:
        rows = (
            await db.execute(
                select(Profile.id, Profile.squadron, Profile.global_name, Profile.username)
                .where(Profile.id.in_(all_pids | noms_pids))
            )
        ).all()
        squad_map = {pid: squad for pid, squad, _g, _u in rows if squad and pid in all_pids}
        noms_map = {pid: (g or u) for pid, _sq, g, u in rows if (g or u)}

    # Lot 2.3 §4.7/§9 : résolution batchée campagnes, même patron que
    # squad_map ci-dessus -- 1 seule requête pour toute la page, jamais en
    # N+1 (défaut nommé §9 du brief).
    campaign_ids = {item["s"].campaign_id for item in per_session if item["s"].campaign_id}
    campaign_name_by_id: dict[uuid.UUID, str] = {}
    if campaign_ids:
        rows = (
            await db.execute(
                select(Campaign.id, Campaign.name).where(Campaign.id.in_(campaign_ids))
            )
        ).all()
        campaign_name_by_id = {cid: name for cid, name in rows}

    # Lot « Le rattachement des dépôts » : la marque « À vérifier », en une
    # requête pour toute la liste (`_sessions_a_verifier`).
    a_verifier_ids = await _sessions_a_verifier(db)

    out = []
    for item in per_session:
        s = item["s"]
        flights = item["flights"]
        n_pilots = len(item["session_pids"])
        squadrons = sorted({squad_map[pid] for pid in item["session_pids"] if squad_map.get(pid)})
        n_named, named_sample, n_anon, n_deposited, n_known = _named_pilots(
            flights, item["flights_all"], noms_map
        )
        # Correctif Jauge v0.9935 : dénominateur = n_known + n_anon (pas
        # n_named + n_anon) -- un déposant pèse au dénominateur même si son
        # propre vol a été filtré, sans quoi la jauge peut dépasser 100 %.
        denom = n_known + n_anon
        doc_ratio = round(n_deposited / denom, 3) if denom else None
        out.append(
            {
                "id": str(s.id),
                "title": s.title,
                # Lot 2.1 §4.3 : nom saisi ou repli embelli -- title reste
                # présent ci-dessus, brut, pour le diagnostic de fusion.
                "display_title": s.display_name or beautify_mission_title(s.title),
                "mission_date": s.mission_date.isoformat() if s.mission_date else None,
                "acmi_present": s.acmi_present,
                "sim": s.sim,
                "n_uploads": item["n_uploads"],
                "n_flights": len(flights),
                "n_kills": item["n_kills"],
                "duration_s": s.duration_s,
                "doc_ratio": doc_ratio,
                "n_pilots": n_pilots,
                "squadrons": squadrons,
                "n_named": n_named,
                "n_anon": n_anon,
                "named_sample": named_sample,
                "campaign": _campaign_ref(s.campaign_id, campaign_name_by_id),
                # Lot « Mission ou training » : la nature de la session.
                "nature": s.nature,
                # Lot Fraîcheur v0.9939 (brief §7) : prédicat unique
                # (`revision.is_stale`), jamais réécrit en ligne ici.
                "stats_stale": revision.is_stale(s.stats_engine_rev),
                # Lot « Le rattachement des dépôts » : un fichier y est
                # rattaché sur l'en-tête d'une mission d'exemple de DCS.
                "a_verifier": s.id in a_verifier_ids,
            }
        )
    return {"sessions": out}


# Lot « Les liens de la soirée » (v1.0107, R796) : le jour d'une session et la soirée d'un jour.
# La fiche d'un évènement passé liste les sessions de son jour ; la session, de son côté, retrouve
# la soirée planifiée par le même jour (côté écran, `app.js`).
def jour_de_soiree(reference_time: datetime | None, mission_date: date | None) -> date | None:
    """Le jour d'une session : la date, à l'heure du fuseau de l'escadre (`fuseau_reference()`, Europe/Paris par défaut), de
    `reference_time` -- le départ réel lu dans le journal ou l'ACMI --, sinon `mission_date`, sinon
    `None`. Le serveur ne décide le jour d'une session que par cette fonction."""
    if reference_time is not None:
        if reference_time.tzinfo is None:
            reference_time = reference_time.replace(tzinfo=timezone.utc)
        return reference_time.astimezone(fuseau_reference()).date()
    return mission_date


@router.get("/soiree")
async def soiree_du_jour(
    jour: date = Query(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Les sessions d'un jour de Paris : `{"jour", "sessions": [{id, display_title, duration_s,
    n_flights}]}`. Une requête bornée (un `reference_time` entre la veille et le surlendemain de
    `jour` en UTC, ou un `reference_time` nul et `mission_date` égal à `jour`), puis le filtre par
    `jour_de_soiree`. `display_title` et `n_flights` se lisent comme dans `GET /sessions` (le nom
    affiché ou le titre embelli ; les vols significatifs). Triées par `reference_time` croissant,
    les nuls à la fin, puis `created_at`."""
    minuit = datetime(jour.year, jour.month, jour.day, tzinfo=timezone.utc)
    candidates = (
        await db.execute(
            select(DebriefSession).where(
                or_(
                    and_(
                        DebriefSession.reference_time >= minuit - timedelta(days=1),
                        DebriefSession.reference_time < minuit + timedelta(days=2),
                    ),
                    and_(DebriefSession.reference_time.is_(None), DebriefSession.mission_date == jour),
                )
            )
        )
    ).scalars().all()
    retenues = [s for s in candidates if jour_de_soiree(s.reference_time, s.mission_date) == jour]
    retenues.sort(
        key=lambda s: (
            s.reference_time is None,
            s.reference_time or datetime.min.replace(tzinfo=timezone.utc),
            s.created_at,
        )
    )
    n_vols: dict = {}
    if retenues:
        ids = [s.id for s in retenues]
        significatifs = await _significant_object_ids_par_session(db, ids)
        for vol in (
            await db.execute(select(DebriefFlight).where(DebriefFlight.session_id.in_(ids)))
        ).scalars().all():
            if vol.object_id and vol.object_id in significatifs.get(vol.session_id, set()):
                n_vols[vol.session_id] = n_vols.get(vol.session_id, 0) + 1
    return {
        "jour": jour.isoformat(),
        "sessions": [
            {
                "id": str(s.id),
                "display_title": _titre_affiche(s),
                "duration_s": s.duration_s,
                "n_flights": n_vols.get(s.id, 0),
            }
            for s in retenues
        ],
    }


async def _sessions_a_verifier(db: AsyncSession, session_id: uuid.UUID | None = None) -> set:
    """Lot « Le rattachement des dépôts » (R326) -- les sessions « À
    vérifier » : celles dont un fichier n'a été rattaché que par son titre
    (`rattachement = 'titre'`) ET dont l'en-tête désigne une mission d'exemple
    de DCS (`entete_exemple`). Une seule requête, pour toute la liste ou pour
    une session (`session_id`). La seule écriture de cette règle."""
    q = select(DebriefUpload.session_id).where(
        DebriefUpload.rattachement == rattachement.TITRE,
        DebriefUpload.entete_exemple.is_(True),
    ).distinct()
    if session_id is not None:
        q = q.where(DebriefUpload.session_id == session_id)
    return set((await db.execute(q)).scalars().all())


# --- Lot D2④ Volet A : enrich carte (n_named + named_sample) --------------
#
# Sérialisation pure à partir des `flights` déjà chargés en mémoire pour
# `list_sessions` ci-dessus -- aucune requête supplémentaire, aucun N+1.
# Réutilise `engine._norm_callsign` (jointure ACMI<->débrief par nom, v0.66)
# pour dédupliquer les respawns d'un même pilote sous une seule entité
# nommée -- même normalisation que le moteur, jamais réimplémentée ici.


def _short_callsign(raw: str) -> str:
    """Forme courte d'affichage : segment après le dernier `|` s'il existe,
    sinon le callsign entier (brief §Volet A/C.3 -- même règle des deux
    côtés). Tronqué à ~14 caractères (ellipse si coupé)."""
    part = raw.rsplit("|", 1)[-1].strip() if "|" in raw else raw.strip()
    if len(part) > 14:
        part = part[:14].rstrip() + "…"
    return part


def _named_pilots(
    flights: list[DebriefFlight],
    all_flights: list[DebriefFlight],
    noms: dict | None = None,
) -> tuple[int, list[str], int, int, int]:
    """`(n_named, named_sample, n_anon, n_deposited, n_known)` -- pilotes
    nommés distincts (axe A identité, cf. checkpoint §2.6), dédupliqués par
    callsign normalisé (respawns = même pilote). `named_sample` : au plus 4
    noms courts, tri alpha stable.

    Lot Jauge ② v0.9928 -- dénominateur pessimiste (brief §5) : `n_anon` est
    un compte de VOLS (pas de groupes) qui tombent dans la branche
    `continue` ci-dessous -- un vol anonyme peut cacher un pilote comme
    plusieurs, on n'en sait rien, donc chacun compte pour un. `n_deposited`
    est le nombre de callsigns normalisés distincts dont au moins un vol
    porte `pilot_deposited`.

    Lot « Filtrage des vols vides » v0.9934 (brief §4.3) -- exception unique
    du lot : `n_named`, `named_sample`, `n_anon` suivent le filtre et sont
    calculés sur `flights` (liste déjà filtrée par l'appelant) ; `n_deposited`
    NE le suit PAS et se calcule sur `all_flights` (liste complète, non
    filtrée) -- un membre qui a déposé son débrief reste un déposant même si
    son propre vol était vide, son dépôt a servi à documenter les vols des
    autres.

    Correctif Jauge v0.9935 -- `n_named`, `named_sample`, `n_anon`,
    `n_deposited` gardent EXACTEMENT leur définition ci-dessus, aucune n'a
    changé. `n_known` est une CINQUIÈME valeur, neuve : les pilotes nommés
    visibles réunis aux déposants, quel que soit le sort de leur vol
    (`len(set(entries) | deposited_norms)`). Un déposant est par définition
    un pilote dont on a connaissance -- il doit peser au dénominateur de la
    jauge, pas seulement au numérateur, sans quoi le filtrage des vols vides
    peut faire dépasser 100 % (un déposant dont le vol est filtré disparaît
    de `n_named` sans disparaître de `n_deposited`).

    Correctif « Le nom du membre » v1.0021 (R2) -- `noms` : `profile_id ->
    nom de l'annuaire`. Le nom d'un vol est son indicatif observé ; à défaut,
    le nom du membre rattaché. Ce nom remplace `pilot_callsign` dans le test,
    la normalisation et l'abrégé, dans les deux boucles. Les définitions des
    cinq valeurs ne changent pas."""
    noms = noms or {}
    entries: dict[str, str] = {}
    n_anon = 0
    for f in flights:
        nom = f.pilot_callsign or noms.get(f.pilote_profile_id)
        if not nom or f.identity_state not in ("nomme", "rattachable"):
            n_anon += 1
            continue
        norm = engine._norm_callsign(nom)
        if norm and norm not in entries:
            entries[norm] = _short_callsign(nom)
    n_named = len(entries)
    named_sample = sorted(entries.values(), key=lambda s: s.lower())[:4]

    deposited_norms: set[str] = set()
    for f in all_flights:
        nom = f.pilot_callsign or noms.get(f.pilote_profile_id)
        if not nom or f.identity_state not in ("nomme", "rattachable"):
            continue
        norm = engine._norm_callsign(nom)
        if norm and (f.stats or {}).get("pilot_deposited"):
            deposited_norms.add(norm)
    n_deposited = len(deposited_norms)
    n_known = len(set(entries) | deposited_norms)
    return n_named, named_sample, n_anon, n_deposited, n_known


# --- GET /sessions/{id} --------------------------------------------------------


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _session_or_404(db, session_id)

    uploads = (
        await db.execute(select(DebriefUpload).where(DebriefUpload.session_id == session_id))
    ).scalars().all()

    flights_all = (
        await db.execute(
            select(DebriefFlight)
            .where(DebriefFlight.session_id == session_id)
            .order_by(DebriefFlight.t_start.nulls_last())
        )
    ).scalars().all()
    # Lot « Filtrage des vols vides » v0.9934 (brief §4.2) : même prédicat,
    # même fonction que `list_sessions` ci-dessus -- tout ce qui dérive de
    # `flights` (bilan kills, sérialisation `flights` de la réponse) hérite
    # du filtre. `flights_all` reste disponible pour `_named_pilots`.
    significant_ids = await _significant_object_ids(db, session_id)
    flights = [f for f in flights_all if f.object_id and f.object_id in significant_ids]

    # Lot D — écussons : une seule requête groupée pour tous les
    # pilote_profile_id de la liste, jamais une requête par vol (même
    # discipline que squad_map plus haut dans ce fichier).
    crest_by_pid = await _crest_refs_bulk(
        db, {f.pilote_profile_id for f in flights if f.pilote_profile_id}
    )
    # Correctif « Le nom du membre » v1.0021 (R1/R2) : noms de l'annuaire, une
    # requête groupée sur `flights_all` (le comptage lit aussi les vols filtrés).
    noms_by_pid = await _noms_membres_bulk(
        db, {f.pilote_profile_id for f in flights_all if f.pilote_profile_id}
    )

    graveyard = (
        await db.execute(select(DebriefGraveyard).where(DebriefGraveyard.session_id == session_id))
    ).scalars().all()

    # --- Révision ④.1 chgt 3 : bilan par KILLS VALIDÉS (agrégat lecture) ----
    # Même calcul que l'écran vol, `_bilan_des_vols` (plus bas dans ce
    # fichier), sur les vols significatifs de la session : les tirs
    # fratricides sortent du bilan et sont comptés à part (`n_fratricides`,
    # lot « Le détecteur et l'hygiène »). Sérialisation pure à partir des
    # `stats["kills"]` déjà chargés -- aucune requête supplémentaire, pas de
    # N+1. `graveyard` reste dans la réponse (rétro-compat) mais n'est plus
    # la source du panneau "Bilan des destructions" côté front (chgt 3). Le
    # repli de camp lit TOUS les vols de la session (`flights_all`), comme
    # `get_flight` : un vol écarté comme vide reste une cible possible.
    camps = {str(f.object_id): f.coalition for f in flights_all if f.object_id is not None}
    bilan = _bilan_des_vols(flights, camps)

    # Couverture temporelle par upload -- approximation dérivée des events
    # fusionnés (cf. app/debrief/engine.py, pas de colonne t_min/t_max sur
    # debrief_upload dans le schéma contractuel D1).
    all_events = (
        await db.execute(select(DebriefEvent).where(DebriefEvent.session_id == session_id))
    ).scalars().all()
    coverage: dict[str, dict] = defaultdict(lambda: {"t_min": None, "t_max": None, "n_events": 0})
    for e in all_events:
        for upload_id in e.seen_in:
            cov = coverage[upload_id]
            cov["t_min"] = e.t if cov["t_min"] is None else min(cov["t_min"], e.t)
            cov["t_max"] = e.t if cov["t_max"] is None else max(cov["t_max"], e.t)
            cov["n_events"] += 1

    # Lot 2.3 §4.7 : une session -> au plus une campagne, une seule requête.
    campaign_ref: dict | None = None
    if session.campaign_id is not None:
        campaign = await db.get(Campaign, session.campaign_id)
        if campaign is not None:
            campaign_ref = {"id": str(campaign.id), "name": campaign.name}

    # Lot Jauge ② v0.9928 (brief §6.2) : le client ne recalcule plus rien --
    # même règle et même fonction que list_sessions ci-dessus.
    n_named, _named_sample, n_anon, n_deposited, n_known = _named_pilots(
        flights, flights_all, noms_by_pid
    )
    # Correctif Jauge v0.9935 : dénominateur = n_known + n_anon (pas
    # n_named + n_anon) -- même règle que list_sessions ci-dessus.
    _denom = n_known + n_anon
    doc_ratio = round(n_deposited / _denom, 3) if _denom else None

    # Lot « Le rattachement des dépôts » : le nom de qui a déplacé chaque
    # fichier, en une requête (même patron que `_noms_membres_bulk`).
    deplaceurs = await _noms_membres_bulk(
        db, {u.deplace_par_profile_id for u in uploads if u.deplace_par_profile_id}
    )

    return {
        "id": str(session.id),
        "title": session.title,
        # Lot 2.1 §4.3 : nom saisi ou repli embelli -- title reste présent
        # ci-dessus, brut, pour le diagnostic de fusion (P4).
        "display_title": session.display_name or beautify_mission_title(session.title),
        # Lot 2.3 §4.7 : défaut mesuré sur la v0.95, corrigé ici -- nom saisi
        # BRUT et nullable, distinct de `display_title` ci-dessus (repli
        # embelli inclus). Le panneau d'édition doit pré-remplir avec le nom
        # saisi seul, jamais avec le repli auto-généré.
        "display_name": session.display_name,
        "wing_note": session.wing_note,
        "campaign": campaign_ref,
        # Lot « Mission ou training » : la nature de la session.
        "nature": session.nature,
        # Lot 2.1 §4.6 : jamais décidé côté client seul.
        "can_edit": await can_edit_session(db, user),
        # Lot Fraîcheur v0.9939 (brief §7) : même prédicat unique que
        # list_sessions ci-dessus, jamais réécrit en ligne.
        "stats_stale": revision.is_stale(session.stats_engine_rev),
        # Lot « Le rattachement des dépôts » : la marque « À vérifier ».
        "a_verifier": bool(await _sessions_a_verifier(db, session_id)),
        # Correctif v0.9940 (Addendum 3 §2) : nombre de sessions périmées
        # dans TOUTE la base -- compté exactement comme
        # `engine.recompute_stale_sessions` les liste : on lit
        # `(id, stats_engine_rev)` pour chaque session et c'est
        # `revision.is_stale` qui tranche, jamais un prédicat réécrit en SQL
        # (ex. `stats_engine_rev IS DISTINCT FROM ...`) -- un seul endroit
        # où « périmé » se définit. Volontairement absent de
        # `list_sessions` : l'écran Missions n'a pas ce bouton.
        "stale_count": sum(
            1
            for _, rev in (
                await db.execute(select(DebriefSession.id, DebriefSession.stats_engine_rev))
            ).all()
            if revision.is_stale(rev)
        ),
        "mission_date": session.mission_date.isoformat() if session.mission_date else None,
        "reference_time": session.reference_time.isoformat() if session.reference_time else None,
        # Lot « Les heures de jour et de nuit » : l'heure du jour de la mission
        # à t = 0 (secondes), `None` sans `mission start` ; les journaux la lisent.
        "horloge_mission_s": session.horloge_mission_s,
        "duration_s": session.duration_s,
        "acmi_present": session.acmi_present,
        "sim": session.sim,
        # Lot Jauge ② v0.9928 (brief §6.2) : servis désormais, le client ne
        # recalcule plus rien (cf. §7.1).
        "n_named": n_named,
        "n_anon": n_anon,
        "doc_ratio": doc_ratio,
        "uploads": [
            {
                "id": str(u.id),
                "kind": u.kind,
                "filename": u.filename,
                "depositor_profile_id": str(u.depositor_profile_id)
                if u.depositor_profile_id
                else None,
                "uploaded_at": u.uploaded_at.isoformat(),
                "coverage": coverage.get(str(u.id), {"t_min": None, "t_max": None, "n_events": 0}),
                # Lot « Le rattachement des dépôts » : la provenance du fichier.
                "provenance": u.rattachement,
                "entete_titre": u.entete_titre,
                "entete_exemple": u.entete_exemple,
                "deplace_par": deplaceurs.get(u.deplace_par_profile_id),
            }
            for u in uploads
        ],
        "flights": [
            _flight_to_dict(
                f,
                crest=crest_by_pid.get(f.pilote_profile_id),
                nom=noms_by_pid.get(f.pilote_profile_id),
            )
            for f in flights
        ],
        "graveyard": [_graveyard_to_dict(g) for g in graveyard],
        "kills_by_category": bilan["kills_by_category"],
        "n_kills_validated": bilan["n_kills_validated"],
        "n_fratricides": bilan["n_fratricides"],
    }


# --- PATCH /sessions/{id} (Lot 2.1 §4.5) --------------------------------------
#
# Première mutation non destructive du module. Les deux champs sont
# optionnels et indépendants -- `model_fields_set` (pas la valeur) distingue
# l'absence de clé (ne rien faire) de `null` (effacer, repli sur l'embelli).
# Aucun effet de bord : aucun crochet, aucune notification, aucun événement
# SSE (les crochets du module Planification sont propres à la Planification).


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: uuid.UUID,
    body: SessionEditPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _session_or_404(db, session_id)

    if not await can_edit_session(db, user):
        raise HTTPException(status_code=403, detail="Modification réservée")

    fields = body.model_fields_set

    if "display_name" in fields:
        val = body.display_name
        if val is not None:
            val = val.strip()
            if not val:
                raise HTTPException(
                    status_code=422,
                    detail="Nom vide : envoyer null pour effacer",
                )
            if len(val) > 80:
                raise HTTPException(
                    status_code=422, detail="Nom de mission trop long (80 caractères max)"
                )
        session.display_name = val

    if "wing_note" in fields:
        val = body.wing_note
        if val is not None:
            val = val.strip()
            if not val:
                raise HTTPException(
                    status_code=422,
                    detail="Note vide : envoyer null pour effacer",
                )
            if len(val) > 2000:
                raise HTTPException(status_code=422, detail="Note trop longue (2000 caractères max)")
        session.wing_note = val

    # Lot 2.3 §4.6 : troisième champ, même mécanique absent/null que les
    # deux précédents -- `null` détache explicitement. Droit inchangé :
    # `session.edit`, la capacité existante (déjà vérifiée ci-dessus),
    # aucune notion de portée escadrille à modéliser (arbitrage du porteur
    # du 13 août -- les chefs d'escadrille sont dans le management).
    if "campaign_id" in fields:
        val = body.campaign_id
        if val is not None:
            campaign = await db.get(Campaign, val)
            if campaign is None:
                raise HTTPException(status_code=422, detail="campaign_id inconnu")
        session.campaign_id = val

    # Lot « Mission ou training » : quatrième champ, même mécanique absent/null
    # -- mais la nature n'a pas d'état « vide » : `null` est refusé. Valeurs
    # `mission` · `training` seulement (Pydantic, 422). Droit : `session.edit`.
    if "nature" in fields:
        if body.nature is None:
            raise HTTPException(status_code=422, detail="La nature ne peut pas être vide.")
        session.nature = body.nature

    await db.commit()

    campaign_ref: dict | None = None
    if session.campaign_id is not None:
        campaign = await db.get(Campaign, session.campaign_id)
        if campaign is not None:
            campaign_ref = {"id": str(campaign.id), "name": campaign.name}

    return {
        "id": str(session.id),
        "display_name": session.display_name,
        "wing_note": session.wing_note,
        "display_title": session.display_name or beautify_mission_title(session.title),
        "campaign": campaign_ref,
        "nature": session.nature,
    }


# --- GET /sessions/{id}/flights/{flight_id} ------------------------------------


def _bilan_des_vols(flights: list[DebriefFlight], camps: dict[str, str | None]) -> dict:
    """Bilan des destructions d'un ensemble de vols -- la session entière
    (`get_session`, révision ④.1 chgt 3) ou un seul vol (`get_flight`, lot
    « Le bilan du pilote ») : un seul calcul pour les deux écrans, donc un
    seul critère de fratricide (lot « Le détecteur et l'hygiène », R159
    étendu). Catégorisation côté serveur, le client n'a pas le référentiel
    objets.

    Un tir fratricide se reconnaît au CAMP DE SA CIBLE, porté sur l'abattage
    lui-même depuis le lot « Le passage moteur » (`target_coalition`, lu dans
    le debrief.log et validé par le moteur) : une cible au sol se reconnaît
    donc aussi. Mesuré en production le 27 septembre : le camp de la cible est
    présent et valide sur les 990 abattages des journaux déposés. Repli, pour
    un abattage qui ne le porte pas : le camp d'un autre VOL de la session
    (`camps`) -- le cimetière n'ayant pas d'identifiant d'objet, c'est la
    seule autre correspondance possible. Chaque abattage est comparé au camp
    du vol qui l'a tiré.

    À compte égal, les catégories gardent l'ordre de leur première
    apparition, vol après vol : sur une session sans fratricide, le bilan est
    exactement celui que `get_session` calculait avant ce lot.
    """
    kbc: dict[str, dict] = {}
    fratricides = 0
    for flight in flights:
        for k in (flight.stats or {}).get("kills", []):
            camp = k.get("target_coalition") or camps.get(str(k.get("target_object_id")))
            if camp is not None and camp == flight.coalition:
                fratricides += 1
                continue
            cat = referentiel.categorie_cible(k.get("target_unit_type"))
            row = kbc.setdefault(cat, {"category": cat, "display_name": cat, "count": 0})
            row["count"] += 1
    groupes = sorted(kbc.values(), key=lambda r: -r["count"])
    return {
        "kills_by_category": groupes,
        "n_kills_validated": sum(r["count"] for r in groupes),
        "n_fratricides": fratricides,
    }


@router.get("/sessions/{session_id}/flights/{flight_id}")
async def get_flight(
    session_id: uuid.UUID,
    flight_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _session_or_404(db, session_id)
    flight = await db.get(DebriefFlight, flight_id)
    if flight is None or flight.session_id != session_id:
        raise HTTPException(status_code=404, detail="Vol introuvable")
    crest = await _crest_ref(db, flight.pilote_profile_id)
    noms = await _noms_membres_bulk(db, {flight.pilote_profile_id})
    # Lot « L'efficacité par arme sur l'écran Vol » : la même lecture des vols de
    # la session sert les camps et les destructions du pilote (membre rattaché,
    # `pilote_profile_id`, et `stats` pour ses kills) -- aucune requête de plus.
    vols_session = (
        await db.execute(
            select(
                DebriefFlight.object_id,
                DebriefFlight.coalition,
                DebriefFlight.pilote_profile_id,
                DebriefFlight.stats,
            ).where(DebriefFlight.session_id == session_id)
        )
    ).all()
    camps = {str(oid): coa for oid, coa, _pid, _stats in vols_session if oid is not None}
    # Lot « L'efficacité par arme sur l'écran Vol » : les lignes de tir de CE
    # vol, quelle que soit sa fiabilité, rapportées aux destructions de son
    # pilote dans la session -- le calcul même du Dossier (R276).
    efficacite = _efficacite_par_arme(
        ((session_id, ligne_tir) for ligne_tir in (flight.stats or {}).get("bursts") or []),
        {session_id: _destructions_du_vol(flight, vols_session)},
    )
    return _flight_to_dict(
        flight, crest=crest, nom=noms.get(flight.pilote_profile_id)
    ) | _bilan_des_vols([flight], camps) | {
        "efficacite": efficacite,
        # Lot « Les heures de jour et de nuit » : le bouton de correction.
        "periode_modifiable": _peut_corriger_periode(
            flight.pilote_profile_id, user["id"], await can_edit_session(db, user)
        ),
    }


# --- PATCH /sessions/{id}/flights/{flight_id}/periode -----------------------


@router.patch("/sessions/{session_id}/flights/{flight_id}/periode")
async def corriger_periode_vol(
    session_id: uuid.UUID,
    flight_id: uuid.UUID,
    body: PeriodeVolPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les heures de jour et de nuit » (v1.0068) : corrige la période
    d'un vol -- son pilote, les chefs et les admins. Choisir la valeur que le
    moteur calcule efface la correction. Ni journal du Commandement, ni
    recalcul : `periode_corrigee` survit au recalcul."""
    await _session_or_404(db, session_id)
    flight = await db.get(DebriefFlight, flight_id)
    if flight is None or flight.session_id != session_id:
        raise HTTPException(status_code=404, detail="Vol introuvable")
    if not _peut_corriger_periode(
        flight.pilote_profile_id, user["id"], await can_edit_session(db, user)
    ):
        raise HTTPException(
            status_code=403,
            detail="Correction réservée au pilote du vol, aux chefs et aux admins",
        )
    flight.periode_corrigee = _correction_periode(flight.periode, body.periode)
    await db.commit()
    crest = await _crest_ref(db, flight.pilote_profile_id)
    noms = await _noms_membres_bulk(db, {flight.pilote_profile_id})
    return _flight_to_dict(
        flight, crest=crest, nom=noms.get(flight.pilote_profile_id)
    ) | {"periode_modifiable": True}


# --- GET /sessions/{id}/report/facts (Lot R1, brief §4) ---------------------
#
# Sert la fiche de faits assemblée par `report_facts.build_report_facts()` --
# module Python pur, aucun accès base au-delà de cette lecture des vols.
# Même garde que la modification de session (`can_edit_session`), pas une
# garde de lecture plus large : la fiche prépare la rédaction (Lot R2), qui
# est elle-même réservée à ceux qui peuvent éditer la session (brief §4).
# **Aucun consommateur dans l'interface pour ce lot, et c'est normal** --
# elle sert la recette hors ligne d'abord, la rédaction ensuite.


async def _build_report_facts_for_session(db: AsyncSession, session: DebriefSession) -> dict:
    """Fiche de faits (Lot R1) pour `session` -- factorisée ici (Lot R2) :
    servie telle quelle par `GET .../report/facts` ci-dessous (recette hors
    ligne) ET consommée par les deux routes `.../report` (rédaction et
    lecture, brief §4). Un seul endroit construit la fiche : aucun risque
    qu'elle diverge entre les deux usages."""
    flights_all = (
        await db.execute(
            select(DebriefFlight)
            .where(DebriefFlight.session_id == session.id)
            .order_by(DebriefFlight.t_start.nulls_last())
        )
    ).scalars().all()
    significant_ids = await _significant_object_ids(db, session.id)
    flights = [f for f in flights_all if f.object_id and f.object_id in significant_ids]
    # Correctif « Le nom du membre » v1.0021 (R1/R3) : la fiche lit `pilote_nom`.
    noms_by_pid = await _noms_membres_bulk(
        db, {f.pilote_profile_id for f in flights if f.pilote_profile_id}
    )
    flight_dicts = [
        _flight_to_dict(f, nom=noms_by_pid.get(f.pilote_profile_id)) for f in flights
    ]
    mission = {
        "id": str(session.id),
        "title": session.title,
        "display_title": session.display_name or beautify_mission_title(session.title),
        # Lot R3 §3⑥ -- source du calcul de "heure" (report_facts._fmt_heure) :
        # ISO avec fuseau, même sérialisation que `_session_to_dict` (ligne
        # ~634). `None` si la session n'a pas de reference_time -- report_facts
        # gère déjà ce cas (heure vaut alors None sur chaque fait, jamais une
        # heure inventée).
        "reference_time": session.reference_time.isoformat() if session.reference_time else None,
        # R119 -- sans cette clé, mission.get("wing_note") vaut toujours None
        # et la note à l'escadre n'atteint jamais la fiche (défaut silencieux).
        "wing_note": session.wing_note,
    }
    # Lot « La plume » §3.1 -- les libellés du Centre nomment types et armes
    # dans la fiche : la même lecture que `GET /api/referentiels/libelles`.
    libelles = await referentiel.lire_libelles(db)
    return report_facts.build_report_facts(flight_dicts, mission, libelles)


@router.get("/sessions/{session_id}/report/facts")
async def get_report_facts(
    session_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _session_or_404(db, session_id)

    if not await can_edit_session(db, user):
        raise HTTPException(status_code=403, detail="Réservé aux éditeurs de la session")

    return await _build_report_facts_for_session(db, session)


# --- POST/GET /sessions/{id}/report (Lot R2, brief §4) ----------------------
#
# Distinctes de GET .../report/facts ci-dessus (Lot R1, fiche BRUTE, recette
# hors ligne) : celles-ci servent/produisent le RAPPORT RÉDIGÉ -- le récit
# du modèle de langage, figé en base (R78/R81). POST rédige ou réécrit,
# réservé à ceux qui peuvent éditer la session (R79) ; GET lit, ouvert à
# tout membre authentifié (R79 : "la lecture est ouverte à tous" -- au sens
# de la garde `can_edit_session`, pas au sens non authentifié).

# Péremption d'une rédaction réputée morte.
#
# Lot FR source unique §2④ : 10 -> 16. La chaîne est désormais SÉQUENTIELLE
# à deux temps (geste ③) -- la borne dure ne protège plus un seul appel,
# mais toute la chaîne :
#   français  -- pas de reprise sur dépassement, une reprise sur panne de
#                transport : 2 × 300 + _RETRY_DELAY_S (1,5) =    601,5 s
#   traduction -- reprise permise :        2 ×  60 + _RETRY_DELAY_S (1,5) =    121,5 s
#   chaîne complète                                                    =    723,0 s
#                                                                   = 12,05 min
# 16 minutes conservent les ~4 minutes de marge arbitrées à l'origine
# (cadrage §4③). `_TIMEOUT_S` / `_TIMEOUT_TRADUCTION_S` (app/llm.py) ne
# bougent jamais sans relire cette valeur.
#
# Lot « La plume » §5 : 16 -> 26, `_TIMEOUT_S` passant de 300 à 600 s :
#   français  -- 2 × 600 + _RETRY_DELAY_S (1,5) =                       1 201,5 s
#   traduction -- 2 ×  60 + _RETRY_DELAY_S (1,5) =                         121,5 s
#   chaîne complète                                                    = 1 323,0 s
#                                                                   = 22,05 min
# 26 minutes gardent la marge d'environ 4 minutes.
REDACTION_PEREMPTION_MIN = 26


async def _redaction_en_cours_et_par(
    db: AsyncSession, session_id: uuid.UUID
) -> tuple[bool, str | None]:
    """Lot R6 §2① -- NON NÉGOCIABLE : l'état « en cours » est porté par
    CETTE lecture, jamais par le canal temps réel (qui n'a aucune mémoire,
    il ne fait que réveiller ceux déjà présents). Péremption calculée ICI,
    à la lecture (brief §3④) : rien n'est purgé, rien n'est à nettoyer, un
    redémarrage ne peut pas geler une session.

    Lot « Le passage moteur » : « maintenant » se lit sur l'horloge de la
    BASE, comme à la pose du verrou (`func.now()`, `generate_report`) -- un
    seul temps pour un seul prédicat, jamais l'horloge du processus d'un
    côté et celle de la base de l'autre."""
    run = await db.get(DebriefReportRun, session_id)
    if run is None:
        return False, None
    maintenant = await db.scalar(select(func.now()))
    if run.started_at < maintenant - timedelta(minutes=REDACTION_PEREMPTION_MIN):
        return False, None
    nom = None
    if run.lance_par_profile_id is not None:
        profil = await db.get(Profile, run.lance_par_profile_id)
        if profil is not None:
            nom = profil.global_name or profil.username
    return True, nom


def _report_to_dict(
    report: DebriefReport | None,
    current_sha: str,
    redaction_en_cours: bool,
    redaction_par: str | None,
) -> dict:
    """Forme commune GET/POST. `a_corriger` (R80) n'est JAMAIS stocké --
    recalculé à la volée par comparaison à `current_sha`, même discipline
    que `revision.is_stale` (jamais un prédicat dupliqué ailleurs).

    Lot R6 §3④ -- `redaction_en_cours`/`redaction_par` dans LES DEUX
    branches (rapport présent et absent) : une clé manquante et une clé
    fausse ne se distinguent pas côté client. Fonction pure : l'appelant
    calcule l'état (`_redaction_en_cours_et_par`) et le passe ici plutôt
    que d'aller le chercher à l'intérieur."""
    if report is None:
        return {
            "exists": False,
            "texte_fr": None,
            "texte_en": None,
            "report_facts_sha": None,
            "a_corriger": False,
            "redige_at": None,
            "auteur_profile_id": None,
            "redaction_en_cours": redaction_en_cours,
            "redaction_par": redaction_par,
        }
    return {
        "exists": True,
        "texte_fr": report.texte_fr,
        "texte_en": report.texte_en,
        "report_facts_sha": report.report_facts_sha,
        "a_corriger": report.report_facts_sha != current_sha,
        "redige_at": report.redige_at.isoformat() if report.redige_at else None,
        "auteur_profile_id": str(report.auteur_profile_id) if report.auteur_profile_id else None,
        "redaction_en_cours": redaction_en_cours,
        "redaction_par": redaction_par,
    }


@router.get("/sessions/{session_id}/report")
async def get_report(
    session_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _session_or_404(db, session_id)
    fiche = await _build_report_facts_for_session(db, session)
    report = await db.get(DebriefReport, session_id)
    redaction_en_cours, redaction_par = await _redaction_en_cours_et_par(db, session_id)
    return _report_to_dict(report, fiche["report_facts_sha"], redaction_en_cours, redaction_par)


@router.post("/sessions/{session_id}/report")
async def generate_report(
    session_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await _session_or_404(db, session_id)

    if not await can_edit_session(db, user):
        raise HTTPException(status_code=403, detail="Réservé aux éditeurs de la session")

    # Piège #2 (brief §7, le plus grave) -- ordre impératif : recalcul
    # avant rédaction, JAMAIS l'inverse. La route REFUSE, elle ne
    # recalcule pas d'elle-même (brief §4) -- sinon le rapport se fige sur
    # des faits déjà faux et son empreinte le déclare frais : le mécanisme
    # entier de R81/R80 s'effondre.
    if revision.is_stale(session.stats_engine_rev):
        raise HTTPException(
            status_code=409,
            detail="Statistiques périmées : recalculez la session avant de rédiger le rapport.",
        )

    # Plafond PAR SESSION (brief §3) -- vérifié ICI, jamais dans app/llm.py
    # (qui ne reçoit pas session_id dans sa signature, cf. sa docstring).
    # Compte les appels réellement tentés pour CETTE session (fr et en
    # comptent chacun pour un, pas le clic) -- même liste de verdicts que
    # le plafond mensuel de la porte (app.llm.VERDICTS_TENTES), un seul
    # vocabulaire de verdicts dans toute l'application.
    #
    # Lot R5 §3 (arbitré par le porteur) -- FENÊTRE D'UNE HEURE GLISSANTE sur
    # `called_at`, ajoutée à la requête : un plafond cumulé depuis la
    # création de la session n'arrête pas une boucle, il en laisse passer
    # dix puis gèle la session à vie (brief §3). La fenêtre se calcule à
    # la LECTURE -- elle ne purge rien, n'efface aucune ligne du journal
    # (l'historique complet reste la seule source du coût réel). Le
    # périmètre des verdicts comptés (`llm.VERDICTS_TENTES`) ne change pas.
    borne_glissante = datetime.now(timezone.utc) - timedelta(hours=1)
    n_session = await db.scalar(
        select(func.count()).select_from(LlmCallLog).where(
            LlmCallLog.session_id == session_id,
            LlmCallLog.verdict.in_(llm.VERDICTS_TENTES),
            LlmCallLog.called_at >= borne_glissante,
        )
    )
    if (n_session or 0) >= llm.SESSION_CALL_CAP:
        # Refus loggé ICI (brief §3 : "une ligne par appel tenté, y
        # compris... les refus de plafond") -- app/llm.py n'est jamais
        # appelé dans cette branche, donc n'écrit rien lui-même.
        db.add(LlmCallLog(
            session_id=session_id, langue=None, model=None,
            tokens_in=None, tokens_out=None, duration_ms=None,
            verdict="refus_plafond_session",
        ))
        await db.commit()
        raise HTTPException(
            status_code=429,
            detail=(
                "Plafond de générations atteint pour cette session "
                "(temporaire : il se libère au fil de l'heure écoulée, "
                "réessayez plus tard)."
            ),
        )

    try:
        auteur_id: int | None = int(user["id"])
    except (KeyError, TypeError, ValueError):
        auteur_id = None

    # Lot R6 §2② -- pose ATOMIQUE de l'état "en cours", après les deux
    # plafonds ci-dessus (qui ne bougent pas) et avant tout appel au
    # modèle. Étend le patron upsert de la maison (app/events.py) : ce
    # patron n'a besoin ni de `where=` ni de `RETURNING` -- le nôtre des
    # deux. Sans le `where`, une rédaction en cours serait écrasée par la
    # suivante ; sans le `RETURNING`, on ne saurait pas si on a gagné la
    # course. `session_id` en clé primaire (migration 0024) rend cette
    # écriture atomique par contrainte, pas par vigilance : deux clics
    # concurrents ne peuvent pas tous les deux obtenir une ligne fraîche.
    pose_stmt = pg_insert(DebriefReportRun).values(
        session_id=session_id,
        lance_par_profile_id=auteur_id,
    )
    pose_stmt = pose_stmt.on_conflict_do_update(
        index_elements=[DebriefReportRun.session_id],
        set_={
            "started_at": func.now(),
            "lance_par_profile_id": pose_stmt.excluded.lance_par_profile_id,
        },
        where=DebriefReportRun.started_at
        < func.now() - text(f"interval '{REDACTION_PEREMPTION_MIN} minutes'"),
    ).returning(DebriefReportRun.session_id)
    pose = await db.execute(pose_stmt)
    await db.commit()
    if pose.first() is None:
        # Aucune ligne rendue => une rédaction est déjà en vol et n'est pas
        # périmée. Rien n'a été tenté (brief §2②) : aucune ligne au
        # journal LLM, VERDICTS_TENTES ne bouge pas. Message i18n §6
        # (`report_busy_conflict`) -- le client n'affiche pas ce texte
        # comme une erreur : il rafraîchit la lecture, qui porte l'état.
        raise HTTPException(
            status_code=409,
            detail="Une rédaction est déjà en cours sur cette session.",
        )

    # Ligne rendue => publication (réveille tout de suite ceux déjà sur la
    # modale, le canal n'a aucune mémoire) puis tâche de fond, puis 202
    # immédiat -- la rédaction elle-même (fiche, gather fr/en, repli,
    # écriture) est intégralement déplacée dans `_redact_report_task`
    # (brief §3③), qui reprend le corps ci-dessous sans en changer une
    # règle, avec sa propre session (fermée quand elle s'exécute) et son
    # `finally` de nettoyage.
    publish_invalidate("report", str(session_id))
    taches.lancer(_redact_report_task(session_id, auteur_id))

    # Le corps du 202 porte la même forme que `_report_to_dict` sur l'état
    # ACTUEL du rapport : l'ancien rapport, s'il existe, reste affiché tel
    # quel tant que la nouvelle rédaction n'a pas abouti.
    fiche = await _build_report_facts_for_session(db, session)
    report = await db.get(DebriefReport, session_id)
    redaction_en_cours, redaction_par = await _redaction_en_cours_et_par(db, session_id)
    return _report_to_dict(report, fiche["report_facts_sha"], redaction_en_cours, redaction_par)


async def _redact_report_task(session_id: uuid.UUID, auteur_id: int | None) -> None:
    """Tâche de fond (Lot R6 §3③) -- réécrite au Lot « Le français source
    unique » (brief §2③) : la chaîne devient SÉQUENTIELLE À DEUX TEMPS.
    `asyncio.gather` sur les deux langues a disparu (R120) : le français
    est la source, l'anglais en est désormais la traduction -- le second
    appel dépend du premier, il ne peut plus partir en parallèle avec lui.

    Temps 1 -- rédaction française. Échec => journaliser et sortir : AUCUN
    rapport écrit (la règle de repli du Lot R2 ne disparaît pas, elle
    cesse seulement de porter sur deux langues à la fois).

    Temps 2 -- le français est écrit et COMMIT SEUL, `texte_en` remis à
    `None` explicitement (R123, le piège de ce lot : sans cette remise à
    zéro, la traduction d'une génération précédente resterait affichée
    sous un texte français neuf). L'invalidation est publiée ICI, après ce
    commit -- c'est ce qui rend R122 réel ("le français s'affiche dès
    qu'il est prêt").

    Temps 3 -- traduction, en tâche de fond, ne bloque plus rien côté
    lecteur. Échec => journaliser, ne rien écrire de plus : le français
    déjà publié reste affiché seul (repli d'affichage, geste ⑤).

    Deux différences avec l'ancienne route synchrone, inchangées par ce
    lot : une session neuve (`AsyncSessionLocal`, jamais celle de la
    requête -- fermée quand cette tâche s'exécute), et ce `try/finally`
    dont le `finally` supprime la ligne `debrief_report_run` PUIS publie
    l'invalidation finale -- après le commit, jamais avant. Le verrou
    (`debrief_report_run`) reste tenu sur TOUTE la chaîne, y compris
    pendant la traduction : une régénération lancée entre les deux temps
    ne doit pas faire atterrir une vieille traduction sur un texte neuf.
    Ce `finally` fait déjà exactement ce qu'il faut -- il n'est pas touché.

    Aucune exception ne remonte hors de la tâche : `logger.exception` et
    on sort. Une tâche de fond qui lève n'a personne pour l'entendre."""
    try:
        async with AsyncSessionLocal() as db:
            try:
                session = await db.get(DebriefSession, session_id)
                if session is None:
                    return

                fiche = await _build_report_facts_for_session(db, session)

                # --- Temps 1 : rédaction française (R120/R122) ----------
                texte_fr, journal_fr = await llm.rediger(fiche, "fr")
                if texte_fr is None:
                    logger.warning(
                        "Debrief : rédaction française échouée pour la "
                        "session %s (fr=%s) -- aucun rapport écrit.",
                        session_id, journal_fr["verdict"],
                    )
                    return

                # --- Temps 2 : publication du français SEUL (R122/R123) -
                # `texte_en = None` n'est pas une précaution, c'est le lot
                # (brief §2③) : sans cette remise à zéro, la traduction
                # d'une génération PRÉCÉDENTE resterait affichée sous ce
                # texte français neuf.
                report = await db.get(DebriefReport, session_id)
                if report is None:
                    report = DebriefReport(session_id=session_id)
                    db.add(report)
                report.texte_fr = texte_fr
                report.texte_en = None
                report.report_facts_sha = fiche["report_facts_sha"]
                report.auteur_profile_id = auteur_id
                await db.commit()
                # Publiée APRÈS le commit, jamais avant -- même discipline
                # que le `finally` ci-dessous, pour la même raison.
                publish_invalidate("report", str(session_id))

                # --- Temps 3 : traduction (R120/§3) ----------------------
                # Le verrou (`debrief_report_run`) n'est PAS libéré ici --
                # il reste tenu jusqu'au `finally`, sur toute la chaîne.
                texte_en, journal_en = await llm.traduire(texte_fr, fiche)
                if texte_en is None:
                    logger.warning(
                        "Debrief : traduction échouée pour la session %s "
                        "(en=%s) -- le français reste seul affiché.",
                        session_id, journal_en["verdict"],
                    )
                    return
                report.texte_en = texte_en
                await db.commit()
            finally:
                run = await db.get(DebriefReportRun, session_id)
                if run is not None:
                    await db.delete(run)
                    await db.commit()
                publish_invalidate("report", str(session_id))
    except Exception:
        logger.exception(
            "Debrief : erreur non bloquante dans la tâche de rédaction "
            "(session_id=%s)",
            session_id,
        )


# --- GET /members (admin only, neuf v0.9917) ---------------------------------


@router.get("/members")
async def list_debrief_members(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Annuaire pour le sélecteur du bordereau d'identification (brief §2/
    §6) -- identifiant, nom d'affichage, escadrille, GROUPÉ par escadrille
    côté front avec un groupe « Sans escadrille » pour les Free Agents.

    Route PROPRE : ne dépend PAS des règles d'accès du Centre de
    Commandement (brief §2, `GET /api/command/members` existe mais n'est
    pas appelée depuis le Débriefing -- ce module ne doit pas dépendre
    d'un autre module verrouillé séparément). Garde admin stricte, même
    patron que les autres routes d'écriture de ce fichier -- l'annuaire
    n'est utile qu'au geste de désignation, réservé aux admins.

    Même requête que `command/api.py::list_command_members` (LEFT JOIN
    appartenance OUVERTE puis Squadron, tri `global_name, username`) --
    dupliquée ici plutôt qu'importée : les deux modules restent
    indépendants l'un de l'autre (cf. ci-dessus), une dépendance croisée
    aurait recréé exactement le couplage que cette route évite."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux admins")

    result = await db.execute(
        select(Profile, Squadron.designation)
        .select_from(Profile)
        .outerjoin(
            SquadronMembership,
            and_(
                SquadronMembership.profile_id == Profile.id,
                SquadronMembership.ended_at.is_(None),
            ),
        )
        .outerjoin(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .order_by(Profile.global_name, Profile.username)
    )
    rows = result.all()
    return {
        "members": [
            {
                # str() impératif : snowflake Discord (BigInteger) au-delà
                # de Number.MAX_SAFE_INTEGER -- idiome repris de
                # `command/api.py::list_command_members`.
                "id": str(p.id),
                "name": p.global_name or p.username,
                "squadron": designation,
            }
            for p, designation in rows
        ]
    }


_ORDRE_ROLE = {"leader": 0, "deputy": 1, "member": 2}


def _escadrille_au_jour(appartenances: dict, profile_id, jour):
    """Lot « Les écrans E et F » (R188) -- l'escadrille d'un pilote le jour
    d'un vol : celle de l'appartenance qui couvre ce jour, la plus récente si
    deux se recouvrent ; `None` pour un Free Agent. `appartenances` : par
    profil, la liste de ses appartenances, closes comprises. Pure."""
    retenue = None
    for m in appartenances.get(profile_id, ()):
        if m.started_at.date() <= jour and (m.ended_at is None or m.ended_at.date() >= jour):
            if retenue is None or m.started_at > retenue.started_at:
                retenue = m
    return retenue.squadron_id if retenue is not None else None


def _bilan_additionne(par_session) -> dict:
    """Lot « L'écran B » -- le bilan de plusieurs sessions : `_bilan_des_vols`
    appliqué à chacune -- ses replis de camp sont propres à une session --
    puis additionné. Un seul calcul pour tous les bilans (R167) : celui de
    l'écran E, par escadrille, et celui de l'écran B, sur trente jours.
    `par_session` : des couples (vols de la session, camps de la session),
    du plus ancien au plus récent. À compte égal, une catégorie garde son
    rang de première apparition. Pure : testée hors ligne
    (tests/test_accueil.py)."""
    comptes: dict[str, int] = {}
    fratricides = 0
    for vols, camps in par_session:
        bilan = _bilan_des_vols(vols, camps)
        for ligne in bilan["kills_by_category"]:
            comptes[ligne["category"]] = comptes.get(ligne["category"], 0) + ligne["count"]
        fratricides += bilan["n_fratricides"]
    return {
        "kills_by_category": [
            {"category": c, "display_name": c, "count": n}
            for c, n in sorted(comptes.items(), key=lambda kv: -kv[1])
        ],
        "n_kills_validated": sum(comptes.values()),
        "n_fratricides": fratricides,
    }


def _unites_au_jour_du_vol(vols, appartenances: dict, camps: dict) -> dict:
    """Lot « Les écrans E et F » (R188) -- l'activité et le bilan de chaque
    escadrille, pour l'écran E. `vols` : des couples (vol, jour de la
    mission), du plus ancien au plus récent ; `camps` : par session, le camp
    de chacun de ses vols. Un vol identifié compte pour l'escadrille de son
    pilote au jour du vol ; un Free Agent ne compte pour aucune.

    Le bilan est `_bilan_additionne` -- `_bilan_des_vols` appliqué session
    par session, puis additionné : un seul calcul pour tous les bilans
    (R167), le même que celui de l'écran B.

    Lot « Les heures comptées par mission » (v1.0069, le porteur, 4 novembre) :
    les heures comptent le temps où au moins un pilote est en l'air, mission
    par mission (`_heures_de_mission`). Pure : testée hors ligne
    (tests/test_ecrans_ef.py)."""
    par_unite: dict = defaultdict(lambda: defaultdict(list))
    for vol, jour in vols:
        if vol.pilote_profile_id is None or jour is None:
            continue
        sq = _escadrille_au_jour(appartenances, vol.pilote_profile_id, jour)
        if sq is not None:
            par_unite[sq][vol.session_id].append(vol)
    unites: dict = {}
    for sq, sessions in par_unite.items():
        tous = [v for liste in sessions.values() for v in liste]
        # Lot « Les heures comptées par mission » : la réunion des vols de chaque session.
        secondes, nuit = _heures_de_mission(tous)
        unites[sq] = {
            "activite": {
                "missions": len(sessions),
                "heures": round(secondes / 3600, 1),
                "heures_jour": round((secondes - nuit) / 3600, 1),
                "heures_nuit": round(nuit / 3600, 1),
                "sorties": len(tous),
                "pilotes": len({v.pilote_profile_id for v in tous}),
            },
            "bilan": _bilan_additionne(
                (liste, camps.get(session_id, {})) for session_id, liste in sessions.items()
            ),
        }
    return unites


_UNITE_VIDE = {
    "activite": {
        "missions": 0, "heures": 0.0, "heures_jour": 0.0, "heures_nuit": 0.0,
        "sorties": 0, "pilotes": 0,
    },
    "bilan": {"kills_by_category": [], "n_kills_validated": 0, "n_fratricides": 0},
}


def _escadre_payload(wing, squadrons, rows, sims: list[str], activite: dict, unites: dict | None = None) -> dict:
    """Lot « L'écran D » (R177) -- l'escadre sur une page, assemblée sans
    requête. `rows` porte les profils non archivés (lot « L'appel »), chacun
    avec l'id d'escadrille et le rôle de son appartenance OUVERTE, ou `None` s'il n'en a pas. Les
    membres d'une escadrille active s'y rangent chef, adjoint, puis pilotes
    par nom ; tout autre profil est un Free Agent -- l'endormissement ferme
    déjà les appartenances d'une escadrille en sommeil. Les escadrilles
    actives d'abord, puis en sommeil, chacune par id. Pure : testée hors
    ligne (tests/test_ecran_escadre.py).

    Lot « Les écrans E et F » : chaque escadrille porte aussi son callsign,
    son nom complet (R189), son activité et son bilan (`unites`, calculés
    par `_unites_au_jour_du_vol`) -- l'écran E se lit dans cette charge, sans
    route propre. Une escadrille sans vol porte une activité nulle."""
    actives = {sq.id for sq in squadrons if sq.status == "actif"}
    par_escadrille: dict[int, list[dict]] = defaultdict(list)
    free: list[dict] = []
    for profil, squadron_id, role in rows:
        membre = {
            # str() impératif : snowflake Discord au-delà de Number.MAX_SAFE_INTEGER.
            "id": str(profil.id),
            "name": profil.global_name or profil.username,
            "avatar_hash": profil.avatar_hash,
            # Lot « Les cartes DCS de chaque pilote » : None = non déclaré.
            "cartes_dcs": profil.cartes_dcs,
        }
        if squadron_id in actives:
            par_escadrille[squadron_id].append(dict(membre, role=role or "member"))
        else:
            free.append(membre)

    def rang(m: dict) -> tuple:
        return (_ORDRE_ROLE.get(m.get("role"), 2), (m["name"] or "").casefold())

    return {
        "wing": {"designation": wing.designation if wing is not None else None},
        "sims": sims,
        "squadrons": [
            {
                "id": sq.id,
                "designation": sq.designation,
                "status": sq.status,
                "aircraft": sq.aircraft or [],
                "crest_sha": sq.crest_sha,
                "callsign": sq.callsign,
                "full_name": sq.full_name,
                "members": sorted(par_escadrille.get(sq.id, []), key=rang),
                **(unites or {}).get(sq.id, _UNITE_VIDE),
            }
            for sq in sorted(squadrons, key=lambda s: (s.status != "actif", s.id))
        ],
        "free_agents": sorted(free, key=rang),
        "activity": activite,
    }


@router.get("/escadre")
async def get_escadre(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « L'écran D » (R177) -- l'onglet « Escadrilles » du Débrief :
    l'escadre, son ordre de bataille, son activité et son organigramme, en
    une lecture. Ouverte à tout membre connecté, comme le reste du Débrief.

    Route PROPRE : ne dépend PAS du Centre de Commandement (cf.
    `list_debrief_members`) -- même requête d'appartenance ouverte, dupliquée
    plutôt qu'importée. Les appareils de chaque escadrille sont ceux qu'elle
    déclare au Centre (`squadron.aircraft`, lot « L'appareil de
    l'escadrille »).

    Activité, arbitrée le 29 septembre : les heures des vols identifiés
    (arrondies), les missions déposées, les campagnes ; les simulateurs
    présents en base. Les « pilotes actifs » ne se comptent pas ici : ce sont
    les pilotes de l'organigramme, que le front compte sur la même liste
    (arbitrage du porteur).

    Lot « L'appel » (R184) : un profil archivé sort de l'organigramme --
    donc de l'effectif ; ses vols restent dans l'activité de l'escadre.

    Lot « Les écrans E et F » : la même lecture porte, par escadrille,
    l'activité et le bilan de l'écran E -- un vol compte pour l'escadrille
    de son pilote au jour du vol (R188), toutes les appartenances lues,
    closes comprises.

    Lot « Correctifs de B » : un vol, ici comme à l'écran de session, est un
    vol RÉEL (`_est_significatif`) -- les heures de l'escadre et l'activité
    de E ne comptent plus les vols vides. Les camps de repli, eux, lisent
    tous les vols de la session, comme l'écran de session.

    Lot « Les heures comptées par mission » (v1.0069, le porteur, 4 novembre) :
    `hours` compte, mission par mission, le temps où au moins un pilote est
    en l'air (`_heures_de_mission`)."""
    wing = (await db.execute(select(Wing).order_by(Wing.id).limit(1))).scalar_one_or_none()
    squadrons = (await db.execute(select(Squadron))).scalars().all()
    rows = (
        await db.execute(
            select(Profile, SquadronMembership.squadron_id, SquadronMembership.role)
            .select_from(Profile)
            .outerjoin(
                SquadronMembership,
                and_(
                    SquadronMembership.profile_id == Profile.id,
                    SquadronMembership.ended_at.is_(None),
                ),
            )
            .where(Profile.archived_at.is_(None))
        )
    ).all()
    missions = (await db.execute(select(func.count()).select_from(DebriefSession))).scalar() or 0
    campagnes = (await db.execute(select(func.count()).select_from(Campaign))).scalar() or 0
    sims = sorted(s for (s,) in (await db.execute(select(DebriefSession.sim).distinct())).all() if s)
    appartenances: dict = defaultdict(list)
    for m in (await db.execute(select(SquadronMembership))).scalars().all():
        appartenances[m.profile_id].append(m)
    vols = (
        await db.execute(
            select(DebriefFlight, DebriefSession.mission_date)
            .join(DebriefSession, DebriefSession.id == DebriefFlight.session_id)
            .order_by(DebriefSession.mission_date, DebriefSession.id)
        )
    ).all()
    camps: dict = defaultdict(dict)
    for vol, _jour in vols:
        if vol.object_id is not None:
            camps[vol.session_id][str(vol.object_id)] = vol.coalition
    significatifs = await _significant_object_ids_par_session(db)
    reels = [(vol, jour) for vol, jour in vols if _est_significatif(vol, significatifs)]
    # Lot « Les heures comptées par mission » : la réunion des vols de chaque session.
    secondes, _nuit = _heures_de_mission([vol for vol, _jour in reels if vol.pilote_profile_id is not None])
    return _escadre_payload(
        wing,
        squadrons,
        rows,
        sims,
        {
            "hours": round(float(secondes) / 3600),
            "missions": int(missions),
            "campaigns": int(campagnes),
        },
        _unites_au_jour_du_vol(reels, appartenances, camps),
    )


def _synthese_membre(vols, campagnes: dict) -> dict:
    """Lot « Les écrans E et F » -- la synthèse d'un membre (écran F),
    assemblée sans requête. `vols` : des couples (vol, session) de ce pilote ;
    `campagnes` : par id, (rang, nom), le rang étant l'ordre de création de
    TOUTES les campagnes -- il donne la teinte de la barrette, la même pour
    chaque pilote. La participation, jamais l'efficacité. Pure : testée hors
    ligne (tests/test_ecrans_ef.py)."""
    sessions: dict = {}
    par_type: dict = {}
    secondes = 0.0
    secondes_nuit = 0.0  # Lot « Les heures de jour et de nuit » : un vol sans période compte de jour.
    for vol, s in vols:
        duree = max((vol.t_end or 0) - (vol.t_start or 0), 0)
        secondes += duree
        if _periode_effective(vol) == "nuit":
            secondes_nuit += duree
        sessions[s.id] = s
        if vol.aircraft_type:
            t = par_type.setdefault(vol.aircraft_type, {"sessions": set(), "secondes": 0.0})
            t["sessions"].add(s.id)
            t["secondes"] += duree
    appareils = sorted(
        (
            {"type": nom, "missions": len(t["sessions"]), "heures": round(t["secondes"] / 3600, 1)}
            for nom, t in par_type.items()
        ),
        key=lambda a: (-a["missions"], a["type"]),
    )
    par_campagne: dict = {}
    for s in sessions.values():
        if s.campaign_id in campagnes:
            rang, nom = campagnes[s.campaign_id]
            c = par_campagne.setdefault(s.campaign_id, {"id": str(s.campaign_id), "name": nom, "rang": rang, "missions": 0})
            c["missions"] += 1
    dates = [s.mission_date for s in sessions.values() if s.mission_date]
    recentes = sorted(
        sessions.values(),
        key=lambda s: (s.mission_date or datetime.min.date(), str(s.id)),
        reverse=True,
    )[:4]
    return {
        "participation": {
            "missions": len(sessions),
            "heures": round(secondes / 3600, 1),
            "heures_jour": round((secondes - secondes_nuit) / 3600, 1),
            "heures_nuit": round(secondes_nuit / 3600, 1),
            "appareils": len(par_type),
            "depuis": min(dates).isoformat() if dates else None,
        },
        "appareils": appareils,
        "campagnes": sorted(par_campagne.values(), key=lambda c: c["rang"]),
        "missions": [
            {
                "session_id": str(s.id),
                "date": s.mission_date.isoformat() if s.mission_date else None,
                "titre": s.display_name or beautify_mission_title(s.title),
                "campagne": campagnes.get(s.campaign_id, (None, None))[1],
            }
            for s in recentes
        ],
    }


async def _fiche_publique(db: AsyncSession, profile_id: int):
    """Lot « Le dossier du pilote — les données » (R208) -- la fiche publique
    d'un membre (écran F), une seule source pour F et pour le dossier A.
    `None` si le profil n'existe pas ; sinon le triplet `(fiche, vols,
    campagnes)` : `fiche`, la charge de F ; `vols`, les couples (vol, session)
    RÉELS du membre, dans l'ordre de F ; `campagnes`, par id, (rang, nom).
    Le corps est celui de `get_membre` avant ce lot, inchangé."""
    profil = await db.get(Profile, profile_id)
    if profil is None:
        return None
    wing = (await db.execute(select(Wing).order_by(Wing.id).limit(1))).scalar_one_or_none()
    escadrille = (
        await db.execute(
            select(Squadron)
            .join(SquadronMembership, SquadronMembership.squadron_id == Squadron.id)
            .where(
                SquadronMembership.profile_id == profile_id,
                SquadronMembership.ended_at.is_(None),
                Squadron.status == "actif",
            )
        )
    ).scalars().first()
    campagnes = {
        c.id: (rang, c.name)
        for rang, c in enumerate(
            (await db.execute(select(Campaign).order_by(Campaign.created_at, Campaign.id))).scalars().all(),
            start=1,
        )
    }
    vols = (
        await db.execute(
            select(DebriefFlight, DebriefSession)
            .join(DebriefSession, DebriefSession.id == DebriefFlight.session_id)
            .where(DebriefFlight.pilote_profile_id == profile_id)
            .order_by(DebriefSession.mission_date, DebriefSession.id)
        )
    ).all()
    significatifs = await _significant_object_ids_par_session(db, {s.id for _vol, s in vols})
    vols = [(vol, s) for vol, s in vols if _est_significatif(vol, significatifs)]
    fiche = {
        # str() impératif : snowflake Discord au-delà de Number.MAX_SAFE_INTEGER.
        "id": str(profil.id),
        "name": profil.global_name or profil.username,
        "avatar_hash": profil.avatar_hash,
        "wing": wing.designation if wing is not None else None,
        "squadron": (
            {"id": escadrille.id, "designation": escadrille.designation, "crest_sha": escadrille.crest_sha}
            if escadrille is not None else None
        ),
        "archived_at": profil.archived_at.isoformat() if profil.archived_at else None,
        # Lot « Les cartes DCS de chaque pilote » : la déclaration du pilote.
        "cartes_dcs": profil.cartes_dcs,
        "cartes_dcs_le": profil.cartes_dcs_le.isoformat() if profil.cartes_dcs_le else None,
        **_synthese_membre(vols, campagnes),
    }
    return fiche, vols, campagnes


@router.get("/membres/{profile_id}")
async def get_membre(
    profile_id: int,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les écrans E et F » (R187) -- l'écran F, la synthèse d'un
    membre. Trois chemins y mènent : un membre de l'organigramme de D, un
    membre de celui de E, le nom d'un pilote identifié à l'écran d'un vol.
    Ouverte à tout membre connecté, comme le reste du Débrief. Un pilote
    archivé garde sa fiche (R184) ; l'escadrille rendue est celle de son
    appartenance ouverte à une escadrille active, sinon aucune. Lot
    « Correctifs de B » : sa participation ne compte que ses vols réels.
    Lot « Le dossier du pilote — les données » : son corps vit dans
    `_fiche_publique`, la source partagée avec le dossier A."""
    publique = await _fiche_publique(db, profile_id)
    if publique is None:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    return publique[0]


# --- Lot « Le dossier du pilote — les données » (R208, R209) ------------------
#
# L'écran A, le dossier personnel : la fiche publique de F, plus une part
# PRIVÉE, que seule la route `GET /dossier` sert, et au seul compte connecté.

_CATEGORIES_AIR = ("Avion", "Hélicoptère")
_GRAVITES_TOUCHE = ("touché", "abattu")


def _efficacite_par_arme(tirs, destructions: dict) -> dict:
    """Lot « L'efficacité par arme sur l'écran Vol » (R276) -- la règle de
    l'efficacité, écrite une seule fois : le Dossier (`_dossier_prive`) et
    l'écran Vol (`get_flight`) l'appellent tous deux. Pure : testée hors ligne
    (tests/test_efficacite_vol.py, tests/test_efficacite_arme.py).

    `tirs` : des couples (identifiant de session, ligne de tir de
    `stats["bursts"]`) ; `destructions` : par identifiant de session, les
    `target_object_id` que le pilote y a détruits, avec n'importe laquelle de
    ses armes (explosion d'épave comprise). Rend, par arme, les cibles
    touchées (couples (session, cible) distincts) et celles qui sont détruites
    -- `canon` pour les lignes `cannon: true`, `precision` pour les autres.
    Une arme n'y entre que si au moins une cible est touchée."""
    touchees: dict = {"precision": {}, "canon": {}}
    for session_id, ligne_tir in tirs:
        cibles = ligne_tir.get("target_object_ids") or []
        if cibles:
            par_arme = touchees["canon" if ligne_tir.get("cannon") else "precision"]
            par_arme.setdefault(ligne_tir.get("weapon"), set()).update((session_id, c) for c in cibles)
    return {
        forme: {
            arme: {
                "cibles_touchees": len(cibles),
                "cibles_detruites": sum(1 for session_id, cible in cibles if cible in destructions.get(session_id, ())),
            }
            for arme, cibles in par_arme.items()
        }
        for forme, par_arme in touchees.items()
    }


def _destructions_du_vol(flight, vols_session) -> set:
    """Lot « L'efficacité par arme sur l'écran Vol » (R276) -- les cibles que
    le pilote de ce vol a détruites dans la session : l'union des
    `target_object_id` de `stats["kills"]` de tous les vols de la session
    rattachés au même membre (`pilote_profile_id`) ; un vol sans membre ne
    compte que ses propres destructions. `vols_session` : des objets qui
    portent `pilote_profile_id` et `stats`. Pure."""
    if flight.pilote_profile_id is None:
        vols = [flight]
    else:
        vols = [v for v in vols_session if v.pilote_profile_id == flight.pilote_profile_id]
    return {
        k["target_object_id"]
        for v in vols
        for k in (v.stats or {}).get("kills") or []
        if k.get("target_object_id")
    }


def _dossier_prive(vols, camps: dict, campagnes: dict) -> dict:
    """Lot « Le dossier du pilote — les données » (R208, R209) -- la part
    privée du dossier A, assemblée sans requête. `vols` : les couples (vol,
    session) réels du membre, dans l'ordre de F (`_fiche_publique`) ; `camps` :
    par session, le camp de chacun de ses vols, réels ou non ; `campagnes` :
    par id, (rang, nom). Pure : testée hors ligne (tests/test_dossier_pilote.py).

    Règles (cadrage §3.3) : le bilan est `_bilan_additionne` session par
    session (R167), air = avions et hélicoptères, sol = tout le reste ; un
    appareil perdu = crash, mort ou éjection (la règle de `flightIssue`) ; le
    ratio = destructions validées par appareil perdu ; la précision sur les
    seuls vols fiables, sans le canon ; les menaces comptées par sortie ; le
    carnet, une ligne par vol, du plus récent au plus ancien."""
    par_session: dict = {}
    for vol, s in vols:
        par_session.setdefault(s.id, []).append(vol)
    bilan = _bilan_additionne(
        (liste, camps.get(session_id, {})) for session_id, liste in par_session.items()
    )
    air = sum(r["count"] for r in bilan["kills_by_category"] if r["category"] in _CATEGORIES_AIR)

    def perdu(st: dict) -> bool:
        return bool(st.get("crashed") or st.get("pilot_dead") or st.get("ejected"))

    appareils_perdus = sum(1 for vol, _s in vols if perdu(vol.stats or {}))
    ejections = sum(1 for vol, _s in vols if (vol.stats or {}).get("ejected"))

    # Précision : vols fiables seulement ; une arme peut porter les deux formes.
    precision: dict = {}
    canon: dict = {}
    # Lot « L'écran de la précision » : la famille de chaque arme, sur les
    # mêmes vols fiables ; la première vue l'emporte.
    familles: dict = {}
    fiables = 0
    # Lot « L'efficacité par arme au Dossier » : par session, les cibles que le
    # pilote a détruites (tous ses vols de la session, quelle que soit l'arme du
    # kill -- explosion d'épave comprise) ; les lignes de tir des vols fiables,
    # que `_efficacite_par_arme` (lot « L'efficacité par arme sur l'écran Vol »,
    # le même calcul que l'écran Vol) rapporte à ces destructions.
    destructions: dict = {}
    for vol, s in vols:
        for k in (vol.stats or {}).get("kills") or []:
            if k.get("target_object_id"):
                destructions.setdefault(s.id, set()).add(k["target_object_id"])
    tirs_fiables: list = []
    for vol, s in vols:
        st = vol.stats or {}
        if st.get("precision_reliability") != "fiable":
            continue
        fiables += 1
        tirs_fiables.extend((s.id, ligne_tir) for ligne_tir in st.get("bursts") or [])
        for arme, famille in (st.get("weapon_families") or {}).items():
            familles.setdefault(arme, famille)
        for arme, w in (st.get("shots_by_weapon") or {}).items():
            ligne = precision.setdefault(arme, {"arme": arme, "tirs": 0, "touches": 0, "largages": 0})
            if "releases" in w:
                ligne["largages"] += int(w.get("releases") or 0)
            if "shots" in w:
                ligne["tirs"] += int(w.get("shots") or 0)
                ligne["touches"] += int(w.get("touched") or 0)
            # Lot « La précision des armes — le moteur » : une arme à
            # sous-munitions porte ses salves, et celles qui ont touché.
            if "salvos" in w:
                ligne["salves"] = ligne.get("salves", 0) + int(w.get("salvos") or 0)
                ligne["salves_touchees"] = ligne.get("salves_touchees", 0) + int(w.get("salvos_hit") or 0)
        # Lot « La précision des armes — le moteur » : le canon, une ligne par
        # arme, sur les mêmes vols fiables.
        for arme, c in (st.get("cannon_by_weapon") or {}).items():
            ligne = canon.setdefault(
                arme, {"arme": arme, "rafales": 0, "obus": 0, "rafales_touchees": 0, "obus_au_but": 0}
            )
            ligne["rafales"] += int(c.get("bursts") or 0)
            ligne["obus"] += int(c.get("rounds") or 0)
            ligne["rafales_touchees"] += int(c.get("bursts_hit") or 0)
            ligne["obus_au_but"] += int(c.get("rounds_hit") or 0)

    # Lot « L'efficacité par arme au Dossier » : deux clés, seulement pour une
    # arme qui a une ligne ici et au moins une cible touchée ; une arme sans
    # ligne dans `precision` ou `canon` n'en reçoit pas.
    efficacite = _efficacite_par_arme(tirs_fiables, destructions)
    for forme, lignes_armes in (("precision", precision), ("canon", canon)):
        for arme, eff in efficacite[forme].items():
            ligne = lignes_armes.get(arme)
            if ligne is None:
                continue
            ligne["cibles_touchees"] = eff["cibles_touchees"]
            ligne["cibles_detruites"] = eff["cibles_detruites"]

    # Menaces : un compte par vol, par type d'initiateur (None compris).
    menaces: dict = {}
    for vol, _s in vols:
        par_type: dict = {}
        for e in (vol.stats or {}).get("threat_log") or []:
            par_type.setdefault(e.get("initiator_unit_type"), set()).add(e.get("gravite"))
        for t, gravites in par_type.items():
            m = menaces.setdefault(t, {"type": t, "engagements": 0, "touche": 0, "abattu": 0})
            m["engagements"] += 1
            if gravites & set(_GRAVITES_TOUCHE):
                m["touche"] += 1
            if "abattu" in gravites:
                m["abattu"] += 1

    carnet = []
    par_appareil: dict = {}
    for vol, s in vols:
        st = vol.stats or {}
        victoires = _bilan_des_vols([vol], camps.get(s.id, {}))["n_kills_validated"]
        carnet.append(
            {
                "session_id": str(s.id),
                "flight_id": str(vol.id),
                "date": s.mission_date.isoformat() if s.mission_date else None,
                "titre": s.display_name or beautify_mission_title(s.title),
                "campagne": campagnes.get(s.campaign_id, (None, None))[1],
                # Lot « L'écran C — la fiche campagne » : l'identifiant, pour
                # que la pastille du carnet ouvre la fiche C.
                "campagne_id": str(s.campaign_id) if s.campaign_id in campagnes else None,
                "appareil": vol.aircraft_type,
                "duree_s": round(float(max((vol.t_end or 0) - (vol.t_start or 0), 0)), 1),
                "victoires": victoires,
                "stats": {
                    "crashed": bool(st.get("crashed", False)),
                    "pilot_dead": bool(st.get("pilot_dead", False)),
                    "ejected": bool(st.get("ejected", False)),
                    "landings": int(st.get("landings") or 0),
                },
                "_cle": (s.mission_date is not None, s.mission_date or datetime.min.date(), str(s.id), vol.t_start or 0),
            }
        )
        a = par_appareil.setdefault(vol.aircraft_type, {"victoires": 0, "pertes": 0, "dernier": None})
        a["victoires"] += victoires
        if perdu(st):
            a["pertes"] += 1
        if s.mission_date and (a["dernier"] is None or s.mission_date.isoformat() > a["dernier"]):
            a["dernier"] = s.mission_date.isoformat()
    carnet.sort(key=lambda ligne: ligne["_cle"], reverse=True)
    for ligne in carnet:
        del ligne["_cle"]

    # Lot « La précision des armes — le moteur » : la clé `canon` n'apparaît
    # que si un vol fiable a tiré au canon -- un dossier sans canon garde sa
    # forme d'avant (tests/test_dossier_pilote.py, le dossier vide).
    en_plus = (
        {"canon": sorted(canon.values(), key=lambda c: (-c["obus"], c["arme"]))} if canon else {}
    )
    # Lot « L'écran de la précision » : `familles` absente quand elle serait
    # vide, comme `canon` -- un dossier sans arme garde sa forme d'avant.
    if familles:
        en_plus["familles"] = familles
    return {
        "vols": len(vols),
        "vols_fiables": fiables,
        "bilan": bilan,
        "victoires": {"air": air, "sol": bilan["n_kills_validated"] - air},
        "pertes": {"appareils": appareils_perdus, "ejections": ejections},
        "ratio": round(bilan["n_kills_validated"] / appareils_perdus, 1) if appareils_perdus else None,
        "precision": sorted(precision.values(), key=lambda p: (-(p["tirs"] + p["largages"]), p["arme"])),
        "menaces": sorted(
            menaces.values(),
            key=lambda m: (-m["abattu"], -m["touche"], -m["engagements"], m["type"] is None, m["type"] or ""),
        ),
        "par_appareil": par_appareil,
        "carnet": carnet,
        **en_plus,
    }


def _vols_par_nature(vols) -> dict:
    """Lot « Mission ou training » -- partage les couples (vol, session) du
    dossier selon `session.nature`, dans l'ordre d'entrée. Pure : testée hors
    ligne (tests/test_mission_training.py)."""
    par_nature: dict = {"mission": [], "training": []}
    for couple in vols:
        _vol, s = couple
        par_nature["training" if s.nature == "training" else "mission"].append(couple)
    return par_nature


@router.get("/dossier")
async def get_dossier(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Le dossier du pilote — les données » (R208) -- l'écran A, le
    dossier personnel du compte connecté : sa fiche publique (F, servie par
    `_fiche_publique`), plus la part privée (`_dossier_prive`).

    PRIVÉE PAR CONSTRUCTION : la route ne prend aucun identifiant, ni de
    chemin ni de requête ; elle ne lit que `user["id"]`. Un admin n'obtient
    que son propre dossier. Les camps de repli lisent tous les vols des
    sessions du membre, réels ou non, comme l'écran E."""
    publique = await _fiche_publique(db, int(user["id"]))
    if publique is None:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    fiche, vols, campagnes = publique
    camps: dict = defaultdict(dict)
    session_ids = {s.id for _vol, s in vols}
    if session_ids:
        for session_id, object_id, coalition in (
            await db.execute(
                select(DebriefFlight.session_id, DebriefFlight.object_id, DebriefFlight.coalition)
                .where(DebriefFlight.session_id.in_(list(session_ids)))
            )
        ).all():
            if object_id is not None:
                camps[session_id][str(object_id)] = coalition
    # Lot « Mission ou training » : le dossier gagne `par_nature` -- le même
    # calcul, une fois sur les vols des missions, une fois sur ceux des
    # trainings. Le reste du dossier ne change pas.
    par_nature = _vols_par_nature(vols)
    dossier = _dossier_prive(vols, camps, campagnes)
    dossier["par_nature"] = {
        "mission": _dossier_prive(par_nature["mission"], camps, campagnes),
        "training": _dossier_prive(par_nature["training"], camps, campagnes),
    }
    return {**fiche, "dossier": dossier}


@router.put("/dossier/cartes")
async def put_dossier_cartes(
    payload: CartesDcsPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les cartes DCS de chaque pilote » (R640) -- le pilote déclare les
    cartes DCS qu'il possède. PRIVÉE PAR CONSTRUCTION, comme `get_dossier` :
    la route n'écrit que le profil du compte connecté (`user["id"]`), jamais
    celui d'un autre, officier ou administrateur compris. La réponse est celle
    de `get_dossier` pour le même compte."""
    profil = await db.get(Profile, int(user["id"]))
    if profil is None:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    profil.cartes_dcs = payload.cartes
    profil.cartes_dcs_le = datetime.now(timezone.utc)
    await db.commit()
    return await get_dossier(user=user, db=db)


def _accueil_payload(campagnes, sessions, vols: dict, aujourdhui, jours: int = 30, significatifs: dict | None = None) -> dict:
    """Lot « L'écran B » -- ce que l'accueil ajoute à la charge de D, assemblé
    sans requête. `campagnes` : par ordre de création ; `sessions` : toutes ;
    `vols` : par id de session, ses vols. Les campagnes EN COURS avec leur
    nombre de missions, les quatre dernières
    missions, avec leur durée et le nombre de pilotes de l'escadre qui y ont
    volé (lot « L'Accueil, durée et pilotes » : profils distincts parmi les
    vols réels, comme le compte « pilotes » de l'écran Campagne ; le nombre de
    vols n'est plus servi), les destructions de l'escadre sur les
    `jours` derniers jours -- trente, arbitré par le porteur le 1er octobre : le
    mois calendaire est vide à chaque début de mois. Pure : testée hors ligne
    (tests/test_accueil.py).

    Lot « Correctifs de B » : `significatifs` (la sortie de
    `_significant_object_ids_par_session`) restreint les vols comptés et le
    bilan aux vols RÉELS, ceux de l'écran de session ; les camps de repli
    lisent tous les vols. `None` : tous les vols comptent.

    Lot « Le Débrief n'est plus en chantier, et l'escadre compte les siens » :
    le bilan des destructions n'additionne que les vols de l'escadre
    (`_est_vol_escadre` : réels et rattachés à un membre) ; le nombre de
    missions et la liste des quatre dernières ne changent pas, et les camps de
    repli lisent toujours tous les vols de la session."""
    chrono = sorted(sessions, key=lambda s: (s.mission_date or datetime.min.date(), str(s.id)))
    recentes = [s for s in chrono if s.mission_date and s.mission_date > aujourdhui - timedelta(days=jours)]
    reels = {
        sid: [v for v in liste if significatifs is None or _est_significatif(v, significatifs)]
        for sid, liste in vols.items()
    }
    escadre = {sid: [v for v in liste if _est_vol_escadre(v, significatifs)] for sid, liste in vols.items()}
    return {
        "campagnes": [
            {
                "id": str(c.id),
                "name": c.name,
                "sim": c.sim,
                "missions": sum(1 for s in sessions if s.campaign_id == c.id),
            }
            for c in campagnes
            if c.status == "en_cours"
        ],
        "missions": [
            {
                "session_id": str(s.id),
                "date": s.mission_date.isoformat() if s.mission_date else None,
                "titre": s.display_name or beautify_mission_title(s.title),
                # Lot « L'Accueil, durée et pilotes » : la durée de la session et le
                # nombre de profils distincts parmi ses vols réels -- la définition
                # des « pilotes » de l'écran Campagne (`presences`). `vols` n'est plus servi.
                "duree_s": s.duration_s,
                "pilotes": len({v.pilote_profile_id for v in reels.get(s.id, []) if v.pilote_profile_id is not None}),
            }
            for s in reversed(chrono[-4:])
        ],
        "destructions": {
            "jours": jours,
            "missions": len(recentes),
            **_bilan_additionne(
                (escadre.get(s.id, []), {str(v.object_id): v.coalition for v in vols.get(s.id, []) if v.object_id is not None})
                for s in recentes
            ),
        },
    }


@router.get("/accueil")
async def get_accueil(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « L'écran B » -- l'accueil du Débrief, le poste de commandement de
    l'escadre. Les chiffres et les escadrilles se lisent dans la charge de D
    (`get_escadre`) ; cette route porte le reste : campagnes en cours,
    dernières missions, destructions des trente derniers jours. Ouverte à tout
    membre connecté, comme le reste du Débrief."""
    campagnes = (await db.execute(select(Campaign).order_by(Campaign.created_at, Campaign.id))).scalars().all()
    sessions = (await db.execute(select(DebriefSession))).scalars().all()
    vols: dict = defaultdict(list)
    for v in (await db.execute(select(DebriefFlight))).scalars().all():
        vols[v.session_id].append(v)
    return _accueil_payload(
        campagnes, sessions, vols, datetime.now(timezone.utc).date(),
        significatifs=await _significant_object_ids_par_session(db),
    )


# --- Lot « Les campagnes — les données » (v1.0025) -----------------------------
#
# Le registre des campagnes et la fiche d'une campagne (écran C, spec Carrière
# §5.4, spec Câblage §3.7) : des LECTURES du Débrief, qui agrègent les missions
# comme `/escadre` ou `/accueil`. Elles ne doublent pas `GET /campaigns`, la
# table brute du sélecteur de la modale Déposer et du Centre, qui ne change pas.
# Tout se calcule à la demande sur les vols réels (R193) : ni table ni
# migration (R209). Le bilan est `_bilan_additionne` (R167), jamais un bilan
# par pilote ; aucun chiffre de performance par participant (R208).


def _periode_campagne(sessions) -> dict:
    """Lot « Les campagnes — les données » -- la période d'une campagne,
    déduite de ses missions : la plus ancienne et la plus récente
    `mission_date` ; `None` toutes deux sans mission datée (la table n'a plus
    de dates depuis la migration 0019). Pure."""
    dates = [s.mission_date for s in sessions if s.mission_date]
    return {
        "debut": min(dates).isoformat() if dates else None,
        "fin": max(dates).isoformat() if dates else None,
    }


def _registre_campagnes(campagnes, sessions) -> dict:
    """Lot « Les campagnes — les données » -- le registre des campagnes,
    assemblé sans requête. `campagnes` : TOUTES, dans l'ordre de création
    (`created_at`, puis `id`) -- le rang en découle, le même calcul que les
    barrettes de F (`_fiche_publique`) ; `sessions` : toutes. Ordre : en cours
    d'abord, puis closes ; dans chaque groupe, la fin de période la plus
    récente d'abord (sans mission datée en dernier), puis le rang décroissant.
    Pure : testée hors ligne (tests/test_campagnes.py)."""
    par_campagne: dict = defaultdict(list)
    for s in sessions:
        if s.campaign_id is not None:
            par_campagne[s.campaign_id].append(s)
    lignes = []
    for rang, c in enumerate(campagnes, start=1):
        siennes = par_campagne.get(c.id, [])
        lignes.append(
            {
                "id": str(c.id),
                "name": c.name,
                "rang": rang,
                "status": c.status,
                "map_name": c.map_name,
                "sim": c.sim,
                "periode": _periode_campagne(siennes),
                "missions": len(siennes),
            }
        )
    lignes.sort(key=lambda l: (l["periode"]["fin"] is not None, l["periode"]["fin"] or "", l["rang"]), reverse=True)
    lignes.sort(key=lambda l: l["status"] != "en_cours")
    return {"campagnes": lignes}


def _fiche_campagne(campagne, rang: int, sessions, vols: dict, significatifs: dict, profils: dict, escadrilles: dict) -> dict:
    """Lot « Les campagnes — les données » -- la fiche d'une campagne,
    assemblée sans requête. `sessions` : ses missions ; `vols` : par id de
    session, TOUS ses vols (les camps de repli du bilan les lisent tous, comme
    `_accueil_payload`) ; `significatifs` : la sortie de
    `_significant_object_ids_par_session` -- seuls les vols RÉELS comptent ;
    `profils` : par id, le profil des pilotes identifiés ; `escadrilles` : par
    id de profil, la désignation de son escadrille ACTUELLE (absent pour un
    Free Agent). Les participants ne sont pas triés par nom : l'écran les
    classera sur le nom qu'il affiche ; ils sortent par identifiant croissant,
    pour une charge stable.

    Lot « Le Débrief n'est plus en chantier, et l'escadre compte les siens » :
    `activite.sorties`, `activite.heures` et `bilan` ne comptent que les vols de
    l'escadre (`_est_vol_escadre` : réels et rattachés à un membre) ;
    `activite.missions`, `activite.pilotes`, les participants et le nombre de
    vols de chaque mission de la liste ne changent pas (le vol d'un invité y
    compte encore), et les camps de repli lisent toujours tous les vols.

    Lot « Les heures comptées par mission » (v1.0069, le porteur, 4 novembre) :
    `activite.heures` compte, mission par mission, le temps où au moins un
    pilote est en l'air (`_heures_de_mission`).
    Pure : testée hors ligne (tests/test_campagnes.py)."""
    sessions = [s for s in sessions if s.campaign_id == campagne.id]
    chrono = sorted(sessions, key=lambda s: (s.mission_date or datetime.min.date(), str(s.id)))
    reels = {s.id: [v for v in vols.get(s.id, []) if _est_significatif(v, significatifs)] for s in chrono}
    escadre = {s.id: [v for v in vols.get(s.id, []) if _est_vol_escadre(v, significatifs)] for s in chrono}
    tous = [v for s in chrono for v in escadre[s.id]]
    secondes, _nuit = _heures_de_mission(tous)  # Lot « Les heures comptées par mission »
    presences: dict = defaultdict(set)
    for v in tous:
        if v.pilote_profile_id is not None:
            presences[v.pilote_profile_id].add(v.session_id)
    participants = []
    for pid in sorted(presences):
        profil = profils.get(pid)
        participants.append(
            {
                # str() impératif : snowflake Discord au-delà de Number.MAX_SAFE_INTEGER.
                "id": str(pid),
                "name": (profil.global_name or profil.username) if profil is not None else None,
                "escadrille": escadrilles.get(pid),
                "archived": profil is not None and profil.archived_at is not None,
                "missions": len(presences[pid]),
            }
        )
    recentes = sorted(
        chrono,
        key=lambda s: (s.mission_date is not None, s.mission_date or datetime.min.date(), str(s.id)),
        reverse=True,
    )
    return {
        "id": str(campagne.id),
        "name": campagne.name,
        "rang": rang,
        "status": campagne.status,
        "map_name": campagne.map_name,
        "sim": campagne.sim,
        "description": campagne.description,
        "periode": _periode_campagne(chrono),
        "activite": {
            "missions": len(chrono),
            "sorties": len(tous),
            "heures": round(secondes / 3600, 1),
            "pilotes": len(presences),
        },
        "missions": [
            {
                "session_id": str(s.id),
                "date": s.mission_date.isoformat() if s.mission_date else None,
                "titre": s.display_name or beautify_mission_title(s.title),
                "vols": len(reels[s.id]),
            }
            for s in recentes
        ],
        "participants": participants,
        "bilan": _bilan_additionne(
            (escadre[s.id], {str(v.object_id): v.coalition for v in vols.get(s.id, []) if v.object_id is not None})
            for s in chrono
        ),
    }


@router.get("/campagnes")
async def get_campagnes(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les campagnes — les données » -- le registre des campagnes de
    l'écran C. Ouverte à tout membre connecté, comme le reste du Débrief."""
    campagnes = (await db.execute(select(Campaign).order_by(Campaign.created_at, Campaign.id))).scalars().all()
    sessions = (await db.execute(select(DebriefSession))).scalars().all()
    return _registre_campagnes(campagnes, sessions)


@router.get("/campagnes/{campaign_id}")
async def get_campagne(
    campaign_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lot « Les campagnes — les données » -- la fiche d'une campagne (écran
    C) : 404 si elle n'existe pas. Ouverte à tout membre connecté, comme le
    reste du Débrief. Le rang suit l'ordre de création de TOUTES les
    campagnes, comme dans `_fiche_publique`."""
    campagne = await db.get(Campaign, campaign_id)
    if campagne is None:
        raise HTTPException(status_code=404, detail="Campagne introuvable")
    ordre = (await db.execute(select(Campaign.id).order_by(Campaign.created_at, Campaign.id))).scalars().all()
    rang = ordre.index(campagne.id) + 1
    sessions = (
        await db.execute(select(DebriefSession).where(DebriefSession.campaign_id == campaign_id))
    ).scalars().all()
    session_ids = {s.id for s in sessions}
    vols: dict = defaultdict(list)
    significatifs: dict = {}
    if session_ids:
        for v in (
            await db.execute(select(DebriefFlight).where(DebriefFlight.session_id.in_(list(session_ids))))
        ).scalars().all():
            vols[v.session_id].append(v)
        significatifs = await _significant_object_ids_par_session(db, session_ids)
    pids = {
        v.pilote_profile_id
        for liste in vols.values()
        for v in liste
        if v.pilote_profile_id is not None and _est_significatif(v, significatifs)
    }
    profils: dict = {}
    escadrilles: dict = {}
    if pids:
        profils = {
            p.id: p for p in (await db.execute(select(Profile).where(Profile.id.in_(pids)))).scalars().all()
        }
        # L'escadrille actuelle, comme la tête de F : l'appartenance ouverte à
        # une escadrille active.
        for pid, designation in (
            await db.execute(
                select(SquadronMembership.profile_id, Squadron.designation)
                .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
                .where(
                    SquadronMembership.profile_id.in_(pids),
                    SquadronMembership.ended_at.is_(None),
                    Squadron.status == "actif",
                )
            )
        ).all():
            escadrilles.setdefault(pid, designation)
    return _fiche_campagne(campagne, rang, sessions, vols, significatifs, profils, escadrilles)


# --- Noms retenus (Geste①, v0.9917) ------------------------------------


async def _record_alias(db: AsyncSession, profile_id: int, segment: str) -> None:
    """Geste ① (brief §1/§3) : enregistre l'alias qui rattachera
    automatiquement les prochains vols portant ce SEGMENT à `profile_id`,
    sans que l'admin ait à revenir désigner ce membre. Appelée par
    `identify_flight` sur le segment de l'indicatif OBSERVÉ du vol (jamais
    une saisie libre -- elle n'existe plus côté front, brief §1).

    Idempotente si l'alias existe déjà pour CE profil (ré-confirmation sans
    effet, ex. « Corriger » choisissant à nouveau le même membre). Sinon
    laisse l'`INSERT` tenter sa chance : la contrainte d'unicité de
    `profile_dcs_alias.alias_segment` arbitre au commit (brief §7 P2) --
    PAS une vérification Python qui déciderait à sa place (« l'unicité est
    en base, pas dans le code », brief §3). `identify_flight` catche
    l'`IntegrityError` correspondante et la traduit en 409, même patron que
    `POST /api/command/campaigns` (app/command/api.py)."""
    seg_lower = segment.lower()
    existing = (
        await db.execute(
            select(ProfileDcsAlias).where(ProfileDcsAlias.alias_segment == seg_lower)
        )
    ).scalar_one_or_none()
    if existing is not None and existing.profile_id == profile_id:
        return
    db.add(ProfileDcsAlias(profile_id=profile_id, alias_segment=seg_lower))


# --- POST /sessions/{id}/flights/{flight_id}/identify (admin only) ------------


@router.post("/sessions/{session_id}/flights/{flight_id}/identify")
async def identify_flight(
    session_id: uuid.UUID,
    flight_id: uuid.UUID,
    body: IdentifyOverride,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux admins")

    await _session_or_404(db, session_id)
    flight = await db.get(DebriefFlight, flight_id)
    if flight is None or flight.session_id != session_id:
        raise HTTPException(status_code=404, detail="Vol introuvable")

    if body.pilote_profile_id is None and not body.pilot_callsign:
        raise HTTPException(
            status_code=422, detail="pilote_profile_id ou pilot_callsign requis"
        )

    if body.pilote_profile_id is not None:
        profile = await db.get(Profile, body.pilote_profile_id)
        if profile is None:
            raise HTTPException(status_code=422, detail="profile_id inconnu")
        # Lot « Le nom qu'on retient » v0.9917, brief §1/§6 : désigner un
        # membre retient aussi le nom vu dans l'ACMI pour lui -- segment
        # calculé sur l'indicatif OBSERVÉ déjà porté par le vol (jamais une
        # saisie libre). Silencieux si le vol n'a aucun callsign (ex. vol
        # ACMI sans pilote nommé) : rien à retenir, seul le rattachement
        # direct de CE vol a lieu.
        segment = engine._extract_name_segment(flight.pilot_callsign)
        if segment:
            await _record_alias(db, body.pilote_profile_id, segment)
        flight.pilote_profile_id = body.pilote_profile_id
        flight.identity_state = "nomme"
    else:
        flight.pilote_profile_id = None
        flight.identity_state = "rattachable"

    if body.pilot_callsign is not None:
        flight.pilot_callsign = body.pilot_callsign
    flight.identity_source = "manuel"

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Ce nom est déjà retenu par un autre membre.",
        )
    crest = await _crest_ref(db, flight.pilote_profile_id)
    noms = await _noms_membres_bulk(db, {flight.pilote_profile_id})
    return _flight_to_dict(flight, crest=crest, nom=noms.get(flight.pilote_profile_id))


# --- DELETE /sessions/{id}/flights/{flight_id}/alias (admin only, neuf) -----


@router.delete("/sessions/{session_id}/flights/{flight_id}/alias")
async def forget_flight_alias(
    session_id: uuid.UUID,
    flight_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Geste ③ (brief §5) : « Oublie » le nom retenu qui a rattaché ce vol
    -- supprime la ligne `profile_dcs_alias` correspondante, puis recalcule
    la session (même patron que `unidentify_flight`) pour que ce vol, et
    tout autre vol du même segment, retombe sur la règle de segment ou
    redevienne anonyme (brief §7 P2, "le nom oublié"). N'existe que pour un
    vol `identity_source == "alias"` -- un vol nommé autrement n'a pas de
    ligne à oublier."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux admins")

    await _session_or_404(db, session_id)
    flight = await db.get(DebriefFlight, flight_id)
    if flight is None or flight.session_id != session_id:
        raise HTTPException(status_code=404, detail="Vol introuvable")

    if flight.identity_source != "alias":
        raise HTTPException(
            status_code=404, detail="Ce vol n'est pas rattaché par un nom retenu"
        )

    segment = engine._extract_name_segment(flight.pilot_callsign)
    if segment:
        await db.execute(
            delete(ProfileDcsAlias).where(
                ProfileDcsAlias.alias_segment == segment.lower()
            )
        )
    await db.flush()
    summary = await engine.recompute_session(db, session_id)
    await db.commit()
    return summary


# --- DELETE /sessions/{id}/flights/{flight_id}/identify (admin only) --------
# Lot « Le nom qu'on retient » v0.9917, brief §5 : sémantique élargie --
# ne « annule » plus une identification manuelle, DÉTACHE DÉFINITIVEMENT
# le vol quelle que soit son origine (moteur, nom retenu ou main). Le 404
# « hors manuel » disparaît : on détache un vol quel que soit son
# `identity_source` de départ, y compris déjà "detache" (idempotent).


@router.delete("/sessions/{session_id}/flights/{flight_id}/identify")
async def unidentify_flight(
    session_id: uuid.UUID,
    flight_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux admins")

    await _session_or_404(db, session_id)
    flight = await db.get(DebriefFlight, flight_id)
    if flight is None or flight.session_id != session_id:
        raise HTTPException(status_code=404, detail="Vol introuvable")

    # Pose le détachement sur la ligne du vol elle-même (brief §2 : aucune
    # table pour ça, c'est une troisième valeur d'identity_source, au même
    # endroit que "manuel"). `_apply_manual_overrides` (engine.py) la
    # retrouvera au recalcul ci-dessous via `manual_by_key` et la
    # reconduira sans jamais la superséder (P1).
    flight.pilote_profile_id = None
    flight.identity_state = "anonyme"
    flight.identity_source = "detache"
    await db.flush()
    summary = await engine.recompute_session(db, session_id)
    await db.commit()
    return summary


# --- POST /sessions/{id}/recompute (admin only) ------------------------------


@router.post("/sessions/{session_id}/recompute")
async def recompute_session_route(
    session_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux admins")

    await _session_or_404(db, session_id)
    summary = await engine.recompute_session(db, session_id)
    await db.commit()
    return summary


# --- POST /sessions/recompute-stale (admin only) -- Lot Fraîcheur v0.9939 --


@router.post("/sessions/recompute-stale")
async def recompute_stale_sessions_route(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Recalcule toutes les sessions périmées (brief §7). Réservée aux
    administrateurs, même garde stricte que la route de recalcul unitaire
    ci-dessus. Appelle `engine.recompute_stale_sessions` -- la même
    fonction que la tâche de fond du `lifespan` (`app/main.py`) : pas de
    second chemin de code. Rend `{"recomputed": n, "echecs": m}` : les sessions
    recalculées, et celles en échec (restées périmées) -- lot « Un dépôt à la
    fois »."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux admins")

    n, echecs = await engine.recompute_stale_sessions(db)
    return {"recomputed": n, "echecs": echecs}


# --- DELETE /sessions/{id} (admin only) -- Révision ④.1 chgt 4 ---------------


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Suppression admin d'une session parasite (ex. deux sessions issues
    d'un même vol sous des noms de mission différents qui ne fusionnent pas).
    Supprime tout le contenu de la session -- enfants puis parent, ordre FK
    -- ainsi que les fichiers bruts stockés sur le volume. Ne touche jamais
    à la logique de fusion/parsing (brief §chgt 4)."""
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Réservé aux admins")

    session = await _session_or_404(db, session_id)

    # Lot « Finitions du Débrief » (ARC-29) : pas de suppression pendant que
    # le récit se rédige -- la même garde que le déplacement et la fusion.
    await _redaction_bloque(
        db,
        session.id,
        detail="Une rédaction est en cours sur cette mission : réessayez quand elle sera finie.",
    )

    # Lot « Le rattachement des dépôts » : une seule fonction de suppression,
    # partagée avec le déplacement et la fusion.
    dossier = await _supprimer_session(db, session)
    await db.commit()
    # Lot « Le Débrief : quatre défauts » : le dossier ne s'efface qu'après le
    # commit réussi -- un échec du commit ne doit rien effacer.
    shutil.rmtree(dossier, ignore_errors=True)

    return {"deleted": True, "session_id": str(session_id)}


async def _supprimer_session(db: AsyncSession, session: DebriefSession) -> Path:
    """Lot « Le rattachement des dépôts » (R326, §3.7) -- LA suppression
    d'une session, appelée par la route de suppression, par le déplacement
    (une source vidée de ses fichiers) et par la fusion (la mission absorbée).
    Supprime, dans l'ordre des clés étrangères : évènements, épaves, vols,
    fichiers, récit (`debrief_report`) et rédaction en vol
    (`debrief_report_run`) -- auparavant laissés, et la clé étrangère
    bloquait la suppression d'une session qui avait un récit --, détache le
    journal des appels au modèle (`llm_call_log.session_id` à `NULL` : il
    garde ses lignes), puis la session. Ne commite pas : l'appelant le fait.
    Lot « Le Débrief : quatre défauts » : elle n'efface plus le dossier de
    stockage ; elle rend son chemin, et l'appelant l'efface APRÈS son
    `commit` réussi, erreurs ignorées."""
    sid = session.id
    await db.execute(delete(DebriefEvent).where(DebriefEvent.session_id == sid))
    await db.execute(delete(DebriefGraveyard).where(DebriefGraveyard.session_id == sid))
    await db.execute(delete(DebriefFlight).where(DebriefFlight.session_id == sid))
    await db.execute(delete(DebriefUpload).where(DebriefUpload.session_id == sid))
    await db.execute(delete(DebriefReport).where(DebriefReport.session_id == sid))
    await db.execute(delete(DebriefReportRun).where(DebriefReportRun.session_id == sid))
    await db.execute(
        LlmCallLog.__table__.update().where(LlmCallLog.session_id == sid).values(session_id=None)
    )
    await db.delete(session)
    await db.flush()
    return engine._storage_dir() / str(sid)


# --- Lot « Le rattachement des dépôts » (v1.0052, R326) : déplacer, fusionner --
#
# Deux gestes réservés au droit `session.edit` (`can_edit_session`), consignés
# au journal du Centre dans la transaction, avant le `commit`. Ni l'un ni
# l'autre ne touche au calcul : ils changent la session d'un fichier, puis
# rappellent `engine.recompute_session`.


def _titre_affiche(session: DebriefSession) -> str:
    """Le titre affiché d'une session : nom saisi, ou repli embelli."""
    return session.display_name or beautify_mission_title(session.title)


async def _redaction_bloque(
    db: AsyncSession,
    *session_ids,
    detail: str = "Une rédaction est en cours sur l'une des deux missions : réessayez quand elle sera finie.",
) -> None:
    """`409` si une rédaction est en cours sur l'une des sessions -- l'état lu
    par `_redaction_en_cours_et_par`, la seule définition de « en cours ».
    `detail` : le message du 409 (celui du déplacement et de la fusion par
    défaut ; la suppression d'une seule mission porte le sien)."""
    for sid in session_ids:
        en_cours, _par = await _redaction_en_cours_et_par(db, sid)
        if en_cours:
            raise HTTPException(status_code=409, detail=detail)


async def _mission_neuve_pour(db: AsyncSession, upload: DebriefUpload) -> DebriefSession:
    """La mission neuve d'un fichier déplacé « vers une nouvelle mission » :
    créée comme `engine._resolve_session` le ferait pour ce fichier seul --
    titre et ancre de son en-tête (`Title`/`RecordingTime` d'un ACMI ; chemin
    de mission et `mark − mission_time` d'un journal), `sim` `dcs` -- sans
    rattachement par le contenu. Un fichier absent ou illisible garde le
    titre noté au dépôt, sans ancre."""
    titre, ancre = upload.entete_titre, None
    chemin = upload.raw_stored_path
    if chemin and Path(chemin).exists():
        try:
            if upload.kind == "acmi":
                meta = (await asyncio.to_thread(parse_acmi, chemin)).meta
                titre, ancre = meta.title, meta.recording_time
            else:
                lu = await asyncio.to_thread(parse_debrief_log, chemin)
                titre = engine._display_mission_name(lu.header.mission_file_path)
                ancre = engine._real_start_debrief(lu.header)
        except (AcmiParseError, DebrieferParseError):
            logger.warning("Débrief : en-tête illisible pour le fichier %s", upload.id)
    session = DebriefSession(
        title=titre or "Session sans titre",
        reference_time=ancre,
        mission_date=ancre.date() if ancre else None,
        sim="dcs",
    )
    db.add(session)
    await db.flush()
    return session


def _deplacer_fichier(upload: DebriefUpload, cible_id: uuid.UUID, par_id: int | None, deplaces: list) -> None:
    """Le fichier brut suit sa ligne : déplacé dans `<stockage>/<cible>/`,
    sous le même nom ; `raw_stored_path` à jour. Un fichier absent sur disque
    se déplace quand même en base. Chaque déplacement réel est noté dans
    `deplaces` (`(depuis, vers)`), pour être défait si la transaction tombe."""
    if upload.raw_stored_path:
        depuis = Path(upload.raw_stored_path)
        dossier = engine._storage_dir() / str(cible_id)
        dossier.mkdir(parents=True, exist_ok=True)
        vers = dossier / depuis.name
        if depuis.exists() and depuis != vers:
            shutil.move(str(depuis), str(vers))
            deplaces.append((vers, depuis))
        upload.raw_stored_path = str(vers)
    upload.session_id = cible_id
    upload.rattachement = rattachement.MANUEL
    upload.deplace_par_profile_id = par_id


def _defaire(deplaces: list) -> None:
    """Remet les fichiers bruts à leur place, du dernier au premier."""
    for vers, depuis in reversed(deplaces):
        try:
            if vers.exists():
                depuis.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(vers), str(depuis))
        except OSError:
            logger.exception("Débrief : fichier %s non remis en place", vers)


async def _recopier_identifications(db: AsyncSession, source_id: uuid.UUID, cible_id: uuid.UUID) -> None:
    """Les identifications manuelles (`manuel`, `detache`) de la source sont
    recopiées dans la cible AVANT son recalcul, comme lignes de vol que
    `engine._apply_manual_overrides` relit par objet ; là où la cible en porte
    déjà une pour le même objet, celle de la cible l'emporte
    (`rattachement.overrides_a_recopier`). Les lignes recopiées servent le
    recalcul, qui les remplace ensuite par ses vols à identifiants
    déterministes."""
    def manuelles(sid):
        return select(DebriefFlight).where(
            DebriefFlight.session_id == sid,
            DebriefFlight.identity_source.in_(("manuel", "detache")),
        )
    source = (await db.execute(manuelles(source_id))).scalars().all()
    cible = (await db.execute(manuelles(cible_id))).scalars().all()
    for v in rattachement.overrides_a_recopier(source, cible):
        db.add(DebriefFlight(
            id=uuid.uuid4(),
            session_id=cible_id,
            object_id=v.object_id,
            acmi_track_id=v.acmi_track_id,
            aircraft_type=v.aircraft_type,
            coalition=v.coalition,
            pilote_profile_id=v.pilote_profile_id,
            pilot_callsign=v.pilot_callsign,
            identity_state=v.identity_state,
            identity_source=v.identity_source,
            t_start=v.t_start,
            t_end=v.t_end,
            slot_mission=v.slot_mission,
            mission_id_dcs=v.mission_id_dcs,
            stats={},
        ))
    await db.flush()


def _id_agissant(user: dict) -> int | None:
    try:
        return int(user["id"])
    except (KeyError, TypeError, ValueError):
        return None


@router.post("/uploads/{upload_id}/deplacer")
async def deplacer_fichier(
    upload_id: uuid.UUID,
    body: DeplacerPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Déplace un fichier vers une autre mission, ou une mission neuve
    (`session_id` à `null`). Les deux missions sont recalculées ; une source
    vidée de ses fichiers est supprimée (`_supprimer_session`). Réponse : le
    résumé de la cible, plus `session_id` et `source_supprimee`."""
    if not await can_edit_session(db, user):
        raise HTTPException(status_code=403, detail="Modification réservée")
    upload = await db.get(DebriefUpload, upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    source = await _session_or_404(db, upload.session_id)
    cible = None
    if body.session_id is not None:
        cible = await _session_or_404(db, body.session_id)
        if cible.id == source.id:
            raise HTTPException(status_code=422, detail="Ce fichier est déjà dans cette mission.")
        await _redaction_bloque(db, source.id, cible.id)
    else:
        await _redaction_bloque(db, source.id)

    titre_source = _titre_affiche(source)
    deposant = None
    if upload.depositor_profile_id:
        deposant = (await _noms_membres_bulk(db, {upload.depositor_profile_id})).get(upload.depositor_profile_id)
    deplaces: list = []
    dossier_source = None
    try:
        if cible is None:
            cible = await _mission_neuve_pour(db, upload)
        _deplacer_fichier(upload, cible.id, _id_agissant(user), deplaces)
        await db.flush()
        await _recopier_identifications(db, source.id, cible.id)
        await engine.recompute_session(db, cible.id)
        reste = await db.scalar(
            select(func.count()).select_from(DebriefUpload).where(DebriefUpload.session_id == source.id)
        )
        source_supprimee = not reste
        if source_supprimee:
            dossier_source = await _supprimer_session(db, source)
        else:
            await engine.recompute_session(db, source.id)
        titre_cible = _titre_affiche(cible)
        avant, apres = rattachement.etats_deplacer(
            rattachement.libelle_fichier(upload.kind, deposant), titre_source, titre_cible
        )
        journal.consigner(db, user, "debrief.deplacer", objet=titre_cible, lignes=journal.ecarts(avant, apres))
        cible_id = cible.id
        await db.commit()
    except Exception:
        await db.rollback()
        _defaire(deplaces)
        raise
    # Lot « Le Débrief : quatre défauts » : le dossier de la source vidée ne
    # s'efface qu'après le commit réussi, hors du bloc qui annule.
    if dossier_source is not None:
        shutil.rmtree(dossier_source, ignore_errors=True)

    resume = await engine._session_summary(db, cible_id)
    resume["session_id"] = str(cible_id)
    resume["source_supprimee"] = source_supprimee
    return resume


@router.post("/sessions/{session_id}/fusionner")
async def fusionner_sessions(
    session_id: uuid.UUID,
    body: FusionnerPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """La mission ouverte absorbe `source_id` : tous ses fichiers la
    rejoignent (comme un déplacement), ses identifications manuelles sont
    recopiées, elle est recalculée, puis la source, vide, est supprimée avec
    son nom, sa note et son récit. La mission ouverte garde les siens --
    nom, note, campagne, nature, récit : rien ne lui vient de la source.
    Réponse : le résumé de la mission gardée."""
    if not await can_edit_session(db, user):
        raise HTTPException(status_code=403, detail="Modification réservée")
    gardee = await _session_or_404(db, session_id)
    source = await _session_or_404(db, body.source_id)
    if source.id == gardee.id:
        raise HTTPException(status_code=422, detail="Une mission ne se fusionne pas avec elle-même.")
    await _redaction_bloque(db, gardee.id, source.id)

    titre_source = _titre_affiche(source)
    fichiers = (
        await db.execute(select(DebriefUpload).where(DebriefUpload.session_id == source.id))
    ).scalars().all()
    deplaces: list = []
    dossier_source = None
    try:
        par_id = _id_agissant(user)
        for upload in fichiers:
            _deplacer_fichier(upload, gardee.id, par_id, deplaces)
        await db.flush()
        await _recopier_identifications(db, source.id, gardee.id)
        await engine.recompute_session(db, gardee.id)
        dossier_source = await _supprimer_session(db, source)
        avant, apres = rattachement.etats_fusionner(titre_source, len(fichiers))
        journal.consigner(
            db, user, "debrief.fusionner", objet=_titre_affiche(gardee),
            lignes=journal.ecarts(avant, apres),
        )
        gardee_id = gardee.id
        await db.commit()
    except Exception:
        await db.rollback()
        _defaire(deplaces)
        raise
    # Lot « Le Débrief : quatre défauts » : idem -- après le commit, hors du
    # bloc qui annule.
    shutil.rmtree(dossier_source, ignore_errors=True)

    return await engine._session_summary(db, gardee_id)


# --- Campagnes (Lot 2.3, §4.4) ------------------------------------------------
#
# Trois routes CRUD sur une table sans mécanique métier -- pas de module
# neuf (brief §4.4). Aucune route de suppression : le statut `close` la
# remplace (arbitrage du porteur, cadrage CC §5.7, "on ne supprime rien").
# Aucun écran : administrées à l'API, comme role_capabilities depuis le
# lot 1 -- l'interface arrive au Centre de Commandement, phase 3.


@router.get("/campaigns")
async def list_campaigns(
    sim: str = Query(default="dcs"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.sim == sim).order_by(Campaign.name)
    )
    campaigns = result.scalars().all()
    return {"campaigns": [_campaign_to_dict(c) for c in campaigns]}
