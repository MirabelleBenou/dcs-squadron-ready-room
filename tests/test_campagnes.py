"""Lot « Les campagnes — les données » : le registre des campagnes
(`_registre_campagnes`) et la fiche d'une campagne (`_fiche_campagne`), hors
ligne -- ni base, ni réseau.

1. `test_registre` -- en cours d'abord, fin de période décroissante, sans
   mission en dernier ; le rang par ordre de création ; période et missions.
2. `test_periode` -- une campagne sans mission ; une mission sans date ignorée
   pour la période mais comptée.
3. `test_vols_reels` -- un vol vide ne compte ni en sorties, ni en heures, ni
   au bilan, ni ne fait un participant.
4. `test_participants` -- deux missions pour un pilote présent sur deux ; un
   vol anonyme n'en fait aucun ; un archivé présent ; un Free Agent sans
   escadrille.
5. `test_bilan` -- le bilan égale `_bilan_additionne` sur les mêmes missions,
   et ne porte aucun identifiant de pilote.
6. `test_vols_de_l_escadre` -- lot « Le Débrief n'est plus en chantier, et
   l'escadre compte les siens » : un vol sans profil ne compte ni en sorties,
   ni en heures, ni au bilan, mais compte encore au nombre de vols de sa mission.
"""
from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _bilan_additionne, _fiche_campagne, _registre_campagnes

T72 = {"target_unit_type": "T-72B", "target_coalition": "1"}
BTR = {"target_unit_type": "BTR-80", "target_coalition": "1"}
AMI = {"target_unit_type": "Ural-375", "target_coalition": "2"}


def _c(cid, nom, status="en_cours"):
    return NS(id=cid, name=nom, status=status, map_name="Germany", sim="dcs", description="Ordre d'opérations")


def _s(sid, jour, camp, titre="m", nom=None):
    return NS(id=sid, mission_date=jour, title=titre, display_name=nom, campaign_id=camp)


def _v(sid, oid, pid=None, t=(0, 3600), kills=(), coa="2"):
    return NS(session_id=sid, object_id=oid, pilote_profile_id=pid, t_start=t[0], t_end=t[1],
              coalition=coa, stats={"kills": [dict(k) for k in kills]})


def _p(nom, archive=False):
    return NS(global_name=nom, username="u_" + nom, archived_at=datetime(2026, 9, 1) if archive else None)


def test_registre():
    campagnes = [_c("C1", "Foothold Germany"), _c("C2", "Ardennes 85", "close"),
                 _c("C3", "Fulda Gap"), _c("C4", "Vide")]
    sessions = [_s("a", date(2026, 7, 6), "C1"), _s("b", date(2026, 8, 17), "C1"),
                _s("c", date(2026, 9, 1), "C2"), _s("d", date(2026, 9, 20), "C3"),
                _s("e", None, None)]
    r = _registre_campagnes(campagnes, sessions)["campagnes"]
    assert [(c["id"], c["rang"], c["status"]) for c in r] == [
        ("C3", 3, "en_cours"), ("C1", 1, "en_cours"), ("C4", 4, "en_cours"), ("C2", 2, "close")]
    c1 = r[1]
    assert c1["periode"] == {"debut": "2026-07-06", "fin": "2026-08-17"}
    assert (c1["missions"], c1["name"], c1["map_name"], c1["sim"]) == (2, "Foothold Germany", "Germany", "dcs")
    assert sum(c["missions"] for c in r) == 4
    # À fin de période égale, le rang décroissant.
    r = _registre_campagnes(campagnes[:2] + [_c("C3", "Fulda Gap")],
                            [_s("a", date(2026, 9, 1), "C1"), _s("d", date(2026, 9, 1), "C3")])["campagnes"]
    assert [c["id"] for c in r] == ["C3", "C1", "C2"]


def test_periode():
    vide = _registre_campagnes([_c("C1", "Vide")], [])["campagnes"][0]
    assert vide["periode"] == {"debut": None, "fin": None} and vide["missions"] == 0
    f = _fiche_campagne(_c("C1", "Vide"), 1, [], {}, {}, {}, {})
    assert f["periode"] == {"debut": None, "fin": None}
    assert f["activite"] == {"missions": 0, "sorties": 0, "heures": 0.0, "pilotes": 0}
    assert (f["missions"], f["participants"]) == ([], [])
    assert f["bilan"] == {"kills_by_category": [], "n_kills_validated": 0, "n_fratricides": 0}
    sessions = [_s("a", date(2026, 8, 17), "C1", "m1"), _s("b", None, "C1", "Sans_date"),
                _s("c", date(2026, 9, 20), "C1", nom="Fulda")]
    r = _registre_campagnes([_c("C1", "Foothold")], sessions)["campagnes"][0]
    assert r["periode"] == {"debut": "2026-08-17", "fin": "2026-09-20"} and r["missions"] == 3
    f = _fiche_campagne(_c("C1", "Foothold"), 1, sessions, {}, {}, {}, {})
    assert f["periode"] == {"debut": "2026-08-17", "fin": "2026-09-20"} and f["activite"]["missions"] == 3
    assert [(m["session_id"], m["date"], m["titre"]) for m in f["missions"]] == [
        ("c", "2026-09-20", "Fulda"), ("a", "2026-08-17", "m1"), ("b", None, "Sans date")]


