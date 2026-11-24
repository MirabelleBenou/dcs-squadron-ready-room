"""Lot « Mission ou training » : la nature d'une session, hors ligne -- ni base,
ni réseau.

1. `test_payload_nature` -- `SessionEditPayload` accepte `training` et refuse
   toute autre valeur.
2. `test_nature_depot` -- la validation pure de la nature choisie dans
   « Déposer » (`_nature_depot`).
3. `test_vols_par_nature` -- le partage des couples (vol, session) du dossier
   selon `session.nature` (`_vols_par_nature`), dans l'ordre d'entrée.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _nature_depot, _vols_par_nature
from app.debrief.schemas import SessionEditPayload


def test_payload_nature():
    assert SessionEditPayload(nature="training").nature == "training"
    assert SessionEditPayload(nature="mission").nature == "mission"
    with pytest.raises(ValidationError):
        SessionEditPayload(nature="exercice")


def test_nature_depot():
    assert _nature_depot(None) is None
    assert _nature_depot("") is None
    assert _nature_depot("mission") == "mission"
    assert _nature_depot("training") == "training"
    with pytest.raises(ValueError):
        _nature_depot("Mission")
    with pytest.raises(ValueError):
        _nature_depot("autre")


def test_vols_par_nature():
    mission_a = NS(id="sa", nature="mission")
    mission_b = NS(id="sb", nature="mission")
    training = NS(id="st", nature="training")
    v1, v2, v3, v4 = NS(id="v1"), NS(id="v2"), NS(id="v3"), NS(id="v4")
    couples = [(v1, mission_a), (v2, training), (v3, mission_b), (v4, training)]
    par_nature = _vols_par_nature(couples)
    assert list(par_nature) == ["mission", "training"]
    assert par_nature["mission"] == [(v1, mission_a), (v3, mission_b)]
    assert par_nature["training"] == [(v2, training), (v4, training)]
    assert _vols_par_nature([]) == {"mission": [], "training": []}
