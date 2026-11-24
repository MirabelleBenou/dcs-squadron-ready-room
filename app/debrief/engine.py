"""Moteur de fusion — spec SPEC_READY_ROOM_Debrief_Fusion_v1 (v1.1) §3-§7.

Principe cardinal (spec §7) : à CHAQUE upload, l'état dérivé de la session
(vols, events fusionnés, identités, stats, graveyard) est **recalculé
intégralement** depuis l'ensemble des fichiers bruts de la session (re-parse
depuis `DEBRIEF_STORAGE_DIR`). Idempotent, insensible à l'ordre d'arrivée.

--- Décisions d'implémentation à faire valider par Opus/le porteur --------------
Le brief laisse quelques points d'implémentation sous-spécifiés (le lot est
qualifié "cascade-trap" à raison). Choix pris ici, documentés pour revue :

1. **Priorité `manuel` vs ordre de liste §3.1** : le texte de la spec liste
   `declare > under_control > replication > acmi_type_unique > manuel`,
   mais §4.6 précise "manuel... prioritaire sur tout SAUF declare". Ces deux
   affirmations sont contradictoires si on lit la liste comme un ordre
   strict. On retient la description explicite de §4.6 (manuel = priorité 2,
   juste sous declare) plutôt que la position dans la liste énumérée.
   `IDENTITY_PRIORITY` ci-dessous encode ce choix.

2. **`identity_source='declare'`** n'est en pratique jamais produit par CE
   lot : l'API d'upload ne prend qu'un `depositor` (profile_id), pas une
   association directe à un `object_id` précis. `declare` établit QUI est le
   déposant ; c'est `under_control` qui relie ensuite cette identité à des
   `object_id` précis. `declare` reste dans l'enum/priorité pour une
   extension future (association directe object_id <-> déposant), non
   implémentée ici.

3. **`identity_state='rattachable'`** : non détaillé en §4. Interprété comme
   "un vrai callsign est connu (réplication / ACMI direct / acmi_type_unique)
   mais pas encore lié à un compte Ready Room précis" -- par opposition à
   `'nomme'` = `pilote_profile_id` réellement renseigné. Un enrichissement
   best-effort tente un match exact (casse-insensible) du callsign contre
   `profiles.global_name`/`username` ; en cas de match unique, promotion en
   `'nomme'` + `pilote_profile_id` renseigné.

4. **Détection "vol humain non identifié" (spec §1 règle 3 : "vol <type>
   anonyme")** : un `object_id` devient un candidat `debrief_flight` s'il
   est (a) énuméré par un `under control`, (b) marqué `PLAYER` dans un
   `*PilotName` n'importe où dans les events (fait 5 -- humain confirmé mais
   non nommé), ou (c) nommé par réplication (§4.4). Un `object_id` qui
   n'apparaît QUE via des `*PilotName` de type IA/unité connue n'est jamais
   un vol (véhicule/IA, hors périmètre "appareils volants").

5. **Déduplication d'events multi-fichiers vs multi-impacts intra-fichier**
   (fait 9 : 1 missile -> 2 `hit` légitimement distincts DANS LE MÊME
   fichier) : un appariement glouton par plus-proche-voisin en `t` est
   utilisé, avec la règle qu'**un même fichier ne peut jamais réclamer deux
   fois le même événement canonique** au sein d'une clé grossière donnée.
   Cela évite qu'un dédup naïf (fenêtre ±0.5s sans égard au fichier
   source) n'écrase à tort deux impacts réels d'un même missile. Les
   fichiers sont traités dans un ordre déterministe (tri par `sha256`),
   garantissant l'insensibilité à l'ordre d'arrivée réel des uploads.

6. **Précision par arme (spec §6.2)** : la distinction "arme à tir unitaire"
   vs "sous-munitions" repose sur une observation **à l'échelle de la
   session** : une arme dont AU MOINS UN `shot` a été vu "touché" (hit lié)
   quelque part dans la session est traitée comme unitaire (précision
   calculée par vol, y compris 0/N) ; une arme dont AUCUN `shot` n'est
   jamais lié à un `hit` sur toute la session est traitée comme
   sous-munition (`releases`, pas de précision). Le canon n'a pas de `shot`
   du tout (`start/end shooting`) et est traité à part (`cannon_bursts` /
   `cannon_hits`).
   Lot « La précision des armes — le moteur » (v1.0027) : cette devinette
   ne sert plus qu'aux armes de famille inconnue -- la famille lue dans le
   journal (`weapon_type`) décide désormais (`_FAMILLES_UNITAIRES`,
   `_FAMILLE_SOUS_MUNITIONS`), et le canon se compte rafale par rafale
   (`_canon_par_arme`).

Ces six points sont **à confirmer** dès que les 4 fichiers d'échantillon
réels (non fournis dans cette session d'exécution) pourront être testés --
cf. rapport de livraison, section "Limites de validation".

--- Décision d'implémentation #7 (HOTFIX jointure ACMI<->débrief par nom) ---

7. **Source du "callsign connu" côté débrief pour le join par nom** : le
   brief HOTFIX décrit un callsign "connu (ident.callsign, issu de
   réplication / under_control / profil)". Historique (v0.67) : `ident.
   callsign` n'était jamais renseigné pour la source `under_control`
   (aucun accès profil -> callsign à cet endroit, seul `profile_id` du
   déposant était connu) ; il ne l'était que pour `replication`. Quand un
   même `object_id` portait à la fois un candidat `under_control` (qui
   gagne, priorité 2) ET un candidat `replication`, `_resolve_identities`
   ne retenait que le meilleur candidat -- le callsign de réplication était
   alors perdu pour CE oid précis, mais restait disponible pour d'AUTRES
   oids under_control du même déposant/log sans jamais leur être propagé
   (cf. HOTFIX identité déposant #8 ci-dessous, qui corrige ce point en
   v0.68). `_build_flights` conserve néanmoins, en secours, un recalcul
   direct de `_collect_replication_candidates` comme source complémentaire
   indépendante de `_resolve_identities` (robustesse si un oid under_control
   n'a, malgré la propagation #8, toujours pas de callsign -- ex. déposant
   dont AUCUNE vie n'a jamais été répliquée par un tiers).

--- Décision d'implémentation #8 (HOTFIX identité déposant, v0.68) --------

8. **Toutes les vies `under_control` d'un déposant partagent le même
   callsign réel.** Constat (recette VM v0.67, session Foothold) : le
   `callsign` racine du `debrief.log` est corrompu/non fiable par
   construction (`callsign_header_unreliable`) et n'est jamais utilisé pour
   résoudre une identité. Sans lui, seule une partie des vies
   `under_control` d'un pilote (celles observées nommément par un AUTRE
   pilote via réplication) portait un callsign exploitable pour la
   jointure ACMI par nom ; les autres (souvent la majorité -- respawns)
   restaient `callsign=None`, empêchant leur jointure et faisant
   apparaître le pilote dédoublé (vies ACMI "Reconstitué" d'un côté, vies
   débrief anonymes "Débrief déposé" de l'autre). Principe validé par
   le porteur : **l'identité du déposant vient de l'upload, pas du log** -- un
   client ne contrôle que ses propres appareils/respawns, donc toutes les
   vies `under_control` d'un même `(upload, log)` appartiennent au même
   pilote et partagent donc le même vrai callsign. `_resolve_identities`
   calcule désormais, pour chaque `(upload, log)` avec `depositor_profile_id`
   défini, le callsign résolu par réplication sur N'IMPORTE LAQUELLE des
   vies `under_control` de CE log, et le propage à TOUTES les vies
   `under_control` de ce même log (tri déterministe par `object_id` pour la
   reproductibilité). Fallback : si aucune de ces vies n'a de callsign
   répliqué (personne ne l'a observé dans toute la session), l'attribution
   profil (identité nommée par le déposant) est conservée mais `callsign`
   reste `None` -- signalé en log ; ces vies ne peuvent alors pas rejoindre
   l'ACMI faute de callsign commun (alias ACMI déclaré par membre = §4.8,
   hors périmètre). Ce correctif renforce uniquement la source
   `under_control` : l'échelle `declare > manuel > under_control >
   replication > acmi_type_unique`, `_merge_events`/`_persist_events`,
   l'ancre temporelle, le rattachement et le mécanisme de join par nom
   lui-même (`_build_flights`) ne sont pas modifiés.

--- Lot « Le siège d'équipage » (v1.0066) ---

Un joueur monté en équipage dans l'appareil d'un autre (copilote, mitrailleur)
voit cet appareil `under control` dans son journal, à son nom, alors que le
pilote le porte sous son indicatif. Ce siège d'équipage n'est pas une vie du
déposant : il n'en reçoit ni l'identité ni l'indicatif, et ne compte dans
aucune de ses statistiques ; le vol reste à son pilote (le porteur, 2 novembre).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import re
import shutil
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.debrief import acmi as acmi_mod
from app.debrief import categorize
from app.debrief import debriefer as debriefer_mod
from app.debrief import lexique
from app.debrief import rattachement as rattachement_mod
from app.debrief import revision
from app.debrief_models import (
    Campaign,
    DebriefEvent,
    DebriefFlight,
    DebriefGraveyard,
    DebriefSession,
    DebriefUnitCategory,
    DebriefUpload,
    ProfileDcsAlias,
)
from app.models import Profile

logger = logging.getLogger(__name__)

# Namespace fixe (arbitraire, généré une fois) pour dériver des UUID
# déterministes à partir de clés naturelles -- garantit des `id` STABLES
# pour debrief_flight/debrief_event/debrief_graveyard à travers les
# recalculs successifs (nécessaire pour que POST .../identify continue de
# viser le même vol après un nouvel upload).
_UUID_NAMESPACE = uuid.UUID("6f1a9b3e-2d4c-4a3b-9e7f-0c8a5d2b7f61")

# Cf. décision d'implémentation #1 ci-dessus.
IDENTITY_PRIORITY = {
    "declare": 0,
    "manuel": 1,
    "under_control": 2,
    "replication": 3,
    "acmi_type_unique": 4,
}

_DEDUP_WINDOW_S = 0.5
_AI_PILOT_MARKER = "PLAYER"

# Brief Lot Fusion §2, geste 3 : `-1` n'est pas une coalition DCS (0 neutre,
# 1 rouge, 2 bleu) -- c'est la valeur écrite quand le moteur de jeu ne sait
# pas. Une chaîne non vide gelait ce camp définitivement dans
# `coalition_by_oid` et bloquait le repli ACMI, pourtant fiable en absolu
# (dérivé du `Color` Tacview). Ensemble explicite plutôt qu'un simple test
# de vérité, pour ne retenir que les coalitions réellement exploitables.
_COALITIONS_VALIDES = {"0", "1", "2"}


def _coalition_valide(brute: str | None) -> str | None:
    """Lot « Le passage moteur » : une coalition DCS admise, DÉTOURÉE -- ou
    `None`. Seul endroit où la validité se juge, pour l'initiateur comme pour
    la cible. Correctif ① du lot Fusion : la garde détourait pour tester mais
    rangeait la valeur brute -- `" 2 "` passait et ne valait `"2"` nulle part
    en aval."""
    valeur = str(brute or "").strip()
    return valeur if valeur in _COALITIONS_VALIDES else None


# Brief Lot Fusion §2, geste 4 -- seuil du repli des sauts : un poser suivi
# d'un décollage à moins de ce délai au sol se replie en `saut`. Constante
# posée par la connaissance du pilotage du porteur, PAS une mesure : les temps
# au sol observés sur la session du 14 septembre (33 / 59 / 70 / 76 / 94 /
# 149 s) ne présentent aucun trou où poser un seuil -- personne n'aurait pu
# le dériver des données. Au niveau du module depuis le lot « Le passage
# moteur » (correctif ② du lot Fusion) : elle était redéclarée à chaque vol.
_SAUT_SEUIL_S = 120.0

# Brief D2⑤ Volet A.1 : bruit massif mesuré sur la session CBU (2768 `failure`
# + 307 `score`, ~88 % des events) -- aucune stat ni résolution d'identité ne
# les utilise (cf. checkpoint invariant §5.19). Exclus AVANT toute prise en
# compte dans `_merge_events` -- ils disparaissent des events persistés ET
# des stats qui en dérivent. Ne touche PAS les collecteurs d'identité
# (under_control/réplication/player-marked), qui n'utilisent jamais ces
# types de toute façon.
_NOISE_EVENT_TYPES = frozenset({"failure", "score"})

_TIMESTAMP_SUFFIX_RE = re.compile(r"-\d{8}-\d{6}$")
_SESSION_MATCH_WINDOW_S = 6 * 3600  # tolérance de proximité reference_time (spec §3.5)

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_.\-]+")


class IngestError(Exception):
    pass


# =============================================================================
# 1. Rapprochement upload -> session (spec §3.5)
# =============================================================================


# Extension CONNUE uniquement (brief HOTFIX §3.a) -- PAS .stem : .stem
# coupe au dernier point et charcuterait un nom de mission versionné du
# type 'Foothold_GCW_V5.2.5_...' en 'foothold_gcw_v5.2'.
_KNOWN_EXT_RE = re.compile(r"\.(trk|miz|acmi|txt)$", re.IGNORECASE)


def _mission_name_pipeline(raw: str | None) -> str | None:
    """Pipeline partagé clé/titre (brief HOTFIX §3.a/§3.b) : nom de fichier
    (chemin Windows OU posix), extension connue retirée, suffixe(s)
    d'enregistrement `.trk` (`-AAAAMMJJ-HHMMSS`) retirés. Ni lower() ni
    strip final ici -- fait par les wrappers (clé vs titre d'affichage)."""
    if not raw:
        return None
    base = re.split(r"[\\/]+", raw)[-1]  # chemin Win OU posix -> nom de fichier
    base = _KNOWN_EXT_RE.sub("", base)
    prev = None
    while prev != base:  # suffixe(s) d'enregistrement .trk
        prev = base
        base = _TIMESTAMP_SUFFIX_RE.sub("", base)
    return base or None


def _normalize_mission_key(raw: str | None) -> str | None:
    """Clé de rattachement ACMI <-> débrief (brief HOTFIX §3.a) : le nom de
    mission est le seul jeton partagé entre les deux sources -- aucune date
    n'est plus jamais dérivée d'un nom de fichier (cf. Bug A)."""
    base = _mission_name_pipeline(raw)
    if base is None:
        return None
    return base.strip().lower() or None


def _display_mission_name(raw: str | None) -> str | None:
    """Titre d'affichage propre (brief HOTFIX §3.b) : même pipeline que la
    clé, SANS lower() -- préserve la casse d'origine."""
    base = _mission_name_pipeline(raw)
    if base is None:
        return None
    return base.strip() or None


def _real_start_debrief(header) -> datetime | None:
    """Début réel de mission : mark - durée (convergence <2 min avec le
    RecordingTime ACMI, mesuré sur données réelles). Jamais depuis un nom
    de fichier (décision du porteur)."""
    if header.mission_file_mark is None:
        return None
    dt = datetime.fromtimestamp(header.mission_file_mark, tz=timezone.utc)
    if header.mission_time:
        dt -= timedelta(seconds=header.mission_time)
    return dt


async def _resolve_session(
    db: AsyncSession,
    *,
    candidate_title: str | None,
    reference_time: datetime | None,
) -> DebriefSession:
    key = _normalize_mission_key(candidate_title)
    candidates: list[DebriefSession] = []
    if key:
        result = await db.execute(select(DebriefSession))
        for sess in result.scalars().all():
            if _normalize_mission_key(sess.title) == key:
                candidates.append(sess)

    if candidates:
        if reference_time is not None:
            close = [
                c
                for c in candidates
                if c.reference_time is not None
                and abs((c.reference_time - reference_time).total_seconds())
                <= _SESSION_MATCH_WINDOW_S
            ]
            if len(close) == 1:
                return close[0]
            without_ref = [c for c in candidates if c.reference_time is None]
            if not close and len(without_ref) == 1:
                return without_ref[0]
        elif len(candidates) == 1:
            return candidates[0]
        # Ambigu (plusieurs candidats plausibles) -> ne jamais fusionner à
        # tort (spec §3.5) : on retombe sur la création d'une session neuve.

    new_session = DebriefSession(
        title=candidate_title or "Session sans titre",
        reference_time=reference_time,
        mission_date=reference_time.date() if reference_time else None,
        sim="dcs",  # détection simulateur à l'ingestion : DCS (seul parseur) — spec §7
    )
    db.add(new_session)
    await db.flush()
    return new_session


async def _session_par_contenu(db: AsyncSession, events) -> DebriefSession | None:
    """Lot « Le rattachement des dépôts » (v1.0052, R326) -- la session d'un
    `debrief.log` par son CONTENU, avant tout en-tête : parmi les sessions
    créées dans les `FENETRE_JOURS` qui précèdent le dépôt, celle dont les
    faits persistés (`DebriefEvent` des types `FAITS` : `type`,
    `initiator_object_id`, `t` seulement) recouvrent ceux du journal
    (`rattachement.taux_communs`, puis `rattachement.choisir`). `None` si
    aucune ne passe les seuils : `_resolve_session` décide alors, inchangée.
    Ne lit rien d'autre et n'écrit rien."""
    faits = rattachement_mod.faits_du_journal(events)
    if not faits:
        return None
    depuis = datetime.now(timezone.utc) - timedelta(days=rattachement_mod.FENETRE_JOURS)
    sessions = (
        await db.execute(select(DebriefSession).where(DebriefSession.created_at >= depuis))
    ).scalars().all()
    if not sessions:
        return None
    par_session: dict[uuid.UUID, list] = defaultdict(list)
    rows = (
        await db.execute(
            select(
                DebriefEvent.session_id,
                DebriefEvent.type,
                DebriefEvent.initiator_object_id,
                DebriefEvent.t,
            ).where(
                DebriefEvent.session_id.in_([s.id for s in sessions]),
                DebriefEvent.type.in_(sorted(rattachement_mod.FAITS)),
            )
        )
    ).all()
    # Pas les `Row` eux-mêmes : `Row.t` est l'accesseur de tuple de SQLAlchemy,
    # pas la colonne `t`.
    for sid, typ, oid, t in rows:
        par_session[sid].append(SimpleNamespace(type=typ, t=t, initiator_object_id=oid))
    candidats = []
    for sess in sessions:
        n, d = rattachement_mod.taux_communs(
            faits, rattachement_mod.faits_du_journal(par_session.get(sess.id, ()))
        )
        candidats.append((sess, n, d))
    return rattachement_mod.choisir(candidats)


# =============================================================================
# 2. Ingestion d'un upload (hash anti-doublon, stockage brut, déclenchement
#    du recalcul complet)
# =============================================================================


def _safe_filename(name: str) -> str:
    base = Path(name).name  # retire tout chemin
    return _SAFE_FILENAME_RE.sub("_", base) or "fichier"


def _storage_dir() -> Path:
    d = Path(settings.DEBRIEF_STORAGE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _apply_optional_deposit_fields(
    session: DebriefSession,
    mission_name: str | None,
    wing_note: str | None,
    campaign_id: uuid.UUID | None,
) -> tuple[bool, bool, bool, bool]:
    """Nom/note/campagne de dépôt (Lot 2.1 §4.4/§4.6 ; Lot 2.3 §4.5) :
    nom et note appliqués **si et seulement si** le champ correspondant de
    la session est encore vide -- c'est ce qui rend le dépôt multi-fichiers
    idempotent (le même nom envoyé avec chacun des fichiers ne s'applique
    qu'une fois, spec §6). Mutation en mémoire sur la session déjà résolue ;
    flush/commit délégués à l'appelant. Ne touche jamais `title` -- aucun de
    ces champs n'entre dans le pipeline de rattachement.

    La campagne suit une mécanique voisine mais à trois issues (brief
    §4.5, arbitrage du porteur du 13 août) : session sans campagne + dépôt
    avec campagne -> posée ; session avec campagne + dépôt sans campagne ->
    héritée en silence, rien n'est écrit ; session avec campagne + dépôt
    avec une AUTRE campagne -> rien n'est écrit, conflit signalé (jamais de
    geste "Conserver / Remplacer" ici, réservé au management). La validité
    du `campaign_id` (existence en base) est vérifiée par l'appelant, avant
    ce point -- ici on ne fait que la mécanique d'application."""
    name_applied = False
    if mission_name is not None and session.display_name is None:
        session.display_name = mission_name
        name_applied = True
    note_applied = False
    if wing_note is not None and session.wing_note is None:
        session.wing_note = wing_note
        note_applied = True
    campaign_applied = False
    campaign_conflict = False
    if campaign_id is not None:
        if session.campaign_id is None:
            session.campaign_id = campaign_id
            campaign_applied = True
        elif session.campaign_id != campaign_id:
            campaign_conflict = True
        # else : même campagne déjà posée -- rien à écrire, pas un conflit.
    return name_applied, note_applied, campaign_applied, campaign_conflict


# Lot « Un dépôt à la fois » (`v1.0072`, ARC-02) : un seul processus (même
# hypothèse que `app/appel.py`) ; sans ce verrou, deux dépôts du même vol
# créaient deux sessions, la neuve de l'un étant invisible à l'autre avant son `commit`.
# Suppose aussi le niveau d'isolement par défaut de PostgreSQL (READ COMMITTED) :
# sous un niveau plus strict, le second dépôt ne verrait pas la session validée du premier.
_verrou_depot = asyncio.Lock()


async def ingest_file(
    db: AsyncSession,
    *,
    kind: str,
    depositor_profile_id: Optional[int],
    filename: str,
    raw_bytes: bytes,
    mission_name: str | None = None,
    wing_note: str | None = None,
    campaign_id: uuid.UUID | None = None,
) -> dict:
    """Point d'entrée de `POST /api/debrief/upload`. Retourne un résumé de
    session (cf. `_session_summary`).

    `mission_name`/`wing_note` (Lot 2.1, addendum A2) : donnée brute
    uniquement -- `display_name`, `wing_note`, `name_applied`, `note_applied`
    ajoutés au résumé ci-dessous. Aucun embellissement ici (cf.
    `app/debrief/display.py`, jamais importé par ce module) : la résolution
    d'affichage se fait exclusivement côté API (règle d'architecture phase 2,
    addendum A2).

    `campaign_id` (Lot 2.3, §4.5) : même patron -- donnée brute, mécanique
    d'application déléguée à `_apply_optional_deposit_fields`,
    `campaign_applied`/`campaign_conflict` ajoutés au résumé. Un
    `campaign_id` inconnu en base lève `IngestError` (-> 422 côté route),
    jamais une clé étrangère qui casse au commit -- vérifié ici, avant tout
    effet de bord (fichier temporaire, session résolue, etc.).

    Lot « Un dépôt à la fois » (`v1.0072`, ARC-02) : tout le dépôt, du
    contrôle du sha256 au dernier `commit`, se joue sous `_verrou_depot` --
    deux dépôts du même vol ne créent plus deux sessions."""
    async with _verrou_depot:
        return await _ingest_file_sous_verrou(
            db,
            kind=kind,
            depositor_profile_id=depositor_profile_id,
            filename=filename,
            raw_bytes=raw_bytes,
            mission_name=mission_name,
            wing_note=wing_note,
            campaign_id=campaign_id,
        )


async def _ingest_file_sous_verrou(
    db: AsyncSession,
    *,
    kind: str,
    depositor_profile_id: Optional[int],
    filename: str,
    raw_bytes: bytes,
    mission_name: str | None = None,
    wing_note: str | None = None,
    campaign_id: uuid.UUID | None = None,
) -> dict:
    """Corps de `ingest_file`, joué sous `_verrou_depot` (lot « Un dépôt à la fois »)."""
    if kind not in ("acmi", "debrief"):
        raise IngestError(f"kind invalide : {kind!r}")
    if kind == "debrief" and depositor_profile_id is None:
        raise IngestError("depositor requis pour un upload de type 'debrief'")
    if campaign_id is not None:
        campaign = await db.get(Campaign, campaign_id)
        if campaign is None:
            raise IngestError(f"campaign_id inconnu : {campaign_id}")
    # Lot « Un dépôt à la fois » (ARC-23) : un déposant inconnu est refusé ici
    # (422), jamais une clé étrangère qui casse au commit.
    if depositor_profile_id is not None:
        if await db.get(Profile, depositor_profile_id) is None:
            raise IngestError(f"depositor inconnu : {depositor_profile_id}")

    sha = hashlib.sha256(raw_bytes).hexdigest()
    existing = await db.scalar(
        select(DebriefUpload).where(DebriefUpload.sha256 == sha)
    )
    if existing is not None:
        # Re-dépôt strict d'un fichier déjà présent = no-op (spec §7.1).
        # Lot 2.1 : le nom/la note peuvent tout de même s'appliquer (champ
        # encore vide) -- un re-dépôt identique reste un moment légitime
        # pour renseigner un nom pas encore saisi. D'où le commit, absent
        # de cette branche avant ce lot (rien n'y était jamais muté).
        session = await db.get(DebriefSession, existing.session_id)
        name_applied, note_applied, campaign_applied, campaign_conflict = (
            _apply_optional_deposit_fields(
                session, mission_name, wing_note, campaign_id
            )
        )
        if name_applied or note_applied or campaign_applied:
            await db.commit()
        summary = await _session_summary(db, existing.session_id)
        summary["no_op"] = True
        summary["session_created"] = False
        summary["display_name"] = session.display_name if session else None
        summary["wing_note"] = session.wing_note if session else None
        summary["name_applied"] = name_applied
        summary["note_applied"] = note_applied
        summary["campaign_applied"] = campaign_applied
        summary["campaign_conflict"] = campaign_conflict
        return summary

    tmp_dir = _storage_dir() / "_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{sha}_{_safe_filename(filename)}"
    await asyncio.to_thread(tmp_path.write_bytes, raw_bytes)

    try:
        if kind == "acmi":
            parsed_meta = await asyncio.to_thread(acmi_mod.parse_acmi, tmp_path)
            candidate_title = parsed_meta.meta.title
            # Ancre = RecordingTime (horodatage réel) -- PLUS JAMAIS
            # reference_time (temps du scénario DCS, cf. Bug A). Fallback
            # None si absent (pas de repli sur le temps DCS).
            reference_time = parsed_meta.meta.recording_time
        else:
            parsed_meta = await asyncio.to_thread(
                debriefer_mod.parse_debrief_log, tmp_path
            )
            candidate_title = _display_mission_name(parsed_meta.header.mission_file_path)
            reference_time = _real_start_debrief(parsed_meta.header)

        # Lot « Le rattachement des dépôts » (R326) : un journal rejoint
        # d'abord la session dont il partage les faits, quel que soit son
        # en-tête ; `_resolve_session` (inchangée) n'est plus que le repli.
        # Un ACMI se rattache comme avant.
        session = None
        if kind == "debrief":
            session = await _session_par_contenu(db, parsed_meta.events)
        par_contenu = session is not None
        if session is None:
            session = await _resolve_session(
                db, candidate_title=candidate_title, reference_time=reference_time
            )

        # Lot 2.1 : "mission créée ou rejointe" (spec §4.4), sans toucher
        # _resolve_session (protégée, §2/§5.1) -- déduit indirectement en
        # comptant les uploads déjà attachés à la session retenue, AVANT
        # que celui-ci n'y ajoute le sien : 0 => session neuve créée par
        # _resolve_session à l'instant, sinon => session existante rejointe.
        existing_upload = await db.scalar(
            select(DebriefUpload.id)
            .where(DebriefUpload.session_id == session.id)
            .limit(1)
        )
        session_created = existing_upload is None

        name_applied, note_applied, campaign_applied, campaign_conflict = (
            _apply_optional_deposit_fields(
                session, mission_name, wing_note, campaign_id
            )
        )

        # Backfill à l'attache (brief HOTFIX §2.b) : couvre le cas d'une
        # session créée sans ancre à laquelle un upload ultérieur en
        # apporte une (ex. débrief sans ancre puis ACMI, ou l'inverse).
        if session.reference_time is None and reference_time is not None:
            session.reference_time = reference_time
            session.mission_date = reference_time.date()

        final_dir = _storage_dir() / str(session.id)
        final_dir.mkdir(parents=True, exist_ok=True)
        final_path = final_dir / f"{sha}_{_safe_filename(filename)}"
        await asyncio.to_thread(shutil.move, str(tmp_path), str(final_path))
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)

    # Lot « Un dépôt à la fois » (ARC-23) : un échec après le déplacement du
    # fichier brut le retire avant de remonter -- aucun fichier orphelin.
    try:
        upload = DebriefUpload(
            session_id=session.id,
            kind=kind,
            depositor_profile_id=depositor_profile_id,
            filename=filename,
            sha256=sha,
            raw_stored_path=str(final_path),
            # Lot « Le rattachement des dépôts » : la provenance, lue à l'écran.
            rattachement=rattachement_mod.rattachement_du_depot(
                par_contenu,
                _normalize_mission_key(session.title),
                _normalize_mission_key(candidate_title),
            ),
            entete_titre=candidate_title,
            entete_exemple=(
                kind == "debrief"
                and rattachement_mod.entete_exemple(parsed_meta.header.mission_file_path)
            ),
        )
        db.add(upload)
        if kind == "acmi":
            session.acmi_present = True
        await db.flush()

        summary = await recompute_session(db, session.id)
        await db.commit()
    except Exception:
        final_path.unlink(missing_ok=True)
        raise
    summary["no_op"] = False
    summary["session_created"] = session_created
    summary["display_name"] = session.display_name
    summary["wing_note"] = session.wing_note
    summary["name_applied"] = name_applied
    summary["note_applied"] = note_applied
    summary["campaign_applied"] = campaign_applied
    summary["campaign_conflict"] = campaign_conflict
    return summary


# =============================================================================
# 3. Fusion des events (spec §3.3/§5)
# =============================================================================


@dataclass
class MergedEvent:
    type: str
    t: float
    initiator_object_id: str | None
    target_object_id: str | None
    initiator_unit_type: str | None
    target_unit_type: str | None
    weapon: str | None
    # Lot « Le passage moteur » : camp de la cible, validé par
    # `_coalition_valide` -- le premier journal qui le donne l'emporte, comme
    # pour les autres champs. HORS de `natural_key` : il ne distingue pas
    # deux faits, il qualifie celui qu'on a.
    target_coalition: str | None = None
    # Lot « La précision des armes — le moteur » : la famille de l'arme,
    # décodée de `weapon_type` (`_famille_arme`), et le nombre d'obus tirés
    # d'une fin de rafale (`ammo_consumption`, `_munitions_tirees`). Le
    # premier journal qui les donne l'emporte. HORS de `natural_key`, comme
    # le camp de la cible : ils qualifient le fait, ils ne le distinguent pas.
    weapon_family: int | None = None
    ammo: int | None = None
    seen_in: list[str] = field(default_factory=list)
    event_id_by_upload: dict[str, str] = field(default_factory=dict)
    linked_event_id_by_upload: dict[str, str] = field(default_factory=dict)

    def natural_key(self) -> str:
        ioid = self.initiator_object_id or "0"
        return f"{self.type}|{ioid}|{self.target_object_id or ''}|{self.weapon or ''}|{round(self.t, 1)}"


def _coarse_event_key(
    ev_type: str,
    t: float,
    ioid: str | None,
    toid: str | None,
    weapon: str | None,
    ioid_unit_type: str | None,
    toid_unit_type: str | None,
) -> tuple:
    if ioid in (None, "", "0"):
        return ("degraded", ev_type, round(t), toid, weapon, ioid_unit_type, toid_unit_type)
    # Lot Moteur §2 (A1) : un abattage se regroupe sur (tireur, cible)
    # SEUL -- l'arme sort de la clé. Fait mesuré : deux journaux d'une même
    # session peuvent nommer la même arme différemment (canon vs obus,
    # p.ex. `M256_120_HE` / `M830 (120mm HEAT-MP-T)`, ou un champ vide côté
    # d'un des deux logs) -- garder l'arme dans la clé fabriquait deux
    # événements canoniques distincts pour un seul abattage réel. Invariant
    # qui justifie ce regroupement : un tireur ne tue jamais deux fois la
    # même cible (vérifié sur la fixture -- aucun des 590 object_id ne
    # porte deux types d'unité, un identifiant DCS n'est jamais recyclé en
    # mission). Ne s'applique qu'à la branche "std" (tireur ET cible
    # réels) -- la branche dégradée (sans initiateur réel) garde sa clé
    # actuelle, inchangée. Tous les autres types d'événement gardent aussi
    # leur clé "std" habituelle (ioid, toid, weapon).
    if ev_type == "kill" and _is_real_oid(toid):
        return ("kill-par-tireur", ioid, toid)
    # Lot « Les quatre dernières dettes » (`v1.0046`) : l'arme sort aussi de
    # la clé "std". Un impact vu par deux journaux est un seul impact : deux
    # évènements de journaux différents, du même type, du même tireur réel
    # et de la même cible, dans la fenêtre de leur type, se rapprochent si
    # leurs armes (après `lexique.canon_arme`) sont égales ou si l'une des
    # deux est vide ; deux armes nommées et différentes ne se rapprochent
    # jamais. Ce jugement se fait dans `_merge_events`, canonique par
    # canonique. Fait mesuré le 15 octobre 2026 sur les 12 sessions de
    # production : 319 impacts vus par deux journaux, l'un avec l'arme et
    # l'autre sans, à 0,47 s au plus d'écart, sur 4 sessions -- l'arme dans
    # la clé les séparait, et chacun comptait deux fois. Dans un même journal,
    # la règle du même journal (`_merge_events`) garde distincts les vrais
    # impacts multiples (sous-munitions).
    return ("std", ev_type, ioid, toid)


def _dedup_window_for(ev_type: str) -> float:
    """Lot Moteur §2 (A2) : fenêtre de rapprochement temporel inter-
    fichiers, PAR TYPE d'événement. Un abattage ne connaît aucune fenêtre
    (`math.inf`) -- une fois la clé (tireur, cible) formée (cf.
    `_coarse_event_key`), deux événements qui la partagent SONT le même
    abattage, quel que soit l'écart mesuré entre les horodatages rapportés
    par les différents journaux (fait mesuré sur la fixture : jusqu'à 10 s
    d'écart entre deux rapports du même abattage). Élargir la fenêtre de
    `_DEDUP_WINDOW_S` pour TOUS les types serait dangereux (risque de
    fusionner deux événements distincts rapprochés dans le temps) -- cette
    fonction isole le cas `kill`, qui seul bénéficie d'un invariant fort
    justifiant l'absence de fenêtre. `_DEDUP_WINDOW_S` reste à `0.5` pour
    tous les autres types, inchangé."""
    return math.inf if ev_type == "kill" else _DEDUP_WINDOW_S


# Lot « La précision des armes — le moteur » : la famille de l'arme, lue
# dans le journal DCS au lieu d'être devinée. C'est l'octet
# `(weapon_type >> 8) & 0xFF` du code d'arme DCS -- mesuré par le CdP sur les
# 22 journaux de production du 9 octobre 2026.
_FAMILLES_UNITAIRES = frozenset({
    7,   # missile air-air
    8,   # missile air-sol
    9,   # bombe
    11,  # missile antichar
    33,  # roquette
    36,  # bombe guidée
})
_FAMILLE_SOUS_MUNITIONS = 38  # arme à sous-munitions : jamais liée à ses impacts
# Lot « Le Débrief : la précision des roquettes par salve » : la roquette est
# une arme de saturation ; elle se lit en salves au but sur salves.
_FAMILLE_ROQUETTE = 33
# Une salve : largages successifs de la même arme, chacun à 5 s au plus du
# précédent ; elle touche si un impact de sous-munition tombe dans les 60 s
# qui suivent son dernier largage.
_SALVE_ECART_S = 5.0
_SALVE_FENETRE_S = 60.0
# Lot « Le Débrief : la précision des roquettes par salve » : une destruction
# avec la même roquette revient à la salve si elle suit son dernier tir de 120 s
# au plus.
_SALVE_ROQUETTE_FENETRE_S = 120.0
# Un obus au but tombe au plus 4 s après la fin de sa rafale.
_CANON_FENETRE_S = 4.0
# Lot « Un seul journal fait foi pour les tirs d'un vol » : des débuts de
# rafale de la même arme, du même vol, à moins de 0,1 s l'un de l'autre sont
# une seule pression de détente -- un canon double (Mirage F1, F-5E) écrit
# deux débuts puis deux fins au même instant, une paire par canon.
_CANON_DOUBLE_S = 0.1
# Lot « Un seul journal fait foi pour les tirs d'un vol » : les faits de tir
# d'un vol, comptés sur son seul journal source, et ceux qui lui en donnent un.
_TYPES_TIR = frozenset({"shot", "hit", "start shooting", "end shooting"})
_TYPES_TIR_INITIAL = frozenset({"shot", "start shooting"})


def _famille_arme(raw: dict) -> int | None:
    """Lot « La précision des armes — le moteur » : `(weapon_type >> 8) &
    0xFF` quand le journal porte un `weapon_type` entier, sinon `None` --
    jamais deviné."""
    try:
        return (int(raw["weapon_type"]) >> 8) & 0xFF
    except (KeyError, TypeError, ValueError):
        return None


def _munitions_tirees(ev_type: str, raw: dict) -> int | None:
    """Lot « La précision des armes — le moteur » : le nombre d'obus tirés,
    que DCS écrit sur la fin d'une rafale (`end shooting`) ; `None` ailleurs,
    ou quand le journal ne le porte pas."""
    if ev_type != "end shooting":
        return None
    try:
        return int(raw["ammo_consumption"])
    except (KeyError, TypeError, ValueError):
        return None


def _merge_events(
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]]
) -> list[MergedEvent]:
    """Fusion + dédup inter-fichiers. Cf. décision d'implémentation #5 en
    tête de module pour la justification de l'appariement glouton."""
    ordered = sorted(debrief_pairs, key=lambda pair: pair[0].sha256)
    canon_by_coarse: dict[tuple, list[MergedEvent]] = defaultdict(list)

    for upload, log_data in ordered:
        upload_id = str(upload.id)
        events = sorted(log_data.events, key=lambda e: (e.t if e.t is not None else 0.0))
        for e in events:
            if e.type in _NOISE_EVENT_TYPES:
                # Volet A.1 : exclu avant toute prise en compte (fusion,
                # dédup, persistance, stats) -- cf. constante ci-dessus.
                continue
            t = e.t if e.t is not None else 0.0
            ev_type = e.type or ""
            w = lexique.canon_arme(e.weapon)
            camp_cible = _coalition_valide(e.target_coalition)
            famille = _famille_arme(e.raw)
            munitions = _munitions_tirees(ev_type, e.raw)
            key = _coarse_event_key(
                ev_type, t, e.initiator_object_id, e.target_object_id, w,
                e.initiator_unit_type, e.target_unit_type,
            )
            bucket = canon_by_coarse[key]
            best: MergedEvent | None = None
            best_dt: float | None = None
            window = _dedup_window_for(ev_type)
            for canon in bucket:
                if upload_id in canon.seen_in:
                    # Ce fichier a déjà réclamé ce canonique -> un event
                    # supplémentaire du MÊME fichier à une clé grossière
                    # identique est un événement DISTINCT (multi-impacts,
                    # fait 9), jamais un doublon inter-fichiers.
                    continue
                if key[0] == "std" and canon.weapon and w and canon.weapon != w:
                    # Lot « Les quatre dernières dettes » : dans la branche
                    # "std", deux armes nommées et différentes ne se
                    # rapprochent jamais ; une arme vide se rapproche de toute
                    # arme (cf. `_coarse_event_key`). L'abattage et la branche
                    # dégradée gardent leur règle.
                    continue
                dt = abs(canon.t - t)
                if dt <= window and (best is None or dt < best_dt):
                    best = canon
                    best_dt = dt
            if best is not None:
                best.seen_in.append(upload_id)
                if e.event_id is not None:
                    best.event_id_by_upload[upload_id] = e.event_id
                if e.linked_event_id is not None:
                    best.linked_event_id_by_upload[upload_id] = e.linked_event_id
                best.t = min(best.t, t)
                best.initiator_unit_type = best.initiator_unit_type or e.initiator_unit_type
                best.target_unit_type = best.target_unit_type or e.target_unit_type
                best.weapon = best.weapon or w
                best.target_object_id = best.target_object_id or e.target_object_id
                best.target_coalition = best.target_coalition or camp_cible
                # Le premier journal l'emporte -- `is None`, pas `or` : 0 est
                # une valeur (une famille 0, une rafale de 0 obus).
                if best.weapon_family is None:
                    best.weapon_family = famille
                if best.ammo is None:
                    best.ammo = munitions
            else:
                new_canon = MergedEvent(
                    type=ev_type,
                    t=t,
                    initiator_object_id=e.initiator_object_id,
                    target_object_id=e.target_object_id,
                    initiator_unit_type=e.initiator_unit_type,
                    target_unit_type=e.target_unit_type,
                    weapon=w,
                    target_coalition=camp_cible,
                    weapon_family=famille,
                    ammo=munitions,
                    seen_in=[upload_id],
                    event_id_by_upload=(
                        {upload_id: e.event_id} if e.event_id is not None else {}
                    ),
                    linked_event_id_by_upload=(
                        {upload_id: e.linked_event_id} if e.linked_event_id is not None else {}
                    ),
                )
                bucket.append(new_canon)

    merged: list[MergedEvent] = []
    for bucket in canon_by_coarse.values():
        for m in bucket:
            m.seen_in = sorted(set(m.seen_in))
            merged.append(m)
    return merged


