"""Lot « Les heures de jour et de nuit » (v1.0068) : les règles R2 à R9 du
cadrage, hors ligne -- doubles `SimpleNamespace`, `engine.ComputedFlight` et
`debriefer.DebriefEvent` ; ni PostgreSQL, ni réseau. `raw["ta"]` est une chaîne,
comme le parseur la rend.

1. `test_horloge_francfort` -- `ta - t` de l'évènement `mission start`.
2. `test_horloge_absente` -- sans `mission start`, sans `ta`, sans paire : `None`.
3. `test_horloge_premier_journal` -- le journal le plus ancien (`uploaded_at`,
   puis `id`) qui porte une horloge la donne.
4. `test_periode_bornes` -- 19 h 00 comprise, 6 h 00 exclue ; passage de minuit.
5. `test_poser_periodes` -- le premier `takeoff` des phases, à défaut `t_start`.
6. `test_periode_effective` -- la correction l'emporte ; `_correction_periode`.
7. `test_peut_corriger` -- le pilote du vol, ou qui peut modifier une session.
8. `test_synthese_membre_jour_nuit` -- heures de jour et de nuit d'un membre.
9. `test_unites_jour_nuit` -- heures de jour et de nuit d'une escadrille.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine
from app.debrief.api import (
    _correction_periode,
    _peut_corriger_periode,
    _periode_effective,
    _synthese_membre,
    _unites_au_jour_du_vol,
)
from app.debrief.debriefer import DebriefEvent


def _ev(type_, t, raw=None) -> DebriefEvent:
    return DebriefEvent(
        index=1, t=t, type=type_,
        initiator_object_id=None, initiator_pilot_name=None, initiator_unit_type=None,
        initiator_mission_id=None, initiator_coalition=None,
        target_object_id=None, target_pilot_name=None, target_unit_type=None,
        weapon=None, event_id=None, linked_event_id=None,
        target_slot=None, target_mission_id=None, raw=raw or {},
    )


def _paire(uploaded_at, id_, *events):
    return (NS(uploaded_at=uploaded_at, id=id_), NS(events=list(events)))


def _depart(t, ta):
    return _ev("mission start", t, {"ta": ta})


def _cf(t_start, phases=()):
    return engine.ComputedFlight(
        object_id="1", acmi_track_id=None, aircraft_type="Mi-24P", coalition="2",
        pilote_profile_id=None, pilot_callsign=None, identity_state="anonyme",
        identity_source=None, t_start=t_start, t_end=None, slot_mission=None,
        mission_id_dcs=None, stats={"phases": [dict(p) for p in phases]},
    )


def test_horloge_francfort() -> None:
    pairs = [_paire(datetime(2026, 11, 1, tzinfo=timezone.utc), "a", _depart(1029.533, "26229.533"))]
    assert abs(engine._horloge_mission(pairs) - 25200.0) < 1e-6


def test_horloge_absente() -> None:
    d = datetime(2026, 11, 1, tzinfo=timezone.utc)
    assert engine._horloge_mission([_paire(d, "a", _ev("takeoff", 10.0))]) is None
    assert engine._horloge_mission([_paire(d, "a", _ev("mission start", 5.0))]) is None
    assert engine._horloge_mission([]) is None


def test_horloge_premier_journal() -> None:
    tot = datetime(2026, 11, 1, 8, tzinfo=timezone.utc)
    tard = datetime(2026, 11, 1, 9, tzinfo=timezone.utc)
    ancien = _paire(tot, "a", _depart(100.0, "3700.0"))      # horloge 3600
    recent = _paire(tard, "b", _depart(100.0, "7300.0"))     # horloge 7200
    # L'ordre de la liste est l'inverse de (uploaded_at, id) : le plus ancien gagne.
    assert engine._horloge_mission([recent, ancien]) == 3600.0
    # Même instant : l'id départage.
    assert engine._horloge_mission([_paire(tot, "z", _depart(0.0, "1.0")),
                                    _paire(tot, "b", _depart(0.0, "2.0"))]) == 2.0
    # Le plus ancien n'a pas d'horloge : le suivant la donne.
    sans = _paire(tot, "a", _ev("takeoff", 1.0))
    assert engine._horloge_mission([recent, sans]) == 7200.0


def test_periode_bornes() -> None:
    f = engine._periode_du_decollage
    assert f(0, 21599) == "nuit"
    assert f(0, 21600) == "jour"
    assert f(0, 68399) == "jour"
    assert f(0, 68400) == "nuit"
    assert f(82800, 7200) == "nuit"   # 23 h + 2 h = 1 h 00
    assert f(25200, 600) == "jour"
    assert f(None, 600) is None
    assert f(25200, None) is None


def test_poser_periodes() -> None:
    de_nuit = _cf(0.0, [{"type": "engine startup", "t": 100.0}, {"type": "takeoff", "t": 3700.0}])
    sans_decollage = _cf(1800.0, [{"type": "engine startup", "t": 1700.0}])
    engine._poser_periodes([de_nuit, sans_decollage], 64800)  # 18 h 00
    assert de_nuit.periode == "nuit"          # 18 h 00 + 3700 s = 19 h 01
    assert sans_decollage.periode == "jour"   # t_start 1800 : 18 h 30
    engine._poser_periodes([de_nuit, sans_decollage], None)
    assert de_nuit.periode is None and sans_decollage.periode is None


def test_periode_effective() -> None:
    assert _periode_effective(NS(periode="jour", periode_corrigee="nuit")) == "nuit"
    assert _periode_effective(NS(periode="jour", periode_corrigee=None)) == "jour"
    assert _periode_effective(NS(periode=None, periode_corrigee=None)) is None
    assert _periode_effective(NS()) is None
    assert _correction_periode("jour", "jour") is None
    assert _correction_periode("jour", "nuit") == "nuit"
    assert _correction_periode(None, "nuit") == "nuit"


def test_peut_corriger() -> None:
    assert _peut_corriger_periode(42, "42", False) is True
    assert _peut_corriger_periode(42, "7", False) is False
    assert _peut_corriger_periode(None, "7", False) is False
    assert _peut_corriger_periode(42, "7", True) is True
    assert _peut_corriger_periode(None, "7", True) is True


def _vol(pid, session, secondes, periode=None, corrigee=None, ac="Mi-24P"):
    return NS(pilote_profile_id=pid, session_id=session, t_start=0, t_end=secondes,
              coalition="2", object_id=None, aircraft_type=ac, stats={"kills": []},
              periode=periode, periode_corrigee=corrigee)


def test_synthese_membre_jour_nuit() -> None:
    s = NS(id="s1", campaign_id=None, mission_date=date(2026, 11, 1), display_name="M", title="M")
    jour = _vol(1, "s1", 3600, "jour")
    nuit = _vol(1, "s1", 7200, "nuit", "jour")   # calculée de nuit, corrigée en jour
    sans = _vol(1, "s1", 5400)                   # sans période : de jour
    p = _synthese_membre([(jour, s), (nuit, s), (sans, s)], {})["participation"]
    assert (p["heures"], p["heures_jour"], p["heures_nuit"]) == (4.5, 4.5, 0.0)
    nuit.periode_corrigee = "nuit"
    p = _synthese_membre([(jour, s), (nuit, s), (sans, s)], {})["participation"]
    assert (p["heures"], p["heures_jour"], p["heures_nuit"]) == (4.5, 2.5, 2.0)


def test_unites_jour_nuit() -> None:
    appartenances = {1: [NS(profile_id=1, squadron_id=10,
                            started_at=datetime(2026, 7, 6, tzinfo=timezone.utc), ended_at=None)]}
    jour_vol = date(2026, 11, 1)
    nuit = _vol(1, "s1", 1800, "nuit")
    nuit.t_start, nuit.t_end = 3600, 5400  # lot « Les heures comptées par mission » : sans recouvrement
    vols = [(_vol(1, "s1", 3600, "jour"), jour_vol), (nuit, jour_vol)]
    a = _unites_au_jour_du_vol(vols, appartenances, {})[10]["activite"]
    assert (a["heures"], a["heures_jour"], a["heures_nuit"]) == (1.5, 1.0, 0.5)
