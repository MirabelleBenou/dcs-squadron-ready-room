"""Lot « La correction à la main superflue » (v1.0067, R1/R3) : dans
`_apply_manual_overrides`, un override `manuel` qui désigne le MÊME profil
que le moteur (vol calculé en `nomme`) est supersédé -- le vol garde tout ce
que le moteur a calculé. Un override vers un autre profil, un override face
à un vol que le moteur ne nomme pas, et un détachement tiennent. Un
invariant déterministe, hors ligne : une fausse session asynchrone (ni
PostgreSQL, ni réseau).
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine

D = "Dragoon 2-1 | DawN-FyX35"


class _FausseBase:
    """`execute(...)` rend un objet dont `.scalars().all()` donne les lignes."""

    def __init__(self, lignes) -> None:
        self.lignes = lignes

    async def execute(self, *_args, **_kwargs):
        lignes = self.lignes
        return SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: lignes))


def _ligne(object_id, source, profil, indicatif, etat):
    return SimpleNamespace(
        object_id=object_id,
        acmi_track_id=None,
        identity_source=source,
        pilote_profile_id=profil,
        pilot_callsign=indicatif,
        identity_state=etat,
    )


def _vol(object_id, profil, indicatif, etat, source):
    return engine.ComputedFlight(
        object_id=object_id,
        acmi_track_id=None,
        aircraft_type="Mi-24P",
        coalition="2",
        pilote_profile_id=profil,
        pilot_callsign=indicatif,
        identity_state=etat,
        identity_source=source,
        t_start=None,
        t_end=None,
        slot_mission=None,
        mission_id_dcs=None,
    )


def _appliquer(ligne, vol):
    base = _FausseBase([ligne])
    asyncio.run(engine._apply_manual_overrides(base, uuid.uuid4(), [vol]))
    return (vol.pilote_profile_id, vol.pilot_callsign, vol.identity_state, vol.identity_source)


def test_meme_pilote_moteur_sans_indicatif():
    ligne = _ligne("16777986", "manuel", 42, D, "nomme")
    vol = _vol("16777986", 42, None, "nomme", "under_control")
    assert _appliquer(ligne, vol) == (42, None, "nomme", "under_control")


def test_meme_pilote_par_nom_retenu():
    ligne = _ligne("16777987", "manuel", 42, D, "nomme")
    vol = _vol("16777987", 42, D, "nomme", "alias")
    assert _appliquer(ligne, vol) == (42, D, "nomme", "alias")


def test_autre_pilote_la_correction_tient():
    ligne = _ligne("16777987", "manuel", 7, D, "nomme")
    vol = _vol("16777987", 42, D, "nomme", "alias")
    assert _appliquer(ligne, vol) == (7, D, "nomme", "manuel")


def test_moteur_sans_profil_la_correction_tient():
    ligne = _ligne("16777987", "manuel", 42, D, "nomme")
    vol = _vol("16777987", None, D, "rattachable", "replication")
    assert _appliquer(ligne, vol) == (42, D, "nomme", "manuel")


def test_detachement_tient():
    ligne = _ligne("16777987", "detache", None, D, "anonyme")
    vol = _vol("16777987", 42, D, "nomme", "alias")
    assert _appliquer(ligne, vol) == (None, D, "anonyme", "detache")
