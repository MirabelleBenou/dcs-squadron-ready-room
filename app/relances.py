"""Les relances -- un pilote d'escadrille qui ne remplit plus le planning est
signalé par MP Discord (lot « Les relances », R1 à R11).

Décidé le 2 octobre (R196), précisé le 3. Un pilote est signalé
aux porteurs des rôles choisis à l'écran Droits (`relances.destinataire`),
**une fois, quand son nom s'ajoute** : jamais un MP par jour. La liste vit
aussi en tête de l'écran Membres du Centre (`GET /api/command/relances`),
MP refusés compris ; les envois se notent en base (`relance_envois`).

La règle, le texte du MP et la décision « qui prévenir de quoi » sont des
fonctions PURES (R12) ; `etat` lit la base, `passe` écrit et parle à
Discord. `app/appel.py` ne gagne que l'appel de `passe` (R3) -- sous son
verrou, après un appel réussi.

« Aujourd'hui » est la date de Paris (`REFERENCE_TZ`), calculée en Python :
le banc fige l'heure de Python, pas celle de PostgreSQL.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import AsyncSessionLocal
from app.discord_rsvp import _bot_request
from app.events import _build_name_strip_regex, _callsign, _load_events_and_overrides
from app.models import (
    AccountCapability,
    Presence,
    Profile,
    RelanceEnvoi,
    RoleCapability,
    Squadron,
    SquadronMembership,
)
from app.recurrence import UnsupportedRecurrenceRule, expand, fuseau_reference

logger = logging.getLogger(__name__)

CAPACITE = "relances.destinataire"
FENETRE_J = 28   # la fenêtre : d'aujourd'hui - 28 j à aujourd'hui - 1 j
HORIZON_J = 90   # les occurrences à venir : d'aujourd'hui à aujourd'hui + 90 j
MP_MAX = 2000    # la limite d'un message Discord, en caractères
REFUS_DISCORD = 50007  # « impossible d'envoyer un message à cet utilisateur »
PREVENU = ("envoye", "refuse")  # un `echec` ne vaut pas « prévenu »


@dataclass(frozen=True)
class Candidat:
    """Un profil, tel que la règle le juge. `escadrille` est l'identifiant de
    l'escadrille ACTIVE de son appartenance en cours, None sinon (Free Agent) ;
    `depuis` la date de Paris du début de cette appartenance ; `reponses` les
    occurrences auxquelles il a répondu, `(event_id, occ_date)` ; `derniere` la
    plus récente `created_at` de ses réponses, toutes occurrences confondues."""

    id: int
    nom: str
    escadrille: Optional[str]
    depuis: Optional[date]
    archive: bool
    reponses: frozenset
    derniere: Optional[datetime]


@dataclass(frozen=True)
class Retard:
    """Un pilote en retard. `derniere` : l'instant de sa dernière réponse, None
    s'il n'a jamais répondu."""

    id: int
    nom: str
    escadrille: str
    derniere: Optional[datetime]

    @property
    def derniere_date(self) -> Optional[date]:
        return self.derniere.astimezone(fuseau_reference()).date() if self.derniere else None


def aujourd_hui() -> date:
    """La date de Paris, calculée en Python (R1)."""
    return datetime.now(timezone.utc).astimezone(fuseau_reference()).date()


def en_retard(jour: date, candidats: Iterable[Candidat], fenetre: set, a_venir: set) -> list[Retard]:
    """R1. Pure. `fenetre` et `a_venir` : les occurrences effectives
    `(event_id, occ_date)` de [jour - 28 j, jour - 1 j] et de [jour, jour + 90 j].
    Une fenêtre sans occurrence effective : personne n'est en retard. Rend les
    retards triés par escadrille puis par nom, sans tenir compte de la casse
    (R5)."""
    if not fenetre:
        return []
    attendues = fenetre | a_venir
    limite = jour - timedelta(days=FENETRE_J)
    retards = []
    for c in candidats:
        if c.archive or c.escadrille is None or c.depuis is None:
            continue
        if c.depuis > limite:  # moins de 28 jours dans l'escadrille
            continue
        if c.reponses & attendues:  # une réponse, quelle qu'elle soit, compte
            continue
        retards.append(Retard(c.id, c.nom, c.escadrille, c.derniere))
    return sorted(retards, key=lambda r: (r.escadrille.casefold(), r.escadrille, r.nom.casefold(), r.id))


def reponses_depuis(lignes: Iterable[tuple]) -> frozenset:
    """R1, condition 4. Pure. `lignes` : `(event_id, occ_date, état)`, une par
    réponse d'un pilote. Présent, peut-être ou absent, au bouton ou au portail :
    toute réponse compte, l'état n'entre pas dans la règle. Rend les
    occurrences auxquelles il a répondu."""
    return frozenset((str(eid), jour) for eid, jour, _etat in lignes)


def par_escadrille(retards: Iterable[Retard]) -> list[tuple[str, list[Retard]]]:
    """Les retards groupés par escadrille, dans l'ordre de `en_retard`. Pure."""
    groupes: list[tuple[str, list[Retard]]] = []
    for r in retards:
        if groupes and groupes[-1][0] == r.escadrille:
            groupes[-1][1].append(r)
        else:
            groupes.append((r.escadrille, [r]))
    return groupes


