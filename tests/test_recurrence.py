"""Lot « La série juste » (v1.0104, ARC-20) : le moteur de récurrence tel qu'il est — changements d'heure,
`count`, `interval`/`until`, exceptions, fenêtre. Sans base, sans réseau ; un évènement est un simple objet
porteur de `start_at` et `recurrence`."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest

from app.recurrence import (
    MAX_WINDOW_DAYS,
    RecurrenceWindowTooLarge,
    check_window,
    expand,
    raw_occurrence_dates,
)


def _serie(debut_utc, regle):
    return SimpleNamespace(
        id="e1", type="mission", game_label="DCS", map_name=None, title="Vol", description="",
        duration_min=90, created_by=1, start_at=debut_utc, recurrence=regle,
    )


def _regle(weekdays=(1,), interval=1, end=None):
    return {"freq": "weekly", "interval": interval, "weekdays": list(weekdays), "end": end}


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_bascule_de_printemps():
    # 21 h à Paris : le mardi 24 mars 2026 (UTC+1) = 20 h UTC ; le 31 (UTC+2, le changement d'heure est le 29) = 19 h UTC.
    serie = _serie(_utc(2026, 3, 24, 20, 0), _regle())
    occ = expand(serie, {}, date(2026, 3, 24), date(2026, 3, 31))
    assert [o.occ_date for o in occ] == [date(2026, 3, 24), date(2026, 3, 31)]
    assert occ[0].start_at_utc == _utc(2026, 3, 24, 20, 0)
    assert occ[1].start_at_utc == _utc(2026, 3, 31, 19, 0)


def test_bascule_d_automne():
    # Le mardi 20 octobre 2026 (UTC+2) = 19 h UTC ; le 27 (UTC+1, le changement d'heure est le 25) = 20 h UTC.
    serie = _serie(_utc(2026, 10, 20, 19, 0), _regle())
    occ = expand(serie, {}, date(2026, 10, 20), date(2026, 10, 27))
    assert [o.occ_date for o in occ] == [date(2026, 10, 20), date(2026, 10, 27)]
    assert occ[0].start_at_utc == _utc(2026, 10, 20, 19, 0)
    assert occ[1].start_at_utc == _utc(2026, 10, 27, 20, 0)


def test_count_depuis_l_ancre():
    # Trois mardis depuis l'ancre (3, 10, 17 mars) ; une fenêtre ouverte après la deuxième date n'en voit qu'une.
    serie = _serie(_utc(2026, 3, 3, 20, 0), _regle(end={"type": "count", "count": 3}))
    assert raw_occurrence_dates(serie, date(2026, 3, 1), date(2026, 4, 30)) == [
        date(2026, 3, 3), date(2026, 3, 10), date(2026, 3, 17)]
    assert raw_occurrence_dates(serie, date(2026, 3, 11), date(2026, 4, 30)) == [date(2026, 3, 17)]


def test_interval_et_until():
    # Un mardi sur deux depuis le 3 mars ; `until` compris (le 31 est le troisième).
    serie = _serie(_utc(2026, 3, 3, 20, 0), _regle(interval=2, end={"type": "until", "until": "2026-03-31"}))
    assert raw_occurrence_dates(serie, date(2026, 3, 1), date(2026, 4, 30)) == [
        date(2026, 3, 3), date(2026, 3, 17), date(2026, 3, 31)]
    avant = _serie(_utc(2026, 3, 3, 20, 0), _regle(interval=2, end={"type": "until", "until": "2026-03-30"}))
    assert raw_occurrence_dates(avant, date(2026, 3, 1), date(2026, 4, 30)) == [date(2026, 3, 3), date(2026, 3, 17)]


def test_exceptions():
    serie = _serie(_utc(2026, 3, 3, 20, 0), _regle())
    exceptions = {
        date(2026, 3, 10): SimpleNamespace(status="cancelled", patch=None),
        date(2026, 3, 17): SimpleNamespace(status="modified", patch={"title": "Autre", "duration_min": 45}),
    }
    occ = expand(serie, exceptions, date(2026, 3, 3), date(2026, 3, 24))
    assert [o.occ_date for o in occ] == [date(2026, 3, 3), date(2026, 3, 17), date(2026, 3, 24)]
    assert [o.is_override for o in occ] == [False, True, False]
    assert (occ[1].title, occ[1].duration_min) == ("Autre", 45)
    assert (occ[0].title, occ[0].duration_min) == ("Vol", 90)


def test_fenetre():
    check_window(date(2026, 3, 1), date(2026, 3, 1))
    check_window(date(2026, 3, 1), date.fromordinal(date(2026, 3, 1).toordinal() + MAX_WINDOW_DAYS))
    with pytest.raises(RecurrenceWindowTooLarge):
        check_window(date(2026, 3, 2), date(2026, 3, 1))
    with pytest.raises(RecurrenceWindowTooLarge):
        check_window(date(2026, 3, 1), date.fromordinal(date(2026, 3, 1).toordinal() + MAX_WINDOW_DAYS + 1))
