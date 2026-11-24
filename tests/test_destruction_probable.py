"""Lot « Le Débrief : la destruction probable » (v1.0056, R10) : une unité que
les journaux donnent morte sans tueur reçoit celui que l'ACMI désigne
(`engine._kills_probables`), et `parse_acmi` dit quels objets ont été retirés
(`AcmiObject.retire`). Invariants déterministes, hors ligne : quatre sessions
de production réduites en fixtures (`tests/fixtures/destruction_probable_*.json`)
et un petit ACMI fabriqué en mémoire.
"""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import acmi as acmi_mod
from app.debrief import engine

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _charger(session: str) -> tuple[list[engine.MergedEvent], acmi_mod.AcmiData]:
    """Un `MergedEvent` par ligne d'`evenements`, un `AcmiObject` par ligne
    d'`acmi`, `AcmiMeta()` vide."""
    d = json.loads((_FIXTURES / f"destruction_probable_{session}.json").read_text(encoding="utf-8"))
    evenements = [
        engine.MergedEvent(
            type=typ, t=t, initiator_object_id=ioid, target_object_id=toid,
            initiator_unit_type=iut, target_unit_type=tut, weapon=arme,
            target_coalition=camp, weapon_family=famille,
        )
        for typ, t, ioid, toid, iut, tut, arme, camp, famille in d["evenements"]
    ]
    objets = {
        tid: acmi_mod.AcmiObject(
            track_id=tid, type=typ, name=nom, coalition=camp,
            t_spawn=apparition, t_despawn=retrait, retire=retire,
        )
        for tid, typ, nom, camp, apparition, retrait, retire in d["acmi"]
    }
    return evenements, acmi_mod.AcmiData(meta=acmi_mod.AcmiMeta(), objects=objets)


def _kills(session: str) -> list[engine.MergedEvent]:
    evenements, acmi_data = _charger(session)
    return engine._kills_probables(evenements, acmi_data)


def _sur(kills: list[engine.MergedEvent], cible: str) -> list[engine.MergedEvent]:
    return [k for k in kills if k.target_object_id == cible]


def test_26_octobre_le_vulcan():
    (k,) = _sur(_kills("783ba454"), "17133569")
    assert k.type == "kill"
    assert k.initiator_object_id == "16779531"
    assert k.weapon == "S-13OF"
    assert k.t == 4518.378


def test_26_octobre_l_uaz():
    (k,) = _sur(_kills("783ba454"), "17134081")
    assert k.initiator_object_id == "16779274"


def test_26_octobre_le_mi8_abattu_par_un_ks19():
    (k,) = _sur(_kills("783ba454"), "16779533")
    assert k.initiator_object_id == "16993537"
    assert k.weapon == "UOF412 (100mm HE)"


def test_26_octobre_trois_kills():
    assert len(_kills("783ba454")) == 3


def test_12_octobre_treize_kills_dont_douze_collateraux():
    kills = _kills("40eb5f03")
    assert len(kills) == 13
    samp = [k for k in kills if k.initiator_object_id == "16779270" and k.weapon == "SAMP-250 HD"]
    assert len(samp) == 12
    (k,) = _sur(kills, "16787719")
    assert k.initiator_object_id == "17150721"


def test_6_et_27_juillet_aucun_kill():
    assert _kills("28dbf799") == []
    assert _kills("e29ea43b") == []


def test_sans_acmi_ou_sans_recalage():
    assert engine._kills_probables([], None) == []
    acmi_data = acmi_mod.AcmiData(objects={
        "a1": acmi_mod.AcmiObject(track_id="a1", type="Weapon+Missile", t_spawn=100.0, t_despawn=110.0, retire=True),
    })
    tirs = [
        engine.MergedEvent(type="shot", t=99.0 + i, initiator_object_id="1", target_object_id=None,
                           initiator_unit_type="F-4E-45MC", target_unit_type=None, weapon="AIM-9J")
        for i in range(3)
    ]
    assert engine._kills_probables(tirs, acmi_data) == []


def test_aucune_cible_deja_tuee():
    for session in ("783ba454", "40eb5f03", "28dbf799", "e29ea43b"):
        evenements, acmi_data = _charger(session)
        deja = {e.target_object_id for e in evenements if e.type == "kill"}
        for k in engine._kills_probables(evenements, acmi_data):
            assert k.target_object_id not in deja


def test_parse_acmi_retire():
    texte = "\n".join([
        "FileType=text/acmi/tacview",
        "FileVersion=2.2",
        "0,ReferenceTime=2026-10-26T12:00:00Z",
        "#0.00",
        "101,T=1|2|3,Type=Air+Rotorcraft,Name=Mi-24P,Color=Red",
        "102,T=1|2|3,Type=Ground+Vehicle,Name=Vulcan,Color=Blue",
        "#5.50",
        "-102",
        "#9.25",
        "101,T=1|2|4",
        "",
    ])
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as zf:
        zf.writestr("essai.txt.acmi", texte)
    tampon.seek(0)
    objets = acmi_mod.parse_acmi(tampon).objects
    assert objets["102"].retire is True
    assert objets["102"].t_despawn == 5.5
    assert objets["101"].retire is False
    assert objets["101"].t_despawn == 9.25


def test_26_octobre_ordre_inverse():
    evenements, acmi_data = _charger("783ba454")
    assert engine._kills_probables(evenements, acmi_data) == engine._kills_probables(
        list(reversed(evenements)), acmi_data
    )
