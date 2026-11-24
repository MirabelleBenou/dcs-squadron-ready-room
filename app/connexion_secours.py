"""Lot « La connexion de secours » (R325) -- deux portes de secours quand la
connexion par Discord (OAuth) ne passe pas :

- la commande `/readyroom`, tapée dans le serveur Discord de l'escadre : le
  pilote reçoit, visible de lui seul, un lien d'entrée valable 5 minutes, une
  seule fois ; son identité et ses rôles viennent de l'interaction, signée par
  Discord (`discord_rsvp.discord_interactions`) ;
- le lien émis par un administrateur au Centre de Commandement, pour un membre
  connu : valable 24 heures, une seule fois, droits lus sur le profil.

Le jeton voyage dans le FRAGMENT de l'URL (`/auth/lien#<jeton>`) : le
navigateur ne l'envoie jamais au serveur, il n'apparaît ni dans les journaux
d'accès ni dans un `Referer`, et un robot d'aperçu qui visite l'URL ne le
consomme pas. Seule son empreinte (SHA-256) est stockée (`login_links`).

Ce module ne change pas le flux OAuth : le prédicat de la porte s'y réécrit à
l'identique (administrateur d'abord, puis rôles ∩ `_app_access_role_ids`),
comme le clic RSVP le fait déjà.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import _app_access_role_ids, _ouvrir_session, has_app_access
from app.command import journal
from app.config import settings
from app.db import get_db
from app import langue
from app.defense import est_json, origine_autorisee
from app.models import LoginLink, Profile
from app.squadron import appliquer_roles

logger = logging.getLogger(__name__)

router = APIRouter()

DUREE_DISCORD = timedelta(minutes=5)
DUREE_ADMIN = timedelta(hours=24)


# --- Les fonctions pures -----------------------------------------------------


def nouveau_jeton() -> str:
    """Un jeton neuf : 32 octets aléatoires, alphabet URL-safe (43 caractères)."""
    return secrets.token_urlsafe(32)


def empreinte(jeton: str) -> str:
    """Le SHA-256 hexadécimal de l'UTF-8 du jeton -- ce que la base stocke."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def url_du_lien(jeton: str) -> str:
    """L'URL d'entrée : `BASE_URL` sans `/` final, `/auth/lien#`, le jeton. Le
    jeton est dans le fragment, jamais dans le chemin ni la requête."""
    return settings.BASE_URL.rstrip("/") + "/auth/lien#" + jeton


def commande_readyroom() -> dict:
    """La définition de la commande, telle que Discord la reçoit."""
    return {
        "name": "readyroom",
        "type": 1,
        # Lot « rr-public-pages-bilingues » : l'anglais par défaut, le français déclaré à Discord.
        "description": langue.DESCRIPTION_COMMANDE["en"],
        "description_localizations": {"fr": langue.DESCRIPTION_COMMANDE["fr"]},
    }


def reponse_commande(url: str, lang: str = "en") -> dict:
    """La réponse à l'interaction : un message éphémère (64) sans aperçu (4),
    avec un seul bouton lien, dans la langue de Discord de la personne."""
    t = langue.textes(lang)
    return {
        "type": 4,
        "data": {
            "flags": 68,
            "content": t["cmd_lien"],
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 5,
                            "label": t["cmd_bouton"],
                            "url": url,
                        }
                    ],
                }
            ],
            "allowed_mentions": {"parse": []},
        },
    }


def _ephemere(contenu: str) -> dict:
    """Une réponse éphémère simple -- jamais d'« interaction failed » côté Discord."""
    return {"type": 4, "data": {"flags": 64, "content": contenu}}


# --- L'émission --------------------------------------------------------------


async def emettre_lien(
    db: AsyncSession, profile_id: int, source: str, created_by: int | None
) -> tuple[str, datetime]:
    """Émet un lien pour `profile_id` : supprime les liens NON utilisés du même
    profil et de la même source (en émettre un annule le précédent), insère le
    nouveau (empreinte seule) et rend `(url, expires_at)`. Ne commite pas :
    l'appelant commite. L'heure est celle de Python, la même que celle de la
    consommation."""
    jeton = nouveau_jeton()
    expire = datetime.now(timezone.utc) + (
        DUREE_DISCORD if source == "discord" else DUREE_ADMIN
    )
    await db.execute(
        delete(LoginLink).where(
            LoginLink.profile_id == profile_id,
            LoginLink.source == source,
            LoginLink.used_at.is_(None),
        )
    )
    db.add(
        LoginLink(
            token_hash=empreinte(jeton),
            profile_id=profile_id,
            source=source,
            created_by=created_by,
            expires_at=expire,
        )
    )
    return url_du_lien(jeton), expire


# --- La commande /readyroom --------------------------------------------------


