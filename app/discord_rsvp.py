"""Socle bot REST Discord + interactions signées — Phase 2b (RSVP
interactif), Lot 2b-1. Cf. BRIEF_SONNET_ReadyRoom_Lot2b-1_Socle_Bot_
Interactions.

Isolé de `app/discord_notify.py` (webhook digest, Phase 2a — jamais
touché ici, rollback). Ce module pose uniquement le SOCLE testable sans UI
Discord live :
- vérification de signature Ed25519 des interactions entrantes (7a) ;
- client REST bot minimal (7b) ;
- construction du rendu d'une occurrence (embed + 3 boutons RSVP) (7c) ;
- service de projection idempotent (post/edit/delete du message associé à
  une occurrence, avec purge D7 sur le passé) (7d) ;
- routeur `/discord/interactions` (PING + accusé éphémère sur clic — le
  traitement réel du clic est Lot 2b-2) et un trigger de test à token
  partagé pour poster manuellement (7e).

Tout est no-op silencieux tant que `settings.rsvp_bot_ready` est faux
(flag `DISCORD_RSVP_ENABLED` à `False` par défaut) : aucune exception
fatale, aucun appel réseau.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import connexion_secours, discord_notify, taches
from app import squadron as squadron_module
from app.auth import _app_access_role_ids
from app.config import settings
from app.db import AsyncSessionLocal, get_db
from app.defense import jeton_valide
from app.events import (
    _effective_occurrence,
    _load_events_and_overrides,
    _presence_names,
    set_presence_state,
)
from app.models import Event, OccurrenceMessage, OccurrenceOverride, Profile
from app.recurrence import (
    fuseau_reference,
    Occurrence,
    RecurrenceWindowTooLarge,
    UnsupportedRecurrenceRule,
    expand,
)

logger = logging.getLogger(__name__)

_API_BASE = "https://discord.com/api/v10"

# --- 7c. Rendu d'occurrence -------------------------------------------------

_TYPE_EMOJI: dict[str, str] = {
    "entrainement": "🟩",
    "mission": "🟨",
    "jeulibre": "🟦",
    "campagne": "🟪",
}
_TYPE_LABEL: dict[str, str] = {
    "entrainement": "Entraînement",
    "mission": "Mission",
    "jeulibre": "Jeu libre",
    "campagne": "Campagne",
}
_DAYS_ABBR: list[str] = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"]

# Ambre — même identité visuelle que le digest webhook (Lot 7), dupliqué ici
# à dessein (module isolé, cf. docstring).
_EMBED_COLOR = 14722106

# Roster : nombre max de noms affichés par état avant troncature "… +N"
# (cf. brief §7c — pas de limite Discord stricte ici, mais un roster trop
# long nuirait à la lisibilité du message).
_ROSTER_MAX_NAMES = 15

_ROSTER_ROWS: tuple[tuple[str, str, str], ...] = (
    ("present", "✓", "Présents"),
    ("maybe", "~", "Peut-être"),
    ("absent", "✗", "Absents"),
)

# États RSVP valides dans un custom_id `rsvp:v1:{event_id}:{occ_date}:{state}`
# (Lot 2b-2 §4 étape 1) — mêmes valeurs que RsvpState (app/models.py).
_RSVP_STATES = {"present", "maybe", "absent"}

# Longueur max de la ligne de descriptif sous-texte (cf. brief v0.78 §5a) —
# au-delà, troncature à _DESC_MAX_LEN - 1 caractères + ellipse unique "…".
_DESC_MAX_LEN = 100


def _esc_md(name: str) -> str:
    for ch in ("\\", "*", "_", "~", "`", "|"):
        name = name.replace(ch, "\\" + ch)
    return name


def _format_roster_row(marker: str, label: str, names: list[str]) -> str:
    """Une ligne de roster en sub-text (`-#`). Glyphes texte `✓ ~ ✗`
    (jamais d'emoji Discord ici : les emoji ne rétrécissent PAS dans `-#`
    et cassent l'alignement, cf. brief §7c VIGILANCE)."""
    if not names:
        return f"-# {marker} {label} : —"
    shown = names[:_ROSTER_MAX_NAMES]
    extra = len(names) - len(shown)
    joined = " • ".join(_esc_md(n) for n in shown)
    if extra > 0:
        joined += f" … +{extra}"
    return f"-# {marker} {label} : {joined}"


def _format_description(raw: str) -> str:
    """Normalise le descriptif libre d'une occurrence en une seule ligne
    de sous-texte (cf. brief v0.78 §5a). Retourne une chaîne vide si le
    résultat est vide après normalisation — dans ce cas, aucune ligne ne
    doit être ajoutée par l'appelant."""
    flattened = raw.replace("\r\n", " ").replace("\r", " ").replace("\n", " ").replace("\t", " ")
    collapsed = " ".join(flattened.split()).strip()
    if not collapsed:
        return ""
    if len(collapsed) > _DESC_MAX_LEN:
        collapsed = collapsed[: _DESC_MAX_LEN - 1] + "…"
    return collapsed


def build_occurrence_payload(
    occurrence: Occurrence, names_by_state: dict[str, list[str]]
) -> dict:
    """Construit le payload Discord (embed + 1 action row de 3 boutons)
    pour une occurrence — cf. brief §7c. `names_by_state` : dict
    `{"present": [...], "maybe": [...], "absent": [...]}` déjà ALLÉGÉ des
    préfixes wing/escadrille et trié en ordre d'inscription (réutilise
    `app.events._presence_names`, cf. étape 5)."""
    emoji = _TYPE_EMOJI.get(occurrence.type, "⬜")
    type_label = _TYPE_LABEL.get(occurrence.type, occurrence.type)
    local_dt = occurrence.start_at_utc.astimezone(fuseau_reference())
    day_abbr = _DAYS_ABBR[occurrence.occ_date.weekday()]
    when = f"{day_abbr} {occurrence.occ_date.day:02d} · {local_dt.strftime('%H:%M')}"

    # Plateforme/map (uniquement si structuré/DCS — jeu libre = plateforme
    # seule si renseignée), même règle que le digest webhook (Lot 7).
    parts: list[str] = []
    if occurrence.type == "jeulibre":
        if occurrence.game_label:
            parts.append(occurrence.game_label)
    else:
        if occurrence.game_label:
            parts.append(occurrence.game_label)
        if occurrence.map_name:
            parts.append(occurrence.map_name)
    context = f" — {' · '.join(parts)}" if parts else ""

    header_line = f"{emoji} **{type_label}** · `{when}`{context}"
    roster_lines = [
        _format_roster_row(marker, label, names_by_state.get(state) or [])
        for state, marker, label in _ROSTER_ROWS
    ]
    desc_line = _format_description(occurrence.description)
    body_lines = [header_line]
    if desc_line:
        body_lines.append(f"-# {desc_line}")
    body_lines.append("")
    body_lines.extend(roster_lines)
    embed_body = "\n".join(body_lines)

    embed = {
        "color": _EMBED_COLOR,
        "title": occurrence.title,
        "description": embed_body,
    }

    event_id = occurrence.event_id
    occ_date_iso = occurrence.occ_date.isoformat()
    buttons = [
        {
            "type": 2,
            "style": 3,  # Success
            "label": "Présent",
            "custom_id": f"rsvp:v1:{event_id}:{occ_date_iso}:present",
        },
        {
            "type": 2,
            "style": 2,  # Secondary
            "label": "Peut-être",
            "custom_id": f"rsvp:v1:{event_id}:{occ_date_iso}:maybe",
        },
        {
            "type": 2,
            "style": 4,  # Danger
            "label": "Absent",
            "custom_id": f"rsvp:v1:{event_id}:{occ_date_iso}:absent",
        },
    ]
    if settings.BASE_URL:
        buttons.append(
            {
                "type": 2,
                "style": 5,  # Link — pas de custom_id, aucune interaction générée
                "label": "Portail",
                # Lot « Les liens de la soirée » (v1.0107) : le bouton ouvre la fiche de cette occurrence.
                "url": f"{settings.BASE_URL.rstrip('/')}/#planif/evenement/{event_id}/{occ_date_iso}",
            }
        )

    return {
        "embeds": [embed],
        "components": [{"type": 1, "components": buttons}],
        "allowed_mentions": {"parse": []},  # aucune mention ne notifie (titre/description = texte libre)
    }


# --- 7a. Vérification de signature Ed25519 ----------------------------------


def verify_signature(
    public_key_hex: str, timestamp: str, raw_body: bytes, signature_hex: str
) -> bool:
    """Vérifie la signature Ed25519 d'une interaction Discord entrante (cf.
    brief §7a). `raw_body` DOIT être les octets bruts exacts du corps de
    requête (jamais un JSON re-sérialisé). Ne lève jamais : toute clé/
    signature invalide ou malformée renvoie simplement `False`."""
    try:
        verify_key = VerifyKey(bytes.fromhex(public_key_hex))
        verify_key.verify(timestamp.encode() + raw_body, bytes.fromhex(signature_hex))
        return True
    except (BadSignatureError, ValueError, TypeError):
        return False


# --- 7b. Client REST bot -----------------------------------------------------


async def _bot_request(
    method: str, path: str, *, json_body: Optional[dict] = None
) -> Optional[httpx.Response]:
    """Requête REST bot générique, un seul retry sur 429 (Retry-After lu
    puis attendu), jamais d'exception propagée (cf. brief §7b)."""
    headers = {"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"}
    try:
        async with httpx.AsyncClient(base_url=_API_BASE, timeout=10.0) as client:
            response = await client.request(method, path, json=json_body, headers=headers)
            if response.status_code == 429:
                retry_after_raw = response.headers.get("Retry-After")
                if retry_after_raw is None:
                    try:
                        retry_after_raw = response.json().get("retry_after")
                    except (ValueError, AttributeError):
                        retry_after_raw = None
                try:
                    wait_s = float(retry_after_raw) if retry_after_raw is not None else 1.0
                except (TypeError, ValueError):
                    wait_s = 1.0
                logger.info(
                    "Bot Discord : 429 sur %s %s, retry après %.1fs", method, path, wait_s
                )
                await asyncio.sleep(wait_s)
                response = await client.request(method, path, json=json_body, headers=headers)
            return response
    except httpx.HTTPError as exc:
        logger.warning("Bot Discord : erreur réseau sur %s %s (%s)", method, path, exc)
        return None


async def post_message(channel_id: str, payload: dict) -> Optional[str]:
    """POST d'un nouveau message dans `channel_id`. Retourne le
    `message_id` ou `None` en cas d'échec (jamais fatal). No-op silencieux
    si `settings.rsvp_bot_ready` est faux."""
    if not settings.rsvp_bot_ready:
        return None
    response = await _bot_request("POST", f"/channels/{channel_id}/messages", json_body=payload)
    if response is None:
        return None
    if 200 <= response.status_code < 300:
        try:
            return str(response.json()["id"])
        except (KeyError, ValueError):
            logger.warning("Bot Discord : réponse POST message sans id exploitable")
            return None
    logger.warning("Bot Discord : échec POST message (status=%s)", response.status_code)
    return None


async def edit_message(channel_id: str, message_id: str, payload: dict) -> Optional[bool]:
    """PATCH d'un message existant. `True` = succès, `False` = 404
    (message supprimé à la main — l'appelant doit purger sa ligne de
    suivi), `None` = toute autre erreur non fatale. No-op si le bot n'est
    pas prêt."""
    if not settings.rsvp_bot_ready:
        return None
    response = await _bot_request(
        "PATCH", f"/channels/{channel_id}/messages/{message_id}", json_body=payload
    )
    if response is None:
        return None
    if 200 <= response.status_code < 300:
        return True
    if response.status_code == 404:
        return False
    logger.warning(
        "Bot Discord : échec PATCH message %s (status=%s)", message_id, response.status_code
    )
    return None


async def delete_message(channel_id: str, message_id: str) -> Optional[bool]:
    """DELETE d'un message. 404 = déjà supprimé (considéré succès). Garde
    **token-seule** (`settings.bot_token_present`), volontairement PAS
    `rsvp_bot_ready` : une suppression reçoit `channel_id` en argument, elle
    n'a besoin que du token bot, pas du flag `DISCORD_RSVP_ENABLED` ni du
    salon de notification -- cf. AMENDEMENT_Lot2b-3_Garde_Suppression §B
    (sinon la réconciliation sens `DISCORD_RSVP_ENABLED=false` ne pourrait
    jamais nettoyer les messages par occurrence). `post_message`/
    `edit_message` restent gardées par `rsvp_bot_ready` : on ne PROJETTE la
    surface 2b que si elle est active ; on peut la NETTOYER dès que le
    token est là."""
    if not settings.bot_token_present:
        return None
    response = await _bot_request("DELETE", f"/channels/{channel_id}/messages/{message_id}")
    if response is None:
        return None
    if response.status_code == 404 or 200 <= response.status_code < 300:
        return True
    logger.warning(
        "Bot Discord : échec DELETE message %s (status=%s)", message_id, response.status_code
    )
    return None


# --- 7d. Service de projection -----------------------------------------------


async def _delete_occurrence_message_row(db: AsyncSession, event_id: UUID, occ_date: date) -> None:
    await db.execute(
        delete(OccurrenceMessage).where(
            OccurrenceMessage.event_id == event_id,
            OccurrenceMessage.occ_date == occ_date,
        )
    )
    await db.commit()


def _log_reproject(outcome: str, event_id: UUID, occ_date: date, **extra: object) -> None:
    """Une ligne INFO lisible par passage de `reproject_occurrence` (cf.
    brief Lot 2b-2 §3b) — `docker compose logs` raconte l'histoire sans
    avoir à requêter la base."""
    details = f" ({', '.join(f'{k}={v}' for k, v in extra.items())})" if extra else ""
    logger.info(
        "Discord RSVP reproject: %s — event_id=%s occ_date=%s%s",
        outcome,
        event_id,
        occ_date,
        details,
    )


async def reproject_occurrence(db: AsyncSession, event_id: UUID, occ_date: date) -> None:
    """Projette l'état courant d'une occurrence sur son message Discord
    associé — idempotent (cf. brief §7d). No-op complet si
    `settings.rsvp_bot_ready` est faux (aucune lecture DB de suivi n'est
    même nécessaire dans ce cas : rien à projeter nulle part).

    Depuis le Lot 2b-2 §3b : une ligne INFO par issue (`posted` / `edited`
    / `deleted` / `skipped:past` / `skipped:no-occurrence` /
    `skipped:beyond-horizon` / `failed:post` / `failed:edit`) — le contrat
    de retour (`None`, jamais d'exception) est strictement inchangé."""
    if not settings.rsvp_bot_ready:
        return

    event = await db.get(Event, event_id)
    occurrence = None
    if event is not None:
        occurrence, _ = await _effective_occurrence(db, event, occ_date)

    row = await db.get(OccurrenceMessage, (event_id, occ_date))
    today = datetime.now(fuseau_reference()).date()

    # D7 : occurrence passée OU introuvable/annulée → supprime le message
    # actif (s'il existe) + purge la ligne de suivi. Jamais de post/edit.
    if occ_date < today or occurrence is None:
        if row is not None:
            await delete_message(row.channel_id, row.message_id)
            await _delete_occurrence_message_row(db, event_id, occ_date)
            _log_reproject("deleted", event_id, occ_date)
        else:
            reason = "skipped:past" if occ_date < today else "skipped:no-occurrence"
            _log_reproject(reason, event_id, occ_date)
        return

    horizon_end = today + timedelta(days=settings.DISCORD_RSVP_HORIZON_DAYS)
    if occ_date > horizon_end:
        # Hors horizon futur : ne rien poster (cf. brief §7d). Un message
        # déjà existant (horizon réduit entre deux passages) est laissé
        # tel quel ici — pas de suppression prématurée hors périmètre.
        _log_reproject("skipped:beyond-horizon", event_id, occ_date)
        return

    names_map = await _presence_names(db, [event_id], occ_date, occ_date)
    names_by_state = names_map.get(
        (str(event_id), occ_date), {"present": [], "maybe": [], "absent": []}
    )
    payload = build_occurrence_payload(occurrence, names_by_state)
    channel_id = settings.DISCORD_NOTIFY_CHANNEL_ID

    if row is None:
        message_id = await post_message(channel_id, payload)
        if message_id is None:
            # Échec non fatal : le statut HTTP est déjà en WARNING juste
            # au-dessus (cf. `_bot_request`/`post_message`) ; cette ligne
            # donne l'issue au niveau reproject.
            _log_reproject("failed:post", event_id, occ_date)
            return  # Rien à persister.
        stmt = pg_insert(OccurrenceMessage).values(
            event_id=event_id,
            occ_date=occ_date,
            channel_id=channel_id,
            message_id=message_id,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[OccurrenceMessage.event_id, OccurrenceMessage.occ_date],
            set_={"channel_id": channel_id, "message_id": message_id},
        )
        await db.execute(stmt)
        await db.commit()
        _log_reproject("posted", event_id, occ_date, message_id=message_id)
        return

    result = await edit_message(row.channel_id, row.message_id, payload)
    if result is False:
        # 404 : message supprimé à la main côté Discord. Purge la ligne —
        # un prochain passage repostera si l'occurrence est toujours dans
        # l'horizon (cf. brief §7d). Compté comme "deleted" côté log : le
        # message tracké n'existe plus, la ligne vient d'être nettoyée.
        await _delete_occurrence_message_row(db, event_id, occ_date)
        _log_reproject("deleted", event_id, occ_date, reason="stale-404")
        return
    if result is None:
        # Autre erreur non fatale : déjà en WARNING au-dessus.
        _log_reproject("failed:edit", event_id, occ_date)
        return
    _log_reproject("edited", event_id, occ_date)


# --- Câblage reproject sur les mutations (Lot 2b-2 étape 5) -----------------
#
# Mêmes garanties partout : tâche de fond avec SA PROPRE `AsyncSessionLocal`
# (jamais le `db` de la route, fermé après réponse), non bloquante,
# `rsvp_bot_ready`-gated (no-op total si Phase 2b désactivée), jamais fatale
# (mirroir du hook digest `_schedule_digest_refresh_full_safe`, cf.
# app/events.py).

_reproject_occurrence_pending: set[tuple[str, str]] = set()


async def _debounced_reproject_occurrence(
    event_id: UUID, occ_date: date, key: tuple[str, str]
) -> None:
    try:
        await asyncio.sleep(settings.DISCORD_DIGEST_REFRESH_DEBOUNCE_SECONDS)
        async with AsyncSessionLocal() as db:
            await reproject_occurrence(db, event_id, occ_date)
            await ensure_channel_order(db)
    except Exception:
        logger.exception(
            "RSVP Discord : erreur non bloquante lors du reproject débouncé "
            "(event_id=%s occ_date=%s)",
            event_id,
            occ_date,
        )
    finally:
        _reproject_occurrence_pending.discard(key)


def schedule_reproject_occurrence(event_id: UUID, occ_date: date) -> None:
    """Programme un reproject débouncé d'une occurrence UNIQUE (miroir web
    -> Discord sur mutation ciblée : édition d'occurrence, annulation,
    RSVP web — cf. brief étape 5). Coalesce les rafales via un débounce
    PAR CLÉ `(event_id, occ_date)` (réutilise
    `DISCORD_DIGEST_REFRESH_DEBOUNCE_SECONDS`, même esprit que le débounce
    digest mais par occurrence plutôt qu'un flag global unique, puisque
    plusieurs occurrences distinctes peuvent muter en parallèle)."""
    if not settings.rsvp_bot_ready:
        return
    key = (str(event_id), occ_date.isoformat())
    if key in _reproject_occurrence_pending:
        return  # Un flush déjà en vol pour cette occurrence absorbera la mutation.
    _reproject_occurrence_pending.add(key)
    try:
        taches.lancer(_debounced_reproject_occurrence(event_id, occ_date, key))
    except RuntimeError:
        _reproject_occurrence_pending.discard(key)
        logger.warning(
            "RSVP Discord : impossible de programmer le reproject (pas de loop)"
        )


async def _reproject_event_horizon(event_id: UUID) -> None:
    try:
        async with AsyncSessionLocal() as db:
            event = await db.get(Event, event_id)
            if event is None:
                return
            today = datetime.now(fuseau_reference()).date()
            horizon_end = today + timedelta(days=settings.DISCORD_RSVP_HORIZON_DAYS)

            overrides_result = await db.execute(
                select(OccurrenceOverride).where(
                    OccurrenceOverride.event_id == event_id,
                    OccurrenceOverride.occ_date >= today,
                    OccurrenceOverride.occ_date <= horizon_end,
                )
            )
            overrides_map = {
                ov.occ_date: ov for ov in overrides_result.scalars().all()
            }
            try:
                occurrences = expand(event, overrides_map, today, horizon_end)
            except (RecurrenceWindowTooLarge, UnsupportedRecurrenceRule):
                occurrences = []
            valid_dates = {occ.occ_date for occ in occurrences}

            for occ_date in sorted(valid_dates):
                await reproject_occurrence(db, event_id, occ_date)

            # Auto-cicatrisation (cf. brief étape 5) : une ligne
            # `occurrence_messages` existante dont l'occ_date n'est PLUS
            # dans l'ensemble valide (occurrence retirée par une édition de
            # récurrence) -- `reproject_occurrence` y verra `occurrence
            # None` et supprimera le message + purgera la ligne. Bornée à
            # CET event (≠ roll complet du 2b-3).
            existing_result = await db.execute(
                select(OccurrenceMessage.occ_date).where(
                    OccurrenceMessage.event_id == event_id,
                    OccurrenceMessage.occ_date >= today,
                    OccurrenceMessage.occ_date <= horizon_end,
                )
            )
            existing_dates = {row[0] for row in existing_result.all()}
            for occ_date in sorted(existing_dates - valid_dates):
                await reproject_occurrence(db, event_id, occ_date)

            await ensure_channel_order(db)
    except Exception:
        logger.exception(
            "RSVP Discord : erreur non bloquante lors du reproject horizon "
            "(event_id=%s)",
            event_id,
        )


def schedule_reproject_event_horizon(event_id: UUID) -> None:
    """Programme le reproject de TOUTES les occurrences valides de
    `event_id` dans l'horizon `[today, today+HORIZON]` + auto-cicatrisation
    des messages devenus orphelins (cf. brief étape 5 — création/édition de
    série). Non bloquant, jamais fatal, no-op si le bot RSVP n'est pas
    prêt."""
    if not settings.rsvp_bot_ready:
        return
    try:
        taches.lancer(_reproject_event_horizon(event_id))
    except RuntimeError:
        logger.warning(
            "RSVP Discord : impossible de programmer le reproject horizon "
            "(pas de loop)"
        )


async def _delete_event_messages(pairs: list[tuple[str, str]]) -> None:
    for channel_id, message_id in pairs:
        try:
            await delete_message(channel_id, message_id)
        except Exception:
            logger.exception(
                "RSVP Discord : erreur non bloquante lors de la suppression du "
                "message %s",
                message_id,
            )


def schedule_delete_event_messages(pairs: list[tuple[str, str]]) -> None:
    """Supprime les messages Discord `(channel_id, message_id)` CAPTURÉS
    AVANT la suppression d'un event en cascade (cf. brief étape 5 —
    `ON DELETE CASCADE` purge `occurrence_messages` avant qu'on ait pu lire
    les `message_id`, d'où la capture préalable par l'appelant). Non
    bloquant, jamais fatal, no-op si le bot RSVP n'est pas prêt ou si
    `pairs` est vide."""
    if not settings.rsvp_bot_ready or not pairs:
        return
    try:
        taches.lancer(_delete_event_messages(list(pairs)))
    except RuntimeError:
        logger.warning(
            "RSVP Discord : impossible de programmer la suppression des messages "
            "(pas de loop)"
        )


# --- Lot 2b-3 : roll quotidien global + réconciliation auto-cicatrisante ----


async def reproject_all(db: AsyncSession) -> None:
    """Roll quotidien global (cf. brief Lot 2b-3 §2 étape 2) : reprojette
    l'union de (a) toutes les occurrences valides de tous les events dans
    `[today, today+HORIZON]` (mêmes moteur/fenêtre que `build_two_weeks` :
    `_load_events_and_overrides` + `expand`) et (b) toutes les lignes
    `occurrence_messages` existantes (couvre la suppression D7 des
    occurrences passées et de celles devenues invalides). Dédupliqué par
    `(event_id, occ_date)`. Délègue strictement post/edit/delete à
    `reproject_occurrence` (jamais réimplémenté ici) -- idempotent. No-op
    complet si `settings.rsvp_bot_ready` est faux."""
    if not settings.rsvp_bot_ready:
        return

    today = datetime.now(fuseau_reference()).date()
    horizon_end = today + timedelta(days=settings.DISCORD_RSVP_HORIZON_DAYS)

    events, overrides_by_event = await _load_events_and_overrides(db, today, horizon_end)
    valid_pairs: set[tuple[UUID, date]] = set()
    for event in events:
        try:
            occurrences = expand(
                event, overrides_by_event.get(event.id, {}), today, horizon_end
            )
        except (RecurrenceWindowTooLarge, UnsupportedRecurrenceRule):
            continue
        for occ in occurrences:
            valid_pairs.add((event.id, occ.occ_date))

    existing_result = await db.execute(
        select(OccurrenceMessage.event_id, OccurrenceMessage.occ_date)
    )
    existing_pairs = {(row[0], row[1]) for row in existing_result.all()}

    union_pairs = valid_pairs | existing_pairs

    posted = edited = deleted = 0
    for event_id, occ_date in sorted(union_pairs, key=lambda p: (p[1], str(p[0]))):
        had_row = (await db.get(OccurrenceMessage, (event_id, occ_date))) is not None
        await reproject_occurrence(db, event_id, occ_date)
        has_row = (await db.get(OccurrenceMessage, (event_id, occ_date))) is not None
        if has_row and not had_row:
            posted += 1
        elif not has_row and had_row:
            deleted += 1
        elif has_row and had_row:
            edited += 1

    logger.info("roll: %d posted, %d edited, %d deleted", posted, edited, deleted)

    await ensure_channel_order(db)


# --- v0.77 : ordre chronologique du canal (chantier B) ----------------------
#
# Discord ne permet pas de réordonner des messages déjà publiés : leur ordre
# d'affichage est celui de leur PUBLICATION, immuable. Comme les messages
# sont postés event par event (et non occurrence par occurrence dans l'ordre
# du calendrier), le canal peut se retrouver dans le désordre. On corrige en
# republiant (delete + repost via `reproject_occurrence`) le SUFFIXE divergent
# uniquement -- jamais tout le canal -- pour ne pas repasser tous les messages
# en "non lu" à chaque roll.
#
# Verrou module-level : jamais deux réordonnancements simultanés (le
# réordonnancement republie, ce qui pourrait sinon se chevaucher avec un
# autre passage déclenché en parallèle -- ex. deux rolls rapprochés).

_channel_order_lock = asyncio.Lock()


async def ensure_channel_order(db: AsyncSession) -> None:
    """Aligne l'ordre d'affichage du canal Discord sur l'ordre chronologique
    des occurrences (cf. brief v0.77 chantier B). Appelée UNIQUEMENT en fin
    des opérations de haut niveau qui publient/éditent des messages
    (`schedule_reproject_occurrence`, `schedule_reproject_event_horizon`,
    `reproject_all`) -- JAMAIS depuis `reproject_occurrence` elle-même (cette
    fonction l'appelle, l'inverse créerait une boucle infinie). No-op si le
    bot RSVP n'est pas prêt. Erreurs non fatales (log + abandon) : un échec
    de réordonnancement ne doit jamais casser une écriture web ni le boot."""
    if not settings.rsvp_bot_ready:
        return

    async with _channel_order_lock:
        try:
            result = await db.execute(select(OccurrenceMessage))
            rows = list(result.scalars().all())
            if not rows:
                logger.info("order: ok")
                return

            event_ids = {row.event_id for row in rows}
            events_result = await db.execute(
                select(Event).where(Event.id.in_(event_ids))
            )
            events_map = {e.id: e for e in events_result.scalars().all()}

            # Lignes "ordonnables" uniquement : une occurrence non résolvable
            # (event supprimé, override d'annulation, série modifiée...) est
            # ignorée ici -- c'est `reproject_occurrence` qui la supprimera
            # (cf. brief §4 B1 étape 2).
            orderable: list[tuple[tuple[date, datetime, str], OccurrenceMessage]] = []
            for row in rows:
                event = events_map.get(row.event_id)
                if event is None:
                    continue
                occurrence, _ = await _effective_occurrence(db, event, row.occ_date)
                if occurrence is None:
                    continue
                local_start = occurrence.start_at_utc.astimezone(fuseau_reference())
                chrono_key = (row.occ_date, local_start, str(row.event_id))
                orderable.append((chrono_key, row))

            expected_rows = [pair[1] for pair in sorted(orderable, key=lambda p: p[0])]
            actual_rows = [
                pair[1]
                for pair in sorted(
                    orderable,
                    key=lambda p: (p[1].posted_at, int(p[1].message_id)),
                )
            ]

            def _identity(row: OccurrenceMessage) -> tuple[UUID, date]:
                return (row.event_id, row.occ_date)

            prefix_len = 0
            max_prefix = min(len(expected_rows), len(actual_rows))
            while prefix_len < max_prefix and _identity(
                expected_rows[prefix_len]
            ) == _identity(actual_rows[prefix_len]):
                prefix_len += 1

            divergent = expected_rows[prefix_len:]
            if not divergent:
                logger.info("order: ok")
                return

            # Suffixe divergent uniquement, republié SÉQUENTIELLEMENT (jamais
            # en parallèle, cf. brief §4 B4 -- risque de 429) dans l'ordre
            # chronologique attendu.
            for row in divergent:
                await delete_message(row.channel_id, row.message_id)
                await _delete_occurrence_message_row(db, row.event_id, row.occ_date)
                await reproject_occurrence(db, row.event_id, row.occ_date)

            logger.info("order: resorted %d/%d messages", len(divergent), len(rows))
        except Exception:
            logger.exception(
                "RSVP Discord : erreur non bloquante lors du réordonnancement "
                "du canal"
            )


# Lot « rr-env-epure » : une seule réconciliation à la fois -- le démarrage, la route du roll, la
# boucle de 6 h et les écritures de réglages s'y succèdent au lieu de s'y croiser.
_VERROU_RECONCILIATION = asyncio.Lock()


async def reconcile_discord_surface(db: AsyncSession) -> None:
    """Prend le verrou du module, puis joue `_reconcile_discord_surface` (ci-dessous) : un
    seul corps à la fois, pour tous les appelants."""
    async with _VERROU_RECONCILIATION:
        await _reconcile_discord_surface(db)


async def _reconcile_discord_surface(db: AsyncSession) -> None:
    """Réconciliation auto-cicatrisante (cf. brief Lot 2b-3 §2 étape 4,
    amendée par AMENDEMENT_Lot2b-3_Garde_Suppression) : rend le canal
    cohérent avec UNE SEULE surface active, quel que soit l'historique de
    bascules de `DISCORD_RSVP_ENABLED`. Déclenchée au démarrage (lifespan)
    et à chaque roll (`POST /discord/rsvp/roll`). Jamais fatale -- toute
    erreur est journalisée, aucune n'est propagée."""
    if settings.DISCORD_RSVP_ENABLED:
        # 2b active : purge l'évergreen s'il existe encore (webhook,
        # indépendant du bot), puis assure la présence/cohérence des
        # messages par occurrence.
        try:
            row = await discord_notify._get_digest_row(db)
            if row is not None and row.message_id:
                if settings.DISCORD_WEBHOOK_URL:
                    base = discord_notify._webhook_base_url()
                    await discord_notify._delete_messages(base, [row.message_id])
                await discord_notify._upsert_digest_row(
                    db,
                    message_id=None,
                    pending_delete=list(row.pending_delete or []),
                    week_monday=row.week_monday,
                    window_end=row.window_end,
                )
        except Exception:
            logger.exception(
                "Reconcile Discord : erreur non bloquante lors de la purge de "
                "l'évergreen"
            )
        await reproject_all(db)
        return

    # DISCORD_RSVP_ENABLED = false (2b inactive) : nettoie les messages par
    # occurrence -- garde TOKEN-SEULE (cf. amendement §B/§C) : appel DIRECT
    # à `delete_message` (PAS via `reproject_occurrence`, qui early-return
    # sur `rsvp_bot_ready`, toujours faux ici) -- puis reposte l'évergreen
    # dans tous les cas.
    if not settings.bot_token_present:
        logger.warning(
            "reconcile[false]: DISCORD_BOT_TOKEN absent -- messages par "
            "occurrence potentiellement orphelins (garder le token même en "
            "rollback)."
        )
    else:
        try:
            result = await db.execute(select(OccurrenceMessage))
            rows = list(result.scalars().all())
            for row in rows:
                await delete_message(row.channel_id, row.message_id)
                await _delete_occurrence_message_row(db, row.event_id, row.occ_date)
        except Exception:
            logger.exception(
                "Reconcile Discord : erreur non bloquante lors de la purge des "
                "messages par occurrence"
            )

    try:
        await discord_notify.post_digest(db)
    except Exception:
        logger.exception(
            "Reconcile Discord : erreur non bloquante lors du repost de "
            "l'évergreen"
        )


# --- 7d bis. Le passage quotidien de 6 h (lot « rr-env-epure », R808) --------------


def prochaine_echeance(maintenant: datetime) -> datetime:
    """Pure. Le premier instant STRICTEMENT après `maintenant` (avec fuseau) où il est
    6 h 00 à `REFERENCE_TZ`, rendu en UTC -- l'heure d'été comprise."""
    local = maintenant.astimezone(fuseau_reference())
    jour = local.date()
    echeance = datetime.combine(jour, time(6, 0), tzinfo=fuseau_reference())
    if echeance <= maintenant:
        echeance = datetime.combine(jour + timedelta(days=1), time(6, 0), tzinfo=fuseau_reference())
    return echeance.astimezone(timezone.utc)


async def boucle_quotidienne() -> None:
    """Tâche de fond lancée par le lifespan (`app/main.py`) : sans fin, attend la
    prochaine échéance de 6 h (Paris) puis joue `reconcile_discord_surface` sur sa propre
    session -- ce que faisait la tâche `cron` de la VM par `POST /discord/rsvp/roll`, qui
    reste pour le déclenchement à la main. Jamais fatale : une erreur se journalise. Le
    sommeil se découpe (une heure au plus) et se reprend tant que l'échéance n'est pas
    atteinte : une horloge qui saute ne la fait ni manquer ni jouer deux fois."""
    derniere = None
    while True:
        maintenant = datetime.now(timezone.utc)
        # L'échéance qu'on vient de jouer est gardée : une horloge qui recule ne rejoue pas le passage.
        echeance = prochaine_echeance(maintenant if derniere is None else max(maintenant, derniere))
        derniere = echeance
        while True:
            restant = (echeance - datetime.now(timezone.utc)).total_seconds()
            if restant <= 0:
                break
            await asyncio.sleep(min(restant, 3600))
        try:
            async with AsyncSessionLocal() as db:
                await reconcile_discord_surface(db)
        except Exception:
            logger.exception("Passage quotidien Discord : erreur non bloquante")


# --- 7e. Routeur interactions + trigger de test -----------------------------

router = APIRouter()


def _ephemeral(content: str) -> dict:
    """Réponse type 4 (CHANNEL_MESSAGE_WITH_SOURCE) éphémère (flags=64) --
    accusé propre, jamais de "interaction failed" Discord."""
    return {"type": 4, "data": {"flags": 64, "content": content}}


def _parse_rsvp_custom_id(custom_id: str) -> Optional[tuple[UUID, date, str]]:
    """Parse `rsvp:v1:{event_id}:{occ_date}:{state}` (cf. brief §4 étape 1).
    Ne lève jamais : tout format inattendu renvoie `None` (défensif — ne
    devrait pas arriver, `custom_id` est généré par nous-mêmes dans
    `build_occurrence_payload`)."""
    parts = custom_id.split(":")
    if len(parts) != 5 or parts[0] != "rsvp" or parts[1] != "v1":
        return None
    _, _, event_id_raw, occ_date_raw, state = parts
    if state not in _RSVP_STATES:
        return None
    try:
        event_id = UUID(event_id_raw)
        occ_date = date.fromisoformat(occ_date_raw)
    except ValueError:
        return None
    return event_id, occ_date, state


async def _handle_rsvp_click(db: AsyncSession, body: dict) -> dict:
    """Traitement réel d'un clic de bouton RSVP (cf. brief §4 étapes 1-6) :
    parse custom_id -> gating D3 -> auto-provision profil (resync ①) ->
    écriture D5 (state seul, prefs préservées) -> réponse type 7
    (UPDATE_MESSAGE) avec le roster à jour. Ne propage JAMAIS un 4xx à
    Discord (toujours un éphémère propre en cas de souci)."""
    data = body.get("data") or {}
    parsed = _parse_rsvp_custom_id(data.get("custom_id") or "")
    if parsed is None:
        return _ephemeral("Requête invalide.")
    event_id, occ_date, state = parsed

    member = body.get("member")
    if not member:
        # DM (hors serveur) -- jamais attendu en usage normal (les boutons
        # ne vivent que dans le salon du serveur), mais défensif.
        return _ephemeral("Cette action doit être effectuée depuis le salon du serveur.")

    user = member.get("user") or {}
    try:
        user_id = int(user["id"])
        username = user["username"]
    except (KeyError, TypeError, ValueError):
        return _ephemeral("Requête invalide.")

    member_role_ids = {str(r) for r in member.get("roles", [])}
    display_name = member.get("nick") or user.get("global_name") or username

    # Gating D3 -- même prédicat que le login (auth.py) : aucune écriture
    # avant d'avoir vérifié l'appartenance. Lot 3.2d Volet 2, §5.4 : la
    # liste passe par le résolveur (même fonction qu'`auth.py:callback`).
    allowed_role_ids = await _app_access_role_ids(db)
    # GARDE-FOU anti-lock-out : un administrateur entre toujours, quels que
    # soient ses rôles Discord. Sans cela, l'écran Droits pourrait fermer la
    # porte à tout le monde, administrateur compris. TOUJOURS avant le test
    # de rôles.
    if str(user_id) not in settings.admin_ids_set:
        if not (member_role_ids & allowed_role_ids):
            return _ephemeral(
                "Accès non autorisé — connecte-toi au portail pour rejoindre l'escadrille."
            )

    # Auto-provision D3 (resync ①) -- MÊME session `db`, AVANT l'écriture
    # de présence pour respecter la FK `presences.profile_id ->
    # profiles.id`. Pas de `last_login_at` : ce n'est pas un login.
    roles_snapshot = sorted(member_role_ids)
    stmt = pg_insert(Profile).values(
        id=user_id,
        username=username,
        global_name=display_name,
        roles_snapshot=roles_snapshot,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Profile.id],
        set_={
            "username": username,
            "global_name": display_name,
            "roles_snapshot": roles_snapshot,
        },
    )
    await db.execute(stmt)
    await db.commit()

    # Lot 2.2b (cf. brief §5/§6/G4) -- meme mecanique de resolution/
    # appartenance que auth.py, DOIT s'executer APRES l'upsert ci-dessus
    # (FK squadron_membership.profile_id). Reste appelable ici : ni
    # requete ni session (pas de `Request` dans la signature). Lot
    # « L'appel » : par `appliquer_roles` ; le gating ci-dessus ne laisse
    # passer que qui passe la porte (`peut_entrer=True`).
    await squadron_module.appliquer_roles(db, user_id, member_role_ids, True)

    # Écriture D5 -- state seul (sentinelle UNSET par défaut) : les prefs
    # aircraft/mission_types existantes ne sont jamais touchées par un
    # simple clic Discord.
    try:
        await set_presence_state(
            db, event_id=event_id, occ_date=occ_date, profile_id=user_id, state=state
        )
    except HTTPException:
        logger.info(
            "RSVP Discord : clic sur occurrence indisponible (event_id=%s occ_date=%s)",
            event_id,
            occ_date,
        )
        return _ephemeral("Cette occurrence n'est plus disponible.")

    # Réponse type 7 (UPDATE_MESSAGE) -- re-résout l'occurrence + roster à
    # jour (incluant ce clic), édition en place du message porteur.
    # `set_presence_state` a déjà fait `publish_invalidate` (portail à
    # jour via SSE) ; pas de reproject planifié ici (ce message vient
    # d'être re-rendu par ce même appel -- éviter un EDIT redondant, cf.
    # brief §4.7).
    event = await db.get(Event, event_id)
    occurrence, _ = await _effective_occurrence(db, event, occ_date)
    if occurrence is None:
        # Ne devrait pas arriver (set_presence_state vient de valider la
        # même occurrence) -- défensif : accusé propre plutôt qu'un crash.
        return _ephemeral("Présence enregistrée.")
    names_map = await _presence_names(db, [event_id], occ_date, occ_date)
    names_by_state = names_map.get(
        (str(event_id), occ_date), {"present": [], "maybe": [], "absent": []}
    )
    payload = build_occurrence_payload(occurrence, names_by_state)
    return {"type": 7, "data": payload}


