"""Authentification Discord OAuth2 (sans bot) — cf. SPEC §5.

Flux : /auth/login redirige vers Discord (Authlib gère le `state` anti-CSRF
via request.session) ; /auth/callback échange le code, récupère l'identité
et les rôles guild, applique le gating par liste blanche, upsert le profil
et ouvre la session applicative ; /auth/logout vide la session.
"""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app import defense, langue
from app.command import journal
from app.config import settings
from app.db import get_db
from app.models import Invitation, Profile, RoleCapability
from app.squadron import appliquer_roles

templates = Jinja2Templates(directory="app/templates")

# Lot « La défense de l'App exposée » (R2) : les empreintes des scripts en ligne de
# la page de refus, calculées une fois, depuis le texte même de son gabarit (elle
# n'en a aucun : `script-src 'self'`).
_EMPREINTES_NOACCESS = defense.empreintes_scripts(
    Path("app/templates/noaccess.html").read_text(encoding="utf-8")
)

# Lot « La connexion de secours » (R325) : chaque refus de connexion se journalise.
logger = logging.getLogger(__name__)

DISCORD_API_BASE = "https://discord.com/api/v10/"

oauth = OAuth()
oauth.register(
    name="discord",
    client_id=settings.DISCORD_CLIENT_ID,
    client_secret=settings.DISCORD_CLIENT_SECRET,
    authorize_url="https://discord.com/api/oauth2/authorize",
    access_token_url="https://discord.com/api/oauth2/token",
    api_base_url=DISCORD_API_BASE,
    client_kwargs={"scope": "identify guilds.members.read"},
)

router = APIRouter()


def _ouvrir_session(
    request: Request,
    profile: Profile,
    roles_snapshot: list,
    squadron: str | None,
    now: datetime,
) -> None:
    """Lot « La connexion de secours » (R325) -- la fonction unique qui pose la
    session applicative, partagée par le callback OAuth et par l'entrée des
    liens de secours (`POST /auth/lien`). Les clés et les valeurs sont celles
    que le callback posait avant le lot, ligne pour ligne.

    Lot « L'entrée vide la session » (`v1.0071`, ARC-01) -- la session est
    vidée d'abord, une entrée n'hérite jamais des clés d'une autre."""
    request.session.clear()
    exp = now + timedelta(days=settings.SESSION_TTL_DAYS)
    request.session["id"] = str(profile.id)
    request.session["name"] = profile.global_name or profile.username
    # Lot « L'appel » : `get_current_user` lit les rôles et l'escadrille sur
    # le profil. Les deux restent posés en session pour qu'un retour arrière
    # vers une version antérieure trouve des sessions complètes.
    request.session["roles"] = roles_snapshot
    request.session["lang"] = profile.locale
    # Ajouté au Lot 3b : exposé par GET /api/me pour l'avatar CDN Discord du
    # chip compte (cf. contrat API v2, §"Avatar"). Posé ici plutôt que
    # re-fetché à chaque requête : la session reste la source de
    # get_current_user pour name/lang/avatar.
    request.session["avatar"] = profile.avatar_hash
    # Lot 6 : escadrille, reposee a chaque login (voir le callback).
    request.session["squadron"] = squadron
    request.session["exp"] = exp.isoformat()


def _ouvrir_session_invite(request: Request, user: dict, now: datetime) -> None:
    """Lot « L'accès invité » (R3) -- la session d'un invité, à côté de
    `_ouvrir_session` : l'invité n'a pas de profil, la session ne porte que son
    identité Discord et le drapeau `invite`. Exactement huit clés, aucune autre ;
    `roles` vide et `squadron` nul : il n'a ni rôle ni escadrille.

    Lot « L'entrée vide la session » (`v1.0071`, ARC-01) -- la session est
    vidée d'abord, une entrée n'hérite jamais des clés d'une autre."""
    request.session.clear()
    exp = now + timedelta(days=settings.SESSION_TTL_DAYS)
    request.session["id"] = str(user["id"])
    request.session["name"] = user.get("global_name") or user["username"]
    request.session["roles"] = []
    request.session["lang"] = "fr"
    request.session["avatar"] = user.get("avatar")
    request.session["squadron"] = None
    request.session["exp"] = exp.isoformat()
    request.session["invite"] = True


# Lot « L'accès invité » (R1, R9) -- fonctions pures de l'invitation.
DUREE_INVITATION = timedelta(days=30)


