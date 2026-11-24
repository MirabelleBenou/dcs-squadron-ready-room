"""Lot « Le miroir des tuiles DCS » (`v1.0059`) -- les tuiles de la couche
« Carte DCS » du Route Planner, servies par `/outils/tuiles/dcs/{cle}/{z}/{x}/{y}.png`
aux seuls membres connectés : le disque, puis les tuiles gardées, puis Olympus.

Huit tests, un par règle du cadrage (R5). Même patron que
`tests/test_wing_config_suite.py` : le `TestClient` de FastAPI sur `app.main.app`,
la garde remplacée par `dependency_overrides[get_current_user_optional]` (vidé
après chaque test), `TILES_DIR` et `TILES_CACHE_DIR` sur des `tmp_path` par
`monkeypatch`. Olympus est remplacé par un `httpx.MockTransport` qui compte ses
appels : aucun accès réseau, ni base.
"""
from __future__ import annotations

import logging
import sys
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

# La garde remplacée : un membre connecté, ou personne.
_MEMBRE = lambda: {"id": "1", "name": "Test", "roles": [], "lang": "fr"}  # noqa: E731
_PERSONNE = lambda: None  # noqa: E731

_PNG = b"\x89PNG\r\n\x1a\n"
_URL = "/outils/tuiles/dcs/alt-GermanyCW/10/526/335.png"
_URL_OLYMPUS = "https://maps.dcsolympus.com/maps/alt-GermanyCW/10/526/335.png"
_DIX_GIO = 10 * 1024**3


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
def olympus(tmp_path, monkeypatch):
    """`TILES_DIR` et `TILES_CACHE_DIR` sur des dossiers temporaires, la table
    des absentes vidée, l'avertissement unique remis à zéro, Olympus hors
    réseau (un `_Olympus` sans réponse : tout appel imprévu fait échouer)."""
    disque = tmp_path / "tiles"
    gardees = tmp_path / "tiles-cache"
    disque.mkdir()
    gardees.mkdir()
    monkeypatch.setattr(settings, "TILES_DIR", str(disque))
    monkeypatch.setattr(settings, "TILES_CACHE_DIR", str(gardees))
    tuiles_dcs.ABSENTES.clear()
    monkeypatch.setattr(tuiles_dcs, "_AVERTI", False)
    faux = _Olympus(AssertionError("appel à Olympus imprévu"))
    monkeypatch.setattr(
        tuiles_dcs, "_CLIENT", httpx.AsyncClient(transport=httpx.MockTransport(faux))
    )
    yield faux
    app.dependency_overrides.clear()
    tuiles_dcs.ABSENTES.clear()


def _brancher_olympus(monkeypatch, reponse) -> _Olympus:
    faux = _Olympus(reponse)
    monkeypatch.setattr(
        tuiles_dcs, "_CLIENT", httpx.AsyncClient(transport=httpx.MockTransport(faux))
    )
    return faux


def _client(membre=True) -> TestClient:
    app.dependency_overrides[get_current_user_optional] = _MEMBRE if membre else _PERSONNE
    return TestClient(app, follow_redirects=False)


def _poser(racine: str, octets: bytes, cle="alt-GermanyCW", z=10, x=526, y=335) -> Path:
    fichier = Path(racine) / cle / str(z) / str(x) / f"{y}.png"
    fichier.parent.mkdir(parents=True)
    fichier.write_bytes(octets)
    return fichier


def test_sans_session_401(olympus):
    # Une tuile bien présente sur le disque : sans session, rien ne part.
    _poser(settings.TILES_DIR, _PNG + b"disque")
    r = _client(membre=False).get(_URL)
    assert r.status_code == 401
    assert "location" not in r.headers
    assert "x-tuile" not in r.headers
    assert r.content == b""
    assert olympus.appels == []


def test_invalides_404_sans_rien_lire_ni_demander(olympus):
    client = _client()
    invalides = [
        "/outils/tuiles/dcs/alt-kola/10/526/335.png",          # clé inconnue
        "/outils/tuiles/dcs/alt-germanycw/10/526/335.png",     # mauvaise casse
        "/outils/tuiles/dcs/alt-GermanyCW/19/1/1.png",         # z = 19
        "/outils/tuiles/dcs/alt-GermanyCW/3/8/1.png",          # x = 2^z
        "/outils/tuiles/dcs/alt-GermanyCW/3/1/8.png",          # y = 2^z
        "/outils/tuiles/dcs/alt-GermanyCW/10/526/1a.png",      # y = 1a
        "/outils/tuiles/dcs/alt-GermanyCW/10/+1/335.png",      # x = +1
        "/outils/tuiles/dcs/alt-GermanyCW/18/1/1234567.png",   # y de 7 chiffres
    ]
    for url in invalides:
        r = client.get(url)
        assert r.status_code == 404, url
        assert r.headers["cache-control"] == "no-store", url
        assert "x-tuile" not in r.headers, url
    assert olympus.appels == []


def test_le_disque_sert_a_l_octet(olympus):
    disque = _PNG + b"disque"
    _poser(settings.TILES_DIR, disque)
    # La même tuile, différente, dans les tuiles gardées : elle ne masque pas le disque.
    _poser(settings.TILES_CACHE_DIR, _PNG + b"gardee")
    r = _client().get(_URL)
    assert r.status_code == 200
    assert r.content == disque
    assert r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"] == "private, max-age=604800"
    assert r.headers["x-tuile"] == "disque"
    assert olympus.appels == []


