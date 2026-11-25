"""Lot « La défense de l'App exposée » (`v1.0083`, `rr-socle-defense`, avec
`rr-contenu-mixte-https`) -- quatorze tests, un par règle du cadrage (§3), sans base
ni réseau : le `TestClient` de FastAPI sur `app.main.app` (le lifespan ne tourne pas),
la garde de session remplacée par `dependency_overrides` ou un cookie signé comme
`SessionMiddleware` le signe. Seuls les chemins de refus des déclencheurs machine se
jouent (aucun appel à Discord).
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import mimetypes
import os
import re
import secrets
import subprocess
import sys
import warnings
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : il
# fausserait la ligne de `pytest`. On n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

import itsdangerous
import pytest

from app import api, auth, defense, main
from app.auth import get_current_user_optional
from app.config import settings
from app.main import app

# Rendre un gabarit par `TemplateResponse(nom, contexte)` (la forme de tout le code existant) émet
# l'avertissement de Starlette sur l'ordre des paramètres : il fausserait la ligne de `pytest`.
pytestmark = pytest.mark.filterwarnings(
    "ignore:The `name` is not the first parameter anymore:DeprecationWarning"
)

RACINE = Path(__file__).resolve().parent.parent
_MEMBRE = lambda: {"id": "1", "name": "Test", "roles": [], "lang": "fr"}  # noqa: E731
_PERSONNE = lambda: None  # noqa: E731

_CSP_AVANT = (
    "default-src 'self'; script-src 'self'{scripts}; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://cdn.discordapp.com; font-src 'self'; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self'"
)


def _cookie(session: dict) -> dict:
    """L'en-tête `cookie` d'une session, signée comme `SessionMiddleware` la signe."""
    donnees = base64.b64encode(json.dumps(session).encode("utf-8"))
    signe = itsdangerous.TimestampSigner(str(settings.SESSION_SECRET)).sign(donnees).decode("utf-8")
    return {"cookie": f"session={signe}"}


def _session_membre() -> dict:
    return _cookie({"id": "1", "roles": [], "exp": "2999-01-01T00:00:00+00:00"})


def _session_invite() -> dict:
    return _cookie({"id": "402871516337258497", "invite": True, "roles": [], "exp": "2999-01-01T00:00:00+00:00"})


def _empreintes_du_corps(html: str) -> list[str]:
    """Les empreintes des scripts en ligne d'un corps reçu, recalculées ici, à part de `app.defense`."""
    return [
        "'sha256-" + base64.b64encode(hashlib.sha256(m.encode("utf-8")).digest()).decode("ascii") + "'"
        for m in re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    ]


async def _identite_repli():
    return ("1st EXAW", "/static/assets/img/emblem-default.png", "Example Air Wing")


def test_entetes_communs():
    client = TestClient(app, follow_redirects=False)
    for chemin in ("/api/version", "/static/styles.css", "/docs"):  # une API, un statique, une erreur
        r = client.get(chemin)
        assert r.headers["x-content-type-options"] == "nosniff", chemin
        assert r.headers["x-frame-options"] == "SAMEORIGIN", chemin
        assert r.headers["strict-transport-security"] == "max-age=31536000", chemin
        # Addendum 1 : `Referrer-Policy` ne vaut que sur les pages de l'App.
        assert "referrer-policy" not in r.headers, chemin
    assert client.get("/docs").status_code == 404
    # Au banc, en http://127.0.0.1 : pas de HSTS ; ni sur `localhost`.
    for hote in ("127.0.0.1", "localhost"):
        local = TestClient(app, base_url=f"http://{hote}:8000", follow_redirects=False)
        r = local.get("/api/version")
        assert "strict-transport-security" not in r.headers, hote
        assert r.headers["x-content-type-options"] == "nosniff", hote
    # Sans écraser ce que la route a posé : la page d'un lien garde son `no-referrer`.
    assert client.get("/auth/lien").headers["referrer-policy"] == "no-referrer"

    # Ce que prouve ce bloc : `EnTetesCommuns` ne remplace pas un en-tête déjà posé par la route
    # (ici `X-Frame-Options: DENY`) et complète les autres.
    async def route_qui_pose_son_cadre(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"x-frame-options", b"DENY"), (b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"ok"})

    r = TestClient(defense.EnTetesCommuns(route_qui_pose_son_cadre, version="1")).get("/")
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"