def deja_prevenu(envois: Iterable[tuple], destinataire: int, retard: Retard) -> bool:
    """R4. Pure. `envois` : `(destinataire_id, pilote_id, envoye_le, statut)`.
    D est déjà prévenu de P s'il existe un envoi (D, P) de statut `envoye` ou
    `refuse` daté après la dernière réponse de P ; si P n'a jamais répondu,
    n'importe quel envoi (D, P) de ces statuts suffit."""
    for d, p, quand, statut in envois:
        if d != destinataire or p != retard.id or statut not in PREVENU:
            continue
        if retard.derniere is None or quand > retard.derniere:
            return True
    return False


def nouveaux_noms(envois: Iterable[tuple], destinataire: int, retards: Iterable[Retard]) -> list[Retard]:
    """R4. Pure. Les pilotes en retard dont `destinataire` n'est pas déjà
    prévenu. Sans nouveau nom, aucun MP à ce destinataire."""
    envois = list(envois)
    return [r for r in retards if not deja_prevenu(envois, destinataire, r)]


def _ligne_pilote(r: Retard, nouveau: bool) -> str:
    dernier = f"dernière réponse le {r.derniere_date:%d/%m}" if r.derniere else "aucune réponse"
    return f"- {r.nom} — {dernier}" + (" · nouveau" if nouveau else "")


def texte_mp(retards: list[Retard], nouveaux: set[int]) -> str:
    """R5. Pure. Le texte du MP, le même pour tous les destinataires hors les
    `· nouveau`, qui suivent les noms de `nouveaux` (identifiants de pilotes).
    La liste est complète ; au-delà de 2 000 caractères, des lignes de pilotes
    partent par la fin et la liste se termine par
    `- … et <n> autres : voir le Centre` -- une escadrille dont tous les
    pilotes sont partis perd aussi son titre."""
    entete = [
        "**Relances de planning**",
        "Pilotes d'escadrille sans aucune réponse au planning depuis quatre semaines :",
        "",
    ]
    pied = ["", "La liste à jour est au Centre de Commandement, écran Membres."]
    groupes = par_escadrille(retards)

    def assembler(gardes: int) -> str:
        lignes = list(entete)
        restants = gardes
        for escadrille, pilotes in groupes:
            if restants <= 0:
                break
            lignes.append(f"**{escadrille}**")
            for r in pilotes[:restants]:
                lignes.append(_ligne_pilote(r, r.id in nouveaux))
            restants -= len(pilotes)
        if gardes < len(retards):
            lignes.append(f"- … et {len(retards) - gardes} autres : voir le Centre")
        return "\n".join(lignes + pied)

    gardes = len(retards)
    texte = assembler(gardes)
    while len(texte) > MP_MAX and gardes > 0:
        gardes -= 1
        texte = assembler(gardes)
    return texte


# ---------------------------------------------------------------------------
# La lecture de la base
# ---------------------------------------------------------------------------


def _occurrences(debut: date, fin: date, tout: tuple) -> set:
    """Les occurrences effectives `(event_id, occ_date)` de [debut, fin],
    prises dans `tout` -- les événements et exceptions déjà chargés (R1 :
    `expand()` avec les exceptions de `_load_events_and_overrides`)."""
    events, overrides = tout
    occs: set = set()
    for e in events:
        try:
            for o in expand(e, overrides.get(e.id, {}), debut, fin):
                occs.add((str(o.event_id), o.occ_date))
        except UnsupportedRecurrenceRule:
            continue
    return occs