def test_vols_reels():
    sessions = [_s("a", date(2026, 8, 17), "C1")]
    vols = {"a": [_v("a", "o1", 1, (0, 5400), [T72]), _v("a", "o2", 2, (0, 7200), [BTR]), _v("a", None, 3)]}
    f = _fiche_campagne(_c("C1", "F"), 1, sessions, vols, {"a": {"o1"}}, {1: _p("Viper"), 2: _p("Ghost")}, {})
    assert f["activite"] == {"missions": 1, "sorties": 1, "heures": 1.5, "pilotes": 1}
    assert [p["id"] for p in f["participants"]] == ["1"]
    assert f["bilan"]["n_kills_validated"] == 1
    assert f["bilan"]["kills_by_category"] == [{"category": "Char", "display_name": "Char", "count": 1}]
    assert f["missions"][0]["vols"] == 1


def test_participants():
    sessions = [_s("a", date(2026, 8, 17), "C1"), _s("b", date(2026, 9, 20), "C1"),
                _s("x", date(2026, 9, 21), "C2")]
    vols = {
        "a": [_v("a", "o1", 200000000000000003), _v("a", "o2", 200000000000000003), _v("a", "o3", 42),
              _v("a", "o4")],
        "b": [_v("b", "o1", 200000000000000003), _v("b", "o5", 7)],
        "x": [_v("x", "o9", 99)],
    }
    significatifs = {"a": {"o1", "o2", "o3", "o4"}, "b": {"o1", "o5"}, "x": {"o9"}}
    profils = {200000000000000003: _p("Viper"), 42: _p("Ancien", archive=True), 7: NS(global_name=None, username="fog", archived_at=None)}
    escadrilles = {200000000000000003: "CHARLIE-33", 42: "BRAVO-22"}
    f = _fiche_campagne(_c("C1", "F"), 2, sessions, vols, significatifs, profils, escadrilles)
    assert f["participants"] == [
        {"id": "7", "name": "fog", "escadrille": None, "archived": False, "missions": 1},
        {"id": "42", "name": "Ancien", "escadrille": "BRAVO-22", "archived": True, "missions": 1},
        {"id": "200000000000000003", "name": "Viper", "escadrille": "CHARLIE-33", "archived": False, "missions": 2},
    ]
    # Lot « Le Débrief n'est plus en chantier… » : le vol « o4 » sans profil n'est plus une sortie de l'escadre.
    assert f["activite"] == {"missions": 2, "sorties": 5, "heures": 2.0, "pilotes": 3}
    assert (f["rang"], f["description"]) == (2, "Ordre d'opérations")


def test_bilan():
    sessions = [_s("b", date(2026, 9, 20), "C1"), _s("a", date(2026, 8, 17), "C1")]
    vols = {
        "a": [_v("a", "o1", 1, kills=[T72, T72]), _v("a", "o2", 2, kills=[AMI]), _v("a", "o3", 3, kills=[BTR])],
        # « o4 » est un membre (4) ; « o5 », sans profil, n'est pas compté mais son camp sert de repli à « o4 ».
        "b": [_v("b", "o1", 1, kills=[BTR, BTR, T72]), _v("b", "o4", 4, kills=[{"target_unit_type": "T-72B", "target_object_id": "o5"}]),
              _v("b", "o5", None, coa="1")],
    }
    significatifs = {"a": {"o1", "o2"}, "b": {"o1", "o4"}}
    f = _fiche_campagne(_c("C1", "F"), 1, sessions, vols, significatifs, {}, {})
    attendu = _bilan_additionne([
        ([vols["a"][0], vols["a"][1]], {"o1": "2", "o2": "2", "o3": "2"}),
        ([vols["b"][0], vols["b"][1]], {"o1": "2", "o4": "2", "o5": "1"}),
    ])
    assert f["bilan"] == attendu
    assert (attendu["n_kills_validated"], attendu["n_fratricides"]) == (6, 1)
    assert set(f["bilan"]) == {"kills_by_category", "n_kills_validated", "n_fratricides"}
    for ligne in f["bilan"]["kills_by_category"]:
        assert set(ligne) == {"category", "display_name", "count"}
    assert "200000000000000003" not in repr(f["bilan"]) and "pilote" not in repr(f["bilan"])


def test_vols_de_l_escadre():
    # Lot « Le Débrief n'est plus en chantier, et l'escadre compte les siens » : sur une même
    # session, un membre (1) et un invité (aucun profil), tous deux réels.
    sessions = [_s("a", date(2026, 8, 17), "C1")]
    vols = {"a": [_v("a", "o1", 1, (0, 5400), [T72]), _v("a", "o2", None, (0, 7200), [BTR, BTR])]}
    f = _fiche_campagne(_c("C1", "F"), 1, sessions, vols, {"a": {"o1", "o2"}}, {1: _p("Viper")}, {})
    # L'invité n'entre ni aux sorties, ni aux heures (1,5 h et non 3,5 h), ni au bilan...
    assert f["activite"] == {"missions": 1, "sorties": 1, "heures": 1.5, "pilotes": 1}
    assert f["bilan"]["n_kills_validated"] == 1
    assert f["bilan"]["kills_by_category"] == [{"category": "Char", "display_name": "Char", "count": 1}]
    assert [p["id"] for p in f["participants"]] == ["1"]
    # ... mais son vol compte encore au nombre de vols de la mission.
    assert f["missions"][0]["vols"] == 2
