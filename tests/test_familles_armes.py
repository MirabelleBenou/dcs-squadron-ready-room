"""Lot « L'écran de la précision » (v1.0029) : le moteur et le dossier servent
la famille des armes (cadrage §2.1, §2.2), hors ligne, sur des évènements
fabriqués -- aucun journal réel dans l'archive, ni base, ni clé API.

1. `test_familles_du_vol` -- `stats["weapon_families"]` : une entrée par arme
   de `shots_by_weapon` dont la famille est connue, la famille du premier tir
   dans l'ordre du temps ; une arme sans famille n'y figure pas.
2. `test_cle_toujours_presente` -- un vol sans tir porte `{}` ; le canon n'y
   entre pas.
3. `test_aucune_autre_cle` -- les `stats` gardent leurs clés d'avant, plus
   `weapon_families` seulement.
4. `test_dossier_familles` -- `familles` réunie sur les seuls vols fiables, la
   première vue l'emporte ; absente quand elle serait vide.
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


def _ev(index, t, type, weapon=None, famille=None, linked=None, ammo=None) -> DebriefEvent:
    raw: dict = {}
    if famille is not None:
        raw["weapon_type"] = _code(famille)
    if ammo is not None:
        raw["ammo_consumption"] = str(ammo)
    return DebriefEvent(
        index=index, t=t, type=type,
        initiator_object_id=OID, initiator_pilot_name=None, initiator_unit_type=None,
        initiator_mission_id=None, initiator_coalition=None,
        target_object_id=None, target_pilot_name=None, target_unit_type=None,
        weapon=weapon, event_id=str(index), linked_event_id=linked,
        target_slot=None, target_mission_id=None, raw=raw,
    )


def _stats(journal: list[DebriefEvent]) -> dict:
    pairs = [(DebriefUpload(id="u0", sha256="u0", kind="debrief", filename="u0.log"),
              DebriefLogData(header=DebriefHeader(), events=journal, graveyard=[]))]
    merged = engine._merge_events(pairs)
    fl = engine.ComputedFlight(
        object_id=OID, acmi_track_id=None, aircraft_type="Mi-24P", coalition="1",
        pilote_profile_id=None, pilot_callsign="MistyKestrel42", identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    engine._compute_flight_stats([fl], merged, None, pairs)
    return fl.stats


def test_familles_du_vol() -> None:
    journal = [
        _ev(1, 100.0, "shot", "9M114 Shturm (AT-6 Spiral)", famille=8),
        _ev(2, 130.0, "shot", "S-5KP HEAT/Frag", famille=33),
        _ev(3, 131.0, "shot", "S-5KP HEAT/Frag", famille=33),
        _ev(4, 200.0, "shot", "BKF - 12 x PTAB-2.5KO", famille=38),
        # Le premier tir n'a pas de famille : la famille est celle du premier qui en a une.
        _ev(5, 250.0, "shot", "Mk-82"),
        _ev(6, 260.0, "shot", "Mk-82", famille=9),
        # Une arme sans famille : hors de la clé.
        _ev(7, 300.0, "shot", "Inconnue"),
    ]
    st = _stats(journal)
    assert st["weapon_families"] == {
        "9M114 Shturm (AT-6 Spiral)": 8,
        "S-5KP HEAT/Frag": 33,
        "BKF - 12 x PTAB-2.5KO": 38,
        "Mk-82": 9,
    }
    assert set(st["weapon_families"]) <= set(st["shots_by_weapon"])
    assert "Inconnue" in st["shots_by_weapon"]
    # L'ordre est celui de `shots_by_weapon`.
    assert list(st["weapon_families"]) == [w for w in st["shots_by_weapon"] if w != "Inconnue"]


def test_cle_toujours_presente() -> None:
    assert _stats([])["weapon_families"] == {}
    canon = [
        _ev(1, 10.0, "start shooting", "GSh-30-2K"),
        _ev(2, 12.0, "end shooting", "GSh-30-2K", famille=4, ammo=20),
    ]
    st = _stats(canon)
    assert st["cannon_by_weapon"]["GSh-30-2K"]["rounds"] == 20
    assert st["weapon_families"] == {}


def test_aucune_autre_cle() -> None:
    st = _stats([_ev(1, 100.0, "shot", "S-5KP HEAT/Frag", famille=33)])
    assert set(st) == {
        "takeoffs", "landings", "engine_on", "engine_off", "crashed", "ejected", "pilot_dead",
        "kills", "shots_by_weapon", "cannon_bursts", "cannon_hits", "cannon_by_weapon",
        "weapon_families", "flight_time_s", "alt_max", "precision_reliability", "pilot_deposited",
        "bursts", "threat_log", "phases",
    }


def test_dossier_familles() -> None:
    s = SimpleNamespace(id="s1", mission_date=None, display_name="M", title="M", campaign_id=None)

    def vol(fid, fiable, **stats):
        stats["precision_reliability"] = "fiable" if fiable else "partielle"
        return SimpleNamespace(id=fid, stats=stats, aircraft_type="Mi-24P", t_start=0.0, t_end=1.0)

    vols = [
        (vol("f1", True, shots_by_weapon={"9M114": {"shots": 4, "touched": 4, "precision": 1.0}},
             weapon_families={"9M114": 8}), s),
        # La première vue l'emporte.
        (vol("f2", True, shots_by_weapon={"9M114": {"shots": 1, "touched": 0, "precision": 0.0},
                                          "BKF": {"releases": 16, "salvos": 1, "salvos_hit": 0}},
             weapon_families={"9M114": 11, "BKF": 38}), s),
        # Un vol non fiable n'apporte rien.
        (vol("f3", False, shots_by_weapon={"S-5KP": {"shots": 64, "touched": 2, "precision": 0.031}},
             weapon_families={"S-5KP": 33}), s),
    ]
    d = _dossier_prive(vols, {}, {})
    assert d["familles"] == {"9M114": 8, "BKF": 38}
    # Sans famille : la clé est absente, le dossier garde sa forme d'avant.
    sans = _dossier_prive([(vol("f4", True, shots_by_weapon={"X": {"releases": 2}}), s)], {}, {})
    assert "familles" not in sans
    vide = _dossier_prive([], {}, {})
    assert "familles" not in vide and "canon" not in vide
