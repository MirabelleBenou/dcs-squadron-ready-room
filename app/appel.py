"""L'appel -- l'effectif suit Discord (lot « L'appel », R183 à R185).

Une passe du bot REST déjà en place (celui des RSVP et de l'écran Droits,
`discord_rsvp._bot_request`) : pour chaque profil,
`GET /guilds/{guild}/members/{id}`, la lecture d'un membre par son
identifiant -- sans intent privilégié. Au démarrage (après
`DELAI_DEMARRAGE_S`), puis toutes les `INTERVALLE_S` secondes -- par
intervalle, jamais à heure fixe : l'horloge de la VM n'est pas réglée --, et
à la demande, par le bouton « Faire l'appel » de l'écran Membres du Centre.

L'appel LIT TOUT avant d'écrire quoi que ce soit : une réponse inattendue ou
un Discord injoignable, et rien n'est écrit -- le compte rendu porte
`erreur`. Seuls « membre inconnu » (10007) et « compte supprimé » (10013)
valent départ. Puis chaque profil passe par `squadron.appliquer_roles`, la
fonction unique qu'appellent aussi la connexion OAuth et le clic RSVP.

La règle (R183) : le rôle d'une escadrille active place dans cette
escadrille ; sinon le droit de connexion place en Free Agent ; sinon le
profil sort de l'effectif, archivé (R184). Le droit de connexion est le
prédicat de la porte (`auth.callback`) : présent sur le serveur, et
administrateur ou porteur d'un rôle de l'écran Droits. Le rôle Free Agent
n'est pas lu -- le repli le couvre.

Lot « L'effectif complet » (R195) : avant d'écrire, l'appel lit aussi la
liste du serveur (`lister_serveur`, `GET /guilds/{guild}/members`) -- sa
seule lecture qui demande l'intent « Server Members ». Tout membre sans
profil qui passe R183 reçoit un profil, nommé comme à la connexion et au clic
RSVP, puis passe par `appliquer_roles`. Un départ reste une lecture
10007/10013 par identifiant, jamais une absence de la liste ; si la liste
manque ou se contredit, personne n'entre, le reste de l'appel se fait, et le
compte rendu porte `liste`.

Les noms et les avatars des profils existants ne sont pas touchés : le
moteur rattache les vols par le nom. Déploiement mono-processus (`entrypoint.sh`, un seul uvicorn) :
le verrou et le dernier compte rendu vivent en mémoire de processus, comme le
cache de la porte (`auth._app_access_cache`).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app import relances
from app.auth import _app_access_role_ids
from app.config import settings
from app.db import AsyncSessionLocal
from app.discord_rsvp import _bot_request
from app.models import Profile, Squadron, SquadronMembership
from app.squadron import _resolve_squadron_id, appliquer_roles

logger = logging.getLogger(__name__)

DELAI_DEMARRAGE_S = 60
INTERVALLE_S = 24 * 3600
PAUSE_S = 0.25
_DEPARTS = (10007, 10013)  # membre inconnu, compte supprimé
PAGE = 1000  # lot « L'effectif complet » : le maximum de Discord par page
PAGES_MAX = 50

HORS = "hors"
FA = "FA"

_verrou = asyncio.Lock()
_dernier: Optional[dict] = None


class AppelInterrompu(Exception):
    """Une réponse que l'appel ne sait pas lire : il n'écrit rien."""


def dernier_appel() -> Optional[dict]:
    """Le compte rendu du dernier appel, None s'il n'y en a pas encore eu."""
    return _dernier


def lecture(statut: Optional[int], corps) -> Optional[set[str]]:
    """Ce qu'une réponse de Discord dit d'un membre. Pure. `statut` None :
    Discord injoignable. 200 -> ses rôles ; 404 « membre inconnu » ou
    « compte supprimé » -> None, il est parti ; tout le reste lève
    `AppelInterrompu`."""
    if statut is None:
        raise AppelInterrompu("Discord injoignable")
    if statut == 200 and isinstance(corps, dict):
        return {str(r) for r in corps.get("roles", [])}
    if statut == 404 and isinstance(corps, dict) and corps.get("code") in _DEPARTS:
        return None
    raise AppelInterrompu(f"réponse HTTP {statut}")


def peut_entrer(profile_id: int, roles: Optional[set[str]], porte: set[str]) -> bool:
    """Le prédicat de la porte, celui d'`auth.callback`. Pure : présent sur
    le serveur (`roles` non None), et administrateur ou porteur d'un rôle de
    l'écran Droits (`porte`)."""
    if roles is None:
        return False
    return str(profile_id) in settings.admin_ids_set or bool(roles & porte)


async def collecter(
    ids: Iterable[int],
    lire: Callable[[int], Awaitable[Optional[set[str]]]],
    pause: float = PAUSE_S,
) -> dict:
    """Lit chaque membre, dans l'ordre, sans rien écrire. `AppelInterrompu`
    remonte telle quelle : l'appelant n'applique alors rien."""
    lus: dict = {}
    for pid in ids:
        lus[pid] = await lire(pid)
        if pause:
            await asyncio.sleep(pause)
    return lus


