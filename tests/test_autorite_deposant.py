"""Lot « Un seul journal fait foi pour les tirs d'un vol » (v1.0028) : les
règles du cadrage §2, hors ligne, sur des évènements fabriqués -- aucun
journal réel dans l'archive, ni base, ni clé API.

1. `test_salve_decalee_le_deposant_fait_foi` -- deux journaux décalés de
   0,05 s, une salve de dix roquettes à 0,04 s d'écart, des liens différents
   dans chaque journal : la précision du déposant égale celle de son journal
   seul, et ses rafales comptent autant de tirs que sa précision.
2. `test_impact_lie_ailleurs_ne_touche_pas` -- un impact lié qui n'existe que
   dans le journal d'un autre ne rend pas touché le tir du déposant.
3. `test_sans_deposant_journal_temoin` -- un pilote qui n'a rien déposé, vu
   par trois journaux dont l'un voit plus de ses tirs : il est compté sur
   celui-là, sans tir fantôme ; à égalité, sur le premier par `sha256`.
4. `test_vol_sans_tir_inchange` -- un vol sans fait de tir n'a pas de journal
   source, et ses statistiques restent celles d'avant.
5. `test_canon_double_une_rafale` -- un canon double fait une rafale, avec la
   somme des obus.
6. `test_obus_lus_dans_le_journal_source` -- deux journaux qui écrivent des
   obus différents pour la même rafale : ceux du journal source.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload

OID = "7001"
ROQUETTE = 33  # famille unitaire : une précision


def _code(famille: int) -> str:
    """Un `weapon_type` DCS fabriqué : la famille au troisième octet."""
    return str((4 << 24) | (4 << 16) | (famille << 8) | 17)


def _ev(index, t, type, weapon=None, famille=None, linked=None, ammo=None, ioid=OID,
        toid=None) -> DebriefEvent:
    raw: dict = {}
    if famille is not None:
        raw["weapon_type"] = _code(famille)
    if ammo is not None:
        raw["ammo_consumption"] = str(ammo)
    return DebriefEvent(
        index=index, t=t, type=type,
        initiator_object_id=ioid, initiator_pilot_name=None, initiator_unit_type=None,
        initiator_mission_id=None, initiator_coalition=None,
        target_object_id=toid, target_pilot_name=None, target_unit_type=None,
        weapon=weapon, event_id=str(index), linked_event_id=linked,
        target_slot=None, target_mission_id=None, raw=raw,
    )


def _sous_controle(index: int) -> DebriefEvent:
    """La vie du déposant : `under control` de l'`object_id` du vol."""
    return _ev(index, 0.0, "under control")


def _paire(sha: str, events: list[DebriefEvent], deposant: int | None = None):
    upload = DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log",
                           depositor_profile_id=deposant)
    return upload, DebriefLogData(header=DebriefHeader(), events=events, graveyard=[])


