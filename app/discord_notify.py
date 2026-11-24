"""Notifications Discord sortantes — Lot 7 (Phase 2a).

Cf. BRIEF_SONNET_ReadyRoom_Lot7_Notifications_Discord. Digest hebdomadaire
(semaine en cours + à venir) posté via **webhook classique** (pas de bot,
pas d'endpoint d'interactions entrant — Phase 2b hors périmètre).

Réutilise intégralement le moteur de récurrence existant
(`_load_events_and_overrides` + `expand`, cf. `app/events.py`) : aucune
expansion d'occurrences dupliquée ici.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import taches
from app.config import settings
from app.db import AsyncSessionLocal
from app.events import _load_events_and_overrides, _presence_counts, _presence_names
from app.models import DiscordDigestMessage, Wing
from app.recurrence import Occurrence, UnsupportedRecurrenceRule, expand, fuseau_reference

logger = logging.getLogger(__name__)

# --- i18n --------------------------------------------------------------

# Entête identique dans les deux langues (cf. brief §2) : hors dict de locale.
# Lot « L'écran Escadre du Centre » : la désignation de l'escadre se lit en
# base AU MOMENT DE L'ENVOI (`_read_header`), repli `WING_TAG`.
_HEADER = "READY ROOM — {designation}"


async def _read_header(db: AsyncSession) -> str:
    """L'entête du digest : « READY ROOM — {désignation} », la désignation
    lue sur la ligne `wing`. Sans ligne ou désignation vide : `WING_TAG`."""
    designation = (
        await db.execute(select(Wing.designation).order_by(Wing.id.asc()).limit(1))
    ).scalar_one_or_none()
    designation = (designation or "").strip() or (settings.WING_TAG or "").strip()
    return _HEADER.format(designation=designation)

_I18N: dict[str, dict] = {
    "en": {
        "title": "Schedule — week of {date}",
        "this_week": "THIS WEEK",
        "next_week": "NEXT WEEK",
        "types": {
            "entrainement": "Training",
            "mission": "Mission",
            "jeulibre": "Free flight",
            "campagne": "Campaign",
        },
        "attending_suffix": " · 👥 **{n}** attending",
        "footer": "Timezone {fuseau}",
        "button_label": "Open the Ready Room",
    },
    "fr": {
        "title": "Planning — semaine du {date}",
        "this_week": "SEMAINE EN COURS",
        "next_week": "SEMAINE À VENIR",
        "types": {
            "entrainement": "Entraînement",
            "mission": "Mission",
            "jeulibre": "Jeu libre",
            "campagne": "Campagne",
        },
        "attending_suffix": " · 👥 **{n}** présents",
        "footer": "Fuseau {fuseau}",
        "button_label": "Ouvrir la Ready Room",
    },
}

# Petites tables d'abréviations jour/mois — pas de `babel`, pas de
# dépendance à la locale système (cf. brief §2). Index 0 = lundi (aligné
# sur `date.weekday()`).
_DAYS_ABBR: dict[str, list[str]] = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "fr": ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"],
}
_MONTHS_ABBR: dict[str, list[str]] = {
    "en": [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ],
    "fr": [
        "janv.", "févr.", "mars", "avr.", "mai", "juin",
        "juil.", "août", "sept.", "oct.", "nov.", "déc.",
    ],
}

_TYPE_EMOJI: dict[str, str] = {
    "entrainement": "🟩",
    "mission": "🟨",
    "jeulibre": "🟦",
    "campagne": "🟪",
}

# Ambre #E0A83A (cf. brief §3 — valeur fournie telle quelle).
_EMBED_COLOR = 14722106

# Limite Discord sur `description` (cf. VIGILANCE brief — erreur 50035
# sinon). On tronque plutôt que de laisser Discord rejeter le post.
_DESCRIPTION_MAX_CHARS = 4096


def _t(locale: str) -> dict:
    return _I18N[locale]


def _format_title_date(d: date, locale: str) -> str:
    return f"{d.day} {_MONTHS_ABBR[locale][d.month - 1]} {d.year}"


def _esc_md(name: str) -> str:
    for ch in ("\\", "*", "_", "~", "`", "|"):
        name = name.replace(ch, "\\" + ch)
    return name


def _format_occ_line(
    occ: Occurrence, present: int, names: dict[str, list[str]], locale: str
) -> str:
    tr = _t(locale)
    local_dt = occ.start_at_utc.astimezone(fuseau_reference())
    day_abbr = _DAYS_ABBR[locale][occ.occ_date.weekday()]
    when = f"{day_abbr} {occ.occ_date.day:02d} · {local_dt.strftime('%H:%M')}"
    emoji = _TYPE_EMOJI.get(occ.type, "⬜")
    type_label = tr["types"].get(occ.type, occ.type)
    # v0.24 : stanza 2 lignes — L1 = type + heure, L2 = intitulé + présents.
    # v0.26 : plateforme unifiee (game_label) + map (DCS uniquement) --
    # jeulibre -> plateforme libre seule ; structure -> plateforme puis map.
    parts = []
    if occ.type == "jeulibre":
        if occ.game_label:
            parts.append(occ.game_label)
    else:  # structuré
        if occ.game_label:
            parts.append(occ.game_label)
        if occ.map_name:
            parts.append(occ.map_name)
    context = f" — {' · '.join(parts)}" if parts else ""
    suffix = tr["attending_suffix"].format(n=present) if present > 0 else ""
    line1 = f"{emoji} **{type_label}** · `{when}`"
    line2 = f"{occ.title}{context}{suffix}"
    roster_lines = []
    for state, marker in (("present", "✓"), ("maybe", "~"), ("absent", "✗")):
        people = names.get(state) or []
        if people:
            joined = " • ".join(_esc_md(p) for p in people)
            roster_lines.append(f"-# {marker} *{joined}*")
    tail = ("\n" + "\n".join(roster_lines)) if roster_lines else ""
    return f"{line1}\n{line2}{tail}"


def _truncate_description(text: str) -> str:
    """Tronque `text` sous la limite Discord en retirant des lignes
    entières depuis la fin, avec un marqueur « … +N » (cf. VIGILANCE)."""
    if len(text) <= _DESCRIPTION_MAX_CHARS:
        return text

    lines = text.split("\n")
    dropped = 0
    while lines:
        dropped += 1
        lines.pop()
        candidate_suffix = f"\n… +{dropped}"
        candidate = "\n".join(lines) + candidate_suffix
        if len(candidate) <= _DESCRIPTION_MAX_CHARS:
            return candidate
    # Cas extrême (une seule ligne déjà trop longue) : coupe brute.
    return text[: _DESCRIPTION_MAX_CHARS]


# --- Récupération des données -------------------------------------------


def _two_week_window(anchor: date) -> tuple[date, date, date, date]:
    """(week1_monday, week1_sunday, week2_monday, week2_sunday) pour
    `anchor`. Source unique du découpage deux-semaines : partagée par
    `build_two_weeks`, le stockage de la fenêtre en base (singleton) et le
    filtre A1 du debounce (cf. brief §3.4)."""
    week1_monday = anchor - timedelta(days=anchor.weekday())
    week1_sunday = week1_monday + timedelta(days=6)
    week2_monday = week1_monday + timedelta(days=7)
    week2_sunday = week2_monday + timedelta(days=6)
    return week1_monday, week1_sunday, week2_monday, week2_sunday


async def build_two_weeks(
    db: AsyncSession, anchor: date
) -> tuple[list[tuple[Occurrence, int, dict]], list[tuple[Occurrence, int, dict]]]:
    """Deux semaines (courante + suivante) à partir de `anchor`, avec le
    nombre de présents par occurrence — même expansion que `/api/hebdo`
    (`_load_events_and_overrides` + `expand`), mêmes compteurs que
    `/api/events` (`_presence_counts`), jamais dupliqués ici."""
    week1_monday, week1_sunday, week2_monday, week2_sunday = _two_week_window(anchor)

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

    counts: dict[tuple[str, date], dict[str, int]] = {}
    names_map: dict[tuple[str, date], dict] = {}
    if all_occurrences:
        occ_event_ids = list({UUID(o.event_id) for o in all_occurrences})
        counts = await _presence_counts(db, occ_event_ids, from_date, to_date)
        names_map = await _presence_names(db, occ_event_ids, from_date, to_date)

    def _present(o: Occurrence) -> int:
        return counts.get((o.event_id, o.occ_date), {}).get("present", 0)

    def _names(o: Occurrence) -> dict:
        return names_map.get((o.event_id, o.occ_date), {"present": [], "maybe": [], "absent": []})

    current_week = [
        (o, _present(o), _names(o))
        for o in all_occurrences
        if week1_monday <= o.occ_date <= week1_sunday
    ]
    next_week = [
        (o, _present(o), _names(o))
        for o in all_occurrences
        if week2_monday <= o.occ_date <= week2_sunday
    ]
    return current_week, next_week


# --- Construction du payload webhook -------------------------------------


def build_webhook_payload(
    current_week: list[tuple[Occurrence, int, dict]],
    next_week: list[tuple[Occurrence, int, dict]],
    base_url: str,
    locale: str,
    header: str,
) -> Optional[dict]:
    """Construit le JSON du webhook Discord (embed unique). `None` si les
    deux semaines sont vides (cf. brief §3 — pas de post dans ce cas)."""
    if not current_week and not next_week:
        return None

    locale = locale if locale in _I18N else "en"
    tr = _t(locale)

    if current_week:
        title_date = _format_title_date(current_week[0][0].occ_date, locale)
    else:
        title_date = _format_title_date(next_week[0][0].occ_date, locale)

    def _section(title: str, pairs: list[tuple[Occurrence, int, dict]]) -> list[str]:
        stanzas = [_format_occ_line(o, n, nm, locale) for o, n, nm in pairs]
        return [f"## {title}", "", "\n\n".join(stanzas)]

    blocks: list[str] = []
    if current_week:
        blocks.extend(_section(tr["this_week"], current_week))
    if next_week:
        if blocks:
            blocks.append("")  # respiration entre les deux sections
        blocks.extend(_section(tr["next_week"], next_week))

    description = _truncate_description("\n".join(blocks))

    embed = {
        "color": _EMBED_COLOR,
        "author": {"name": header},
        "title": tr["title"].format(date=title_date),
        "description": description,
        # Lot « rr-fuseau-reglage » : le pied dit le fuseau réglé (Europe/Paris par défaut, texte inchangé).
        "footer": {"text": tr["footer"].format(fuseau=settings.REFERENCE_TZ)},
    }

    return {
        "embeds": [embed],
        "components": [
            {
                "type": 1,
                "components": [
                    {
                        "type": 2,
                        "style": 5,
                        "label": tr["button_label"],
                        # Lot « Les liens de la soirée » (v1.0107) : le bouton ouvre le Tableau hebdo ;
                        # sans adresse de base, la conduite d'avant reste.
                        "url": f"{base_url.rstrip('/')}/#planif/hebdo" if base_url else base_url,
                    }
                ],
            }
        ],
        "allowed_mentions": {"parse": []},  # aucune mention ne notifie (titre/description = texte libre)
    }


# --- Webhook : base URL, singleton, suppression --------------------------


def _webhook_base_url() -> str:
    """Dérive `https://discord.com/api/webhooks/{id}/{token}` depuis
    `DISCORD_WEBHOOK_URL` (retire toute query string), cf. brief §3.1.
    Sert de base pour `{base}/messages/{message_id}`. N'appeler que si
    `settings.DISCORD_WEBHOOK_URL` est défini (vérifié par l'appelant)."""
    parts = urlsplit(settings.DISCORD_WEBHOOK_URL)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


async def _get_digest_row(db: AsyncSession) -> Optional[DiscordDigestMessage]:
    return await db.get(DiscordDigestMessage, 1)


async def _upsert_digest_row(
    db: AsyncSession,
    *,
    message_id: Optional[str],
    pending_delete: list[str],
    week_monday: Optional[date],
    window_end: Optional[date],
) -> None:
    """Upsert du singleton (id=1) — cf. brief §1/§3.2."""
    values = {
        "id": 1,
        "message_id": message_id,
        "pending_delete": pending_delete,
        "week_monday": week_monday,
        "window_end": window_end,
    }
    stmt = pg_insert(DiscordDigestMessage).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[DiscordDigestMessage.id],
        set_={
            "message_id": message_id,
            "pending_delete": pending_delete,
            "week_monday": week_monday,
            "window_end": window_end,
            "updated_at": func.now(),
        },
    )
    await db.execute(stmt)
    await db.commit()


