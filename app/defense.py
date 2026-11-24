"""Lot « La défense de l'App exposée » (`v1.0083`, `rr-socle-defense`, avec
`rr-contenu-mixte-https`) -- les middlewares et les fonctions pures qui
défendent l'App exposée sur Internet (audit ARC-04, 08, 09, 10, 11, 12, 13).

Ce module ne dépend ni de `app.config`, ni de `app.api`, ni de `app.auth` :
il se lance seul (`python -B -m app.defense`, contrôle du secret de session au
démarrage, `entrypoint.sh`) et chaque module qui s'en sert l'importe sans cycle.
La version servie, que le cache durable des fichiers de `/static` compare au
paramètre `v`, lui est passée par `app.main`.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import mimetypes
import os
import re
import sys
from collections.abc import Iterable
from urllib.parse import parse_qs, urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.middleware.gzip import DEFAULT_EXCLUDED_CONTENT_TYPES, GZipMiddleware
from starlette.responses import JSONResponse

# --- R1 : les en-têtes communs ----------------------------------------------
# (R1 et son addendum 1 : `nosniff`, `X-Frame-Options` et HSTS partout ; `Referrer-Policy` sur les
# seules pages de l'App.)

# Addendum 4 (B) : dans l'image `python:3.12-slim` (sans `/etc/mime.types`), la table de Python ne
# connaît ni `.woff2` ni `.webp` : `StaticFiles` les servirait en `text/plain`, que `a_compresser`
# compresserait.
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/webp", ".webp")

_HOTES_LOCAUX = ("localhost", "127.0.0.1")
_HSTS = "max-age=31536000"
_CACHE_DURABLE = "public, max-age=31536000, immutable"


def hote_local(host: str | None) -> bool:
    """Vrai quand l'hôte de la requête (en-tête `Host`, port ôté) est `localhost`
    ou `127.0.0.1` : ni HSTS ni `upgrade-insecure-requests` au banc, en http."""
    hote = (host or "").strip().lower()
    if ":" in hote and not hote.startswith("["):
        hote = hote.rsplit(":", 1)[0]
    return hote in _HOTES_LOCAUX


class EnTetesCommuns:
    """Middleware ASGI (R1, R9) : les en-têtes de sécurité de toute réponse HTTP,
    sans écraser un en-tête déjà posé par la route ; et le cache durable des
    fichiers versionnés de `/static` (`GET /static/…?v=<version servie>`).
    Posé le plus à l'extérieur (`app.main`), pour couvrir aussi les erreurs que
    Starlette rend lui-même (404, 405, 500)."""

    def __init__(self, app, version: str):
        self.app = app
        self.version = version

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        local = hote_local(Headers(scope=scope).get("host"))
        versionne = (
            scope["method"] in ("GET", "HEAD")
            and scope["path"].startswith("/static/")
            and parse_qs(scope.get("query_string", b"").decode("latin-1")).get("v") == [self.version]
        )

        async def envoyer(message):
            if message["type"] == "http.response.start":
                en_tetes = MutableHeaders(scope=message)
                # `Referrer-Policy` n'est pas ici (addendum 1) : les suites servies chargent des
                # tuiles chez des tiers, dont certains exigent un `Referer` ; elle ne vaut que
                # sur les pages de l'App (`poser_politique`).
                for nom, valeur in (
                    ("X-Content-Type-Options", "nosniff"),
                    ("X-Frame-Options", "SAMEORIGIN"),
                ):
                    if nom not in en_tetes:
                        en_tetes[nom] = valeur
                if not local and "Strict-Transport-Security" not in en_tetes:
                    en_tetes["Strict-Transport-Security"] = _HSTS
                # Le cache durable ne vaut que pour une réponse servie : jamais
                # pour un 404 ou une erreur, qu'un navigateur garderait un an.
                if versionne and message["status"] in (200, 206, 304):
                    en_tetes["Cache-Control"] = _CACHE_DURABLE
            await send(message)

        await self.app(scope, receive, envoyer)


# --- R2 : la politique de contenu des pages de l'App -------------------------

_SCRIPT_EN_LIGNE = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.DOTALL | re.IGNORECASE)


def empreintes_scripts(html: str) -> list[str]:
    """Les empreintes CSP (`'sha256-<base64>'`) des scripts en ligne de la page, dans
    leur ordre d'apparition : un `<script>` sans `src`, son texte exact. Une page
    sans script en ligne n'en a aucune."""
    empreintes = []
    for attributs, texte in _SCRIPT_EN_LIGNE.findall(html):
        if re.search(r"\bsrc\s*=", attributs, re.IGNORECASE):
            continue
        digest = hashlib.sha256(texte.encode("utf-8")).digest()
        empreintes.append("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")
    return empreintes