def _stats(pairs, profil: int | None = None) -> dict:
    merged = engine._merge_events(pairs)
    fl = engine.ComputedFlight(
        object_id=OID, acmi_track_id=None, aircraft_type="Mi-24P", coalition="1",
        pilote_profile_id=profil, pilot_callsign="Golem", identity_state="nomme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    engine._compute_flight_stats([fl], merged, None, pairs)
    return fl.stats


def _tirs_des_rafales(st: dict) -> dict:
    tot: dict = {}
    for b in st["bursts"]:
        for x in b.get("weapons") or [{"weapon": b["weapon"], "shots": b["shots"]}]:
            tot[x["weapon"]] = tot.get(x["weapon"], 0) + x["shots"]
    return tot


def _salve(t0: float, ids: int, liens: set[int]) -> list[DebriefEvent]:
    """Dix S-8KOM à 0,04 s d'écart ; un impact lié pour chaque tir de `liens`."""
    evs = []
    for i in range(10):
        evs.append(_ev(ids + i, t0 + 0.04 * i, "shot", "S-8KOM", famille=ROQUETTE))
    for i in sorted(liens):
        evs.append(_ev(ids + 100 + i, t0 + 3.0 + 0.04 * i, "hit", "S-8KOM", famille=ROQUETTE,
                       linked=str(ids + i), toid=f"90{i}"))
    return evs


def test_salve_decalee_le_deposant_fait_foi() -> None:
    # Le témoin (sha « a », premier de la fusion) est en avance de 0,05 s :
    # chaque roquette du déposant tombe au plus près de la VOISINE du témoin.
    deposant = _paire("b", [_sous_controle(1)] + _salve(100.0, 10, {1, 2}), deposant=42)
    temoin = _paire("a", _salve(99.95, 500, {5, 6, 7}), deposant=7)

    # Le piège est bien là : la fusion apparie des roquettes voisines, et la
    # lecture « n'importe quel journal » gonflerait la précision.
    merged = engine._merge_events([temoin, deposant])
    tirs = [e for e in merged if e.type == "shot"]
    assert any(int(e.event_id_by_upload["b"]) - 10 != int(e.event_id_by_upload["a"]) - 500
               for e in tirs if "a" in e.event_id_by_upload and "b" in e.event_id_by_upload)
    impacts = [e for e in merged if e.type == "hit"]
    assert sum(1 for s in tirs if any(engine._shot_hit_linked(s, h) for h in impacts)) > 2

    st = _stats([temoin, deposant], profil=42)
    seul = _stats([deposant], profil=42)
    assert st["shots_by_weapon"]["S-8KOM"] == {"shots": 10, "touched": 2, "precision": 0.2, "salvos": 1, "salvos_hit": 1}
    assert st["shots_by_weapon"] == seul["shots_by_weapon"]
    assert _tirs_des_rafales(st) == {"S-8KOM": 10}
    assert st["bursts"][0]["hits"] == 2
    # Ce qui n'est pas un tir ne bouge pas : la fiabilité reste lue au profil.
    assert st["precision_reliability"] == "fiable" and st["pilot_deposited"] is True


def test_impact_lie_ailleurs_ne_touche_pas() -> None:
    deposant = _paire("b", [_sous_controle(1), _ev(2, 100.0, "shot", "9M114", famille=11)], deposant=42)
    autre = _paire("a", [
        _ev(11, 100.02, "shot", "9M114", famille=11),
        _ev(12, 104.0, "hit", "9M114", famille=11, linked="11", toid="900"),
    ], deposant=7)
    st = _stats([autre, deposant], profil=42)
    assert st["shots_by_weapon"]["9M114"] == {"shots": 1, "touched": 0, "precision": 0.0}
    assert st["bursts"][0]["hits"] == 0 and st["bursts"][0]["target_object_ids"] == []


def test_sans_deposant_journal_temoin() -> None:
    # Trois journaux, aucun du pilote, un tir toutes les 2 s. « b » voit quatre
    # tirs, « a » et « c » trois ; « c » est décalé de 0,6 s, hors de la
    # fenêtre de fusion : ses trois tirs seraient trois fantômes.
    a = _paire("a", [_ev(i, 100.0 + 2 * i, "shot", "SNEB", famille=ROQUETTE) for i in range(3)], deposant=1)
    b = _paire("b", [_ev(10 + i, 100.0 + 2 * i, "shot", "SNEB", famille=ROQUETTE) for i in range(4)], deposant=2)
    c = _paire("c", [_ev(20 + i, 100.6 + 2 * i, "shot", "SNEB", famille=ROQUETTE) for i in range(3)], deposant=3)
    pairs = [a, b, c]
    assert sum(1 for e in engine._merge_events(pairs) if e.type == "shot") == 7
    st = _stats(pairs)
    assert st["shots_by_weapon"]["SNEB"] == {"shots": 4, "touched": 0, "precision": 0.0, "salvos": 1, "salvos_hit": 0}
    assert st["shots_by_weapon"] == _stats([b])["shots_by_weapon"]
    assert _tirs_des_rafales(st) == {"SNEB": 4}
    assert st["precision_reliability"] == "partielle" and st["pilot_deposited"] is False

    # À égalité (trois tirs chacun), le premier par `sha256` : « a », le seul
    # à lier un impact à son deuxième tir.
    a2 = _paire("a", [_ev(i, 100.0 + 2 * i, "shot", "SNEB", famille=ROQUETTE) for i in range(3)]
                + [_ev(9, 103.0, "hit", "SNEB", famille=ROQUETTE, linked="1", toid="900")], deposant=1)
    c2 = _paire("c", [_ev(20 + i, 100.6 + 2 * i, "shot", "SNEB", famille=ROQUETTE) for i in range(3)], deposant=3)
    st2 = _stats([c2, a2])
    assert st2["shots_by_weapon"]["SNEB"] == {"shots": 3, "touched": 1, "precision": 0.333, "salvos": 1, "salvos_hit": 1}


def test_vol_sans_tir_inchange() -> None:
    # Décollage, une collision (un `hit` au nom d'un appareil), un obus reçu
    # sans arme ni lien, un abattage, un atterrissage -- vus par deux journaux.
    def journal(dt: float, base: int) -> list[DebriefEvent]:
        return [
            _ev(base + 1, 10.0 + dt, "takeoff"),
            _ev(base + 2, 50.0 + dt, "hit", "F-4E", famille=1, toid="901"),
            _ev(base + 3, 60.0 + dt, "hit", toid="902"),
            _ev(base + 4, 61.0 + dt, "kill", "F-4E", toid="901"),
            _ev(base + 5, 90.0 + dt, "land"),
        ]
    pairs = [_paire("a", journal(0.0, 0), deposant=7), _paire("b", journal(0.03, 100), deposant=8)]
    fl = engine.ComputedFlight(
        object_id=OID, acmi_track_id=None, aircraft_type="F-4E", coalition="2",
        pilote_profile_id=None, pilot_callsign=None, identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    assert engine._journal_source(fl, pairs) is None
    st = _stats(pairs)
    # Les valeurs du v1.0027, au champ près.
    assert st["shots_by_weapon"] == {} and st["cannon_by_weapon"] == {} and st["bursts"] == []
    assert st["cannon_bursts"] == 0 and st["cannon_hits"] == 1
    assert st["kills"] == [{"target_object_id": "901", "target_unit_type": None, "weapon": "F-4E", "t": 61.0}]
    assert (st["takeoffs"], st["landings"]) == (1, 1)
    assert st["phases"] == [{"type": "takeoff", "t": 10.0}, {"type": "land", "t": 90.0}]


def test_canon_double_une_rafale() -> None:
    # Un Mirage F1 : deux débuts puis deux fins au même instant, une paire
    # par canon -- une pression de détente, les obus des deux canons.
    double = [
        _ev(1, 50.0, "start shooting", "defa_553"),
        _ev(2, 50.0, "start shooting", "defa_553"),
        _ev(3, 50.8, "end shooting", "defa_553", ammo=15),
        _ev(4, 50.8, "end shooting", "defa_553", ammo=14),
        _ev(5, 52.0, "hit", toid="900"),
    ]
    st = _stats([_paire("a", double)])
    assert st["cannon_by_weapon"]["defa_553"] == {"bursts": 1, "rounds": 29, "bursts_hit": 1, "rounds_hit": 1}
    # Un canon simple n'est pas touché : deux rafales à 0,1 s, deux rafales.
    simple = [
        _ev(1, 50.0, "start shooting", "GSh-30-2K"),
        _ev(2, 50.05, "end shooting", "GSh-30-2K", ammo=4),
        _ev(3, 50.1, "start shooting", "GSh-30-2K"),
        _ev(4, 50.3, "end shooting", "GSh-30-2K", ammo=6),
    ]
    st = _stats([_paire("a", simple)])
    assert st["cannon_by_weapon"]["GSh-30-2K"] == {"bursts": 2, "rounds": 10, "bursts_hit": 0, "rounds_hit": 0}


def test_obus_lus_dans_le_journal_source() -> None:
    # Le témoin, premier de la fusion, écrit 49 obus ; le déposant, 38.
    deposant = _paire("b", [_sous_controle(1), _ev(2, 70.0, "start shooting", "M-61A1"),
                            _ev(3, 71.0, "end shooting", "M-61A1", ammo=38)], deposant=42)
    temoin = _paire("a", [_ev(12, 70.02, "start shooting", "M-61A1"),
                          _ev(13, 71.02, "end shooting", "M-61A1", ammo=49)], deposant=7)
    st = _stats([temoin, deposant], profil=42)
    assert st["cannon_by_weapon"]["M-61A1"]["rounds"] == 38
