"""Lot « Les suites servies par la Ready Room » (`v1.0047`) -- Mission Plan et
Mission Tools servis par l'application, derrière la règle d'accès de `/`.

Huit tests, un par règle du cadrage (§5). Le client est le `TestClient` de
FastAPI sur `app.main.app` : la garde se remplace par
`dependency_overrides[get_current_user_optional]` (vidé après chaque test),
`SUITES_DIR` pointe un `tmp_path` par `monkeypatch` sur `settings`. Ni base, ni
réseau : le lifespan ne tourne pas (le client n'est pas un gestionnaire de
contexte) et la garde remplacée ne touche pas la session de base.
"""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : il
# fausserait la ligne de `pytest` (« 1 warning »). On n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

from app.auth import get_current_user_optional
from app.config import settings
from app.main import app

# La garde remplacée : un membre connecté, ou personne.
_MEMBRE = lambda: {"id": "1", "name": "Test", "roles": [], "lang": "fr"}  # noqa: E731
_PERSONNE = lambda: None  # noqa: E731

_PLAN = ("mission-plan", "dcs_mission_plan.html", "https://mirabellebenou.github.io/dcs-mission-plan/")
_TOOLS = ("mission-tools", "dcs_mission_tools.html", "https://mirabellebenou.github.io/dcs-mission-tools/")
_CONTENU = "<!doctype html><title>Suite é — ça marche</title>".encode("utf-8")


def test_sans_session_retour_accueil(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUITES_DIR", str(tmp_path))
    for _, fichier, _ in (_PLAN, _TOOLS):
        (tmp_path / fichier).write_bytes(_CONTENU)
    app.dependency_overrides[get_current_user_optional] = _PERSONNE
    try:
        client = TestClient(app, follow_redirects=False)
        for suite, _, _ in (_PLAN, _TOOLS):
            r = client.get(f"/outils/{suite}/")
            assert r.status_code == 307
            assert r.headers["location"] == "/"
    finally:
        app.dependency_overrides.clear()


def test_fichier_servi(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUITES_DIR", str(tmp_path))
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    try:
        client = TestClient(app, follow_redirects=False)
        for suite, fichier, _ in (_PLAN, _TOOLS):
            contenu = _CONTENU + suite.encode("ascii")
            (tmp_path / fichier).write_bytes(contenu)
            r = client.get(f"/outils/{suite}/")
            assert r.status_code == 200
            assert r.content == contenu
            assert r.headers["content-type"] == "text/html; charset=utf-8"
            assert r.headers["cache-control"] == "private, no-cache"
            etag = r.headers["etag"]
            assert etag.startswith('"') and etag.endswith('"') and len(etag) > 2
            assert "last-modified" not in r.headers
    finally:
        app.dependency_overrides.clear()


def test_etag_304(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUITES_DIR", str(tmp_path))
    (tmp_path / _PLAN[1]).write_bytes(_CONTENU)
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    try:
        client = TestClient(app, follow_redirects=False)
        etag = client.get("/outils/mission-plan/").headers["etag"]
        # Seul, puis dans une liste séparée par des virgules.
        for valeur in (etag, f'"autre", {etag}'):
            r = client.get("/outils/mission-plan/", headers={"If-None-Match": valeur})
            assert r.status_code == 304
            assert r.content == b""
            assert r.headers["etag"] == etag
            assert r.headers["cache-control"] == "private, no-cache"
    finally:
        app.dependency_overrides.clear()


def test_retour_arriere_contenu_plus_ancien(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUITES_DIR", str(tmp_path))
    fichier = tmp_path / _PLAN[1]
    fichier.write_bytes(_CONTENU)
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    try:
        client = TestClient(app, follow_redirects=False)
        ancien = client.get("/outils/mission-plan/").headers["etag"]
        # Le retour arrière : un autre contenu, à la date reculée.
        autre = "<!doctype html><title>Version précédente</title>".encode("utf-8")
        fichier.write_bytes(autre)
        os.utime(fichier, (1_000_000_000, 1_000_000_000))
        r = client.get(
            "/outils/mission-plan/",
            headers={
                "If-None-Match": ancien,
                "If-Modified-Since": "Fri, 16 Oct 2026 12:00:00 GMT",
            },
        )
        assert r.status_code == 200
        assert r.content == autre
        assert r.headers["etag"] != ancien
    finally:
        app.dependency_overrides.clear()


def test_absent_vers_github(tmp_path, monkeypatch):
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    try:
        client = TestClient(app, follow_redirects=False)
        # Dossier présent, mais vide, puis dossier inexistant.
        for dossier in (tmp_path, tmp_path / "inexistant"):
            monkeypatch.setattr(settings, "SUITES_DIR", str(dossier))
            for suite, _, github in (_PLAN, _TOOLS):
                r = client.get(f"/outils/{suite}/")
                assert r.status_code == 307
                assert r.headers["location"] == github
    finally:
        app.dependency_overrides.clear()


def test_sans_barre_finale(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUITES_DIR", str(tmp_path))
    # Sans session : la redirection ne lit pas la session.
    app.dependency_overrides[get_current_user_optional] = _PERSONNE
    try:
        client = TestClient(app, follow_redirects=False)
        for suite, _, _ in (_PLAN, _TOOLS):
            r = client.get(f"/outils/{suite}")
            assert r.status_code == 307
            assert r.headers["location"] == f"/outils/{suite}/"
    finally:
        app.dependency_overrides.clear()


def test_aucun_autre_fichier(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUITES_DIR", str(tmp_path))
    for nom in ("dcs_mission_plan.html", "dcs_mission_plan.prec.html", "autre.html"):
        (tmp_path / nom).write_bytes(_CONTENU)
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    try:
        client = TestClient(app, follow_redirects=False)
        for url in (
            "/outils/mission-plan/dcs_mission_plan.prec.html",
            "/outils/mission-plan/dcs_mission_plan.html",
            "/outils/mission-plan/autre.html",
            "/outils/",
            "/outils/dcs_mission_plan.prec.html",
            "/outils/mission-plan/..%2Fautre.html",
        ):
            assert client.get(url).status_code == 404, url
    finally:
        app.dependency_overrides.clear()


def test_tuiles():
    html = (Path(__file__).resolve().parent.parent / "app" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    assert "github.io" not in html
    for suite in ("mission-plan", "mission-tools"):
        assert (
            f'<a class="external-tile" href="/outils/{suite}/" target="_blank" rel="noopener noreferrer">'
            in html
        )