def invitation_active(inv, maintenant: datetime) -> bool:
    """Une invitation est active quand elle existe, n'est pas révoquée et que son
    échéance est postérieure à `maintenant`. Faux pour `None`."""
    if inv is None:
        return False
    return inv.revoque_le is None and inv.jusqua > maintenant


def echeance_initiale(maintenant: datetime) -> datetime:
    """L'échéance d'une invitation neuve : maintenant + 30 jours."""
    return maintenant + DUREE_INVITATION


def echeance_prolongee(jusqua: datetime) -> datetime:
    """L'échéance après une prolongation : l'échéance courante + 30 jours."""
    return jusqua + DUREE_INVITATION


def identifiant_discord_valide(s) -> bool:
    """Un identifiant Discord (« snowflake ») : 17 à 20 chiffres, espaces autour
    tolérés."""
    if not isinstance(s, str):
        return False
    s = s.strip()
    return s.isascii() and s.isdigit() and 17 <= len(s) <= 20


def _redirect_uri() -> str:
    """Construit TOUJOURS le redirect_uri depuis BASE_URL.

    Jamais depuis request.url : derrière le Tailscale Funnel, TLS est
    terminé au nœud et l'app ne voit que du HTTP local — utiliser
    request.url casserait l'OAuth (redirect_uri en http:// refusé par
    Discord / différent de celui déclaré au portail).
    """
    return f"{settings.BASE_URL.rstrip('/')}/auth/callback"


@router.get("/auth/login")
async def login(request: Request):
    redirect_uri = _redirect_uri()
    # Authlib stocke le `state` anti-CSRF dans request.session avant la
    # redirection et le revérifie automatiquement au callback.
    return await oauth.discord.authorize_redirect(request, redirect_uri)


def _contexte_refus(request: Request, user: dict, motif: str) -> dict:
    """Lot « La connexion de secours » (R325) -- le contexte de la page de
    refus : le compte Discord avec lequel on s'est présenté, pourquoi il est
    refusé, et si la commande `/readyroom` est offerte (bot et clé publique
    renseignés)."""
    lang = langue.langue_requete(request)
    return {
        "request": request,
        "lang": lang,
        "t": langue.textes(lang),
        "nom": user.get("global_name") or user["username"],
        "identifiant": user["username"],
        "motif": motif,
        "commande": bool(settings.bot_token_present and settings.DISCORD_PUBLIC_KEY),
    }