def politique_contenu(empreintes: Iterable[str], local: bool) -> str:
    """La valeur de `Content-Security-Policy` d'une page de l'App. `upgrade-insecure-requests`
    n'y est pas quand l'hôte est local : en `http://127.0.0.1`, la directive ferait
    passer les requêtes en `https://` et casserait tout."""
    scripts = " ".join(["'self'", *empreintes])
    valeur = (
        "default-src 'self'; "
        f"script-src {scripts}; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://cdn.discordapp.com; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'self'"
    )
    if not local:
        valeur += "; upgrade-insecure-requests"
    return valeur


def poser_politique(reponse, request, empreintes: Iterable[str]):
    """Pose `Content-Security-Policy` sur la réponse d'une page de l'App (la valeur
    dépend de l'hôte de la requête), avec `Referrer-Policy: same-origin` -- sauf si la
    route a posé la sienne (`/auth/lien` garde son `no-referrer`) -- et la rend."""
    reponse.headers["Content-Security-Policy"] = politique_contenu(
        empreintes, hote_local(request.headers.get("host"))
    )
    if "Referrer-Policy" not in reponse.headers:
        reponse.headers["Referrer-Policy"] = "same-origin"
    return reponse


# --- R5 : le jeton des déclencheurs machine -----------------------------------


def jeton_valide(attendu: str, en_tete: str | None) -> bool:
    """Le jeton des déclencheurs machine (R5, addendum 3) : faux quand `attendu` est vide ou
    l'en-tête `X-Digest-Token` absent ; sinon vrai quand l'en-tête est égal à `attendu`,
    comparé à temps constant sur les octets UTF-8. Lot « rr-socle-proprete » (v1.0111) : la
    transition du `?token=` (v1.0083) est terminée, le troisième paramètre est retiré -- le
    jeton ne se lit plus que dans l'en-tête, jamais dans l'adresse."""
    if not attendu:
        return False
    if en_tete is None:
        return False
    return hmac.compare_digest(en_tete.encode("utf-8"), attendu.encode("utf-8"))


# --- R6 : le secret de session contrôlé au démarrage ---------------------------

_LONGUEUR_MINIMALE = 32
# Empreinte sha256 (hex) de la valeur d'exemple du `.env.example` de la v1.0082 :
# jamais la valeur elle-même.
_EMPREINTE_EXEMPLE = "95abdbb340e1c6a23ae3e8750fb9bf0b6389cedd3c2e7247b1204cfbca0ca3bb"


def secret_refuse(secret: str) -> str | None:
    """La raison pour laquelle le secret de session est refusé, ou `None` : moins de
    32 caractères, ou la valeur d'exemple du `.env.example`."""
    if len(secret) < _LONGUEUR_MINIMALE:
        return f"fewer than {_LONGUEUR_MINIMALE} characters"
    if hashlib.sha256(secret.encode("utf-8")).hexdigest() == _EMPREINTE_EXEMPLE:
        return "the .env.example sample value"
    return None


def _controle_au_demarrage() -> int:
    """`python -B -m app.defense` : lit `SESSION_SECRET` dans l'environnement (pas par
    `app.config`), écrit la raison du refus sur la sortie d'erreur et rend 1 ; 0 sinon."""
    raison = secret_refuse(os.environ.get("SESSION_SECRET", ""))
    if raison is not None:
        print(raison, file=sys.stderr)
        return 1
    return 0


# --- R7 : l'origine de l'App ---------------------------------------------------

_PORTS_PAR_DEFAUT = {"http": 80, "https": 443}


def _origine(url: str) -> tuple[str, str, int | None] | None:
    """(schéma, hôte, port) d'une URL, port par défaut du schéma rendu explicite ;
    `None` quand l'URL n'a ni schéma ni hôte (l'en-tête `Origin: null`, par exemple)."""
    try:
        morceaux = urlsplit(url.strip())
        schema = morceaux.scheme.lower()
        hote = (morceaux.hostname or "").lower()
        port = morceaux.port or _PORTS_PAR_DEFAUT.get(schema)
    except ValueError:
        return None
    if not schema or not hote:
        return None
    return schema, hote, port


def origine_autorisee(origin: str | None, base_url: str) -> bool:
    """Un en-tête `Origin` absent passe (les essais, les clients sans navigateur) ; présent,
    il doit être l'origine de `BASE_URL` (schéma, hôte, port)."""
    if origin is None:
        return True
    obtenue = _origine(origin)
    return obtenue is not None and obtenue == _origine(base_url)


def est_json(content_type: str | None) -> bool:
    """Vrai pour `application/json`, paramètres admis (`; charset=utf-8`)."""
    return (content_type or "").split(";", 1)[0].strip().lower() == "application/json"


# --- R8 : le corps refusé sans session, et plafonné ----------------------------

PLAFOND_DEPOT_DEBRIEF = 268_435_456  # 256 Mio
PLAFOND_DEFAUT = 8_388_608  # 8 Mio
# Lot « La réception du .rrlog de l'agent » (R1) : le corps gzip de l'agent du serveur DCS.
PLAFOND_AGENT = 33_554_432  # 32 Mio
_CHEMIN_DEPOT_DEBRIEF = "/api/debrief/upload"
_CHEMIN_AGENT = "/api/agent/rrlog"
_METHODES_SANS_CORPS = ("GET", "HEAD", "OPTIONS")


