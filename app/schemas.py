"""Schémas Pydantic — validation stricte des entrées API. Cf. brief Lot 2 et
SPEC_TECHNIQUE_READY_ROOM_Planification_v1 §3/§4/§6.
"""
from __future__ import annotations

import uuid
from datetime import date
from enum import Enum
from typing import Annotated, Literal, Optional

from pydantic import AwareDatetime, BaseModel, Field, field_validator


class EventType(str, Enum):
    entrainement = "entrainement"
    mission = "mission"
    jeulibre = "jeulibre"
    campagne = "campagne"


class RsvpState(str, Enum):
    present = "present"
    maybe = "maybe"
    absent = "absent"


# --- Preferences RSVP : appareils + types de mission (SPEC B.3) -----------
# Listes figees, codes = valeurs stockees telles quelles (appareils non
# traduits ; types de mission traduits cote front uniquement, cf. app.js).

AIRCRAFT_CODES: frozenset[str] = frozenset(
    {
        "A-10A", "A-10C", "A-10C II", "AH-64", "AJS-37",
        "AV-8B", "C-101", "C-130", "CH-47", "Christen Eagle II",
        "F-100", "F-14A", "F-14B", "F-15C", "F-15E",
        "F-16C", "F/A-18", "F-4E", "F-5E", "F-86F",
        "Hawk", "J-11A", "JF-17", "Ka-50", "L-39",
        "M-2000C", "MB-339", "Mi-24P", "Mi-8", "MIG-15Bis",
        "MIG-19P", "MIG-21Bis", "MIG-29 FC3", "MIG-29 FF", "Mirage F1 BE",
        "Mirage F1 CE", "Mirage F1 EE", "OH-58D", "SA-342 Gazelle", "SU-25",
        "SU-27", "SU-33", "UH-1H", "Yak-52", "Combined Arms (JTAC)",
        "LotATC",
    }
)

MISSION_TYPE_CODES: frozenset[str] = frozenset(
    {
        "CAP", "STRIKE", "CAS", "SEAD", "ESCORTE", "INTERCEPTION",
        "PVP", "AGRESSEUR", "ENTRAINEMENT", "PEU_IMPORTE",
    }
)

# Types d'evenement pour lesquels les preferences aircraft/mission_types sont
# acceptees (cf. SPEC B.1/B.4). Reutilise par app/events.py.
PRESENCE_PREFS_EVENT_TYPES: frozenset[str] = frozenset(
    {"mission", "entrainement", "campagne"}
)

# --- Plateformes structurees (v0.26) : liste fermee pour Mission/
# Entrainement/Campagne. Miroir EXACT de la constante JS `STRUCTURED_GAMES`
# (app/static/app.js). map_name valide/affichee uniquement si la plateforme
# choisie est "DCS".
STRUCTURED_GAMES: frozenset[str] = frozenset({"DCS", "IL-2 GB", "IL-2 Korea"})

# --- Maps (v0.23) : liste fermee pour Mission/Entrainement -----------------
# Miroir EXACT (memes chaines, meme casse) de la constante JS `MAPS`
# (app/static/app.js) -- cf. VIGILANCE BRIEF_SONNET_ReadyRoom_v0.23. Pas de
# "autre" ici (contrairement au jeu libre) : toute valeur hors liste est
# rejetee en 422.
# Lot « Les cartes DCS de chaque pilote » (v1.0085) : une seule liste, les
# quatorze cartes officielles, dans l'ordre d'affichage ; `MAPS` en derive.
CARTES_DCS: tuple[str, ...] = (
    "Syria", "Germany (Cold War)", "Caucasus", "Marianas", "Normandy",
    "Afghanistan", "Persian Gulf", "Sinai", "Iraq", "Kola",
    "South Atlantic", "Nevada", "The Channel", "Marianas WWII",
)
MAPS: frozenset[str] = frozenset(CARTES_DCS)


# --- Règle de récurrence --------------------------------------------------


class RecurrenceEndUntil(BaseModel):
    type: Literal["until"]
    until: date


