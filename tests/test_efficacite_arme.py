"""Lot « L'efficacité par arme au Dossier » (v1.0048) : les règles du cadrage
§3.1, hors ligne, sur des vols fabriqués -- ni base, ni journal réel, ni clé
API. La part privée du dossier (`_dossier_prive`) dit, par arme, combien des
cibles touchées le pilote a détruites, avec n'importe laquelle de ses armes.

1. `test_le_compte` -- deux lignes de la même arme dans deux vols fiables de
   la même session, des cibles distinctes, des kills sur une partie d'entre
   elles : les deux clés justes.
2. `test_n_importe_quelle_arme` -- un kill d'une autre arme, et un kill sans
   arme (l'explosion d'une épave) : les deux détruisent la cible touchée.
3. `test_la_session_compte` -- un kill d'un autre vol de la même session
   compte ; le même identifiant détruit dans une autre session ne compte pas.
4. `test_la_forme` -- un vol non fiable n'apporte rien ; une arme fiable sans
   cible touchée n'a aucune des deux clés ; une arme sans ligne n'en reçoit pas.
5. `test_canon_et_nature` -- une ligne `cannon: true` alimente `canon`, pas
   `precision` ; une cible d'une session de training n'entre pas dans le compte
   des missions.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _dossier_prive, _vols_par_nature

ARME = "9M114"
CANON = "GSh-30-2K"


def _session(sid: str, nature: str = "mission") -> SimpleNamespace:
    return SimpleNamespace(
        id=sid, mission_date=None, display_name="M", title="M", campaign_id=None, nature=nature
    )


def _tir(arme: str, cibles: list[str], canon: bool = False) -> dict:
    """Une ligne de tir de `stats["bursts"]`, telle que le moteur la donne."""
    return {"weapon": arme, "target_object_ids": cibles, **({"cannon": True} if canon else {})}


def _kill(cible: str, arme: str | None = None) -> dict:
    """Une destruction de `stats["kills"]` ; `arme` vide = l'explosion d'une épave."""
    return {"target_object_id": cible, "weapon": arme, "target_unit_type": "T-72B"}


def _vol(fid: str, fiable: bool = True, tirs=None, bursts=(), kills=(), canon=None) -> SimpleNamespace:
    stats: dict = {
        "precision_reliability": "fiable" if fiable else "partielle",
        "bursts": list(bursts),
        "kills": list(kills),
    }
    if tirs is not None:
        stats["shots_by_weapon"] = tirs
    if canon is not None:
        stats["cannon_by_weapon"] = canon
    return SimpleNamespace(id=fid, stats=stats, aircraft_type="Mi-24P", coalition="2", t_start=0.0, t_end=1.0)


def _ligne(dossier: dict, arme: str, cle: str = "precision") -> dict:
    return next(p for p in dossier[cle] if p["arme"] == arme)


def test_le_compte() -> None:
    s = _session("s1")
    f1 = _vol(
        "f1", tirs={ARME: {"shots": 5, "touched": 3}},
        bursts=[_tir(ARME, ["t1", "t2"]), _tir(ARME, ["t3"])],
        kills=[_kill("t1", ARME), _kill("t3", ARME)],
    )
    f2 = _vol(
        "f2", tirs={ARME: {"shots": 3, "touched": 2}},
        bursts=[_tir(ARME, ["t4", "t5"])],
        kills=[_kill("t5", ARME)],
    )
    d = _dossier_prive([(f1, s), (f2, s)], {}, {})
    # Les clés d'avant gardent leurs valeurs ; les deux nouvelles s'y ajoutent.
    assert _ligne(d, ARME) == {
        "arme": ARME, "tirs": 8, "touches": 5, "largages": 0,
        "cibles_touchees": 5, "cibles_detruites": 3,
    }


def test_n_importe_quelle_arme() -> None:
    s = _session("s1")
    f1 = _vol(
        "f1", tirs={ARME: {"shots": 3, "touched": 3}},
        bursts=[_tir(ARME, ["t1", "t2", "t3"])],
        kills=[
            _kill("t1", "S-13OF"),   # détruite par une autre arme
            _kill("t2", None),       # détruite par l'explosion d'une épave
        ],
    )
    d = _dossier_prive([(f1, s)], {}, {})
    ligne = _ligne(d, ARME)
    assert ligne["cibles_touchees"] == 3
    assert ligne["cibles_detruites"] == 2   # t3 n'a pas été détruite


def test_la_session_compte() -> None:
    s1, s2 = _session("s1"), _session("s2")
    # Session 1 : le pilote touche t1 et t2 sur un premier appareil, puis repart
    # sur un autre qui détruit t1 -- t1 est détruite, t2 ne l'est pas.
    f1 = _vol("f1", tirs={ARME: {"shots": 2, "touched": 2}}, bursts=[_tir(ARME, ["t1", "t2"])])
    f2 = _vol("f2", kills=[_kill("t1", "S-13OF")])
    # Session 2 : le même identifiant t1 est touché ; seul t2 y est détruit.
    f3 = _vol("f3", tirs={ARME: {"shots": 1, "touched": 1}}, bursts=[_tir(ARME, ["t1"])], kills=[_kill("t2", ARME)])
    d = _dossier_prive([(f1, s1), (f2, s1), (f3, s2)], {}, {})
    ligne = _ligne(d, ARME)
    # Trois couples (session, cible) : (s1, t1), (s1, t2), (s2, t1) ; un seul détruit, (s1, t1).
    assert ligne["cibles_touchees"] == 3
    assert ligne["cibles_detruites"] == 1


def test_la_forme() -> None:
    s = _session("s1")
    # Une arme fiable dont aucune ligne de tir ne touche : aucune des deux clés.
    f1 = _vol("f1", tirs={ARME: {"shots": 2, "touched": 0}}, bursts=[_tir(ARME, [])], kills=[_kill("t1", ARME)])
    # Un vol non fiable apporte ni touches ni cibles : sa ligne de tir sur une autre arme n'ouvre rien.
    f2 = _vol(
        "f2", fiable=False, tirs={"S-13OF": {"shots": 4, "touched": 4}},
        bursts=[_tir(ARME, ["t1"]), _tir("S-13OF", ["t9"])],
    )
    # Une ligne de tir fiable dont l'arme n'a pas de ligne dans `precision` : aucune ligne créée.
    f3 = _vol("f3", tirs={}, bursts=[_tir("AIM-9", ["t7"])])
    d = _dossier_prive([(f1, s), (f2, s), (f3, s)], {}, {})
    assert d["precision"] == [{"arme": ARME, "tirs": 2, "touches": 0, "largages": 0}]
    assert "canon" not in d


def test_canon_et_nature() -> None:
    # Le canon : la ligne `cannon: true` donne les clés à `canon`, pas à `precision`.
    s = _session("s1")
    f1 = _vol(
        "f1", tirs={ARME: {"shots": 1, "touched": 1}},
        canon={CANON: {"bursts": 4, "rounds": 120, "bursts_hit": 2, "rounds_hit": 9}},
        bursts=[_tir(ARME, ["t1"]), _tir(CANON, ["t2", "t3"], canon=True)],
        kills=[_kill("t2", CANON)],
    )
    d = _dossier_prive([(f1, s)], {}, {})
    assert _ligne(d, ARME) == {
        "arme": ARME, "tirs": 1, "touches": 1, "largages": 0, "cibles_touchees": 1, "cibles_detruites": 0,
    }
    assert _ligne(d, CANON, "canon") == {
        "arme": CANON, "rafales": 4, "obus": 120, "rafales_touchees": 2, "obus_au_but": 9,
        "cibles_touchees": 2, "cibles_detruites": 1,
    }

    # La nature : une cible d'une session de training n'entre pas dans le compte des missions.
    mission, training = _session("m1"), _session("t1", nature="training")
    fm = _vol("fm", tirs={ARME: {"shots": 1, "touched": 1}}, bursts=[_tir(ARME, ["c1"])], kills=[_kill("c1", ARME)])
    ft = _vol("ft", tirs={ARME: {"shots": 1, "touched": 1}}, bursts=[_tir(ARME, ["c7"])], kills=[_kill("c8", ARME)])
    couples = [(fm, mission), (ft, training)]
    par_nature = _vols_par_nature(couples)
    des_missions = _ligne(_dossier_prive(par_nature["mission"], {}, {}), ARME)
    du_training = _ligne(_dossier_prive(par_nature["training"], {}, {}), ARME)
    assert (des_missions["cibles_touchees"], des_missions["cibles_detruites"]) == (1, 1)
    assert (du_training["cibles_touchees"], du_training["cibles_detruites"]) == (1, 0)
    tout = _ligne(_dossier_prive(couples, {}, {}), ARME)
    assert (tout["cibles_touchees"], tout["cibles_detruites"]) == (2, 1)
