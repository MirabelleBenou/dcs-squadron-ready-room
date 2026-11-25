"""Lot « Discord 429 » : `_bot_request` (`app/discord_rsvp.py`) suit les limites
que Discord annonce, hors ligne -- ni réseau, ni base, ni attente réelle
(`httpx.MockTransport`, horloge du test à la place de `time.monotonic` et
`asyncio.sleep`).

1. `test_429_reessaye_deux_fois` -- trois appels au plus, l'attente annoncée,
   et une durée au-delà de 10 s rendue tout de suite ;
2. `test_limite_annoncee_par_route` -- `X-RateLimit-Remaining: 0` fait attendre
   la route suivante du même salon, pas celle d'un autre salon ;
3. `test_429_global` -- un 429 global retarde toutes les routes.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

import app.discord_rsvp as discord_rsvp

_CLIENT_REEL = httpx.AsyncClient


class _Banc:
    """Horloge du test et réponses jouées, dans l'ordre, par le faux Discord."""

    def __init__(self, monkeypatch):
        self.maintenant = 1000.0
        self.attentes: list[float] = []
        self.appels: list[tuple[str, str]] = []
        self.reponses: list[httpx.Response] = []
        monkeypatch.setattr(discord_rsvp._time, "monotonic", lambda: self.maintenant)
        monkeypatch.setattr(discord_rsvp.asyncio, "sleep", self._dormir)
        transport = httpx.MockTransport(self._repondre)
        monkeypatch.setattr(
            discord_rsvp.httpx, "AsyncClient", lambda **kw: _CLIENT_REEL(transport=transport, **kw)
        )
        self.remettre_a_zero()

    @staticmethod
    def remettre_a_zero():
        discord_rsvp._attente_route.clear()
        discord_rsvp._attente_globale = 0.0

    async def _dormir(self, duree):
        self.attentes.append(duree)
        self.maintenant += duree

    def _repondre(self, requete: httpx.Request) -> httpx.Response:
        self.appels.append((requete.method, requete.url.path))
        return self.reponses.pop(0)

    def jouer(self, *reponses: httpx.Response):
        self.reponses = list(reponses)
        self.appels.clear()
        self.attentes.clear()


def _reponse(statut, entetes=None, corps=None):
    return httpx.Response(statut, headers=entetes or {}, json=corps if corps is not None else {})


def _patch(salon, message="1"):
    return asyncio.run(
        discord_rsvp._bot_request("PATCH", f"/channels/{salon}/messages/{message}", json_body={})
    )


def test_429_reessaye_deux_fois(monkeypatch):
    banc = _Banc(monkeypatch)

    banc.jouer(
        _reponse(429, {"Retry-After": "2"}),
        _reponse(429, corps={"retry_after": 3}),
        _reponse(200),
    )
    assert _patch("A").status_code == 200
    assert len(banc.appels) == 3
    assert banc.attentes == [2.0, 3.0]

    banc.remettre_a_zero()
    banc.jouer(_reponse(429, {"Retry-After": "1"}), _reponse(429, {"Retry-After": "1"}),
               _reponse(429, {"Retry-After": "1"}))
    assert _patch("A").status_code == 429
    assert len(banc.appels) == 3

    banc.remettre_a_zero()
    banc.jouer(_reponse(429, {"Retry-After": "30"}))
    assert _patch("A").status_code == 429
    assert len(banc.appels) == 1
    assert banc.attentes == []


def test_limite_annoncee_par_route(monkeypatch):
    banc = _Banc(monkeypatch)
    assert discord_rsvp._cle_route("PATCH", "/channels/A/messages/123") == "PATCH /channels/A/messages/{m}"

    banc.jouer(
        _reponse(200, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset-After": "1.5"}),
        _reponse(200),
        _reponse(200),
    )
    assert _patch("A", "1").status_code == 200
    assert banc.attentes == []
    assert _patch("B", "1").status_code == 200       # autre salon : aucune attente
    assert banc.attentes == []
    assert _patch("A", "2").status_code == 200       # même salon, autre message
    assert banc.attentes == [1.5]


def test_429_global(monkeypatch):
    banc = _Banc(monkeypatch)
    global_429 = {"retry_after": 2, "global": True}

    # trois 429 globaux sur le salon A : le dernier est rendu, l'instant global
    # est alors à 2 s devant
    banc.jouer(_reponse(429, corps=global_429), _reponse(429, corps=global_429),
               _reponse(429, corps=global_429), _reponse(200))
    assert _patch("A").status_code == 429
    assert banc.attentes == [2.0, 2.0]
    arrivee = banc.maintenant
    assert discord_rsvp._attente_globale == arrivee + 2.0

    # n'importe quelle autre route attend jusqu'à cet instant
    reponse = asyncio.run(discord_rsvp._bot_request("GET", "/users/42"))
    assert reponse.status_code == 200
    assert banc.attentes == [2.0, 2.0, 2.0]
    assert banc.maintenant == arrivee + 2.0
