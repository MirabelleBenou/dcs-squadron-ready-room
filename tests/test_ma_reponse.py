"""Lot « Ma réponse sur la Planche » (`v1.0073`, ARU-20) -- `GET /api/events` porte
la réponse du demandeur (`my_state`).

Deux tests, sans base ni réseau : `_mes_reponses` se joue avec `asyncio.run` et une
fausse session de base dont `execute` est une coroutine qui compte ses appels.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.events import _mes_reponses


def _fausse_base(lignes):
    """Une fausse session : `execute` compte ses appels et rend un objet dont `all()` rend les lignes."""
    appels = []

    async def execute(requete):
        appels.append(requete)
        return SimpleNamespace(all=lambda: list(lignes))

    return SimpleNamespace(execute=execute), appels


def test_invite_sans_requete():
    """Un invité ne répond pas (R431) : `{}`, et la base n'est pas interrogée."""
    db, appels = _fausse_base([])
    rendu = asyncio.run(
        _mes_reponses(db, {"id": "5", "invite": True}, [uuid.uuid4()], date(2026, 11, 1), date(2026, 11, 30))
    )
    assert rendu == {}
    assert appels == []


def test_membre_une_requete_cles_str_date():
    """Un membre : une seule requête, rendue en `{(str(event_id), occ_date): état}`."""
    a, b = uuid.uuid4(), uuid.uuid4()
    d1, d2 = date(2026, 11, 12), date(2026, 11, 13)
    db, appels = _fausse_base([(a, d1, "present"), (b, d2, "maybe")])
    rendu = asyncio.run(
        _mes_reponses(db, {"id": "200000000000000003"}, [a, b], date(2026, 11, 1), date(2026, 11, 30))
    )
    assert rendu == {(str(a), d1): "present", (str(b), d2): "maybe"}
    assert len(appels) == 1
