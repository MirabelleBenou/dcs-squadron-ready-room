"""Schémas Pydantic — module Debriefing (Lot D1). Ne pollue pas
`app/schemas.py` (périmètre distinct, brief §4)."""
from __future__ import annotations

import uuid
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas import CARTES_DCS, MAPS


class UploadKind(str, Enum):
    acmi = "acmi"
    debrief = "debrief"


class IdentifyOverride(BaseModel):
    """Corps de `POST /api/debrief/sessions/{id}/flights/{flight_id}/identify`
    (admin only, spec §4.6). L'un des deux champs au moins doit être fourni."""

    pilote_profile_id: Optional[int] = None
    pilot_callsign: Optional[str] = Field(default=None, min_length=1)


class SessionEditPayload(BaseModel):
    """Corps de `PATCH /api/debrief/sessions/{id}` (Lot 2.1, §4.5 ; Lot 2.3,
    §4.6 pour `campaign_id`). Les trois champs sont optionnels et
    indépendants -- `model_fields_set` (et non la valeur) distingue
    l'absence de clé (ne rien faire) de `null` (effacer/détacher) ;
    validation strip()/longueur faite dans la route, pas ici (elle dépend de
    la distinction absent/null que la seule contrainte de champ Pydantic ne
    permet pas de coupler proprement)."""

    display_name: Optional[str] = None
    wing_note: Optional[str] = None
    campaign_id: Optional[uuid.UUID] = None
    # Lot « Mission ou training » : la nature de la session. Une autre valeur
    # est refusée par Pydantic (422) ; `null` est refusé par la route.
    nature: Optional[Literal["mission", "training"]] = None


class DeplacerPayload(BaseModel):
    """Lot « Le rattachement des dépôts » (v1.0052) : corps de
    `POST /api/debrief/uploads/{id}/deplacer`. `session_id` est obligatoire et
    peut valoir `null` : le fichier part alors vers une mission neuve."""

    session_id: Optional[uuid.UUID]


class FusionnerPayload(BaseModel):
    """Lot « Le rattachement des dépôts » (v1.0052) : corps de
    `POST /api/debrief/sessions/{id}/fusionner` -- la mission absorbée."""

    source_id: uuid.UUID


class PeriodeVolPayload(BaseModel):
    """Lot « Les heures de jour et de nuit » (v1.0068) : corps de
    `PATCH /api/debrief/sessions/{id}/flights/{flight_id}/periode` -- la
    période voulue ; toute autre valeur est un 422."""

    periode: Literal["jour", "nuit"]


class CartesDcsPayload(BaseModel):
    """Corps de `PUT /api/debrief/dossier/cartes` (lot « Les cartes DCS de
    chaque pilote ») : les cartes que le pilote déclare posséder. Une valeur
    hors de `MAPS` (casse comprise) est refusée en 422 ; sinon la liste est
    rendue dans l'ordre de `CARTES_DCS`, sans doublon."""

    cartes: list[str] = Field(max_length=64)

    @field_validator("cartes")
    @classmethod
    def _cartes_connues(cls, v: list[str]) -> list[str]:
        for c in v:
            if c not in MAPS:
                raise ValueError(f"Carte inconnue : {c!r}")
        voulues = set(v)
        return [c for c in CARTES_DCS if c in voulues]
