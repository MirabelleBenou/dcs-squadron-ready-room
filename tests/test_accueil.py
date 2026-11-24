"""Lot « L'écran B » : l'addition des bilans (`_bilan_additionne`, R167) et
la charge de l'accueil (`_accueil_payload`), hors ligne -- ni base, ni réseau.

1. `test_bilan_additionne` -- deux sessions s'additionnent, fratricides à
   part ; à compte égal, l'ordre de première apparition.
2. `test_accueil_campagnes_et_missions` -- les campagnes en cours seules, les
   quatre dernières missions de la plus récente.
3. `test_accueil_trente_jours` -- les destructions des trente derniers jours,
   bornes comprises au bon endroit.
4. `test_accueil_vols_reels` -- lot « Correctifs de B » : un vol vide ne compte
   ni dans le nombre de pilotes d'une mission, ni dans le bilan.
5. `test_accueil_vols_de_l_escadre` -- lot « Le Débrief n'est plus en chantier,
   et l'escadre compte les siens » : sur une même session, la destruction d'un
   vol sans profil n'entre pas au bilan de l'escadre, celle d'un membre y entre ;
   les camps de repli lisent encore tous les vols.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _accueil_payload, _bilan_additionne

T72 = {"target_unit_type": "T-72B", "target_coalition": "1"}
BTR = {"target_unit_type": "BTR-80", "target_coalition": "1"}
AMI = {"target_unit_type": "Ural-375", "target_coalition": "2"}


def _v(kills=(), coa="2", obj=None, pilote=None):
    return NS(coalition=coa, object_id=obj, pilote_profile_id=pilote, stats={"kills": [dict(k) for k in kills]})


def test_bilan_additionne():
    b = _bilan_additionne([([_v([BTR]), _v([AMI])], {}), ([_v([T72, T72])], {})])
    assert b == {
        "kills_by_category": [
            {"category": "Char", "display_name": "Char", "count": 2},
            {"category": "Blindé léger", "display_name": "Blindé léger", "count": 1},
        ],
        "n_kills_validated": 3,
        "n_fratricides": 1,
    }
    assert _bilan_additionne([]) == {"kills_by_category": [], "n_kills_validated": 0, "n_fratricides": 0}


def _s(sid, jour, titre, camp=None, nom=None, duree=None):
    return NS(id=sid, mission_date=jour, title=titre, display_name=nom, campaign_id=camp, duration_s=duree)


CAMPAGNES = [NS(id="C1", name="Foothold Germany", status="en_cours", sim="dcs"),
             NS(id="C2", name="Ardennes 85", status="close", sim="dcs")]
SESSIONS = [_s("a", date(2026, 7, 6), "m1", "C1"), _s("b", date(2026, 8, 17), "m2", "C2"),
            _s("c", date(2026, 9, 1), "m3", duree=3720), _s("d", date(2026, 9, 7), "m4", nom="Entrainement Syrie", duree=5100.5),
            _s("e", date(2026, 9, 28), "m5", "C1", duree=None), _s("f", None, "sans date")]


def test_accueil_campagnes_et_missions():
    # Lot « L'Accueil, durée et pilotes » : la durée de la session (None comprise) et les
    # profils distincts -- deux vols du même profil comptent pour un, un vol sans profil pour zéro.
    vols = {"e": [_v(pilote=1), _v(pilote=1), _v(pilote=2)], "d": [_v()]}
    p = _accueil_payload(CAMPAGNES, SESSIONS, vols, date(2026, 10, 1))
    assert p["campagnes"] == [{"id": "C1", "name": "Foothold Germany", "sim": "dcs", "missions": 2}]
    assert "hors_campagne" not in p
    assert all("vols" not in m for m in p["missions"])
    assert [(m["date"], m["titre"], m["duree_s"], m["pilotes"]) for m in p["missions"]] == [
        ("2026-09-28", "m5", None, 2), ("2026-09-07", "Entrainement Syrie", 5100.5, 0), ("2026-09-01", "m3", 3720, 0), ("2026-08-17", "m2", None, 0)]


def test_accueil_trente_jours():
    # Lot « Le Débrief n'est plus en chantier… » : un chiffre de l'escadre ne compte que
    # des vols rattachés à un membre -- chaque vol porte donc un profil.
    vols = {"a": [_v([T72], pilote=1)], "c": [_v([T72], pilote=1)], "d": [_v([BTR, AMI], pilote=1)], "e": [_v([BTR], pilote=1)]}
    p = _accueil_payload(CAMPAGNES, SESSIONS, vols, date(2026, 10, 1))
    d = p["destructions"]
    assert (d["jours"], d["missions"], d["n_kills_validated"], d["n_fratricides"]) == (30, 2, 2, 1)
    assert d["kills_by_category"] == [{"category": "Blindé léger", "display_name": "Blindé léger", "count": 2}]
    p = _accueil_payload(CAMPAGNES, SESSIONS, vols, date(2026, 9, 30))
    assert p["destructions"]["missions"] == 3


def test_accueil_vols_reels():
    def vol(sid, oid, kills=(), pilote=None):
        return NS(session_id=sid, object_id=oid, coalition="2", pilote_profile_id=pilote, stats={"kills": [dict(k) for k in kills]})
    vols = {"e": [vol("e", "o1", [BTR], 7), vol("e", "o2", (), 8), vol("e", "o3", [T72], 9)], "d": [vol("d", "o4", (), 7), vol("d", None, (), 7)]}
    significatifs = {"e": {"o1", "o2"}, "d": set()}
    p = _accueil_payload(CAMPAGNES, SESSIONS, vols, date(2026, 10, 1), significatifs=significatifs)
    # Pilotes : seuls les vols réels comptent (le vol o3 de « e », 9, et ceux de « d » sortent).
    assert [(m["date"], m["pilotes"]) for m in p["missions"][:2]] == [("2026-09-28", 2), ("2026-09-07", 0)]
    d = p["destructions"]
    assert (d["n_kills_validated"], [g["category"] for g in d["kills_by_category"]]) == (1, ["Blindé léger"])


def test_accueil_vols_de_l_escadre():
    # Lot « Le Débrief n'est plus en chantier, et l'escadre compte les siens » : sur une même
    # session, un invité (aucun profil) et un membre. Seule la destruction du membre entre au
    # bilan de l'escadre ; les camps de repli lisent encore l'invité -- le membre qui abat la
    # cible « o2 » (aucun camp porté par l'abattage) la reconnaît pour un fratricide.
    def vol(oid, kills, pilote=None):
        return NS(session_id="e", object_id=oid, coalition="2", pilote_profile_id=pilote, stats={"kills": [dict(k) for k in kills]})
    membre = vol("o1", [BTR, {"target_unit_type": "Ural-375", "target_object_id": "o2"}], pilote=7)
    invite = vol("o2", [T72, T72])
    vols = {"e": [membre, invite]}
    significatifs = {"e": {"o1", "o2"}}
    p = _accueil_payload(CAMPAGNES, SESSIONS, vols, date(2026, 10, 1), significatifs=significatifs)
    d = p["destructions"]
    assert (d["missions"], d["n_kills_validated"], d["n_fratricides"]) == (2, 1, 1)
    assert d["kills_by_category"] == [{"category": "Blindé léger", "display_name": "Blindé léger", "count": 1}]
    # Le reste du bloc ne change pas : la liste des missions compte ses pilotes comme avant.
    assert (p["missions"][0]["date"], p["missions"][0]["pilotes"]) == ("2026-09-28", 1)
    # Sans le membre, l'invité seul ne fait aucune destruction d'escadre.
    p = _accueil_payload(CAMPAGNES, SESSIONS, {"e": [invite]}, date(2026, 10, 1), significatifs=significatifs)
    assert p["destructions"]["n_kills_validated"] == 0 and p["destructions"]["kills_by_category"] == []
