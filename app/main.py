"""Ready Room / Planification — app FastAPI.

Migrations appliquées au démarrage (entrypoint.sh), auth Discord OAuth2
(sans bot), session cookie signée, gating par rôles (Lot 1). Depuis le
Lot 3b : sert aussi le front réel en statique (`app/static/`) — maquette
validée dé-monofichiérisée, câblée sur l'API + SSE.
"""
import asyncio
import hashlib
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote


def _configure_app_logging() -> None:
    """Garantit que les loggers `app.*` remontent en **stdout** au niveau
    **INFO** (donc WARNING aussi), sans casser le logging d'uvicorn (cf.
    brief Lot 2b-2 §3a). Dette révélée : sans handler explicite, les
    `logger.warning(...)` applicatifs restaient invisibles dans
    `docker compose logs`. Posé ICI, avant l'import des modules `app.*`
    ci-dessous, pour couvrir aussi les warnings émis au chargement des
    modules (ex. garde-fou Phase 2b dans `app/config.py`). Idempotent
    (rechargement module / tests) : n'ajoute pas de handler en double."""
    app_logger = logging.getLogger("app")
    app_logger.disabled = False
    app_logger.setLevel(logging.INFO)
    if not app_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        app_logger.addHandler(handler)
    # Pas de propagation vers la racine : un seul handler, une seule ligne
    # par log (évite un double-affichage si uvicorn attache aussi un
    # handler racine).
    app_logger.propagate = False


_configure_app_logging()

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from sqlalchemy import select

from app import agent, api, appel, auth, connexion_secours, crests, defense, discord_digest, discord_rsvp, langue, reglages, sauvegardes_auto, taches, tuiles_dcs, wing_config
from app.auth import get_current_user_optional
from app.config import settings
from app.db import AsyncSessionLocal
from app.debrief import engine as debrief_engine
from app.debrief import referentiel as debrief_referentiel
from app.models import Squadron, Wing
from app.squadron import reconcile_squadrons_from_env

_main_logger = logging.getLogger("app.main")


async def _startup_reconcile_discord_surface() -> None:
    """Tâche de fond (non bloquante) lancée par le lifespan ci-dessous --
    cf. brief Lot 2b-3 §2 étape 4 : un flip de flag (qui impose
    `--force-recreate`) déclenche automatiquement la réconciliation au
    redémarrage suivant. Sa propre `AsyncSessionLocal` (jamais celle d'une
    route), jamais fatale : le boot ne doit jamais échouer à cause de
    Discord."""
    try:
        async with AsyncSessionLocal() as db:
            await discord_rsvp.reconcile_discord_surface(db)
    except Exception:
        _main_logger.exception(
            "Reconcile Discord : erreur non bloquante au démarrage (lifespan)"
        )


async def _startup_reconcile_squadrons() -> None:
    """Tâche de fond (non bloquante) -- Lot 2.2b, cf. brief G3 / cadrage CC
    §4 : au démarrage, recrée la ligne `wing` depuis `WING_TAG` si sa table
    est muette (le filet seulement ; lot « rr-socle-proprete », v1.0111 : les
    escadrilles ne se sèment plus depuis le `.env`). Même modèle que
    `_startup_reconcile_discord_surface` ci-dessus : sa propre session,
    jamais fatale."""
    try:
        async with AsyncSessionLocal() as db:
            await reconcile_squadrons_from_env(db)
    except Exception:
        _main_logger.exception(
            "Réconciliation escadrille : erreur non bloquante au démarrage (lifespan)"
        )


async def _startup_recompute_stale_sessions() -> None:
    """Tâche de fond (non bloquante) -- Lot Fraîcheur v0.9939, brief §6.
    Exactement sur le patron des deux tâches ci-dessus : sa propre
    `AsyncSessionLocal` (jamais celle d'une route), jamais fatale -- le
    démarrage ne doit jamais échouer à cause d'elle. Recalcule, une par
    une, toutes les sessions dont l'empreinte moteur est périmée (fonction
    unique `engine.recompute_stale_sessions`, partagée avec la route admin
    `POST /sessions/recompute-stale`)."""
    try:
        async with AsyncSessionLocal() as db:
            n, echecs = await debrief_engine.recompute_stale_sessions(db)
            _main_logger.info(
                "Fraîcheur : %d session(s) périmée(s) recalculée(s), %d en échec, au démarrage (lifespan)",
                n,
                echecs,
            )
    except Exception:
        _main_logger.exception(
            "Recalcul fraîcheur : erreur non bloquante au démarrage (lifespan)"
        )


