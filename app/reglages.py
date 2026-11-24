"""Lot « rr-env-epure » (v1.0105) -- les réglages de l'application gardés en base.

Le `.env` ne garde que ce qu'exige le premier démarrage (`app/config.py`, `_AMORCAGE`) ;
les quatorze réglages de `DEFINITIONS` vivent dans la table `reglage`, lus au démarrage par
`charger_au_demarrage` (qui les pose sur l'objet `settings`, le cache des réglages : l'App
tourne en un seul processus) et écrits par `ecrire`, que les routes de l'administrateur
appellent (`app/command/api.py`). Les secrets y sont chiffrés (Fernet, clé `CONFIG_KEY`),
jamais rendus en clair, leurs changements journalisés sans leur valeur.

CE MODULE NE LIT NI `app.config` NI `app.db` À SON IMPORT : les fonctions pures et le
contrôle du démarrage tournent sans eux (`python -B -m app.reglages`, appelé par
`entrypoint.sh` avant l'attente de la base). Les imports de l'App se font dans les
fonctions asynchrones."""
from __future__ import annotations

import logging
import os
import re
import sys
import zoneinfo
from datetime import datetime, timezone
from typing import Any, NamedTuple

from cryptography.fernet import Fernet

from app import taches

logger = logging.getLogger(__name__)

_BIGINT_MAX = 2**63 - 1
_LIGNE_REPRISE = "_reprise"


class CleAbsente(Exception):
    """`CONFIG_KEY` absente ou invalide : un secret ne s'écrit pas (l'appelant rend 409)."""


# --- 1. Les définitions ------------------------------------------------------------


class Definition(NamedTuple):
    cle: str
    groupe: str
    type: str  # texte | url | choix | booleen | entier | fuseau
    defaut: Any
    secret: bool
    bornes: tuple[int, int] | None = None
    choix: tuple[str, ...] | None = None
    motif: str | None = None