# =============================================================================
# 3 bis. La destruction probable, attribuée par l'ACMI
# =============================================================================
# Lot « Le Débrief : la destruction probable » (v1.0056, R2 à R8) : une unité
# que les journaux donnent morte (`dead`, `crash`) sans qu'aucun `kill` ne la
# vise reçoit le tueur que l'ACMI désigne. Son retrait de l'ACMI marque
# l'impact mortel ; les armes retirées dans la seconde qui précède sont
# remontées à leur tireur par les tirs (puis les rafales), l'heure de l'ACMI
# recalée sur celle des journaux par les tirs. Décision du porteur, 28 octobre :
# ce kill compte comme un kill DCS, collatéraux compris.

_KP_FENETRE_S = 1.0          # armes retirées jusqu'à 1,0 s avant la victime
_KP_TOLERANCE_FIN_S = 0.05   # ... et jusqu'à 0,05 s après
_KP_TOLERANCE_TIR_S = 0.15   # un tir et l'apparition de son arme
_KP_MARGE_RAFALE_S = 0.3     # une rafale et l'apparition de ses projectiles
_KP_COINCIDENCES_MIN = 10    # paires au mode du recalage, au moins


def _cle_acmi(oid: str | None) -> str | None:
    """Lot « La destruction probable » (R4) : la clé ACMI d'un object_id DCS,
    `hex((object_id & 0xFFFFFF) + 1)`. `None` si l'identifiant n'est pas un
    entier (aucun objet ACMI ne lui répond alors)."""
    try:
        return format((int(oid) & 0xFFFFFF) + 1, "x")
    except (TypeError, ValueError):
        return None