async def _startup_charger_referentiel() -> None:
    """Tâche de fond (non bloquante) -- lot « Les référentiels : types et
    armes » : relit en mémoire les catégories forcées de l'écran Référentiels
    (`debrief_referentiel.FORCEES`). Même modèle que les tâches ci-dessus : sa
    propre `AsyncSessionLocal`, jamais fatale -- sans elle, les catégories
    restent automatiques."""
    try:
        async with AsyncSessionLocal() as db:
            await debrief_referentiel.charger(db)
    except Exception:
        _main_logger.exception(
            "Référentiel : chargement des catégories forcées en erreur non bloquante au démarrage (lifespan)"
        )


async def _startup_enregistrer_commande() -> None:
    """Tâche de fond (non bloquante) -- lot « La connexion de secours » (R325) :
    déclare la commande `/readyroom` sur le serveur Discord, seulement si le
    bot et la clé publique des interactions sont renseignés. Même modèle que
    les tâches ci-dessus : jamais fatale, le démarrage ne dépend pas de Discord."""
    try:
        if settings.bot_token_present and settings.DISCORD_PUBLIC_KEY:
            await connexion_secours.enregistrer_commande()
    except Exception:
        _main_logger.exception(
            "Commande /readyroom : erreur non bloquante au démarrage (lifespan)"
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cf. brief Lot 2b-3 §2 étape 4 -- posé sans perturber l'init existante
    (`_configure_app_logging()` reste appelée à l'import, avant même cet
    import de module). Tâche de fond non bloquante : le `yield` n'attend
    pas la réconciliation, le serveur sert donc immédiatement. Lot
    « L'appel » : la boucle de l'appel (`app/appel.py`) -- sa tâche est
    gardée ici le temps de vie de l'application, puis annulée.

    Lot « rr-env-epure » : les réglages gardés en base sont chargés AVANT les tâches de
    fond (`reglages.charger_au_demarrage`, attendue, jamais fatale) -- elles lisent
    `settings` -- ; le passage quotidien de 6 h (Paris) est une tâche de l'App, comme la
    boucle des sauvegardes."""
    await reglages.charger_au_demarrage()
    taches.lancer(_startup_reconcile_discord_surface())
    taches.lancer(_startup_reconcile_squadrons())
    taches.lancer(_startup_recompute_stale_sessions())
    taches.lancer(_startup_charger_referentiel())
    taches.lancer(_startup_enregistrer_commande())
    tache_appel = taches.lancer(appel.boucle_appel())
    # Lot « Les sauvegardes automatiques » : la boucle des sauvegardes, à côté
    # de celle de l'appel, annulée de la même façon.
    tache_sauvegardes = taches.lancer(sauvegardes_auto.boucle())
    # Lot « rr-env-epure » : le passage quotidien de 6 h (Paris), annulé de la même façon.
    tache_quotidienne = taches.lancer(discord_rsvp.boucle_quotidienne())
    yield
    tache_appel.cancel()
    tache_sauvegardes.cancel()
    tache_quotidienne.cancel()


class _Application(FastAPI):
    """Lot « La défense de l'App exposée » (R1) : les en-têtes communs se posent sur le
    middleware le plus extérieur, au-dessus même de celui qui rend les erreurs 500 de
    Starlette -- aucune réponse n'y échappe, quelle que soit la route."""

    def build_middleware_stack(self):
        return defense.EnTetesCommuns(super().build_middleware_stack(), version=api._APP_VERSION)


# Lot « La défense de l'App exposée » : plus de redirection de barre finale (R3 --
# celle de Starlette sortait en `http://`, d'après le schéma reçu derrière le Funnel)
# et la documentation de l'API fermée (R4).
app = _Application(
    title="Squadron Ready Room — Planification",
    lifespan=lifespan,
    redirect_slashes=False,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

# Lot « L'accès invité » (R6) -- le mur : un invité (session portant `invite`
# vrai) ne fait que lire. Toute requête d'une autre méthode que GET, HEAD ou
# OPTIONS reçoit 403 avant le routage, sans lecture en base, aucune exception
# (`/api/seen` compris). La décision est une fonction pure.
_METHODES_LECTURE = ("GET", "HEAD", "OPTIONS")
_MUR_INVITE_DETAIL = "Accès invité : lecture seule."


def ecriture_refusee(session: dict | None, methode: str) -> bool:
    """Vrai quand la session est celle d'un invité et que la méthode n'est ni
    `GET`, ni `HEAD`, ni `OPTIONS`. Une session absente, ou d'un membre (sans la
    clé `invite`), ne refuse rien."""
    if not session or session.get("invite") is not True:
        return False
    return methode.upper() not in _METHODES_LECTURE


class MurInvite:
    """Middleware ASGI du mur. Il lit la session telle que `SessionMiddleware` l'a
    décodée (`scope["session"]`) : il doit donc être posé PLUS PROFOND que lui --
    ajouté AVANT lui dans `add_middleware`, qui empile vers l'extérieur.

    Lot « La défense de l'App exposée » (R7) : le mur laisse passer `POST /auth/logout`
    -- sans cela, un invité ne pourrait plus se déconnecter. `ecriture_refusee` ne
    change pas : l'exception vit ici."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] == "http"
            and not (scope["method"] == "POST" and scope["path"] == "/auth/logout")
            and ecriture_refusee(scope.get("session"), scope["method"])
        ):
            reponse = JSONResponse({"detail": _MUR_INVITE_DETAIL}, status_code=403)
            await reponse(scope, receive, send)
            return
        await self.app(scope, receive, send)


# Le mur d'abord (le plus profond), puis la garde du corps (R8), puis la session
# (au-dessus, qui les précède à l'entrée d'une requête).
app.add_middleware(MurInvite)
# Lot « La défense de l'App exposée » (R8) : le corps refusé sans session et plafonné,
# avant toute lecture ; il lit la session décodée, donc plus profond que `SessionMiddleware`.
app.add_middleware(defense.GardeDuCorps)

# Cookie de session signé : HttpOnly (par défaut Starlette), Secure, SameSite=Lax.
# SameSite=Lax est IMPÉRATIF (pas Strict) : le retour d'OAuth depuis Discord
# est une navigation top-level cross-site ; Strict ferait perdre le cookie
# et donc le `state` stocké en session avant redirection.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET,
    https_only=True,
    same_site="lax",
    max_age=settings.session_max_age_seconds,
)
# Lot « La défense de l'App exposée » (R9) : gzip des réponses de plus de 1 000 octets,
# sauf le flux SSE, les images (hors SVG), les polices et les archives.
app.add_middleware(defense.CompressionSelective)

# IMPORTANT (cf. brief Lot 3b) : les routes /auth/* et /api/* sont montées
# AVANT le montage StaticFiles ci-dessous.
app.include_router(auth.router)
app.include_router(api.router)
app.include_router(discord_digest.router)
# Lot « La réception du .rrlog de l'agent » : la route de l'agent du serveur DCS (jeton, hors session).
app.include_router(agent.router)
app.include_router(discord_rsvp.router)
app.include_router(connexion_secours.router)

templates = Jinja2Templates(directory="app/templates")

STATIC_DIR = "app/static"

# Cache-busting (v0.27) : le shell référence app.js/styles.css avec
# ?v=<VERSION>. Source unique = fichier VERSION (déjà chargé par
# app.api._APP_VERSION). Substitution faite UNE fois à l'import (la
# VERSION est figée par image/boot) -> pas d'I/O par requête.
def _substituer_version(texte: str, version: str) -> str:
    """Lot « Le cache sous un numéro publié » : la version entre dans l'adresse (?v=) encodée
    comme une composante d'adresse, aucun caractère sûr gardé (`+` -> `%2B`) ; sinon un `+` se
    lirait comme une espace et `EnTetesCommuns` ne reconnaîtrait plus la version servie."""
    return texte.replace("__ASSET_VERSION__", quote(version, safe=""))


_INDEX_HTML = _substituer_version(
    Path(STATIC_DIR, "index.html").read_text(encoding="utf-8"),
    api._APP_VERSION,
)

# Lot « La défense de l'App exposée » (R2) : les empreintes des scripts en ligne des
# pages de l'App, calculées UNE fois, depuis le texte même que la page sert (le shell
# après la substitution ci-dessus ; les gabarits de connexion et de lien, dont les
# blocs `<script>` n'ont aucune syntaxe Jinja) -- jamais écrites en dur.
_EMPREINTES_INDEX = defense.empreintes_scripts(_INDEX_HTML)
_EMPREINTES_LOGIN = defense.empreintes_scripts(
    Path("app/templates/login.html").read_text(encoding="utf-8")
)
_EMPREINTES_LIEN = defense.empreintes_scripts(
    Path("app/templates/lien.html").read_text(encoding="utf-8")
)


@app.get("/")
async def root(request: Request, user: dict | None = Depends(get_current_user_optional)):
    """Non authentifié -> page de login (Lot 1, `app/templates/login.html`).
    Authentifié -> shell statique réel (`app/static/index.html`), qui se
    charge lui-même de tout le reste (fetch `/api/me`, calendrier, SSE...).
    """
    if user is not None:
        return defense.poser_politique(HTMLResponse(_INDEX_HTML), request, _EMPREINTES_INDEX)
    # Lot « rr-public-pages-bilingues » : `?lang=fr|en` pose le cookie du choix et revient à `/`.
    choix = request.query_params.get("lang")
    if choix in langue.LANGUES:
        retour = RedirectResponse("/", status_code=303)
        retour.set_cookie(
            langue.COOKIE, choix, max_age=langue.UN_AN, path="/", samesite="lax",
            httponly=True, secure=settings.BASE_URL.lower().startswith("https://"),
        )
        return retour
    lang = langue.langue_requete(request)
    designation, emblem_url, full_name = await _wing_login_identity()
    return defense.poser_politique(
        templates.TemplateResponse(
            request,
            "login.html",
            {
                "request": request,
                "lang": lang,
                "t": langue.textes(lang),
                "wing_designation": designation,
                "wing_emblem_url": emblem_url,
                "wing_full_name": full_name,  # lot « L'écran Archives du Centre » : le sur-titre
            },
        ),
        request, _EMPREINTES_LOGIN,
    )


@app.get("/auth/lien")
async def page_lien(request: Request):
    """Lot « La connexion de secours » (R325) -- la page d'un lien d'entrée. Aucune
    garde : elle ne révèle rien, elle lit le fragment de l'URL (le jeton, que le
    serveur ne voit jamais) et n'envoie le jeton à `POST /auth/lien` qu'au clic.
    Ni cache ni `Referer`."""
    designation, emblem_url, full_name = await _wing_login_identity()
    lang = langue.langue_requete(request)
    reponse = templates.TemplateResponse(
        request,
        "lien.html",
        {
            "request": request,
            "lang": lang,
            "t": langue.textes(lang),
            "wing_designation": designation,
            "wing_emblem_url": emblem_url,
            "wing_full_name": full_name,
        },
    )
    reponse.headers["Cache-Control"] = "no-store"
    reponse.headers["Referrer-Policy"] = "no-referrer"
    return defense.poser_politique(reponse, request, _EMPREINTES_LIEN)


# Lot « Les suites servies par la Ready Room » : Mission Plan et Mission Tools,
# deux fichiers HTML autoportants déposés par le porteur dans `settings.SUITES_DIR`.
# Deux routes à noms de fichiers FIXES (aucun nom ne se tire de l'URL, aucun
# StaticFiles sur le dossier), derrière la même garde que `/`. Ces routes sont
# écrites ici, dans aucun routeur.
_SUITE_PLAN = ("dcs_mission_plan.html", "https://mirabellebenou.github.io/dcs-mission-plan/")
_SUITE_TOOLS = ("dcs_mission_tools.html", "https://mirabellebenou.github.io/dcs-mission-tools/")
_SUITE_CACHE_CONTROL = "private, no-cache"


def _suite_repondre(request: Request, user: dict | None, suite: tuple[str, str]) -> Response:
    """Toutes les redirections du lot sont des 307 : une redirection permanente
    resterait dans le cache du navigateur après un dépôt. La garde passe avant
    toute lecture du dossier. L'ETag est une empreinte des OCTETS du fichier
    (jamais sa date) et `If-Modified-Since` est ignoré : le retour arrière
    renomme un `*.prec.html` qui garde sa date ancienne, une validation par la
    date laisserait la version fautive en cache."""
    fichier, repli_github = suite
    if user is None:
        return RedirectResponse("/", status_code=307)
    try:
        chemin = Path(settings.SUITES_DIR) / fichier
        if not chemin.is_file():
            return RedirectResponse(repli_github, status_code=307)
        contenu = chemin.read_bytes()
    except OSError:
        # Dossier ou fichier illisible : jamais une erreur serveur.
        return RedirectResponse(repli_github, status_code=307)
    etag = '"' + hashlib.sha256(contenu).hexdigest()[:32] + '"'
    en_tetes = {"ETag": etag, "Cache-Control": _SUITE_CACHE_CONTROL}
    candidats = [
        c.strip().removeprefix("W/")
        for c in request.headers.get("if-none-match", "").split(",")
    ]
    if etag in candidats:
        return Response(status_code=304, headers=en_tetes)
    return Response(
        content=contenu, media_type="text/html; charset=utf-8", headers=en_tetes
    )


@app.get("/outils/mission-plan/")
async def suite_mission_plan(
    request: Request, user: dict | None = Depends(get_current_user_optional)
):
    return _suite_repondre(request, user, _SUITE_PLAN)


@app.get("/outils/mission-tools/")
async def suite_mission_tools(
    request: Request, user: dict | None = Depends(get_current_user_optional)
):
    return _suite_repondre(request, user, _SUITE_TOOLS)


# Sans barre finale : 307 vers le chemin avec barre, `Location` relatif, sans
# lire la session.
@app.get("/outils/mission-plan")
async def suite_mission_plan_sans_barre():
    return RedirectResponse("/outils/mission-plan/", status_code=307)


@app.get("/outils/mission-tools")
async def suite_mission_tools_sans_barre():
    return RedirectResponse("/outils/mission-tools/", status_code=307)


# Lot « Le Manuel Pilote, le socle » : le manuel est un document buildé
# (`python3.12 -B manuel/build_manuel.py`), servi tel quel depuis
# `app/manuel/manuel.html` — jamais sous `/static` (public). Même patron que les
# suites : même garde que `/`, 307 vers `/` sans session, ETag sur les octets,
# `Cache-Control` des suites, 304 sur `If-None-Match`. Fichier absent ou
# illisible : 404, jamais une erreur serveur.
_MANUEL_FICHIER = Path(__file__).resolve().parent / "manuel" / "manuel.html"


@app.get("/manuel/")
async def manuel_pilote(
    request: Request, user: dict | None = Depends(get_current_user_optional)
):
    if user is None:
        return RedirectResponse("/", status_code=307)
    try:
        contenu = _MANUEL_FICHIER.read_bytes()
    except OSError:
        return Response(status_code=404)
    etag = '"' + hashlib.sha256(contenu).hexdigest()[:32] + '"'
    en_tetes = {"ETag": etag, "Cache-Control": _SUITE_CACHE_CONTROL}
    candidats = [
        c.strip().removeprefix("W/")
        for c in request.headers.get("if-none-match", "").split(",")
    ]
    if etag in candidats:
        return Response(status_code=304, headers=en_tetes)
    return Response(
        content=contenu, media_type="text/html; charset=utf-8", headers=en_tetes
    )


# Sans barre finale : 307 vers le chemin avec barre, sans lire la session.
@app.get("/manuel")
async def manuel_pilote_sans_barre():
    return RedirectResponse("/manuel/", status_code=307)


# Lot « La config d'escadre de Mission Plan fabriquée par le Centre » (v1.0091) :
# la config d'escadre que lisent les modules de Mission Plan est FABRIQUÉE par la
# Ready Room (`app/wing_config.py`) depuis l'Escadre et ses escadrilles actives qui
# ont un callsign ; elle est servie aux seuls membres connectés, et le front
# (`syncWingConfigSuite`) l'écrit dans le navigateur sous `wing_config_v1`. Le
# fichier `wing_config.json` déposé à la main ne sert plus : la route ne lit plus
# `SUITES_DIR`. Elle ne lit que `wing`, `squadron` et les fichiers d'écusson (sans rien
# créer sur le disque), sert
# toujours `200`, et ne rend la main à personne sans session : sans session, `401`
# (pas de redirection), sans lire la base.
def _wing_config_chemin_logo(cle) -> Path:
    """Le chemin d'un écusson (`"wing"` : l'emblème de l'escadre ; un entier :
    l'écusson de cette escadrille), bâti depuis `CREST_STORAGE_DIR` avec les noms
    de fichier de `app/crests.py` -- SANS `mkdir` : cette route ne crée rien sur
    le disque (`crests.crest_path` crée le dossier à la demande)."""
    nom = "wing.png" if cle == "wing" else f"{cle}.png"
    return Path(settings.CREST_STORAGE_DIR) / nom


def _wing_config_lire_logo(cle):
    """Les octets PNG d'un écusson, ou `None` : un dossier absent ou illisible
    vaut « pas de logo »."""
    try:
        return _wing_config_chemin_logo(cle).read_bytes()
    except OSError:
        return None


def _wing_config_logo_present(cle) -> bool:
    try:
        return _wing_config_chemin_logo(cle).is_file()
    except OSError:
        return False


@app.get("/outils/wing-config.json")
async def wing_config_suite(
    request: Request, user: dict | None = Depends(get_current_user_optional)
):
    if user is None:
        return Response(status_code=401)
    async with AsyncSessionLocal() as db:
        escadre = (
            await db.execute(select(Wing).order_by(Wing.id.asc()).limit(1))
        ).scalar_one_or_none()
        escadrilles = (
            await db.execute(select(Squadron).order_by(Squadron.id.asc()))
        ).scalars().all()
    # Pillow et les lectures de fichiers ne bloquent pas la boucle d'événements.
    contenu = await asyncio.to_thread(
        wing_config.en_memoire,
        escadre, escadrilles, _wing_config_lire_logo, _wing_config_logo_present,
        settings.WING_ID,
    )
    # Même forme que `_suite_repondre` : ETag des OCTETS, `If-Modified-Since`
    # ignoré, pas de `Last-Modified`.
    etag = '"' + hashlib.sha256(contenu).hexdigest()[:32] + '"'
    en_tetes = {"ETag": etag, "Cache-Control": _SUITE_CACHE_CONTROL}
    candidats = [
        c.strip().removeprefix("W/")
        for c in request.headers.get("if-none-match", "").split(",")
    ]
    if etag in candidats:
        return Response(status_code=304, headers=en_tetes)
    return Response(content=contenu, media_type="application/json", headers=en_tetes)


# Lot « Le miroir des tuiles DCS » : les tuiles de la couche « Carte DCS » du
# Route Planner, servies aux seuls membres connectés -- le disque
# (`settings.TILES_DIR`), puis les tuiles gardées (`settings.TILES_CACHE_DIR`),
# puis Olympus, dont la tuile est gardée. Toute la logique (validation, lecture,
# appel d'Olympus, garde) vit dans `app/tuiles_dcs.py` ; la route ne fait que
# l'enchaîner. C'est une image chargée par le front : sans session, `401` (pas
# de redirection), sans rien lire ni rien demander. `z`, `x` et `y` restent des
# chaînes : le module les valide avant toute conversion.
@app.get("/outils/tuiles/dcs/{cle}/{z}/{x}/{y}.png")
async def tuiles_dcs_miroir(
    cle: str,
    z: str,
    x: str,
    y: str,
    user: dict | None = Depends(get_current_user_optional),
):
    if user is None:
        return Response(status_code=401)
    return await tuiles_dcs.servir(cle, z, x, y)


# Lot « L'écran Escadre du Centre » : la page de connexion se rend avant toute
# authentification, côté serveur -- elle lit donc la ligne `wing` elle-même.
# Repli (aucune ligne, base injoignable, aucun emblème posé ou fichier absent
# du volume) : « Ready Room » et l'insigne générique (lot « rr-public-sans-escadre » :
# une installation neuve ne porte le nom d'aucune escadre).
_WING_FALLBACK_DESIGNATION = "Ready Room"
_WING_FALLBACK_EMBLEM_URL = "/static/assets/img/emblem-default.png"
# Lot « L'écran Archives du Centre » (dette `connexion-sur-titre`) : le
# sur-titre de la page lit le nom complet de l'escadre, avec ce repli.
_WING_FALLBACK_FULL_NAME = "Squadron Ready Room"


async def _wing_login_identity() -> tuple[str, str, str]:
    designation = _WING_FALLBACK_DESIGNATION
    emblem_url = _WING_FALLBACK_EMBLEM_URL
    full_name = _WING_FALLBACK_FULL_NAME
    try:
        async with AsyncSessionLocal() as db:
            wing = (
                await db.execute(select(Wing).order_by(Wing.id.asc()).limit(1))
            ).scalar_one_or_none()
        if wing is not None:
            designation = (wing.designation or "").strip() or designation
            full_name = (wing.full_name or "").strip() or full_name
            if wing.emblem_sha and crests.wing_emblem_path().is_file():
                emblem_url = f"/api/wing/emblem?v={wing.emblem_sha}"
    except Exception:
        _main_logger.exception("Page de connexion : identité de l'escadre illisible, repli")
    return designation, emblem_url, full_name


# Sert app.js / styles.css / assets/* sous /static/*. Monté en dernier :
# ne doit jamais masquer /auth/* ni /api/* (cf. note ci-dessus).
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
