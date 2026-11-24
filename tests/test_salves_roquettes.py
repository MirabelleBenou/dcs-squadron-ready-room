"""Lot « Le Débrief : la précision des roquettes par salve » (v1.0057) : les
règles du cadrage R1, hors ligne, sur des évènements fabriqués -- aucun
journal réel, ni base, ni clé API.

1. `test_salves_separees_par_plus_de_5_s` -- deux tirs à 0,1 s et un à 10 s :
   deux salves.
2. `test_borne_de_5_s_comprise` -- deux tirs à 5,0 s d'écart : une salve.
3. `test_kill_dans_la_fenetre_met_la_salve_au_but` -- sans impact, un kill
   100 s après le dernier tir : au but.
4. `test_kill_hors_fenetre_ne_compte_pas` -- le même kill 121 s après : pas au
   but.
5. `test_un_kill_revient_a_une_seule_salve` -- deux salves (t 0 et t 30), un
   kill à t 40 : la seconde seule.
6. `test_kill_du_vol_par_le_moteur` -- par `_compute_flight_stats` : un kill du
   vol avec la même arme met la salve au but, un kill avec une autre arme non.
7. `test_missile_sans_salves` -- par `_compute_flight_stats` : une arme de
   famille 11 n'a ni `salvos` ni `salvos_hit`.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload

OID = "7001"


def _tir(t: float) -> engine.MergedEvent:
    """Un tir de roquette fabriqué, sans lien avec un impact."""
    return engine.MergedEvent(
        type="shot", t=t, initiator_object_id=OID, target_object_id=None,
        initiator_unit_type=None, target_unit_type=None, weapon="S-13OF", weapon_family=33,
    )


def _salves(ts: list[float], kills_t: list[float] | None = None) -> dict:
    return engine._salves_roquettes([_tir(t) for t in ts], [], kills_t or [])


def _code(famille: int) -> str:
    """Un `weapon_type` DCS fabriqué : la famille au troisième octet."""
    return str((4 << 24) | (4 << 16) | (famille << 8) | 17)


def _ev(index, t, type, weapon, famille=None, toid=None) -> DebriefEvent:
    return DebriefEvent(
        index=index, t=t, type=type,
        initiator_object_id=OID, initiator_pilot_name=None, initiator_unit_type=None,
        initiator_mission_id=None, initiator_coalition=None,
        target_object_id=toid, target_pilot_name=None, target_unit_type=None,
        weapon=weapon, event_id=str(index), linked_event_id=None,
        target_slot=None, target_mission_id=None,
        raw={"weapon_type": _code(famille)} if famille is not None else {},
    )


def _stats(evs: list[DebriefEvent]) -> dict:
    pairs = [(
        DebriefUpload(id="u0", sha256="u0", kind="debrief", filename="u0.log"),
        DebriefLogData(header=DebriefHeader(), events=evs, graveyard=[]),
    )]
    merged = engine._merge_events(pairs)
    fl = engine.ComputedFlight(
        object_id=OID, acmi_track_id=None, aircraft_type="Mi-24P", coalition="2",
        pilote_profile_id=None, pilot_callsign="Hind", identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    engine._compute_flight_stats([fl], merged, None, pairs)
    return fl.stats


def test_salves_separees_par_plus_de_5_s() -> None:
    assert _salves([0.0, 0.1, 10.0]) == {"salvos": 2, "salvos_hit": 0}


def test_borne_de_5_s_comprise() -> None:
    assert _salves([0.0, 5.0]) == {"salvos": 1, "salvos_hit": 0}


def test_kill_dans_la_fenetre_met_la_salve_au_but() -> None:
    assert _salves([0.0, 1.0], kills_t=[101.0]) == {"salvos": 1, "salvos_hit": 1}


def test_kill_hors_fenetre_ne_compte_pas() -> None:
    assert _salves([0.0, 1.0], kills_t=[122.0]) == {"salvos": 1, "salvos_hit": 0}


def test_un_kill_revient_a_une_seule_salve() -> None:
    assert _salves([0.0, 30.0], kills_t=[40.0]) == {"salvos": 2, "salvos_hit": 1}


def test_kill_du_vol_par_le_moteur() -> None:
    tirs = [_ev(i, 100.0 + i, "shot", "S-13OF", famille=33) for i in range(3)]
    # Le dernier tir est à 102 s : le kill, 18 s après, est à 120 s.
    st = _stats(tirs + [_ev(10, 120.0, "kill", "S-13OF", toid="900")])
    assert st["shots_by_weapon"]["S-13OF"] == {
        "shots": 3, "touched": 0, "precision": 0.0, "salvos": 1, "salvos_hit": 1,
    }
    # Un kill du vol avec une autre arme ne compte pas.
    st = _stats(tirs + [_ev(10, 120.0, "kill", "Mk-82", toid="900")])
    assert st["shots_by_weapon"]["S-13OF"]["salvos_hit"] == 0


def test_missile_sans_salves() -> None:
    st = _stats([
        _ev(1, 100.0, "shot", "AGM-114K", famille=11),
        _ev(2, 120.0, "kill", "AGM-114K", toid="900"),
    ])
    assert st["shots_by_weapon"]["AGM-114K"] == {"shots": 1, "touched": 0, "precision": 0.0}