async def _delete_messages(base: str, message_ids: list[str]) -> list[str]:
    """Supprime chaque id de `message_ids` séquentiellement, chacun isolé
    en try/except (cf. brief §3.2) : un échec n'empêche pas les suivants.
    404 = considéré supprimé. Retourne les id restant en échec (à
    conserver dans `pending_delete` pour retry au prochain post)."""
    remaining: list[str] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for message_id in message_ids:
            try:
                response = await client.delete(f"{base}/messages/{message_id}")
                if response.status_code == 404 or 200 <= response.status_code < 300:
                    continue
                logger.warning(
                    "Digest Discord : échec suppression message %s (status=%s), "
                    "conservé en file pour retry",
                    message_id,
                    response.status_code,
                )
                remaining.append(message_id)
            except httpx.HTTPError as exc:
                logger.warning(
                    "Digest Discord : erreur réseau à la suppression du message %s "
                    "(%s), conservé en file pour retry",
                    message_id,
                    exc,
                )
                remaining.append(message_id)
    return remaining


def _dedupe(ids: list[str]) -> list[str]:
    """Déduplique en conservant l'ordre (un même id peut apparaître dans
    `pending_delete`, l'ancien `message_id` courant et le backlog de purge)."""
    return list(dict.fromkeys(i for i in ids if i))