def _kp_recalage(merged_events: list[MergedEvent], objets) -> float | None:
    """Lot « La destruction probable » (R3) : le décalage `off` tel que heure
    ACMI ≈ heure du journal + `off`, recalé par les tirs. `None` si le mode
    réunit moins de `_KP_COINCIDENCES_MIN` paires."""
    apparitions = [
        o.t_spawn for o in objets
        if o.t_spawn is not None and (o.type or "").startswith("Weapon")
    ]
    tirs = [e.t for e in merged_events if e.type == "shot"]
    ecarts = Counter(round(w - t, 1) for w in apparitions for t in tirs)
    if not ecarts:
        return None
    mode, nombre = min(ecarts.items(), key=lambda kv: (-kv[1], kv[0]))
    if nombre < _KP_COINCIDENCES_MIN:
        return None
    proches = [
        w - t for w in apparitions for t in tirs
        if abs((w - t) - mode) <= _KP_TOLERANCE_TIR_S
    ]
    return sum(proches) / len(proches)


def _kp_rafales(merged_events: list[MergedEvent]) -> list[tuple[MergedEvent, MergedEvent]]:
    """Lot « La destruction probable » (R6) : les rafales, paires
    `start shooting` -> `end shooting` du même initiateur, dans l'ordre des
    `t` (à égalité, l'ordre de la liste). Une rafale jamais fermée n'en est
    pas une."""
    ouvertes: dict[str | None, MergedEvent] = {}
    rafales: list[tuple[MergedEvent, MergedEvent]] = []
    for e in sorted(merged_events, key=lambda e: e.t):
        if e.type == "start shooting":
            if e.initiator_object_id not in ouvertes:
                ouvertes[e.initiator_object_id] = e
        elif e.type == "end shooting":
            debut = ouvertes.pop(e.initiator_object_id, None)
            if debut is not None:
                rafales.append((debut, e))
    return rafales


def _kills_probables(
    merged_events: list[MergedEvent], acmi_data: acmi_mod.AcmiData | None
) -> list[MergedEvent]:
    """Lot « Le Débrief : la destruction probable » (v1.0056, R2 à R8) : les
    kills que l'ACMI désigne pour les morts sans tueur. Pure : ne modifie
    pas ses entrées, rend des `MergedEvent` neufs, triés par
    `(t, target_object_id)`. `[]` sans ACMI, sans objet, ou si le recalage
    échoue."""
    if acmi_data is None or not acmi_data.objects:
        return []
    objets = acmi_data.objects
    off = _kp_recalage(merged_events, objets.values())
    if off is None:
        return []

    # R4 -- les victimes : le premier `dead`/`crash` de chaque initiateur réel,
    # hors des cibles d'un `kill`.
    deja_tues = {e.target_object_id for e in merged_events if e.type == "kill"}
    morts: dict[str, MergedEvent] = {}
    for e in sorted(merged_events, key=lambda e: e.t):
        if e.type not in ("dead", "crash") or not _is_real_oid(e.initiator_object_id):
            continue
        if e.initiator_object_id not in morts:
            morts[e.initiator_object_id] = e

    tirs = [e for e in merged_events if e.type == "shot" and _is_real_oid(e.initiator_object_id)]
    rafales = _kp_rafales(merged_events)
    armes_retirees = [
        o for o in objets.values()
        if o.retire and (o.type or "").startswith(("Weapon", "Projectile"))
    ]

    def _camp_admis(arme, ev: MergedEvent) -> bool:
        # R6 -- le camp : l'arme sans coalition, le tireur sans objet ACMI ou
        # sans coalition, ou les deux coalitions égales.
        if arme.coalition is None:
            return True
        tireur = objets.get(_cle_acmi(ev.initiator_object_id))
        if tireur is None or tireur.coalition is None:
            return True
        return tireur.coalition == arme.coalition

    def _retenus(arme) -> list[MergedEvent]:
        # R6 -- par les tirs, puis par les rafales (projectiles seulement).
        if arme.t_spawn is None:
            return []
        evs = [e for e in tirs if abs(e.t + off - arme.t_spawn) <= _KP_TOLERANCE_TIR_S]
        if not evs and (arme.type or "").startswith("Projectile"):
            evs = [
                debut for debut, fin in rafales
                if debut.t + off - _KP_MARGE_RAFALE_S
                <= arme.t_spawn
                <= fin.t + off + _KP_MARGE_RAFALE_S
            ]
        return [e for e in evs if _camp_admis(arme, e)]

    kills: list[MergedEvent] = []
    for victime, mort in morts.items():
        if victime in deja_tues:
            continue
        obj = objets.get(_cle_acmi(victime))
        if obj is None or not obj.retire:
            continue
        segments = (obj.type or "").split("+")
        if segments[0] not in ("Air", "Ground", "Sea") or "Static" in segments:
            continue
        if obj.name != mort.initiator_unit_type:
            continue

        # R5 -- les armes de la fenêtre ; les adverses seules s'il y en a.
        armes = [
            a for a in armes_retirees
            if obj.t_despawn - _KP_FENETRE_S <= a.t_despawn <= obj.t_despawn + _KP_TOLERANCE_FIN_S
        ]
        if not armes:
            continue
        adverses = [a for a in armes if a.coalition is not None and a.coalition != obj.coalition]
        if adverses:
            armes = adverses

        # R7 -- la décision : chaque arme a un évènement retenu, un seul
        # tireur pour toutes, qui n'est pas la victime.
        retenus = {a.track_id: _retenus(a) for a in armes}
        if any(not evs for evs in retenus.values()):
            continue
        tireurs = {e.initiator_object_id for evs in retenus.values() for e in evs}
        if len(tireurs) != 1:
            continue
        tireur = next(iter(tireurs))
        if tireur == victime:
            continue

        # R8 -- le kill rendu ; l'évènement de référence vient de la dernière
        # arme retirée.
        ref_arme = max(armes, key=lambda a: (a.t_despawn, a.track_id))
        ref = min(
            retenus[ref_arme.track_id],
            key=lambda e: (abs(e.t + off - ref_arme.t_spawn), e.t),
        )
        kills.append(MergedEvent(
            type="kill",
            t=mort.t,
            initiator_object_id=tireur,
            target_object_id=victime,
            initiator_unit_type=ref.initiator_unit_type,
            target_unit_type=mort.initiator_unit_type,
            weapon=ref.weapon,
            target_coalition=obj.coalition,
            weapon_family=ref.weapon_family,
            ammo=None,
            seen_in=[],
            event_id_by_upload={},
            linked_event_id_by_upload={},
        ))
    kills.sort(key=lambda k: (k.t, k.target_object_id))
    return kills


# =============================================================================
# 4. Fusion du graveyard (spec §5 : dédup (type, x, y) arrondi au mètre)
# =============================================================================


@dataclass
class MergedGraveyard:
    unit_type: str
    coalition: str | None
    x: float
    y: float
    alt: float | None
    heading: float | None
    seen_in: list[str] = field(default_factory=list)


def _merge_graveyard(
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]]
) -> list[MergedGraveyard]:
    ordered = sorted(debrief_pairs, key=lambda pair: pair[0].sha256)
    canon: dict[tuple, MergedGraveyard] = {}
    for upload, log_data in ordered:
        upload_id = str(upload.id)
        for g in log_data.graveyard:
            if g.x is None or g.y is None:
                continue
            key = (g.unit_type or "Inconnu", round(g.x), round(g.y))
            existing = canon.get(key)
            if existing is None:
                canon[key] = MergedGraveyard(
                    unit_type=g.unit_type or "Inconnu",
                    coalition=g.coalition,
                    x=g.x,
                    y=g.y,
                    alt=g.alt,
                    heading=g.heading,
                    seen_in=[upload_id],
                )
            else:
                if upload_id not in existing.seen_in:
                    existing.seen_in.append(upload_id)
                existing.coalition = existing.coalition or g.coalition
                existing.alt = existing.alt if existing.alt is not None else g.alt
                existing.heading = existing.heading if existing.heading is not None else g.heading
    return list(canon.values())


# =============================================================================
# 5. Identités & construction des vols (spec §3.1/§3.2/§3.4/§4)
# =============================================================================


@dataclass
class _IdentityCandidate:
    profile_id: int | None
    callsign: str | None
    state: str  # 'nomme' | 'rattachable' | 'anonyme'
    source: str | None
    slot_mission: str | None = None
    mission_id_dcs: str | None = None


@dataclass
class ComputedFlight:
    object_id: str | None
    acmi_track_id: str | None
    aircraft_type: str
    coalition: str | None
    pilote_profile_id: int | None
    pilot_callsign: str | None
    identity_state: str
    identity_source: str | None
    t_start: float | None
    t_end: float | None
    slot_mission: str | None
    mission_id_dcs: str | None
    stats: dict = field(default_factory=dict)
    # Lot « Les heures de jour et de nuit » (v1.0068, le porteur, 4 novembre) :
    # `'jour'`, `'nuit'` ou `None` (horloge de la mission inconnue) --
    # posée par `_poser_periodes`, jamais par la construction du vol.
    periode: str | None = None

    def natural_key(self) -> str:
        if self.object_id:
            return f"do:{self.object_id}"
        return f"ac:{self.acmi_track_id}"


def _collect_object_types(
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]]
) -> dict[str, str]:
    counts: dict[str, Counter] = defaultdict(Counter)
    for _, log in debrief_pairs:
        for e in log.events:
            if e.initiator_object_id and e.initiator_unit_type:
                counts[e.initiator_object_id][e.initiator_unit_type] += 1
            if e.target_object_id and e.target_unit_type:
                counts[e.target_object_id][e.target_unit_type] += 1
    return {oid: counter.most_common(1)[0][0] for oid, counter in counts.items()}


def _is_real_oid(oid: str | None) -> bool:
    """Correctif « vérités du roster » v0.9913 -- DCS journalise l'abandon
    de slot (`type="relinquished"`) avec `initiatorObjectID="0"`,
    `initiatorPilotName="PLAYER"` (fait mesuré : 1 occurrence par log,
    Francfort et 27/07, t≈4719 sur la session du 27/07). `"0"` n'est
    JAMAIS un object_id de vie réelle -- sans ce filtre, les collecteurs de
    candidats l'admettaient (chaîne non vide = truthy) et fabriquaient un
    vol fantôme « Inconnu anonyme 0:00 ». `_coarse_event_key` (fusion
    d'events, plus haut) traitait déjà `"0"` comme absent ; ce prédicat
    applique la même règle à la résolution d'identité et à la
    construction des vols."""
    return oid not in (None, "", "0")


def _collect_player_marked_ids(
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]]
) -> set[str]:
    """Object_ids marqués `PLAYER` (fait 5) -- humain confirmé, non
    forcément nommé (cf. décision d'implémentation #4)."""
    ids: set[str] = set()
    for _, log in debrief_pairs:
        for e in log.events:
            if e.initiator_pilot_name == _AI_PILOT_MARKER and _is_real_oid(e.initiator_object_id):
                ids.add(e.initiator_object_id)
            if e.target_pilot_name == _AI_PILOT_MARKER and _is_real_oid(e.target_object_id):
                ids.add(e.target_object_id)
    return ids


def _is_true_callsign(name: str | None, object_types: dict[str, str]) -> bool:
    """Détection "vrai callsign" (spec §4.4/§3.2)."""
    if not name or name == _AI_PILOT_MARKER:
        return False
    if name in set(object_types.values()):
        return False
    if categorize.is_known_unit_type(name):
        return False
    return True


def _collect_replication_candidates(
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]],
    object_types: dict[str, str],
) -> dict[str, str]:
    """`object_id -> callsign` via réplication opportuniste (spec §4.4)."""
    found: dict[str, str] = {}
    for _, log in debrief_pairs:
        for e in log.events:
            for oid, pilot_name in (
                (e.initiator_object_id, e.initiator_pilot_name),
                (e.target_object_id, e.target_pilot_name),
            ):
                if _is_real_oid(oid) and pilot_name and _is_true_callsign(pilot_name, object_types):
                    found.setdefault(oid, pilot_name)
    return found


async def _match_profile_by_callsign(db: AsyncSession, callsign: str) -> int | None:
    """Enrichissement best-effort (décision #3) : match exact
    casse-insensible du callsign contre `profiles.global_name`/`username`."""
    result = await db.execute(select(Profile))
    matches = [
        p
        for p in result.scalars().all()
        if (p.global_name or "").strip().lower() == callsign.strip().lower()
        or p.username.strip().lower() == callsign.strip().lower()
    ]
    if len(matches) == 1:
        return matches[0].id
    return None


def _sieges_equipage(
    log: "debriefer_mod.DebriefLogData", object_types: dict[str, str]
) -> set[str]:
    """Lot « Le siège d'équipage » (v1.0066) : les `object_id` d'UN journal
    qui sont des sièges d'équipage de son déposant.

    Fait DCS : un joueur peut monter en équipage (copilote, mitrailleur) dans
    l'appareil d'un autre joueur. Son `debrief.log` porte alors un
    `under control` sur l'appareil de l'autre, AU NOM du joueur (et non
    `PLAYER`), sur un objet que le pilote porte, sous son propre indicatif,
    dans le même journal -- avant ou après ce contrôle (le copilote monté au
    parking).

    Un évènement `under control` E, d'`object_id` réel O, fait de O un siège
    d'équipage si et seulement si les deux conditions tiennent :
    (a) `E.initiator_pilot_name` est non vide et différent de `PLAYER` ;
    (b) le même journal porte un évènement F, QUEL QUE SOIT SON `t` (avant,
        après, égal ou absent : le copilote qui monte au parking prend sa
        place avant la mise en route du pilote, donc avant tout évènement
        nommé de celui-ci), où O est l'initiateur (avec
        `initiator_pilot_name`) ou la cible (avec `target_pilot_name`), dont
        ce nom est un vrai indicatif (`_is_true_callsign`) ET dont le segment
        de nom (`_extract_name_segment`, sans casse) diffère de celui de
        `E.initiator_pilot_name` (un nom sans segment vaut la chaîne vide).
    Rien d'autre ne fait un siège d'équipage.

    Cas réel (le porteur, 2 novembre 2026, Mi-24P à Konya) : `under control` de
    l'objet 16777986 (`PLAYER`, t = 176,574), `relinquished` à t = 4731,395,
    puis deux `under control` de l'objet 16777987 au nom `MistyKestrel42`
    (t = 4738,791) -- l'appareil de DawN, vu depuis t = 1497,82 sous
    `Dragoon 2-1 | DawN-FyX35`. Le journal est lu seul : les sièges d'un
    déposant sur plusieurs journaux se réunissent dans `_resolve_identities`.
    Ne lit aucune base."""
    vus: dict[str, list[str]] = defaultdict(list)
    for e in log.events:
        for oid, nom in (
            (e.initiator_object_id, e.initiator_pilot_name),
            (e.target_object_id, e.target_pilot_name),
        ):
            if _is_real_oid(oid) and _is_true_callsign(nom, object_types):
                vus[oid].append((_extract_name_segment(nom) or "").casefold())

    sieges: set[str] = set()
    for e in log.events:
        if e.type != "under control":
            continue
        oid = e.initiator_object_id
        nom = e.initiator_pilot_name
        if not _is_real_oid(oid) or not nom or nom == _AI_PILOT_MARKER:
            continue
        segment = (_extract_name_segment(nom) or "").casefold()
        if any(seg != segment for seg in vus.get(oid, ())):
            sieges.add(oid)
    return sieges


