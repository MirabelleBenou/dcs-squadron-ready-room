"""Lot « Les cartes DCS de chaque pilote » (v1.0085, R640), hors ligne -- pas de base.

1. `test_la_liste_des_cartes` -- `CARTES_DCS` porte les quatorze cartes dans l'ordre
   d'affichage ; `MAPS` en est l'ensemble.
2. `test_le_miroir_js` -- les chaînes de `const MAPS = [...]` d'`app.js` égalent `CARTES_DCS`.
3. `test_declaration_ordonnee_sans_doublon` -- la déclaration se rend dans l'ordre de la liste,
   sans doublon ; vide reste vide.
4. `test_carte_hors_liste_refusee` -- une valeur hors liste, casse comprise, est refusée ; au-delà
   de 64 valeurs, la liste l'est aussi.
5. `test_escadre_porte_les_cartes` -- `_escadre_payload` rend `cartes_dcs` tel quel (liste,
   `None`, `[]`), pour un membre d'escadrille comme pour un sans-escadrille.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _escadre_payload
from app.debrief.schemas import CartesDcsPayload
from app.schemas import CARTES_DCS, MAPS

LES_QUATORZE = (
    "Syria", "Germany (Cold War)", "Caucasus", "Marianas", "Normandy",
    "Afghanistan", "Persian Gulf", "Sinai", "Iraq", "Kola",
    "South Atlantic", "Nevada", "The Channel", "Marianas WWII",
)


def test_la_liste_des_cartes() -> None:
    assert CARTES_DCS == LES_QUATORZE
    assert MAPS == frozenset(CARTES_DCS)
    assert len(MAPS) == 14


def test_le_miroir_js() -> None:
    source = (Path(__file__).resolve().parent.parent / "app" / "static" / "app.js").read_text(encoding="utf-8")
    bloc = re.search(r"const MAPS = \[(.*?)\];", source, re.S)
    assert bloc is not None
    assert tuple(re.findall(r'"([^"]+)"', bloc.group(1))) == CARTES_DCS


def test_declaration_ordonnee_sans_doublon() -> None:
    assert CartesDcsPayload(cartes=["Nevada", "Syria", "Nevada"]).cartes == ["Syria", "Nevada"]
    assert CartesDcsPayload(cartes=[]).cartes == []


def test_carte_hors_liste_refusee() -> None:
    for valeur in ("Mars", "syria"):
        with pytest.raises(ValidationError):
            CartesDcsPayload(cartes=["Syria", valeur])
    # Addendum 1 (A4) : la liste est bornée.
    with pytest.raises(ValidationError):
        CartesDcsPayload(cartes=["Syria"] * 65)


def test_escadre_porte_les_cartes() -> None:
    def profil(pid: int, nom: str, cartes) -> NS:
        return NS(id=pid, global_name=nom, username=nom.lower(), avatar_hash=None, cartes_dcs=cartes)

    escadrilles = [NS(id=1, designation="CHARLIE-33", status="actif", aircraft=None, crest_sha=None, callsign=None, full_name=None)]
    lignes = [
        (profil(11, "Alpha", ["Syria"]), 1, "member"),
        (profil(12, "Bravo", None), 1, "member"),
        (profil(13, "Charlie", []), 1, "member"),
        (profil(21, "Delta", ["Syria"]), None, None),
        (profil(22, "Echo", None), None, None),
        (profil(23, "Foxtrot", []), None, None),
    ]
    p = _escadre_payload(NS(designation="1st EXAW"), escadrilles, lignes, ["dcs"], {})
    assert {m["name"]: m["cartes_dcs"] for m in p["squadrons"][0]["members"]} == {"Alpha": ["Syria"], "Bravo": None, "Charlie": []}
    assert {m["name"]: m["cartes_dcs"] for m in p["free_agents"]} == {"Delta": ["Syria"], "Echo": None, "Foxtrot": []}