DEFINITIONS: tuple[Definition, ...] = (
    # Lot « rr-fuseau-reglage » (v1.0120) : le fuseau de l'escadre, lu à chaque usage (`recurrence.fuseau_reference`).
    Definition("REFERENCE_TZ", "fuseau", "fuseau", "Europe/Paris", False),
    Definition("ANTHROPIC_API_KEY", "recit", "texte", "", True),
    Definition("ANTHROPIC_MODEL", "recit", "texte", "", False),
    Definition("ANTHROPIC_EFFORT", "recit", "choix", "medium", False, choix=("low", "medium", "high", "xhigh", "max")),
    Definition("DISCORD_WEBHOOK_URL", "digest", "url", None, True),
    Definition("DISCORD_DIGEST_LOCALE", "digest", "choix", "en", False, choix=("fr", "en")),
    Definition("DISCORD_DIGEST_TOKEN", "digest", "texte", "", True),
    Definition("DISCORD_RSVP_ENABLED", "reponses", "booleen", False, False),
    Definition("DISCORD_BOT_TOKEN", "reponses", "texte", None, True),
    Definition("DISCORD_PUBLIC_KEY", "reponses", "texte", None, False, motif=r"^[0-9a-f]{64}$"),
    Definition("DISCORD_NOTIFY_CHANNEL_ID", "reponses", "texte", None, False, motif=r"^[0-9]{17,20}$"),
    Definition("DISCORD_RSVP_HORIZON_DAYS", "reponses", "entier", 14, False, bornes=(1, 120)),
    Definition("TILES_UPSTREAM", "tuiles", "url", "https://maps.dcsolympus.com/maps", False),
    Definition("WING_ID", "suites", "texte", "", False, motif=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"),
)
PAR_CLE: dict[str, Definition] = {d.cle: d for d in DEFINITIONS}

# Les dix-sept noms qui ne se lisent plus ni dans l'environnement ni dans le `.env`.
RETIREES: tuple[str, ...] = (
    "ALLOWED_ROLE_IDS",
    "EVENT_EDITOR_ROLE_IDS",
    "EVENT_EDITOR_IDS",
    "SQUADRON_ROLES",
    "DORMANT_SQUADRON_NAMES",
    "WING_TAG",
    "DISCORD_DIGEST_CLEANUP_IDS",
    "DISCORD_DIGEST_REFRESH_ENABLED",
    "DISCORD_DIGEST_REFRESH_DEBOUNCE_SECONDS",
    "SESSION_TTL_DAYS",
    "PRESENCE_SERIES_HORIZON_DAYS",
    "DEBRIEF_STORAGE_DIR",
    "CREST_STORAGE_DIR",
    "BACKUP_DIR",
    "SUITES_DIR",
    "TILES_DIR",
    "TILES_CACHE_DIR",
)

_LONGUEUR_MAX = 500
# Lot « rr-fuseau-reglage » (A1) : trois noms de `zoneinfo.available_timezones()` que le navigateur refuse (`Intl` lève
# `RangeError` sur `Factory` et `posixrules`) ou qui valent le fuseau du conteneur (`localtime`) : jamais admis.
FUSEAUX_REFUSES: frozenset[str] = frozenset({"Factory", "localtime", "posixrules"})
_VRAI = {"true", "1", "yes", "on", "oui"}
_FAUX = {"false", "0", "no", "off", "non"}


# --- 2. Les fonctions pures --------------------------------------------------------


def fuseaux_admis() -> set[str]:
    """Les noms de fuseau admis : `zoneinfo.available_timezones()` moins `FUSEAUX_REFUSES`."""
    return set(zoneinfo.available_timezones()) - FUSEAUX_REFUSES


def est_vide(brut: Any) -> bool:
    """`None`, ou une chaîne vide après `strip()`."""
    return brut is None or (isinstance(brut, str) and brut.strip() == "")


def convertir(definition: Definition, brut: Any) -> Any:
    """La valeur typée d'un brut non vide ; `ValueError` sur tout refus (brut vide
    compris). `texte` : chaîne, `strip()`, 500 caractères au plus, le motif s'il y en a un
    (la clé publique mise en minuscules avant) ; `url` : chaîne passée par `strip()`, sans blanc à l'intérieur, qui commence par
    `https://`, 500 au plus ; `choix` : chaîne en minuscules parmi `choix` ; `booleen` : un
    `bool` JSON ou une chaîne `true 1 yes on oui` / `false 0 no off non`, JAMAIS un entier ;
    `entier` : un `int` qui n'est pas un `bool`, ou une chaîne de chiffres, dans `bornes` ;
    `fuseau` (lot « rr-fuseau-reglage ») : une chaîne passée par `strip()`, exactement un nom de
    `zoneinfo.available_timezones()` hors `FUSEAUX_REFUSES` (la casse compte)."""
    if est_vide(brut):
        raise ValueError("valeur vide")
    t = definition.type
    if t == "texte":
        if not isinstance(brut, str):
            raise ValueError("une chaîne est attendue")
        v = brut.strip()
        if len(v) > _LONGUEUR_MAX:
            raise ValueError("valeur trop longue")
        if definition.motif is not None:
            if definition.cle == "DISCORD_PUBLIC_KEY":
                v = v.lower()
            if not re.fullmatch(definition.motif, v):
                raise ValueError("valeur hors du motif")
        return v
    if t == "url":
        if not isinstance(brut, str):
            raise ValueError("une chaîne est attendue")
        v = brut.strip()
        if re.search(r"\s", v) or not v.startswith("https://") or len(v) > _LONGUEUR_MAX:
            raise ValueError("URL https:// sans blanc, 500 caractères au plus")
        return v
    if t == "fuseau":
        if not isinstance(brut, str):
            raise ValueError("une chaîne est attendue")
        v = brut.strip()
        if v not in fuseaux_admis():
            raise ValueError("fuseau inconnu")
        return v
    if t == "choix":
        if not isinstance(brut, str):
            raise ValueError("une chaîne est attendue")
        v = brut.strip().lower()
        if v not in (definition.choix or ()):
            raise ValueError("choix inconnu")
        return v
    if t == "booleen":
        if isinstance(brut, bool):
            return brut
        if isinstance(brut, str):
            v = brut.strip().lower()
            if v in _VRAI:
                return True
            if v in _FAUX:
                return False
        raise ValueError("booléen attendu")
    if t == "entier":
        if isinstance(brut, bool):
            raise ValueError("entier attendu")
        if isinstance(brut, int):
            n = brut
        elif isinstance(brut, str) and re.fullmatch(r"[0-9]+", brut.strip()):
            n = int(brut.strip())
        else:
            raise ValueError("entier attendu")
        bas, haut = definition.bornes or (n, n)
        if not bas <= n <= haut:
            raise ValueError("entier hors des bornes")
        return n
    raise ValueError("type inconnu")


def en_texte(definition: Definition, valeur: Any) -> str:
    """Le texte gardé en base : `true`/`false`, l'entier en décimal, sinon la chaîne."""
    if isinstance(valeur, bool):
        return "true" if valeur else "false"
    if isinstance(valeur, int):
        return str(valeur)
    return str(valeur)


def cle_valide(cle: Any) -> bool:
    """Vrai si `Fernet` accepte cette clé."""
    try:
        Fernet(cle)
    except Exception:
        return False
    return True


def chiffrer(cle: str, clair: str) -> str:
    """Le jeton Fernet du clair, en texte."""
    return Fernet(cle).encrypt(clair.encode("utf-8")).decode("ascii")


def dechiffrer(cle: str, jeton: str) -> str | None:
    """Le clair d'un jeton, ou `None` (clé ou jeton invalides)."""
    try:
        return Fernet(cle).decrypt(jeton.encode("ascii")).decode("utf-8")
    except Exception:
        return None


def lire_env(definition: Definition, environ) -> Any:
    """La valeur convertie de `environ[cle]`, ou `None` (absente, vide, invalide)."""
    brut = environ.get(definition.cle)
    if est_vide(brut):
        return None
    try:
        return convertir(definition, brut)
    except ValueError:
        return None


def element(definition: Definition, valeur: Any, rempli: bool, lisible: bool, maj_le, maj_par) -> dict:
    """L'élément que servent les routes. Pour un secret, `valeur` et `defaut` valent `None` ;
    un réglage en clair est toujours `lisible`."""
    e = {
        "cle": definition.cle,
        "groupe": definition.groupe,
        "type": definition.type,
        "secret": definition.secret,
        "valeur": None if definition.secret else valeur,
        "defaut": None if definition.secret else definition.defaut,
        "rempli": bool(rempli),
        "lisible": bool(lisible) if definition.secret else True,
        "maj_le": maj_le.isoformat() if maj_le is not None else None,
        "maj_par": str(maj_par) if maj_par is not None else None,
    }
    if definition.type == "entier":
        e["bornes"] = list(definition.bornes)
    if definition.type == "choix":
        e["choix"] = list(definition.choix)
    if definition.type == "fuseau":
        e["fuseaux"] = sorted(fuseaux_admis())
    return e


def controle_au_demarrage(environ) -> str | None:
    """La raison d'un refus de démarrer, ou `None` : `CONFIG_KEY` absente ou refusée par
    `cle_valide`, puis `ADMIN_IDS` sans aucun identifiant fait de chiffres."""
    if not cle_valide(environ.get("CONFIG_KEY", "")):
        return "CONFIG_KEY missing or invalid"
    identifiants = [i.strip() for i in environ.get("ADMIN_IDS", "").split(",")]
    if not any(re.fullmatch(r"[0-9]+", i) for i in identifiants):
        return "ADMIN_IDS empty: at least one founding administrator"
    return None


def _identifiants(brut: str | None) -> list[str]:
    """Les identifiants faits de chiffres d'un CSV, sans doublon, dans l'ordre."""
    vus: list[str] = []
    for i in (brut or "").split(","):
        i = i.strip()
        if re.fullmatch(r"[0-9]+", i) and int(i) <= _BIGINT_MAX and i not in vus:
            vus.append(i)
    return vus


# --- 3. Le chargement au démarrage -------------------------------------------------


async def _reprise(db, cle: str) -> None:
    """La reprise unique, dans la transaction de `db` (le commit est à l'appelant)."""
    from sqlalchemy import func, select

    from app import capabilities
    from app.models import AccountCapability, Profile, Reglage, RoleCapability

    existantes = set((await db.execute(select(Reglage.cle))).scalars().all())
    for d in DEFINITIONS:
        if d.cle in existantes:
            continue
        valeur = lire_env(d, os.environ)
        if valeur is None:
            if not est_vide(os.environ.get(d.cle)):
                logger.warning("Réglage du .env invalide, non repris : %s", d.cle)
            continue
        texte = en_texte(d, valeur)
        db.add(Reglage(cle=d.cle, valeur=chiffrer(cle, texte) if d.secret else texte, maj_par=None))
        logger.info("Réglage repris du .env : %s", d.cle)

    # L'accès à l'application : la base qui parle n'est pas touchée.
    deja = (
        await db.execute(
            select(func.count()).select_from(RoleCapability).where(RoleCapability.capability == "app.access")
        )
    ).scalar_one()
    if not deja:
        for role_id in _identifiants(os.environ.get("ALLOWED_ROLE_IDS")):
            db.add(RoleCapability(role_id=role_id, capability="app.access"))

    # La création d'évènements : idem, la base qui parle n'est pas touchée.
    if not await capabilities._event_create_base_authoritative(db):
        for role_id in _identifiants(os.environ.get("EVENT_EDITOR_ROLE_IDS")):
            db.add(RoleCapability(role_id=role_id, capability="event.create"))
        voulus = [int(i) for i in _identifiants(os.environ.get("EVENT_EDITOR_IDS"))]
        if voulus:
            presents = (await db.execute(select(Profile.id).where(Profile.id.in_(voulus)))).scalars().all()
            for profile_id in sorted(presents):
                db.add(AccountCapability(profile_id=profile_id, capability="event.create", granted_by=None))

    db.add(Reglage(cle=_LIGNE_REPRISE, valeur=datetime.now(timezone.utc).isoformat()))


def _avertir(settings, reprise_faite: bool) -> None:
    """Les avertissements de chaque démarrage : des noms seulement, jamais une valeur."""
    retirees = [n for n in RETIREES if n in os.environ]
    if retirees:
        logger.warning("Variables retirées du .env, sans effet : %s", ", ".join(retirees))
    if reprise_faite:
        encore = [d.cle for d in DEFINITIONS if d.cle in os.environ]
        if encore:
            logger.warning("Réglages en base, encore au .env, sans effet : %s", ", ".join(encore))
    if settings.DISCORD_RSVP_ENABLED and not settings.rsvp_bot_ready:
        manquantes = [
            nom
            for nom, valeur in (
                ("DISCORD_BOT_TOKEN", settings.DISCORD_BOT_TOKEN),
                ("DISCORD_NOTIFY_CHANNEL_ID", settings.DISCORD_NOTIFY_CHANNEL_ID),
            )
            if not valeur
        ]
        logger.warning(
            "Phase 2b (RSVP Discord) : DISCORD_RSVP_ENABLED actif mais réglage(s) "
            "manquant(s) (%s) -- le bot RSVP reste inactif (no-op).",
            ", ".join(manquantes),
        )


async def charger_au_demarrage() -> None:
    """Appelée en tête du `lifespan` (`app/main.py`), attendue avant les tâches de fond ; sa
    propre session ; jamais fatale (une erreur se journalise, l'App sert avec ses défauts).
    Dans l'ordre : la clé, la reprise unique du `.env` (seulement avec une clé valide), la
    lecture des réglages et des administrateurs nommés sur `settings`, les avertissements."""
    try:
        from sqlalchemy import select

        from app import auth
        from app.config import settings
        from app.db import AsyncSessionLocal
        from app.models import AccountCapability, Reglage

        cle = settings.CONFIG_KEY
        cle_ok = cle_valide(cle)
        if not cle_ok:
            logger.error(
                "CONFIG_KEY absente ou invalide : les secrets des réglages ne sont ni lus ni écrits"
            )
        async with AsyncSessionLocal() as db:
            if cle_ok:
                # La reprise a son propre `try` : en échec, `rollback`, un journal par le type de
                # l'exception seul (la trace de SQLAlchemy porterait les paramètres, donc des
                # jetons), sa marque n'est pas posée -- elle se retente au démarrage suivant --
                # et la lecture se fait quand même.
                try:
                    if await db.get(Reglage, _LIGNE_REPRISE) is None:
                        await _reprise(db, cle)
                        await db.commit()
                        auth.invalidate_app_access_cache()
                except Exception as e:
                    await db.rollback()
                    logger.error(
                        "Réglages : reprise du .env en échec, retentée au prochain démarrage : %s",
                        type(e).__name__,
                    )
            lignes = {r.cle: r for r in (await db.execute(select(Reglage))).scalars().all()}
            nommes = (
                await db.execute(
                    select(AccountCapability.profile_id).where(AccountCapability.capability == "admin")
                )
            ).scalars().all()
        for d in DEFINITIONS:
            ligne = lignes.get(d.cle)
            if ligne is None:
                continue
            if d.secret:
                clair = dechiffrer(cle, ligne.valeur) if cle_ok else None
                if clair is None:
                    continue
                setattr(settings, d.cle, clair)
                continue
            try:
                setattr(settings, d.cle, convertir(d, ligne.valeur))
            except ValueError:
                logger.warning("Réglage en base illisible, le défaut est gardé : %s", d.cle)
                setattr(settings, d.cle, d.defaut)
        settings.ADMINS_NOMMES = frozenset(str(p) for p in nommes)
        _avertir(settings, _LIGNE_REPRISE in lignes)
    except Exception as e:
        # Par le type seul, jamais `logger.exception` : la trace de SQLAlchemy porterait des paramètres.
        logger.error("Réglages : erreur non bloquante au chargement (lifespan) : %s", type(e).__name__)


# --- 4. L'écriture -----------------------------------------------------------------

_CLES_DISCORD_SURFACE = {
    "DISCORD_RSVP_ENABLED",
    "DISCORD_BOT_TOKEN",
    "DISCORD_NOTIFY_CHANNEL_ID",
    "DISCORD_RSVP_HORIZON_DAYS",
    "DISCORD_WEBHOOK_URL",
}


async def _reconcilier_surface() -> None:
    """La surface Discord reconciliée sur sa propre session ; jamais fatale."""
    try:
        from app import discord_rsvp
        from app.db import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await discord_rsvp.reconcile_discord_surface(db)
    except Exception:
        logger.exception("Réglages : réconciliation Discord en erreur non bloquante")


async def _enregistrer_commande() -> None:
    """La commande `/readyroom` redéclarée ; jamais fatale."""
    try:
        from app import connexion_secours

        await connexion_secours.enregistrer_commande()
    except Exception:
        logger.exception("Réglages : commande /readyroom en erreur non bloquante")


async def ecrire(db, definition: Definition, brut: Any, user: dict) -> None:
    """Écrit un réglage. Vide (`est_vide`) : la ligne s'efface et `settings` reprend le
    défaut. Sinon `convertir` (`ValueError` : l'appelant rend 422) ; un secret sans clé
    valide lève `CleAbsente` (l'appelant rend 409) -- en vider un reste permis sans clé. La
    ligne s'écrit (`maj_le` à l'heure de la base, `maj_par` l'agissant), `reglage.edit` se
    consigne -- un secret s'y écrit `rempli`, `vide` ou `remplacé`, jamais sa valeur ni son jeton --, le
    `commit`, puis le `setattr` ; ensuite, sans attendre, la réconciliation Discord et la
    commande `/readyroom` quand le réglage les touche."""
    from sqlalchemy import delete
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.sql import func

    from app.command import journal
    from app.config import settings
    from app.models import Reglage

    vide = est_vide(brut)
    valeur = None if vide else convertir(definition, brut)
    if not vide and definition.secret and not cle_valide(settings.CONFIG_KEY):
        raise CleAbsente()

    ligne = await db.get(Reglage, definition.cle)
    if definition.secret:
        avant = "rempli" if ligne is not None else "vide"
        # Un secret rempli qui reçoit une nouvelle valeur : `remplacé` (le changement laisse une ligne).
        apres = "vide" if vide else ("remplacé" if ligne is not None else "rempli")
    else:
        avant = ligne.valeur if ligne is not None else None
        apres = None if vide else en_texte(definition, valeur)

    if vide:
        await db.execute(delete(Reglage).where(Reglage.cle == definition.cle))
    else:
        texte = en_texte(definition, valeur)
        if definition.secret:
            texte = chiffrer(settings.CONFIG_KEY, texte)
        poser = {"valeur": texte, "maj_le": func.now(), "maj_par": int(user["id"])}
        await db.execute(
            pg_insert(Reglage)
            .values(cle=definition.cle, **poser)
            .on_conflict_do_update(index_elements=[Reglage.cle], set_=poser)
        )
    journal.consigner(
        db, user, "reglage.edit", objet=definition.cle,
        lignes=journal.ecarts({"valeur": avant}, {"valeur": apres}),
    )
    if ligne is not None and not vide:
        # Écrite par le noyau, pas par l'objet : la relecture de l'élément doit être fraîche (une
        # ligne effacée, elle, sort déjà de la session par le `delete`).
        db.expire(ligne)
    await db.commit()
    setattr(settings, definition.cle, definition.defaut if vide else valeur)

    if definition.cle in _CLES_DISCORD_SURFACE:
        taches.lancer(_reconcilier_surface())
    if (
        definition.cle in ("DISCORD_BOT_TOKEN", "DISCORD_PUBLIC_KEY")
        and settings.bot_token_present
        and settings.DISCORD_PUBLIC_KEY
    ):
        taches.lancer(_enregistrer_commande())


# --- 5. La liste des modèles --------------------------------------------------------

# Lot « rr-centre-config-modele-effort » : les tests y posent un `httpx.MockTransport`.
_TRANSPORT = None

_NIVEAUX_EFFORT = ("low", "medium", "high", "xhigh", "max")
# Lot « rr-centre-config-modele-effort » (v1.0109) : la version de l'API de CET appel seul (celle de l'exemple de la
# référence `GET /v1/models`) ; le Récit garde la sienne (`app/llm.py`).
_VERSION_API_MODELES = "2026-10-21"


def _indisponible(detail: str, cle: str) -> dict:
    """La réponse `erreur` : `detail` (300 caractères au plus), la clé de l'API masquée par `***` si elle y figure ;
    le même texte va au journal, rien d'autre."""
    if cle:
        detail = detail.replace(cle, "***")
    detail = detail[:300]
    logger.warning("Liste des modèles : %s", detail)
    return {"disponible": False, "raison": "erreur", "detail": detail, "modeles": []}


async def lister_modeles() -> dict:
    """Les modèles actifs d'Anthropic qui conviennent au Récit, pour la page Configuration.
    Sans clé de l'API : `raison` `cle`, sans appel. Sinon un `GET /v1/models` (`limit=100`, `has_more`
    ignoré ; `anthropic-version` `_VERSION_API_MODELES`) ; toute exception, un statut autre que 200 ou
    un corps sans liste `data` : `raison` `erreur` et un `detail` (chaîne, 300 caractères au plus) :
    `HTTP <statut>` suivi, si le corps JSON porte `error.type` et/ou `error.message`, de ` · <type>` et/ou
    ` · <message>` ; le nom du type de l'exception ; ou `réponse sans liste`. La clé n'est jamais dans
    `detail` (remplacée par `***`) ; le journal écrit ce même `detail`, ni en-tête ni corps. Un modèle est
    gardé s'il accepte l'effort (`capabilities.effort.supported`), si son plafond de sortie (`max_tokens`)
    est absent ou couvre `_MAX_TOKENS` du Récit, et si son `lifecycle`, quand il est présent, est
    `active` ; il porte les niveaux d'effort qu'il accepte, de `low` à `max`. Un administrateur reçoit
    toujours une réponse, jamais une erreur."""
    import httpx

    from app.config import settings
    from app.llm import _MAX_TOKENS

    cle = settings.ANTHROPIC_API_KEY
    if est_vide(cle):
        return {"disponible": False, "raison": "cle", "modeles": []}
    try:
        async with httpx.AsyncClient(timeout=10.0, transport=_TRANSPORT) as client:
            reponse = await client.get(
                "https://api.anthropic.com/v1/models",
                params={"limit": 100},
                headers={"x-api-key": cle, "anthropic-version": _VERSION_API_MODELES},
            )
        if reponse.status_code != 200:
            detail = f"HTTP {reponse.status_code}"
            try:
                erreur = reponse.json().get("error")
                if isinstance(erreur, dict):
                    for champ in ("type", "message"):
                        if isinstance(erreur.get(champ), str) and erreur[champ]:
                            detail += " · " + erreur[champ]
            except Exception:
                pass
            return _indisponible(detail, cle)
        corps = reponse.json()
        donnees = corps.get("data") if isinstance(corps, dict) else None
        if not isinstance(donnees, list):
            return _indisponible("réponse sans liste", cle)
        modeles = []
        for m in donnees:
            if not isinstance(m, dict) or not isinstance(m.get("id"), str) or not m["id"]:
                continue
            if m.get("lifecycle") is not None and m.get("lifecycle") != "active":
                continue
            capacites = m.get("capabilities")
            effort = capacites.get("effort") if isinstance(capacites, dict) else None
            if not isinstance(effort, dict) or effort.get("supported") is not True:
                continue
            plafond = m.get("max_tokens")
            if plafond is not None and (
                isinstance(plafond, bool) or not isinstance(plafond, int) or plafond < _MAX_TOKENS
            ):
                continue
            nom = m.get("display_name")
            modeles.append({
                "id": m["id"],
                "nom": nom if isinstance(nom, str) and nom.strip() else m["id"],
                "efforts": [
                    n for n in _NIVEAUX_EFFORT
                    if isinstance(effort.get(n), dict) and effort[n].get("supported") is True
                ],
            })
        return {"disponible": True, "raison": None, "modeles": modeles}
    except Exception as e:
        return _indisponible(type(e).__name__, cle)


# --- 6. Les dossiers branchés -------------------------------------------------------

# Lot « rr-centre-config-montages » (v1.0124) : les trois dossiers que Docker branche au démarrage (lignes `*_HOST_DIR` du
# `.env`, lues par Docker et jamais par l'App), montrés en lecture seule à la page Configuration du Centre.
DOSSIERS = (
    ("suites", "SUITES_HOST_DIR", "SUITES_DIR"),
    ("tuiles", "TILES_HOST_DIR", "TILES_DIR"),
    ("tuiles_gardees", "TILES_CACHE_HOST_DIR", "TILES_CACHE_DIR"),
)
PLAFOND_FICHIERS = 100_000


def compter_fichiers(chemin: str, plafond: int = PLAFOND_FICHIERS) -> int | None:
    """Le nombre de fichiers ordinaires de toute l'arborescence de `chemin` ; `None` si ce n'est pas un dossier.
    Aucun lien symbolique n'est ni compté ni parcouru ; le parcours s'arrête à `plafond` (rendu alors tel quel) ;
    un sous-dossier illisible est sauté."""
    if not os.path.isdir(chemin):
        return None
    n = 0
    a_voir = [chemin]
    while a_voir:
        try:
            with os.scandir(a_voir.pop()) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            a_voir.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            n += 1
                            if n >= plafond:
                                return plafond
                    except OSError:
                        continue
        except OSError:
            continue
    return n


def etat_dossiers(settings) -> list[dict]:
    """L'état des trois dossiers de `DOSSIERS`, dans l'ordre : chemin vu par le conteneur, présent ou non, nombre de
    fichiers (`None` si absent), `plafond` vrai si le compte a atteint `PLAFOND_FICHIERS`. `settings` vient de l'appelant."""
    etat = []
    for ident, variable, attribut in DOSSIERS:
        chemin = getattr(settings, attribut)
        n = compter_fichiers(chemin)
        etat.append({
            "id": ident,
            "variable": variable,
            "chemin": chemin,
            "present": n is not None,
            "fichiers": n,
            "plafond": n is not None and n >= PLAFOND_FICHIERS,
        })
    return etat


if __name__ == "__main__":
    _raison = controle_au_demarrage(os.environ)
    if _raison is not None:
        print(_raison, file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