async def _resolve_identities(
    db: AsyncSession,
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]],
    object_types: dict[str, str],
) -> dict[str, _IdentityCandidate]:
    candidates: dict[str, list[_IdentityCandidate]] = defaultdict(list)

    # Réplication calculée une seule fois (spec §4.4) -- réutilisée ci-dessous
    # à la fois comme candidat propre et comme source de propagation
    # under_control (HOTFIX identité déposant, cf. tête de module #7).
    replication = _collect_replication_candidates(debrief_pairs, object_types)

    # Priorité under_control (spec §4.2) + HOTFIX identité déposant : L'IDENTITÉ
    # (le "qui") d'une vie under_control vient TOUJOURS du déposant de
    # l'upload -- jamais du callsign racine du log (corrompu/non fiable, cf.
    # `callsign_header_unreliable`). Pour le CALLSIGN (nécessaire à la
    # jointure ACMI par nom, cf. `_build_flights`), on propage à TOUTES les
    # vies under_control d'un même (upload, log) le callsign déjà résolu par
    # réplication sur N'IMPORTE LAQUELLE de ces vies : un client ne contrôle
    # que ses propres appareils/respawns (principe validé par le porteur), donc
    # toutes les vies under_control d'un log partagent le même pilote humain
    # et donc le même vrai callsign, même si seule une partie de ces vies a
    # été vue nommément par un AUTRE pilote (réplication). Exception (lot
    # « Le siège d'équipage », v1.0066) : un siège d'équipage -- l'appareil
    # d'un autre joueur, rejoint en copilote -- n'est pas une vie du déposant
    # (cf. `_sieges_equipage`) ; il est écarté de chacun de ses journaux,
    # réuni sur tous (une reconnexion ne le lui redonne pas). Fallback (aucun
    # callsign observé pour aucune des vies de ce déposant dans ce log) :
    # l'attribution profil est conservée (identité documentée par le
    # déposant), mais `callsign` reste `None` -- ces vies ne pourront pas
    # rejoindre l'ACMI faute de callsign commun ; signalé en log, cf. §4.8
    # (alias ACMI déclaré par membre) hors périmètre de ce hotfix.
    sieges_par_deposant: dict[int, set[str]] = defaultdict(set)
    for upload, log in debrief_pairs:
        if upload.depositor_profile_id is not None:
            sieges_par_deposant[upload.depositor_profile_id] |= _sieges_equipage(
                log, object_types
            )
    for upload, log in debrief_pairs:
        if upload.depositor_profile_id is None:
            continue
        sieges_equipage = sieges_par_deposant[upload.depositor_profile_id]
        vies_du_log = {
            oid for oid in log.under_control_object_ids() if _is_real_oid(oid)
        }
        log_under_control_ids = vies_du_log - sieges_equipage
        if vies_du_log & sieges_equipage:
            logger.info(
                "siège d'équipage: déposant profile_id=%s, %d siège(s) "
                "d'équipage écarté(s) des vies under_control.",
                upload.depositor_profile_id,
                len(vies_du_log & sieges_equipage),
            )
        propagated_callsign = next(
            (
                replication[oid]
                for oid in sorted(log_under_control_ids)
                if oid in replication
            ),
            None,
        )
        if propagated_callsign is None and log_under_control_ids:
            logger.info(
                "under_control: aucun callsign (réplication) trouvé pour le "
                "déposant profile_id=%s sur %d vie(s) under_control -- "
                "attribution profil conservée, jointure ACMI par nom impossible "
                "pour ce log tant qu'aucun callsign n'est observé.",
                upload.depositor_profile_id,
                len(log_under_control_ids),
            )
        for e in log.events:
            if (
                e.type == "under control"
                and _is_real_oid(e.initiator_object_id)
                and e.initiator_object_id not in sieges_equipage
            ):
                candidates[e.initiator_object_id].append(
                    _IdentityCandidate(
                        profile_id=upload.depositor_profile_id,
                        callsign=propagated_callsign,
                        state="nomme",
                        source="under_control",
                        slot_mission=e.target_slot,
                        mission_id_dcs=e.target_mission_id,
                    )
                )

    # Priorité réplication (spec §4.4).
    for oid, callsign in replication.items():
        candidates[oid].append(
            _IdentityCandidate(
                profile_id=None, callsign=callsign, state="rattachable", source="replication"
            )
        )

    resolved: dict[str, _IdentityCandidate] = {}
    for oid, cands in candidates.items():
        best = min(cands, key=lambda c: IDENTITY_PRIORITY.get(c.source or "", 99))
        resolved[oid] = best

    # Enrichissement profil (décision #3) pour les candidats 'rattachable'
    # nommés par réplication : promotion en 'nomme' sur match exact unique.
    for oid, cand in resolved.items():
        if cand.state == "rattachable" and cand.callsign and cand.profile_id is None:
            match = await _match_profile_by_callsign(db, cand.callsign)
            if match is not None:
                cand.profile_id = match
                cand.state = "nomme"

    return resolved


_SEGMENT_SEP_RE = re.compile(r"\s(\||I)\s")


def _extract_name_segment(s: str | None) -> str | None:
    """Extrait le segment nom humain d'un callsign ACMI ou d'un nom de
    profil, pour le rattachement par le nom (brief v0.9916, geste ①).
    Coupe sur le DERNIER séparateur -- '|' ou 'I' majuscule isolé,
    entouré d'espaces des DEUX côtés -- et garde ce qui suit ; repli sur
    la chaîne entière si aucun séparateur trouvé. Puis `strip()`.

    Distincte de `_norm_callsign()` (jointure ACMI<->débrief, ne pas
    toucher) : celle-ci REMPLACE le séparateur par un espace, celle-ci
    EXTRAIT un segment -- deux besoins différents.

    Règle miroir côté front : `shortCallsign()` (`app.js`) -- un
    commentaire y renvoie ici, et réciproquement ; toute évolution de
    l'une doit être répercutée sur l'autre.

    ⚠ L'isolement du 'I' est structurel, pas optionnel : sans l'exigence
    d'espaces des deux côtés, un nom comme 'Red Kite' serait tronqué
    sur son 'i' interne. Ne jamais assouplir cette contrainte (mesuré,
    cf. brief §2)."""
    if not s:
        return None
    matches = list(_SEGMENT_SEP_RE.finditer(s))
    segment = s[matches[-1].end():] if matches else s
    segment = segment.strip()
    return segment or None


async def _attach_profiles_by_name(
    db: AsyncSession, computed_flights: list[ComputedFlight]
) -> int:
    """Geste ① (brief v0.9916), étendu Geste ② (brief v0.9917) : rattache
    par le nom les vols dont `pilote_profile_id` est encore `None` mais
    qui portent un `pilot_callsign` -- typiquement les vols ACMI orphelins
    (aucun log de débrief ne les a nommés, cf. brief v0.9916 §1 fait ⑥).
    Tourne dans `recompute_session`, entre `_build_flights()` et
    `_apply_manual_overrides()` -- AVANT les overrides, pour que la
    supersession (arbitrage du porteur du 23/08, cf.
    `_apply_manual_overrides`) s'applique aussi aux vols que CETTE passe
    vient de nommer.

    Compare le SEGMENT (`_extract_name_segment`) du callsign à trois
    sources, DANS CET ORDRE (brief v0.9917 §4 -- un fait déclaré par un
    humain prime toujours sur un fait dérivé) :

    1. `profile_dcs_alias.alias_segment` (Geste ①, migration 0020) -- un
       nom explicitement retenu pour un membre (`POST .../identify`,
       `_record_alias()` dans `app/debrief/api.py`). L'unicité de la
       colonne rend cette étape sans ambiguïté possible : au plus un
       profil par segment. Écrit `identity_source = "alias"` -- valeur
       neuve, distincte de "nom_acmi".
    2. à défaut, le segment du nom de chaque profil (`global_name` ou, à
       défaut, `username` -- même champ que celui exposé par
       `GET /api/command/members`), SEULEMENT sur correspondance UNIQUE
       (`len(matches) == 1`) ; zéro ou plusieurs candidats laissent le vol
       intact (brief v0.9916 §2, §6 condition 3). Écrit
       `identity_source = "nom_acmi"`, inchangé depuis v0.9916.

    3. à défaut SEULEMENT si l'étage 2 n'a trouvé AUCUN candidat (deux
       candidats exacts restent une ambiguïté, jamais rattrapée ici) : le
       segment du vol COMMENCE PAR le segment d'un profil, ET le caractère
       qui suit ce préfixe N'EST PAS UNE LETTRE (arbitrage du porteur du
       2 septembre, forme F1 bornée). Un pilote fabrique son alias en
       AJOUTANT des caractères à son nom, il ne le prolonge pas en un
       autre mot : `Tapir.fr`, `Vortex2`, `Lace-rck`, `Thorn_2` rattachent
       -- `Lacerte` et `The Hawksmoore` sont des noms pleins et restent
       INTACTS. `str.isalpha()` est Unicode : la frontière vaut aussi pour
       le cyrillique. SEULEMENT sur correspondance UNIQUE.
       ⚠ JAMAIS l'inverse (`Kest` ne doit pas rattacher `Mistykestrel42`)
       et JAMAIS une sous-chaîne libre : sur les seize membres réels, le
       sens inverse ouvre 230 fragments de 3 caractères ou plus qui
       rattacheraient en silence (mesuré). Écrit
       `identity_source = "nom_prefixe"`, valeur neuve -- la colonne est
       un `Text` nullable sans contrainte, aucune migration. Le front la
       regroupe sous « le moteur » par `slipOrigin()` sans modification.
       N'écrit AUCUN alias : une déduction ne se promeut pas en fait
       déclaré.

    Ne consulte jamais `IDENTITY_PRIORITY` (cette table arbitre à
    l'intérieur de `_resolve_identities`, en amont -- cette passe
    postérieure ne concourt avec personne, cf. brief v0.9916 §2, ne pas y
    toucher) et n'appelle jamais `_match_profile_by_callsign` (requête
    profil distincte, propre à cette passe).

    Retourne le nombre de vols rattachés (journal + porte v0.9916 P2 /
    v0.9917 P3)."""
    result = await db.execute(select(Profile))
    profiles = result.scalars().all()

    segment_to_ids: dict[str, list[int]] = defaultdict(list)
    for p in profiles:
        seg = _extract_name_segment(p.global_name or p.username)
        if seg:
            segment_to_ids[seg.lower()].append(p.id)

    alias_rows = (await db.execute(select(ProfileDcsAlias))).scalars().all()
    alias_by_segment: dict[str, int] = {
        row.alias_segment: row.profile_id for row in alias_rows
    }

    attached = 0
    attached_by_alias = 0
    attached_by_prefix = 0
    for cf in computed_flights:
        if cf.pilote_profile_id is not None or not cf.pilot_callsign:
            continue
        seg = _extract_name_segment(cf.pilot_callsign)
        if not seg:
            continue
        seg_lower = seg.lower()

        alias_profile_id = alias_by_segment.get(seg_lower)
        if alias_profile_id is not None:
            cf.pilote_profile_id = alias_profile_id
            cf.identity_state = "nomme"
            cf.identity_source = "alias"
            attached += 1
            attached_by_alias += 1
            continue

        matches = segment_to_ids.get(seg_lower, [])
        if len(matches) == 1:
            cf.pilote_profile_id = matches[0]
            cf.identity_state = "nomme"
            cf.identity_source = "nom_acmi"
            attached += 1
            continue
        if matches:
            continue

        prefix_matches = [
            pid
            for pseg, pids in segment_to_ids.items()
            if len(pseg) < len(seg_lower)
            and seg_lower.startswith(pseg)
            and not seg_lower[len(pseg)].isalpha()
            for pid in pids
        ]
        if len(prefix_matches) != 1:
            continue
        cf.pilote_profile_id = prefix_matches[0]
        cf.identity_state = "nomme"
        cf.identity_source = "nom_prefixe"
        attached += 1
        attached_by_prefix += 1

    if attached:
        logger.info(
            "Rattachement par le nom : %d vol(s) rattaché(s) (%d par nom "
            "retenu, identity_source='alias' ; %d par segment de profil, "
            "identity_source='nom_acmi' ; %d par préfixe de segment, "
            "identity_source='nom_prefixe').",
            attached, attached_by_alias,
            attached - attached_by_alias - attached_by_prefix,
            attached_by_prefix,
        )
    return attached


def _norm_callsign(s: str | None) -> str | None:
    """Normalisation du callsign pour la jointure ACMI<->débrief PAR NOM
    (brief HOTFIX jointure ACMI<->débrief par nom, §Normalisation). DCS
    mélange `|` et `I` (lettre) comme séparateur entre le tag de formation
    et le vrai callsign humain -- vérifié sur données réelles : gère
    `COLT 1-1 | Vortex` <-> `colt 1-1 vortex` et `MAMBA 1-1 I Golem` des
    deux côtés (tant que la même graphie est utilisée aux deux extrémités,
    ce qui est le cas car les deux proviennent du même moteur DCS)."""
    if not s:
        return None
    s = s.replace("|", " ")  # séparateur | ou I (DCS mélange les deux)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s or None


def _build_flights(
    *,
    acmi_data: acmi_mod.AcmiData | None,
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]],
    object_types: dict[str, str],
    identities: dict[str, "_IdentityCandidate"],
) -> list[ComputedFlight]:
    under_control_ids: set[str] = set()
    for _, log in debrief_pairs:
        under_control_ids |= {
            oid for oid in log.under_control_object_ids() if _is_real_oid(oid)
        }
    player_marked_ids = _collect_player_marked_ids(debrief_pairs)
    replication_ids = set(_collect_replication_candidates(debrief_pairs, object_types).keys())

    candidate_object_ids = under_control_ids | player_marked_ids | replication_ids

    # Bornes temporelles + coalition par object_id (spec §3.4).
    t_bounds: dict[str, list[float]] = defaultdict(list)
    coalition_by_oid: dict[str, str] = {}
    for _, log in debrief_pairs:
        for e in log.events:
            if e.t is None:
                continue
            if e.initiator_object_id:
                t_bounds[e.initiator_object_id].append(e.t)
                camp = _coalition_valide(e.initiator_coalition)
                if camp is not None and e.initiator_object_id not in coalition_by_oid:
                    coalition_by_oid[e.initiator_object_id] = camp
            if e.target_object_id:
                t_bounds[e.target_object_id].append(e.t)

    # --- Jointure ACMI <-> debrief PAR NOM (PRIMAIRE) ----------------------
    # (brief HOTFIX jointure ACMI<->débrief par nom). Le champ ACMI `Pilot`
    # porte le callsign humain exact -- prioritaire sur la jointure par
    # unicité de type (ci-dessous, conservée en fallback), qui échoue dès
    # qu'un type d'appareil compte plusieurs humains (cas réel : plusieurs
    # Mi-24P, plusieurs F-4E).
    joined_acmi_track_ids: set[str] = set()
    acmi_join_by_oid: dict[str, acmi_mod.AcmiObject] = {}
    join_source_by_oid: dict[str, str] = {}

    acmi_by_cs: dict[str, list[acmi_mod.AcmiObject]] = defaultdict(list)
    if acmi_data is not None:
        for obj in acmi_data.objects.values():
            if obj.is_human:
                cs = _norm_callsign(obj.pilot)
                if cs:
                    acmi_by_cs[cs].append(obj)

    # Callsign "connu" côté débrief pour un oid donné : celui déjà résolu
    # par _resolve_identities (ident.callsign -- depuis le HOTFIX identité
    # déposant #8, cf. tête de module, la source 'under_control' porte
    # elle aussi ce callsign, propagé à toutes les vies under_control d'un
    # même déposant/log) OU, à défaut (secours), celui observé par
    # réplication directement -- utile si un oid under_control n'a, malgré
    # la propagation, toujours aucun callsign connu dans toute la session
    # (aucune de ses vies soeurs n'a jamais été vue nommément par un tiers).
    replication_callsigns = _collect_replication_candidates(debrief_pairs, object_types)

    def _known_debrief_callsign(o: str) -> str | None:
        cand_ident = identities.get(o)
        if cand_ident and cand_ident.callsign:
            return cand_ident.callsign
        return replication_callsigns.get(o)

    def _debrief_t_start(o: str) -> float:
        times = t_bounds.get(o, [])
        return min(times) if times else float("inf")

    # Groupement des oids débrief par callsign normalisé -- gère les
    # RESPAWNS (brief §Respawns) : un même callsign peut avoir plusieurs
    # vies débrief (plusieurs oids) ET plusieurs vies ACMI (plusieurs
    # track_id). On n'en fusionne jamais deux : chaque vie débrief consomme
    # sa propre piste ACMI, la plus proche en temps (t_spawn ACMI le plus
    # proche du t_start débrief), les autres vies restant des vols distincts.
    debrief_oids_by_cs: dict[str, list[str]] = defaultdict(list)
    for oid in candidate_object_ids:
        cs = _norm_callsign(_known_debrief_callsign(oid))
        if cs and cs in acmi_by_cs:
            debrief_oids_by_cs[cs].append(oid)

    for cs in sorted(debrief_oids_by_cs):
        # Tri temporel + oid pour déterminisme total (insensibilité à
        # l'ordre d'arrivée des uploads, cf. décision d'implémentation #5).
        group_sorted = sorted(debrief_oids_by_cs[cs], key=lambda o: (_debrief_t_start(o), o))
        for oid in group_sorted:
            available = [h for h in acmi_by_cs[cs] if h.track_id not in joined_acmi_track_ids]
            if not available:
                continue  # plus de piste dispo pour ce callsign -- vies non appariées restent distinctes
            d_t_start = _debrief_t_start(oid)
            if d_t_start == float("inf"):
                chosen = available[0]
            else:
                chosen = min(
                    available,
                    key=lambda h: abs(
                        (h.t_spawn if h.t_spawn is not None else float("inf")) - d_t_start
                    ),
                )
            acmi_join_by_oid[oid] = chosen
            join_source_by_oid[oid] = "acmi_callsign"
            joined_acmi_track_ids.add(chosen.track_id)

    # --- Jointure ACMI <-> debrief par unicité de type (spec §4.5) --------
    # FALLBACK -- ne s'applique qu'aux oids non déjà appariés par nom
    # ci-dessus, et aux pistes ACMI encore disponibles après le join par nom.
    # NB : le champ ACMI `Name` porte la désignation DCS précise (ex.
    # "F-16C_50", "Mi-24P"), homogène avec `*_unit_type` du debrief. Le champ
    # `Type` est une étiquette de catégorie Tacview (ex. "Air+FixedWing") --
    # non comparable à `*_unit_type` et donc jamais utilisé pour la jointure.
    human_acmi_by_type: dict[str, list[acmi_mod.AcmiObject]] = defaultdict(list)
    if acmi_data is not None:
        for obj in acmi_data.objects.values():
            if obj.is_human:
                human_acmi_by_type[obj.name or ""].append(obj)

    for oid in sorted(candidate_object_ids):
        if oid in acmi_join_by_oid:
            continue  # déjà résolu par le join par nom (primaire) ci-dessus
        # NB : la jointure par unicité de type sert à DEUX choses : nommer
        # un vol encore anonyme (identity_source='acmi_type_unique'), ET
        # enrichir de données ACMI (alt_max, bornes, coalition) un vol DÉJÀ
        # identifié par ailleurs (under_control/replication) -- l'identité
        # déjà connue n'est jamais écrasée (cf. plus bas), mais la fusion de
        # données, elle, doit avoir lieu dans les deux cas.
        actype = object_types.get(oid)
        if not actype:
            continue
        humans_of_type = human_acmi_by_type.get(actype, [])
        available = [h for h in humans_of_type if h.track_id not in joined_acmi_track_ids]
        if len(available) == 1:
            acmi_join_by_oid[oid] = available[0]
            join_source_by_oid[oid] = "acmi_type_unique"
            joined_acmi_track_ids.add(available[0].track_id)

    flights: list[ComputedFlight] = []

    for oid in sorted(candidate_object_ids):
        ident = identities.get(oid)
        joined = acmi_join_by_oid.get(oid)
        pilot_callsign = ident.callsign if ident else None
        pilote_profile_id = ident.profile_id if ident else None
        identity_state = ident.state if ident else "anonyme"
        identity_source = ident.source if ident else None

        if joined is not None:
            if pilot_callsign is None:
                pilot_callsign = joined.pilot
            if identity_source is None:
                identity_state = "rattachable"
                identity_source = join_source_by_oid.get(oid, "acmi_type_unique")

        times = t_bounds.get(oid, [])
        t_start = min(times) if times else (joined.t_spawn if joined else None)
        t_end = max(times) if times else (joined.t_despawn if joined else None)
        if joined is not None:
            if joined.t_spawn is not None:
                t_start = joined.t_spawn if t_start is None else min(t_start, joined.t_spawn)
            if joined.t_despawn is not None:
                t_end = joined.t_despawn if t_end is None else max(t_end, joined.t_despawn)

        flights.append(
            ComputedFlight(
                object_id=oid,
                acmi_track_id=joined.track_id if joined else None,
                aircraft_type=object_types.get(oid) or (joined.name if joined else None) or "Inconnu",
                coalition=coalition_by_oid.get(oid) or (joined.coalition if joined else None),
                pilote_profile_id=pilote_profile_id,
                pilot_callsign=pilot_callsign,
                identity_state=identity_state,
                identity_source=identity_source,
                t_start=t_start,
                t_end=t_end,
                slot_mission=ident.slot_mission if ident else None,
                mission_id_dcs=ident.mission_id_dcs if ident else None,
            )
        )

    # --- Vies humaines ACMI non jointes -> flight autonome (spec §3.4) -----
    if acmi_data is not None:
        for obj in acmi_data.objects.values():
            if not obj.is_human or obj.track_id in joined_acmi_track_ids:
                continue
            flights.append(
                ComputedFlight(
                    object_id=None,
                    acmi_track_id=obj.track_id,
                    aircraft_type=obj.name or "Inconnu",
                    coalition=obj.coalition,
                    pilote_profile_id=None,
                    pilot_callsign=obj.pilot,
                    identity_state="rattachable" if obj.pilot else "anonyme",
                    identity_source=None,
                    t_start=obj.t_spawn,
                    t_end=obj.t_despawn,
                    slot_mission=None,
                    mission_id_dcs=None,
                )
            )

    return flights