def compte_rendu(avant: dict, apres: dict, noms: dict) -> dict:
    """Ce qui a changé, d'une case à l'autre. Pure. Une case vaut
    l'identifiant de l'escadrille active, `FA` ou `HORS`. Les destinations
    d'escadrille d'abord, par identifiant ; les passages en Free Agent
    ensuite ; les noms par
    ordre alphabétique, sans tenir compte de la casse.

    Lot « L'effectif complet » (R195) : un profil absent d'`avant` est une
    arrivée -- groupée par destination comme un changement de case."""
    def tri(ids):
        return sorted((noms[i] for i in ids), key=str.casefold)

    def groupes(par_case):
        return [
            {"vers": None if v == FA else v, "noms": tri(ids)}
            for v, ids in sorted(par_case.items(), key=lambda kv: (kv[0] == FA, kv[0]))
        ]
    sortent = [i for i in apres if apres[i] == HORS and avant.get(i) not in (HORS, None)]
    reviennent = [i for i in apres if avant.get(i) == HORS and apres[i] != HORS]
    vers: dict = {}
    arrivent: dict = {}
    for i, b in apres.items():
        a = avant.get(i)
        if a is None:
            if b != HORS:
                arrivent.setdefault(b, []).append(i)
        elif a != b and HORS not in (a, b):
            vers.setdefault(b, []).append(i)
    return {
        "sortent": tri(sortent),
        "bougent": groupes(vers),
        "reviennent": tri(reviennent),
        "arrivent": groupes(arrivent),
    }


def liste_incomplete(listes: set, avant: dict, lus: dict) -> bool:
    """Lot « L'effectif complet » (R195). Pure. La liste du serveur se
    contredit si un profil de l'effectif (case autre que `HORS`) en est
    absent alors que sa lecture directe le dit présent (`lus` non None)."""
    return any(c != HORS and pid not in listes and lus.get(pid) is not None for pid, c in avant.items())


async def _cases(db) -> tuple[dict, dict]:
    """La case de chaque profil, et son nom : l'identifiant de son escadrille
    active, `FA`, ou `HORS` s'il est archivé -- la lecture de l'organigramme."""
    ouvertes = dict((await db.execute(
        select(SquadronMembership.profile_id, Squadron.designation)
        .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .where(SquadronMembership.ended_at.is_(None), Squadron.status == "actif")
    )).all())
    cases, noms = {}, {}
    for p in (await db.execute(select(Profile))).scalars().all():
        cases[p.id] = HORS if p.archived_at is not None else ouvertes.get(p.id, FA)
        noms[p.id] = p.global_name or p.username
    return cases, noms


async def _lire_membre(profile_id: int) -> Optional[set[str]]:
    reponse = await _bot_request("GET", f"/guilds/{settings.DISCORD_GUILD_ID}/members/{profile_id}")
    if reponse is None:
        return lecture(None, None)
    try:
        corps = reponse.json()
    except ValueError:
        corps = None
    return lecture(reponse.status_code, corps)


async def lister_serveur() -> tuple[Optional[list], Optional[str]]:
    """Lot « L'effectif complet » (R195) : tous les membres du serveur, page
    par page -- la seule lecture de l'appel qui demande l'intent « Server
    Members ». Rend `(membres, None)` ou `(None, motif)`, jamais d'exception.
    Une liste vide est un motif, jamais un serveur vide : le bot en est
    membre."""
    membres: list = []
    apres = "0"
    for _ in range(PAGES_MAX):
        reponse = await _bot_request(
            "GET", f"/guilds/{settings.DISCORD_GUILD_ID}/members?limit={PAGE}&after={apres}"
        )
        if reponse is None:
            return None, "Discord injoignable"
        if reponse.status_code != 200:
            return None, f"HTTP {reponse.status_code}"
        try:
            page = reponse.json()
        except ValueError:
            page = None
        if not isinstance(page, list):
            return None, "réponse illisible"
        membres += page
        if len(page) < PAGE:
            break
        apres = str(max(int(m["user"]["id"]) for m in page))
    else:
        return None, f"plus de {PAGES_MAX} pages"
    if not membres:
        return None, "liste vide"
    return membres, None


async def _entrants(db, avant: dict, lus: dict, porte: set[str]) -> tuple[list, Optional[str]]:
    """Lot « L'effectif complet » (R195) : les membres du serveur sans
    profil qui passent R183 -- le rôle d'une escadrille active, ou le droit
    d'entrée --, avec leurs rôles. Lecture seule. Rend `(entrants, motif)` :
    si la liste manque ou se contredit, personne n'entre et `motif` dit
    pourquoi. Les bots n'entrent jamais."""
    membres, motif = await lister_serveur()
    if motif:
        return [], motif
    humains = [m for m in membres if not (m.get("user") or {}).get("bot")]
    if liste_incomplete({int(m["user"]["id"]) for m in humains}, avant, lus):
        return [], "liste incomplète"
    entrants = []
    for m in humains:
        uid = int(m["user"]["id"])
        if uid in avant:
            continue
        roles = {str(r) for r in m.get("roles", [])}
        if peut_entrer(uid, roles, porte) or await _resolve_squadron_id(db, roles) is not None:
            entrants.append((m, roles))
    return entrants, None


