"""Lot « Le miroir des tuiles DCS » (`v1.0059`) -- les tuiles de la couche
« Carte DCS » du Route Planner, servies par la Ready Room aux seuls membres
connectés : `GET /outils/tuiles/dcs/{cle}/{z}/{x}/{y}.png` (la route est écrite
dans `app/main.py`, à côté de `/outils/wing-config.json` ; elle ne fait que
vérifier la session puis appeler `servir`).

Pour chaque tuile, dans l'ordre :

1. le disque (`TILES_DIR`) : les archives de DCS Olympus extraites, en lecture
   seule ;
2. les tuiles gardées (`TILES_CACHE_DIR`) : celles qu'Olympus nous a déjà
   fournies ;
3. Olympus (`TILES_UPSTREAM`) : la tuile est demandée, servie, puis gardée.
   Une tuile qu'Olympus n'a pas est retenue absente 24 heures, en mémoire.

Lot « Le miroir des tuiles DCS se tient à jour » (`v1.0060`) : une tuile
gardée depuis plus de 30 jours (la date du fichier) est redemandée à Olympus
avec cette date (`If-Modified-Since`) ; `304` : elle reste, sa date est remise
au jour ; `200` : la nouvelle la remplace ; tout le reste : l'ancienne est
servie et la question ne se repose pas avant 24 heures. Les archives extraites
(`TILES_DIR`) ne sont jamais revalidées.

Lot « Les tuiles gardées lisibles » (`v1.0065`) : une tuile gardée est écrite
avec les droits 0644, pour que le serveur public des tuiles de la VM (nginx,
`/tuiles/`, R369) puisse la lire.

Aucun texte de l'URL n'entre tel quel dans un chemin ni dans l'URL d'Olympus :
la clé vient d'une liste fermée, `z`, `x` et `y` sont convertis en entiers
après validation. Jamais une erreur serveur sur le disque : une `OSError` se lit
« pas de fichier » ou « pas gardée ». Le module n'écrit aucune ligne de journal
par tuile, au plus un avertissement depuis le démarrage.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import tempfile
import time
from collections import OrderedDict
from email.utils import formatdate
from pathlib import Path

import httpx
from fastapi import Response

from app.config import settings

_logger = logging.getLogger(__name__)

# Les huit clés d'Olympus (casse exacte).
CLES = (
    "alt-syria",
    "alt-caucasus",
    "alt-nevada",
    "alt-marianaislands-modern",
    "alt-MarianaIslandsWWII",
    "alt-persiangulf",
    "alt-GermanyCW",
    "alt-Normandy",
)
_ZOOM_MAX = 18
_CHIFFRES = re.compile(r"[0-9]{1,6}")  # ASCII seulement : ni signe, ni espace

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_PNG_MAX_OCTETS = 2_000_000
_DELAI_CONNEXION_S = 3.0
_DELAI_TOTAL_S = 8.0
_USER_AGENT = "SquadronReadyRoom/1.0 (miroir de tuiles DCS)"

_LIBRE_MIN_OCTETS = 10 * 1024**3  # rien n'est gardé s'il reste moins de 10 Gio

# Lot « Les tuiles gardées lisibles » : les droits d'une tuile gardée (lisible
# par tous), pour que le serveur public des tuiles de la VM (nginx, `www-data`,
# R369) puisse la servir. Ni réglage, ni variable d'environnement.
_MODE_TUILE = 0o644

_CACHE_SERVIE = "private, max-age=604800"   # 7 jours au navigateur
_CACHE_ABSENTE = "private, max-age=86400"   # 24 heures
_NO_STORE = "no-store"

# Les tuiles qu'Olympus a déclarées absentes : (cle, z, x, y) -> instant
# (`time.monotonic`), 20 000 entrées au plus (la plus ancienne sort), valables
# 24 heures. En mémoire du processus, rien sur disque.
ABSENTES: "OrderedDict[tuple[str, int, int, int], float]" = OrderedDict()
_ABSENTES_MAX = 20_000
_ABSENTES_VALIDITE_S = 24 * 3600

# Lot « Le miroir des tuiles DCS se tient à jour » : l'âge (la date du fichier)
# à partir duquel une tuile gardée est redemandée à Olympus -- 30 jours, ni
# réglage ni variable d'environnement.
_REVALIDATION_S = 30 * 24 * 3600

# Les essais récents de revalidation restés sans réponse utile : (cle, z, x, y)
# -> instant (`time.monotonic`), 20 000 entrées au plus (la plus ancienne
# sort), valables 24 heures. En mémoire du processus, rien sur disque : un
# Olympus muet ne fait pas attendre chaque membre sur chaque tuile ancienne.
ESSAIS: "OrderedDict[tuple[str, int, int, int], float]" = OrderedDict()
_ESSAIS_MAX = 20_000
_ESSAIS_VALIDITE_S = 24 * 3600

# Le client d'Olympus, créé une fois (au premier besoin). Les tests y posent
# un client à transport simulé.
_CLIENT: httpx.AsyncClient | None = None

# L'avertissement unique : posé à la première garde impossible.
_AVERTI = False


def valider(cle: str, z: str, x: str, y: str) -> tuple[str, int, int, int] | None:
    """`(cle, z, x, y)` validés, ou `None`. La clé est l'une des huit de la
    liste ; `z`, `x`, `y` font de 1 à 6 chiffres ASCII ; `z` <= 18 ;
    `x` et `y` < 2^z."""
    if cle not in CLES:
        return None
    if not (_CHIFFRES.fullmatch(z) and _CHIFFRES.fullmatch(x) and _CHIFFRES.fullmatch(y)):
        return None
    zi, xi, yi = int(z), int(x), int(y)
    if zi > _ZOOM_MAX or xi >= 2**zi or yi >= 2**zi:
        return None
    return cle, zi, xi, yi


def _chemin(racine: str, cle: str, z: int, x: int, y: int) -> Path:
    # Seules les valeurs validées entrent ici.
    return Path(racine) / cle / str(z) / str(x) / f"{y}.png"


def _lire(chemin: Path) -> bytes | None:
    """Les octets du fichier, ou `None` : absent, pas un fichier, illisible."""
    try:
        if not chemin.is_file():
            return None
        return chemin.read_bytes()
    except OSError:
        return None


def _client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(_DELAI_TOTAL_S, connect=_DELAI_CONNEXION_S),
            follow_redirects=False,
        )
    return _CLIENT


async def _demander(
    cle: str, z: int, x: int, y: int, depuis: float | None = None
) -> tuple[str, bytes | None]:
    """Demande la tuile à Olympus. `("ok", octets)`, `("absente", None)` pour
    un `404`, `("erreur", None)` pour tout le reste (délai, réseau, redirection,
    autre statut, corps trop gros ou qui n'est pas un PNG). Ni cookie ni
    en-tête du membre : seule l'URL part.

    Lot « Le miroir des tuiles DCS se tient à jour » : avec `depuis` (la date
    du fichier gardé), la demande est conditionnelle (`If-Modified-Since`) et un
    `304` se lit `("inchangee", None)`. Sans `depuis`, un `304` reste une erreur."""
    url = f"{settings.TILES_UPSTREAM.rstrip('/')}/{cle}/{z}/{x}/{y}.png"
    entetes = {"User-Agent": _USER_AGENT}
    if depuis is not None:
        entetes["If-Modified-Since"] = formatdate(depuis, usegmt=True)

    async def _aller() -> tuple[str, bytes | None]:
        async with _client().stream("GET", url, headers=entetes) as reponse:
            if depuis is not None and reponse.status_code == 304:
                return "inchangee", None
            if reponse.status_code == 404:
                return "absente", None
            if reponse.status_code != 200:
                return "erreur", None
            corps = bytearray()
            async for morceau in reponse.aiter_bytes():
                corps += morceau
                if len(corps) > _PNG_MAX_OCTETS:
                    return "erreur", None
        if not corps.startswith(_PNG_SIGNATURE):
            return "erreur", None
        return "ok", bytes(corps)

    try:
        return await asyncio.wait_for(_aller(), timeout=_DELAI_TOTAL_S)
    except Exception:  # noqa: BLE001 -- tout incident d'Olympus se lit « erreur » (502)
        return "erreur", None


def _est_retenue(cle: str, z: int, x: int, y: int) -> bool:
    clef = (cle, z, x, y)
    instant = ABSENTES.get(clef)
    if instant is None:
        return False
    if time.monotonic() - instant >= _ABSENTES_VALIDITE_S:
        ABSENTES.pop(clef, None)
        return False
    return True


def _retenir(cle: str, z: int, x: int, y: int) -> None:
    clef = (cle, z, x, y)
    ABSENTES.pop(clef, None)
    while len(ABSENTES) >= _ABSENTES_MAX:
        ABSENTES.popitem(last=False)
    ABSENTES[clef] = time.monotonic()


def _essai_recent(cle: str, z: int, x: int, y: int) -> bool:
    clef = (cle, z, x, y)
    instant = ESSAIS.get(clef)
    if instant is None:
        return False
    if time.monotonic() - instant >= _ESSAIS_VALIDITE_S:
        ESSAIS.pop(clef, None)
        return False
    return True


def _noter_essai(cle: str, z: int, x: int, y: int) -> None:
    clef = (cle, z, x, y)
    ESSAIS.pop(clef, None)
    while len(ESSAIS) >= _ESSAIS_MAX:
        ESSAIS.popitem(last=False)
    ESSAIS[clef] = time.monotonic()


def _effacer_essai(cle: str, z: int, x: int, y: int) -> None:
    ESSAIS.pop((cle, z, x, y), None)


def _date_fichier(chemin: Path) -> float | None:
    """La date du fichier (`st_mtime`), ou `None` si elle ne se lit pas."""
    try:
        return chemin.stat().st_mtime
    except OSError:
        return None


def _rajeunir(chemin: Path) -> bool:
    """Remet la date du fichier à l'heure courante. `False` si le système de
    fichiers refuse."""
    try:
        os.utime(chemin, None)
        return True
    except OSError:
        return False


def _octets_libres(dossier: str) -> int:
    return shutil.disk_usage(dossier).free


def _avertir(motif: str) -> None:
    """Un seul avertissement depuis le démarrage, à la première garde impossible."""
    global _AVERTI
    if _AVERTI:
        return
    _AVERTI = True
    _logger.warning(
        "Tuiles DCS : une tuile d'Olympus n'a pas pu être gardée (%s) ; "
        "elle est servie sans être gardée.",
        motif,
    )


def _garder(cle: str, z: int, x: int, y: int, octets: bytes) -> bool:
    """Écrit la tuile sous `TILES_CACHE_DIR/<cle>/<z>/<x>/<y>.png`, par un
    fichier temporaire du même dossier puis `os.replace` : aucun fichier partiel
    n'est jamais servi, aucun temporaire ne reste. Le dossier racine doit exister
    et il doit rester au moins 10 Gio libres. `True` si la tuile est gardée."""
    racine = settings.TILES_CACHE_DIR
    temporaire = None
    try:
        if not os.path.isdir(racine):
            _avertir("dossier des tuiles gardées absent ou illisible")
            return False
        if _octets_libres(racine) < _LIBRE_MIN_OCTETS:
            _avertir("moins de 10 Gio libres")
            return False
        chemin = _chemin(racine, cle, z, x, y)
        chemin.parent.mkdir(parents=True, exist_ok=True)
        descripteur, temporaire = tempfile.mkstemp(
            dir=chemin.parent, prefix=".tuile-", suffix=".tmp"
        )
        # `mkstemp` crée en 0600 : les droits se posent ici, avant l'écriture,
        # sans dépendre du masque du processus.
        os.fchmod(descripteur, _MODE_TUILE)
        with os.fdopen(descripteur, "wb") as fichier:
            fichier.write(octets)
        os.replace(temporaire, chemin)
        temporaire = None
        return True
    except OSError as erreur:
        _avertir(f"{type(erreur).__name__}: {erreur}")
        return False
    finally:
        if temporaire is not None:
            try:
                os.unlink(temporaire)
            except OSError:
                pass


def _servie(octets: bytes, origine: str) -> Response:
    return Response(
        content=octets,
        media_type="image/png",
        headers={"Cache-Control": _CACHE_SERVIE, "X-Tuile": origine},
    )


def _absente() -> Response:
    return Response(
        status_code=404,
        headers={"Cache-Control": _CACHE_ABSENTE, "X-Tuile": "absente"},
    )


async def _servir_gardee(
    cle: str, z: int, x: int, y: int, chemin: Path, octets: bytes
) -> Response:
    """Une tuile gardée, lue. Plus jeune que 30 jours, ou déjà redemandée dans
    les 24 dernières heures : servie telle quelle. Sinon, demande conditionnelle
    à Olympus : `304` (date remise au jour), `200` PNG (la nouvelle remplace
    l'ancienne), tout le reste (l'ancienne est servie, rien ne change sur le
    disque, un essai récent est noté). Jamais une erreur serveur."""
    date = await asyncio.to_thread(_date_fichier, chemin)
    if date is None or time.time() - date < _REVALIDATION_S or _essai_recent(cle, z, x, y):
        return _servie(octets, "cache")

    etat, neuf = await _demander(cle, z, x, y, depuis=date)
    if etat == "inchangee":
        if await asyncio.to_thread(_rajeunir, chemin):
            _effacer_essai(cle, z, x, y)
        else:
            _noter_essai(cle, z, x, y)  # date non remise : pas de demande à chaque tuile
        return _servie(octets, "cache")
    if etat == "ok" and neuf is not None:
        await asyncio.to_thread(_garder, cle, z, x, y, neuf)
        _effacer_essai(cle, z, x, y)
        return _servie(neuf, "olympus")
    _noter_essai(cle, z, x, y)
    return _servie(octets, "cache")


async def servir(cle: str, z: str, x: str, y: str) -> Response:
    """La tuile demandée, une fois la session vérifiée par la route. Dans
    l'ordre : validation, disque, tuiles gardées, retenue absente, Olympus."""
    valide = valider(cle, z, x, y)
    if valide is None:
        return Response(status_code=404, headers={"Cache-Control": _NO_STORE})
    cle, zi, xi, yi = valide

    octets = await asyncio.to_thread(_lire, _chemin(settings.TILES_DIR, cle, zi, xi, yi))
    if octets is not None:
        return _servie(octets, "disque")

    gardee = _chemin(settings.TILES_CACHE_DIR, cle, zi, xi, yi)
    octets = await asyncio.to_thread(_lire, gardee)
    if octets is not None:
        return await _servir_gardee(cle, zi, xi, yi, gardee, octets)

    if _est_retenue(cle, zi, xi, yi):
        return _absente()

    etat, octets = await _demander(cle, zi, xi, yi)
    if etat == "absente":
        _retenir(cle, zi, xi, yi)
        return _absente()
    if etat != "ok" or octets is None:
        return Response(status_code=502, headers={"Cache-Control": _NO_STORE})
    await asyncio.to_thread(_garder, cle, zi, xi, yi, octets)
    return _servie(octets, "olympus")