# =============================================================================
# 6. Métriques dérivées (spec §3.6/§6)
# =============================================================================

_LANDING_TYPES = {"land", "pilot landing"}
_ALTMAX_BY_TRACK: dict[str, float] = {}  # renseigné depuis l'ACMI, cf. _compute_flight_stats


def _human_object_ids(
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]]
) -> set[str]:
    """Lot Moteur §5 (D2) : object_ids CONFIRMÉS humains dans la session --
    vies déclarées `under control` par un déposant, marquées `PLAYER`
    (fait 5), ou nommées par la réplication. Jamais l'ACMI seul. Sert à
    `also_engaged_by`/`destroyed_by_other` -- on n'attribue jamais un fait
    de collaboration/destruction à un objet dont on ne sait pas avec
    certitude qu'il fut piloté par un humain.

    Lot « Polish du moteur du Débrief » (v1.0039) : la réplication confirme
    désormais l'humain. Un vrai indicatif lu dans un journal -- ni `PLAYER`,
    ni un type d'unité (`_is_true_callsign`) -- ne se rencontre que sur un
    joueur : 8 objets sur 8, tous des joueurs et aucune IA, dans la mesure
    du 14 octobre 2026 sur les 22 journaux de production."""
    ids: set[str] = set()
    for _, log in debrief_pairs:
        ids |= {oid for oid in log.under_control_object_ids() if _is_real_oid(oid)}
    ids |= _collect_player_marked_ids(debrief_pairs)
    ids |= set(
        _collect_replication_candidates(debrief_pairs, _collect_object_types(debrief_pairs))
    )
    return ids


def _flight_display_label(fl: "ComputedFlight | None") -> str:
    """Lot Moteur §5 : indicatif réduit au SEGMENT (`_extract_name_segment`,
    déjà utilisé pour le rattachement par le nom) -- jamais l'indicatif
    complet ("COLT 2-1 | Noctis" -> "Noctis"). Repli sur le type d'unité du
    vol si aucun callsign n'est connu -- cas réel et fréquent sur la
    fixture (vol identifié par ACMI/under_control mais jamais nommé par un
    déposant ni répliqué)."""
    if fl is None:
        return "Inconnu"
    seg = _extract_name_segment(fl.pilot_callsign)
    return seg or fl.aircraft_type or "Inconnu"


def _oids_by_pilot(flights: list["ComputedFlight"]) -> dict[str, set[str]]:
    """Regroupe les vols par PERSONNE. Deux vols sont la même personne s'ils
    partagent un profil OU un segment d'indicatif -- les indicatifs sont
    uniques dans l'escadre (arbitrage du porteur du 30 août 2026). Fermeture
    TRANSITIVE : un vol qui porte les deux fait le pont entre un vol sans
    indicatif et un vol sans profil, cas que deux clés en cascade
    scinderaient -- c'est-à-dire le défaut même que ce geste corrige. Un vol
    sans profil ni indicatif reste seul avec lui-même : comportement
    identique à l'ancien `exclude_oid`."""
    parent: dict = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for fl in flights:
        if not fl.object_id:
            continue
        find(("o", fl.object_id))
        if fl.pilote_profile_id is not None:
            union(("o", fl.object_id), ("p", fl.pilote_profile_id))
        seg = _extract_name_segment(fl.pilot_callsign)
        if seg:
            union(("o", fl.object_id), ("c", seg.casefold()))

    groupes: dict = defaultdict(set)
    for fl in flights:
        if fl.object_id:
            groupes[find(("o", fl.object_id))].add(fl.object_id)
    return {fl.object_id: groupes[find(("o", fl.object_id))]
            for fl in flights if fl.object_id}


def _compute_also_engaged_by(
    *,
    target_object_id: str | None,
    exclude_oids: set[str],
    events_by_target: dict[str, list[MergedEvent]],
    human_oids: set[str],
    flights_by_oid: dict[str, "ComputedFlight"],
) -> list[dict]:
    """Lot Moteur §5 (D2①) / Lot Journal v0.9941 §3-§4 : `stats["kills"][*]
    ["also_engaged_by"]` -- les AUTRES PERSONNES humaines ayant touché
    (`hit`, jamais `shot` : "le seuil est l'impact, jamais le tir") la même
    cible que ce kill. Clé sur le TIREUR SEUL (Lot Journal §4, R45) : deux
    journaux peuvent nommer la même arme différemment pour le même tireur
    (ex. 'Mk 118' / `None`), et gardaient auparavant deux entrées pour un
    seul fait. Une entrée par tireur, à sa PREMIÈRE touche (chronologique,
    tri en amont de la boucle), l'arme affichée étant la PREMIÈRE non vide
    rencontrée pour ce tireur -- sans quoi l'entrée survivante pourrait
    être celle qui ne nomme rien. Exclut tous les vols de la MÊME PERSONNE
    que ce kill (`exclude_oids`, cf. `_oids_by_pilot` -- Lot Journal §3 :
    un pilote ne peut pas collaborer à sa propre touche) et tout tireur non
    confirmé humain (`human_oids`, cf. `_human_object_ids`). Invariant
    permanent du projet : ceci décrit un FAIT (qui a touché quoi, quand),
    jamais un classement ni une comparaison entre membres."""
    if not target_object_id:
        return []
    first_touch: dict[str, dict] = {}
    for e in sorted(events_by_target.get(target_object_id, []), key=lambda x: x.t):
        if e.type != "hit":
            continue
        ioid = e.initiator_object_id
        if not _is_real_oid(ioid) or ioid in exclude_oids or ioid not in human_oids:
            continue
        cur = first_touch.get(ioid)
        if cur is None:
            first_touch[ioid] = {"t": e.t, "weapon": e.weapon}
        elif not cur["weapon"] and e.weapon:
            cur["weapon"] = e.weapon
    result = [
        {"pilot": _flight_display_label(flights_by_oid.get(ioid)),
         "weapon": v["weapon"], "t": v["t"]}
        for ioid, v in first_touch.items()
    ]
    result.sort(key=lambda x: x["t"])
    return result


def _compute_destroyed_by_other(
    *,
    target_object_ids: list[str],
    exclude_oids: set[str],
    own_kill_targets: set[str],
    events_by_target: dict[str, list[MergedEvent]],
    human_oids: set[str],
    flights_by_oid: dict[str, "ComputedFlight"],
) -> list[dict]:
    """Lot Moteur §5 (D2②) : `stats["bursts"][*]["destroyed_by_other"]" --
    pour chaque cible de CETTE rafale (`target_object_ids`, Volet D1) que
    ce vol n'a PAS abattue (`own_kill_targets`) et qu'un AUTRE humain
    (jamais la MÊME PERSONNE que ce vol -- Lot Journal v0.9941 §3,
    `exclude_oids`) a détruite (`kill`, jamais `hit` -- le seuil est
    l'impact), en retenant le PREMIER abattage (par heure). Même
    exclusions que `_compute_also_engaged_by` : tous les vols de la même
    personne que le vol courant exclus, tireur non confirmé humain exclu."""
    result = []
    for toid in target_object_ids:
        if toid in own_kill_targets:
            continue
        candidates = [
            e for e in events_by_target.get(toid, [])
            if e.type == "kill"
            and _is_real_oid(e.initiator_object_id)
            and e.initiator_object_id not in exclude_oids
            and e.initiator_object_id in human_oids
        ]
        if not candidates:
            continue
        first = min(candidates, key=lambda e: e.t)
        result.append(
            {
                "target_unit_type": first.target_unit_type,
                "killer": _flight_display_label(flights_by_oid.get(first.initiator_object_id)),
                "killer_weapon": first.weapon,
                "kill_t": first.t,
            }
        )
    return result


def _journal_source(
    fl: ComputedFlight,
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]],
) -> str | None:
    """Lot « Un seul journal fait foi pour les tirs d'un vol » : l'upload
    (`str(upload.id)`) dont les faits de tir du vol font foi, ou `None` pour
    un vol sans `object_id` ou sans aucun fait de tir (un `shot` ou un
    `start shooting` dont il est l'initiateur) -- ce vol-là ne change pas.

    1. Le journal du déposant : son `depositor_profile_id` égale le profil du
       pilote du vol et ses `under control` portent l'`object_id` ; à
       plusieurs, le premier dans l'ordre des `sha256` (celui de
       `_merge_events`).
    2. Sinon, le journal témoin : celui qui porte le plus de `shot` et de
       `start shooting` du vol ; à égalité, le premier par `sha256`."""
    oid = fl.object_id
    if not oid:
        return None
    ordered = sorted(debrief_pairs, key=lambda pair: pair[0].sha256)
    comptes = [
        sum(
            1 for e in log.events
            if (e.type or "") in _TYPES_TIR_INITIAL and e.initiator_object_id == oid
        )
        for _, log in ordered
    ]
    if not any(comptes):
        return None
    if fl.pilote_profile_id is not None:
        for upload, log in ordered:
            if (
                upload.depositor_profile_id == fl.pilote_profile_id
                and oid in log.under_control_object_ids()
            ):
                return str(upload.id)
    meilleur = 0
    for i, n in enumerate(comptes):
        if n > comptes[meilleur]:
            meilleur = i
    return str(ordered[meilleur][0].id)


def _vu_dans(
    e: MergedEvent, upload_id: str, obus_par_journal: dict[tuple[str, str], int | None]
) -> MergedEvent:
    """Lot « Un seul journal fait foi pour les tirs d'un vol » : le fait tel
    que le voit le seul journal `upload_id` -- ses liens tir–impact réduits à
    ce journal, si bien que `_shot_hit_linked` et `_hit_is_linked_to_any` n'y
    lisent plus que lui ; une fin de rafale y porte les obus que CE journal
    écrit (`obus_par_journal`, clé `(upload, event_id)`), et non ceux du
    premier journal de la fusion -- mesuré : deux journaux peuvent écrire
    38 et 49 obus pour la même rafale. Une copie : le fait fusionné ne
    change pas."""
    event_id = e.event_id_by_upload.get(upload_id)
    obus = e.ammo
    if e.type == "end shooting" and event_id is not None:
        obus = obus_par_journal.get((upload_id, event_id), e.ammo)
    return replace(
        e,
        ammo=obus,
        seen_in=[upload_id],
        event_id_by_upload=(
            {upload_id: e.event_id_by_upload[upload_id]}
            if upload_id in e.event_id_by_upload else {}
        ),
        linked_event_id_by_upload=(
            {upload_id: e.linked_event_id_by_upload[upload_id]}
            if upload_id in e.linked_event_id_by_upload else {}
        ),
    )