async def _creer_profil(db, membre: dict, roles: set[str]) -> int:
    """Lot « L'effectif complet » (R195) : le profil d'un membre jamais vu,
    nommé comme à la connexion et au clic RSVP -- pseudo du serveur, sinon
    nom global, sinon identifiant --, avec son avatar et sans
    `last_login_at`. Un profil né entre-temps n'est jamais réécrit (R185)."""
    u = membre["user"]
    await db.execute(
        pg_insert(Profile)
        .values(
            id=int(u["id"]),
            username=u["username"],
            global_name=membre.get("nick") or u.get("global_name") or u["username"],
            avatar_hash=u.get("avatar"),
            roles_snapshot=sorted(roles),
        )
        .on_conflict_do_nothing(index_elements=[Profile.id])
    )
    await db.commit()
    return int(u["id"])


async def _appel(source: str) -> dict:
    cr = {"at": datetime.now(timezone.utc).isoformat(), "source": source, "lus": 0,
          "sortent": [], "bougent": [], "reviennent": [], "arrivent": [], "liste": None,
          "erreur": None}
    if not settings.DISCORD_BOT_TOKEN:
        cr["erreur"] = "pas de jeton bot"
        return cr
    async with AsyncSessionLocal() as db:
        avant, _noms = await _cases(db)
        try:
            lus = await collecter(sorted(avant), _lire_membre)
        except AppelInterrompu as exc:
            cr["erreur"] = str(exc)
            return cr
        porte = await _app_access_role_ids(db)
        entrants, cr["liste"] = await _entrants(db, avant, lus, porte)
        for pid, roles in lus.items():
            await appliquer_roles(db, pid, roles or set(), peut_entrer(pid, roles, porte))
        for membre, roles in entrants:
            uid = await _creer_profil(db, membre, roles)
            await appliquer_roles(db, uid, roles, peut_entrer(uid, roles, porte))
        apres, noms = await _cases(db)
    cr["lus"] = len(lus)
    cr.update(compte_rendu(avant, apres, noms))
    return cr


async def faire_appel(source: str) -> dict:
    """Fait l'appel, un seul à la fois. Un appel déjà en cours n'en lance pas
    un second : on attend sa fin et l'on rend son compte rendu."""
    global _dernier
    if _verrou.locked():
        async with _verrou:
            return _dernier
    async with _verrou:
        _dernier = await _appel(source)
        # Lot « Les relances » (R3) : la passe tourne à la fin de chaque appel
        # réussi, sous le même verrou, et se termine avant que la main soit
        # rendue. Une erreur de la passe se journalise : elle ne change ni le
        # compte rendu de l'appel, ni son issue.
        if not _dernier.get("erreur"):
            try:
                bilan = await relances.passe()
                logger.info("Relances (%s) : %s", source, bilan)
            except Exception:
                logger.exception("Relances : erreur de la passe")
    logger.info("Appel (%s) : %s", source, _dernier)
    return _dernier


async def passe_apres_reglage() -> None:
    """Lot « Les relances nominatives » (R5). Après chaque enregistrement
    réussi de `PUT /command/rights/relances`, la passe des relances tourne SOUS
    le verrou de l'appel -- jamais en même temps qu'un appel ni qu'une autre
    passe -- et se termine avant que la route réponde. Un destinataire ajouté
    reçoit ainsi aussitôt la liste en cours ; c'est la règle R4 des relances
    qui décide de ce qui part (un destinataire déjà prévenu ne reçoit rien).
    Sans jeton bot, `relances.passe` ne fait rien. Une erreur se journalise :
    l'enregistrement du réglage tient, la route répond 200."""
    async with _verrou:
        try:
            bilan = await relances.passe()
            logger.info("Relances (reglage) : %s", bilan)
        except Exception:
            logger.exception("Relances : erreur de la passe")


async def boucle_appel() -> None:
    """Tâche de fond lancée par le lifespan (`app/main.py`) : un appel après
    `DELAI_DEMARRAGE_S`, puis toutes les `INTERVALLE_S` secondes. Jamais
    fatale : une erreur se journalise, la boucle continue."""
    await asyncio.sleep(DELAI_DEMARRAGE_S)
    source = "demarrage"
    while True:
        try:
            await faire_appel(source)
        except Exception:
            logger.exception("Appel : erreur non bloquante")
        source = "quotidien"
        await asyncio.sleep(INTERVALLE_S)
