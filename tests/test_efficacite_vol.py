"""Lot « L'efficacité par arme sur l'écran Vol » (v1.0049, R276) : la règle de
l'efficacité n'est écrite qu'une fois (`_efficacite_par_arme`) et sert le
Dossier comme l'écran Vol (`get_flight`). Hors ligne, sur des vols fabriqués
et sur la fixture Francfort -- ni base, ni journal réel, ni clé API.

1. `test_un_vol` -- des lignes de tir d'une arme et d'un canon, des kills du
   vol sur une partie des cibles : les deux dictionnaires justes, le canon
   séparé, une arme sans cible touchée absente.
2. `test_le_pilote_et_le_vol_anonyme` -- une cible du vol détruite par un autre
   vol du même membre dans la session : détruite ; la même situation pour un
   vol sans membre : pas détruite.
3. `test_equivalence_francfort` -- sur la fixture Francfort, pour chaque membre
   qui n'y a qu'un vol fiable, son Dossier et la règle de `get_flight` donnent
   les mêmes `cibles_touchees` et `cibles_detruites`.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _destructions_du_vol, _dossier_prive, _efficacite_par_arme

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "89f20c83-54ec-4fd4-bf0c-1700463ff155.json"

ARME = "9M114"
CANON = "GSh-30-2K"


def _tir(arme: str, cibles: list[str], canon: bool = False) -> dict:
    """Une ligne de tir de `stats["bursts"]`, telle que le moteur la donne."""
    return {"weapon": arme, "target_object_ids": cibles, **({"cannon": True} if canon else {})}


def _kill(cible: str, arme: str | None = None) -> dict:
    """Une destruction de `stats["kills"]` ; `arme` vide = l'explosion d'une épave."""
    return {"target_object_id": cible, "weapon": arme, "target_unit_type": "T-72B"}


def _vol(pid: int | None, bursts=(), kills=()) -> NS:
    return NS(pilote_profile_id=pid, stats={"bursts": list(bursts), "kills": list(kills)})


def _de_ce_vol(vol: NS, vols_session: list, session_id: str = "s1") -> dict:
    """Ce que `get_flight` rend sous `efficacite` : les tirs du seul vol, les
    destructions de son pilote dans la session."""
    return _efficacite_par_arme(
        ((session_id, ligne) for ligne in vol.stats["bursts"]),
        {session_id: _destructions_du_vol(vol, vols_session)},
    )


def test_un_vol() -> None:
    vol = _vol(
        7,
        bursts=[
            _tir(ARME, ["t1", "t2"]), _tir(ARME, ["t3"]),
            _tir(CANON, ["t1", "t4"], canon=True),
            _tir("R-60M", []),  # aucune cible touchée : l'arme n'entre pas
        ],
        kills=[_kill("t1", ARME), _kill("t3", None), _kill("t9", "R-60M")],
    )
    assert _de_ce_vol(vol, [vol]) == {
        "precision": {ARME: {"cibles_touchees": 3, "cibles_detruites": 2}},
        "canon": {CANON: {"cibles_touchees": 2, "cibles_detruites": 1}},
    }
    # Un vol sans tir ni destruction : les deux dictionnaires, vides.
    vide = _vol(7)
    assert _de_ce_vol(vide, [vide]) == {"precision": {}, "canon": {}}


def test_le_pilote_et_le_vol_anonyme() -> None:
    # Le membre 7 : un autre de ses vols a détruit t2 ; un vol d'un autre
    # membre a détruit t3, qui ne compte pas pour lui.
    a = _vol(7, bursts=[_tir(ARME, ["t1", "t2", "t3"])], kills=[_kill("t1", ARME)])
    b = _vol(7, kills=[_kill("t2", "Mk-82")])
    autre = _vol(8, kills=[_kill("t3", ARME)])
    assert _destructions_du_vol(a, [a, b, autre]) == {"t1", "t2"}
    assert _de_ce_vol(a, [a, b, autre])["precision"] == {ARME: {"cibles_touchees": 3, "cibles_detruites": 2}}

    # Le même cas sans membre rattaché : seules ses propres destructions.
    a = _vol(None, bursts=[_tir(ARME, ["t1", "t2", "t3"])], kills=[_kill("t1", ARME)])
    b = _vol(None, kills=[_kill("t2", "Mk-82")])
    autre = _vol(8, kills=[_kill("t3", ARME)])
    assert _destructions_du_vol(a, [a, b, autre]) == {"t1"}
    assert _de_ce_vol(a, [a, b, autre])["precision"] == {ARME: {"cibles_touchees": 3, "cibles_detruites": 1}}


def test_equivalence_francfort() -> None:
    d = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    session = NS(id=d["id"], mission_date=date.fromisoformat(d["mission_date"]), title=d["title"],
                 display_name=d["display_name"], campaign_id=None)
    vols = [NS(id=f["id"], session_id=d["id"], t_start=f["t_start"], t_end=f["t_end"],
               coalition=f["coalition"], object_id=f["object_id"], aircraft_type=f["aircraft_type"],
               stats=f["stats"], pilote_profile_id=f["pilote_profile_id"]) for f in d["flights"]]
    camps = {d["id"]: {str(v.object_id): v.coalition for v in vols if v.object_id is not None}}

    membres = {v.pilote_profile_id for v in vols if v.pilote_profile_id is not None}
    verifies = 0
    for pid in membres:
        siens = [v for v in vols if v.pilote_profile_id == pid]
        fiables = [v for v in siens if v.stats.get("precision_reliability") == "fiable"]
        if len(fiables) != 1:
            continue
        dossier = _dossier_prive([(v, session) for v in siens], camps, {})
        vu = _efficacite_par_arme(
            ((session.id, ligne) for ligne in fiables[0].stats.get("bursts") or []),
            {session.id: _destructions_du_vol(fiables[0], vols)},
        )
        for forme in ("precision", "canon"):
            lignes = {l["arme"]: l for l in dossier.get(forme, [])}
            # Les armes que le Dossier chiffre sont celles que l'écran Vol chiffre.
            assert {a for a, l in lignes.items() if "cibles_touchees" in l} == set(vu[forme])
            for arme, eff in vu[forme].items():
                assert (lignes[arme]["cibles_touchees"], lignes[arme]["cibles_detruites"]) == (
                    eff["cibles_touchees"], eff["cibles_detruites"])
                verifies += 1
    assert verifies >= 1