def _compute_flight_stats(
    flights: list[ComputedFlight],
    merged_events: list[MergedEvent],
    acmi_data: acmi_mod.AcmiData | None,
    debrief_pairs: list[tuple[DebriefUpload, "debriefer_mod.DebriefLogData"]],
) -> None:
    events_by_initiator: dict[str, list[MergedEvent]] = defaultdict(list)
    events_by_target: dict[str, list[MergedEvent]] = defaultdict(list)
    for ev in merged_events:
        if ev.initiator_object_id:
            events_by_initiator[ev.initiator_object_id].append(ev)
        if ev.target_object_id:
            events_by_target[ev.target_object_id].append(ev)

    # Armes "linkables" à l'échelle de la session (décision d'implémentation
    # #6) : au moins un hit lié à un shot de cette arme, n'importe où.
    linkable_weapons: set[str] = set()
    shots_by_weapon: dict[str, list[MergedEvent]] = defaultdict(list)
    for ev in merged_events:
        if ev.type == "shot" and ev.weapon:
            shots_by_weapon[ev.weapon].append(ev)
    for ev in merged_events:
        if ev.type == "hit" and ev.weapon:
            for shot in shots_by_weapon.get(ev.weapon, []):
                if _shot_hit_linked(shot, ev):
                    linkable_weapons.add(ev.weapon)
                    break

    depositor_profile_ids = {
        u.depositor_profile_id for u, _ in debrief_pairs if u.depositor_profile_id is not None
    }

    alt_max_by_track: dict[str, float] = {}
    if acmi_data is not None:
        for obj in acmi_data.objects.values():
            if obj.alt_max is not None:
                alt_max_by_track[obj.track_id] = obj.alt_max

    # Lot Moteur §5 (D2) : périmètre "vol humain" + résolution object_id ->
    # vol, calculés UNE FOIS pour toute la session (cf. `_human_object_ids`,
    # `_flight_display_label`).
    human_oids = _human_object_ids(debrief_pairs)
    flights_by_oid: dict[str, ComputedFlight] = {
        fl.object_id: fl for fl in flights if fl.object_id
    }
    # Lot « Le journal dit quand un tir touche » : le premier kill de chaque
    # cible, et les kills d'explosion par tireur d'origine, pour la session.
    premiers_kills = _premiers_kills(merged_events)
    kills_explosion = _kills_d_explosion(premiers_kills)
    # Lot Journal v0.9941 §3 : vols regroupés par PERSONNE (profil ou
    # segment d'indicatif partagé) -- un pilote ne peut pas collaborer à
    # sa propre touche, même sous une sortie différente.
    oids_by_pilot = _oids_by_pilot(flights)
    # Lot « Un seul journal fait foi pour les tirs d'un vol » : les obus de
    # chaque fin de rafale, journal par journal (cf. `_vu_dans`).
    obus_par_journal: dict[tuple[str, str], int | None] = {}
    for upload, log in debrief_pairs:
        for e in log.events:
            if e.type == "end shooting" and e.event_id is not None:
                obus_par_journal[(str(upload.id), e.event_id)] = _munitions_tirees(e.type, e.raw)

    for fl in flights:
        oid = fl.object_id
        own_events = events_by_initiator.get(oid, []) if oid else []
        exclude_oids = oids_by_pilot.get(oid, {oid}) if oid else set()
        target_events = events_by_target.get(oid, []) if oid else []
        # Lot « Un seul journal fait foi pour les tirs d'un vol » : les tirs,
        # impacts et rafales du vol se comptent sur son seul journal source
        # (`_journal_source`), liens compris (`_vu_dans`) -- la fusion au plus
        # proche dans le temps prenait la roquette voisine pour la même. Ils
        # nourrissent `shots_by_weapon`, `cannon_by_weapon` et `bursts`, et
        # rien d'autre. Sans journal source, les faits fusionnés, comme avant.
        source = _journal_source(fl, debrief_pairs)
        if source is None:
            tir_events = own_events
        else:
            tir_events = [
                _vu_dans(e, source, obus_par_journal) for e in own_events
                if e.type in _TYPES_TIR and source in e.seen_in
            ]

        takeoffs =sum(1 for e in own_events if e.type == "takeoff")
        landings = sum(1 for e in own_events if e.type in _LANDING_TYPES)
        engine_on = sum(1 for e in own_events if e.type == "engine startup")
        engine_off = sum(1 for e in own_events if e.type == "engine shutdown")
        crashed = any(e.type == "crash" for e in own_events)
        ejected = any(e.type == "eject" for e in own_events)
        pilot_dead = any(e.type == "pilot dead" for e in own_events)

        kills = []
        for e in own_events:
            if e.type != "kill":
                continue
            kill_entry = {
                "target_object_id": e.target_object_id,
                "target_unit_type": e.target_unit_type,
                "weapon": e.weapon,
                "t": e.t,
            }
            # Lot « Le passage moteur » : camp de la cible, champ additif --
            # absent quand aucun journal ne le donne, jamais deviné. C'est lui
            # qui rend un tir fratricide au sol reconnaissable (api.py).
            if e.target_coalition is not None:
                kill_entry["target_coalition"] = e.target_coalition
            # Lot UI Journal v0.9918 §4 : heure de l'impact qui a causé
            # cette destruction, résolue via le lien tir<->impact existant
            # (_shot_hit_linked). Champ additif -- absent si le lien ne
            # résout pas, jamais une valeur inventée, jamais l'heure du
            # tir en repli. Lot Moteur §3 (Volet B) : bornée à <= e.t.
            impact_t = _resolve_kill_impact_t(e.weapon, e.target_object_id, own_events, e.t)
            if impact_t is not None:
                kill_entry["impact_t"] = impact_t
            # Lot Moteur §5 (D2①) : autres vols humains ayant touché la
            # même cible -- champ additif, absent si vide.
            also_engaged_by = _compute_also_engaged_by(
                target_object_id=e.target_object_id,
                exclude_oids=exclude_oids,
                events_by_target=events_by_target,
                human_oids=human_oids,
                flights_by_oid=flights_by_oid,
            )
            if also_engaged_by:
                kill_entry["also_engaged_by"] = also_engaged_by
            kills.append(kill_entry)

        # Lot « La précision des armes — le moteur » : la famille lue dans le
        # journal décide de la forme -- une arme unitaire a toujours une
        # précision, même à 0/N ; une arme à sous-munitions compte ses
        # largages et ses salves. Famille inconnue : la règle d'avant
        # (`linkable_weapons`), inchangée.
        tirs_par_arme: dict[str, list[MergedEvent]] = {}
        for e in tir_events:
            if e.type == "shot" and e.weapon:
                tirs_par_arme.setdefault(e.weapon, []).append(e)
        hits_propres = [e for e in tir_events if e.type == "hit"]

        precision_by_weapon = {}
        # Lot « L'écran de la précision » : la famille de chaque arme, celle
        # que la précision lit ci-dessous -- seulement quand elle est connue.
        familles_armes: dict[str, int] = {}
        for weapon, tirs in tirs_par_arme.items():
            famille = next(
                (s.weapon_family for s in sorted(tirs, key=lambda s: s.t) if s.weapon_family is not None),
                None,
            )
            if famille is not None:
                familles_armes[weapon] = famille
            if famille == _FAMILLE_SOUS_MUNITIONS:
                precision_by_weapon[weapon] = {
                    "releases": len(tirs),
                    **_salves_sous_munitions(tirs, hits_propres),
                }
                continue
            if famille in _FAMILLES_UNITAIRES:
                # Un tir est touché par un impact lié, quel que soit le nom
                # d'arme de l'impact (deux noms de la même S-13OF coexistent).
                touched = sum(
                    1 for s in tirs if any(_shot_hit_linked(s, h) for h in hits_propres)
                )
            elif weapon in linkable_weapons:
                touched = sum(
                    1
                    for s in tirs
                    if any(h.weapon == weapon and _shot_hit_linked(s, h) for h in hits_propres)
                )
            else:
                precision_by_weapon[weapon] = {"releases": len(tirs)}
                continue
            precision_by_weapon[weapon] = {
                "shots": len(tirs),
                "touched": touched,
                "precision": round(touched / len(tirs), 3) if tirs else None,
            }
            # Lot « Le Débrief : la précision des roquettes par salve » : une
            # roquette gagne ses salves, sans rien perdre de `shots`,
            # `touched` ni `precision`. Les kills sont ceux du vol (kills
            # probables compris) qui portent exactement le nom de l'arme.
            if famille == _FAMILLE_ROQUETTE:
                precision_by_weapon[weapon].update(
                    _salves_roquettes(
                        tirs,
                        hits_propres,
                        [e.t for e in own_events if e.type == "kill" and e.weapon == weapon],
                    )
                )

        cannon_bursts = sum(1 for e in own_events if e.type == "start shooting")
        cannon_hits = sum(
            1
            for e in own_events
            if e.type == "hit" and not e.weapon and not _hit_is_linked_to_any(e)
        )
        cannon_by_weapon = _canon_par_arme(tir_events)

        threat_log = []
        for e in target_events:
            if e.type == "kill":
                gravite = "abattu"
            elif e.type == "hit":
                gravite = "touché"
            elif e.type == "shot":
                gravite = "visé"
            else:
                continue
            threat_log.append(
                {
                    "type": e.type,
                    "t": e.t,
                    "initiator_object_id": e.initiator_object_id,
                    "initiator_unit_type": e.initiator_unit_type,
                    "weapon": e.weapon,
                    "gravite": gravite,
                }
            )
        threat_log.sort(key=lambda x: x["t"])

        # Brief D2⑤ Volet A.2 : horodatages de phases pour la timeline de vol
        # (⑤) -- les compteurs takeoffs/landings existaient deja, il
        # manquait les `t` correspondants. Purement additif, rien retire.
        phases = sorted(
            (
                {"type": e.type, "t": e.t}
                for e in own_events
                if e.type in {
                    "takeoff", "land", "crash", "eject", "pilot dead",
                    "engine startup", "engine shutdown",
                }
            ),
            key=lambda p: p["t"],
        )

        # Lot Moteur §4 (Volet C) : démarrages moteur consécutifs PRÉCÉDANT
        # le premier décollage du vol -- repli à l'AFFICHAGE seulement, sur
        # un seul `engine startup`, à l'heure du PREMIER. S'il n'y a aucun
        # `takeoff`, tous les `engine startup` se replient. Ce ne sont PAS
        # des doublons de fusion (écarts mesurés de 5,35 s à 135 s sur la
        # fixture, jamais sous la seconde -- majoritairement des bimoteurs
        # dont chaque moteur démarre séparément) : ne JAMAIS les
        # dédoublonner dans `_merge_events`/les compteurs. Seule la
        # timeline affichée change ; `stats["engine_on"]` (compteur réel,
        # ci-dessus) reste inchangé.
        first_takeoff_t = next((p["t"] for p in phases if p["type"] == "takeoff"), None)
        folded_phases = []
        startups_before = [
            p for p in phases
            if p["type"] == "engine startup"
            and (first_takeoff_t is None or p["t"] < first_takeoff_t)
        ]
        startup_ids_before = {id(p) for p in startups_before}
        seen_folded_startup = False
        for p in phases:
            if id(p) in startup_ids_before:
                if not seen_folded_startup:
                    folded_phases.append({"type": "engine startup", "t": startups_before[0]["t"]})
                    seen_folded_startup = True
                continue
            folded_phases.append(p)
        phases = folded_phases

        # Brief Lot Fusion §2, geste 4 : repli des sauts (tours de piste) au
        # journal de vol -- appliqué APRÈS le repli des démarrages moteur
        # ci-dessus, sur son résultat ; les deux replis ne se recouvrent
        # pas mais l'ordre doit être déterministe. Seuil : `_SAUT_SEUIL_S`,
        # au niveau du module.
        folded_sauts = []
        i = 0
        while i < len(phases):
            p = phases[i]
            if (
                p["type"] == "land"
                and i + 1 < len(phases)
                and phases[i + 1]["type"] == "takeoff"
                and (phases[i + 1]["t"] - p["t"]) < _SAUT_SEUIL_S
            ):
                folded_sauts.append(
                    {
                        "type": "saut",
                        "t": p["t"],
                        "au_sol_s": round(phases[i + 1]["t"] - p["t"], 1),
                    }
                )
                i += 2
                continue
            folded_sauts.append(p)
            i += 1
        phases = folded_sauts

        flight_time_s = None
        if fl.t_start is not None and fl.t_end is not None:
            flight_time_s = round(fl.t_end - fl.t_start, 1)

        alt_max = alt_max_by_track.get(fl.acmi_track_id) if fl.acmi_track_id else None

        precision_reliability = (
            "fiable" if fl.pilote_profile_id in depositor_profile_ids else "partielle"
        )

        # Lot Moteur §5 (D2②) : pour chaque rafale, les cibles touchées que
        # CE vol n'a pas abattues et qu'un AUTRE humain a détruites.
        own_kill_targets = {
            k["target_object_id"] for k in kills if k.get("target_object_id")
        }
        bursts = _compute_bursts(tir_events)
        for burst in bursts:
            destroyed_by_other = _compute_destroyed_by_other(
                target_object_ids=burst.get("target_object_ids", []),
                exclude_oids=exclude_oids,
                own_kill_targets=own_kill_targets,
                events_by_target=events_by_target,
                human_oids=human_oids,
                flights_by_oid=flights_by_oid,
            )
            if destroyed_by_other:
                burst["destroyed_by_other"] = destroyed_by_other
        # Lot « Le journal dit quand un tir touche » : le canon entre au
        # journal ; les lignes se rangent par heure, la rafale de tirs avant
        # le canon à égalité. Chaque ligne dit l'issue de ses cibles.
        bursts = sorted(bursts + _lignes_canon(tir_events),
                        key=lambda b: (b["t"], bool(b.get("cannon"))))
        for burst in bursts:
            burst["outcomes"] = _issues_cibles(
                cibles=burst.pop("_cibles"),
                targets=burst["targets"],
                exclude_oids=exclude_oids,
                premiers=premiers_kills,
                human_oids=human_oids,
                flights_by_oid=flights_by_oid,
            )

        # Lot « Le journal dit quand un tir touche » : une destruction par
        # l'explosion d'une épave est un kill du tireur d'origine, ajouté
        # après les kills existants quand le vol ne la compte pas déjà.
        ajouts = sorted(
            (k for k in kills_explosion.get(oid, []) if k["target_object_id"] not in own_kill_targets),
            key=lambda k: k["t"],
        ) if oid else []
        for k in ajouts:
            kill_entry = dict(k)
            also_engaged_by = _compute_also_engaged_by(
                target_object_id=k["target_object_id"],
                exclude_oids=exclude_oids,
                events_by_target=events_by_target,
                human_oids=human_oids,
                flights_by_oid=flights_by_oid,
            )
            if also_engaged_by:
                kill_entry["also_engaged_by"] = also_engaged_by
            kills.append(kill_entry)

        fl.stats = {
            "takeoffs": takeoffs,
            "landings": landings,
            "engine_on": engine_on,
            "engine_off": engine_off,
            "crashed": crashed,
            "ejected": ejected,
            "pilot_dead": pilot_dead,
            "kills": kills,
            "shots_by_weapon": precision_by_weapon,
            "cannon_bursts": cannon_bursts,
            "cannon_hits": cannon_hits,
            # Lot « La précision des armes — le moteur » : le canon, rafale
            # par rafale (`_canon_par_arme`). `cannon_bursts` et `cannon_hits`
            # restent, inchangés : ils sont lus ailleurs.
            "cannon_by_weapon": cannon_by_weapon,
            # Lot « L'écran de la précision » : {arme: famille} pour chaque
            # arme de `shots_by_weapon` dont la famille est connue ; `{}` au
            # besoin. L'écran range les armes par type d'après elle.
            "weapon_families": familles_armes,
            "flight_time_s": flight_time_s,
            "alt_max": alt_max,
            "precision_reliability": precision_reliability if oid else "partielle",
            # Lot 1.5 §4 (brief) / §4.4 (cadrage) : precision_reliability replie
            # deux causes distinctes -- drapeau propre, un seul motif (le pilote
            # de CE vol a déposé son propre débrief), sans le second (oid manquant).
            "pilot_deposited": fl.pilote_profile_id in depositor_profile_ids,
            # Lot UI Journal v0.9918 §5 : rafales de tirs groupées (une
            # arme, <= 5s entre deux tirs consécutifs). Additif, ne
            # remplace pas `shots_by_weapon` -- même logique que
            # `threat_log`/`aggregateThreatLog()` côté front, mais côté tir
            # plutôt que côté menace subie. Lot Moteur §5-6 : porte
            # désormais `target_object_ids` (D1) et, le cas échéant,
            # `destroyed_by_other` (D2②) -- calculé plus haut.
            "bursts": bursts,
            "threat_log": threat_log,
            "phases": phases,
        }


def _resolve_kill_impact_t(
    weapon: str | None,
    target_object_id: str | None,
    events: list[MergedEvent],
    kill_t: float,
) -> float | None:
    """Lot UI Journal v0.9918 §4 : heure de l'impact qui a causé une
    destruction (`stats["kills"][*]["impact_t"]`), résolue en réutilisant
    le lien tir<->impact existant (`_shot_hit_linked`), jamais un second
    mécanisme. `events` = own_events du vol (mêmes events que ceux déjà
    utilisés pour `kills`/`weapons_fired`).

    Candidat = un `hit` de la MÊME arme et de la MÊME cible que le kill,
    lié à au moins un `shot` de cette arme (n'importe lequel -- même
    logique que `linkable_weapons`/`wstats["touched"]` plus haut : le lien
    se vérifie par arme, pas par cible sur le shot, qui ne porte pas de
    cible), et dont l'heure est ANTÉRIEURE OU ÉGALE à `kill_t` (Lot Moteur
    §3, Volet B) -- un impact ne peut pas suivre la mort qu'il cause.
    Correctif : la version précédente retenait le dernier candidat sans
    borner par `kill_t`, en contradiction avec sa propre docstring ("le
    dernier avant la mort"). Mesure refaite le 30 août 2026 sur la fixture
    des quatre sessions, moteur courant exécuté hors base, borne retirée
    sur copie jetable et PIPELINE RÉEL (jamais une reconstitution de cette
    fonction : trois reconstitutions successives ont donné 9, 3 et 0) --
    2 abattages sur 165 retiendraient alors un impact postérieur au décès :
    session 89f20c83, un Mi-24V abattu à l'AIM-9M (impact 7,42 s après la
    mort) et un BMP-1 abattu au 9M114 Shturm (1,17 s après). Sur plusieurs
    impacts liés valides (rafale qui a fini par tuer), on retient le
    DERNIER avant la mort -- mesuré sur golem.log (M-1 Abrams, 6 impacts
    liés : le premier donnerait un écart de 50 s, le dernier les 47 s
    attendus). Aucune valeur inventée : None si rien ne résout (borner ne
    fait perdre aucune heure : les 2 cas ont chacun un impact valide À
    L'INSTANT MÊME de la mort, écart 0,000 s)."""
    if weapon is None or target_object_id is None:
        return None
    shots = [e for e in events if e.type == "shot" and e.weapon == weapon]
    if not shots:
        return None
    candidates = [
        e.t
        for e in events
        if e.type == "hit"
        and e.weapon == weapon
        and e.target_object_id == target_object_id
        and e.t <= kill_t
        and any(_shot_hit_linked(s, e) for s in shots)
    ]
    return max(candidates) if candidates else None


def _compute_bursts(events: list[MergedEvent]) -> list[dict]:
    """Lot UI Journal v0.9918 §5 : `stats["bursts"]` -- tirs groupés par
    arme, même patron de regroupement que `aggregateThreatLog()` côté
    front (app.js), reconduit ici côté moteur pour les mêmes raisons :
    même arme, même vol (implicite -- `events` = own_events d'UN seul
    vol), écart <= 5s entre deux tirs CONSÉCUTIFS. Seuil mesuré, pas
    choisi au hasard : sur la rafale réelle de Golem (48 x S-8KOM en
    5,7 s), l'écart maximal entre deux tirs consécutifs est de 1,9 s --
    5 s laisse plus du double de marge sans coller deux passes distinctes.

    Chaque rafale porte : l'arme, l'heure du premier tir, le nombre de
    tirs, le nombre d'impacts liés, et les types de cibles touchées
    (dédoublonnés). "Impacts liés" compte les TIRS de la rafale ayant
    reçu au moins un `hit` lié -- même sémantique que `wstats["touched"]`
    plus haut dans cette fonction (un tir touché ou non, jamais le compte
    brut d'entrées `hit`) -- fait mesuré sur golem.log : le DCS log peut
    porter DEUX entrées `hit` dupliquées pour un seul impact physique
    (R-60M, event_id 7182 et 7184, toutes deux liées au même tir 7181) ;
    compter les entrées `hit` brutes donnerait 2 au lieu du 1 impact
    attendu. Un tir isolé reste une rafale de taille 1 (l'écran ne montre
    pas de multiplicateur pour celles-là, cf app.js).

    Lot Journal v0.9941 §5 : une rafale peut mêler PLUSIEURS munitions --
    fait mesuré, une bombe à fragmentation alterne ses sous-munitions
    (BLU-49/B / Bomblets - BLU-18/B x 30, HE) au sein d'un même largage. Le
    regroupement passe donc à un seuil À DEUX ÉTAGES, mesuré sur la
    fixture (pas choisi) : même arme -> <= `WINDOW_SAME_S` (inchangé,
    5 s) ; arme différente -> <= `WINDOW_MIXED_S` (0,5 s -- marge 3,5x
    au-dessus de l'écart de dispersion mesuré, 0,124-0,140 s, et 7x en
    dessous du contre-exemple mesuré, 3,545 s entre deux actions
    distinctes). La comparaison porte sur le tir PRÉCÉDENT, pas sur
    l'ensemble des armes déjà accumulées dans la rafale -- lecture
    littérale de la règle, qui fait foi. `weapon`/`hits`/`target_unit_types`
    conservent exactement leur sens pour les rafales mono-arme (l'écrasante
    majorité) ; la clé `weapons` (répartition par arme) n'apparaît QUE sur
    une rafale à plusieurs armes -- rien de l'existant ne casse.
    """
    WINDOW_SAME_S = 5.0
    WINDOW_MIXED_S = 0.5
    shots = sorted(
        (e for e in events if e.type == "shot" and e.weapon),
        key=lambda e: e.t,
    )

    raw_bursts: list[list[MergedEvent]] = []
    for e in shots:
        last = raw_bursts[-1] if raw_bursts else None
        if last:
            dt = e.t - last[-1].t
            seuil = WINDOW_SAME_S if last[-1].weapon == e.weapon else WINDOW_MIXED_S
            if dt <= seuil:
                last.append(e)
                continue
        raw_bursts.append([e])
    weapons_by_burst = [{s.weapon for s in g} for g in raw_bursts]

    # Brief Lot Fusion §2, geste 2 : la table de `lexique.canon_arme` ne
    # couvre que le connu -- chaque version de DCS et chaque nouveau membre
    # peuvent introduire d'autres divergences, symptôme silencieux. Une
    # rafale qui mêle plus d'un nom d'arme distinct est signalée, pas
    # corrigée : c'est un signalement, pas un verdict (une rafale mixte
    # peut être légitime, roquettes et canon dans la même fenêtre).
    for group, weapons in zip(raw_bursts, weapons_by_burst):
        if len(weapons) > 1:
            logging.warning(
                "Rafale à armes multiples : tireur=%s t=%s armes=%s",
                group[0].initiator_object_id,
                group[0].t,
                sorted(weapons),
            )

    hits = [e for e in events if e.type == "hit" and e.weapon]

    # Lot Moteur §5 (D1) : attribution des CIBLES (`target_object_ids`) à
    # leur rafale -- par le TEMPS, pas par le lien tir<->impact (une rafale
    # peut toucher une cible sans qu'aucun de ses tirs individuels ne soit
    # nommément lié). Règle : un `hit` appartient à la DERNIÈRE rafale de
    # la MÊME arme dont l'heure de début précède (ou égale) l'impact. Une
    # cible n'est attribuée qu'UNE FOIS, à sa PREMIÈRE touche (chronologie
    # globale, toutes armes confondues) -- si une cible re-touchée
    # (éventuellement par une arme différente) a déjà été attribuée à une
    # rafale antérieure, les touches suivantes ne la ré-attribuent pas.
    target_ids_by_burst: list[list[str]] = [[] for _ in raw_bursts]
    attributed_targets: set[str] = set()
    for h in sorted(hits, key=lambda e: e.t):
        if not h.target_object_id or h.target_object_id in attributed_targets:
            continue
        best_idx = None
        best_start = None
        for idx, group in enumerate(raw_bursts):
            if h.weapon not in weapons_by_burst[idx]:
                continue
            start = group[0].t
            if start <= h.t and (best_start is None or start > best_start):
                best_start = start
                best_idx = idx
        if best_idx is None:
            continue
        target_ids_by_burst[best_idx].append(h.target_object_id)
        attributed_targets.add(h.target_object_id)

    hits_by_weapon: dict[str, list[MergedEvent]] = defaultdict(list)
    for h in hits:
        hits_by_weapon[h.weapon].append(h)

    # Lot « Le journal dit quand un tir touche » : une salve de sous-munitions
    # (rafale dont tous les tirs sont de famille 38) touche les cibles des
    # impacts de famille 38 non liés tombés dans [premier largage, dernier
    # largage + `_SALVE_FENETRE_S`] ; dans deux fenêtres, l'impact va à la
    # salve commencée le plus tard.
    salves = [
        idx for idx, group in enumerate(raw_bursts)
        if all(s.weapon_family == _FAMILLE_SOUS_MUNITIONS for s in group)
    ]
    touches_salve: dict[int, list[MergedEvent]] = {idx: [] for idx in salves}
    for h in events:
        if (
            h.type != "hit"
            or h.weapon_family != _FAMILLE_SOUS_MUNITIONS
            or _hit_is_linked_to_any(h)
        ):
            continue
        dans = [
            idx for idx in salves
            if raw_bursts[idx][0].t <= h.t <= raw_bursts[idx][-1].t + _SALVE_FENETRE_S
        ]
        if dans:
            touches_salve[max(dans, key=lambda i: raw_bursts[i][0].t)].append(h)

    bursts = []
    for idx, group in enumerate(raw_bursts):
        weapon = group[0].weapon
        touched_shots = [
            s for s in group
            if any(_shot_hit_linked(s, h) for h in hits_by_weapon.get(s.weapon, []))
        ]
        # Lot « Le journal dit quand un tir touche » : les cibles touchées de
        # la ligne -- celles des impacts liés à ses tirs, sous le même nom
        # d'arme (l'ensemble de `target_unit_types`), ou celles de la salve.
        if idx in touches_salve:
            cibles = _cibles_touchees(touches_salve[idx])
        else:
            cibles = _cibles_touchees([
                h for s in group for h in hits_by_weapon.get(s.weapon, [])
                if _shot_hit_linked(s, h)
            ])
        target_types = sorted({
            h.target_unit_type
            for s in touched_shots
            for h in hits_by_weapon.get(s.weapon, [])
            if h.target_unit_type and _shot_hit_linked(s, h)
        })
        breakdown: dict[str, int] = {}
        for s in group:
            breakdown[s.weapon] = breakdown.get(s.weapon, 0) + 1
        bursts.append(
            {
                "weapon": weapon,
                "t": group[0].t,
                "shots": len(group),
                "hits": len(touched_shots),
                "target_unit_types": target_types,
                "target_object_ids": target_ids_by_burst[idx],
                **(
                    {"weapons": [{"weapon": w, "shots": n} for w, n in breakdown.items()]}
                    if len(breakdown) > 1
                    else {}
                ),
                # Lot « Le journal dit quand un tir touche » : `targets`, et
                # `_cibles`, clé privée que `_compute_flight_stats` remplace
                # par `outcomes`.
                **({"salvo": True} if idx in touches_salve else {}),
                "targets": _cibles_par_type(cibles),
                "_cibles": cibles,
            }
        )
    return bursts


