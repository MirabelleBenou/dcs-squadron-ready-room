"""Lot « La config d'escadre de Mission Plan fabriquée par le Centre » (v1.0091) --
les livrées d'une escadrille au Centre : la table des appareils (codes du Centre
-> types DCS) contre la liste des types jouables d'HQ, la normalisation de ce que
`PATCH /command/squadrons/{id}` reçoit, l'élagage quand les appareils changent,
la forme rendue et le détail du journal.

Sept tests, sans base ni réseau : les fonctions pures de `app/command/api.py`,
sur des objets minimaux (`SimpleNamespace`).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.command import api as cmd
from app.schemas import AIRCRAFT_CODES

_RACINE = Path(__file__).resolve().parent.parent
_APPAREILS = ["Mi-24P", "Mi-8", "A-4E-C"]


def _refus(fonction, *args) -> str:
    with pytest.raises(HTTPException) as e:
        fonction(*args)
    assert e.value.status_code == 422
    return e.value.detail


def test_table_types_dans_hq():
    table = json.loads((_RACINE / "app" / "static" / "dcs_types_livrees.json").read_text("utf-8"))
    hq = json.loads((_RACINE / "tests" / "fixtures" / "types_dcs_hq.json").read_text("utf-8"))
    jouables = set(hq["helicopters"]) | set(hq["planes"])
    types = table["types"]
    for code, types_dcs in types.items():
        for type_dcs in types_dcs:
            assert type_dcs in jouables, f"{code} : {type_dcs} inconnu d'HQ"
    # Un code ajouté à AIRCRAFT_CODES sans ligne dans la table casse ; une ligne en trop aussi.
    assert set(types) == set(AIRCRAFT_CODES)


def test_normaliser_livrees():
    brut = [
        {"name": "  CHARLIE-33 Grau ", "aircraft": ["mi-24p", "MI-8", "Mi-24P", "  "], "jeu": False},
        {"name": "GDR Mi-24P", "aircraft": ["Mi-24P"], "jeu": True},
        {"name": "Mod", "aircraft": ["a-4e-c"]},
    ]
    assert cmd._normaliser_livrees(brut, _APPAREILS) == [
        {"name": "CHARLIE-33 Grau", "aircraft": ["Mi-24P", "Mi-8"], "jeu": False},
        {"name": "GDR Mi-24P", "aircraft": ["Mi-24P"], "jeu": True},
        {"name": "Mod", "aircraft": ["A-4E-C"], "jeu": False},
    ]
    assert cmd._normaliser_livrees([], _APPAREILS) is None
    assert cmd._normaliser_livrees(None, _APPAREILS) is None


def test_normaliser_livrees_refus():
    normaliser = cmd._normaliser_livrees
    ok = {"name": "Une", "aircraft": ["Mi-24P"]}
    assert _refus(normaliser, [{"name": "  ", "aircraft": ["Mi-24P"]}], _APPAREILS) == "Chaque livrée a un nom."
    assert _refus(normaliser, [{"name": "x" * 81, "aircraft": ["Mi-24P"]}], _APPAREILS) == (
        "Le nom d'une livrée tient en 80 caractères."
    )
    assert _refus(normaliser, [{"name": "Vide", "aircraft": []}], _APPAREILS) == "La livrée Vide n'a aucun appareil."
    assert _refus(normaliser, [{"name": "Hors", "aircraft": ["F-4E"]}], _APPAREILS) == (
        "La livrée Hors porte un appareil que l'escadrille ne déclare pas."
    )
    assert _refus(normaliser, [ok, {"name": " une ", "aircraft": ["Mi-8"]}], _APPAREILS) == (
        "La livrée une est en double."
    )
    assert _refus(normaliser, [{"name": f"L{i}", "aircraft": ["Mi-8"]} for i in range(31)], _APPAREILS) == (
        "30 livrées au plus par escadrille."
    )
    # 80 caractères pile, 30 livrées pile : acceptés.
    assert cmd._normaliser_livrees([{"name": "x" * 80, "aircraft": ["Mi-8"]}], _APPAREILS)
    assert len(cmd._normaliser_livrees([{"name": f"L{i}", "aircraft": ["Mi-8"]} for i in range(30)], _APPAREILS)) == 30


def test_normaliser_defauts():
    defauts = cmd._normaliser_defauts(
        {"mi-24p": "  CHARLIE-33 Grau ", "Mi-8": "   ", "a-4e-c": "Mod"}, _APPAREILS
    )
    assert defauts == {"Mi-24P": "CHARLIE-33 Grau", "A-4E-C": "Mod"}
    assert cmd._normaliser_defauts({"Mi-8": " "}, _APPAREILS) is None
    assert cmd._normaliser_defauts({}, _APPAREILS) is None
    assert cmd._normaliser_defauts(None, _APPAREILS) is None
    assert _refus(cmd._normaliser_defauts, {"F-4E": "X"}, _APPAREILS) == (
        "La livrée par défaut porte un appareil que l'escadrille ne déclare pas."
    )
    assert _refus(cmd._normaliser_defauts, {"Mi-8": "y" * 81}, _APPAREILS) == (
        "Le nom d'une livrée tient en 80 caractères."
    )


def test_elaguer():
    livrees = [
        {"name": "Deux", "aircraft": ["Mi-24P", "Mi-8"], "jeu": False},
        {"name": "Seule", "aircraft": ["Mi-8"], "jeu": True},
    ]
    defauts = {"Mi-24P": "Deux", "Mi-8": "Seule"}
    # Mi-8 retiré : il quitte la livrée « Deux », « Seule » n'a plus d'appareil et part, son défaut aussi.
    assert cmd._elaguer_livrees(livrees, defauts, ["Mi-24P"]) == (
        [{"name": "Deux", "aircraft": ["Mi-24P"], "jeu": False}],
        {"Mi-24P": "Deux"},
    )
    # Plus aucun appareil : tout part, les deux valeurs deviennent None.
    assert cmd._elaguer_livrees(livrees, defauts, []) == (None, None)
    assert cmd._elaguer_livrees(None, None, ["Mi-24P"]) == (None, None)


def test_squadron_to_dict():
    base = dict(
        id=3, designation="CHARLIE-33", callsign=None, full_name=None, nickname=None, status="actif",
        discord_role_id=None, crest_sha=None, aircraft=None,
    )
    vide = cmd._squadron_to_dict(SimpleNamespace(**base, liveries=None, default_liveries=None))
    assert vide["liveries"] == [] and vide["default_liveries"] == {}
    assert vide["nickname"] is None
    livrees = [{"name": "Grau", "aircraft": ["Mi-24P"], "jeu": False}]
    rempli = cmd._squadron_to_dict(
        SimpleNamespace(**base, liveries=livrees, default_liveries={"Mi-24P": "Grau"})
    )
    assert rempli["liveries"] == livrees and rempli["default_liveries"] == {"Mi-24P": "Grau"}


def test_journal_livrees():
    sq = SimpleNamespace(
        designation="CHARLIE-33", callsign="Dragoon", full_name=None, nickname="Aigle", discord_role_id=None,
        aircraft=["Mi-24P", "Mi-8"],
        liveries=[{"name": "Nom", "aircraft": ["Mi-24P", "Mi-8"], "jeu": False}],
        default_liveries={"Mi-24P": "Nom"},
    )
    etat = cmd._etat_escadrille(sq)
    assert etat["liveries"] == ["Nom (Mi-24P, Mi-8)"]
    assert etat["default_liveries"] == ["Mi-24P : Nom"]
    assert etat["nickname"] == "Aigle"
    # Ce que le journal écrit : ajouté et retiré.
    avant = cmd._etat_escadrille(SimpleNamespace(**{**sq.__dict__, "liveries": None, "default_liveries": None}))
    lignes = cmd.journal.ecarts(avant, etat)
    assert {"champ": "liveries", "ajoutes": ["Nom (Mi-24P, Mi-8)"], "retires": []} in lignes
    assert {"champ": "default_liveries", "ajoutes": ["Mi-24P : Nom"], "retires": []} in lignes


def test_livrees_du_jeu_dans_hq():
    # Lot « livrées du jeu de tous les types » (v1.0097) : la section `livrees` de la table
    # ne porte que des types jouables d'HQ, chacun avec une liste non vide et sans doublon.
    table = json.loads((_RACINE / "app" / "static" / "dcs_types_livrees.json").read_text("utf-8"))
    hq = json.loads((_RACINE / "tests" / "fixtures" / "types_dcs_hq.json").read_text("utf-8"))
    jouables = set(hq["helicopters"]) | set(hq["planes"])
    assert table["livrees"]
    for type_dcs, noms in table["livrees"].items():
        assert type_dcs in jouables, type_dcs
        assert noms, type_dcs
        assert len(noms) == len(set(noms)), type_dcs