@router.get("/auth/callback")
async def callback(request: Request, db: AsyncSession = Depends(get_db)):
    token = await oauth.discord.authorize_access_token(request)

    user_resp = await oauth.discord.get("users/@me", token=token)
    user_resp.raise_for_status()
    user = user_resp.json()

    member_resp = await oauth.discord.get(
        f"users/@me/guilds/{settings.DISCORD_GUILD_ID}/member", token=token
    )
    if member_resp.status_code == 404:
        # Lot « L'accès invité » (R2) : un compte hors du serveur peut avoir une
        # invitation ACTIVE -- avant le refus « non membre ». Aucun upsert de
        # profil, aucun `appliquer_roles` : l'invité n'a pas de profil.
        now = datetime.now(timezone.utc)
        inv = await db.get(Invitation, int(user["id"]))
        if invitation_active(inv, now):
            inv.nom = user.get("global_name") or user["username"]
            inv.username = user["username"]
            inv.derniere_entree = now
            journal.consigner(
                db, {"id": inv.invite_par}, "invites.entree",
                objet=inv.nom, lignes=[], toujours=True,
            )
            await db.commit()
            _ouvrir_session_invite(request, user, now)
            return RedirectResponse(url="/")
        # Non-membre du guild → pas d'accès.
        logger.warning(
            "Connexion refusée (non membre du serveur) : compte Discord %s (@%s)",
            user["id"], user["username"],
        )
        return defense.poser_politique(
            templates.TemplateResponse(
                request, "noaccess.html", _contexte_refus(request, user, "non_membre"), status_code=403
            ),
            request, _EMPREINTES_NOACCESS,
        )
    member_resp.raise_for_status()
    member = member_resp.json()

    # IDs = snowflakes → toujours comparés en str.
    member_role_ids = {str(r) for r in member.get("roles", [])}
    # Lot 3.2d Volet 2, §5.4 : la liste passe par le résolveur (la base ; muette,
    # seuls les administrateurs entrent).
    allowed_role_ids = await _app_access_role_ids(db)
    # GARDE-FOU anti-lock-out : un administrateur entre toujours, quels que
    # soient ses rôles Discord. Sans cela, l'écran Droits pourrait fermer la
    # porte à tout le monde, administrateur compris. TOUJOURS avant le test
    # de rôles.
    if str(user["id"]) not in settings.admin_ids_set:
        if not (member_role_ids & allowed_role_ids):
            logger.warning(
                "Connexion refusée (aucun rôle d'accès) : compte Discord %s (@%s), rôles du membre : %s",
                user["id"], user["username"], sorted(member_role_ids),
            )
            return defense.poser_politique(
                templates.TemplateResponse(
                    request, "noaccess.html", _contexte_refus(request, user, "sans_role"), status_code=403
                ),
                request, _EMPREINTES_NOACCESS,
            )

    discord_id = int(user["id"])
    now = datetime.now(timezone.utc)
    roles_snapshot = sorted(member_role_ids)

    # Nom affiché = pseudo serveur Discord (`member.nick`) en priorité (cf.
    # brief Lot 5 §3) : le pseudo propre au serveur peut différer du
    # `global_name`/`username` du compte. `nick` peut être `null` (membre
    # sans pseudo serveur) → repli sur `global_name` puis `username`
    # (jamais vide). Stocké dans le champ `global_name` du profil pour
    # éviter une migration ; ce champ sert donc désormais de nom d'affichage
    # unique, utilisé partout (roster, hebdo, chip compte, /api/me).
    display_name = member.get("nick") or user.get("global_name") or user["username"]

    stmt = pg_insert(Profile).values(
        id=discord_id,
        username=user["username"],
        global_name=display_name,
        avatar_hash=user.get("avatar"),
        roles_snapshot=roles_snapshot,
        last_login_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[Profile.id],
        set_={
            "username": user["username"],
            "global_name": display_name,
            "avatar_hash": user.get("avatar"),
            "roles_snapshot": roles_snapshot,
            "last_login_at": now,
        },
    )
    await db.execute(stmt)
    await db.commit()

    # Lot 2.2b (cf. brief §5/§6) -- escadrille resolue depuis la table
    # `squadron` (plus le mapping .env brut), qui clot/ouvre une
    # appartenance datee et renvoie le nom a mettre en cache. Reevaluee a
    # CHAQUE login (les roles Discord peuvent changer), jamais figee apres
    # la premiere connexion. DOIT s'executer apres l'upsert ci-dessus (FK
    # squadron_membership.profile_id). Lot « L'appel » : par
    # `appliquer_roles`, la fonction unique que partagent la connexion, le
    # clic RSVP et l'appel ; qui passe la porte ici ne peut qu'etre
    # desarchive (`peut_entrer=True`).
    squadron = await appliquer_roles(db, discord_id, member_role_ids, True)

    profile = await db.get(Profile, discord_id)

    # Lot « La connexion de secours » : la session se pose par la fonction
    # partagée avec l'entrée des liens de secours (mêmes clés, mêmes valeurs).
    _ouvrir_session(request, profile, roles_snapshot, squadron, now)

    return RedirectResponse(url="/")


@router.post("/auth/logout", status_code=204)
async def logout(request: Request):
    """Lot « La défense de l'App exposée » (R7, ARC-12) : la déconnexion passe en
    `POST` (un lien ou une image d'un autre site ne déconnecte plus personne) ; elle
    vide la session et répond `204`. Le front navigue vers `/` de lui-même."""
    request.session.clear()
    return Response(status_code=204)


# --- Lot 3.2d, Volet 2 (§5.1) -- résolveur de l'accès à l'application ------
#
# Cache mémoire de processus, sans expiration, invalidé UNIQUEMENT à
# l'écriture (`invalidate_app_access_cache()`, appelée après commit par
# `PUT /rights/app-access`). Hypothèse déjà posée et documentée pour le bus
# temps réel (`app/realtime.py`, docstring) : le déploiement est
# mono-processus (`entrypoint.sh:75`, un seul `uvicorn`, pas de
# `--workers`). Un passage multi-instances casserait ce cache comme il
# casse déjà le temps réel -- même dette, pas une nouvelle.
_app_access_cache: set[str] | None = None


async def _app_access_role_ids(db: AsyncSession) -> set[str]:
    """Liste courante des rôles Discord qui ouvrent la connexion : les lignes
    `capability='app.access'` de `role_capabilities`. La base fait autorité
    SEULE ; base muette = ensemble vide (seuls les administrateurs entrent,
    comme aujourd'hui). Lot « rr-socle-proprete » (v1.0111) : le repli `.env`
    et le drapeau `from_env` sont retirés -- la variable n'est plus lue
    depuis le v1.0105."""
    global _app_access_cache
    if _app_access_cache is not None:
        return _app_access_cache
    stmt = select(RoleCapability.role_id).where(
        RoleCapability.capability == "app.access"
    )
    result = await db.execute(stmt)
    _app_access_cache = {str(r) for r in result.scalars().all()}
    return _app_access_cache