def test_les_tuiles_gardees_servent_quand_le_disque_n_a_pas(olympus):
    gardee = _PNG + b"gardee"
    _poser(settings.TILES_CACHE_DIR, gardee)
    r = _client().get(_URL)
    assert r.status_code == 200
    assert r.content == gardee
    assert r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"] == "private, max-age=604800"
    assert r.headers["x-tuile"] == "cache"
    assert olympus.appels == []


def test_olympus_tuile_gardee(monkeypatch):
    octets = _PNG + b"olympus"
    olympus = _brancher_olympus(monkeypatch, httpx.Response(200, content=octets))
    client = _client()
    # Cookie et Authorization du membre : rien de cela ne part chez Olympus.
    r = client.get(_URL, headers={"Cookie": "session=secret", "Authorization": "Bearer secret"})
    assert r.status_code == 200
    assert r.content == octets
    assert r.headers["content-type"] == "image/png"
    assert r.headers["cache-control"] == "private, max-age=604800"
    assert r.headers["x-tuile"] == "olympus"
    assert [str(a.url) for a in olympus.appels] == [_URL_OLYMPUS]
    requete = olympus.appels[0]
    assert "cookie" not in requete.headers and "authorization" not in requete.headers
    assert "ReadyRoom" in requete.headers["user-agent"]
    # Le fichier gardé égale les octets, seul dans son dossier (aucun temporaire).
    gardee = Path(settings.TILES_CACHE_DIR) / "alt-GermanyCW" / "10" / "526" / "335.png"
    assert gardee.read_bytes() == octets
    assert list(gardee.parent.iterdir()) == [gardee]
    # Un second appel vient des tuiles gardées, sans rappeler Olympus.
    r2 = client.get(_URL)
    assert r2.status_code == 200
    assert r2.content == octets
    assert r2.headers["x-tuile"] == "cache"
    assert len(olympus.appels) == 1


def test_olympus_tuile_absente_retenue(monkeypatch):
    olympus = _brancher_olympus(monkeypatch, httpx.Response(404))
    client = _client()
    for _ in range(2):
        r = client.get(_URL)
        assert r.status_code == 404
        assert r.headers["cache-control"] == "private, max-age=86400"
        assert r.headers["x-tuile"] == "absente"
    # Le second appel est répondu par la table des absentes : Olympus n'est pas rappelé.
    assert len(olympus.appels) == 1
    assert list(Path(settings.TILES_CACHE_DIR).rglob("*")) == []


def test_olympus_defaillant_502(monkeypatch):
    cas = {
        "délai dépassé": httpx.ConnectTimeout("délai"),
        "500": httpx.Response(500),
        "200 qui n'est pas un PNG": httpx.Response(200, content=b"<html>pas un PNG</html>"),
        "200 de plus de 2 000 000 octets": httpx.Response(
            200, content=_PNG + b"\0" * (2_000_000 - len(_PNG) + 1)
        ),
        "302": httpx.Response(302, headers={"Location": "https://exemple.invalid/tuile.png"}),
    }
    client = _client()
    for nom, reponse in cas.items():
        olympus = _brancher_olympus(monkeypatch, reponse)
        for essai in (1, 2):
            r = client.get(_URL)
            assert r.status_code == 502, nom
            assert r.headers["cache-control"] == "no-store", nom
            assert "x-tuile" not in r.headers, nom
            # Rien n'est retenu : chaque appel redemande Olympus (sans suivre la redirection).
            assert len(olympus.appels) == essai, nom
        assert list(Path(settings.TILES_CACHE_DIR).rglob("*")) == [], nom
        assert tuiles_dcs.ABSENTES == {}, nom


def test_garde_impossible_la_tuile_est_servie(tmp_path, monkeypatch, caplog):
    octets = _PNG + b"olympus"
    olympus = _brancher_olympus(monkeypatch, httpx.Response(200, content=octets))
    client = _client()
    caplog.set_level(logging.DEBUG, logger="app.tuiles_dcs")
    # `TILES_CACHE_DIR` sur un fichier, pas un dossier : servie quand même.
    fichier = tmp_path / "pas-un-dossier"
    fichier.write_bytes(b"x")
    monkeypatch.setattr(settings, "TILES_CACHE_DIR", str(fichier))
    for _ in range(2):
        r = client.get(_URL)
        assert r.status_code == 200
        assert r.content == octets
        assert r.headers["x-tuile"] == "olympus"
    assert len(olympus.appels) == 2
    assert fichier.read_bytes() == b"x"
    # Au plus un avertissement, sans « Échec » ni « Traceback ».
    messages = [e.getMessage() for e in caplog.records if e.name == "app.tuiles_dcs"]
    assert len(messages) == 1
    assert "Échec" not in messages[0] and "Traceback" not in messages[0]
    # Dossier utilisable, mais place libre simulée sous 10 Gio : servie, rien de gardé.
    dossier = tmp_path / "gardees-pleines"
    dossier.mkdir()
    monkeypatch.setattr(settings, "TILES_CACHE_DIR", str(dossier))
    monkeypatch.setattr(tuiles_dcs, "_octets_libres", lambda _d: _DIX_GIO - 1)
    r = client.get(_URL)
    assert r.status_code == 200
    assert r.content == octets
    assert r.headers["x-tuile"] == "olympus"
    assert list(dossier.rglob("*")) == []
    # Pile 10 Gio libres : la tuile est gardée.
    monkeypatch.setattr(tuiles_dcs, "_octets_libres", lambda _d: _DIX_GIO)
    assert client.get(_URL).status_code == 200
    assert (dossier / "alt-GermanyCW" / "10" / "526" / "335.png").read_bytes() == octets
