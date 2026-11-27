"""Lot « La carte des destructions » (`rr-v1.1.0+2`), hors ligne -- ni base, ni réseau, ni navigateur : cinq invariants
déterministes sur des entrées synthétiques (la route est appelée avec une base factice, même patron que
`test_debrief_charge_fenetre.py`).

1. `test_projection` -- sept points de référence, projetés à 1e-7 degré près ;
2. `test_theatre_de` -- le théâtre se reconnaît aux noms d'aérodrome ; la table est saine ;
3. `test_fusion_lieu_et_camp_initiateur` -- `_merge_events` garde le lieu et le camp de l'initiateur ;
4. `test_construire_carte` -- la fonction pure : épaves, camps, chutes, aérodromes, camp ami, vols cités ;
5. `test_route_carte` -- `GET /sessions/{id}/carte` : les clés exactes, le 404, un nombre fixe de requêtes ;
   `GET /sessions/{id}` porte `theatre`.

L'écran ne se joue pas ici : il se prouve au banc, sous Playwright."""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import api, carte, engine
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload

# Les sept points de référence : (théâtre, nom, x DCS, y DCS, lon, lat).
POINTS = [
    ("syria", "Bassel Al-Assad", 42236.566406, 5836.231689, 35.95023987, 35.4038483),
    ("syria", "Damascus", -178652.320313, 52081.296875, 36.5185125, 33.42550826),
    ("germanycw", "Frankfurt", -444041.21875, -853570.90625, 8.56732005, 50.04043132),
    ("germanycw", "Mendig", -392182.984375, -936027.8125, 7.31562913, 50.36601329),
    ("caucasus", "Batumi", -355810.703125, 617386.1875, 41.60023692, 41.60959685),
    ("caucasus", "Mineralnye Vody", -51259.983985, 705734.026899, 43.08119174, 44.2278526),
    ("germanycw", "(cimetière du banc, MiG-21Bis)", -463457.46875, -907635.5, 7.87870321, 49.78784583),
]


# =============================================================================
# 1. La projection
# =============================================================================


def test_projection() -> None:
    for theatre, nom, x, y, lon, lat in POINTS:
        lon_c, lat_c = carte.dcs_vers_lonlat(theatre, x, y)
        assert abs(lon_c - lon) < 1e-7, f"{nom} : lon {lon_c} (attendu {lon})"
        assert abs(lat_c - lat) < 1e-7, f"{nom} : lat {lat_c} (attendu {lat})"


# =============================================================================
# 2. Le théâtre
# =============================================================================


def test_theatre_de() -> None:
    table = carte.aerodromes_par_theatre()
    syrie = ["Bassel Al-Assad", "Damascus", "Bassel Al-Assad"]
    assert carte.theatre_de(syrie) == "syria"
    assert carte.theatre_de(["Frankfurt", "Mendig", "Frankfurt"]) == "germanycw"
    assert carte.theatre_de([]) is None
    assert carte.theatre_de(["Nulle Part", "Inconnu"]) is None
    assert carte.theatre_de(["Damascus", "Frankfurt"]) is None          # un lieu de chacun de deux théâtres : égalité
    assert carte.theatre_de(["Damascus", "Frankfurt", "Frankfurt"]) == "germanycw"
    assert carte.theatre_de([None, "", "Damascus"]) == "syria"
    # La table : Frankfurt et Mendig en Allemagne, et aucun nom dans deux théâtres.
    assert "Frankfurt" in table["germanycw"] and "Mendig" in table["germanycw"]
    assert set(table) == {"syria", "germanycw", "caucasus"}
    tous = [nom for noms in table.values() for nom in noms]
    assert len(tous) == len(set(tous))


# =============================================================================
# 3. La fusion : le lieu et le camp de l'initiateur
# =============================================================================


def _upload(sha: str) -> DebriefUpload:
    return DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log")


def _ev(index, t, type, ioid, *, place=None, coalition=None, target=None):
    raw = {} if place is None else {"place": place}
    return DebriefEvent(
        index=index, t=t, type=type, initiator_object_id=ioid, initiator_pilot_name=None,
        initiator_unit_type="Mi-24P", initiator_mission_id=None, initiator_coalition=coalition,
        target_object_id=target, target_pilot_name=None, target_unit_type=None, weapon=None,
        event_id=str(index), linked_event_id=None, target_slot=None, target_mission_id=None, raw=raw,
    )