async def _traiter(db: AsyncSession, body: dict) -> dict:
    data = body.get("data") or {}
    t = langue.textes(langue.langue_discord(body.get("locale")))
    if data.get("name") != "readyroom":
        return _ephemere(t["cmd_inconnue"])

    member = body.get("member")
    if not member:
        # Message privé : la commande ne vaut que dans le serveur.
        return _ephemere(t["cmd_hors_serveur"])

    user = member.get("user") or {}
    user_id = int(user["id"])
    username = user["username"]
    member_role_ids = {str(r) for r in member.get("roles", [])}

    # La porte : le prédicat du login, réécrit à l'identique -- administrateur
    # d'abord, puis rôles ∩ rôles d'accès.
    allowed_role_ids = await _app_access_role_ids(db)
    if str(user_id) not in settings.admin_ids_set:
        if not (member_role_ids & allowed_role_ids):
            logger.warning(
                "Commande /readyroom refusée (aucun rôle d'accès) : compte Discord %s (@%s)",
                user_id, username,
            )
            return _ephemere(t["cmd_sans_acces"])

    # Le profil, comme une connexion (sans `last_login_at` : il se pose à
    # l'entrée). Nom affiché : la règle du callback.
    display_name = member.get("nick") or user.get("global_name") or username
    roles_snapshot = sorted(member_role_ids)
    stmt = pg_insert(Profile).values(
        id=user_id,
        username=username,
        global_name=display_name,
        avatar_hash=user.get("avatar"),
        roles_snapshot=roles_snapshot,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Profile.id],
        set_={
            "username": username,
            "global_name": display_name,
            "avatar_hash": user.get("avatar"),
            "roles_snapshot": roles_snapshot,
        },
    )
    await db.execute(stmt)
    await db.commit()
    await appliquer_roles(db, user_id, member_role_ids, True)

    url, _expire = await emettre_lien(db, user_id, "discord", None)
    await db.commit()
    return reponse_commande(url, langue.langue_discord(body.get("locale")))


async def traiter_commande(db: AsyncSession, body: dict) -> dict:
    """Traite une interaction de type 2 (commande) pour `discord_interactions` :
    ne lève jamais -- toute exception imprévue se journalise et rend un
    éphémère propre."""
    try:
        return await _traiter(db, body)
    except Exception:
        logger.exception("Commande /readyroom : erreur imprévue")
        try:
            await db.rollback()
        except Exception:
            logger.exception("Commande /readyroom : annulation de la transaction impossible")
        return _ephemere(langue.textes(langue.langue_discord(body.get("locale")))["cmd_erreur"])


async def enregistrer_commande() -> None:
    """Déclare la commande `/readyroom` sur le serveur de l'escadre. Discord crée
    ou met à jour la commande de même nom : l'appel est idempotent. Ne propage
    jamais d'exception. L'import de `_bot_request` est local : `discord_rsvp`
    importe ce module."""
    from app.discord_rsvp import _bot_request

    try:
        reponse = await _bot_request(
            "POST",
            f"/applications/{settings.DISCORD_CLIENT_ID}/guilds/{settings.DISCORD_GUILD_ID}/commands",
            json_body=commande_readyroom(),
        )
        if reponse is None:
            logger.warning("Commande /readyroom : pas de réponse de Discord à l'enregistrement.")
        elif reponse.status_code in (200, 201):
            logger.info("Commande /readyroom enregistrée sur le serveur.")
        else:
            logger.warning(
                "Commande /readyroom : enregistrement refusé (%s) : %s",
                reponse.status_code, reponse.text[:300],
            )
    except Exception:
        logger.exception("Commande /readyroom : erreur à l'enregistrement")


# --- L'entrée : POST /auth/lien ----------------------------------------------


@router.post("/auth/lien")
async def entrer_par_lien(request: Request, db: AsyncSession = Depends(get_db)):
    """Consomme un lien d'entrée et ouvre la session. Corps JSON `{"token": …}`.
    `400` corps illisible ou jeton absent · `410` lien expiré ou déjà servi ·
    `403` plus de droit de connexion (le lien reste consommé) · `204` entré.

    Lot « La défense de l'App exposée » (R7, ARC-12) : un `Content-Type` qui n'est pas
    `application/json` → `415`, avant toute lecture du corps ; un `Origin` présent
    et différent de l'origine de `BASE_URL` → `403` ; un `Origin` absent passe."""
    t = langue.textes(langue.langue_requete(request))
    if not est_json(request.headers.get("content-type")):
        raise HTTPException(status_code=415, detail=t["auth_415"])
    if not origine_autorisee(request.headers.get("origin"), settings.BASE_URL):
        raise HTTPException(status_code=403, detail=t["auth_403_origine"])
    try:
        corps = await request.json()
        jeton = corps.get("token") if isinstance(corps, dict) else None
    except ValueError:
        jeton = None
    if not isinstance(jeton, str) or not jeton.strip():
        raise HTTPException(status_code=400, detail=t["auth_400"])

    # Une seule requête atomique consomme le lien : deux entrées simultanées
    # ne peuvent pas passer toutes les deux.
    now = datetime.now(timezone.utc)
    resultat = await db.execute(
        update(LoginLink)
        .where(
            LoginLink.token_hash == empreinte(jeton),
            LoginLink.used_at.is_(None),
            LoginLink.expires_at > now,
        )
        .values(used_at=now)
        .returning(LoginLink.profile_id, LoginLink.source)
    )
    ligne = resultat.first()
    await db.commit()
    if ligne is None:
        logger.info("Lien de secours refusé : expiré, déjà servi ou inconnu")
        raise HTTPException(
            status_code=410,
            detail=t["auth_410"],
        )
    profile_id, source = ligne

    # La porte, sur le profil (rôles relevés par l'appel quotidien ou la
    # dernière connexion), sans appel à Discord.
    profile = await db.get(Profile, profile_id)
    if (
        profile is None
        or profile.archived_at is not None
        or not (
            str(profile.id) in settings.admin_ids_set
            or await has_app_access(
                db, {"id": profile.id, "roles": profile.roles_snapshot}
            )
        )
    ):
        logger.info(
            "Lien de secours refusé : le profil %s n'a plus le droit de connexion", profile_id
        )
        raise HTTPException(
            status_code=403,
            detail=t["auth_403_droit"],
        )

    profile.last_login_at = now
    if source == "admin":
        journal.consigner(db, {"id": profile_id}, "auth.lien_secours", toujours=True)
    await db.commit()

    _ouvrir_session(request, profile, profile.roles_snapshot, profile.squadron, now)
    logger.info("Entrée par lien de secours : profil %s, source %s", profile_id, source)
    return Response(status_code=204)