def plafond_du_corps(chemin: str) -> int:
    """256 Mio au dépôt du Débrief, 32 Mio à la route de l'agent, 8 Mio ailleurs."""
    if chemin == _CHEMIN_AGENT:
        return PLAFOND_AGENT
    return PLAFOND_DEPOT_DEBRIEF if chemin == _CHEMIN_DEPOT_DEBRIEF else PLAFOND_DEFAUT


def chemin_machine(chemin: str) -> bool:
    """Les chemins qu'appellent des machines, sans session : `/auth/lien` (exact), `/discord/…`,
    `/api/internal/…` et `/api/agent/rrlog` (exact, l'agent du serveur DCS, qui porte un jeton)."""
    return (
        chemin in ("/auth/lien", _CHEMIN_AGENT)
        or chemin.startswith(("/discord/", "/api/internal/"))
    )


class _CorpsTropGros(Exception):
    """Levée par la lecture du corps au dépassement du plafond."""


class GardeDuCorps:
    """Middleware ASGI (R8), posé plus profond que `SessionMiddleware` : il lit la session telle
    que celui-ci l'a décodée. Pour les méthodes autres que GET, HEAD et OPTIONS, avant toute
    lecture du corps : le plafond (413), puis la session (401, hors des chemins machine).
    Sans `Content-Length`, les octets se comptent à la lecture et la requête s'arrête en 413
    au dépassement. Les gardes des routes ne changent pas : il ne fait qu'avancer le refus."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] in _METHODES_SANS_CORPS:
            await self.app(scope, receive, send)
            return
        chemin = scope["path"]
        plafond = plafond_du_corps(chemin)
        annonce = Headers(scope=scope).get("content-length")
        # Addendum 4 (C) : `re.fullmatch`, pas `isdigit()` (qui admet « ² » et lèverait une erreur).
        if annonce is not None and re.fullmatch(r"[0-9]+", annonce.strip()) and int(annonce) > plafond:
            await self._trop_gros()(scope, receive, send)
            return
        if not chemin_machine(chemin) and "id" not in (scope.get("session") or {}):
            await JSONResponse({"detail": "Non authentifié"}, status_code=401)(scope, receive, send)
            return

        lus = 0
        depasse = False
        reponse_envoyee = False

        async def recevoir():
            nonlocal lus, depasse
            message = await receive()
            if message["type"] == "http.request":
                lus += len(message.get("body", b""))
                if lus > plafond:
                    depasse = True
                    raise _CorpsTropGros()
            return message

        async def envoyer(message):
            nonlocal reponse_envoyee
            if depasse:
                # Le corps a dépassé le plafond : quoi que la route réponde (FastAPI
                # transforme une lecture en échec en 400), c'est le 413 qui part.
                return
            reponse_envoyee = True
            await send(message)

        try:
            await self.app(scope, recevoir, envoyer)
        except Exception:
            if not depasse:
                raise
        if depasse and not reponse_envoyee:
            await self._trop_gros()(scope, receive, send)

    @staticmethod
    def _trop_gros() -> JSONResponse:
        return JSONResponse({"detail": "Requête trop volumineuse."}, status_code=413)


# --- R9 : la compression --------------------------------------------------------

# Lot « Les dépendances de l'App » : la liste d'exclusion au format de Starlette 1.x
# (`GZipMiddleware(exclude_content_types=…)`) ; `a_compresser` lit cette même liste.
_SANS_COMPRESSION = DEFAULT_EXCLUDED_CONTENT_TYPES + (
    "font/*", "application/octet-stream", "image/x-icon", "image/vnd.microsoft.icon",
)


def a_compresser(content_type: str) -> bool:
    """Vrai quand une réponse de ce `Content-Type` se compresse : tout, sauf les types de
    `_SANS_COMPRESSION` (la liste d'exclusion de Starlette : flux `text/event-stream`, images
    sauf `image/svg+xml`, `application/zip`, `application/gzip`… — plus `font/*`,
    `application/octet-stream` et les icônes). Même correspondance que Starlette : le type sans
    paramètres, en minuscules, est exclu s'il figure dans la liste ou si sa famille `<famille>/*`
    y figure."""
    type_ = (content_type or "").split(";", 1)[0].strip().lower()
    return not (type_ in _SANS_COMPRESSION or f"{type_.split('/', 1)[0]}/*" in _SANS_COMPRESSION)


class CompressionSelective(GZipMiddleware):
    """Gzip des réponses de plus de 1 000 octets, quand le client l'accepte, sauf les
    `Content-Type` que `a_compresser` écarte. Starlette 1.x exclut ces types de lui-même : pour
    un type écarté, `http.response.start` part tout de suite, tel quel (le flux `/api/stream`
    n'attend pas son premier évènement), et le corps suit sans compression ni tampon."""

    def __init__(self, app):
        super().__init__(app, minimum_size=1001, exclude_content_types=_SANS_COMPRESSION)


if __name__ == "__main__":
    raise SystemExit(_controle_au_demarrage())