def _fusionner(*journaux):
    paires = [
        (_upload(sha), DebriefLogData(header=DebriefHeader(), events=evs, graveyard=[]))
        for sha, evs in journaux
    ]
    return [m for m in engine._merge_events(paires) if m.type in ("takeoff", "land")]


def test_fusion_lieu_et_camp_initiateur() -> None:
    # Le premier journal qui les donne l'emporte (l'ordre est celui du sha256 des dépôts).
    a = [_ev(0, 10.0, "takeoff", "1", place=None, coalition=None)]
    b = [_ev(0, 10.0, "takeoff", "1", place="Mendig", coalition=" 2 ")]
    c = [_ev(0, 10.0, "takeoff", "1", place="Frankfurt", coalition="1")]
    fusion = _fusionner(("a", a), ("b", b), ("c", c))
    assert len(fusion) == 1
    assert fusion[0].place == "Mendig"                 # `a` ne le donne pas : `b` l'emporte sur `c`
    assert fusion[0].initiator_coalition == "2"        # `" 2 "` détouré
    # Un seul journal : le lieu est détouré, un lieu vide vaut `None`.
    assert _fusionner(("a", [_ev(0, 5.0, "land", "1", place="  Frankfurt ")]))[0].place == "Frankfurt"
    assert _fusionner(("a", [_ev(0, 5.0, "land", "1", place="   ")]))[0].place is None
    # Une coalition invalide (`-1`, `blue`, vide) vaut `None`.
    for brute in ("-1", "blue", "", "3", None):
        assert _fusionner(("a", [_ev(0, 5.0, "land", "1", coalition=brute)]))[0].initiator_coalition is None
    # Deux évènements qui ne diffèrent que par `place` restent un seul fait.
    deux = _fusionner(("a", [_ev(0, 20.0, "land", "1", place="Mendig")]), ("b", [_ev(0, 20.0, "land", "1", place="Frankfurt")]))
    assert len(deux) == 1 and deux[0].place == "Mendig"
    # `place` et `initiator_coalition` ne sont pas dans la clé naturelle.
    m = deux[0]
    avant = m.natural_key()
    m.place, m.initiator_coalition = "Autre", "1"
    assert m.natural_key() == avant


# =============================================================================
# 4. La construction de la carte
# =============================================================================

# Des points près de Francfort et de Mendig, en coordonnées de DCS (x = nord, y = est).
XY = {"a": (-444000.0, -853500.0), "b": (-443000.0, -852000.0), "c": (-430000.0, -850000.0), "d": (-420000.0, -840000.0)}


def _vol(i, oid, *, nom=None, etat="nomme", coalition="2", type_="Mi-24P", pid=None, t=0.0):
    return NS(id=f"F{i}", object_id=oid, pilot_callsign=nom, identity_state=etat, aircraft_type=type_,
              coalition=coalition, pilote_profile_id=pid, t_start=t)


def _g(type_, coalition, xy, alt=None):
    return NS(unit_type=type_, coalition=coalition, x=xy[0], y=xy[1], alt=alt)


def _e(t, type_, ioid=None, *, itype=None, icoal=None, ttype=None, tcoal=None, place=None, weapon=None, toid=None):
    return NS(type=type_, t=t, initiator_object_id=ioid, target_object_id=toid, initiator_unit_type=itype,
              target_unit_type=ttype, weapon=weapon, place=place, initiator_coalition=icoal, target_coalition=tcoal,
              seen_in=[])


ENTETE = {"id": "S1", "display_title": "Mission d'essai", "mission_date": "2026-11-27", "duration_s": 5000}