class RecurrenceEndCount(BaseModel):
    type: Literal["count"]
    # Lot « Les finitions de l'édition » (v1.0103, ARC-17) : borne haute.
    count: int = Field(ge=1, le=500)


# `end` = until XOR count XOR null — garanti par l'union discriminée
# (chaque variante porte un `type` littéral distinct) + `None`.
RecurrenceEnd = Annotated[
    "RecurrenceEndUntil | RecurrenceEndCount", Field(discriminator="type")
]


class RecurrenceRule(BaseModel):
    freq: Literal["weekly"]
    # Lot « Les finitions de l'édition » (v1.0103, ARC-17) : borne haute.
    interval: int = Field(default=1, ge=1, le=52)
    weekdays: list[int] = Field(min_length=1)
    end: Optional[RecurrenceEnd] = None

    @field_validator("weekdays")
    @classmethod
    def _check_weekdays(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError(
                "weekdays doit contenir des entiers entre 0 (lundi) et 6 (dimanche)"
            )
        return sorted(set(v))


# --- Événements ------------------------------------------------------------


def _titre_sans_espaces(v: str) -> str:
    """Lot « Les finitions de l'édition » (v1.0103, ARC-17) : titre rendu sans
    espaces de tête ni de queue ; refusé s'il est vide après `strip`."""
    v = v.strip()
    if not v:
        raise ValueError("Le titre ne peut pas être vide")
    return v


class EventCreate(BaseModel):
    type: EventType
    # Lot « Les finitions de l'édition » (v1.0103, ARC-17) : longueurs,
    # durée et début avec fuseau bornés.
    game_label: Optional[str] = Field(default=None, max_length=60)
    map_name: Optional[str] = None
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    start_at: AwareDatetime
    duration_min: Optional[int] = Field(default=None, ge=1, le=1440)
    recurrence: Optional[RecurrenceRule] = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        return _titre_sans_espaces(v)

    @field_validator("map_name")
    @classmethod
    def _check_map_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MAPS:
            raise ValueError(f"Map inconnue : {v!r}")
        return v


class EventPatchBody(BaseModel):
    """Corps du PATCH — tous les champs optionnels ; seuls les champs
    réellement fournis (`model_dump(exclude_unset=True)`) sont appliqués.
    Pour `scope=occurrence`, `start_at`/`recurrence` sont interdits (portée
    série uniquement)."""

    type: Optional[EventType] = None
    game_label: Optional[str] = Field(default=None, max_length=60)
    map_name: Optional[str] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=4000)
    start_at: Optional[AwareDatetime] = None
    duration_min: Optional[int] = Field(default=None, ge=1, le=1440)
    recurrence: Optional[RecurrenceRule] = None

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _titre_sans_espaces(v)

    @field_validator("map_name")
    @classmethod
    def _check_map_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in MAPS:
            raise ValueError(f"Map inconnue : {v!r}")
        return v


# --- Présences ---------------------------------------------------------


class PresenceUpsert(BaseModel):
    event_id: uuid.UUID
    occ_date: date
    state: RsvpState
    # Facultatifs (SPEC B.4) : valides contre les listes figees ; la
    # restriction "mission/entrainement uniquement" est appliquee cote
    # route (app/events.py), pas ici (ce schema ne connait pas le type
    # de l'evenement cible).
    aircraft: Optional[list[str]] = None
    mission_types: Optional[list[str]] = None
    # v0.80 -- portée de l'écriture. `occurrence` (défaut) = comportement
    # historique strict. `series` = applique aux occurrences effectives de
    # la série dans [max(occ_date, today), +PRESENCE_SERIES_HORIZON_DAYS].
    scope: Literal["occurrence", "series"] = "occurrence"

    @field_validator("aircraft")
    @classmethod
    def _check_aircraft(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        unknown = set(v) - AIRCRAFT_CODES
        if unknown:
            raise ValueError(f"Appareil(s) inconnu(s) : {sorted(unknown)}")
        return v

    @field_validator("mission_types")
    @classmethod
    def _check_mission_types(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        unknown = set(v) - MISSION_TYPE_CODES
        if unknown:
            raise ValueError(f"Type(s) de mission inconnu(s) : {sorted(unknown)}")
        return v