async def _candidats(db: AsyncSession, debut: date) -> list[Candidat]:
    """Tous les profils, avec leur escadrille ACTIVE en cours s'ils en ont
    une, leurs réponses depuis `debut` et leur dernière réponse. Les noms
    sont ceux du tableau des membres, préfixe d'escadrille retiré (R10)."""
    lignes = (await db.execute(
        select(Profile, Squadron.designation, SquadronMembership.started_at)
        .select_from(Profile)
        .outerjoin(
            SquadronMembership,
            (SquadronMembership.profile_id == Profile.id) & SquadronMembership.ended_at.is_(None),
        )
        .outerjoin(
            Squadron,
            (Squadron.id == SquadronMembership.squadron_id) & (Squadron.status == "actif"),
        )
    )).all()
    lignes_reponses: dict[int, list] = {}
    for pid, eid, jour, etat in (await db.execute(
        select(Presence.profile_id, Presence.event_id, Presence.occ_date, Presence.state)
        .where(Presence.occ_date >= debut)
    )).all():
        lignes_reponses.setdefault(pid, []).append((eid, jour, etat))
    dernieres = dict((await db.execute(
        select(Presence.profile_id, func.max(Presence.created_at)).group_by(Presence.profile_id)
    )).all())
    rx = await _build_name_strip_regex(db)
    return [
        Candidat(
            id=p.id,
            nom=_callsign(p.global_name or p.username, rx),
            escadrille=designation,
            depuis=debut_membre.astimezone(fuseau_reference()).date() if designation and debut_membre else None,
            archive=p.archived_at is not None,
            reponses=reponses_depuis(lignes_reponses.get(p.id, ())),
            derniere=dernieres.get(p.id),
        )
        for p, designation, debut_membre in lignes
    ]


async def retards_du_jour(db: AsyncSession, jour: Optional[date] = None) -> list[Retard]:
    """R1, sur la base : les pilotes en retard, triés (R5)."""
    jour = jour or aujourd_hui()
    debut = jour - timedelta(days=FENETRE_J)
    fin = jour + timedelta(days=HORIZON_J)
    tout = await _load_events_and_overrides(db, debut, fin)
    fenetre = _occurrences(debut, jour - timedelta(days=1), tout)
    a_venir = _occurrences(jour, fin, tout)
    return en_retard(jour, await _candidats(db, debut), fenetre, a_venir)


def retenir_destinataires(profils: Iterable[tuple], roles: set, comptes: set) -> list[int]:
    """Lot « Les relances nominatives » (R4). Pure. `profils` : `(id, archivé,
    roles_snapshot)`, un par profil ; `roles` : les identifiants de rôles
    choisis (texte) ; `comptes` : les identifiants de profils choisis par leur
    nom. Rend les identifiants des profils NON archivés qui portent un rôle
    choisi OU qui sont choisis par leur nom -- chacun une seule fois, dans
    l'ordre de son identifiant. Ni rôle ni compte choisi : personne."""
    if not roles and not comptes:
        return []
    retenus = set()
    for pid, archive, snapshot in profils:
        if archive:
            continue
        if pid in comptes or roles & {str(r) for r in (snapshot or [])}:
            retenus.add(pid)
    return sorted(retenus)


async def destinataires(db: AsyncSession) -> list[tuple[int, str]]:
    """R2, étendu par le lot « Les relances nominatives » (R4). `(id, nom)` des
    profils non archivés qui portent au moins un des rôles choisis à l'écran
    Droits (`roles_snapshot`) ou qui y sont choisis par leur nom
    (`account_capability`), chacun une seule fois, dans l'ordre de leur
    identifiant. Ni rôle ni compte choisi : aucun destinataire."""
    roles = set((await db.execute(
        select(RoleCapability.role_id).where(RoleCapability.capability == CAPACITE)
    )).scalars().all())
    comptes = set((await db.execute(
        select(AccountCapability.profile_id).where(AccountCapability.capability == CAPACITE)
    )).scalars().all())
    if not roles and not comptes:
        return []
    rx = await _build_name_strip_regex(db)
    profils = (await db.execute(
        select(Profile).where(Profile.archived_at.is_(None)).order_by(Profile.id)
    )).scalars().all()
    retenus = set(retenir_destinataires(
        ((p.id, p.archived_at is not None, p.roles_snapshot) for p in profils), roles, comptes,
    ))
    return [
        (p.id, _callsign(p.global_name or p.username, rx))
        for p in profils
        if p.id in retenus
    ]