# --- Cache mémoire de la fenêtre courante + debounce (cf. brief §3.4) -----

_current_window: Optional[tuple[date, date]] = None
_flush_scheduled: bool = False


def _set_current_window(week_monday: Optional[date], window_end: Optional[date]) -> None:
    global _current_window
    _current_window = (week_monday, window_end) if week_monday and window_end else None


async def _hydrate_current_window() -> None:
    """Lecture lazy de la ligne singleton (premier déclenchement après un
    redémarrage de l'app — le cache mémoire est vide), cf. brief §3.4."""
    async with AsyncSessionLocal() as db:
        row = await _get_digest_row(db)
    if row and row.week_monday and row.window_end:
        _set_current_window(row.week_monday, row.window_end)
    else:
        _set_current_window(None, None)


# --- Envoi -----------------------------------------------------------------


async def post_digest(db: AsyncSession, anchor: Optional[date] = None) -> None:
    """Construit puis poste le digest évergreen : POST du nouveau message
    **avant** toute suppression (jamais l'inverse), puis purge de tous les
    anciens messages connus (file `pending_delete` + ancien `message_id` +
    backlog `DISCORD_DIGEST_CLEANUP_IDS`), avec retry des échecs. Ne lève
    jamais : toute erreur est journalisée, pas de crash (cf. checklist
    d'acceptation brief)."""
    if anchor is None:
        anchor = datetime.now(fuseau_reference()).date()

    week1_monday, _week1_sunday, _week2_monday, week2_sunday = _two_week_window(anchor)
    current_week, next_week = await build_two_weeks(db, anchor)
    payload = build_webhook_payload(
        current_week, next_week, settings.BASE_URL, settings.digest_locale,
        await _read_header(db),
    )

    if not settings.DISCORD_WEBHOOK_URL:
        logger.warning("Digest Discord : DISCORD_WEBHOOK_URL non défini, digest non posté")
        return

    base = _webhook_base_url()
    row = await _get_digest_row(db)
    pending = list(row.pending_delete) if row and row.pending_delete else []
    old_message_id = row.message_id if row else None
    cleanup_ids = settings.digest_cleanup_ids_list

    if payload is None:
        # Deux semaines vides : on nettoie le canal (ancien message +
        # backlog de retry), pas de nouveau post (cf. brief §3.2).
        logger.info("Digest Discord : digest vide, non posté (anchor=%s)", anchor)
        to_delete = _dedupe(pending + ([old_message_id] if old_message_id else []))
        remaining = await _delete_messages(base, to_delete)
        await _upsert_digest_row(
            db, message_id=None, pending_delete=remaining, week_monday=None, window_end=None
        )
        _set_current_window(None, None)
        return

    # `wait=true` impératif pour récupérer l'objet message (donc son id) ;
    # `with_components=true` impératif, sinon le bouton-lien est ignoré
    # silencieusement par Discord (cf. VIGILANCE brief).
    url = f"{base}?wait=true&with_components=true"
    new_id: Optional[str] = None
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
        if response.status_code < 200 or response.status_code >= 300:
            logger.error(
                "Digest Discord : réponse non-2xx du webhook au POST (status=%s)",
                response.status_code,
            )
            return
        new_id = str(response.json()["id"])
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.error("Digest Discord : erreur d'envoi vers le webhook (%s)", exc)
        return

    # Ordre impératif (cf. VIGILANCE) : le nouveau message est confirmé
    # posté (new_id obtenu) AVANT toute suppression.
    to_delete = _dedupe(pending + ([old_message_id] if old_message_id else []) + cleanup_ids)
    remaining = await _delete_messages(base, to_delete)

    await _upsert_digest_row(
        db,
        message_id=new_id,
        pending_delete=remaining,
        week_monday=week1_monday,
        window_end=week2_sunday,
    )
    _set_current_window(week1_monday, week2_sunday)