@router.post("/discord/interactions")
async def discord_interactions(request: Request, db: AsyncSession = Depends(get_db)):
    """Endpoint d'interactions Discord (hors OAuth, comme
    `discord_digest`). Vérifie la signature Ed25519 sur le corps BRUT
    (avant tout parsing JSON), répond PONG au PING de validation du
    portail, et traite réellement le clic de bouton RSVP (Lot 2b-2, cf.
    brief §4) via `_handle_rsvp_click`."""
    raw_body = await request.body()
    signature = request.headers.get("X-Signature-Ed25519")
    timestamp = request.headers.get("X-Signature-Timestamp")

    if (
        not settings.DISCORD_PUBLIC_KEY
        or not signature
        or not timestamp
        or not verify_signature(settings.DISCORD_PUBLIC_KEY, timestamp, raw_body, signature)
    ):
        raise HTTPException(status_code=401, detail="Signature invalide")

    try:
        body = json.loads(raw_body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Corps JSON invalide") from None

    if body.get("type") == 1:
        return {"type": 1}

    if body.get("type") == 3:
        return await _handle_rsvp_click(db, body)

    # Lot « La connexion de secours » (R325) : la commande `/readyroom`
    # (APPLICATION_COMMAND) rend un lien d'entrée éphémère.
    if body.get("type") == 2:
        return await connexion_secours.traiter_commande(db, body)

    # Tout autre type non géré à ce stade : réponse éphémère propre,
    # jamais de "interaction failed".
    return _ephemeral("Type d'interaction non pris en charge.")


@router.post("/discord/rsvp/reproject", status_code=204)
async def trigger_reproject(
    event_id: UUID = Query(...),
    occ_date: date = Query(...),
    x_digest_token: Optional[str] = Header(None, alias="X-Digest-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger de test à token partagé (même mécanique que
    `discord_digest`) : permet au porteur de poster un vrai message de test
    sans attendre le câblage complet (Lot 2b-2/2b-3), cf. brief §7e.
    Lot « La défense de l'App exposée » (R5, addendum 3) : le jeton se lit dans l'en-tête
    `X-Digest-Token`, jamais dans l'adresse ; comparé à temps constant."""
    if not jeton_valide(settings.DISCORD_DIGEST_TOKEN, x_digest_token):
        raise HTTPException(status_code=403, detail="Token invalide ou absent")

    await reproject_occurrence(db, event_id, occ_date)
    return None


@router.post("/discord/rsvp/roll", status_code=204)
async def trigger_roll(
    x_digest_token: Optional[str] = Header(None, alias="X-Digest-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Roll quotidien (cf. brief Lot 2b-3 §2/§6, cron externe) : réconcilie
    la surface Discord entière -- avance de la fenêtre glissante + purge D7
    (2b active) ou nettoyage + repost évergreen (2b inactive), selon
    `DISCORD_RSVP_ENABLED`. Même mécanique à token partagé que
    `trigger_reproject` ci-dessus (jeton en en-tête `X-Digest-Token`, jamais dans
    l'adresse : R5 et addendum 3 du lot « La défense de l'App exposée »)."""
    if not jeton_valide(settings.DISCORD_DIGEST_TOKEN, x_digest_token):
        raise HTTPException(status_code=403, detail="Token invalide ou absent")

    await reconcile_discord_surface(db)
    return None
