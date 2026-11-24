"""Lot « La série juste » (v1.0104, ARC-15, ARC-19) : les trois fonctions pures de `app/events.py` qui décident
ce qu'un changement de série efface et si deux éditeurs se sont croisés. Sans base, sans réseau."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.events import _changement_de_serie, _dates_retirees, _meme_version, _premiere_date_touchee


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def _regle(weekdays=(1, 3), interval=1, end=None):
    return {"freq": "weekly", "interval": interval, "weekdays": list(weekdays), "end": end}


def test_changement_de_serie():
    debut = _utc(2026, 11, 24, 20, 0)
    serie = (debut, _regle())
    # l'heure seule (même jour à Paris) : rien
    assert _changement_de_serie(serie, (_utc(2026, 11, 24, 20, 30), _regle())) == "rien"
    # le titre, le type… ne passent pas par ce couple : mêmes valeurs, rien
    assert _changement_de_serie(serie, (debut, _regle())) == "rien"
    # la date de début : tout
    assert _changement_de_serie(serie, (_utc(2026, 11, 25, 20, 0), _regle())) == "tout"
    # les jours : tout (l'ordre des jours n'est pas un changement)
    assert _changement_de_serie(serie, (debut, _regle(weekdays=(1,)))) == "tout"
    assert _changement_de_serie(serie, (debut, _regle(weekdays=(3, 1)))) == "rien"
    # l'intervalle : tout
    assert _changement_de_serie(serie, (debut, _regle(interval=2))) == "tout"
    # la récurrence ajoutée ou retirée : tout
    assert _changement_de_serie((debut, None), (debut, _regle())) == "tout"
    assert _changement_de_serie(serie, (debut, None)) == "tout"
    # la fin seule : fin
    jusque = {"type": "until", "until": "2026-12-15"}
    assert _changement_de_serie(serie, (debut, _regle(end=jusque))) == "fin"
    assert _changement_de_serie((debut, _regle(end=jusque)), (debut, _regle(end={"type": "count", "count": 4}))) == "fin"
    assert _changement_de_serie((debut, _regle(end=jusque)), (debut, _regle())) == "fin"
    assert _changement_de_serie((debut, _regle(end=jusque)), (debut, _regle(end=dict(jusque)))) == "rien"
    # un évènement unique : l'heure seule, rien ; le jour, tout
    assert _changement_de_serie((debut, None), (_utc(2026, 11, 24, 21, 0), None)) == "rien"
    assert _changement_de_serie((debut, None), (_utc(2026, 11, 25, 20, 0), None)) == "tout"
    # le 28 mars 2026 à 23 h 30 UTC et le 29 à 8 h UTC sont le même jour à Paris (le 29) : pas « tout » pour la date
    assert _changement_de_serie((_utc(2026, 3, 28, 23, 30), None), (_utc(2026, 3, 29, 8, 0), None)) == "rien"
    # … alors que le 28 à 22 h 30 UTC (le 28 à Paris) et le 28 à 23 h 30 UTC (le 29 à Paris) sont deux jours
    assert _changement_de_serie((_utc(2026, 3, 28, 22, 30), None), (_utc(2026, 3, 28, 23, 30), None)) == "tout"
    # « à venir » au jour près de l'heure : une série de 21 h à Paris (20 h UTC en hiver)
    debut_21h = _utc(2026, 11, 24, 20, 0)
    assert _premiere_date_touchee(_utc(2026, 11, 24, 19, 0), debut_21h) == date(2026, 11, 24)   # 20 h à Paris : aujourd'hui
    assert _premiere_date_touchee(_utc(2026, 11, 24, 22, 0), debut_21h) == date(2026, 11, 25)   # 23 h à Paris : demain
    assert _premiere_date_touchee(_utc(2026, 11, 24, 23, 30), debut_21h) == date(2026, 11, 25)  # 0 h 30 le 25 à Paris : aujourd'hui (le 25)


def test_dates_retirees():
    dates = {date(2026, 3, 3), date(2026, 3, 10), date(2026, 3, 11), date(2026, 3, 17), date(2026, 3, 24), date(2026, 3, 31)}

    def serie(fin):
        return SimpleNamespace(start_at=_utc(2026, 3, 3, 20, 0), recurrence=_regle(weekdays=(1,), end=fin))

    # fin avancée au 17 : les mardis après le 17 sont retirés, ainsi que le mercredi 11 (jamais une occurrence)
    retirees = _dates_retirees(serie({"type": "until", "until": "2026-03-17"}), dates)
    assert retirees == {date(2026, 3, 11), date(2026, 3, 24), date(2026, 3, 31)}
    # sans fin : seul le mercredi n'est pas une occurrence
    assert _dates_retirees(serie(None), dates) == {date(2026, 3, 11)}
    # `count` réduit à 2 (les 3 et 10) : les mardis 17, 24 et 31 sont retirés de même
    retirees = _dates_retirees(serie({"type": "count", "count": 2}), dates)
    assert retirees == {date(2026, 3, 11), date(2026, 3, 17), date(2026, 3, 24), date(2026, 3, 31)}
    assert _dates_retirees(serie(None), set()) == set()


def test_meme_version():
    maj = datetime(2026, 11, 21, 15, 0, 0, 123456, tzinfo=timezone.utc)
    assert _meme_version(maj, "2026-11-21T15:00:00.123456Z") is True
    assert _meme_version(maj, "2026-11-21T15:00:00.123456+00:00") is True
    assert _meme_version(maj, "2026-11-21T16:00:00.123456+01:00") is True   # le même instant, un autre fuseau
    assert _meme_version(maj, "2026-11-21T15:00:00.123457Z") is False       # un autre instant
    assert _meme_version(maj, "2026-11-21T15:00:01.123456Z") is False
    # un `+` brut décodé par l'adresse arrive en espace : `…T15:00:00 00:00` = `…T15:00:00+00:00`
    assert _meme_version(maj, "2026-11-21T15:00:00.123456 00:00") is True
    assert _meme_version(maj, "2026-11-21T15:00:00.123456 00:00") == _meme_version(maj, "2026-11-21T15:00:00.123456+00:00")
    assert _meme_version(maj, "pas une date") is False
    assert _meme_version(maj, "") is False