def _monde():
    vols = [
        _vol(1, "100", nom="CHARLIE-33 | Wren", pid=7, t=1.0),
        _vol(2, "200", etat="anonyme", t=2.0),
        _vol(3, "300", nom="CHARLIE-33 | Ghost", t=3.0),
        _vol(4, "400", nom="Rouge", coalition="red", t=4.0),
        _vol(5, "500", nom="Jamais cité", t=5.0),
    ]
    cimetiere = [
        _g("T-72B", "1", XY["a"], alt=80.6), _g("T-72B", "1", XY["b"]),                 # un groupe de deux
        _g("2S6 Tunguska", "red", XY["c"], alt=12.4),                                 # `\"` ; camp `red`
        _g("F-4E-45MC", "2", XY["d"]),                                                # une épave unique
        _g("Mi-24P", "2", XY["a"]), _g("Mi-24P", "2", XY["b"]),                       # un groupe de deux
    ]
    evenements = [
        _e(100.4, "kill", "100", itype="Mi-24P", icoal="2", ttype="T-72B", tcoal="1", weapon="9M114"),
        _e(101.6, "kill", None, itype="2S6 Tunguska", icoal="red", ttype="F-4E-45MC", tcoal="blue", weapon="9M311"),
        _e(90.0, "hit", "100", itype="Mi-24P", ttype="T-72B", tcoal="1"),
        _e(91.0, "hit", "100", itype="Mi-24P", ttype=None),                                # sans cible : écarté
        _e(10.0, "takeoff", "100", itype="Mi-24P", place="Frankfurt"),
        _e(3000.0, "land", "100", itype="Mi-24P", place="Frankfurt"),
        _e(11.0, "takeoff", None, itype="F-4E-45MC", place="Mendig"),                         # l'IA
        _e(12.0, "takeoff", "200", itype="Mi-24P", place="Nulle Part"),                    # un lieu inconnu
        _e(13.0, "takeoff", "300", itype="Mi-24P", place=None),                            # un lieu absent
        # Deux sièges d'un même équipage : 4 s d'écart -> une chute ; 15 s -> deux.
        _e(500.0, "eject", "100", itype="Mi-24P", icoal="2"),
        _e(504.0, "pilot dead", "100", itype="Mi-24P", icoal="2"),
        _e(600.0, "eject", "200", itype="Mi-24P", icoal="2"),
        _e(615.0, "pilot dead", "200", itype="Mi-24P", icoal="2"),
        # L'IA : même type et même camp, 3 s -> une chute, posée sur l'épave unique du F-4E.
        _e(700.0, "eject", None, itype="F-4E-45MC", icoal="2"),
        _e(703.0, "eject", None, itype="F-4E-45MC", icoal="2"),
        _e(5.0, "start shooting", "100"),                                                  # hors carte
    ]
    return vols, evenements, cimetiere