def test_csp_des_pages(monkeypatch):
    monkeypatch.setattr(main, "_wing_login_identity", _identite_repli)
    # T2 : aucun bloc `<script>` des gabarits ne porte de syntaxe Jinja.
    sources = [
        (RACINE / "app" / "static" / "index.html").read_text(encoding="utf-8"),
        (RACINE / "app" / "templates" / "login.html").read_text(encoding="utf-8"),
        (RACINE / "app" / "templates" / "lien.html").read_text(encoding="utf-8"),
    ]
    for source in sources:
        for bloc in re.findall(r"<script>(.*?)</script>", source, re.DOTALL):
            assert "{{" not in bloc and "{%" not in bloc and "{#" not in bloc
    client = TestClient(app, follow_redirects=False)
    pages = []
    app.dependency_overrides[get_current_user_optional] = _PERSONNE
    try:
        pages.append(("/", client.get("/"), 1))  # la page de connexion : un script
        pages.append(("/auth/lien", client.get("/auth/lien"), 1))  # la page d'un lien : un script
        app.dependency_overrides[get_current_user_optional] = _MEMBRE
        pages.append(("/", client.get("/"), 2))  # le shell d'un membre : les deux de `index.html`
    finally:
        app.dependency_overrides.clear()
    for chemin, r, attendu in pages:
        assert r.status_code == 200, chemin
        empreintes = _empreintes_du_corps(r.text)
        assert len(empreintes) == attendu, chemin  # chaque script en ligne, et lui seul
        scripts = "".join(" " + e for e in empreintes)
        assert r.headers["content-security-policy"] == _CSP_AVANT.format(scripts=scripts) + "; upgrade-insecure-requests", chemin
        assert r.headers["referrer-policy"] in ("same-origin", "no-referrer"), chemin
    # Les empreintes du shell se calculent sur le texte servi, après la substitution de la version.
    assert "__ASSET_VERSION__" not in pages[2][1].text
    # La page de refus n'a aucun script en ligne : `script-src 'self'` seul.
    assert auth._EMPREINTES_NOACCESS == []
    assert defense.politique_contenu(auth._EMPREINTES_NOACCESS, False) == _CSP_AVANT.format(scripts="") + "; upgrade-insecure-requests"