def invalidate_app_access_cache() -> None:
    """Vide le cache du résolveur. Appelée après commit par la route
    d'écriture (`PUT /rights/app-access`) -- sans quoi l'effet immédiat
    promis par l'écran Droits n'existe pas."""
    global _app_access_cache
    _app_access_cache = None


async def has_app_access(db: AsyncSession, user: dict) -> bool:
    """Résolution de l'accès permanent à l'application (§5.1/§5.2).
    `is_admin`-équivalent en premier, avant toute lecture de table --
    `is_admin()` vit dans `capabilities.py` et l'importer ici créerait un
    cycle (`capabilities` importe déjà `get_current_user`). Test dupliqué
    volontairement sur `settings.admin_ids_set`, pas de refactor de
    `is_admin()` pour l'occasion (hors périmètre, 40 points d'appel).
    Sinon, intersection entre les rôles de `user` -- ceux du profil depuis
    le lot « L'appel » -- et la liste résolue."""
    if str(user["id"]) in settings.admin_ids_set:
        return True
    role_ids = await _app_access_role_ids(db)
    roles = {str(r) for r in user.get("roles", [])}
    return bool(roles & role_ids)


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> dict:
    """Dépendance FastAPI. Ordre impératif (§5.2) : session absente → 401 ·
    session expirée → 401 (session VIDÉE, comportement actuel inchangé) ·
    profil introuvable → 401 · PUIS accès retiré → 401 (§5.1, Volet 2 du
    Lot 3.2d).

    Lot « L'appel » (R185) : la session dit qui l'on est, la base ce qu'on
    peut faire. Les rôles et l'escadrille se lisent sur le profil
    (`roles_snapshot`, `squadron`), que l'appel tient à jour chaque jour --
    plus dans le cookie, figé jusqu'à sa fin de vie. `name`, `lang` et
    `avatar` restent ceux de la session.

    ⚠ Le cas « accès retiré » NE VIDE PAS la session (cf. §5.3) : si elle
    l'était, remettre le rôle ne suffirait plus, la personne devrait se
    reconnecter -- l'écran Droits promet le contraire, mot pour mot
    (« Le remettre la fait rentrer aussitôt »). La session non vidée n'est
    pas un trou : elle ne donne accès à rien tant que le contrôle refuse,
    elle redevient simplement valide dès que le rôle revient."""
    session_id = request.session.get("id")
    if session_id is None:
        raise HTTPException(status_code=401, detail="Non authentifié")

    exp_raw = request.session.get("exp")
    if exp_raw:
        exp = datetime.fromisoformat(exp_raw)
        if datetime.now(timezone.utc) > exp:
            request.session.clear()
            raise HTTPException(status_code=401, detail="Session expirée")

    # Lot « L'accès invité » (R4) : la session d'un invité se reconnaît à son
    # drapeau `invite` ; on lit l'invitation, JAMAIS le profil (il n'en a pas).
    # Révoquée ou échue : 401, session préservée (même patron que le retrait
    # d'un rôle) -- l'effet est celui de la requête suivante.
    if request.session.get("invite") is True:
        inv = await db.get(Invitation, int(session_id))
        if not invitation_active(inv, datetime.now(timezone.utc)):
            raise HTTPException(status_code=401, detail="Accès retiré")
        return {
            "id": session_id,
            "name": request.session.get("name"),
            "roles": [],
            "lang": request.session.get("lang", "fr"),
            "avatar": request.session.get("avatar"),
            "squadron": None,
            "invite": True,
            "invite_jusqua": inv.jusqua.astimezone(timezone.utc).isoformat(),
        }

    profile = await db.get(Profile, int(session_id))
    if profile is None:
        raise HTTPException(status_code=401, detail="Non authentifié")

    user = {
        "id": session_id,
        "name": request.session.get("name"),
        "roles": list(profile.roles_snapshot or []),
        "lang": request.session.get("lang", "fr"),
        "avatar": request.session.get("avatar"),
        "squadron": profile.squadron,
    }

    if not await has_app_access(db, user):
        # Accès retiré (§5.3) : 401, session PRÉSERVÉE -- voir docstring.
        raise HTTPException(status_code=401, detail="Accès retiré")

    return user


async def get_current_user_optional(
    request: Request, db: AsyncSession = Depends(get_db)
) -> dict | None:
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
