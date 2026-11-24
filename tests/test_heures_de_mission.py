"""Lot « Les heures comptées par mission » (v1.0069) -- `_heures_de_mission` :
par session, la réunion des intervalles des vols (le temps où au moins un
pilote est en l'air), de jour et de nuit. Pure : testée hors ligne.

1. `test_vols_ensemble` -- quatre vols simultanés comptent une fois.
2. `test_vols_decales_et_sessions` -- la réunion de vols qui se chevauchent,
   puis la somme des sessions.
3. `test_nuit` -- la nuit est la réunion des seuls vols de nuit (période
   corrigée comprise).
4. `test_bords` -- aucun vol, début absent, intervalle inversé.
"""
from types import SimpleNamespace

from app.debrief.api import _heures_de_mission


def _vol(session, debut, fin, **kw):
    return SimpleNamespace(session_id=session, t_start=debut, t_end=fin, **kw)


def test_vols_ensemble():
    vols = [_vol("s1", 0, 7200) for _ in range(4)]
    assert _heures_de_mission(vols) == (7200.0, 0.0)


def test_vols_decales_et_sessions():
    vols = [
        _vol("s1", 3600, 10800), _vol("s1", 7200, 14400),
        _vol("s2", 0, 1800), _vol("s2", 3600, 5400),
    ]
    assert _heures_de_mission(vols) == (14400.0, 0.0)


def test_nuit():
    vols = [
        _vol("s1", 0, 3600, periode="nuit"),
        _vol("s1", 1800, 5400, periode="jour"),
        _vol("s2", 0, 1800, periode="jour", periode_corrigee="nuit"),
    ]
    assert _heures_de_mission(vols) == (7200.0, 5400.0)


def test_bords():
    assert _heures_de_mission([]) == (0.0, 0.0)
    assert _heures_de_mission([_vol("s1", None, 3600)]) == (3600.0, 0.0)
    assert _heures_de_mission([_vol("s1", 3600, 1800)]) == (0.0, 0.0)
