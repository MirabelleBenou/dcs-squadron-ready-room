"""Router `/api/events`, `/api/events/{id}/occurrences/{occ_date}`,
`/api/presences`, `/api/hebdo` — cf. BRIEF_SONNET_ReadyRoom_Lot2.

Monté sans préfixe propre ; le préfixe `/api` est appliqué par le router
parent (`app/api.py`), comme pour `GET /api/me` du Lot 1.

Aucune modification du schéma ni de l'auth : réutilise intégralement
`get_current_user`, `settings`, les modèles existants (cf. brief).
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date, datetime, time as dt_time, timedelta, timezone
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Date, and_, case, delete, func, not_, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.capabilities import can_create_event, can_edit_event
from app.config import settings
from app.db import get_db
from app.models import Event, OccurrenceMessage, OccurrenceOverride, Presence, Profile
from app.realtime import publish_invalidate
from app.squadron import get_name_strip_tokens
from app.recurrence import (
    Occurrence,
    RecurrenceWindowTooLarge,
    fuseau_reference,
    UnsupportedRecurrenceRule,
    check_window,
    expand,
    raw_occurrence_dates,
)
from app.schemas import (
    EventCreate,
    EventPatchBody,
    PRESENCE_PREFS_EVENT_TYPES,
    PresenceUpsert,
    STRUCTURED_GAMES,
)

router = APIRouter()
logger = logging.getLogger(__name__)

UTC = timezone.utc

# Champs qui ne peuvent JAMAIS être modifiés au niveau d'une occurrence
# individuelle (portée série uniquement : ils affecteraient la récurrence
# elle-même, pas une seule occurrence).
_SERIES_ONLY_FIELDS = {"start_at", "recurrence"}

_EMPTY_COUNTS: dict[str, int] = {"present": 0, "maybe": 0, "absent": 0}

# Types "structurés" : la plateforme (game_label) est une liste fermée
# (STRUCTURED_GAMES) et la map n'est pertinente que si la plateforme
# choisie est "DCS". Jeu libre (jeulibre) : game_label libre, map forcée
# null. Cf. BRIEF_SONNET_ReadyRoom_v0.26 §3.
_STRUCTURED_EVENT_TYPES = {"mission", "entrainement", "campagne"}


def _enforce_game_map_rules(
    event_type: str, game_label: Optional[str], map_name: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """Structurés -> game_label = plateforme fermée (422 sinon) ; map
    conservée seulement si plateforme == DCS. jeulibre -> game_label
    libre, map forcée null."""
    if event_type in _STRUCTURED_EVENT_TYPES:
        if game_label not in STRUCTURED_GAMES:
            raise HTTPException(
                status_code=422,
                detail=f"Plateforme invalide pour {event_type} : {game_label!r}",
            )
        if game_label != "DCS":
            map_name = None
        return game_label, map_name
    return game_label, None


def _occurrence_game_map(event, patch_fields: dict) -> dict:
    """Lot « Les finitions de l'édition » (v1.0103, ARC-16) : `patch_fields`
    complété pour une occurrence. Type, plateforme et carte EFFECTIFS = la
    valeur du patch si la clé y est, sinon celle de `event` ; les règles
    game/map s'y appliquent (leur 422 remonte tel quel) ; si la carte rendue
    diffère de la carte effective, le patch porte `map_name` à cette valeur
    (`None`). La plateforme n'est jamais réécrite."""
    out = dict(patch_fields)
    type_eff = out["type"] if "type" in out else event.type
    label_eff = out["game_label"] if "game_label" in out else event.game_label
    map_eff = out["map_name"] if "map_name" in out else event.map_name
    _, map_rendue = _enforce_game_map_rules(type_eff, label_eff, map_eff)
    if map_rendue != map_eff:
        out["map_name"] = map_rendue
    return out


def _check_recurrence_end(start_at_utc: datetime, recurrence: Optional[dict]) -> None:
    """Lot « Les finitions de l'édition » (v1.0103, ARC-17) : 422 quand la
    règle finit par `until` et que `until` précède la date de début lue en
    REFERENCE_TZ (Europe/Paris). `until` égale à cette date passe ; une fin
    par `count`, sans fin, ou pas de récurrence : rien."""
    if not recurrence:
        return
    end = recurrence.get("end")
    if not end or end.get("type") != "until":
        return
    until = end["until"]
    if not isinstance(until, date):
        until = date.fromisoformat(str(until))
    if start_at_utc.tzinfo is None:
        start_at_utc = start_at_utc.replace(tzinfo=UTC)
    if until < start_at_utc.astimezone(fuseau_reference()).date():
        raise HTTPException(
            status_code=422, detail="La fin de la série précède son début."
        )


def _jour_de_reference(debut: datetime) -> date:
    """Lot « La série juste » (v1.0104) : la DATE d'un début lue en
    REFERENCE_TZ (un début sans fuseau est lu comme UTC, comme en base)."""
    if debut.tzinfo is None:
        debut = debut.replace(tzinfo=UTC)
    return debut.astimezone(fuseau_reference()).date()


def _fin_normalisee(fin: Optional[dict]) -> Optional[tuple]:
    """Lot « La série juste » (v1.0104) : la fin d'une règle sous une forme
    comparable (`until` en texte ISO, que la valeur soit une date ou un
    texte ; `count` en entier)."""
    if not fin:
        return None
    if fin.get("type") == "until":
        return ("until", str(fin.get("until")))
    return (fin.get("type"), int(fin["count"]) if fin.get("count") is not None else None)


def _changement_de_serie(avant: tuple, apres: tuple) -> str:
    """Lot « La série juste » (v1.0104, ARC-15) : ce qu'un changement de
    `(start_at, recurrence)` fait aux réponses à venir. `tout` : la DATE de
    début (REFERENCE_TZ) change, la récurrence apparaît ou disparaît, ou
    `weekdays` / `interval` changent. `fin` : les deux sont récurrentes,
    `weekdays` et `interval` égaux, seule `end` diffère. `rien` : le reste
    (l'heure seule, etc.). Pure : sans base."""
    debut_a, rec_a = avant
    debut_b, rec_b = apres
    rec_a, rec_b = rec_a or None, rec_b or None
    if _jour_de_reference(debut_a) != _jour_de_reference(debut_b):
        return "tout"
    if (rec_a is None) != (rec_b is None):
        return "tout"
    if rec_a is None:
        return "rien"
    jours_a = sorted({int(j) for j in rec_a.get("weekdays", [])})
    jours_b = sorted({int(j) for j in rec_b.get("weekdays", [])})
    if jours_a != jours_b or int(rec_a.get("interval", 1)) != int(rec_b.get("interval", 1)):
        return "tout"
    if _fin_normalisee(rec_a.get("end")) != _fin_normalisee(rec_b.get("end")):
        return "fin"
    return "rien"


