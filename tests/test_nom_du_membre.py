"""Correctif « Le nom du membre » (v1.0021), hors ligne -- ni base, ni réseau.

1. `test_report_flight_name` -- la fiche nomme un vol rattaché sans indicatif
   par le nom du membre ; l'indicatif observé l'emporte ; l'anonyme garde son
   libellé.
2. `test_named_pilots_noms` -- le comptage suit le même nom, et un même nom
   ne compte qu'une fois.
3. `test_flight_to_dict_pilote_nom` -- le serveur sert `pilote_nom`.
"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _flight_to_dict, _named_pilots
from app.debrief.report_facts import _report_flight_name


def _vol(callsign=None, pid=None, etat="nomme", **kw):
    base = dict(
        id=uuid.uuid4(), session_id=uuid.uuid4(), object_id=1, acmi_track_id=None,
        aircraft_type="Mi-24P", coalition="1", pilote_profile_id=pid,
        pilot_callsign=callsign, identity_state=etat, identity_source="manuel",
        t_start=0, t_end=10, slot_mission=None, mission_id_dcs=None, stats={},
    )
    base.update(kw)
    return NS(**base)


def test_report_flight_name():
    sans_indicatif = {"identity_state": "nomme", "pilot_callsign": None,
                      "pilote_nom": "CHARLIE-33 | DawNFyX"}
    assert _report_flight_name(sans_indicatif) == "DawNFyX"
    avec = {"identity_state": "nomme", "pilot_callsign": "CHARLIE-33 | Wren5",
            "pilote_nom": "CHARLIE-33 | DawNFyX"}
    assert _report_flight_name(avec) == "Wren5"
    anon = {"identity_state": "anonyme", "aircraft_type": "Mi-24P",
            "pilot_callsign": None, "pilote_nom": None}
    assert "anonyme" in _report_flight_name(anon)


def test_named_pilots_noms():
    noms = {2: "CHARLIE-33 | DawNFyX"}
    vols = [_vol("CHARLIE-33 | Wren5", 1), _vol(None, 2)]
    n_named, sample, n_anon, _n_dep, _n_known = _named_pilots(vols, vols, noms)
    assert (n_named, n_anon, sample) == (2, 0, ["DawNFyX", "Wren5"])
    # Sans le dictionnaire, le vol sans indicatif reste anonyme (état d'avant).
    assert _named_pilots(vols, vols)[:3] == (1, ["Wren5"], 1)
    # Même nom qu'un indicatif présent : un seul pilote.
    doublon = [_vol("CHARLIE-33 | Wren5", 1), _vol(None, 3)]
    n_named, sample, n_anon, *_ = _named_pilots(doublon, doublon, {3: "CHARLIE-33 | Wren5"})
    assert (n_named, n_anon, sample) == (1, 0, ["Wren5"])


def test_flight_to_dict_pilote_nom():
    v = _vol(None, 2)
    assert _flight_to_dict(v, nom="CHARLIE-33 | DawNFyX")["pilote_nom"] == "CHARLIE-33 | DawNFyX"
    assert _flight_to_dict(v)["pilote_nom"] is None
