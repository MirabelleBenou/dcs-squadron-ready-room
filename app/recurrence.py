"""Moteur de récurrence — cf. SPEC_TECHNIQUE_READY_ROOM_Planification_v1 §4
et BRIEF_SONNET_ReadyRoom_Lot2.

Toute la logique calendaire (jours ET heure du jour) est calculée en
`fuseau_reference()` (Europe/Paris par défaut) via `zoneinfo`, jamais en UTC ni en heure
serveur. Le DST est géré nativement par `zoneinfo` : une même heure locale
(ex. 20h30) reste 20h30 de part et d'autre d'un changement d'heure, seul le
décalage UTC change.

`expand()` ne déroule jamais une série à l'infini : la fenêtre `[from_date,
to_date]` est obligatoire et bornée (`MAX_WINDOW_DAYS`).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time as dt_time
from typing import TYPE_CHECKING, Optional
from zoneinfo import ZoneInfo

from app.config import settings

if TYPE_CHECKING:
    from app.models import Event, OccurrenceOverride


def fuseau_reference() -> ZoneInfo:
    """Lot « rr-fuseau-reglage » (v1.0120) : le fuseau de l'escadre, réglé en base
    (`settings.REFERENCE_TZ`, Europe/Paris par défaut), lu à CHAQUE appel -- jamais à
    l'import ni dans une constante -- pour qu'un changement vaille sans redémarrage."""
    return ZoneInfo(settings.REFERENCE_TZ)


UTC = ZoneInfo("UTC")

# Fenêtre d'expansion maximale autorisée (jours). Rejette les fenêtres trop
# larges pour éviter tout risque de déroulé quasi-illimité.
MAX_WINDOW_DAYS = 120


class RecurrenceWindowTooLarge(ValueError):
    """Fenêtre `[from_date, to_date]` invalide ou trop large."""


class UnsupportedRecurrenceRule(ValueError):
    """Règle de récurrence non supportée (freq inconnue, etc.)."""


@dataclass
class Occurrence:
    """Une occurrence effective (série ou unique), overrides déjà appliqués."""

    event_id: str
    occ_date: date
    start_at_utc: datetime
    type: str
    game_label: Optional[str]
    map_name: Optional[str]
    title: str
    description: str
    duration_min: Optional[int]
    recurring: bool
    is_override: bool
    created_by: str


def check_window(from_date: date, to_date: date) -> None:
    if to_date < from_date:
        raise RecurrenceWindowTooLarge(
            "La borne 'to' doit être postérieure ou égale à 'from'."
        )
    if (to_date - from_date).days > MAX_WINDOW_DAYS:
        raise RecurrenceWindowTooLarge(
            f"Fenêtre trop large (> {MAX_WINDOW_DAYS} jours)."
        )


def _to_local(dt: datetime) -> datetime:
    """Convertit un datetime aware (n'importe quel fuseau, typiquement UTC
    stocké en base) vers le fuseau de référence."""
    return dt.astimezone(fuseau_reference())


def _local_datetime(occ_date: date, local_time: dt_time) -> datetime:
    """Construit un datetime *aware* en fuseau de référence pour `occ_date` à
    l'heure locale `local_time`. `zoneinfo` calcule l'offset UTC correct
    pour CETTE date précise (gère le DST correctement, contrairement à un
    offset fixe)."""
    naive = datetime.combine(occ_date, local_time)
    return naive.replace(tzinfo=fuseau_reference())


def _weekly_dates(
    anchor_date: date,
    interval: int,
    weekdays: list[int],
    until_date: date | None,
    max_count: int | None,
    from_date: date,
    to_date: date,
) -> list[date]:
    """Déroule les dates (calendaires, fuseau de référence) d'une règle weekly dans
    la fenêtre [from_date, to_date], en comptant `count` depuis l'ancre
    (jamais depuis le début de la fenêtre)."""
    anchor_monday = anchor_date - timedelta(days=anchor_date.weekday())

    hard_limit = to_date
    if until_date is not None:
        hard_limit = min(hard_limit, until_date)

    if hard_limit < anchor_monday:
        # Toute la fenêtre est strictement avant la semaine de l'ancre.
        max_weeks = -1
    else:
        max_weeks = ((hard_limit - anchor_monday).days // 7) + 1

    sorted_weekdays = sorted(set(weekdays))
    result: list[date] = []
    occurrence_index = 0  # compté depuis l'ancre, toutes semaines confondues

    week = 0
    while week <= max_weeks:
        if week % interval == 0:
            week_monday = anchor_monday + timedelta(weeks=week)
            stop = False
            for wd in sorted_weekdays:
                occ_date = week_monday + timedelta(days=wd)
                if occ_date < anchor_date:
                    continue  # jamais avant l'ancre
                if until_date is not None and occ_date > until_date:
                    continue
                if max_count is not None and occurrence_index >= max_count:
                    stop = True
                    break
                occurrence_index += 1
                if from_date <= occ_date <= to_date:
                    result.append(occ_date)
            if stop:
                break
        week += 1

    return result


def raw_occurrence_dates(event: "Event", from_date: date, to_date: date) -> list[date]:
    """Dates calendaires (fuseau de référence) générées par la règle brute de
    l'événement, SANS tenir compte des overrides. Sert à valider qu'une
    `occ_date` donnée appartient bien à la série."""
    check_window(from_date, to_date)

    anchor_local = _to_local(event.start_at)
    anchor_date = anchor_local.date()

    rule = event.recurrence
    if not rule:
        if from_date <= anchor_date <= to_date:
            return [anchor_date]
        return []

    freq = rule.get("freq")
    if freq != "weekly":
        raise UnsupportedRecurrenceRule(f"Fréquence non supportée: {freq!r}")

    interval = int(rule.get("interval", 1))
    weekdays = list(rule.get("weekdays", []))
    end = rule.get("end")

    until_date: date | None = None
    max_count: int | None = None
    if end:
        if end.get("type") == "until":
            until_date = date.fromisoformat(end["until"])
        elif end.get("type") == "count":
            max_count = int(end["count"])

    return _weekly_dates(
        anchor_date, interval, weekdays, until_date, max_count, from_date, to_date
    )


def expand(
    event: "Event",
    overrides_by_date: dict[date, "OccurrenceOverride"],
    from_date: date,
    to_date: date,
) -> list[Occurrence]:
    """Déroule les occurrences EFFECTIVES (overrides appliqués) d'un
    événement dans la fenêtre [from_date, to_date].

    `overrides_by_date` doit être pré-filtré sur cet `event.id` par
    l'appelant (une seule requête groupée en amont — jamais de N+1 ici).
    """
    raw_dates = raw_occurrence_dates(event, from_date, to_date)

    anchor_local = _to_local(event.start_at)
    local_time = anchor_local.time()
    is_recurring = bool(event.recurrence)

    result: list[Occurrence] = []
    for occ_date in raw_dates:
        override = overrides_by_date.get(occ_date)
        if override is not None and override.status == "cancelled":
            continue

        eff_type = event.type
        eff_game_label = event.game_label
        eff_map_name = event.map_name
        eff_title = event.title
        eff_description = event.description
        eff_duration = event.duration_min
        is_override = False

        if override is not None and override.status == "modified":
            is_override = True
            patch = override.patch or {}
            if "type" in patch:
                eff_type = patch["type"]
            if "game_label" in patch:
                eff_game_label = patch["game_label"]
            if "map_name" in patch:
                eff_map_name = patch["map_name"]
            if "title" in patch:
                eff_title = patch["title"]
            if "description" in patch:
                eff_description = patch["description"]
            if "duration_min" in patch:
                eff_duration = patch["duration_min"]

        local_dt = _local_datetime(occ_date, local_time)
        start_at_utc = local_dt.astimezone(UTC)

        result.append(
            Occurrence(
                event_id=str(event.id),
                occ_date=occ_date,
                start_at_utc=start_at_utc,
                type=eff_type,
                game_label=eff_game_label,
                map_name=eff_map_name,
                title=eff_title,
                description=eff_description,
                duration_min=eff_duration,
                recurring=is_recurring,
                is_override=is_override,
                created_by=str(event.created_by),
            )
        )

    return result
