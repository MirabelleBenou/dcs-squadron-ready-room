"""Lot « Le dossier du pilote — les données » (R208, R209) : la part privée
du dossier A (`_dossier_prive`) et le titre embelli de F et B, hors ligne --
ni base, ni réseau.

1. `test_victoires_pertes_ratio` -- air et sol, fratricide exclu, appareils
   perdus et éjections, ratio arrondi ; un dossier vide.
2. `test_precision_vols_fiables` -- vols fiables seuls, une arme sous ses deux
   formes, l'ordre.
3. `test_menaces_par_sortie` -- un compte par vol et par type, `touche` et
   `abattu`, un type `None`, l'ordre.
4. `test_carnet_et_par_appareil` -- une ligne par vol, l'ordre, le titre, la
   campagne, la durée, les `stats` par défaut, le bilan par appareil, les
   invariants.
5. `test_titres_f_et_b` -- le titre embelli dans `_synthese_membre` et
   `_accueil_payload` ; les clés de F inchangées.
6. `test_dossier_francfort` -- la fixture « Bataille de Francfort », deux
   pilotes, valeur pour valeur.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _accueil_payload, _dossier_prive, _synthese_membre

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "89f20c83-54ec-4fd4-bf0c-1700463ff155.json"

ENNEMI = "1"


def _k(type_):
    return {"target_unit_type": type_, "target_coalition": ENNEMI}


def _s(sid, jour=date(2026, 8, 17), titre="Op_Tempete_20260801-2100", nom=None, camp=None):
    return NS(id=sid, mission_date=jour, title=titre, display_name=nom, campaign_id=camp, duration_s=None)


def _v(fid, session, kills=(), t0=0.0, t1=600.0, coa="2", ac="Mi-24P", **stats):
    st = {"kills": [dict(k) for k in kills]}
    st.update(stats)
    return NS(id=fid, session_id=session.id, object_id=None, coalition=coa, aircraft_type=ac,
              t_start=t0, t_end=t1, stats=st)


def _vols(*couples):
    return [(v, s) for v, s in couples]


def test_victoires_pertes_ratio():
    s = _s("s1")
    vols = _vols(
        (_v("f1", s, [_k("MiG-21Bis"), _k("Mi-8MT")], crashed=True), s),
        (_v("f2", s, [_k("T-72B"), _k("MOLNIYA"), _k("ZZZ-absent")], pilot_dead=True), s),
        (_v("f3", s, [{"target_unit_type": "T-72B", "target_coalition": "2"}], ejected=True), s),
        (_v("f4", s, [_k("T-72B")], landings=1), s),
    )
    d = _dossier_prive(vols, {}, {})
    assert d["vols"] == 4
    assert d["bilan"]["n_kills_validated"] == 6 and d["bilan"]["n_fratricides"] == 1
    assert d["victoires"] == {"air": 2, "sol": 4}
    assert d["pertes"] == {"appareils": 3, "ejections": 1}
    assert d["ratio"] == 2.0
    d2 = _dossier_prive(_vols((_v("f1", s, [_k("T-72B")] * 2, ejected=True), s),
                              (_v("f2", s, [_k("T-72B")], crashed=True), s),
                              (_v("f3", s, [], pilot_dead=True), s)), {}, {})
    assert d2["ratio"] == 1.0
    d3 = _dossier_prive(_vols((_v("f1", s, [_k("T-72B")] * 2, crashed=True), s),
                              (_v("f2", s, [_k("T-72B")] * 2), s),
                              (_v("f3", s, [], crashed=True), s),
                              (_v("f4", s, [], crashed=True), s)), {}, {})
    assert d3["ratio"] == round(4 / 3, 1) == 1.3
    vide = _dossier_prive([], {}, {})
    assert vide == {
        "vols": 0, "vols_fiables": 0,
        "bilan": {"kills_by_category": [], "n_kills_validated": 0, "n_fratricides": 0},
        "victoires": {"air": 0, "sol": 0},
        "pertes": {"appareils": 0, "ejections": 0},
        "ratio": None, "precision": [], "menaces": [], "par_appareil": {}, "carnet": [],
    }


def test_precision_vols_fiables():
    s = _s("s1")
    vols = _vols(
        (_v("f1", s, precision_reliability="fiable", cannon_bursts=4, cannon_hits=2,
            shots_by_weapon={"S-8KOM": {"shots": 10, "touched": 2, "precision": 0.2},
                             "Mk-20": {"releases": 6}}), s),
        (_v("f2", s, precision_reliability="fiable",
            shots_by_weapon={"Mk-20": {"shots": 4, "touched": 1, "precision": 0.25},
                             "R-60M": {"shots": 1, "touched": 1, "precision": 1.0}}), s),
        (_v("f3", s, precision_reliability="partielle",
            shots_by_weapon={"S-8KOM": {"shots": 99, "touched": 99}}), s),
        (_v("f4", s, precision_reliability="fiable", shots_by_weapon={"9M114": {"shots": 1, "touched": 0}}), s),
    )
    d = _dossier_prive(vols, {}, {})
    assert d["vols"] == 4 and d["vols_fiables"] == 3
    assert d["precision"] == [
        {"arme": "Mk-20", "tirs": 4, "touches": 1, "largages": 6},
        {"arme": "S-8KOM", "tirs": 10, "touches": 2, "largages": 0},
        {"arme": "9M114", "tirs": 1, "touches": 0, "largages": 0},
        {"arme": "R-60M", "tirs": 1, "touches": 1, "largages": 0},
    ]


def _m(type_, gravite, obj="1"):
    return {"t": 1.0, "type": "hit", "weapon": "x", "gravite": gravite,
            "initiator_object_id": obj, "initiator_unit_type": type_}


def test_menaces_par_sortie():
    s = _s("s1")
    vols = _vols(
        (_v("f1", s, threat_log=[_m("BMP-1", "visé", "1"), _m("BMP-1", "touché", "2"),
                                 _m("BMP-1", "abattu", "1"), _m("BMP-1", "abattu", "2"),
                                 _m("T-55", "touché"), _m(None, "visé")]), s),
        (_v("f2", s, threat_log=[_m("BMP-1", "visé"), _m("ZSU-23-4 Shilka", "visé"),
                                 _m("T-55", "touché")]), s),
        (_v("f3", s, threat_log=[_m("Soldier stinger", "visé"), _m(None, "abattu")]), s),
    )
    d = _dossier_prive(vols, {}, {})
    assert d["menaces"] == [
        {"type": "BMP-1", "engagements": 2, "touche": 1, "abattu": 1},
        {"type": None, "engagements": 2, "touche": 1, "abattu": 1},
        {"type": "T-55", "engagements": 2, "touche": 2, "abattu": 0},
        {"type": "Soldier stinger", "engagements": 1, "touche": 0, "abattu": 0},
        {"type": "ZSU-23-4 Shilka", "engagements": 1, "touche": 0, "abattu": 0},
    ]
    seul = _dossier_prive(_vols((_v("f1", s, threat_log=[_m(None, "visé"), _m("AAA", "visé")]), s)), {}, {})
    assert [m["type"] for m in seul["menaces"]] == ["AAA", None]


def test_carnet_et_par_appareil():
    a = _s("aaa", date(2026, 8, 17), "Op_Tempete_20260801-2100", camp="C1")
    b = _s("bbb", date(2026, 8, 17), "Brut", nom="Retour à Kutaisi")
    c = _s("ccc", date(2026, 7, 6), "Ancienne")
    x = _s("xxx", None, "Sans_date")
    vols = _vols(
        (_v("c1", c, [_k("T-72B")], 0, 1800, ac="Mi-8MT", crashed=True), c),
        (_v("a1", a, [_k("T-72B")], 100, 400.04, ac="Mi-24P", ejected=True), a),
        (_v("a2", a, [_k("MiG-21Bis"), _k("T-72B")], 500, 1200, ac="Mi-24P", landings=2), a),
        (_v("b1", b, [], 50, 10, ac="Mi-24P"), b),
        (_v("x1", x, [_k("T-72B")], None, None, ac="Mi-8MT"), x),
    )
    d = _dossier_prive(vols, {}, {"C1": (1, "Foothold Germany")})
    assert [l["flight_id"] for l in d["carnet"]] == ["b1", "a2", "a1", "c1", "x1"]
    l_a1 = d["carnet"][2]
    assert l_a1 == {
        "session_id": "aaa", "flight_id": "a1", "date": "2026-08-17", "titre": "Op Tempete",
        "campagne": "Foothold Germany", "campagne_id": "C1", "appareil": "Mi-24P", "duree_s": 300.0, "victoires": 1,
        "stats": {"crashed": False, "pilot_dead": False, "ejected": True, "landings": 0},
    }
    assert d["carnet"][0]["titre"] == "Retour à Kutaisi" and d["carnet"][0]["campagne"] is None
    assert d["carnet"][0]["campagne_id"] is None
    assert d["carnet"][0]["duree_s"] == 0.0
    assert d["carnet"][1]["stats"] == {"crashed": False, "pilot_dead": False, "ejected": False, "landings": 2}
    assert d["carnet"][4]["date"] is None and d["carnet"][4]["duree_s"] == 0.0
    assert d["par_appareil"] == {
        "Mi-8MT": {"victoires": 2, "pertes": 1, "dernier": "2026-07-06"},
        "Mi-24P": {"victoires": 3, "pertes": 1, "dernier": "2026-08-17"},
    }
    n = d["bilan"]["n_kills_validated"]
    assert n == 5
    assert d["victoires"]["air"] + d["victoires"]["sol"] == n
    assert sum(l["victoires"] for l in d["carnet"]) == n
    assert sum(p["victoires"] for p in d["par_appareil"].values()) == n
    seul = _dossier_prive(_vols((_v("x1", x, ac="Mi-8MT"), x)), {}, {})
    assert seul["par_appareil"] == {"Mi-8MT": {"victoires": 0, "pertes": 0, "dernier": None}}


def test_titres_f_et_b():
    brut = _s("a", date(2026, 9, 28), "Op_Tempete_20260801-2100")
    nomme = _s("b", date(2026, 9, 29), "Op_Tempete_20260801-2100", nom="Tempête du désert")
    vols = [(_v("f1", brut), brut), (_v("f2", nomme), nomme)]
    f = _synthese_membre(vols, {})
    assert set(f) == {"participation", "appareils", "campagnes", "missions"}
    assert [m["titre"] for m in f["missions"]] == ["Tempête du désert", "Op Tempete"]
    b = _accueil_payload([], [brut, nomme], {}, date(2026, 10, 1))
    assert [m["titre"] for m in b["missions"]] == ["Tempête du désert", "Op Tempete"]


def _francfort():
    d = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    session = NS(id=d["id"], mission_date=date.fromisoformat(d["mission_date"]), title=d["title"],
                 display_name=d["display_name"], campaign_id=None)
    vols = [NS(id=f["id"], session_id=d["id"], t_start=f["t_start"], t_end=f["t_end"],
               coalition=f["coalition"], object_id=f["object_id"], aircraft_type=f["aircraft_type"],
               stats=f["stats"], pilote_profile_id=f["pilote_profile_id"]) for f in d["flights"]]
    camps = {d["id"]: {str(v.object_id): v.coalition for v in vols if v.object_id is not None}}
    return session, vols, camps


def _du_pilote(pid):
    session, vols, camps = _francfort()
    return _dossier_prive([(v, session) for v in vols if v.pilote_profile_id == pid], camps, {})


def test_dossier_francfort():
    d = _du_pilote("8000000000000000001")
    assert (d["vols"], d["vols_fiables"]) == (11, 11)
    assert d["bilan"]["n_kills_validated"] == 6 and d["bilan"]["n_fratricides"] == 0
    assert [(r["category"], r["count"]) for r in d["bilan"]["kills_by_category"]] == [("Avion", 5), ("Char", 1)]
    assert d["victoires"] == {"air": 5, "sol": 1}
    assert d["pertes"] == {"appareils": 11, "ejections": 6}
    assert d["ratio"] == 0.5
    assert [(p["arme"], p["tirs"], p["touches"], p["largages"]) for p in d["precision"]] == [
        ("S-8KOM HEAT/Frag", 58, 8, 0), ("S530F", 4, 2, 0), ("AIM-9JULI", 3, 2, 0), ("R-60M", 1, 1, 0),
    ]
    assert [(m["type"], m["engagements"], m["touche"], m["abattu"]) for m in d["menaces"]] == [
        ("F-4E-45MC", 4, 4, 4), ("F-16C_50", 4, 4, 3), ("F-14A-135-GR", 4, 1, 1), ("Soldier stinger", 2, 1, 1),
    ]
    assert d["par_appareil"] == {
        "Su-25": {"victoires": 2, "pertes": 4, "dernier": "2026-08-17"},
        "MiG-29 Fulcrum": {"victoires": 0, "pertes": 1, "dernier": "2026-08-17"},
        "Mirage-F1EE": {"victoires": 4, "pertes": 6, "dernier": "2026-08-17"},
    }
    assert len(d["carnet"]) == 11
    premiere, derniere = d["carnet"][0], d["carnet"][-1]
    assert premiere["flight_id"] == "95fbf7de-fd2a-56a4-9366-fb964e805119"
    assert (premiere["appareil"], premiere["duree_s"], premiere["victoires"]) == ("Su-25", 377.8, 2)
    assert premiere["stats"] == {"crashed": True, "pilot_dead": False, "ejected": True, "landings": 0}
    assert derniere["flight_id"] == "1f500c7b-e97d-5dcd-aa09-8ddead8be0e1"
    assert all((l["titre"], l["date"], l["campagne"]) == ("Bataille de Francfort", "2026-08-17", None)
               for l in d["carnet"])

    m = _du_pilote("800000000000000002")
    assert (m["vols"], m["vols_fiables"]) == (1, 1)
    assert [(r["category"], r["count"]) for r in m["bilan"]["kills_by_category"]] == [("Char", 2), ("Blindé léger", 2)]
    assert m["victoires"] == {"air": 0, "sol": 4}
    assert m["pertes"] == {"appareils": 1, "ejections": 0}
    assert m["ratio"] == 4.0
    assert [(p["arme"], p["tirs"], p["touches"], p["largages"]) for p in m["precision"]] == [
        ("9M114 Shturm (AT-6 Spiral)", 6, 6, 0),
    ]
    assert [(t["type"], t["engagements"], t["touche"], t["abattu"]) for t in m["menaces"]] == [
        ("BMP-1", 1, 1, 1), ("T-55", 1, 1, 0),
    ]
    assert m["par_appareil"] == {"Mi-24P": {"victoires": 4, "pertes": 1, "dernier": "2026-08-17"}}
    assert len(m["carnet"]) == 1
    l = m["carnet"][0]
    assert (l["flight_id"], l["duree_s"], l["victoires"]) == ("db0bdb6e-f3fe-5e0a-8bc0-7d848a0ebabc", 3524.4, 4)
    assert l["stats"] == {"crashed": True, "pilot_dead": True, "ejected": False, "landings": 1}
