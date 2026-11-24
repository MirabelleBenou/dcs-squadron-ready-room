"""Lot « Les tuiles gardées lisibles » (`v1.0065`) -- une tuile gardée par le
miroir (`TILES_CACHE_DIR`) est écrite avec les droits 0644, pour que le serveur
public des tuiles de la VM (nginx, `/tuiles/`, R369) puisse la lire.

Deux tests : une tuile venue d'Olympus, une tuile remplacée à la revalidation.
Même patron que `tests/test_tuiles_dcs.py` : le `TestClient` de FastAPI sur
`app.main.app`, la garde remplacée par `dependency_overrides[get_current_user_optional]`
(vidé après chaque test), `TILES_DIR` et `TILES_CACHE_DIR` sur des `tmp_path`,
Olympus remplacé par un `httpx.MockTransport` posé sur `tuiles_dcs._CLIENT`.
`ABSENTES` et `ESSAIS` sont vidées avant et après chaque test. La fixture pose
`os.umask(0o077)` pendant le test : seul un changement de droits explicite donne
0644. Aucun accès réseau, ni base.
"""
from __future__ import annotations

import os
import stat
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import pytest

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : il
# fausserait la ligne de `pytest` (« 1 warning »). On n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

from app import tuiles_dcs
from app.auth import get_current_user_optional
from app.config import settings
from app.main import app

_MEMBRE = lambda: {"id": "1", "name": "Test", "roles": [], "lang": "fr"}  # noqa: E731

_PNG = b"\x89PNG\r\n\x1a\n"
_URL = "/outils/tuiles/dcs/alt-caucasus/8/157/94.png"
_JOUR_S = 24 * 3600


class _Olympus:
    """Un Olympus simulé : compte ses appels et répond ce qu'on lui a posé
    (`reponse` : une `httpx.Response`, ou une exception à lever)."""

    def __init__(self, reponse=None):
        self.reponse = reponse
        self.appels: list[httpx.Request] = []

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.appels.append(requete)
        if isinstance(self.reponse, Exception):
            raise self.reponse
        return self.reponse


@pytest.fixture(autouse=True)
def miroir(tmp_path, monkeypatch):
    """`TILES_DIR` et `TILES_CACHE_DIR` sur des dossiers temporaires, les tables
    `ABSENTES` et `ESSAIS` vidées, Olympus hors réseau, le masque du processus à
    0o077 (remis après le test)."""
    disque = tmp_path / "tiles"
    gardees = tmp_path / "tiles-cache"
    disque.mkdir()
    gardees.mkdir()
    monkeypatch.setattr(settings, "TILES_DIR", str(disque))
    monkeypatch.setattr(settings, "TILES_CACHE_DIR", str(gardees))
    tuiles_dcs.ABSENTES.clear()
    tuiles_dcs.ESSAIS.clear()
    monkeypatch.setattr(tuiles_dcs, "_AVERTI", False)
    faux = _Olympus(AssertionError("appel à Olympus imprévu"))
    monkeypatch.setattr(
        tuiles_dcs, "_CLIENT", httpx.AsyncClient(transport=httpx.MockTransport(faux))
    )
    ancien_masque = os.umask(0o077)
    yield faux
    os.umask(ancien_masque)
    app.dependency_overrides.clear()
    tuiles_dcs.ABSENTES.clear()
    tuiles_dcs.ESSAIS.clear()


def _brancher_olympus(monkeypatch, reponse) -> _Olympus:
    faux = _Olympus(reponse)
    monkeypatch.setattr(
        tuiles_dcs, "_CLIENT", httpx.AsyncClient(transport=httpx.MockTransport(faux))
    )
    return faux


def _client() -> TestClient:
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    return TestClient(app, follow_redirects=False)


def _gardee() -> Path:
    return Path(settings.TILES_CACHE_DIR) / "alt-caucasus" / "8" / "157" / "94.png"


def test_tuile_venue_d_olympus_est_gardee_en_0644(monkeypatch):
    neuve = _PNG + b"olympus"
    olympus = _brancher_olympus(monkeypatch, httpx.Response(200, content=neuve))
    r = _client().get(_URL)
    assert r.status_code == 200
    assert r.headers["x-tuile"] == "olympus"
    assert len(olympus.appels) == 1
    fichier = _gardee()
    assert fichier.read_bytes() == neuve
    assert stat.S_IMODE(fichier.stat().st_mode) == 0o644
    assert [p.name for p in fichier.parent.iterdir()] == ["94.png"]


def test_tuile_remplacee_a_la_revalidation_est_en_0644(monkeypatch):
    fichier = _gardee()
    fichier.parent.mkdir(parents=True)
    fichier.write_bytes(_PNG + b"ancienne")
    fichier.chmod(0o600)
    date = time.time() - 31 * _JOUR_S
    os.utime(fichier, (date, date))
    neuve = _PNG + b"nouvelle"
    olympus = _brancher_olympus(monkeypatch, httpx.Response(200, content=neuve))
    r = _client().get(_URL)
    assert r.status_code == 200
    assert r.headers["x-tuile"] == "olympus"
    assert len(olympus.appels) == 1
    assert fichier.read_bytes() == neuve
    assert stat.S_IMODE(fichier.stat().st_mode) == 0o644
    assert [p.name for p in fichier.parent.iterdir()] == ["94.png"]