def test_construire_carte() -> None:
    # Les deux encodages du camp.
    assert [carte.camp(v) for v in ("2", "blue", " Blue ", "1", "RED", "red")] == ["blue"] * 3 + ["red"] * 3
    assert [carte.camp(v) for v in (None, "0", "-1", "", "neutrals", "3")] == ["neutral"] * 6

    vols, evenements, cimetiere = _monde()
    r = carte.construire_carte(ENTETE, vols, evenements, cimetiere, {7: "Wren-nom"})
    assert set(r) == {"id", "display_title", "mission_date", "duration_s", "theatre", "camp_ami", "vols", "epaves",
                      "tirs", "touches", "aerodromes", "sans_lieu", "chutes"}
    assert r["theatre"] == "germanycw" and r["id"] == "S1" and r["duration_s"] == 5000

    # Les épaves : `homonymes`, les noms, les catégories, l'arrondi, l'ordre (camp, type, lon, lat).
    ep = r["epaves"]
    assert len(ep) == 6
    assert ep == sorted(ep, key=lambda e: (e["camp"], e["type"], e["lon"], e["lat"]))
    t72 = [e for e in ep if e["type"] == "T-72B"]
    assert [e["homonymes"] for e in t72] == [2, 2]
    assert [e["camp"] for e in t72] == ["red", "red"]                      # `"1"` -> `red`
    sam = next(e for e in ep if e["type"] == "2S6 Tunguska")
    assert sam["camp"] == "red" and sam["homonymes"] == 1                  # `"red"` -> `red`
    assert sam["nom"] == 'SAM SA-19 Tunguska "Grison" ' and "\\" not in sam["nom"]
    assert sam["categorie"] == "Défense AA" and sam["alt"] == 12
    assert next(e for e in ep if e["type"] == "F-4E-45MC")["alt"] is None
    assert next(e for e in t72 if e["alt"] is not None)["alt"] == 81
    for e in ep:
        assert e["lon"] == round(e["lon"], 6) and e["lat"] == round(e["lat"], 6)
        assert 6 < e["lon"] < 10 and 49 < e["lat"] < 52                   # l'Allemagne

    # Les tirs et les touches : triés par `t`, `t` à la seconde, le camp par R7.
    assert [k["t"] for k in r["tirs"]] == [100, 102]
    k0, k1 = r["tirs"]
    assert (k0["vol"], k0["tireur_camp"], k0["cible"], k0["cible_camp"], k0["arme"]) == ("F1", "blue", "T-72B", "red", "9M114")
    assert k0["tireur_type"] == "Mi-24P"
    assert k1["vol"] is None and k1["tireur_type"] == 'SAM SA-19 Tunguska "Grison" ' and k1["tireur_camp"] == "red"
    assert [(h["t"], h["vol"], h["cible"], h["cible_camp"]) for h in r["touches"]] == [(90, "F1", "T-72B", "red")]

    # Les aérodromes : `dec` / `att`, triés ; `sans_lieu` compte le lieu inconnu et le lieu absent.
    assert [a["nom"] for a in r["aerodromes"]] == ["Frankfurt", "Mendig"]
    fra, men = r["aerodromes"]
    assert fra["dec"] == [{"t": 10, "vol": "F1", "type": "Mi-24P"}] and fra["att"] == [{"t": 3000, "vol": "F1", "type": "Mi-24P"}]
    assert men["dec"] == [{"t": 11, "vol": None, "type": "F-4E-45MC"}] and men["att"] == []
    lon, lat = carte.dcs_vers_lonlat("germanycw", *carte.aerodromes_par_theatre()["germanycw"]["Frankfurt"])
    assert (fra["lon"], fra["lat"]) == (lon, lat)
    assert r["sans_lieu"] == 2

    # Les chutes : deux sièges à 4 s -> une chute, à 15 s -> deux ; l'IA dédoublée à 3 s -> une.
    assert [(c["t"], c["vol"], c["quoi"]) for c in r["chutes"]] == [
        (500, "F1", "ejection"), (600, "F2", "ejection"), (615, "F2", "tue"), (700, None, "ejection"),
    ]
    # Posée sur l'épave unique (F-4E) ; non posée sur un groupe (deux Mi-24P).
    f4 = next(e for e in ep if e["type"] == "F-4E-45MC")
    ia = r["chutes"][3]
    assert (ia["lon"], ia["lat"], ia["type"], ia["camp"]) == (f4["lon"], f4["lat"], "F-4E-45MC", "blue")
    assert all(c["lon"] is None and c["lat"] is None for c in r["chutes"][:3])

    # Le camp ami : le plus nombreux parmi les vols nommés (deux bleus, un rouge) ; une égalité, ou aucun : `None`.
    assert r["camp_ami"] == "blue"
    egal = [_vol(1, "100", nom="a", coalition="2"), _vol(2, "200", nom="b", coalition="1")]
    assert carte.construire_carte(ENTETE, egal, evenements, cimetiere, {})["camp_ami"] is None
    anonymes = [_vol(1, "100", etat="anonyme"), _vol(2, "200", etat="rattachable")]
    assert carte.construire_carte(ENTETE, anonymes, evenements, cimetiere, {})["camp_ami"] is None

    # `vols` ne porte que les vols cités (le 4 et le 5 ne le sont pas ; le 3 ne l'est que par un lieu absent).
    assert set(r["vols"]) == {"F1", "F2"}
    assert r["vols"]["F1"] == {"pilot_callsign": "CHARLIE-33 | Wren", "pilote_nom": "Wren-nom", "identity_state": "nomme", "aircraft_type": "Mi-24P"}
    assert r["vols"]["F2"]["identity_state"] == "anonyme" and r["vols"]["F2"]["pilote_nom"] is None

    # Aucun lieu reconnu : le théâtre est nul, et tout le reste est vide.
    sans_lieu = [e for e in evenements if e.place is None]
    vide = carte.construire_carte(ENTETE, vols, sans_lieu, cimetiere, {7: "x"})
    assert vide["theatre"] is None and vide["camp_ami"] is None and vide["vols"] == {} and vide["sans_lieu"] == 0
    assert all(vide[k] == [] for k in ("epaves", "tirs", "touches", "aerodromes", "chutes"))
    assert vide["id"] == "S1" and vide["display_title"] == "Mission d'essai"


# =============================================================================
# 5. La route
# =============================================================================


class _Resultat:
    def __init__(self, lignes):
        self._lignes = lignes

    def all(self):
        return list(self._lignes)

    def scalars(self):
        return NS(all=lambda: list(self._lignes))


