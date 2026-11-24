"""Lot « Le siège d'équipage » (v1.0066) : les règles du cadrage §2, hors ligne,
sur des évènements fabriqués -- aucun journal réel dans l'archive, ni base, ni
réseau. Les dix évènements reproduisent le cas réel du 2 novembre (Mi-24P à
Konya) : le déposant (profil 42) rejoint en copilote l'appareil d'un autre
joueur, `16777987`, après son propre vol, `16777986`.

1. `test_siege_equipage_reste_a_son_pilote` -- le contrôle est au nom du
   déposant, l'appareil de l'autre a un pilote connu plus tôt sous un autre
   nom : c'est un siège d'équipage ; le vol reste à son pilote.
2. `test_controle_player_reste_au_deposant` -- le contrôle est `PLAYER` :
   condition (a) non tenue, comportement d'avant.
3. `test_copilote_monte_au_parking` -- le contrôle précède la mise en route
   de l'autre : la place prise avant tout évènement nommé du pilote est un
   siège d'équipage, quel que soit le `t`.
4. `test_deux_journaux_du_meme_deposant` -- un second journal du même déposant
   (reconnexion), qui ne porte que le contrôle, ne redonne pas le siège.
5. `test_controle_sous_son_propre_nom_reste_au_deposant` -- le contrôle et
   l'évènement nommé portent le même segment de nom : pas un siège.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload

DEPOSANT = 42
SON_VOL = "16777986"
VOL_DE_L_AUTRE = "16777987"
INDICATIF_DE_L_AUTRE = "Dragoon 2-1 | DawN-FyX35"


def _ev(index, t, type, oid, pilote, mission_id=None) -> DebriefEvent:
    return DebriefEvent(
        index=index, t=t, type=type,
        initiator_object_id=oid, initiator_pilot_name=pilote, initiator_unit_type="Mi-24P",
        initiator_mission_id=None, initiator_coalition="2",
        target_object_id=None, target_pilot_name=None, target_unit_type=None,
        weapon=None, event_id=str(index), linked_event_id=None,
        target_slot=None, target_mission_id=mission_id, raw={},
    )


def _journal(nom_du_controle: str, *, t_controle: float = 4738.791) -> list[DebriefEvent]:
    """Les dix évènements du cas réel ; `t_controle` est le `t` des
    évènements 7 et 8 (le contrôle de l'appareil de l'autre)."""
    evs = [
        _ev(1, 176.574, "under control", SON_VOL, "PLAYER", "1"),
        _ev(2, 1494.074, "engine startup", SON_VOL, "Mi-24P"),
        _ev(3, 1497.82, "engine startup", VOL_DE_L_AUTRE, INDICATIF_DE_L_AUTRE),
        _ev(4, 2149.389, "takeoff", VOL_DE_L_AUTRE, INDICATIF_DE_L_AUTRE),
        _ev(5, 4682.514, "land", SON_VOL, "Mi-24P"),
        _ev(6, 4731.395, "relinquished", SON_VOL, "PLAYER", "1"),
        _ev(7, t_controle, "under control", VOL_DE_L_AUTRE, nom_du_controle, "2"),
        _ev(8, t_controle, "under control", VOL_DE_L_AUTRE, nom_du_controle, "2"),
        _ev(9, 4937.955, "takeoff", VOL_DE_L_AUTRE, INDICATIF_DE_L_AUTRE),
        _ev(10, 5596.072, "land", VOL_DE_L_AUTRE, INDICATIF_DE_L_AUTRE),
    ]
    return evs


def _rejouer(monkeypatch, *journaux: list[DebriefEvent]):
    """`_resolve_identities` (db=None, profil non apparié) puis `_build_flights`
    (sans ACMI) : les identités et les vols par `object_id`. Chaque journal
    est déposé par le profil 42 (sha « a », « b »…)."""
    async def _aucun_profil(db, callsign):
        return None

    monkeypatch.setattr(engine, "_match_profile_by_callsign", _aucun_profil)
    pairs = []
    for sha, events in zip("abcd", journaux):
        upload = DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log",
                               depositor_profile_id=DEPOSANT)
        pairs.append((upload, DebriefLogData(header=DebriefHeader(), events=events, graveyard=[])))
    object_types = engine._collect_object_types(pairs)
    identites = asyncio.run(engine._resolve_identities(None, pairs, object_types))
    vols = engine._build_flights(
        acmi_data=None, debrief_pairs=pairs, object_types=object_types, identities=identites
    )
    return identites, {f.object_id: f for f in vols}


def test_siege_equipage_reste_a_son_pilote(monkeypatch) -> None:
    identites, vols = _rejouer(monkeypatch, _journal("MistyKestrel42"))

    son = identites[SON_VOL]
    assert (son.profile_id, son.callsign, son.source) == (DEPOSANT, None, "under_control")
    autre = identites[VOL_DE_L_AUTRE]
    assert (autre.profile_id, autre.callsign, autre.source) == (
        None, INDICATIF_DE_L_AUTRE, "replication"
    )
    # Un seul vol porte le profil du déposant : le sien.
    assert [oid for oid, f in vols.items() if f.pilote_profile_id == DEPOSANT] == [SON_VOL]
    assert vols[VOL_DE_L_AUTRE].pilot_callsign == INDICATIF_DE_L_AUTRE


def test_controle_player_reste_au_deposant(monkeypatch) -> None:
    identites, vols = _rejouer(monkeypatch, _journal("PLAYER"))
    autre = identites[VOL_DE_L_AUTRE]
    assert (autre.profile_id, autre.source) == (DEPOSANT, "under_control")
    # Comportement d'avant : l'indicatif de l'autre se propage à la vie du déposant.
    assert identites[SON_VOL].callsign == INDICATIF_DE_L_AUTRE
    assert vols[VOL_DE_L_AUTRE].pilote_profile_id == DEPOSANT


def test_copilote_monte_au_parking(monkeypatch) -> None:
    # Les évènements 7 et 8 à t = 1400,0 : avant la mise en route de l'autre
    # (t = 1497,82). Le siège est le même.
    identites, vols = _rejouer(monkeypatch, _journal("MistyKestrel42", t_controle=1400.0))
    autre = identites[VOL_DE_L_AUTRE]
    assert (autre.profile_id, autre.callsign, autre.source) == (
        None, INDICATIF_DE_L_AUTRE, "replication"
    )
    assert [oid for oid, f in vols.items() if f.pilote_profile_id == DEPOSANT] == [SON_VOL]


def test_deux_journaux_du_meme_deposant(monkeypatch) -> None:
    # Le journal « b » (reconnexion) ne porte que le contrôle : seul, il ne
    # reconnaît aucun siège ; ceux du journal « a » valent pour tout le déposant.
    seul = _ev(1, 4800.0, "under control", VOL_DE_L_AUTRE, "MistyKestrel42", "2")
    identites, vols = _rejouer(monkeypatch, _journal("MistyKestrel42"), [seul])
    autre = identites[VOL_DE_L_AUTRE]
    assert (autre.profile_id, autre.source) == (None, "replication")
    assert [oid for oid, f in vols.items() if f.pilote_profile_id == DEPOSANT] == [SON_VOL]


def test_controle_sous_son_propre_nom_reste_au_deposant(monkeypatch) -> None:
    journal = [
        _ev(1, 100.0, "under control", VOL_DE_L_AUTRE, "MistyKestrel42", "2"),
        _ev(2, 200.0, "takeoff", VOL_DE_L_AUTRE, "CHARLIE 1 | MistyKestrel42"),
    ]
    identites, vols = _rejouer(monkeypatch, journal)
    autre = identites[VOL_DE_L_AUTRE]
    assert (autre.profile_id, autre.source) == (DEPOSANT, "under_control")
    assert vols[VOL_DE_L_AUTRE].pilote_profile_id == DEPOSANT