async def refresh_digest_message(db: AsyncSession) -> None:
    """Édition en direct (PATCH) du message digest courant — cf. brief
    §3.3. N'existe que pour rafraîchir un message déjà posté : si aucune
    ligne singleton n'a de `message_id`, on ne fait rien (décision D — pas
    de création de message hors post hebdo/manuel)."""
    if not settings.DISCORD_DIGEST_REFRESH_ENABLED:
        return
    if not settings.DISCORD_WEBHOOK_URL:
        return

    row = await _get_digest_row(db)
    if row is None or not row.message_id:
        return

    anchor = row.week_monday or datetime.now(fuseau_reference()).date()
    current_week, next_week = await build_two_weeks(db, anchor)
    payload = build_webhook_payload(
        current_week, next_week, settings.BASE_URL, settings.digest_locale,
        await _read_header(db),
    )
    if payload is None:
        # Fenêtre redevenue vide entre deux posts (cas rare) : on laisse le
        # message tel quel, le prochain post hebdo nettoiera le canal.
        return

    base = _webhook_base_url()
    url = f"{base}/messages/{row.message_id}?with_components=true"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.patch(url, json=payload)
    except httpx.HTTPError as exc:
        logger.warning("Digest Discord : erreur réseau au PATCH (%s)", exc)
        return

    if response.status_code in (404, 401):
        # Message supprimé côté Discord ou webhook tourné : on vide la
        # ligne + le cache ; le prochain post hebdo recrée (cf. brief §3.3).
        logger.info(
            "Digest Discord : message %s introuvable/invalide au PATCH (status=%s), "
            "ligne vidée",
            row.message_id,
            response.status_code,
        )
        await _upsert_digest_row(
            db,
            message_id=None,
            pending_delete=list(row.pending_delete or []),
            week_monday=None,
            window_end=None,
        )
        _set_current_window(None, None)
        return

    if response.status_code == 429:
        logger.info("Digest Discord : PATCH throttlé (429), pas de retry immédiat")
        return

    if response.status_code < 200 or response.status_code >= 300:
        logger.warning(
            "Digest Discord : réponse non-2xx du webhook au PATCH (status=%s)",
            response.status_code,
        )