class _FauxDb:
    """Répond selon la table que nomme la requête ; compte chaque lecture (`get` et `execute`)."""

    def __init__(self, session, vols=(), evenements=(), cimetiere=(), profils=()):
        self.session, self.vols, self.evenements = session, list(vols), list(evenements)
        self.cimetiere, self.profils = list(cimetiere), list(profils)
        self.requetes = 0

    async def get(self, modele, cle):
        self.requetes += 1
        return self.session if (self.session is not None and cle == self.session.id) else None

    async def execute(self, requete):
        self.requetes += 1
        sql = str(requete)
        if "FROM debrief_upload" in sql:
            return _Resultat([])
        if "FROM debrief_flight" in sql:
            return _Resultat(self.vols)
        if "FROM debrief_graveyard" in sql:
            return _Resultat(self.cimetiere)
        if "FROM debrief_event" in sql:
            if "debrief_event.seen_in" in sql:   # l'entité entière
                return _Resultat(self.evenements)
            return _Resultat([(self.session.id, e.initiator_object_id, e.target_object_id) for e in self.evenements])
        if "FROM profiles" in sql:
            return _Resultat([p for p in self.profils])
        if "FROM debrief_session" in sql:        # les sessions périmées
            return _Resultat([(self.session.id, None)])
        raise AssertionError(f"requête inattendue : {sql}")


def _session():
    return NS(
        id=uuid.uuid4(), title="Mission", display_name="Mission d'essai", wing_note=None, campaign_id=None, nature="mission",
        mission_date=date(2026, 11, 27), reference_time=None, horloge_mission_s=None, duration_s=5000, acmi_present=False,
        sim="dcs", stats_engine_rev=None,
    )


def test_route_carte(monkeypatch) -> None:
    async def _non(db, user):
        return False
    monkeypatch.setattr(api, "can_edit_session", _non)

    vols, evenements, cimetiere = _monde()
    # Des évènements de la base : les attributs d'un `DebriefEvent` de la base (`seen_in` pour la requête de l'entité).
    session = _session()
    db = _FauxDb(session, vols, evenements, cimetiere, [(7, "Wren-nom", "wren")])
    r = asyncio.run(api.get_session_carte(session_id=session.id, user={}, db=db))
    assert set(r) == {"id", "display_title", "mission_date", "duration_s", "theatre", "camp_ami", "vols", "epaves",
                      "tirs", "touches", "aerodromes", "sans_lieu", "chutes"}
    assert r["id"] == str(session.id) and r["display_title"] == "Mission d'essai"
    assert r["mission_date"] == "2026-11-27" and r["duration_s"] == 5000
    assert r["theatre"] == "germanycw" and len(r["epaves"]) == 6 and len(r["chutes"]) == 4
    assert r["vols"]["F1"]["pilote_nom"] == "Wren-nom"

    # Un nombre fixe de requêtes : dix fois plus d'évènements et de vols, le même compte.
    beaucoup = _FauxDb(session, vols * 10, evenements * 10, cimetiere * 10, [(7, "Wren-nom", "wren")])
    asyncio.run(api.get_session_carte(session_id=session.id, user={}, db=beaucoup))
    assert beaucoup.requetes == db.requetes

    # Une session inconnue : 404.
    with pytest.raises(HTTPException) as erreur:
        asyncio.run(api.get_session_carte(session_id=uuid.uuid4(), user={}, db=_FauxDb(session)))
    assert erreur.value.status_code == 404

    # `GET /sessions/{id}` porte `theatre` (sans requête de plus : il lit les évènements qu'il lit déjà).
    detail = asyncio.run(api.get_session(session_id=session.id, user={}, db=_FauxDb(session, [], evenements, [])))
    assert detail["theatre"] == "germanycw"
    sans = [e for e in evenements if e.place is None]
    assert asyncio.run(api.get_session(session_id=session.id, user={}, db=_FauxDb(session, [], sans, [])))["theatre"] is None
    avant = _FauxDb(session, [], evenements, [])
    asyncio.run(api.get_session(session_id=session.id, user={}, db=avant))
    apres = _FauxDb(session, [], evenements * 10, [])
    asyncio.run(api.get_session(session_id=session.id, user={}, db=apres))
    assert avant.requetes == apres.requetes
