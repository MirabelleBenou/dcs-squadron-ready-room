"""Lot « Les finitions de l'édition » (v1.0103) : schémas, fin de série,
carte d'une occurrence, borne basse des fenêtres. Sans base, sans réseau."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.events import (
    _check_recurrence_end,
    _occurrence_game_map,
    _window_lower_bound_utc,
)
from app.schemas import EventCreate, EventPatchBody, RecurrenceRule

DEBUT = "2026-11-21T20:30:00+01:00"


def _creer(**kw):
    base = {"type": "jeulibre", "title": "Soirée", "start_at": DEBUT}
    base.update(kw)
    return EventCreate(**base)


def _patch(**kw):
    return EventPatchBody(**kw)


def _refuse(fabrique, **kw):
    with pytest.raises(ValidationError):
        fabrique(**kw)


def test_titre_et_longueurs():
    for fabrique in (_creer, _patch):
        _refuse(fabrique, title="   ")
        assert fabrique(title="  Vol du soir  ").title == "Vol du soir"
        assert len(fabrique(title="a" * 120).title) == 120
        _refuse(fabrique, title="a" * 121)
        assert len(fabrique(game_label="g" * 60).game_label) == 60
        _refuse(fabrique, game_label="g" * 61)
        assert len(fabrique(description="d" * 4000).description) == 4000
        _refuse(fabrique, description="d" * 4001)
    assert _patch(title=None).title is None


def test_debut_avec_fuseau():
    _refuse(_creer, start_at="2026-11-21T20:30:00")
    _refuse(_patch, start_at="2026-11-21T20:30:00")
    assert _creer(start_at="2026-11-21T20:30:00Z").start_at.tzinfo is not None
    assert _patch(start_at="2026-11-21T20:30:00+01:00").start_at.tzinfo is not None


def test_bornes_des_nombres():
    assert _creer(duration_min=1440).duration_min == 1440
    assert _patch(duration_min=1440).duration_min == 1440
    _refuse(_creer, duration_min=1441)
    _refuse(_patch, duration_min=1441)
    regle = {"freq": "weekly", "weekdays": [1]}
    assert RecurrenceRule(**regle, interval=52).interval == 52
    _refuse(RecurrenceRule, **regle, interval=53)
    fin = {"type": "count", "count": 500}
    assert RecurrenceRule(**regle, end=fin).end.count == 500
    _refuse(RecurrenceRule, **regle, end={"type": "count", "count": 501})


def test_fin_de_serie():
    debut = datetime(2026, 11, 21, 19, 30, tzinfo=timezone.utc)
    def until(j):
        return {"freq": "weekly", "weekdays": [5],
                "end": {"type": "until", "until": j}}
    _check_recurrence_end(debut, until("2026-11-21"))
    with pytest.raises(HTTPException) as e:
        _check_recurrence_end(debut, until("2026-11-20"))
    assert e.value.status_code == 422
    # 23 h 30 UTC le 28 mars = le 29 à Paris (hiver, UTC+1)
    tard = datetime(2026, 3, 28, 23, 30, tzinfo=timezone.utc)
    with pytest.raises(HTTPException):
        _check_recurrence_end(tard, until("2026-03-28"))
    _check_recurrence_end(tard, until("2026-03-29"))
    _check_recurrence_end(debut, {"freq": "weekly", "weekdays": [5],
                                  "end": {"type": "count", "count": 3}})
    _check_recurrence_end(debut, {"freq": "weekly", "weekdays": [5], "end": None})
    _check_recurrence_end(debut, None)


def test_occurrence_sans_carte():
    serie = SimpleNamespace(type="mission", game_label="DCS", map_name="Syria")
    assert _occurrence_game_map(serie, {"type": "jeulibre"}) == {
        "type": "jeulibre", "map_name": None}
    assert _occurrence_game_map(serie, {"title": "Autre titre"}) == {
        "title": "Autre titre"}
    with pytest.raises(HTTPException) as e:
        _occurrence_game_map(serie, {"game_label": "Autre jeu"})
    assert e.value.status_code == 422


def test_borne_basse():
    assert _window_lower_bound_utc(date(2026, 11, 1)) == datetime(
        2026, 10, 31, tzinfo=timezone.utc)
