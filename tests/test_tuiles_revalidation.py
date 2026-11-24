"""Lot « Le miroir des tuiles DCS se tient à jour » (`v1.0060`) -- une tuile
gardée depuis plus de 30 jours est redemandée à Olympus en requête conditionnelle
(`If-Modified-Since`), les archives extraites (`TILES_DIR`) jamais.

Cinq tests, un par cas du cadrage (R5). Même patron que
`tests/test_tuiles_dcs.py` : le `TestClient` de FastAPI sur `app.main.app`, la
garde remplacée par `dependency_overrides[get_current_user_optional]` (vidé
après chaque test), `TILES_DIR` et `TILES_CACHE_DIR` sur des `tmp_path` par
`monkeypatch`, Olympus remplacé par un `httpx.MockTransport` qui compte et garde
ses requêtes. `ABSENTES` et `ESSAIS` sont vidées avant chaque test. Aucun accès
réseau, ni base.
"""
from __future__ import annotations

import os
import sys
import time
import warnings
from email.utils import formatdate
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
    """Un Olympus simulé : compte et garde ses requêtes, répond ce qu'on lui a
    posé (`reponse` : une `httpx.Response`, ou une exception à lever)."""

    def __init__(self, reponse=None):
        self.reponse = reponse
        self.appels: list[httpx.Request] = []

    def __call__(self, requete: httpx.Request) -> httpx.Response:
        self.appels.append(requete)
        if isinstance(self.reponse, Exception):
            raise self.reponse
        return self.reponse


@pytest.fixture(autouse=True)
def olympus(tmp_path, monkeypatch):
    """`TILES_DIR` et `TILES_CACHE_DIR` sur des dossiers temporaires, les tables
    `ABSENTES` et `ESSAIS` vidées, Olympus hors réseau (un `_Olympus` sans
    réponse : tout appel imprévu fait échouer)."""
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
    yield faux
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


def _poser(racine: str, octets: bytes, jours: float) -> tuple[Path, float]:
    """Pose la tuile témoin sous `racine`, datée d'il y a `jours` jours. Rend le
    fichier et la date posée."""
    fichier = Path(racine) / "alt-caucasus" / "8" / "157" / "94.png"
    fichier.parent.mkdir(parents=True)
    fichier.write_bytes(octets)
    date = time.time() - jours * _JOUR_S
    os.utime(fichier, (date, date))
    return fichier, date


def test_fraiche_aucun_appel(olympus):
    gardee = _PNG + b"gardee"
    _poser(settings.TILES_CACHE_DIR, gardee, 29)
    r = _client().get(_URL)
    assert r.status_code == 200
    assert r.content == gardee
    assert r.headers["x-tuile"] == "cache"
    assert olympus.appels == []


def test_304_la_tuile_gardee_est_gardee_30_jours_de_plus(monkeypatch):
    gardee = _PNG + b"gardee"
    fichier, date = _poser(settings.TILES_CACHE_DIR, gardee, 31)
    olympus = _brancher_olympus(monkeypatch, httpx.Response(304))
    client = _client()
    r = client.get(_URL)
    assert r.status_code == 200
    assert r.content == gardee
    assert r.headers["x-tuile"] == "cache"
    assert len(olympus.appels) == 1
    assert olympus.appels[0].headers["if-modified-since"] == formatdate(date, usegmt=True)
    assert fichier.read_bytes() == gardee
    assert abs(time.time() - fichier.stat().st_mtime) < 60
    # Une seconde demande : la tuile est de nouveau fraîche, Olympus n'est pas rappelé.
    r2 = client.get(_URL)
    assert r2.status_code == 200
    assert r2.content == gardee
    assert r2.headers["x-tuile"] == "cache"
    assert len(olympus.appels) == 1


def test_200_la_nouvelle_tuile_remplace_l_ancienne(monkeypatch):
    fichier, _ = _poser(settings.TILES_CACHE_DIR, _PNG + b"ancienne", 31)
    neuve = _PNG + b"neuve"
    olympus = _brancher_olympus(monkeypatch, httpx.Response(200, content=neuve))
    r = _client().get(_URL)
    assert r.status_code == 200
    assert r.content == neuve
    assert r.headers["x-tuile"] == "olympus"
    assert len(olympus.appels) == 1
    assert "if-modified-since" in olympus.appels[0].headers
    # Le fichier porte les nouveaux octets, seul dans son dossier (aucun temporaire).
    assert fichier.read_bytes() == neuve
    assert list(fichier.parent.iterdir()) == [fichier]


def test_olympus_defaillant_l_ancienne_est_servie(monkeypatch):
    gardee = _PNG + b"gardee"
    cas = {
        "délai dépassé": httpx.ConnectTimeout("délai"),
        "500": httpx.Response(500),
        "404": httpx.Response(404),
        "200 qui n'est pas un PNG": httpx.Response(200, content=b"<html>pas un PNG</html>"),
    }
    client = _client()
    for nom, reponse in cas.items():
        tuiles_dcs.ESSAIS.clear()
        fichier, _ = _poser(settings.TILES_CACHE_DIR, gardee, 31)
        date_posee = fichier.stat().st_mtime
        olympus = _brancher_olympus(monkeypatch, reponse)
        r = client.get(_URL)
        assert r.status_code == 200, nom
        assert r.content == gardee, nom
        assert r.headers["x-tuile"] == "cache", nom
        assert len(olympus.appels) == 1, nom
        # Ni les octets ni la date du fichier ne bougent ; un 404 ne retient rien.
        assert fichier.read_bytes() == gardee, nom
        assert fichier.stat().st_mtime == date_posee, nom
        assert tuiles_dcs.ABSENTES == {}, nom
        # Une seconde demande : l'essai récent évite d'appeler Olympus.
        r2 = client.get(_URL)
        assert r2.status_code == 200, nom
        assert r2.content == gardee, nom
        assert r2.headers["x-tuile"] == "cache", nom
        assert len(olympus.appels) == 1, nom
        # La tuile est reposée à 31 jours pour le cas suivant.
        fichier.unlink()
        fichier.parent.rmdir()


def test_le_disque_n_est_jamais_revalide(olympus):
    disque = _PNG + b"disque"
    _poser(settings.TILES_DIR, disque, 400)
    r = _client().get(_URL)
    assert r.status_code == 200
    assert r.content == disque
    assert r.headers["x-tuile"] == "disque"
    assert olympus.appels == []