async def _envois(db: AsyncSession) -> list[RelanceEnvoi]:
    return list((await db.execute(select(RelanceEnvoi))).scalars().all())


async def etat(db: AsyncSession) -> dict:
    """R9. La charge de `GET /api/command/relances` : les retards par
    escadrille, les destinataires, et ceux dont le dernier envoi est refusé
    (le plus récent par date, puis par identifiant)."""
    retards = await retards_du_jour(db)
    dest = await destinataires(db)
    derniers: dict[int, RelanceEnvoi] = {}
    for e in await _envois(db):
        if e.destinataire_id not in derniers or (e.envoye_le, e.id) > (
            derniers[e.destinataire_id].envoye_le, derniers[e.destinataire_id].id
        ):
            derniers[e.destinataire_id] = e
    return {
        "retards": [
            {
                "escadrille": escadrille,
                "pilotes": [
                    {
                        "id": str(r.id),
                        "nom": r.nom,
                        "derniere_reponse": r.derniere_date.isoformat() if r.derniere else None,
                    }
                    for r in pilotes
                ],
            }
            for escadrille, pilotes in par_escadrille(retards)
        ],
        "destinataires": [{"id": str(i), "nom": nom} for i, nom in dest],
        "refus": [
            {"destinataire": {"id": str(i), "nom": nom}, "le": derniers[i].envoye_le.isoformat()}
            for i, nom in dest
            if i in derniers and derniers[i].statut == "refuse"
        ],
    }


# ---------------------------------------------------------------------------
# L'envoi
# ---------------------------------------------------------------------------


def _code(reponse) -> Optional[int]:
    try:
        corps = reponse.json()
    except ValueError:
        return None
    return corps.get("code") if isinstance(corps, dict) else None


async def envoyer_mp(destinataire_id: int, texte: str) -> str:
    """R5. Un MP par `_bot_request` : ouverture du canal privé
    (`POST /users/@me/channels`), puis dépôt (`POST /channels/{id}/messages`),
    corps `{"content": …}` sans embed. Rend le statut de R4 : `envoye`
    (Discord répond 200 au dépôt), `refuse` (403, code 50007, à l'ouverture ou
    au dépôt), `echec` (toute autre réponse, ou Discord injoignable). Ne lève
    jamais."""
    canal = await _bot_request("POST", "/users/@me/channels", json_body={"recipient_id": str(destinataire_id)})
    if canal is None:
        return "echec"
    if canal.status_code == 403 and _code(canal) == REFUS_DISCORD:
        return "refuse"
    if canal.status_code != 200:
        return "echec"
    try:
        canal_id = canal.json()["id"]
    except (KeyError, TypeError, ValueError):
        return "echec"
    depot = await _bot_request("POST", f"/channels/{canal_id}/messages", json_body={"content": texte})
    if depot is None:
        return "echec"
    if depot.status_code == 200:
        return "envoye"
    if depot.status_code == 403 and _code(depot) == REFUS_DISCORD:
        return "refuse"
    return "echec"


async def passe() -> dict:
    """R3, R4. La passe : à la fin de chaque appel réussi, sous le verrou de
    `appel.faire_appel`. Pour chaque destinataire (R2), les nouveaux noms
    (R4) ; sans nouveau nom aucun MP, sinon un MP (R5) puis un envoi noté par
    nouveau nom, avec le statut du MP. Un envoi noté après chaque
    destinataire : une interruption ne refait jamais un MP parti. Rend un
    bilan `{statut: nombre de MP}`, pour le journal."""
    bilan = {"envoye": 0, "refuse": 0, "echec": 0}
    if not settings.DISCORD_BOT_TOKEN:
        return bilan
    async with AsyncSessionLocal() as db:
        retards = await retards_du_jour(db)
        if not retards:
            return bilan
        envois = [(e.destinataire_id, e.pilote_id, e.envoye_le, e.statut) for e in await _envois(db)]
        for dest_id, _nom in await destinataires(db):
            nouveaux = nouveaux_noms(envois, dest_id, retards)
            if not nouveaux:
                continue
            statut = await envoyer_mp(dest_id, texte_mp(retards, {r.id for r in nouveaux}))
            bilan[statut] += 1
            quand = datetime.now(timezone.utc)  # posé en Python, jamais par un défaut SQL (R6)
            for r in nouveaux:
                db.add(RelanceEnvoi(destinataire_id=dest_id, pilote_id=r.id, envoye_le=quand, statut=statut))
            await db.commit()
    return bilan