# --- Debounce (tâche one-shot, sans lifespan) — cf. brief §3.4 ------------


def schedule_digest_refresh(occ_date: date, event_id: str) -> None:
    """Programme un rafraîchissement débouncé du digest suite à un
    changement de présence. Non bloquant, jamais fatal : le hook
    `PUT /api/presences` ne doit jamais échouer à cause de Discord."""
    if settings.DISCORD_RSVP_ENABLED:
        return  # Phase 2b active -> digest évergreen suspendu (cf. cutover 2b-3)
    if not settings.DISCORD_DIGEST_REFRESH_ENABLED:
        return
    try:
        taches.lancer(_maybe_schedule_flush(occ_date, event_id))
    except RuntimeError:
        # Pas de event loop en cours : ne devrait pas arriver depuis une
        # route FastAPI, mais on abandonne silencieusement plutôt que de
        # faire échouer l'appelant.
        logger.warning("Digest Discord : impossible de programmer le refresh (pas de loop)")


def schedule_digest_refresh_full() -> None:
    """Variante v0.23 (§2.4) : rafraîchissement débouncé/coalescé
    INCONDITIONNEL (sans le filtre fenêtre A1) suite à une mutation
    d'événement (création/édition/suppression). Ces mutations peuvent
    affecter plusieurs occurrences à la fois (séries récurrentes) sans
    `occ_date` précise à tester contre la fenêtre courante — d'où le
    bypass. Non bloquant, jamais fatal (même exigence que le hook
    présence)."""
    if settings.DISCORD_RSVP_ENABLED:
        return  # Phase 2b active -> digest évergreen suspendu (cf. cutover 2b-3)
    if not settings.DISCORD_DIGEST_REFRESH_ENABLED:
        return
    try:
        taches.lancer(
            _maybe_schedule_flush(None, "event-mutation", bypass_window=True)
        )
    except RuntimeError:
        logger.warning(
            "Digest Discord : impossible de programmer le refresh full (pas de loop)"
        )


async def _maybe_schedule_flush(
    occ_date: Optional[date], event_id: str, bypass_window: bool = False
) -> None:
    global _flush_scheduled
    try:
        if not bypass_window:
            if _current_window is None:
                await _hydrate_current_window()

            if _current_window is not None:
                week_monday, window_end = _current_window
                if not (week_monday <= occ_date <= window_end):
                    return  # Décision A1 : occurrence hors fenêtre, aucun appel Discord.

        if _flush_scheduled:
            return  # Un flush déjà en vol absorbera ce changement.

        _flush_scheduled = True
        taches.lancer(_debounced_flush())
    except Exception:
        logger.exception(
            "Digest Discord : erreur lors de la programmation du refresh (event_id=%s)",
            event_id,
        )


async def _debounced_flush() -> None:
    global _flush_scheduled
    try:
        await asyncio.sleep(settings.DISCORD_DIGEST_REFRESH_DEBOUNCE_SECONDS)
        async with AsyncSessionLocal() as db:
            await refresh_digest_message(db)
    except Exception:
        logger.exception("Digest Discord : erreur lors du flush débouncé")
    finally:
        _flush_scheduled = False
