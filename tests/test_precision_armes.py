"""Lot « La précision des armes — le moteur » (v1.0027) : les règles du
cadrage §2, hors ligne, sur des évènements fabriqués -- aucun journal réel
dans l'archive, ni base, ni clé API.

1. `test_famille_decodee` -- l'octet `(weapon_type >> 8) & 0xFF`, `None`
   sans code entier ; la fusion garde le premier journal, 0 compris.
2. `test_bombe_unitaire_ratee_en_precision` -- deux Mk-82 ratées : 0/2, plus
   « 2 largages ».
3. `test_tir_touche_par_impact_au_nom_different` -- le lien suffit, le nom
   d'arme de l'impact n'y fait rien ; famille inconnue : la règle d'avant.
4. `test_deux_salves_separees` -- plus de 5 s entre deux largages : deux salves.
5. `test_salve_touchee_59_s_pas_61_s` -- la fenêtre de 60 s après le dernier
   largage.
6. `test_canon_rafales_et_obus` -- obus tirés, obus au but, deux fenêtres qui
   se chevauchent, un obus compté une fois, un canon double.
7. `test_collision_exclue` -- un `hit` au nom d'un appareil n'est ni un obus
   au but ni un impact de sous-munition.
8. `test_dossier_salves_et_canon` -- la charge du dossier : salves sommées,
   clé `canon` triée par obus, absente sans canon.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine
from app.debrief.api import _dossier_prive
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload

OID = "7001"


def _code(famille: int) -> str:
    """Un `weapon_type` DCS fabriqué : la famille au troisième octet."""
    return str((4 << 24) | (4 << 16) | (famille << 8) | 17)


def _ev(index, t, type, weapon=None, famille=None, linked=None, ammo=None, ioid=OID) -> DebriefEvent:
    raw: dict = {}
    if famille is not None:
        raw["weapon_type"] = _code(famille)
    if ammo is not None:
        raw["ammo_consumption"] = str(ammo)
    return DebriefEvent(
        index=index, t=t, type=type,
        initiator_object_id=ioid, initiator_pilot_name=None, initiator_unit_type=None,
        initiator_mission_id=None, initiator_coalition=None,
        target_object_id=None, target_pilot_name=None, target_unit_type=None,
        weapon=weapon, event_id=str(index), linked_event_id=linked,
        target_slot=None, target_mission_id=None, raw=raw,
    )


def _upload(sha: str) -> DebriefUpload:
    return DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log")


def _stats(*journaux: list[DebriefEvent]) -> dict:
    pairs = [
        (_upload(f"u{i}"), DebriefLogData(header=DebriefHeader(), events=evs, graveyard=[]))
        for i, evs in enumerate(journaux)
    ]
    merged = engine._merge_events(pairs)
    fl = engine.ComputedFlight(
        object_id=OID, acmi_track_id=None, aircraft_type="F-4E", coalition="2",
        pilote_profile_id=None, pilot_callsign="Vortex", identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    engine._compute_flight_stats([fl], merged, None, pairs)
    return fl.stats


def test_famille_decodee() -> None:
    for famille in (7, 8, 9, 11, 33, 36, 38):
        assert engine._famille_arme({"weapon_type": _code(famille)}) == famille
    assert engine._famille_arme({}) is None
    assert engine._famille_arme({"weapon_type": "Mk-82"}) is None
    assert engine._munitions_tirees("end shooting", {"ammo_consumption": "25"}) == 25
    assert engine._munitions_tirees("start shooting", {"ammo_consumption": "25"}) is None
    assert engine._munitions_tirees("end shooting", {}) is None

    # Fusion : le premier journal qui les donne l'emporte (tri par sha256), 0 compris.
    a = [_ev(1, 10.0, "end shooting", "GSh-30-2K", ammo=0)]
    b = [_ev(1, 10.1, "end shooting", "GSh-30-2K", famille=4, ammo=12)]
    pairs = [
        (_upload(sha), DebriefLogData(header=DebriefHeader(), events=evs, graveyard=[]))
        for sha, evs in (("a", a), ("b", b))
    ]
    (fin,) = engine._merge_events(pairs)
    assert fin.ammo == 0 and fin.weapon_family == 4
    # Hors de la clé naturelle : elle garde sa forme d'avant.
    assert fin.natural_key() == f"end shooting|{OID}||GSh-30-2K|10.0"


def test_bombe_unitaire_ratee_en_precision() -> None:
    st = _stats([_ev(1, 100.0, "shot", "Mk-82", famille=9), _ev(2, 160.0, "shot", "Mk-82", famille=9)])
    assert st["shots_by_weapon"]["Mk-82"] == {"shots": 2, "touched": 0, "precision": 0.0}


def test_tir_touche_par_impact_au_nom_different() -> None:
    journal = [
        _ev(1, 100.0, "shot", "S-13OF", famille=33),
        _ev(2, 101.5, "hit", "S-13OF Frag HE", famille=33, linked="1"),
        _ev(3, 102.0, "shot", "S-13OF", famille=33),
    ]
    assert _stats(journal)["shots_by_weapon"]["S-13OF"] == {"shots": 2, "touched": 1, "precision": 0.5, "salvos": 1, "salvos_hit": 1}
    # Famille inconnue : la règle d'avant -- aucun impact de la même arme n'est
    # lié dans la session, donc des largages.
    inconnue = [
        _ev(1, 100.0, "shot", "S-13OF"),
        _ev(2, 101.5, "hit", "S-13OF Frag HE", linked="1"),
    ]
    assert _stats(inconnue)["shots_by_weapon"]["S-13OF"] == {"releases": 1}


def test_deux_salves_separees() -> None:
    journal = [
        _ev(1, 100.0, "shot", "CBU-87", famille=38),
        _ev(2, 103.0, "shot", "CBU-87", famille=38),
        _ev(3, 108.5, "shot", "CBU-87", famille=38),  # 5,5 s après le précédent
        _ev(4, 112.0, "shot", "CBU-87", famille=38),
    ]
    assert _stats(journal)["shots_by_weapon"]["CBU-87"] == {"releases": 4, "salvos": 2, "salvos_hit": 0}


def test_salve_touchee_59_s_pas_61_s() -> None:
    largages = [_ev(1, 100.0, "shot", "Mk-20 Rockeye", famille=38),
                _ev(2, 101.0, "shot", "Mk-20 Rockeye", famille=38)]
    a_59 = largages + [_ev(3, 160.0, "hit", "Mk 118", famille=38)]   # 59 s après le dernier
    a_61 = largages + [_ev(3, 162.0, "hit", "Mk 118", famille=38)]   # 61 s après
    lie = largages + [_ev(3, 130.0, "hit", "Mk 118", famille=38, linked="1")]  # lié : ne compte pas
    assert _stats(a_59)["shots_by_weapon"]["Mk-20 Rockeye"] == {"releases": 2, "salvos": 1, "salvos_hit": 1}
    assert _stats(a_61)["shots_by_weapon"]["Mk-20 Rockeye"] == {"releases": 2, "salvos": 1, "salvos_hit": 0}
    assert _stats(lie)["shots_by_weapon"]["Mk-20 Rockeye"]["salvos_hit"] == 0


def test_canon_rafales_et_obus() -> None:
    journal = [
        _ev(1, 10.0, "start shooting", "GSh-30-2K"),
        _ev(2, 12.0, "end shooting", "GSh-30-2K", ammo=20),
        _ev(3, 13.0, "start shooting", "GSh-30-2K"),
        _ev(4, 15.0, "end shooting", "GSh-30-2K", ammo=30),
        _ev(5, 14.0, "hit"),   # dans les deux fenêtres : à la rafale commencée à 13 s
        _ev(6, 18.5, "hit"),   # dans la seule fenêtre de la seconde (15 + 4)
        _ev(7, 19.5, "hit"),   # hors de toute fenêtre
        _ev(8, 11.0, "hit", linked="99"),  # lié : jamais un obus au but
    ]
    st = _stats(journal)
    assert st["cannon_by_weapon"] == {
        "GSh-30-2K": {"bursts": 2, "rounds": 50, "bursts_hit": 1, "rounds_hit": 2},
    }
    # Les compteurs d'avant restent, inchangés.
    assert st["cannon_bursts"] == 2 and st["cannon_hits"] == 3
    # Le même obus vu par deux journaux ne compte qu'une fois.
    st2 = _stats(journal, [_ev(5, 14.1, "hit")])
    assert st2["cannon_by_weapon"]["GSh-30-2K"]["rounds_hit"] == 2
    # Un canon double (Mirage F1) : deux débuts puis deux fins au même
    # instant, une par canon -- une rafale par pression de détente, avec les
    # obus des deux canons.
    double = [
        _ev(1, 50.0, "start shooting", "defa_553"),
        _ev(2, 50.0, "start shooting", "defa_553"),
        _ev(3, 50.8, "end shooting", "defa_553", ammo=15),
        _ev(4, 50.8, "end shooting", "defa_553", ammo=15),
    ]
    assert _stats(double)["cannon_by_weapon"]["defa_553"] == {
        "bursts": 1, "rounds": 30, "bursts_hit": 0, "rounds_hit": 0,
    }


def test_collision_exclue() -> None:
    journal = [
        _ev(1, 10.0, "start shooting", "M61A1"),
        _ev(2, 12.0, "end shooting", "M61A1", ammo=100),
        _ev(3, 13.0, "shot", "CBU-87", famille=38),
        # Une collision : l'« arme » est l'appareil, sans lien.
        _ev(4, 13.5, "hit", "F-4E", famille=1),
        _ev(5, 13.6, "hit", "F-4E", famille=1),
    ]
    st = _stats(journal)
    assert st["cannon_by_weapon"]["M61A1"] == {"bursts": 1, "rounds": 100, "bursts_hit": 0, "rounds_hit": 0}
    assert st["shots_by_weapon"]["CBU-87"] == {"releases": 1, "salvos": 1, "salvos_hit": 0}
    assert "F-4E" not in st["shots_by_weapon"]


def test_dossier_salves_et_canon() -> None:
    s = SimpleNamespace(id="s1", mission_date=None, display_name="M", title="M", campaign_id=None)

    def vol(fid, fiable, **stats):
        stats["precision_reliability"] = "fiable" if fiable else "partielle"
        return SimpleNamespace(id=fid, stats=stats, aircraft_type="Mi-24P", t_start=0.0, t_end=1.0)

    vols = [
        (vol("f1", True,
             shots_by_weapon={"BKF PTAB": {"releases": 16, "salvos": 1, "salvos_hit": 0},
                              "9M114": {"shots": 6, "touched": 4, "precision": 0.667}},
             cannon_by_weapon={"GSh-30-2K": {"bursts": 34, "rounds": 346, "bursts_hit": 6, "rounds_hit": 16}}), s),
        (vol("f2", True,
             shots_by_weapon={"BKF PTAB": {"releases": 8, "salvos": 2, "salvos_hit": 1}},
             cannon_by_weapon={"GSh-30-2K": {"bursts": 1, "rounds": 25, "bursts_hit": 0, "rounds_hit": 0},
                               "M61A1": {"bursts": 2, "rounds": 400, "bursts_hit": 1, "rounds_hit": 3}}), s),
        (vol("f3", False,
             cannon_by_weapon={"GSh-30-2K": {"bursts": 99, "rounds": 999, "bursts_hit": 9, "rounds_hit": 9}}), s),
    ]
    d = _dossier_prive(vols, {}, {})
    lignes = {p["arme"]: p for p in d["precision"]}
    assert lignes["BKF PTAB"] == {"arme": "BKF PTAB", "tirs": 0, "touches": 0, "largages": 24,
                                  "salves": 3, "salves_touchees": 1}
    assert lignes["9M114"] == {"arme": "9M114", "tirs": 6, "touches": 4, "largages": 0}
    assert d["canon"] == [
        {"arme": "M61A1", "rafales": 2, "obus": 400, "rafales_touchees": 1, "obus_au_but": 3},
        {"arme": "GSh-30-2K", "rafales": 35, "obus": 371, "rafales_touchees": 6, "obus_au_but": 16},
    ]
    sans_canon = _dossier_prive([(vol("f4", True, shots_by_weapon={}), s)], {}, {})
    assert "canon" not in sans_canon