def test_csp_absente_ailleurs(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SUITES_DIR", str(tmp_path))
    (tmp_path / "dcs_mission_plan.html").write_bytes("<!doctype html><title>Suite</title>".encode("utf-8"))
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    try:
        client = TestClient(app, follow_redirects=False)
        reponses = {c: client.get(c) for c in ("/outils/mission-plan/", "/manuel/", "/static/app.js", "/api/version")}
    finally:
        app.dependency_overrides.clear()
    assert reponses["/outils/mission-plan/"].status_code == 200
    assert reponses["/manuel/"].status_code == 200
    for chemin, r in reponses.items():
        assert "content-security-policy" not in r.headers, chemin
    # Addendum 1 : les suites chargent des tuiles chez des tiers, le navigateur garde son défaut.
    assert "referrer-policy" not in reponses["/outils/mission-plan/"].headers


def test_csp_sans_upgrade_en_local(monkeypatch):
    monkeypatch.setattr(main, "_wing_login_identity", _identite_repli)
    client = TestClient(app, base_url="http://127.0.0.1:8000", follow_redirects=False)
    r = client.get("/")
    assert r.status_code == 200
    assert r.headers["content-security-policy"].endswith("frame-ancestors 'self'")
    assert "upgrade-insecure-requests" not in r.headers["content-security-policy"]


def test_referrer_du_lien():
    r = TestClient(app, follow_redirects=False).get("/auth/lien")
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_docs_fermes():
    client = TestClient(app, follow_redirects=False)
    for chemin in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(chemin).status_code == 404, chemin


def test_sans_redirection_de_barre():
    client = TestClient(app, follow_redirects=False)
    for chemin in ("/api/events/", "/static"):
        r = client.get(chemin)
        assert r.status_code == 404, chemin
        assert "location" not in r.headers, chemin


def test_jeton_en_entete(monkeypatch):
    jeton_ok = secrets.token_urlsafe(24)
    # La fonction pure : l'en-tête juste, l'en-tête faux, l'en-tête absent, `attendu` vide.
    assert defense.jeton_valide(jeton_ok, jeton_ok) is True
    assert defense.jeton_valide(jeton_ok, "faux") is False
    assert defense.jeton_valide(jeton_ok, None) is False  # en-tête seul : jamais l'adresse
    assert defense.jeton_valide("", "") is False
    assert defense.jeton_valide("", None) is False
    assert defense.jeton_valide("éà", "éà") is True  # les octets UTF-8
    assert defense.jeton_valide("éà", "éa") is False

    # Par les routes, sans jamais atteindre le travail (aucun appel à Discord) : les refus.
    monkeypatch.setattr(settings, "DISCORD_DIGEST_TOKEN", jeton_ok)
    client = TestClient(app, follow_redirects=False)
    reproject = "/discord/rsvp/reproject?event_id=11111111-1111-1111-1111-111111111111&occ_date=2026-11-12"
    machine = ("/discord/rsvp/roll", reproject, "/api/internal/digest")
    refus = {"detail": "Token invalide ou absent"}
    for chemin in machine:
        sans = client.post(chemin)
        assert sans.status_code == 403 and sans.json() == refus, chemin
        assert client.post(chemin, headers={"X-Digest-Token": jeton_ok + "x"}).status_code == 403, chemin
    sep = "&" if "?" in reproject else "?"
    assert client.post("/discord/rsvp/roll?token=faux").status_code == 403
    assert client.post(reproject + sep + "token=faux").status_code == 403
    # Lot « rr-socle-proprete » (v1.0111) : la transition est finie, le jeton JUSTE en `?token=` est refusé aussi.
    assert client.post("/discord/rsvp/roll?token=" + jeton_ok).status_code == 403
    assert client.post(reproject + sep + "token=" + jeton_ok).status_code == 403
    # Le digest ne lit pas l'URL : le jeton juste en `?token=` n'y vaut rien.
    assert client.post("/api/internal/digest?token=" + jeton_ok).status_code == 403
    # `DISCORD_DIGEST_TOKEN` vide : refus, même avec des valeurs vides ou quelconques.
    monkeypatch.setattr(settings, "DISCORD_DIGEST_TOKEN", "")
    for chemin in machine:
        assert client.post(chemin, headers={"X-Digest-Token": ""}).status_code == 403, chemin
        assert client.post(chemin, headers={"X-Digest-Token": "x"}).status_code == 403, chemin
    assert client.post("/discord/rsvp/roll?token=").status_code == 403
    assert client.post(reproject + sep + "token=x").status_code == 403
    # Lot « La réception du .rrlog de l'agent » (R1, R19) : `/api/agent/rrlog` est un chemin machine --
    # sans session, la garde du corps ne répond pas « Non authentifié » : c'est la route qui refuse le jeton.
    assert defense.chemin_machine("/api/agent/rrlog") is True
    assert defense.chemin_machine("/api/agent/rrlog/autre") is False
    refus_agent = {"detail": "Jeton refusé."}
    r = client.post("/api/agent/rrlog")
    assert r.status_code == 401 and r.json() == refus_agent
    r = client.post("/api/agent/rrlog", headers={"Authorization": "Bearer pas-un-jeton"})
    assert r.status_code == 401 and r.json() == refus_agent


def test_secret_refuse():
    exemple = next(
        ligne.split("=", 1)[1].strip()
        for ligne in (RACINE / ".env.example").read_text(encoding="utf-8").splitlines()
        if ligne.startswith("SESSION_SECRET=")
    )
    assert defense.secret_refuse("a" * 31) is not None
    assert defense.secret_refuse("") is not None
    assert defense.secret_refuse(exemple) is not None  # la valeur d'exemple, 32 caractères ou plus
    assert len(exemple) >= 32
    valide = secrets.token_hex(32)
    assert len(valide) == 64 and defense.secret_refuse(valide) is None
    assert defense.secret_refuse("a" * 32) is None

    def lancer(valeur: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "SESSION_SECRET": valeur}
        return subprocess.run(
            [sys.executable, "-B", "-m", "app.defense"], cwd=RACINE, env=env, capture_output=True, text=True
        )

    refus = lancer("a" * 31)
    assert refus.returncode == 1 and refus.stderr.strip() != ""
    assert lancer(exemple).returncode == 1
    assert lancer(valide).returncode == 0


def test_lien_exige_json():
    client = TestClient(app, follow_redirects=False)
    # Un formulaire : 415, avant toute lecture du corps.
    assert client.post("/auth/lien", data={"token": "abc"}).status_code == 415
    assert client.post("/auth/lien", content=b"x", headers={"content-type": "text/plain"}).status_code == 415
    # Du JSON avec un `Origin` étranger : 403.
    r = client.post("/auth/lien", json={"token": "abc"}, headers={"origin": "https://autre.example"})
    assert r.status_code == 403
    r = client.post("/auth/lien", json={"token": "abc"}, headers={"origin": "null"})
    assert r.status_code == 403
    # Les fonctions : charset admis, origine (schéma, hôte, port) de `BASE_URL`, `Origin` absent admis.
    assert defense.est_json("application/json; charset=utf-8") is True
    assert defense.est_json("Application/JSON") is True
    assert defense.est_json("text/plain") is False and defense.est_json(None) is False
    base = "https://rr.example.org/"
    assert defense.origine_autorisee(None, base) is True
    assert defense.origine_autorisee("https://rr.example.org", base) is True
    assert defense.origine_autorisee("https://rr.example.org:443", base) is True
    assert defense.origine_autorisee("http://rr.example.org", base) is False
    assert defense.origine_autorisee("https://rr.example.org:8443", base) is False
    assert defense.origine_autorisee("https://autre.example.org", base) is False


def test_deconnexion_en_post():
    client = TestClient(app, follow_redirects=False)
    assert client.get("/auth/logout").status_code == 405
    # Un membre : 204, et le cookie de session est vidé.
    r = client.post("/auth/logout", headers=_session_membre())
    assert r.status_code == 204
    assert "session=null" in r.headers["set-cookie"] and "expires=Thu, 01 Jan 1970" in r.headers["set-cookie"]
    # Un invité passe le mur (R7), et sa session se vide aussi.
    r = client.post("/auth/logout", headers=_session_invite())
    assert r.status_code == 204
    assert "session=null" in r.headers["set-cookie"]


def test_corps_sans_session():
    client = TestClient(app, follow_redirects=False)
    non_authentifie = {"detail": "Non authentifié"}
    # JSON mal formé : 401, pas 422.
    r = client.post("/api/events", content=b"{pas du json", headers={"content-type": "application/json"})
    assert r.status_code == 401 and r.json() == non_authentifie
    # Multipart mal formé : 401, pas 400.
    r = client.post(
        "/api/debrief/upload", content=b"pas du multipart", headers={"content-type": "multipart/form-data; boundary=x"}
    )
    assert r.status_code == 401 and r.json() == non_authentifie
    # La déconnexion sans session, et un cookie mal signé : 401 aussi.
    assert client.post("/auth/logout").status_code == 401
    assert client.post("/api/events", json={}, headers={"cookie": "session=pas.signe.du.tout"}).status_code == 401
    # Les chemins machine ne sont pas refusés par le middleware : ils répondent par leurs propres gardes.
    assert client.post("/auth/lien", data={"token": "abc"}).status_code == 415
    assert client.post("/discord/rsvp/roll").status_code == 403
    assert client.post("/api/internal/digest").status_code == 403
    # Les méthodes de lecture ne sont pas touchées.
    assert client.get("/api/version").status_code == 200


def test_plafond_du_corps():
    client = TestClient(app, follow_redirects=False)
    trop = str(8 * 1024 * 1024 + 1)
    refus = {"detail": "Requête trop volumineuse."}
    # `Content-Length` de 8 Mio + 1 : 413, avant la session comme avant la lecture.
    for en_tetes in ({}, _session_membre()):
        r = client.post("/api/events", content=b"{}", headers={"content-length": trop, "content-type": "application/json", **en_tetes})
        assert r.status_code == 413 and r.json() == refus
    # Le dépôt du Débrief a son propre plafond : 8 Mio + 1 n'y est pas refusé pour sa taille (sans session : 401).
    r = client.post("/api/debrief/upload", content=b"x", headers={"content-length": trop, "content-type": "multipart/form-data; boundary=x"})
    assert r.status_code == 401
    r = client.post(
        "/api/debrief/upload", content=b"x",
        headers={"content-length": str(256 * 1024 * 1024 + 1), "content-type": "multipart/form-data; boundary=x"},
    )
    assert r.status_code == 413 and r.json() == refus
    # Sans `Content-Length` (envoi par morceaux) : les octets se comptent à la lecture.
    def morceaux():
        for _ in range(9):
            yield b"x" * (1024 * 1024)

    r = client.post("/api/events", content=morceaux(), headers={"content-type": "application/json", **_session_membre()})
    assert r.status_code == 413 and r.json() == refus
    assert defense.plafond_du_corps("/api/debrief/upload") == 268_435_456
    assert defense.plafond_du_corps("/api/events") == 8_388_608
    # Lot « La réception du .rrlog de l'agent » (R1, R19) : la route de l'agent a le sien, 32 Mio.
    assert defense.plafond_du_corps("/api/agent/rrlog") == 33_554_432


def test_compression_et_cache():
    for refuse in ("text/event-stream", "text/event-stream; charset=utf-8", "image/png", "font/woff2",
                   "application/zip", "application/gzip", "application/octet-stream"):
        assert defense.a_compresser(refuse) is False, refuse
    for accepte in ("application/javascript", "text/html; charset=utf-8", "image/svg+xml", "application/json", "text/css"):
        assert defense.a_compresser(accepte) is True, accepte
    client = TestClient(app, follow_redirects=False)
    gzip = {"accept-encoding": "gzip"}
    version = quote(api._APP_VERSION, safe="")
    r = client.get(f"/static/app.js?v={version}", headers=gzip)
    assert r.headers["content-encoding"] == "gzip"
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    # `HEAD` porte les mêmes en-têtes que `GET` (`curl -sI`).
    assert client.head(f"/static/app.js?v={version}").headers["cache-control"] == "public, max-age=31536000, immutable"
    for chemin in ("/static/app.js?v=0", "/static/app.js"):
        r = client.get(chemin, headers=gzip)
        assert r.headers["content-encoding"] == "gzip", chemin
        assert "immutable" not in r.headers.get("cache-control", ""), chemin
    # Une erreur n'est jamais gardée un an.
    r = client.get(f"/static/absent.js?v={version}")
    assert r.status_code == 404 and "immutable" not in r.headers.get("cache-control", "")

    # Le flux d'évènements ne se compresse pas, même au-dessus de 1 000 octets ; une page, si.
    async def reponse(scope, receive, send):
        type_ = "text/event-stream" if scope["path"] == "/flux" else "text/html; charset=utf-8"
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", type_.encode())]})
        await send({"type": "http.response.body", "body": b"data: x\n\n" * 200})

    petit = TestClient(defense.CompressionSelective(reponse))
    assert "content-encoding" not in petit.get("/flux", headers=gzip).headers
    assert petit.get("/page", headers=gzip).headers["content-encoding"] == "gzip"

    # Addendum 4 (A) : au fil de l'eau. Une app de type `text/event-stream` envoie `start`, attend, puis
    # deux corps `more_body=True` et un dernier : le `start` doit partir AVANT le premier corps, et chaque
    # corps arriver tel quel (les en-têtes de `/api/stream` ne doivent pas attendre le premier évènement).
    corps = [b"data: un\n\n" * 150, b"data: deux\n\n" * 150, b"data: trois\n\n" * 150]

    async def jouer(accept: str):
        porte = asyncio.Event()
        recus: list[dict] = []

        async def flux(scope, receive, send):
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"text/event-stream; charset=utf-8")]})
            await porte.wait()
            for i, morceau in enumerate(corps):
                await send({"type": "http.response.body", "body": morceau, "more_body": i < len(corps) - 1})

        async def recevoir():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def envoyer(message):
            recus.append(message)

        scope = {"type": "http", "method": "GET", "path": "/api/stream", "query_string": b"",
                 "headers": [(b"accept-encoding", accept.encode())]}
        tache = asyncio.ensure_future(defense.CompressionSelective(flux)(scope, recevoir, envoyer))
        for _ in range(50):  # au plus 0,5 s
            if recus:
                break
            await asyncio.sleep(0.01)
        avant = list(recus)  # ce qui est parti alors que l'app n'a pas encore envoyé de corps
        porte.set()
        await tache
        return avant, recus

    avant, tout = asyncio.run(jouer("gzip"))
    assert [m["type"] for m in avant] == ["http.response.start"]
    assert dict(avant[0]["headers"]) == {b"content-type": b"text/event-stream; charset=utf-8"}
    assert [m["body"] for m in tout[1:]] == corps  # chaque corps tel quel, sans compression ni tampon
    assert [m.get("more_body", False) for m in tout[1:]] == [True, True, False]

    # Addendum 4 (B) : les types que la table de Python ignore dans une image sans `/etc/mime.types`.
    assert mimetypes.guess_type("x.woff2")[0] == "font/woff2"
    assert mimetypes.guess_type("x.webp")[0] == "image/webp"
    assert defense.a_compresser("font/woff2") is False and defense.a_compresser("image/webp") is False

    # Lot « Les dépendances de l'App » : la liste d'exclusion au format de Starlette 1.x. Les polices et
    # les icônes ne se compressent pas, le SVG si ; `octet-stream` et le SVG au-dessus de 1 000 octets,
    # par le middleware lui-même.
    assert defense.a_compresser("font/ttf") is False and defense.a_compresser("image/x-icon") is False
    assert defense.a_compresser("image/svg+xml") is True

    async def types(scope, receive, send):
        type_ = "application/octet-stream" if scope["path"] == "/binaire" else "image/svg+xml"
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", type_.encode())]})
        await send({"type": "http.response.body", "body": b"<g/>" * 400})

    types_client = TestClient(defense.CompressionSelective(types))
    assert "content-encoding" not in types_client.get("/binaire", headers=gzip).headers
    assert types_client.get("/vecteur", headers=gzip).headers["content-encoding"] == "gzip"


def test_cache_sous_numero_publie():
    # Lot « Le cache sous un numéro publié » : sous `RR-V1.0.0+3`, le `+` doit être encodé dans
    # l'adresse (`%2B`), sinon il se lit comme une espace et le cache durable disparaît en silence.
    brut = (RACINE / "app" / "static" / "index.html").read_text(encoding="utf-8")
    texte = main._substituer_version(brut, "RR-V1.0.0+3")
    assert texte.count("?v=RR-V1.0.0%2B3") == 14
    assert texte.count("__ASSET_VERSION__") == 0
    assert texte.count("RR-V1.0.0+3") == 0

    async def sert_200(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"text/javascript")]})
        await send({"type": "http.response.body", "body": b"ok"})

    client = TestClient(defense.EnTetesCommuns(sert_200, version="RR-V1.0.0+3"))
    assert client.get("/static/app.js?v=RR-V1.0.0%2B3").headers["cache-control"] == "public, max-age=31536000, immutable"
    assert "immutable" not in client.get("/static/app.js?v=RR-V1.0.0+3").headers.get("cache-control", "")
