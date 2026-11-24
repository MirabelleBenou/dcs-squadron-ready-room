"""Escadrille : résolution + appartenance datée, lecture base de
`name_strip_tokens` — Lot 2.2b (couche d'entités partagée, phase 2).

Ce module remplace, pour la partie DYNAMIQUE (lecture/écriture), ce qui
vivait avant comme un simple aller-retour de chaîne dans `Profile.squadron`
et une property statique de `Settings`. Quatre points d'entrée :

- `sync_squadron_membership()` — clôt/ouvre l'appartenance d'un profil
  (cf. brief §5) et renvoie le nom à mettre en cache sur `Profile.squadron`
  / la session. Appelée par `appliquer_roles()` — TOUJOURS après l'upsert
  du profil (la FK `squadron_membership.profile_id` l'impose). C'est
  l'UNIQUE point d'écriture de `Profile.squadron` (cf. brief §6) : la
  fonction upsert du profil elle-même n'écrit plus ce champ.

- `appliquer_roles()` — lot « L'appel » : la fonction UNIQUE qui applique
  les rôles Discord d'un profil — photo des rôles, appartenance, date
  d'archive. Appelée par la connexion (`app/auth.py`), le clic RSVP
  (`app/discord_rsvp.py`) et l'appel (`app/appel.py`).

- `get_name_strip_tokens()` — le préfixe de l'escadre et l'identifiant de
  TOUTES les escadrilles (actives et en sommeil), lus en base. Remplace l'ancienne property
  `Settings.name_strip_tokens` (qui n'avait pas accès à la base) ; même
  contrat exact (dédup insensible à la casse, tri par longueur
  décroissante) — cf. brief §7, porte P4.

- `reconcile_squadrons_from_env()` — réconciliation "au démarrage" (cf.
  brief G3, cadrage CC §4) : depuis le lot « rr-socle-proprete » (v1.0111),
  seulement le filet de la ligne `wing` (recréée depuis `WING_TAG` si sa
  table est muette) ; les escadrilles vivent en base. Appelée en tâche de
  fond non bloquante depuis le lifespan de `app/main.py`, sur le même
  modèle que `discord_rsvp.reconcile_discord_surface()`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Profile, Squadron, SquadronMembership, Wing

logger = logging.getLogger(__name__)

FREE_AGENT = "Free Agent"


async def _resolve_squadron_id(
    db: AsyncSession, member_role_ids: set[str]
) -> int | None:
    """Id de la PREMIÈRE escadrille ACTIVE dont le rôle Discord de
    rattachement figure dans `member_role_ids`, dans l'ordre de la table
    (`Squadron.id` croissant = ordre de semis, cf. docstring du modèle) --
    jamais l'ordre des rôles du membre (même règle qu'avant, cf. brief §5
    point 1). Les escadrilles en sommeil n'ont pas de rôle Discord
    (`discord_role_id IS NULL`) : la clause `IS NOT NULL` les exclut déjà,
    mais on le documente explicitement -- elles ne sont JAMAIS résolues."""
    result = await db.execute(
        select(Squadron.id, Squadron.discord_role_id)
        .where(Squadron.status == "actif", Squadron.discord_role_id.is_not(None))
        .order_by(Squadron.id.asc())
    )
    for squadron_id, discord_role_id in result.all():
        if discord_role_id in member_role_ids:
            return squadron_id
    return None


async def sync_squadron_membership(
    db: AsyncSession, profile_id: int, member_role_ids: set[str]
) -> str:
    """Clôt/ouvre l'appartenance escadrille du profil (cf. brief §5) et
    renvoie le nom à mettre en cache (`Profile.squadron`, session). DOIT
    être appelée APRÈS l'upsert du profil (FK). Reste appelable SANS
    requête ni session (cf. brief G4) : ne dépend que de `db` et des ids
    déjà résolus par l'appelant (`appliquer_roles`, pour la connexion, le
    clic RSVP et l'appel).

    Règle (identique au cadrage, brief §5 points 2-4) :
    - identique à l'appartenance ouverte -> ne rien faire (`started_at`
      n'est jamais réécrit) ;
    - différente -> clôt l'ouverte à maintenant, en ouvre une nouvelle ;
    - plus d'escadrille -> clôt sans rouvrir (Free Agent, historique
      conservé)."""
    resolved_id = await _resolve_squadron_id(db, member_role_ids)

    open_membership = (
        await db.execute(
            select(SquadronMembership).where(
                SquadronMembership.profile_id == profile_id,
                SquadronMembership.ended_at.is_(None),
            )
        )
    ).scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if resolved_id is None:
        if open_membership is not None:
            open_membership.ended_at = now
        squadron_name = FREE_AGENT
    else:
        if open_membership is not None and open_membership.squadron_id == resolved_id:
            pass  # identique -> ne rien faire, ne pas réécrire started_at
        else:
            if open_membership is not None:
                open_membership.ended_at = now
                await db.flush()  # clôture envoyée avant l'ouverture -- l'index unique partiel (ended_at IS NULL) rejetterait sinon un instant les deux lignes ouvertes pour ce profil
            # Phase 3, lot 3.1 (spec Socle v1.1 §9) -- si le profil a déjà
            # porté une appartenance CLOSE sur la MÊME escadrille, le role
            # de la plus récente (ended_at maximal) est reporté. Sinon,
            # 'member'. Neutralise la perte silencieuse de commandement
            # qu'un incident de résolution Discord provoquerait sinon (clôture
            # puis réouverture sur la même escadrille, role qui repartirait à
            # 'member'). Un changement VERS UNE AUTRE escadrille repart bien
            # à 'member' -- et c'est bien ce même `else` qui s'exécute alors :
            # ce qui produit 'member' n'est pas une branche différente, c'est
            # que le SELECT ci-dessous filtre sur squadron_id == resolved_id,
            # c'est-à-dire la NOUVELLE escadrille, sur laquelle le profil n'a
            # aucune appartenance close -- le fallback `or "member"` joue donc
            # systématiquement dans ce cas.
            reported_role = (
                await db.execute(
                    select(SquadronMembership.role)
                    .where(
                        SquadronMembership.profile_id == profile_id,
                        SquadronMembership.squadron_id == resolved_id,
                        SquadronMembership.ended_at.is_not(None),
                    )
                    .order_by(SquadronMembership.ended_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none() or "member"
            db.add(
                SquadronMembership(
                    profile_id=profile_id,
                    squadron_id=resolved_id,
                    started_at=now,
                    ended_at=None,
                    role=reported_role,
                )
            )
        squadron = await db.get(Squadron, resolved_id)
        squadron_name = squadron.designation

    profile = await db.get(Profile, profile_id)
    profile.squadron = squadron_name  # seul point d'écriture (cf. brief §6)
    await db.commit()
    return squadron_name


async def appliquer_roles(
    db: AsyncSession, profile_id: int, member_role_ids: set[str], peut_entrer: bool
) -> str:
    """Lot « L'appel » (R183, R184) -- la fonction UNIQUE qui applique les
    rôles Discord d'un profil : photo des rôles (`roles_snapshot`, que
    `auth.get_current_user` lit désormais), appartenance
    (`sync_squadron_membership`, inchangée) et date d'archive. Renvoie le nom
    à mettre en cache, comme `sync_squadron_membership`. DOIT être appelée
    APRÈS l'upsert du profil (FK).

    Appelée par la connexion OAuth et par le clic RSVP avec
    `peut_entrer=True` -- ils ne laissent passer que qui passe la porte, ils
    ne peuvent donc que désarchiver -- et par l'appel (`app/appel.py`), seul
    à archiver. La règle : une escadrille active, sinon le droit de connexion
    (Free Agent), sinon hors de l'effectif. `archived_at` porte la date de la
    sortie, gardée telle quelle tant que le profil reste dehors, effacée à
    son retour."""
    profile = await db.get(Profile, profile_id)
    profile.roles_snapshot = sorted(member_role_ids)
    squadron_name = await sync_squadron_membership(db, profile_id, member_role_ids)
    dehors = squadron_name == FREE_AGENT and not peut_entrer
    if dehors and profile.archived_at is None:
        profile.archived_at = datetime.now(timezone.utc)
    elif not dehors and profile.archived_at is not None:
        profile.archived_at = None
    await db.commit()
    return squadron_name


async def get_name_strip_tokens(db: AsyncSession) -> list[str]:
    """Préfixes retirables des noms affichés -- wing + TOUTES les
    escadrilles (actives ET en sommeil), lues en base (cf. brief §7).

    Contrat vérifiable, IDENTIQUE élément par élément à l'ancien
    `Settings.name_strip_tokens` sur la même configuration (porte P4) :
    dédup insensible à la casse, puis tri par longueur décroissante.
    L'ordre de concaténation (wing, puis TOUTES les escadrilles triées par
    `Squadron.id`) reproduit exactement l'ancien ordre `WING_TAG` +
    `squadron_roles_map.values()` (ordre du dict JSON = ordre de semis
    ligne par ligne à la migration) + `dormant_squadron_names_list` (les
    escadrilles en sommeil sont semées APRÈS les actives, donc leurs `id`
    sont plus grands -- `ORDER BY id` retombe exactement sur cette
    séquence).

    Lot « L'identité de l'escadrille » (R189) : le préfixe d'une escadrille
    est son identifiant (`designation`). L'ancien indicatif, qui le valait
    pour chaque escadrille, est devenu le callsign radio -- aucun nom
    affiché ne change au passage."""
    toks: list[str] = []

    wing_tag = (
        await db.execute(select(Wing.tag).order_by(Wing.id.asc()).limit(1))
    ).scalar_one_or_none()
    if wing_tag and wing_tag.strip():
        toks.append(wing_tag.strip())

    identifiants = (
        await db.execute(select(Squadron.designation).order_by(Squadron.id.asc()))
    ).scalars().all()
    toks += [t.strip() for t in identifiants if t and t.strip()]

    seen: set[str] = set()
    uniq = [t for t in toks if not (t.casefold() in seen or seen.add(t.casefold()))]
    return sorted(uniq, key=len, reverse=True)


async def reconcile_squadrons_from_env(db: AsyncSession) -> None:
    """Réconciliation "au démarrage" (cf. brief G3, cadrage CC §4). Lot
    « rr-socle-proprete » (v1.0111) : ne garde que le filet de la ligne `wing`
    -- ligne recréée SEULEMENT si sa table est muette, depuis `WING_TAG`. Le
    semis des escadrilles depuis `SQUADRON_ROLES` et `DORMANT_SQUADRON_NAMES`
    est retiré : ces variables ne sont plus lues depuis le v1.0105, les
    escadrilles vivent en base (écran Escadrilles du Centre). Non bloquante,
    jamais fatale (cf. `_startup_reconcile_discord_surface` dans
    `app/main.py`, même modèle)."""
    wing_row = (
        await db.execute(select(Wing).order_by(Wing.id.asc()).limit(1))
    ).scalar_one_or_none()
    if wing_row is None:
        # Ne devrait pas arriver après la migration 0011 (G2 : le semis
        # n'est pas optionnel) -- filet défensif seulement. Commit isolé et
        # immédiat.
        wing_tag = (settings.WING_TAG or "").strip() or "Ready Room"
        wing_row = Wing(designation=wing_tag, tag=wing_tag)
        db.add(wing_row)
        await db.commit()
        await db.refresh(wing_row)
        logger.warning(
            "Réconciliation escadrille : table wing vide au démarrage, "
            "ligne recréée depuis WING_TAG -- ne devrait survenir qu'après "
            "une base restaurée sans son historique."
        )
    else:
        await db.rollback()