def _dates_retirees(event, dates) -> set:
    """Lot « La série juste » (v1.0104) : parmi `dates`, celles qui ne sont
    PAS une occurrence brute de `event` (la règle déjà appliquée) — les dates
    que la règle retire. Pure : sans base."""
    return {d for d in dates if not _raw_occurrence_exists(event, d)}


def _meme_version(updated_at: datetime, version: str) -> bool:
    """Lot « La série juste » (v1.0104, ARC-19) : la chaîne ISO `version`
    désigne-t-elle le MÊME instant que `updated_at` (`Z` et `+00:00` égaux) ?
    Une chaîne illisible, ou sans fuseau, rend faux. Pure : sans base."""
    texte = str(version).strip()
    if texte.endswith(("Z", "z")):
        texte = texte[:-1] + "+00:00"
    # Un `+` brut dans l'adresse est lu comme une espace : `…T15:00:00 00:00` se lit `…T15:00:00+00:00`.
    texte = re.sub(r" (\d{2}:\d{2})$", r"+\1", texte)
    try:
        lue = datetime.fromisoformat(texte)
    except (TypeError, ValueError):
        return False
    if lue.tzinfo is None:
        return False
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    return lue == updated_at


def _premiere_date_touchee(maintenant: datetime, start_at_avant: datetime) -> date:
    """Lot « La série juste » (v1.0104, addendum 1, règle 2.3) : la première
    date dont les réponses sont « à venir » — AUJOURD'HUI (REFERENCE_TZ) si
    l'heure de début de la série AVANT le changement, ce jour-là à Paris,
    n'est pas encore passée ; sinon DEMAIN (une soirée déjà volée garde ses
    réponses). Pure : sans base."""
    if maintenant.tzinfo is None:
        maintenant = maintenant.replace(tzinfo=UTC)
    if start_at_avant.tzinfo is None:
        start_at_avant = start_at_avant.replace(tzinfo=UTC)
    ici = maintenant.astimezone(fuseau_reference())
    if ici.time() < start_at_avant.astimezone(fuseau_reference()).time():
        return ici.date()
    return ici.date() + timedelta(days=1)


def _schedule_digest_refresh_full_safe() -> None:
    """Rafraîchissement digest inconditionnel (bypass fenêtre A1) suite à
    une mutation d'événement (création/édition/suppression) -- lève la
    limite v0.22 (cf. brief v0.23 §2.4). Non bloquant / jamais fatal : une
    panne Discord ne doit jamais faire échouer la mutation. Import différé
    (même motif que le hook présence, cf. app/discord_notify.py)."""
    try:
        from app.discord_notify import schedule_digest_refresh_full

        schedule_digest_refresh_full()
    except Exception:
        logger.exception(
            "Digest Discord : erreur non bloquante lors du hook mutation d'événement"
        )


# --- Hooks miroir live Discord (Lot 2b-2 §5) --------------------------------
#
# Même patron que ci-dessus : import différé (évite le cycle -- cf. brief,
# `app.discord_rsvp` importe déjà `app.events`), try/except large, jamais
# fatal. Un souci Discord ne doit jamais faire échouer une mutation web.


def _schedule_reproject_event_horizon_safe(event_id: UUID) -> None:
    try:
        from app.discord_rsvp import schedule_reproject_event_horizon

        schedule_reproject_event_horizon(event_id)
    except Exception:
        logger.exception(
            "RSVP Discord : erreur non bloquante lors du hook mutation d'événement "
            "(event_id=%s)",
            event_id,
        )


def _schedule_reproject_occurrence_safe(event_id: UUID, occ_date: date) -> None:
    try:
        from app.discord_rsvp import schedule_reproject_occurrence

        schedule_reproject_occurrence(event_id, occ_date)
    except Exception:
        logger.exception(
            "RSVP Discord : erreur non bloquante lors du hook occurrence "
            "(event_id=%s occ_date=%s)",
            event_id,
            occ_date,
        )


def _schedule_delete_event_messages_safe(pairs: list[tuple[str, str]]) -> None:
    try:
        from app.discord_rsvp import schedule_delete_event_messages

        schedule_delete_event_messages(pairs)
    except Exception:
        logger.exception(
            "RSVP Discord : erreur non bloquante lors du hook suppression d'événement"
        )


# --- Helpers de sérialisation -----------------------------------------------


