"""Lot « Le journal dit quand un tir touche » (v1.0030) : les règles du
cadrage §3.1, hors ligne, sur des évènements fabriqués -- aucun journal réel
dans l'archive, ni base, ni clé API. La preuve sur les 22 journaux réels se
fait hors archive, contre la prédiction du CdP (cadrage §4.2).

1. `test_canon_au_journal` -- R1 : les pressions de détente de la même arme à
   5 s au plus se groupent en une ligne ; obus sommés, impacts reçus, cibles ;
   la rafale de tirs passe avant le canon à heure égale ; `cannon_by_weapon`
   ne change pas.
2. `test_salve_et_ses_cibles` -- R2 : une salve de sous-munitions porte les
   cibles des impacts de famille 38 non liés de sa fenêtre ; dans deux
   fenêtres, l'impact va à la salve commencée le plus tard ; ses autres clés
   ne changent pas.
3. `test_issues_des_cibles` -- R3 : intacte, détruite par un autre pilote,
   par une IA ; détruite par le vol lui-même, aucune entrée ; ordre.
4. `test_chaine_des_epaves` -- R3, R4 : une cible détruite par l'explosion
   d'une épave est un kill du tireur d'origine, compté à son bilan ; la ligne
   d'un autre la crédite au tireur d'origine, avec `explosion`.
5. `test_tolerance_et_maillons` -- la chaîne ne passe que par une épave déjà
   détruite (à 0,05 s près), dix maillons au plus.
6. `test_sans_cible_ni_kill_rien_de_neuf` -- un vol sans touche ni kill
   d'explosion : `targets` et `outcomes` vides, ses kills inchangés.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload

VOL, AUTRE = "7001", "7002"
MISSILE, SOUS_MUNITIONS = 11, 38


def _code(famille: int) -> str:
    return str((4 << 24) | (4 << 16) | (famille << 8) | 17)


def _ev(index, t, type, weapon=None, famille=None, linked=None, ammo=None, ioid=VOL,
        itype="Mi-24P", toid=None, ttype=None) -> DebriefEvent:
    raw: dict = {}
    if famille is not None:
        raw["weapon_type"] = _code(famille)
    if ammo is not None:
        raw["ammo_consumption"] = str(ammo)
    return DebriefEvent(
        index=index, t=t, type=type,
        initiator_object_id=ioid, initiator_pilot_name=None, initiator_unit_type=itype,
        initiator_mission_id=None, initiator_coalition=None,
        target_object_id=toid, target_pilot_name=None, target_unit_type=ttype,
        weapon=weapon, event_id=str(index), linked_event_id=linked,
        target_slot=None, target_mission_id=None, raw=raw,
    )


def _paire(sha: str, events: list[DebriefEvent], deposant: int | None = None):
    upload = DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log",
                           depositor_profile_id=deposant)
    return upload, DebriefLogData(header=DebriefHeader(), events=events, graveyard=[])


def _vol(oid: str, nom: str, profil: int) -> engine.ComputedFlight:
    return engine.ComputedFlight(
        object_id=oid, acmi_track_id=None, aircraft_type="Mi-24P", coalition="2",
        pilote_profile_id=profil, pilot_callsign=nom, identity_state="nomme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )


def _session(evenements: list[DebriefEvent]) -> dict[str, dict]:
    """Deux pilotes humains (`under control` dans leur journal) ; chaque
    évènement va au journal de son initiateur, les IA à celui du vol."""
    vol = [_ev(1, 0.0, "under control")] + [e for e in evenements if e.initiator_object_id != AUTRE]
    autre = [_ev(2, 0.0, "under control", ioid=AUTRE)] + [
        e for e in evenements if e.initiator_object_id == AUTRE
    ]
    pairs = [_paire("a", vol, deposant=1), _paire("b", autre, deposant=2)]
    vols = [_vol(VOL, "CHARLIE-33 | MistyKestrel42", 1), _vol(AUTRE, "COLT 1-1 | Vortex", 2)]
    engine._compute_flight_stats(vols, engine._merge_events(pairs), None, pairs)
    return {fl.object_id: fl.stats for fl in vols}


def test_canon_au_journal() -> None:
    st = _session([
        _ev(10, 100.0, "shot", "9M114", famille=MISSILE),
        _ev(11, 100.0, "start shooting", "GSh-30-2K"),
        _ev(12, 101.0, "end shooting", "GSh-30-2K", ammo=10),
        _ev(13, 102.0, "hit", toid="900", ttype="BRDM-2"),
        _ev(14, 105.5, "start shooting", "GSh-30-2K"),   # 4,5 s après la fin : même ligne
        _ev(15, 106.0, "end shooting", "GSh-30-2K", ammo=6),
        _ev(16, 107.0, "hit", toid="901", ttype="Ural-375"),
        _ev(17, 107.5, "hit", toid="900", ttype="BRDM-2"),
        _ev(18, 120.0, "start shooting", "GSh-30-2K"),   # 14 s après : ligne suivante
        _ev(19, 120.5, "end shooting", "GSh-30-2K", ammo=4),
    ])[VOL]
    lignes = st["bursts"]
    assert [(b["t"], bool(b.get("cannon"))) for b in lignes] == [(100.0, False), (100.0, True), (120.0, True)]
    assert lignes[1] == {
        "weapon": "GSh-30-2K", "t": 100.0, "cannon": True, "shots": 2, "rounds": 16,
        "rounds_hit": 3, "hits": 2, "target_unit_types": ["BRDM-2", "Ural-375"],
        "target_object_ids": ["900", "901"],
        "targets": [{"type": "BRDM-2", "n": 1}, {"type": "Ural-375", "n": 1}],
        "outcomes": [{"type": "BRDM-2", "issue": "intact", "n": 1},
                     {"type": "Ural-375", "issue": "intact", "n": 1}],
    }
    assert lignes[2]["shots"] == 1 and lignes[2]["rounds"] == 4 and lignes[2]["hits"] == 0
    assert lignes[2]["targets"] == [] and lignes[2]["outcomes"] == []
    # Le canon, arme par arme : la valeur d'avant le lot.
    assert st["cannon_by_weapon"] == {
        "GSh-30-2K": {"bursts": 3, "rounds": 20, "bursts_hit": 2, "rounds_hit": 3}}


def test_salve_et_ses_cibles() -> None:
    st = _session([
        _ev(10, 100.0, "shot", "CBU-87", famille=SOUS_MUNITIONS),
        _ev(11, 101.0, "shot", "CBU-87", famille=SOUS_MUNITIONS),
        _ev(12, 120.0, "hit", "BLU-97B", famille=SOUS_MUNITIONS, toid="900", ttype="BMP-1"),
        _ev(13, 140.0, "shot", "CBU-87", famille=SOUS_MUNITIONS),
        # Dans les deux fenêtres : à la salve commencée le plus tard.
        _ev(14, 150.0, "hit", "BLU-97B", famille=SOUS_MUNITIONS, toid="901", ttype="BMP-1"),
        # Lié : ce n'est pas une sous-munition de la salve.
        _ev(15, 151.0, "hit", "BLU-97B", famille=SOUS_MUNITIONS, linked="13", toid="902", ttype="T-55"),
        # Hors de toute fenêtre.
        _ev(16, 300.0, "hit", "BLU-97B", famille=SOUS_MUNITIONS, toid="903", ttype="T-55"),
    ])[VOL]
    premiere, seconde = st["bursts"]
    assert premiere["salvo"] is True and premiere["shots"] == 2 and premiere["hits"] == 0
    assert premiere["targets"] == [{"type": "BMP-1", "n": 1}]
    assert premiere["target_unit_types"] == [] and premiere["target_object_ids"] == []
    assert seconde["salvo"] is True and seconde["targets"] == [{"type": "BMP-1", "n": 1}]
    assert st["shots_by_weapon"]["CBU-87"] == {"releases": 3, "salvos": 2, "salvos_hit": 2}


def test_issues_des_cibles() -> None:
    st = _session([
        _ev(10, 100.0, "shot", "9M114", famille=MISSILE),
        _ev(11, 103.0, "hit", "9M114", famille=MISSILE, linked="10", toid="900", ttype="T-55"),
        _ev(12, 103.0, "hit", "9M114", famille=MISSILE, linked="10", toid="901", ttype="T-55"),
        _ev(13, 103.0, "hit", "9M114", famille=MISSILE, linked="10", toid="902", ttype="T-55"),
        _ev(14, 103.0, "hit", "9M114", famille=MISSILE, linked="10", toid="903", ttype="BMP-1"),
        _ev(15, 103.1, "hit", "9M114", famille=MISSILE, linked="10", toid="904", ttype="T-55"),
        _ev(20, 104.0, "kill", "9M114", toid="900", ttype="T-55"),               # le vol lui-même
        _ev(21, 300.0, "kill", "Mk 118", ioid=AUTRE, itype="F-4E-45MC", toid="901", ttype="T-55"),
        _ev(22, 200.0, "kill", "L31_120mm_HESH", ioid="555", itype="Challenger2",
            toid="902", ttype="T-55"),
    ])[VOL]
    ligne = st["bursts"][0]
    assert ligne["hits"] == 1
    assert ligne["targets"] == [{"type": "T-55", "n": 4}, {"type": "BMP-1", "n": 1}]
    assert ligne["outcomes"] == [
        {"type": "T-55", "issue": "detruit", "t": 200.0, "by": None,
         "by_unit_type": "Challenger2", "by_weapon": "L31 (120mm HESH)"},
        {"type": "T-55", "issue": "detruit", "t": 300.0, "by": "Vortex",
         "by_unit_type": "F-4E-45MC", "by_weapon": "Mk 118"},
        {"type": "T-55", "issue": "intact", "n": 1},
        {"type": "BMP-1", "issue": "intact", "n": 1},
    ]
    # La sous-ligne d'avant le lot ne bouge pas.
    assert ligne["destroyed_by_other"] == [
        {"target_unit_type": "T-55", "killer": "Vortex", "killer_weapon": "Mk 118", "kill_t": 300.0}]


def test_chaine_des_epaves() -> None:
    sts = _session([
        # Le vol détruit le Grad (950), dont l'épave explose : 951 puis 952 par 951.
        _ev(10, 100.0, "shot", "9M114", famille=MISSILE),
        _ev(11, 103.0, "hit", "9M114", famille=MISSILE, linked="10", toid="950", ttype="Grad_FDDM"),
        _ev(12, 103.5, "kill", "9M114", toid="950", ttype="Grad_FDDM"),
        _ev(13, 130.0, "kill", ioid="950", itype="Grad_FDDM", toid="951", ttype="BTR-70"),
        _ev(14, 160.0, "kill", ioid="951", itype="BTR-70", toid="952", ttype="BTR-70"),
        # L'autre pilote avait touché 951.
        _ev(20, 110.0, "shot", "Mk-81", famille=9, ioid=AUTRE, itype="F-4E-45MC"),
        _ev(21, 112.0, "hit", "Mk-81", famille=9, linked="20", ioid=AUTRE, itype="F-4E-45MC",
            toid="951", ttype="BTR-70"),
    ])
    st = sts[VOL]
    assert st["kills"][0]["target_object_id"] == "950"
    assert st["kills"][1:] == [
        {"target_object_id": "951", "target_unit_type": "BTR-70", "weapon": None, "t": 130.0,
         "explosion": {"wreck": "Grad_FDDM", "wreck_t": 103.5},
         "also_engaged_by": [{"pilot": "Vortex", "weapon": "Mk-81", "t": 112.0}]},
        {"target_object_id": "952", "target_unit_type": "BTR-70", "weapon": None, "t": 160.0,
         "explosion": {"wreck": "BTR-70", "wreck_t": 130.0}},
    ]
    # La ligne du vol : la cible qu'il a détruite n'a pas de sous-ligne.
    assert st["bursts"][0]["outcomes"] == []
    # La ligne de l'autre : créditée au tireur d'origine, l'explosion notée.
    assert sts[AUTRE]["bursts"][0]["outcomes"] == [
        {"type": "BTR-70", "issue": "detruit", "t": 130.0, "by": "MistyKestrel42",
         "by_unit_type": "Mi-24P", "by_weapon": "9M114", "explosion": "Grad_FDDM"}]
    assert not any("explosion" in k for k in sts[AUTRE]["kills"])


def _kill(t: float, ioid: str, toid: str, weapon: str | None = None) -> engine.MergedEvent:
    return engine.MergedEvent(type="kill", t=t, initiator_object_id=ioid, target_object_id=toid,
                              initiator_unit_type=None, target_unit_type=None, weapon=weapon)


def test_tolerance_et_maillons() -> None:
    premiers = {
        "a": _kill(10.0, "9", "a", "R-60"),
        "b": _kill(9.96, "a", "b"),
        "c": _kill(12.0, "d", "c"),
        "d": _kill(13.0, "7", "d", "Mk-82"),
    }
    # « a » est détruit 0,04 s après le kill de « b » : c'est son épave.
    r, maillons = engine._tireur_d_origine(premiers["b"], premiers)
    assert (r.initiator_object_id, maillons) == ("9", 1)
    # « d » n'est détruit qu'une seconde après : il tirait encore.
    r, maillons = engine._tireur_d_origine(premiers["c"], premiers)
    assert (r.initiator_object_id, maillons) == ("d", 0)
    # Une chaîne de douze épaves : dix maillons au plus.
    chaine = {str(i): _kill(float(i), str(i - 1), str(i)) for i in range(1, 13)}
    r, maillons = engine._tireur_d_origine(chaine["12"], chaine)
    assert maillons == 10 and r.target_object_id == "2"


def test_sans_cible_ni_kill_rien_de_neuf() -> None:
    st = _session([
        _ev(10, 100.0, "shot", "AIM-9M", famille=7),
        _ev(11, 150.0, "kill", "AIM-9M", toid="960", ttype="Su-25"),
    ])[VOL]
    assert st["bursts"] == [{
        "weapon": "AIM-9M", "t": 100.0, "shots": 1, "hits": 0, "target_unit_types": [],
        "target_object_ids": [], "targets": [], "outcomes": []}]
    assert st["kills"] == [{"target_object_id": "960", "target_unit_type": "Su-25",
                            "weapon": "AIM-9M", "t": 150.0}]
