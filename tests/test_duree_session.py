"""Lot « Les dettes du moteur » -- la durée de session (hors ligne)."""
import types
from app.debrief import engine


def _journal(temps, mission_time=None):
    evs = [types.SimpleNamespace(t=t) for t in temps]
    return (None, types.SimpleNamespace(events=evs, header=types.SimpleNamespace(mission_time=mission_time)))


def _acmi(d):
    return types.SimpleNamespace(meta=types.SimpleNamespace(duration_s=d))


def test_journaux_seuls():
    assert engine._duree_session(None, [_journal([379, 4000], 4105.0), _journal([412, 4800], 4817.9)]) == 4439


def test_acmi_plus_long():
    assert engine._duree_session(_acmi(3387), [_journal([0, 3262], 3262.5)]) == 3387


def test_aucune_source():
    assert engine._duree_session(None, []) is None