def _event_to_dict(event: Event) -> dict:
    return {
        "id": str(event.id),
        "type": event.type,
        "game_label": event.game_label,
        "map_name": event.map_name,
        "title": event.title,
        "description": event.description,
        "start_at": event.start_at,
        "duration_min": event.duration_min,
        "recurrence": event.recurrence,
        "created_by": str(event.created_by),
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


def _occ_to_dict(occ: Occurrence, counts: dict, created_at: datetime | None = None) -> dict:
    c = counts.get((occ.event_id, occ.occ_date), _EMPTY_COUNTS)
    return {
        "event_id": occ.event_id,
        "occ_date": occ.occ_date,
        "start_at_utc": occ.start_at_utc,
        "type": occ.type,
        "game_label": occ.game_label,
        "map_name": occ.map_name,
        "title": occ.title,
        "description": occ.description,
        "duration_min": occ.duration_min,
        "recurring": occ.recurring,
        "is_override": occ.is_override,
        # Ajouté au Lot 3b (contrat API v2) : id du créateur, déjà porté par
        # l'Occurrence depuis `expand()` (cf. app/recurrence.py), lui-même
        # renseigné depuis `event.created_by`.
        "created_by": occ.created_by,
        # v0.36 (tag "NOUVEAU") : created_at de l'Event PARENT, pas de
        # l'occurrence (qui n'en a pas de propre). Fourni par l'appelant,
        # qui a déjà l'Event en mémoire (_load_events_and_overrides ou
        # `db.get(Event, ...)`) -- volontairement PAS porté par la
        # dataclass Occurrence (cf. brief : ne pas modifier recurrence.py).
        "created_at": created_at,
        "presence_counts": c,
    }


def _window_upper_bound_utc(to_date: date) -> datetime:
    """Borne haute large (UTC) pour le filtre SQL grossier : un événement
    dont l'ancre est postérieure à `to_date` (n'importe quel fuseau) ne peut
    générer aucune occurrence dans la fenêtre. Le filtrage précis (jours,
    heures REFERENCE_TZ, until/count, overrides) est fait par `expand()`."""
    return datetime.combine(to_date + timedelta(days=1), dt_time.min, tzinfo=UTC)


def _window_lower_bound_utc(from_date: date) -> datetime:
    """Borne basse large (UTC), pendant de `_window_upper_bound_utc` : minuit
    UTC du jour `from_date - 1 jour`. Un évènement sans récurrence dont
    l'ancre précède cette borne ne peut pas tomber dans la fenêtre (marge d'un
    jour pour le fuseau) ; le filtrage précis reste fait par `expand()`."""
    return datetime.combine(from_date - timedelta(days=1), dt_time.min, tzinfo=UTC)


async def _load_events_and_overrides(
    db: AsyncSession, from_date: date, to_date: date
) -> tuple[list[Event], dict]:
    """Évènements pouvant toucher [from_date, to_date], au grossier. Borne
    haute : ancre avant `to_date + 1 jour` (UTC). Borne basse (v1.0103,
    ARC-24) : on ne charge plus un évènement sans récurrence (NULL SQL ou
    `null` JSON) dont `start_at` précède `_window_lower_bound_utc(from_date)`,
    ni une série finie par `until` dont `until` précède `from_date` ; une
    série finie par `count` ou sans fin se charge comme avant."""
    upper_bound = _window_upper_bound_utc(to_date)
    lower_bound = _window_lower_bound_utc(from_date)
    sans_recurrence = or_(
        Event.recurrence.is_(None), func.jsonb_typeof(Event.recurrence) == "null"
    )
    fin_until = Event.recurrence["end"]["type"].astext == "until"
    until_passee = case(
        (fin_until, Event.recurrence["end"]["until"].astext.cast(Date) < from_date),
        else_=False,
    )
    ecarte = or_(
        and_(sans_recurrence, Event.start_at < lower_bound),
        and_(not_(sans_recurrence), until_passee),
    )
    result = await db.execute(
        select(Event).where(Event.start_at < upper_bound, not_(func.coalesce(ecarte, False)))
    )
    events = list(result.scalars().all())

    overrides_by_event: dict[UUID, dict[date, OccurrenceOverride]] = defaultdict(dict)
    if events:
        event_ids = [e.id for e in events]
        overrides_result = await db.execute(
            select(OccurrenceOverride).where(
                OccurrenceOverride.event_id.in_(event_ids),
                OccurrenceOverride.occ_date >= from_date,
                OccurrenceOverride.occ_date <= to_date,
            )
        )
        for ov in overrides_result.scalars().all():
            overrides_by_event[ov.event_id][ov.occ_date] = ov

    return events, overrides_by_event


async def _event_overrides_map(
    db: AsyncSession, event_id: UUID, from_date: date, to_date: date
) -> dict[date, OccurrenceOverride]:
    """Overrides d'UN seul événement sur une fenêtre — évite de charger
    toute la table comme le fait `_load_events_and_overrides` (usage
    calendrier). Introduit en v0.80 pour le RSVP série."""
    rows = await db.execute(
        select(OccurrenceOverride).where(
            OccurrenceOverride.event_id == event_id,
            OccurrenceOverride.occ_date >= from_date,
            OccurrenceOverride.occ_date <= to_date,
        )
    )
    return {ov.occ_date: ov for ov in rows.scalars().all()}


async def _presence_counts(
    db: AsyncSession, event_ids: list[UUID], from_date: date, to_date: date
) -> dict[tuple[str, date], dict[str, int]]:
    """Une seule requête agrégée — pas de N+1 (cf. vigilance brief)."""
    if not event_ids:
        return {}
    result = await db.execute(
        select(
            Presence.event_id,
            Presence.occ_date,
            Presence.state,
            func.count().label("n"),
        )
        .where(
            Presence.event_id.in_(event_ids),
            Presence.occ_date >= from_date,
            Presence.occ_date <= to_date,
        )
        .group_by(Presence.event_id, Presence.occ_date, Presence.state)
    )
    counts: dict[tuple[str, date], dict[str, int]] = defaultdict(
        lambda: {"present": 0, "maybe": 0, "absent": 0}
    )
    for event_id, occ_date, state, n in result.all():
        counts[(str(event_id), occ_date)][state] = n
    return counts


async def _mes_reponses(
    db: AsyncSession, user: dict, event_ids: list[UUID], from_date: date, to_date: date
) -> dict[tuple[str, date], str]:
    """Lot « Ma réponse sur la Planche » (v1.0073, ARU-20) : la réponse du demandeur
    par occurrence, en une seule requête ; `{}` sans requête pour un invité."""
    if user.get("invite"):
        return {}
    result = await db.execute(
        select(Presence.event_id, Presence.occ_date, Presence.state).where(
            Presence.profile_id == int(user["id"]),
            Presence.event_id.in_(event_ids),
            Presence.occ_date >= from_date,
            Presence.occ_date <= to_date,
        )
    )
    return {(str(event_id), occ_date): state for event_id, occ_date, state in result.all()}


def _escape_strip_token(token: str) -> str:
    """Échappement d'un token de préfixe (matcher partagé §3 du brief
    v0.35) : espaces littéraux tolérés en \\s* (ex. "1stEAW" == "1st EAW")."""
    escaped = re.sub(r"([.^$*+?{}\[\]()|\\-])", r"\\\1", token.strip())
    return re.sub(r"\s+", r"\\s*", escaped)


async def _build_name_strip_regex(db: AsyncSession) -> Optional[re.Pattern[str]]:
    """Regex unique construite depuis get_name_strip_tokens (wing +
    escadrilles, lues en base -- Lot 2.2b, cf. brief §7). None si aucun
    token configuré (no-op)."""
    tokens = await get_name_strip_tokens(db)
    if not tokens:
        return None
    alternation = "|".join(_escape_strip_token(t) for t in tokens)
    pattern = rf"^\s*\[?\s*(?:{alternation})\s*\]?\s*\|?\s*"
    return re.compile(pattern, re.IGNORECASE)


def _callsign(name: str, rx: Optional[re.Pattern[str]]) -> str:
    """Retire les préfixes CONNUS (wing/escadrille) d'un nom affiché, en
    boucle (double préfixe type "[1st EAW] BRAVO-22 | X"). Lot « Polish du
    Centre » : la boucle n'a plus de limite de passes -- tant que le retrait
    change le nom et que le nom n'est pas vide --, comme `callsign()` de
    `app.js` : le serveur et l'écran retirent les préfixes de la même façon.
    Fallback = nom d'origine si le résultat serait vide ou si aucun regex n'est
    fourni."""
    if not name or rx is None:
        return name or ""
    out = name
    while out:
        stripped = rx.sub("", out)
        if stripped == out:
            break
        out = stripped
    out = out.strip()
    return out or name


async def _presence_names(
    db: AsyncSession, event_ids: list[UUID], from_date: date, to_date: date
) -> dict[tuple[str, date], dict[str, list[str]]]:
    """Noms des inscrits par occurrence et par état, en ORDRE D'INSCRIPTION
    (Presence.created_at -- dette (2), cf. brief Lot 2b-1 étape 5 ; avant ce
    lot, triait sur updated_at qui bouge à chaque changement d'état). Nom =
    global_name sinon username, ALLÉGÉ des préfixes wing/escadrille CONNUS
    (callsign, cf. brief v0.35 §5). Une requête."""
    if not event_ids:
        return {}
    result = await db.execute(
        select(
            Presence.event_id, Presence.occ_date, Presence.state,
            func.coalesce(Profile.global_name, Profile.username).label("name"),
        )
        .join(Profile, Profile.id == Presence.profile_id)
        .where(
            Presence.event_id.in_(event_ids),
            Presence.occ_date >= from_date,
            Presence.occ_date <= to_date,
        )
        .order_by(Presence.created_at.asc())
    )
    strip_rx = await _build_name_strip_regex(db)
    names: dict[tuple[str, date], dict[str, list[str]]] = defaultdict(
        lambda: {"present": [], "maybe": [], "absent": []}
    )
    for event_id, occ_date, state, name in result.all():
        names[(str(event_id), occ_date)][state].append(_callsign(name, strip_rx))
    return names


def _raw_occurrence_exists(event: Event, occ_date: date) -> bool:
    """L'occurrence `occ_date` appartient-elle à la règle brute de la série
    (indépendamment de tout override existant) ? Utilisé pour valider les
    PATCH/DELETE `scope=occurrence` : on ne peut modifier/annuler qu'une
    date réellement produite par la récurrence."""
    try:
        dates = raw_occurrence_dates(event, occ_date, occ_date)
    except (RecurrenceWindowTooLarge, UnsupportedRecurrenceRule):
        return False
    return len(dates) > 0


async def _effective_occurrence(
    db: AsyncSession, event: Event, occ_date: date
) -> tuple[Optional[Occurrence], Optional[OccurrenceOverride]]:
    """Occurrence EFFECTIVE (override réel appliqué) pour ce jour précis.
    Renvoie (None, override) si l'occurrence n'existe pas ou est annulée —
    utilisé pour le détail et pour valider un RSVP."""
    result = await db.execute(
        select(OccurrenceOverride).where(
            OccurrenceOverride.event_id == event.id,
            OccurrenceOverride.occ_date == occ_date,
        )
    )
    override = result.scalar_one_or_none()
    overrides_map = {occ_date: override} if override else {}
    try:
        occs = expand(event, overrides_map, occ_date, occ_date)
    except (RecurrenceWindowTooLarge, UnsupportedRecurrenceRule):
        return None, override
    return (occs[0] if occs else None), override


# --- GET /api/events/{id} (Event brut, Lot 4 §1) ---------------------------


@router.get("/events/{event_id}")
async def get_event(
    event_id: UUID,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Event brut (pas l'occurrence effective) — sert à pré-remplir le
    formulaire d'édition (date/heure/récurrence de la SÉRIE), cf. brief
    Lot 4 §1. Lecture ouverte à tout membre authentifié (comme le reste
    de `/api/events`), pas de restriction `can_edit_event` ici : c'est une
    lecture, pas une mutation."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    return _event_to_dict(event)


# --- GET /api/events ---------------------------------------------------


@router.get("/events")
async def list_events(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        check_window(from_, to)
    except RecurrenceWindowTooLarge as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    events, overrides_by_event = await _load_events_and_overrides(db, from_, to)
    if not events:
        return []

    all_occurrences: list[Occurrence] = []
    for event in events:
        try:
            all_occurrences.extend(
                expand(event, overrides_by_event.get(event.id, {}), from_, to)
            )
        except UnsupportedRecurrenceRule:
            continue  # règle inconnue : ignorée plutôt que de faire échouer tout /api/events

    if not all_occurrences:
        return []

    occ_event_ids = list({UUID(o.event_id) for o in all_occurrences})
    counts = await _presence_counts(db, occ_event_ids, from_, to)
    # Lot « Ma réponse sur la Planche » : la réponse du demandeur (`my_state`).
    mes_reponses = await _mes_reponses(db, user, occ_event_ids, from_, to)
    # v0.36 (tag "NOUVEAU") : map depuis les events déjà chargés ci-dessus,
    # aucune requête supplémentaire.
    created_at_by_event = {str(e.id): e.created_at for e in events}

    all_occurrences.sort(key=lambda o: o.start_at_utc)
    return [
        {
            **_occ_to_dict(o, counts, created_at_by_event.get(o.event_id)),
            "my_state": mes_reponses.get((o.event_id, o.occ_date)),
        }
        for o in all_occurrences
    ]


# --- POST /api/events ---------------------------------------------------


@router.post("/events", status_code=201)
async def create_event(
    body: EventCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await can_create_event(db, user):
        raise HTTPException(status_code=403, detail="Droit de création d'événement requis")

    start_at_utc = body.start_at.astimezone(UTC)
    recurrence_dict = (
        body.recurrence.model_dump(mode="json") if body.recurrence else None
    )
    game_label, map_name = _enforce_game_map_rules(
        body.type.value, body.game_label, body.map_name
    )
    _check_recurrence_end(start_at_utc, recurrence_dict)

    event = Event(
        type=body.type.value,
        game_label=game_label,
        map_name=map_name,
        title=body.title,
        description=body.description,
        start_at=start_at_utc,
        duration_min=body.duration_min,
        recurrence=recurrence_dict,
        created_by=int(user["id"]),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Diffusion APRÈS commit (jamais avant, cf. vigilance brief Lot 3a) :
    # pas d'occ_date précise pour une mutation de série entière.
    publish_invalidate("events", str(event.id))
    _schedule_digest_refresh_full_safe()
    _schedule_reproject_event_horizon_safe(event.id)

    return _event_to_dict(event)


# --- PATCH /api/events/{id} ----------------------------------------------


@router.patch("/events/{event_id}")
async def patch_event(
    event_id: UUID,
    body: EventPatchBody,
    scope: Literal["series", "occurrence"] = Query(...),
    occ_date: Optional[date] = Query(default=None),
    # Lot « La série juste » (v1.0104) : `version` = l'`updated_at` que
    # l'éditeur a lu (absent : pas de contrôle) ; `effacer` = confirmer
    # l'effacement des réponses que le changement de série emporte.
    version: Optional[str] = Query(default=None),
    effacer: bool = Query(default=False),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Lot « La série juste » (v1.0104, addendum 1) : la ligne se lit avec un verrou — deux requêtes portant la
    # même version ne passent pas toutes deux le contrôle : la seconde attend, relit la version avancée et reçoit
    # le 409 `modifie_entre_temps`.
    event = await db.get(Event, event_id, with_for_update=True)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")

    if not await can_edit_event(db, user, event.created_by):
        raise HTTPException(
            status_code=403, detail="Droit insuffisant pour modifier cet événement"
        )

    provided = body.model_dump(exclude_unset=True)

    # Champs obligatoires de l'événement : jamais vidables via patch partiel.
    for required in ("type", "title", "start_at"):
        if required in provided and provided[required] is None:
            raise HTTPException(
                status_code=422, detail=f"Le champ '{required}' ne peut pas être vidé"
            )

    if scope == "series":
        # Lot « La série juste » (v1.0104, ARC-19) : l'évènement a été
        # modifié depuis la lecture de l'éditeur -> 409, rien n'est écrit.
        if version is not None and not _meme_version(event.updated_at, version):
            raise HTTPException(status_code=409, detail={"code": "modifie_entre_temps"})
        # Le couple d'avant, pris AVANT d'appliquer les champs.
        avant = (event.start_at, event.recurrence)
        if "type" in provided:
            event.type = body.type.value
        if "game_label" in provided:
            event.game_label = body.game_label
        if "map_name" in provided:
            event.map_name = body.map_name
        if "title" in provided:
            event.title = body.title
        if "description" in provided:
            event.description = body.description if body.description is not None else ""
        if "duration_min" in provided:
            event.duration_min = body.duration_min
        if "start_at" in provided:
            event.start_at = body.start_at.astimezone(UTC)
        if "recurrence" in provided:
            event.recurrence = (
                body.recurrence.model_dump(mode="json") if body.recurrence else None
            )

        # Réapplique les règles game/map sur le type EFFECTIF final (pris
        # en compte même si seul `type` a changé, sans re-fournir l'autre
        # champ) : un changement de type structuré sans plateforme fournie
        # lèvera 422 (le front envoie toujours la plateforme).
        event.game_label, event.map_name = _enforce_game_map_rules(
            event.type, event.game_label, event.map_name
        )
        # Lot « Les finitions de l'édition » (v1.0103, ARC-17) : sur les
        # valeurs effectives, avant le commit.
        _check_recurrence_end(event.start_at, event.recurrence)

        # Lot « La série juste » (v1.0104, ARC-15) : une série dont la date,
        # les jours ou le rythme changent efface ses réponses À VENIR (le
        # passé n'est jamais touché) ; une fin avancée n'efface que les dates
        # qu'elle retire. Sans `effacer`, 409 qui compte, rien d'écrit.
        changement = _changement_de_serie(avant, (event.start_at, event.recurrence))
        if changement != "rien":
            a_partir_du = _premiere_date_touchee(datetime.now(UTC), avant[0])
            reponses = dict(
                (
                    await db.execute(
                        select(Presence.occ_date, func.count())
                        .where(
                            Presence.event_id == event.id,
                            Presence.occ_date >= a_partir_du,
                        )
                        .group_by(Presence.occ_date)
                    )
                ).all()
            )
            dates_ov = dict(
                (
                    await db.execute(
                        select(OccurrenceOverride.occ_date, func.count())
                        .where(
                            OccurrenceOverride.event_id == event.id,
                            OccurrenceOverride.occ_date >= a_partir_du,
                        )
                        .group_by(OccurrenceOverride.occ_date)
                    )
                ).all()
            )
            if changement == "fin":
                retirees = _dates_retirees(event, set(reponses) | set(dates_ov))
                reponses = {d: n for d, n in reponses.items() if d in retirees}
                dates_ov = {d: n for d, n in dates_ov.items() if d in retirees}
            n_reponses, n_dates = sum(reponses.values()), sum(dates_ov.values())
            if n_reponses or n_dates:
                if not effacer:
                    await db.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "reponses_a_effacer",
                            "reponses": n_reponses,
                            "dates": n_dates,
                        },
                    )
                # Effacement puis enregistrement, dans la même transaction.
                if reponses:
                    await db.execute(
                        delete(Presence).where(
                            Presence.event_id == event.id,
                            Presence.occ_date.in_(list(reponses)),
                        )
                    )
                if dates_ov:
                    await db.execute(
                        delete(OccurrenceOverride).where(
                            OccurrenceOverride.event_id == event.id,
                            OccurrenceOverride.occ_date.in_(list(dates_ov)),
                        )
                    )

        await db.commit()
        await db.refresh(event)
        publish_invalidate("events", str(event.id))
        _schedule_digest_refresh_full_safe()
        _schedule_reproject_event_horizon_safe(event.id)
        return _event_to_dict(event)

    # scope == "occurrence"
    if occ_date is None:
        raise HTTPException(
            status_code=400, detail="Paramètre 'occ_date' requis pour scope=occurrence"
        )

    # Lot « La série juste » (v1.0104, ARC-19) : le même contrôle de version
    # (avant les contrôles de date, qu'une édition de série concurrente peut
    # avoir rendus faux : le 409 dit alors la vraie raison).
    if version is not None and not _meme_version(event.updated_at, version):
        raise HTTPException(status_code=409, detail={"code": "modifie_entre_temps"})

    forbidden = _SERIES_ONLY_FIELDS & provided.keys()
    if forbidden:
        raise HTTPException(
            status_code=400,
            detail=f"Champs non modifiables au niveau occurrence: {sorted(forbidden)}",
        )

    if not _raw_occurrence_exists(event, occ_date):
        raise HTTPException(
            status_code=404, detail="Cette occurrence n'appartient pas à la série"
        )

    patch_fields = {k: v for k, v in provided.items() if k not in _SERIES_ONLY_FIELDS}
    if patch_fields.get("type") is not None:
        patch_fields["type"] = body.type.value
    # Lot « Les finitions de l'édition » (v1.0103, ARC-16) : la carte suit la
    # plateforme et le type effectifs de l'occurrence.
    patch_fields = _occurrence_game_map(event, patch_fields)

    stmt = pg_insert(OccurrenceOverride).values(
        event_id=event.id, occ_date=occ_date, status="modified", patch=patch_fields
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[OccurrenceOverride.event_id, OccurrenceOverride.occ_date],
        set_={"status": "modified", "patch": patch_fields},
    )
    await db.execute(stmt)
    # Lot « La série juste » (v1.0104, ARC-19) : une date modifiée est une
    # modification de l'évènement — son `updated_at` avance.
    event.updated_at = func.now()
    await db.commit()
    publish_invalidate("events", str(event.id), occ_date.isoformat())
    _schedule_digest_refresh_full_safe()
    _schedule_reproject_occurrence_safe(event.id, occ_date)

    occ, _ = await _effective_occurrence(db, event, occ_date)
    return _occ_to_dict(occ, counts={}, created_at=event.created_at)


# --- DELETE /api/events/{id} ----------------------------------------------


@router.delete("/events/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    scope: Literal["series", "occurrence"] = Query(...),
    occ_date: Optional[date] = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")

    if not await can_edit_event(db, user, event.created_by):
        raise HTTPException(
            status_code=403, detail="Droit insuffisant pour supprimer cet événement"
        )

    if scope == "series":
        # Capture AVANT toute suppression (cf. brief Lot 2b-2 §5) : la ligne
        # `occurrence_messages` a `ondelete="CASCADE"` sur `event_id` --
        # une fois l'event supprimé, les (channel_id, message_id) seraient
        # perdus. On les lit ici pour pouvoir purger les messages Discord
        # après coup.
        captured_messages = (
            await db.execute(
                select(OccurrenceMessage.channel_id, OccurrenceMessage.message_id).where(
                    OccurrenceMessage.event_id == event.id
                )
            )
        ).all()

        # Cascade EXPLICITE (pas de FK ondelete en base pour presences/
        # overrides) : présences puis overrides puis la série elle-même,
        # dans une seule transaction. `occurrence_messages` est purgée par
        # le ON DELETE CASCADE de sa propre FK au DELETE Event ci-dessous.
        await db.execute(delete(Presence).where(Presence.event_id == event.id))
        await db.execute(
            delete(OccurrenceOverride).where(OccurrenceOverride.event_id == event.id)
        )
        await db.execute(delete(Event).where(Event.id == event.id))
        await db.commit()
        publish_invalidate("events", str(event.id))
        _schedule_digest_refresh_full_safe()
        _schedule_delete_event_messages_safe(
            [(row.channel_id, row.message_id) for row in captured_messages]
        )
        return None

    # scope == "occurrence"
    if occ_date is None:
        raise HTTPException(
            status_code=400, detail="Paramètre 'occ_date' requis pour scope=occurrence"
        )

    if not _raw_occurrence_exists(event, occ_date):
        raise HTTPException(
            status_code=404, detail="Cette occurrence n'appartient pas à la série"
        )

    stmt = pg_insert(OccurrenceOverride).values(
        event_id=event.id, occ_date=occ_date, status="cancelled", patch=None
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[OccurrenceOverride.event_id, OccurrenceOverride.occ_date],
        set_={"status": "cancelled", "patch": None},
    )
    await db.execute(stmt)
    # Lot « La série juste » (v1.0104, addendum 1) : annuler une date est une modification de l'évènement — son
    # `updated_at` avance, comme au PATCH d'une date.
    event.updated_at = func.now()
    await db.commit()
    publish_invalidate("events", str(event.id), occ_date.isoformat())
    _schedule_digest_refresh_full_safe()
    # Occurrence annulée -> reproject verra `occurrence=None` et supprimera
    # le message (la ligne `occurrence_messages` existe encore ici, pas de
    # cascade sur une simple annulation d'occurrence).
    _schedule_reproject_occurrence_safe(event.id, occ_date)
    return None


# --- GET /api/events/{id}/occurrences/{occ_date} ---------------------------


def trier_roster(roster: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Lot « La Planification en grand écran » (v1.0077) : chaque état du roster (`present`, `maybe`, `absent`) trié
    par nom affiché sans casse, puis par `profile_id` — la requête n'a pas d'ordre, et la fiche montrait les mêmes
    pilotes dans un ordre qui changeait d'un affichage à l'autre. Un nom absent compte comme vide."""
    return {
        etat: sorted(
            roster.get(etat, []),
            key=lambda p: ((p.get("name") or "").casefold(), str(p.get("profile_id"))),
        )
        for etat in ("present", "maybe", "absent")
    }


@router.get("/events/{event_id}/occurrences/{occ_date}")
async def get_occurrence_detail(
    event_id: UUID,
    occ_date: date,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")

    occ, _ = await _effective_occurrence(db, event, occ_date)
    if occ is None:
        raise HTTPException(status_code=404, detail="Occurrence introuvable ou annulée")

    roster_result = await db.execute(
        select(
            Presence.state,
            Profile.id,
            Profile.username,
            Profile.global_name,
            Profile.avatar_hash,
            Profile.squadron,
            Presence.aircraft,
            Presence.mission_types,
        )
        .join(Profile, Profile.id == Presence.profile_id)
        .where(Presence.event_id == event_id, Presence.occ_date == occ_date)
    )
    roster: dict[str, list[dict]] = {"present": [], "maybe": [], "absent": []}
    for (
        state,
        profile_id,
        username,
        global_name,
        avatar_hash,
        squadron,
        aircraft,
        mission_types,
    ) in roster_result.all():
        roster[state].append(
            {
                "profile_id": str(profile_id),
                "name": global_name or username,
                "avatar_hash": avatar_hash,
                # Lot 6 : escadrille + preferences RSVP (SPEC A.4 / B.4).
                "squadron": squadron or "Free Agent",
                "aircraft": aircraft,
                "mission_types": mission_types,
            }
        )

    result = _occ_to_dict(occ, counts={}, created_at=event.created_at)
    # Lot « La série juste » (v1.0104, ARC-19) : la version de la série que
    # lit l'éditeur, renvoyée à l'enregistrement (`version`).
    result["event_updated_at"] = event.updated_at
    result["roster"] = trier_roster(roster)
    return result


# --- Service d'écriture présence (Lot 2b-1 étape 6) ------------------------
#
# Extrait de l'ancienne route `upsert_presence` pour être réutilisable par
# le futur traitement de clic Discord (Lot 2b-2), SANS dupliquer la logique
# (validation occurrence, upsert ON CONFLICT, règle prefs, invalidation SSE,
# hook digest). `UNSET` distingue "non fourni" de "fourni explicitement à
# None" : un simple present/maybe/absent (state-only, chemin Discord) ne
# doit jamais toucher aux colonnes aircraft/mission_types (garantit D5 par
# construction, sans dépendre de `model_fields_set` qui n'existe que côté
# Pydantic/route web).


class _UnsetType:
    def __repr__(self) -> str:  # pragma: no cover -- confort de debug
        return "UNSET"


UNSET = _UnsetType()


async def set_presence_state(
    db: AsyncSession,
    *,
    event_id: UUID,
    occ_date: date,
    profile_id: int,
    state: str,
    aircraft: list[str] | None | _UnsetType = UNSET,
    mission_types: list[str] | None | _UnsetType = UNSET,
) -> None:
    """Écrit l'état RSVP d'un profil pour une occurrence — logique
    STRICTEMENT identique à l'ancienne route `upsert_presence` (cf. brief
    Lot 2b-1 §2 étape 6) : valide l'occurrence effective, upsert
    `Presence` via `ON CONFLICT`, applique la règle prefs (SPEC B.4 :
    aircraft/mission_types forcés à `None` si le type d'événement ne les
    autorise pas, sinon touchés uniquement si explicitement fournis),
    publie l'invalidation SSE, et programme le refresh digest (hook non
    bloquant, jamais fatal).

    `aircraft`/`mission_types` par défaut = sentinelle `UNSET` → chemin
    **state-only** (celui qu'utilisera Discord au Lot 2b-2) : ces colonnes
    ne sont alors jamais touchées à l'upsert.

    Lève `HTTPException(404)` si l'événement ou l'occurrence est
    introuvable/annulée (même contrat que l'ancienne route web).
    """
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")

    occ, _ = await _effective_occurrence(db, event, occ_date)
    if occ is None:
        raise HTTPException(
            status_code=404, detail="Occurrence inexistante ou annulée"
        )

    # Preferences RSVP (SPEC B.4) : acceptees uniquement pour mission/
    # entrainement/campagne. Pour jeulibre (ou tout autre type), on les
    # FORCE a null cote base (jamais de valeur residuelle stockee), quoi
    # que l'appelant fournisse -- pas d'erreur ici : on ignore plutot que
    # de bloquer un simple present/maybe/absent sur un evenement jeu libre.
    prefs_allowed = occ.type in PRESENCE_PREFS_EVENT_TYPES
    aircraft_provided = aircraft is not UNSET
    mission_types_provided = mission_types is not UNSET

    insert_values = {
        "event_id": event_id,
        "occ_date": occ_date,
        "profile_id": profile_id,
        "state": state,
        "aircraft": (aircraft if aircraft_provided else None) if prefs_allowed else None,
        "mission_types": (
            (mission_types if mission_types_provided else None) if prefs_allowed else None
        ),
    }
    update_fields: dict = {"state": state}
    if prefs_allowed:
        # On ne touche aux colonnes de preferences QUE si l'appelant les a
        # explicitement fournies : un simple clic present/maybe/absent
        # (state-only) ne doit jamais effacer une selection deja
        # enregistree.
        if aircraft_provided:
            update_fields["aircraft"] = aircraft
        if mission_types_provided:
            update_fields["mission_types"] = mission_types
    else:
        update_fields["aircraft"] = None
        update_fields["mission_types"] = None

    stmt = pg_insert(Presence).values(**insert_values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Presence.event_id, Presence.occ_date, Presence.profile_id],
        set_=update_fields,
    )
    await db.execute(stmt)
    await db.commit()
    publish_invalidate("presences", str(event_id), occ_date.isoformat())

    # Extension 2a.1 (digest Discord évergreen) : rafraîchissement débouncé
    # du message digest sur changement de présence. Import différé
    # (`app.discord_notify` importe `_load_events_and_overrides`/
    # `_presence_counts` depuis ce module — un import en tête de fichier
    # créerait un cycle au chargement). Non bloquant / jamais fatal (cf.
    # brief §4 + VIGILANCE) : ne doit jamais faire échouer l'écriture RSVP.
    try:
        from app.discord_notify import schedule_digest_refresh

        schedule_digest_refresh(occ_date, str(event_id))
    except Exception:
        logger.exception("Digest Discord : erreur non bloquante lors du hook RSVP")

    # Miroir web -> Discord (Lot 2b-2 §5, déjà éprouvé manuellement) : le
    # message Discord de cette occurrence doit refléter le RSVP fait
    # depuis le portail.
    _schedule_reproject_occurrence_safe(event_id, occ_date)


# --- v0.80 -- RSVP à l'échelle de la série (`scope=series`) ----------------
#
# Matérialisation (une ligne Presence par occurrence effective), jamais de
# "défaut de série" appliqué à la lecture -- cf. brief v0.80 §2.1. Fenêtre
# bornée [max(occ_date, today), +PRESENCE_SERIES_HORIZON_DAYS] -- jamais de
# rétroactivité (§2.2). Un seul bulk upsert par groupe (prefs autorisées /
# non autorisées), un seul commit, et exactement trois hooks de bord
# (SSE, digest, reproject horizon Discord) -- jamais en boucle (§3.5).


async def set_presence_series(
    db: AsyncSession,
    *,
    event_id: UUID,
    occ_date: date,
    profile_id: int,
    state: str,
    aircraft: list[str] | None | _UnsetType = UNSET,
    mission_types: list[str] | None | _UnsetType = UNSET,
) -> list[date]:
    """v0.80 — applique un état RSVP à TOUTES les occurrences effectives de
    la série dans [max(occ_date, today), +PRESENCE_SERIES_HORIZON_DAYS].
    Retourne les dates réellement écrites (triées).

    Écrit en UN bulk upsert (jamais de boucle par occurrence) et ne
    déclenche les effets de bord Discord/SSE qu'UNE seule fois — cf. §3.5.
    Lève 404 si l'événement est introuvable, 400 s'il n'est pas récurrent.
    """
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Événement introuvable")
    if not event.recurrence:
        raise HTTPException(status_code=400, detail="Événement non récurrent")

    today = datetime.now(fuseau_reference()).date()
    from_date = max(occ_date, today)
    to_date = from_date + timedelta(days=settings.PRESENCE_SERIES_HORIZON_DAYS)

    overrides = await _event_overrides_map(db, event_id, from_date, to_date)
    occs = expand(event, overrides, from_date, to_date)
    if not occs:
        return []

    aircraft_provided = aircraft is not UNSET
    mission_types_provided = mission_types is not UNSET

    prefs_allowed_occs = [o for o in occs if o.type in PRESENCE_PREFS_EVENT_TYPES]
    prefs_denied_occs = [o for o in occs if o.type not in PRESENCE_PREFS_EVENT_TYPES]

    if prefs_allowed_occs:
        insert_values = [
            {
                "event_id": event_id,
                "occ_date": o.occ_date,
                "profile_id": profile_id,
                "state": state,
                "aircraft": aircraft if aircraft_provided else None,
                "mission_types": mission_types if mission_types_provided else None,
            }
            for o in prefs_allowed_occs
        ]
        stmt = pg_insert(Presence).values(insert_values)
        update_fields: dict = {"state": stmt.excluded.state}
        if aircraft_provided:
            update_fields["aircraft"] = stmt.excluded.aircraft
        if mission_types_provided:
            update_fields["mission_types"] = stmt.excluded.mission_types
        stmt = stmt.on_conflict_do_update(
            index_elements=[Presence.event_id, Presence.occ_date, Presence.profile_id],
            set_=update_fields,
        )
        await db.execute(stmt)

    if prefs_denied_occs:
        insert_values = [
            {
                "event_id": event_id,
                "occ_date": o.occ_date,
                "profile_id": profile_id,
                "state": state,
                "aircraft": None,
                "mission_types": None,
            }
            for o in prefs_denied_occs
        ]
        stmt = pg_insert(Presence).values(insert_values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[Presence.event_id, Presence.occ_date, Presence.profile_id],
            set_={
                "state": stmt.excluded.state,
                "aircraft": None,
                "mission_types": None,
            },
        )
        await db.execute(stmt)

    await db.commit()

    dates = sorted(o.occ_date for o in occs)

    publish_invalidate("presences", str(event_id), occ_date.isoformat())
    _schedule_digest_refresh_full_safe()
    _schedule_reproject_event_horizon_safe(event_id)

    return dates


# --- PUT /api/presences ---------------------------------------------------


@router.put("/presences")
async def upsert_presence(
    body: PresenceUpsert,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile_id = int(user["id"])

    # Ne transmet aircraft/mission_types que si le client les a
    # explicitement fournis (model_fields_set) -- au-delà, `set_presence_state`
    # applique EXACTEMENT la même règle prefs qu'avant l'extraction (cf.
    # brief étape 6).
    provided = body.model_fields_set
    prefs_kwargs: dict = {}
    if "aircraft" in provided:
        prefs_kwargs["aircraft"] = body.aircraft
    if "mission_types" in provided:
        prefs_kwargs["mission_types"] = body.mission_types

    # v0.80 -- scope=series : aiguillage minimal, réponse dédiée (nombre de
    # dates écrites). Le chemin scope=occurrence (défaut) est strictement
    # inchangé ci-dessous.
    if body.scope == "series":
        dates = await set_presence_series(
            db,
            event_id=body.event_id,
            occ_date=body.occ_date,
            profile_id=profile_id,
            state=body.state.value,
            **prefs_kwargs,
        )
        return {
            "event_id": str(body.event_id),
            "occ_date": body.occ_date,
            "profile_id": str(profile_id),
            "state": body.state.value,
            "scope": "series",
            "applied_dates": [d.isoformat() for d in dates],
            "applied_count": len(dates),
        }

    await set_presence_state(
        db,
        event_id=body.event_id,
        occ_date=body.occ_date,
        profile_id=profile_id,
        state=body.state.value,
        **prefs_kwargs,
    )

    # Comportement web strictement inchangé (cf. brief étape 6) : la
    # réponse reflète l'état RÉELLEMENT persisté (prefs forcées à None si
    # le type d'événement ne les autorise pas) -- relecture légère sur
    # l'index unique existant plutôt que de dupliquer la règle prefs ici.
    row = (
        await db.execute(
            select(Presence.aircraft, Presence.mission_types).where(
                Presence.event_id == body.event_id,
                Presence.occ_date == body.occ_date,
                Presence.profile_id == profile_id,
            )
        )
    ).one()

    return {
        "event_id": str(body.event_id),
        "occ_date": body.occ_date,
        "profile_id": str(profile_id),
        "state": body.state.value,
        "aircraft": row.aircraft,
        "mission_types": row.mission_types,
    }


# --- GET /api/hebdo --------------------------------------------------------


@router.get("/hebdo")
async def hebdo(
    anchor: date = Query(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    week1_monday = anchor - timedelta(days=anchor.weekday())
    week1_sunday = week1_monday + timedelta(days=6)
    week2_monday = week1_monday + timedelta(days=7)
    week2_sunday = week2_monday + timedelta(days=6)

    from_date, to_date = week1_monday, week2_sunday

    events, overrides_by_event = await _load_events_and_overrides(db, from_date, to_date)

    all_occurrences: list[Occurrence] = []
    for event in events:
        try:
            all_occurrences.extend(
                expand(event, overrides_by_event.get(event.id, {}), from_date, to_date)
            )
        except UnsupportedRecurrenceRule:
            continue

    all_occurrences.sort(key=lambda o: o.start_at_utc)

    # v0.36 (tag "NOUVEAU") : map depuis les events déjà chargés ci-dessus.
    created_at_by_event = {str(e.id): e.created_at for e in events}

    # Lot « L'appel » (R184) : un profil archivé sort du hebdo.
    members_result = await db.execute(
        select(Profile)
        .where(Profile.archived_at.is_(None))
        .order_by(Profile.global_name, Profile.username)
    )
    members = [
        {
            "id": str(p.id),
            "name": p.global_name or p.username,
            "avatar_hash": p.avatar_hash,
            # Lot 6 (SPEC A.4) : escadrille exposee dans le hebdo aussi.
            "squadron": p.squadron or "Free Agent",
        }
        for p in members_result.scalars().all()
    ]

    states: dict[tuple[str, date], dict[str, str]] = defaultdict(dict)
    # Lot v0.21 : map parallèle des choix (appareil + types de mission),
    # indépendante de `states` qui doit rester strictement profile_id -> state.
    choices: dict[tuple[str, date], dict[str, dict]] = defaultdict(dict)
    if all_occurrences:
        occ_event_ids = list({UUID(o.event_id) for o in all_occurrences})
        presences_result = await db.execute(
            select(
                Presence.event_id,
                Presence.occ_date,
                Presence.profile_id,
                Presence.state,
                Presence.aircraft,
                Presence.mission_types,
            ).where(
                Presence.event_id.in_(occ_event_ids),
                Presence.occ_date >= from_date,
                Presence.occ_date <= to_date,
            )
        )
        for event_id, occ_date, profile_id, state, aircraft, mission_types in presences_result.all():
            states[(str(event_id), occ_date)][str(profile_id)] = state
            choices[(str(event_id), occ_date)][str(profile_id)] = {
                "aircraft": aircraft or [],
                "mission_types": mission_types or [],
            }

    def _week_payload(start: date, end: date) -> dict:
        occs = [o for o in all_occurrences if start <= o.occ_date <= end]
        occurrences = []
        for o in occs:
            # Le hebdo utilise `states` (état par membre), pas des compteurs
            # agrégés : `presence_counts` y serait de toute façon toujours
            # {0,0,0} (jamais calculé pour cette vue) donc trompeur. On le
            # retire explicitement plutôt que de le laisser à zéro (cf.
            # brief Lot 3a §5). `/api/events` conserve le compteur réel.
            occ_dict = _occ_to_dict(
                o, counts={}, created_at=created_at_by_event.get(o.event_id)
            )
            occ_dict.pop("presence_counts", None)
            occ_dict["states"] = states.get((o.event_id, o.occ_date), {})
            occ_dict["choices"] = choices.get((o.event_id, o.occ_date), {})
            occurrences.append(occ_dict)
        return {"start": start, "end": end, "occurrences": occurrences}

    return {
        "current_week": _week_payload(week1_monday, week1_sunday),
        "next_week": _week_payload(week2_monday, week2_sunday),
        "members": members,
    }