def _salves_sous_munitions(tirs: list[MergedEvent], hits: list[MergedEvent]) -> dict:
    """Lot « La précision des armes — le moteur » : les salves d'une arme à
    sous-munitions (famille 38), pour UN vol. `tirs` : ses largages de cette
    arme ; `hits` : les impacts du même vol.

    Une salve : les largages successifs, chacun à `_SALVE_ECART_S` au plus
    du précédent. Elle touche quand au moins un impact du vol, NON lié, de
    famille 38, tombe dans [premier largage, dernier largage +
    `_SALVE_FENETRE_S`] -- les petites charges frappent sous leur propre nom
    (Mk 118, BLU-97B, BLU-18/B), jamais liées au largage."""
    salves: list[list[MergedEvent]] = []
    for s in sorted(tirs, key=lambda e: e.t):
        if salves and s.t - salves[-1][-1].t <= _SALVE_ECART_S:
            salves[-1].append(s)
        else:
            salves.append([s])
    impacts = [
        h.t for h in hits
        if h.weapon_family == _FAMILLE_SOUS_MUNITIONS and not _hit_is_linked_to_any(h)
    ]
    touchees = sum(
        1
        for salve in salves
        if any(salve[0].t <= t <= salve[-1].t + _SALVE_FENETRE_S for t in impacts)
    )
    return {"salvos": len(salves), "salvos_hit": touchees}


def _salves_roquettes(
    tirs: list[MergedEvent], hits: list[MergedEvent], kills_t: list[float]
) -> dict:
    """Lot « Le Débrief : la précision des roquettes par salve » : les salves
    d'une arme de famille 33 (roquette), pour UN vol. `tirs` : ses tirs de
    cette arme, ceux que la précision compte déjà ; `hits` : les impacts du
    même vol ; `kills_t` : les `t` des kills du vol (kills probables compris)
    dont l'arme est exactement celle-ci.

    Une salve : les tirs successifs, chacun à `_SALVE_ECART_S` au plus du
    précédent. Elle est au but quand un de ses tirs est lié à un impact de
    `hits` (`_shot_hit_linked`), ou quand un kill lui revient : un kill
    revient à la dernière salve dont le premier tir est à `t` ou avant lui,
    si le kill tombe au plus `_SALVE_ROQUETTE_FENETRE_S` après le dernier tir
    de cette salve. Un kill ne revient qu'à une seule salve."""
    salves: list[list[MergedEvent]] = []
    for s in sorted(tirs, key=lambda e: e.t):
        if salves and s.t - salves[-1][-1].t <= _SALVE_ECART_S:
            salves[-1].append(s)
        else:
            salves.append([s])
    au_but = [
        any(_shot_hit_linked(s, h) for s in salve for h in hits) for salve in salves
    ]
    for t_kill in kills_t:
        for i in range(len(salves) - 1, -1, -1):
            if salves[i][0].t <= t_kill:
                if t_kill <= salves[i][-1].t + _SALVE_ROQUETTE_FENETRE_S:
                    au_but[i] = True
                break
    return {"salvos": len(salves), "salvos_hit": sum(au_but)}


def _canon_par_arme(events: list[MergedEvent]) -> dict:
    """Lot « La précision des armes — le moteur » : `stats["cannon_by_weapon"]`,
    pour UN vol (`events` = ses own_events) --
    `{arme: {"bursts", "rounds", "bursts_hit", "rounds_hit"}}`.

    Une rafale : un `start shooting` et le `end shooting` qui le suit ; ses
    obus tirés sont l'`ammo_consumption` de la fin (0 s'il manque). Les fins
    vont aux débuts dans l'ordre (la plus ancienne rafale ouverte d'abord) :
    un canon double écrit deux débuts puis deux fins. Un début que ne suit
    aucune fin reste une rafale, de 0 obus, qui finit à son début ; une fin
    sans début ne compte pas. L'arme est celle du début, sinon celle de la
    fin. Lot « Un seul journal fait foi pour les tirs d'un vol » : les
    rafales d'une même arme commencées à moins de `_CANON_DOUBLE_S` l'une de
    l'autre n'en font qu'une, aux obus sommés (une pression de détente).

    Un obus au but : un `hit` du vol, SANS arme, non lié, dans [début de
    rafale, fin de rafale + `_CANON_FENETRE_S`] ; dans plusieurs fenêtres, il
    va à la rafale commencée le plus tard, et ne compte qu'une fois. Une
    collision n'en est jamais un : son `hit` porte une arme, le nom d'un
    appareil."""
    par_arme: dict[str, dict] = {}
    for r in _pressions_canon(events):
        ligne = par_arme.setdefault(
            r["arme"] or "", {"bursts": 0, "rounds": 0, "bursts_hit": 0, "rounds_hit": 0}
        )
        ligne["bursts"] += 1
        ligne["rounds"] += r["obus"]
        ligne["rounds_hit"] += len(r["impacts"])
        if r["impacts"]:
            ligne["bursts_hit"] += 1
    return par_arme


def _pressions_canon(events: list[MergedEvent]) -> list[dict]:
    """Lot « Le journal dit quand un tir touche » : les pressions de détente
    du canon d'UN vol, dans l'ordre de leurs débuts --
    `{"arme", "debut", "fin", "obus", "impacts"}`, `impacts` étant les `hit`
    reçus. Les règles sont celles de `_canon_par_arme` (qui les lit ici) :
    appariement des débuts et des fins, canon double à `_CANON_DOUBLE_S`, un
    impact sans arme et non lié à la pression commencée le plus tard dont la
    fenêtre `[début, fin + _CANON_FENETRE_S]` le contient."""
    rafales: list[dict] = []
    ouvertes: list[dict] = []
    for e in sorted(events, key=lambda e: (e.t, e.type != "start shooting")):
        if e.type == "start shooting":
            rafale = {"arme": e.weapon, "debut": e.t, "fin": e.t, "obus": 0, "au_but": 0}
            rafales.append(rafale)
            ouvertes.append(rafale)
        elif e.type == "end shooting" and ouvertes:
            # La plus ancienne rafale ouverte reçoit la fin -- mesuré sur les
            # canons doubles (Mirage F1, F-5E) : deux débuts puis deux fins au
            # même instant, une par canon, chacune avec ses obus.
            rafale = ouvertes.pop(0)
            rafale["arme"] = rafale["arme"] or e.weapon
            rafale["fin"] = e.t
            rafale["obus"] = e.ammo or 0

    # Lot « Un seul journal fait foi pour les tirs d'un vol » : une rafale par
    # pression de détente. Des débuts de la même arme à moins de
    # `_CANON_DOUBLE_S` l'un de l'autre (un canon double : une paire par
    # canon) font une seule rafale, dont les obus sont la somme de leurs fins.
    # Un canon simple n'est pas touché.
    pressions: list[dict] = []
    for r in rafales:  # dans l'ordre des débuts
        meme = next(
            (p for p in reversed(pressions)
             if p["arme"] == r["arme"] and r["debut"] - p["dernier_debut"] < _CANON_DOUBLE_S),
            None,
        )
        if meme is None:
            pressions.append({**r, "dernier_debut": r["debut"], "impacts": []})
        else:
            meme["obus"] += r["obus"]
            meme["fin"] = max(meme["fin"], r["fin"])
            meme["dernier_debut"] = r["debut"]
    rafales = pressions

    for h in events:
        if h.type != "hit" or h.weapon or _hit_is_linked_to_any(h):
            continue
        dans = [r for r in rafales if r["debut"] <= h.t <= r["fin"] + _CANON_FENETRE_S]
        if dans:
            max(dans, key=lambda r: r["debut"])["impacts"].append(h)
    return rafales


# Lot « Le journal dit quand un tir touche » : deux pressions de la même arme
# font une seule ligne de canon au journal quand la suivante commence à 5 s au
# plus de la fin de la précédente.
_CANON_LIGNE_ECART_S = 5.0
# Lot « Le journal dit quand un tir touche » : la chaîne des épaves -- un kill
# sans arme dont l'initiateur est déjà détruit (à 0,05 s près) est l'explosion
# de son épave ; on remonte au plus dix maillons.
_EPAVE_TOLERANCE_S = 0.05
_EPAVE_MAILLONS_MAX = 10


def _cibles_touchees(touches: list[MergedEvent]) -> list[tuple[str, str | None]]:
    """Lot « Le journal dit quand un tir touche » : les cibles d'une ligne de
    tir, `(object_id, type)`, dans l'ordre de leur première touche -- une
    cible une fois, sous le type de sa première touche dans la ligne. Une
    touche sans cible identifiée ne compte pas."""
    cibles: dict[str, str | None] = {}
    for h in sorted(touches, key=lambda e: e.t):
        if h.target_object_id and h.target_object_id not in cibles:
            cibles[h.target_object_id] = h.target_unit_type
    return list(cibles.items())


def _cibles_par_type(cibles: list[tuple[str, str | None]]) -> list[dict]:
    """Lot « Le journal dit quand un tir touche » : `targets` --
    `[{"type", "n"}]`, `n` décroissant puis `type` croissant."""
    compte: dict[str | None, int] = {}
    for _, typ in cibles:
        compte[typ] = compte.get(typ, 0) + 1
    return [
        {"type": typ, "n": n}
        for typ, n in sorted(compte.items(), key=lambda kv: (-kv[1], kv[0] or ""))
    ]


def _lignes_canon(events: list[MergedEvent]) -> list[dict]:
    """Lot « Le journal dit quand un tir touche » : les lignes de canon du
    journal d'UN vol (`events` = ses faits de tir, ceux de `_canon_par_arme`).
    Les pressions de `_pressions_canon` de la même arme se groupent quand la
    suivante commence à `_CANON_LIGNE_ECART_S` au plus de la fin de la
    précédente. Chaque ligne porte une clé privée `_cibles`, que
    `_compute_flight_stats` remplace par `outcomes`."""
    groupes: list[list[dict]] = []
    ouverts: dict[str | None, list[dict]] = {}
    for p in _pressions_canon(events):
        g = ouverts.get(p["arme"])
        if g is not None and p["debut"] - g[-1]["fin"] <= _CANON_LIGNE_ECART_S:
            g.append(p)
            continue
        g = [p]
        groupes.append(g)
        ouverts[p["arme"]] = g
    lignes = []
    for g in groupes:
        touches = [h for p in g for h in p["impacts"]]
        cibles = _cibles_touchees(touches)
        lignes.append({
            "weapon": g[0]["arme"],
            "t": g[0]["debut"],
            "cannon": True,
            "shots": len(g),
            "rounds": sum(p["obus"] for p in g),
            "rounds_hit": len(touches),
            "hits": sum(1 for p in g if p["impacts"]),
            "target_unit_types": sorted({typ for _, typ in cibles if typ}),
            "target_object_ids": [oid for oid, _ in cibles],
            "targets": _cibles_par_type(cibles),
            "_cibles": cibles,
        })
    return lignes


def _premiers_kills(merged_events: list[MergedEvent]) -> dict[str, MergedEvent]:
    """Lot « Le journal dit quand un tir touche » : le premier kill de chaque
    cible de la session -- le fait `kill` fusionné de plus petite heure."""
    premiers: dict[str, MergedEvent] = {}
    for e in merged_events:
        if e.type != "kill" or not e.target_object_id:
            continue
        cur = premiers.get(e.target_object_id)
        if cur is None or e.t < cur.t:
            premiers[e.target_object_id] = e
    return premiers


def _tireur_d_origine(
    kill: MergedEvent, premiers: dict[str, MergedEvent]
) -> tuple[MergedEvent, int]:
    """Lot « Le journal dit quand un tir touche » : remonte la chaîne des
    épaves depuis le premier kill d'une cible -- tant que le kill courant
    est sans arme, que son initiateur est un objet réel, autre que sa cible,
    déjà détruit au plus tard `_EPAVE_TOLERANCE_S` après lui, le kill courant
    devient le premier kill de cet initiateur ; `_EPAVE_MAILLONS_MAX` au
    plus. Une unité détruite ne tire plus : c'est son épave qui explose.
    Rend le kill du tireur d'origine et le nombre de maillons."""
    courant = kill
    maillons = 0
    while maillons < _EPAVE_MAILLONS_MAX:
        ioid = courant.initiator_object_id
        if courant.weapon or not _is_real_oid(ioid) or ioid == courant.target_object_id:
            break
        epave = premiers.get(ioid)
        if epave is None or epave.t > courant.t + _EPAVE_TOLERANCE_S:
            break
        courant = epave
        maillons += 1
    return courant, maillons


def _issues_cibles(
    *,
    cibles: list[tuple[str, str | None]],
    targets: list[dict],
    exclude_oids: set[str],
    premiers: dict[str, MergedEvent],
    human_oids: set[str],
    flights_by_oid: dict[str, "ComputedFlight"],
) -> list[dict]:
    """Lot « Le journal dit quand un tir touche » : `outcomes` d'une ligne
    de tir -- l'issue de chaque cible touchée. Détruite par un autre (humain,
    IA, ou explosion d'une épave créditée à son tireur d'origine), par `t`
    croissant ; puis les intactes, groupées par type dans l'ordre de
    `targets`. Une cible dont le tireur d'origine est la même personne que
    le vol n'a pas d'entrée : sa ligne KILL le dit déjà."""
    detruites = []
    intactes: dict[str | None, int] = {}
    for oid, typ in cibles:
        k = premiers.get(oid)
        if k is None:
            intactes[typ] = intactes.get(typ, 0) + 1
            continue
        r, maillons = _tireur_d_origine(k, premiers)
        tireur = r.initiator_object_id
        if tireur in exclude_oids:
            continue
        issue = {
            "type": typ,
            "issue": "detruit",
            "t": k.t,
            "by": (
                _flight_display_label(flights_by_oid.get(tireur))
                if tireur in human_oids else None
            ),
            "by_unit_type": r.initiator_unit_type if _is_real_oid(tireur) else None,
            "by_weapon": r.weapon or None,
        }
        if maillons:
            issue["explosion"] = k.initiator_unit_type
        detruites.append(issue)
    detruites.sort(key=lambda d: d["t"])
    return detruites + [
        {"type": c["type"], "issue": "intact", "n": intactes[c["type"]]}
        for c in targets if c["type"] in intactes
    ]


def _kills_d_explosion(premiers: dict[str, MergedEvent]) -> dict[str, list[dict]]:
    """Lot « Le journal dit quand un tir touche » : une destruction par
    l'explosion d'une épave est un kill normal, crédité au tireur d'origine.
    Rend, par `object_id` du tireur d'origine, les kills `{target_object_id,
    target_unit_type, weapon: None, t, target_coalition?, explosion: {wreck,
    wreck_t}}` des cibles dont le premier kill a au moins un maillon ;
    `_compute_flight_stats` n'ajoute que ceux que le vol ne compte pas déjà."""
    par_tireur: dict[str, list[dict]] = defaultdict(list)
    for toid, k in premiers.items():
        r, maillons = _tireur_d_origine(k, premiers)
        if not maillons:
            continue
        kill = {
            "target_object_id": toid,
            "target_unit_type": k.target_unit_type,
            "weapon": None,
            "t": k.t,
        }
        if k.target_coalition is not None:
            kill["target_coalition"] = k.target_coalition
        kill["explosion"] = {
            "wreck": k.initiator_unit_type,
            "wreck_t": premiers[k.initiator_object_id].t,
        }
        par_tireur[r.initiator_object_id].append(kill)
    return par_tireur


def _shot_hit_linked(shot: MergedEvent, hit: MergedEvent) -> bool:
    """Spec §6.2 : un `shot` est "touché" ssi >= 1 `hit` DU MÊME UPLOAD
    porte `linked_event_id == event_id` du shot -- chaînage intra-fichier."""
    for upload_id, shot_event_id in shot.event_id_by_upload.items():
        hit_linked = hit.linked_event_id_by_upload.get(upload_id)
        if hit_linked is not None and hit_linked == shot_event_id:
            return True
    return False


def _hit_is_linked_to_any(hit: MergedEvent) -> bool:
    return len(hit.linked_event_id_by_upload) > 0 and any(
        v not in (None, "0", "") for v in hit.linked_event_id_by_upload.values()
    )


# =============================================================================
# 7. Catégorisation (spec §6.5) -- table de complétion locale
# =============================================================================


def _collect_all_unit_types(
    acmi_data: acmi_mod.AcmiData | None,
    merged_events: list[MergedEvent],
    merged_graveyard: list[MergedGraveyard],
) -> set[str]:
    types: set[str] = set()
    if acmi_data is not None:
        for obj in acmi_data.objects.values():
            if obj.name:
                types.add(obj.name)
    for e in merged_events:
        if e.initiator_unit_type:
            types.add(e.initiator_unit_type)
        if e.target_unit_type:
            types.add(e.target_unit_type)
    for g in merged_graveyard:
        types.add(g.unit_type)
    return types


async def _persist_unit_categories(db: AsyncSession, unit_types: set[str]) -> None:
    if not unit_types:
        return
    existing = await db.execute(
        select(DebriefUnitCategory).where(DebriefUnitCategory.unit_type.in_(unit_types))
    )
    existing_types = {row.unit_type for row in existing.scalars().all()}
    # Lot « Un dépôt à la fois » (ARC-02, face b) : insertion sans heurt, dans
    # l'ordre trié -- deux recalculs du même type neuf ne se heurtent plus.
    for ut in sorted(unit_types - existing_types):
        display_name, category, resolved_from = categorize.categorize(ut)
        await db.execute(
            pg_insert(DebriefUnitCategory)
            .values(
                unit_type=ut,
                display_name=display_name,
                category=category,
                resolved_from=resolved_from,
            )
            .on_conflict_do_nothing(index_elements=["unit_type"])
        )
    await db.flush()


# =============================================================================
# 8. Persistance (spec : events/graveyard recalculés à neuf ; flights en
#    upsert par clé naturelle pour préserver les overrides manuels + garder
#    un `id` stable pour POST .../identify -- cf. rapport de livraison)
# =============================================================================


def _deterministic_uuid(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_UUID_NAMESPACE, "|".join(parts))


async def _persist_events(
    db: AsyncSession, session_id: uuid.UUID, merged_events: list[MergedEvent]
) -> None:
    await db.execute(
        DebriefEvent.__table__.delete().where(DebriefEvent.session_id == session_id)
    )
    # Fait 9 (rafales) : plusieurs events DISTINCTS peuvent partager la même
    # natural_key (même type/initiator/target/arme au même round(t,1)). L'id
    # uuid5(natural_key) collisionnerait -> rang d'occurrence déterministe.
    # Sûr : la persistance est recalculée à neuf (DELETE + INSERT).
    #
    # Volet G (Addendum 2, Lot Fraîcheur) : `db.add()` inscrit chaque objet
    # dans la carte d'identité de la Session SQLAlchemy -- coût mesuré non
    # négligeable sur une grosse session (20 840 events). Un rendu de main
    # explicite tous les 500 events restaure des battements réguliers
    # (5-6 sur ~6 attendus, mesuré) SANS toucher à un seul objet construit,
    # à un seul identifiant, ni à l'ordre DELETE puis INSERT. Volontairement
    # PAS de asyncio.to_thread ici : `db.add()` touche la carte d'identité
    # de la Session, qui n'est pas sûre entre fils d'exécution -- contraire
    # à `parse_debrief_log`/`parse_acmi` (§5 ci-dessus), fonctions pures sur
    # un chemin de fichier. Ne pose ce rendu de main NULLE PART ailleurs :
    # `_persist_graveyard` (479 lignes, quatre sessions réunies) et
    # `_persist_flights` (60 lignes) sont deux ordres de grandeur sous le
    # seuil où le blocage se voit -- l'ajouter y serait du bruit.
    occ: dict[str, int] = defaultdict(int)
    for i, ev in enumerate(merged_events):
        nk = ev.natural_key()
        n = occ[nk]
        occ[nk] += 1
        db.add(
            DebriefEvent(
                id=_deterministic_uuid("event", str(session_id), nk, str(n)),
                session_id=session_id,
                type=ev.type,
                t=ev.t,
                initiator_object_id=ev.initiator_object_id,
                target_object_id=ev.target_object_id,
                initiator_unit_type=ev.initiator_unit_type,
                target_unit_type=ev.target_unit_type,
                weapon=ev.weapon,
                seen_in=ev.seen_in,
                event_id_by_upload=ev.event_id_by_upload,
                linked_event_id_by_upload=ev.linked_event_id_by_upload,
            )
        )
        if i % 500 == 0:
            await asyncio.sleep(0)
    await db.flush()


