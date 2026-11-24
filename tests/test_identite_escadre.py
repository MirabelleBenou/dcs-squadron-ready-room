"""Lot « L'écran Escadre du Centre » : l'identité de l'escadre, hors ligne --
ni base, ni réseau.

1. `test_identite_normalisee` -- désignation et tag rognés ; sigle mis en
   capitales ; nom complet, période ou sigle vides -> `None`.
2. `test_identite_refusee` -- désignation vide, tag vide, sigle « EX AW » et
   sigle de 13 caractères, période de 61 caractères : chacun lève
   `ValueError` avec son message.
3. `test_wing_dict` -- `_wing_to_dict` rend exactement les six clés, NULL
   compris.
4. `test_chemin_embleme` -- le chemin de l'emblème finit par `wing.png`, et
   diffère de `crest_path(n)` pour tout `n` de 1 à 50.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import crests
from app.command.api import _valider_identite_escadre, _wing_to_dict
from app.config import settings


def test_identite_normalisee():
    out = _valider_identite_escadre({
        "designation": "  5th TEST  ",
        "tag": "  5th TEST ",
        "sigle": "  tst-1 ",
        "full_name": "  5th Test Wing ",
        "period": " Guerre froide ",
    })
    assert out == {
        "designation": "5th TEST",
        "tag": "5th TEST",
        "sigle": "TST-1",
        "full_name": "5th Test Wing",
        "period": "Guerre froide",
    }
    # Vides -> None ; seuls les champs présents sont rendus.
    out = _valider_identite_escadre({"full_name": "   ", "period": "", "sigle": "  "})
    assert out == {"full_name": None, "period": None, "sigle": None}
    assert _valider_identite_escadre({}) == {}
    # Aux plafonds exacts : accepté.
    assert _valider_identite_escadre({"designation": "A" * 40, "tag": "B" * 40})["tag"] == "B" * 40
    assert _valider_identite_escadre({"full_name": "C" * 120, "period": "D" * 60, "sigle": "E" * 12})["sigle"] == "E" * 12


def test_identite_refusee():
    sigle = "Le sigle ne prend que des lettres, des chiffres et le tiret, douze au plus."
    cas = [
        ({"designation": "   "}, "La désignation ne peut pas être vide."),
        ({"designation": None}, "La désignation ne peut pas être vide."),
        ({"tag": ""}, "Le tag ne peut pas être vide."),
        ({"sigle": "EX AW"}, sigle),
        ({"sigle": "ABCDEFGHIJKLM"}, sigle),
        ({"period": "x" * 61}, "Période : 60 caractères au plus."),
        ({"designation": "x" * 41}, "Désignation : 40 caractères au plus."),
        ({"tag": "x" * 41}, "Tag : 40 caractères au plus."),
        ({"full_name": "x" * 121}, "Nom complet : 120 caractères au plus."),
    ]
    for champs, message in cas:
        with pytest.raises(ValueError) as exc:
            _valider_identite_escadre(champs)
        assert str(exc.value) == message


def test_wing_dict():
    plein = NS(designation="1st EXAW", full_name="Example Air Wing",
               period="Guerre froide · 1980–1990", sigle="EXAW", tag="1st EXAW", emblem_sha="ab12")
    assert _wing_to_dict(plein) == {
        "designation": "1st EXAW",
        "full_name": "Example Air Wing",
        "period": "Guerre froide · 1980–1990",
        "sigle": "EXAW",
        "tag": "1st EXAW",
        "emblem_sha": "ab12",
    }
    vide = NS(designation="X", full_name=None, period=None, sigle=None, tag="X", emblem_sha=None)
    d = _wing_to_dict(vide)
    assert set(d) == {"designation", "full_name", "period", "sigle", "tag", "emblem_sha"}
    assert d["full_name"] is None and d["period"] is None and d["sigle"] is None and d["emblem_sha"] is None


def test_chemin_embleme(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CREST_STORAGE_DIR", str(tmp_path))
    p = crests.wing_emblem_path()
    assert p.name == "wing.png"
    for n in range(1, 51):
        assert p != crests.crest_path(n)