async def _persist_graveyard(
    db: AsyncSession, session_id: uuid.UUID, merged_graveyard: list[MergedGraveyard]
) -> None:
    await db.execute(
        DebriefGraveyard.__table__.delete().where(DebriefGraveyard.session_id == session_id)
    )
    for idx, g in enumerate(merged_graveyard):
        key = f"{g.unit_type}|{round(g.x)}|{round(g.y)}"
        db.add(
            DebriefGraveyard(
                id=_deterministic_uuid("graveyard", str(session_id), key),
                session_id=session_id,
                unit_type=g.unit_type,
                coalition=g.coalition,
                x=g.x,
                y=g.y,
                alt=g.alt,
                heading=g.heading,
                seen_in=sorted(g.seen_in),
            )
        )
    await db.flush()


async def _apply_manual_overrides(
    db: AsyncSession, session_id: uuid.UUID, computed_flights: list[ComputedFlight]
) -> None:
    """Applique les identifications manuelles et les détachements existants
    aux vols fraîchement calculés, AVANT le calcul des statistiques
    (`_compute_flight_stats`) et la persistance (`_persist_flights`) -- pour
    que `cf.stats` et `cf.identity_state` dérivent tous deux de la MÊME
    identité retenue.

    Deux valeurs d'`identity_source` sont indexées dans `manual_by_key`,
    TRAITÉES DIFFÉREMMENT (brief v0.9917 §2/§7 P1) :

    - `"manuel"` (inchangé depuis v0.9915) : arbitrage du porteur du 23/08,
      l'automatique nommé l'emporte. Si le moteur a désormais résolu ce vol
      en `nomme` avec un profil, l'override est supersédé -- le vol reste
      intact (profil, indicatif, état, identity_source automatiques), sans
      exiger la concordance des chaînes d'indicatif. Conséquence assumée :
      un override supersédé perd son `identity_source = "manuel"`, donc il
      disparaît de `manual_by_key` au recalcul suivant. C'est voulu -- le
      vol est désormais nommé par le moteur, le prétendre « manuel » serait
      faux. L'indicatif manuel saisi est abandonné au profit de l'indicatif
      observé par DCS ; nécessaire, le roster groupe par indicatif
      normalisé (`groupFlightsByPilot`, `app.js:3462`) et deux graphies
      scinderaient le pilote en deux groupes.
      Lot « La correction à la main superflue » (v1.0067, le porteur, 3
      novembre) : un override qui désigne le MÊME profil que le moteur
      (vol calculé en `nomme` avec ce même `pilote_profile_id`) est lui
      aussi supersédé -- il n'apporte plus rien, et le moteur reprend
      l'indicatif observé. Un override vers un profil DIFFÉRENT reste
      inchangé : il s'applique.

    - `"detache"` (neuf, v0.9917, geste « Détacher » du bordereau) :
      JAMAIS supersédé -- condition explicite, pas un effet de bord de la
      condition ci-dessus (brief §2 : « c'est le défaut que ce lot
      répare »). Le moteur renonce à ce vol tant que le détachement n'est
      pas explicitement oublié (alias) ou remplacé par une nouvelle
      désignation (`POST .../identify`, qui réécrit `identity_source` à
      `"manuel"` et sort donc ce vol de l'état détaché au recalcul
      suivant). `pilote_profile_id` reste `None`, `identity_state` reste
      `"anonyme"` -- l'indicatif observé (`pilot_callsign`) est conservé
      tel qu'il était au moment du détachement, pour rester lisible sur la
      fiche.
    """
    existing_rows = (
        await db.execute(select(DebriefFlight).where(DebriefFlight.session_id == session_id))
    ).scalars().all()

    # Index des overrides manuels ET des détachements existants par clé
    # plausible (objet_id ET acmi_track_id) pour survivre à un changement de
    # clé pivot (ex. jointure tardive ACMI <-> debrief qui bascule "ac:<n>"
    # vers "do:<n>"). Les DEUX valeurs sont ramassées (brief §2, §7 P1) --
    # un détachement qui ne survivrait pas à un tel changement de clé
    # reviendrait au même défaut que ce lot répare.
    manual_by_key: dict[str, DebriefFlight] = {}
    for row in existing_rows:
        if row.identity_source in ("manuel", "detache"):
            if row.object_id:
                manual_by_key[f"do:{row.object_id}"] = row
            if row.acmi_track_id:
                manual_by_key[f"ac:{row.acmi_track_id}"] = row

    for cf in computed_flights:
        natural_key = cf.natural_key()

        override = manual_by_key.get(natural_key)
        if override is None and cf.acmi_track_id:
            override = manual_by_key.get(f"ac:{cf.acmi_track_id}")
        if override is None and cf.object_id:
            override = manual_by_key.get(f"do:{cf.object_id}")

        if override is None:
            continue

        if override.identity_source == "detache":
            # Jamais supersédé : condition à part entière, vérifiée AVANT
            # la règle de supersession ci-dessous qui, elle, ne concerne
            # que "manuel". Le moteur renonce à ce vol.
            cf.pilote_profile_id = None
            cf.pilot_callsign = override.pilot_callsign
            cf.identity_state = "anonyme"
            cf.identity_source = "detache"
            continue

        # Lot « La correction à la main superflue » (v1.0067) : un override
        # qui désigne le même profil que le moteur est supersédé -- le vol
        # garde tout ce que le moteur a calculé.
        if (
            override.pilote_profile_id is not None
            and cf.identity_state == "nomme"
            and cf.pilote_profile_id == override.pilote_profile_id
        ):
            logger.info(
                "Override manuel du même pilote supersédé pour le vol %s : indicatif "
                "manuel '%s' abandonné au profit de l'indicatif automatique '%s'.",
                natural_key,
                override.pilot_callsign,
                cf.pilot_callsign,
            )
            continue

        if (
            override.pilote_profile_id is None
            and cf.identity_state == "nomme"
            and cf.pilote_profile_id is not None
        ):
            logger.info(
                "Override manuel supersédé pour le vol %s : indicatif manuel "
                "'%s' abandonné au profit de l'indicatif automatique '%s'.",
                natural_key,
                override.pilot_callsign,
                cf.pilot_callsign,
            )
            continue

        cf.pilote_profile_id = override.pilote_profile_id
        cf.pilot_callsign = override.pilot_callsign
        cf.identity_state = override.identity_state
        cf.identity_source = "manuel"


def _horloge_mission(debrief_pairs) -> float | None:
    """Lot « Les heures de jour et de nuit » (v1.0068, le porteur, 4 novembre) :
    l'heure du jour de la mission à `t = 0`, en secondes depuis minuit. Le
    `debrief.log` ne la porte qu'à l'évènement `mission start`, champ `ta`
    (l'heure du jour au moment `t` de cet évènement) : l'horloge est `ta - t`.
    Le premier journal -- par `(uploaded_at, id)` -- qui porte un tel
    évènement la donne ; aucun -> `None`. Pure."""
    ordered = sorted(debrief_pairs, key=lambda pair: (pair[0].uploaded_at, str(pair[0].id)))
    for _upload, journal in ordered:
        for e in journal.events:
            if e.type != "mission start" or e.t is None:
                continue
            try:
                ta = float((e.raw or {}).get("ta"))
            except (TypeError, ValueError):
                continue
            return ta - e.t
    return None


def _periode_du_decollage(horloge: float | None, t: float | None) -> str | None:
    """Lot « Les heures de jour et de nuit » : `'nuit'` si l'heure de la
    mission au décollage `t` est entre 19 h 00 (comprise) et 6 h 00 (exclue),
    `'jour'` sinon ; `None` si l'horloge ou `t` est inconnu. Pure."""
    if horloge is None or t is None:
        return None
    h = (horloge + t) % 86400
    return "nuit" if (h >= 68400 or h < 21600) else "jour"


def _poser_periodes(computed_flights: list[ComputedFlight], horloge: float | None) -> None:
    """Lot « Les heures de jour et de nuit » : pose `periode` sur chaque vol,
    d'après son décollage -- le `t` de la première entrée `takeoff` de
    `stats["phases"]`, à défaut `t_start`. Pure (ne touche que `periode`)."""
    for cf in computed_flights:
        decollage = next(
            (p["t"] for p in (cf.stats or {}).get("phases", []) if p.get("type") == "takeoff"),
            None,
        )
        if decollage is None:
            decollage = cf.t_start
        cf.periode = _periode_du_decollage(horloge, decollage)


async def _persist_flights(
    db: AsyncSession, session_id: uuid.UUID, computed_flights: list[ComputedFlight]
) -> None:
    existing_rows = (
        await db.execute(select(DebriefFlight).where(DebriefFlight.session_id == session_id))
    ).scalars().all()
    existing_by_id = {row.id: row for row in existing_rows}

    kept_ids: set[uuid.UUID] = set()

    for cf in computed_flights:
        natural_key = cf.natural_key()
        flight_id = _deterministic_uuid("flight", str(session_id), natural_key)
        kept_ids.add(flight_id)

        existing = existing_by_id.get(flight_id)
        if existing is None:
            db.add(
                DebriefFlight(
                    id=flight_id,
                    session_id=session_id,
                    object_id=cf.object_id,
                    acmi_track_id=cf.acmi_track_id,
                    aircraft_type=cf.aircraft_type,
                    coalition=cf.coalition,
                    pilote_profile_id=cf.pilote_profile_id,
                    pilot_callsign=cf.pilot_callsign,
                    identity_state=cf.identity_state,
                    identity_source=cf.identity_source,
                    t_start=cf.t_start,
                    t_end=cf.t_end,
                    slot_mission=cf.slot_mission,
                    mission_id_dcs=cf.mission_id_dcs,
                    stats=cf.stats,
                    # Lot « Les heures de jour et de nuit » : la période que
                    # calcule le moteur ; `periode_corrigee` n'est jamais
                    # touchée ici (la correction à la main survit au recalcul).
                    periode=cf.periode,
                )
            )
        else:
            existing.object_id = cf.object_id
            existing.acmi_track_id = cf.acmi_track_id
            existing.aircraft_type = cf.aircraft_type
            existing.coalition = cf.coalition
            existing.pilote_profile_id = cf.pilote_profile_id
            existing.pilot_callsign = cf.pilot_callsign
            existing.identity_state = cf.identity_state
            existing.identity_source = cf.identity_source
            existing.t_start = cf.t_start
            existing.t_end = cf.t_end
            existing.slot_mission = cf.slot_mission
            existing.mission_id_dcs = cf.mission_id_dcs
            existing.stats = cf.stats
            existing.periode = cf.periode

    # Nettoyage des clés obsolètes (ex. vol ACMI-seul absorbé par une
    # jointure ultérieure -- son contenu est fusionné dans le vol joint,
    # rien n'est perdu ; cf. décision d'implémentation en tête de module).
    stale_ids = set(existing_by_id) - kept_ids
    for sid in stale_ids:
        await db.delete(existing_by_id[sid])

    await db.flush()


# =============================================================================
# 9. Orchestration du recalcul complet (spec §7 -- point d'entrée principal)
# =============================================================================


def _duree_session(acmi_data, debrief_pairs) -> int | None:
    """Lot « Les dettes du moteur » : la durée de la session, de la première
    arrivée à la dernière sortie, en temps de mission. Chaque journal y entre
    de son premier évènement (son arrivée) à sa sortie (`mission_time`, ou à
    défaut son dernier évènement) ; la durée de l'ACMI l'emporte si elle est
    plus longue. `None` sans aucune source."""
    debuts: list[float] = []
    fins: list[float] = []
    for _upload, journal in debrief_pairs:
        temps = [e.t for e in journal.events if e.t is not None]
        if not temps:
            continue
        debuts.append(min(temps))
        fins.append(max(temps))
        if journal.header.mission_time is not None:
            fins.append(journal.header.mission_time)
    candidates: list[int] = []
    if debuts:
        candidates.append(int(round(max(fins) - min(debuts))))
    if acmi_data is not None and acmi_data.meta.duration_s is not None:
        candidates.append(acmi_data.meta.duration_s)
    return max(candidates) if candidates else None


def _acmi_qui_fait_foi(uploads) -> DebriefUpload | None:
    """Lot « Le rattachement des dépôts » (R326) : l'ACMI d'une session qui en
    porte plusieurs (après une fusion ou un déplacement) est celui déposé le
    premier -- par `uploaded_at`, puis `id`. Auparavant : le premier rendu par
    la base, sans ordre. Pure."""
    acmis = [u for u in uploads if u.kind == "acmi"]
    if len(acmis) <= 1:
        return acmis[0] if acmis else None
    return min(acmis, key=lambda u: (u.uploaded_at, str(u.id)))


async def recompute_session(db: AsyncSession, session_id: uuid.UUID) -> dict:
    uploads = (
        await db.execute(select(DebriefUpload).where(DebriefUpload.session_id == session_id))
    ).scalars().all()

    acmi_upload = _acmi_qui_fait_foi(uploads)
    acmi_data: acmi_mod.AcmiData | None = None
    if acmi_upload is not None and acmi_upload.raw_stored_path:
        # Lot Fraîcheur v0.9939, correctif de gel (brief §5) : lecture/parse
        # synchrone déportée sur un thread -- une coroutine qui calcule en
        # synchrone bloque toute la boucle d'évènements pendant sa durée.
        # Aucun calcul, aucun résultat ne change : seul l'endroit où le
        # travail s'exécute change. Lecteur sûr en fil (aucun état mutable
        # de module, aucun cache, vérifié).
        acmi_data = await asyncio.to_thread(acmi_mod.parse_acmi, acmi_upload.raw_stored_path)

    debrief_pairs: list[tuple[DebriefUpload, debriefer_mod.DebriefLogData]] = []
    for u in uploads:
        if u.kind == "debrief" and u.raw_stored_path:
            # Même correctif que ci-dessus, même raison (brief §5).
            parsed = await asyncio.to_thread(debriefer_mod.parse_debrief_log, u.raw_stored_path)
            debrief_pairs.append((u, parsed))

    merged_events = _merge_events(debrief_pairs)
    # Lot « Le Débrief : la destruction probable » (R9) : les morts sans tueur
    # reçoivent celui que l'ACMI désigne ; ces kills suivent ensuite le chemin
    # de tous les kills.
    merged_events = merged_events + _kills_probables(merged_events, acmi_data)
    merged_graveyard = _merge_graveyard(debrief_pairs)
    object_types = _collect_object_types(debrief_pairs)

    identities = await _resolve_identities(db, debrief_pairs, object_types)
    computed_flights = _build_flights(
        acmi_data=acmi_data,
        debrief_pairs=debrief_pairs,
        object_types=object_types,
        identities=identities,
    )
    await _attach_profiles_by_name(db, computed_flights)
    await _apply_manual_overrides(db, session_id, computed_flights)
    _compute_flight_stats(computed_flights, merged_events, acmi_data, debrief_pairs)
    # Lot « Les heures de jour et de nuit » : la période de chaque vol, après
    # les stats (elle lit les phases).
    horloge = _horloge_mission(debrief_pairs)
    _poser_periodes(computed_flights, horloge)

    unit_types = _collect_all_unit_types(acmi_data, merged_events, merged_graveyard)
    await _persist_unit_categories(db, unit_types)

    await _persist_events(db, session_id, merged_events)
    await _persist_graveyard(db, session_id, merged_graveyard)
    await _persist_flights(db, session_id, computed_flights)

    session = await db.get(DebriefSession, session_id)
    session.acmi_present = acmi_data is not None
    session.duration_s = _duree_session(acmi_data, debrief_pairs)
    session.horloge_mission_s = horloge
    if acmi_data is not None:
        if acmi_data.meta.title:
            session.title = acmi_data.meta.title
        if acmi_data.meta.recording_time:
            session.reference_time = acmi_data.meta.recording_time
            session.mission_date = acmi_data.meta.recording_time.date()
    # Lot Fraîcheur v0.9939 (brief §4) : empreinte courante du moteur posée
    # avec les autres écritures sur la session -- après ce recalcul, cette
    # session porte l'empreinte qui l'a produite et n'est donc plus périmée
    # (`revision.is_stale`) tant que le moteur ne change pas à nouveau.
    session.stats_engine_rev = revision.ENGINE_REVISION
    await db.flush()

    return await _session_summary(db, session_id)


async def recompute_stale_sessions(db: AsyncSession) -> tuple[int, int]:
    """Recalcule, **une par une, jamais deux en parallèle**, toutes les
    sessions dont l'empreinte moteur est périmée -- Lot Fraîcheur v0.9939,
    brief §6/§7. **Fonction unique** appelée à la fois par la tâche de fond
    du `lifespan` (`app/main.py`) et par la route admin
    `POST /sessions/recompute-stale` (`app/debrief/api.py`) : pas de second
    chemin de code pour la même opération.

    Le prédicat de péremption (`revision.is_stale`) n'est jamais réécrit en
    ligne ici : on lit seulement `(id, stats_engine_rev)` pour chaque
    session, et c'est l'unique fonction du §4 qui tranche.

    Lot « Un dépôt à la fois » (`v1.0072`, ARC-02, ARC-07) : chaque session se
    recalcule et se `commit` sous `_verrou_depot`, relâché entre deux sessions
    (un dépôt attend au plus une session) -- le verrou protège du dépôt, que le
    recalcul unitaire seul ne gênait pas. Une session en échec (fichier brut
    absent, etc.) est annulée (`rollback`), journalisée, et reste périmée ; la
    boucle passe à la suivante. Une session disparue depuis la lecture de la liste
    (supprimée ou fusionnée) est sautée sans être comptée. Rend `(recalculees, echecs)`."""
    rows = (
        await db.execute(select(DebriefSession.id, DebriefSession.stats_engine_rev))
    ).all()
    stale_ids = [sid for sid, rev in rows if revision.is_stale(rev)]

    recalculees = 0
    echecs = 0
    for session_id in stale_ids:
        async with _verrou_depot:
            try:
                # Session supprimée ou fusionnée depuis la lecture de la liste :
                # sautée, ni recalculée ni en échec.
                if await db.get(DebriefSession, session_id) is None:
                    continue
                await recompute_session(db, session_id)
                await db.commit()
                recalculees += 1
            except Exception as exc:
                await db.rollback()
                echecs += 1
                logger.warning(
                    "Fraîcheur : recalcul de la session %s en échec : %r",
                    str(session_id)[:8],
                    exc,
                )
    return recalculees, echecs


async def _session_summary(db: AsyncSession, session_id: uuid.UUID) -> dict:
    session = await db.get(DebriefSession, session_id)
    uploads = (
        await db.execute(select(DebriefUpload).where(DebriefUpload.session_id == session_id))
    ).scalars().all()
    flights = (
        await db.execute(select(DebriefFlight).where(DebriefFlight.session_id == session_id))
    ).scalars().all()
    n_kills = sum(len(f.stats.get("kills", [])) for f in flights)
    return {
        "session_id": str(session_id),
        "title": session.title if session else None,
        "mission_date": session.mission_date.isoformat() if session and session.mission_date else None,
        "acmi_present": session.acmi_present if session else False,
        "n_uploads": len(uploads),
        "n_flights": len(flights),
        "n_kills": n_kills,
    }
