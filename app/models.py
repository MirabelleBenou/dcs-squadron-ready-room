"""Modèle de données Postgres — cf. SPEC_TECHNIQUE_READY_ROOM_Planification_v1 §3.

Toutes les tables/enums de la spec sont créées dès la migration 0001, même si
ce Lot 1 n'utilise en pratique que `profiles`.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base

# --- Enums --------------------------------------------------------------

EventType = SAEnum(
    "entrainement", "mission", "jeulibre", "campagne", name="event_type"
)
RsvpState = SAEnum("present", "maybe", "absent", name="rsvp_state")
OverrideStatus = SAEnum("cancelled", "modified", name="override_status")
# Lot 2.2b -- DEUX valeurs seulement : "fermé" est un synonyme de "en
# sommeil" (arbitrage du porteur du 11 août, cf. brief §3). Ne pas en
# ajouter une troisième, même "pour plus tard".
SquadronStatus = SAEnum("actif", "sommeil", name="squadron_status")
# Phase 3, lot 3.1 -- TROIS valeurs, pas plus : la hiérarchie de
# l'attribution des rôles (lot 3.2) en dépend. Cf. spec Socle v1.1 §3.2.
MembershipRole = SAEnum("leader", "deputy", "member", name="membership_role")
# Lot « Les relances » (R6) -- l'issue d'un MP de relance. `echec` ne vaut pas
# « prévenu » : la passe suivante réessaie.
RelanceStatut = SAEnum("envoye", "refuse", "echec", name="relance_statut")
# Lot « La connexion de secours » (R325) -- d'où vient un lien d'entrée : la
# commande `/readyroom` dans Discord, ou un administrateur au Centre.
LoginLinkSource = SAEnum("discord", "admin", name="login_link_source")


# --- Tables ---------------------------------------------------------------


class Profile(Base):
    """Un profil par membre Discord."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Discord user id
    username: Mapped[str] = mapped_column(Text, nullable=False)
    global_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    locale: Mapped[str] = mapped_column(Text, nullable=False, default="fr")
    tz: Mapped[str] = mapped_column(Text, nullable=False, default="Europe/Paris")
    # Escadrille resolue au login (cf. SPEC Escadrilles A3, migration 0002).
    squadron: Mapped[str | None] = mapped_column(Text, nullable=True)
    roles_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # v0.36 : horodatage de derniere visite (tag "NOUVEAU"), mis a jour par
    # POST /api/seen ; distinct de last_login_at (auth).
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Lot « L'appel » (R184) : la date à laquelle l'appel a trouvé le profil
    # hors de l'effectif ; NULL tant qu'il y figure. Archiver, c'est dater.
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Lot « Les cartes DCS de chaque pilote » (v1.0085, R640) : les cartes que
    # le pilote déclare posséder, dans l'ordre de `CARTES_DCS`. NULL = non
    # déclaré ; [] = déclaré sans carte. `cartes_dcs_le` date la déclaration.
    cartes_dcs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    cartes_dcs_le: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    events_created: Mapped[list["Event"]] = relationship(back_populates="creator")


class Event(Base):
    """Définition d'un événement (unique ou série récurrente)."""

    __tablename__ = "events"
    __table_args__ = (Index("ix_events_start_at", "start_at"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(EventType, nullable=False)
    game_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    # v0.23 : map fermee (mission/entrainement) -- mutuellement exclusive
    # avec game_label (jeu libre), exclusivite geree cote app/events.py.
    map_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recurrence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    creator: Mapped["Profile"] = relationship(back_populates="events_created")


class OccurrenceOverride(Base):
    """Exception (annulation/modification) d'une occurrence d'une série."""

    __tablename__ = "occurrence_overrides"
    __table_args__ = (
        UniqueConstraint("event_id", "occ_date", name="uq_override_event_occdate"),
        Index("ix_overrides_event_occdate", "event_id", "occ_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False
    )
    occ_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(OverrideStatus, nullable=False)
    patch: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class Presence(Base):
    """RSVP — un par (membre × occurrence)."""

    __tablename__ = "presences"
    __table_args__ = (
        UniqueConstraint(
            "event_id", "occ_date", "profile_id", name="uq_presence_event_occ_profile"
        ),
        Index("ix_presences_event_occdate", "event_id", "occ_date"),
        Index("ix_presences_profile_id", "profile_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False
    )
    occ_date: Mapped[date] = mapped_column(Date, nullable=False)
    profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=False
    )
    state: Mapped[str] = mapped_column(RsvpState, nullable=False)
    # Preferences RSVP (cf. SPEC Escadrilles/RSVP B.2, migration 0002) :
    # facultatives, restreintes en API aux evenements mission/entrainement.
    aircraft: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    mission_types: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Lot 2b-1 -- ordre d'inscription reel (dette (2)), distinct de
    # updated_at (qui bouge a chaque changement d'etat). Backfillee =
    # updated_at a la migration 0009 pour les lignes preexistantes.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class OccurrenceMessage(Base):
    """Message Discord (bot RSVP) actif pour une occurrence -- Phase 2b,
    Lot 2b-1. Une ligne par occurrence ayant un message pose. Pas de
    `closed_at` (D7 : fin de vie = suppression de la ligne, pas de
    cloture conservee) -- cf. BRIEF_SONNET_ReadyRoom_Lot2b-1 §2/§7d."""

    __tablename__ = "occurrence_messages"

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    occ_date: Mapped[date] = mapped_column(Date, primary_key=True)
    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[str] = mapped_column(Text, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DiscordDigestMessage(Base):
    """Singleton (id=1 toujours) du message digest Discord courant --
    Extension 2a.1 (édition en direct + remplacement). Cf. SPEC/BRIEF
    BRIEF_SONNET_ReadyRoom_v0.22 §1. `pending_delete` = file de retry des
    suppressions échouées (jamais perdues)."""

    __tablename__ = "discord_digest_message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    pending_delete: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    week_monday: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Wing(Base):
    """L'escadre (Lot 2.2b, cf. brief §3) -- une seule ligne, semée depuis
    `WING_TAG`. N'existe que pour que `name_strip_tokens` (cf. app/squadron.py)
    lise une seule source (la base) au lieu d'être à cheval entre la base et
    le `.env`."""

    __tablename__ = "wing"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    designation: Mapped[str] = mapped_column(Text, nullable=False)
    tag: Mapped[str] = mapped_column(Text, nullable=False)
    # Lot « L'écran Escadre du Centre » (migration 0033) : l'identité de
    # l'escadre. Toutes nullables -- une ligne recréée depuis `WING_TAG`
    # (reconcile_squadrons_from_env) les a NULL et tout replie proprement.
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    period: Mapped[str | None] = mapped_column(Text, nullable=True)
    sigle: Mapped[str | None] = mapped_column(Text, nullable=True)
    emblem_sha: Mapped[str | None] = mapped_column(Text, nullable=True)


class Squadron(Base):
    """Une escadrille (Lot 2.2b, cf. brief §3). Elle se saisit à l'écran
    Escadrilles du Centre (elle se semait depuis le `.env` jusqu'au v1.0105) ;
    le statut `sommeil` est celui d'une escadrille sans rôle Discord
    (`discord_role_id` NULL), qui n'est donc jamais résolue, cf. brief §5.

    `id` est un entier auto-incrémenté (Identity), pas un UUID comme le
    reste de l'application : la résolution (§5) exige la PREMIÈRE
    correspondance "dans l'ordre de la table", et un entier croissant est le
    seul moyen simple de garantir cet ordre de façon déterministe --
    `created_at` ne le pourrait pas (plusieurs lignes semées dans la même
    transaction de migration partagent le même `now()` Postgres).

    Lot 3.2e, volet ① -- au plus UNE escadrille ACTIVE par
    `discord_role_id`, garanti en base (index unique partiel, migration
    0016) : deux escadrilles peuvent partager un rôle si l'une des deux
    est en sommeil (`discord_role_id` y est de toute façon NULL).

    Lot 3.2e, volet ② -- `crest_sha` (migration 0017) : sha256 du PNG
    normalisé effectivement stocké sur le volume `crests` (cf.
    app/crests.py), `NULL` = aucun écusson posé. Une escadrille en sommeil
    garde son écusson (délibéré, cf. brief §2 point 4) : contrairement à
    `discord_role_id`, rien ici ne s'efface à l'endormissement.

    Lot « L'appareil de l'escadrille » -- `aircraft` (migration 0026) :
    la liste ordonnée des appareils que l'escadrille déclare au Centre
    (« Mi-24P », « Mi-8 »), quatre au plus, normalisée par
    `app.command.api._normalize_aircraft`. `NULL` = rien de déclaré.
    Une escadrille en sommeil garde ses appareils, comme son écusson.

    Lot « L'identité de l'escadrille » (R189, migration 0028) -- l'identité
    tient en trois champs : `designation`, l'identifiant (« ALPHA-11 »), qui
    est AUSSI le préfixe retiré des pseudos (`squadron.get_name_strip_tokens`) ;
    `callsign`, le callsign radio (« Kodiak »), ex-`tag`, facultatif ;
    `full_name`, le nom complet (« Alpha Eleven Squadron »),
    facultatif.

    Lot « La config d'escadre de Mission Plan fabriquée par le Centre »
    (migration 0044) -- `liveries`, `default_liveries` et `nickname` : ses livrées
    et son surnom."""

    __tablename__ = "squadron"
    __table_args__ = (
        Index(
            "ux_squadron_discord_role_id_actif",
            "discord_role_id",
            unique=True,
            postgresql_where=text(
                "discord_role_id IS NOT NULL AND status = 'actif'"
            ),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    designation: Mapped[str] = mapped_column(Text, nullable=False)
    callsign: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(SquadronStatus, nullable=False)
    discord_role_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    wing_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("wing.id"), nullable=False
    )
    crest_sha: Mapped[str | None] = mapped_column(Text, nullable=True)
    aircraft: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Lot « La config d'escadre de Mission Plan fabriquée par le Centre »
    # (migration 0044) : les livrées de l'escadrille -- une liste de
    # {"name", "aircraft", "jeu"} -- et sa livrée par défaut par appareil
    # ({appareil: nom}). NULL = rien de déclaré ; les appareils s'écrivent comme
    # `aircraft`.
    liveries: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    default_liveries: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    nickname: Mapped[str | None] = mapped_column(Text, nullable=True)


class SquadronMembership(Base):
    """Appartenance datée d'un profil à une escadrille (Lot 2.2b, cf. brief
    §3/§5). Au plus UNE appartenance ouverte (`ended_at IS NULL`) par
    profil -- garanti par un index unique PARTIEL, en base et non
    seulement dans le code."""

    __tablename__ = "squadron_membership"
    __table_args__ = (
        Index(
            "ux_squadron_membership_open_per_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
        ),
        # Lot 3.2d, Volet 1 -- au plus UN `leader` et UN `deputy` OUVERTS par
        # escadrille, garanti en base et non seulement au niveau applicatif
        # (idiome exact de `ux_squadron_membership_open_per_profile`
        # ci-dessus, migration 0014). C'est cette contrainte que le geste
        # atomique de désignation (abaisser puis promouvoir, `db.flush()`
        # entre les deux) doit respecter sans jamais la heurter.
        Index(
            "ux_squadron_leader_per_squadron",
            "squadron_id",
            unique=True,
            postgresql_where=text("role = 'leader' AND ended_at IS NULL"),
        ),
        Index(
            "ux_squadron_deputy_per_squadron",
            "squadron_id",
            unique=True,
            postgresql_where=text("role = 'deputy' AND ended_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=False
    )
    squadron_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("squadron.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Phase 3, lot 3.1 -- rang de rattachement (cf. spec Socle v1.1 §3.2,
    # can_admin_squadron()). Défaut 'member' : reprise des lignes
    # existantes, aucune source pour en déduire autre chose. À la
    # réouverture d'une appartenance, app/squadron.py reporte le rôle de la
    # plus récente appartenance close sur la même escadrille (spec §9).
    role: Mapped[str] = mapped_column(
        MembershipRole, nullable=False, server_default="member"
    )
    # Lot 3.2d, Volet 1 (migration 0014) -- traçabilité de qui a posé ce
    # rang et quand. NULL signifie « écrit par le système » : c'est
    # exactement le cas d'un rang REPORTÉ par `sync_squadron_membership()`
    # (app/squadron.py:120-140) à la réouverture d'une appartenance sur la
    # même escadrille -- aucun agissant humain n'est à l'origine de ce
    # report. Même sémantique que `AccountCapability.granted_by` ci-dessous.
    # Nullable : les lignes existantes et les reports système n'en portent
    # pas.
    role_granted_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )
    role_granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class RoleCapability(Base):
    """Permissions pilotées par la donnée (extensibilité — vide au Lot 1).

    La portée par escadrille a été écartée par arbitrage (phase 3, lot 3.1,
    cf. spec Socle v1.1 §0 arbitrage n°1) : la portée est une appartenance,
    pas une capacité."""

    __tablename__ = "role_capabilities"
    __table_args__ = (
        PrimaryKeyConstraint("role_id", "capability", name="role_capabilities_pkey"),
    )

    role_id: Mapped[str] = mapped_column(Text)
    capability: Mapped[str] = mapped_column(Text)


class AccountCapability(Base):
    """Octroi nominatif d'une capacité à un compte, indépendamment de ses
    rôles Discord (Phase 3, lot 3.1, cf. spec Socle v1.1 §3.1).

    Lot 3.2d, Volet 1 (§5.6) -- CONSERVÉE et RÉAFFECTÉE : la capacité admise
    en v1 était `command.access` (résolution désormais assurée par
    `has_command_access()`, cf. `app/capabilities.py`, qui ne la consulte
    plus) ; elle porte désormais `event.create`, les éditeurs nominatifs du
    planning (cf. brief §5.4/§6.3, écran Droits, bloc 3).

    Aucune colonne de portée : c'est la conséquence directe de l'arbitrage
    n°1 (la portée est une appartenance, pas une capacité). Aucune
    contrainte `CHECK` sur `capability` : la restriction à `event.create`
    est portée par la spec et par l'écran Droits, pas par la base -- une
    contrainte figerait la table au premier ajout de capacité.

    Lot « Correctif des relances nominatives » (migration 0032) : elle porte
    aussi `relances.destinataire`, les comptes choisis par leur nom pour
    recevoir les MP de relance (la table `profile_capabilities` du `v1.0019`,
    qui la doublait, est reprise ici puis retirée).

    Table naît vide, aucun semis -- `ADMIN_IDS` assure l'amorçage."""

    __tablename__ = "account_capability"

    profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), primary_key=True
    )
    capability: Mapped[str] = mapped_column(Text, primary_key=True)
    granted_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CommandJournal(Base):
    """Lot « Polish du Centre » (migration 0036) -- le journal des modifications
    du Centre de Commandement. Une ligne par écriture du Centre qui a changé
    quelque chose : `par_id` l'agissant, `action` le geste (`squadron.edit`,
    `rights.app_access`, …), `objet` ce qu'il touche (nul quand le geste n'en a
    pas), `lignes` le détail -- l'avant et l'après, une liste JSON écrite par
    `app.command.journal.ecarts`. Elle se lit à l'écran Archives, pour un
    administrateur seul ; aucune route ne la modifie ni ne l'efface.

    `fait_le` prend l'heure de PostgreSQL à l'écriture."""

    __tablename__ = "command_journal"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    fait_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    par_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(Text, nullable=False)
    objet: Mapped[str | None] = mapped_column(Text, nullable=True)
    lignes: Mapped[list] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), nullable=False, default=list
    )


class AgentJeton(Base):
    """Lot « La réception du .rrlog de l'agent » (v1.0089, migration 0043) -- le jeton
    de l'agent du serveur DCS. 32 octets aléatoires, préfixés (voir `app.agent`) ; SEULE
    l'empreinte (sha256 hexadécimal, unique) est gardée, le jeton en clair ne
    vit que dans la réponse de l'émission. Un seul jeton actif
    (`revoque_le` nul) : émettre révoque l'actif dans la même transaction.
    `emis_par` est l'identifiant du compte (texte, sans clé étrangère)."""

    __tablename__ = "agent_jeton"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    empreinte: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    emis_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    emis_par: Mapped[str] = mapped_column(Text, nullable=False)
    revoque_le: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dernier_envoi_le: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentRrlog(Base):
    """Lot « La réception du .rrlog de l'agent » (v1.0089, migration 0043) -- le
    registre des fichiers reçus de l'agent, sans session : une ligne par
    `.rrlog` (sha256 du fichier décompressé, unique). Le corps gzip reçu est
    rangé sous `DEBRIEF_STORAGE_DIR/_agent/<sha256>.rrlog.gz` (`chemin`, relatif).
    Les champs de la ligne `H` sont nullables. `etat` vaut `en_attente` ;
    `session_id` reste vide (sans clé étrangère) jusqu'à la lecture par le Débrief."""

    __tablename__ = "agent_rrlog"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    sha256: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    fichier: Mapped[str] = mapped_column(Text, nullable=False)
    chemin: Mapped[str] = mapped_column(Text, nullable=False)
    taille_gz: Mapped[int] = mapped_column(BigInteger, nullable=False)
    taille: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recu_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    jeton_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_jeton.id"), nullable=False
    )
    format: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agent_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    theatre: Mapped[str | None] = mapped_column(Text, nullable=True)
    date_mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    depart_reel: Mapped[str | None] = mapped_column(Text, nullable=True)
    etat: Mapped[str] = mapped_column(Text, nullable=False)
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    __table_args__ = (Index("ix_agent_rrlog_recu_le", "recu_le"),)


class SauvegardeAutoReglage(Base):
    """Lot « Les sauvegardes automatiques » (migration 0037) -- le réglage de
    la sauvegarde automatique : une ligne au plus (`id = 1`, garanti par la
    contrainte `ck_sauvegarde_auto_reglage_unique`). `intervalle_h` est la
    fréquence en heures (`0` : désactivée), `garder` le nombre d'automatiques
    gardées. Sans ligne, le réglage est le défaut de `app/sauvegardes_auto.py`
    (24 h, 7). Un administrateur l'écrit à l'écran Archives.

    `modifie_le` prend l'heure de PostgreSQL à l'écriture."""

    __tablename__ = "sauvegarde_auto_reglage"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_sauvegarde_auto_reglage_unique"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    intervalle_h: Mapped[int] = mapped_column(Integer, nullable=False)
    garder: Mapped[int] = mapped_column(Integer, nullable=False)
    modifie_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RelanceEnvoi(Base):
    """Lot « Les relances » (R6, migration 0030) -- un MP de relance noté :
    `destinataire_id` a reçu (ou n'a pas pu recevoir) un MP qui signalait
    `pilote_id` comme n'ayant plus répondu au planning. Une ligne par couple
    (destinataire, pilote signalé dans ce MP), `statut` celui du MP. Sert à
    ne signaler un pilote qu'une fois à chacun (`app/relances.py`, R4).

    `envoye_le` se pose en Python (`datetime.now(timezone.utc)`), jamais par
    un défaut SQL : le banc fige l'heure de Python, alors que celle de
    PostgreSQL avance."""

    __tablename__ = "relance_envois"
    __table_args__ = (
        Index("ix_relance_envois_dest_pilote", "destinataire_id", "pilote_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    destinataire_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=False
    )
    # Lot « rr-socle-proprete » (migration 0046) : indexée, la colonne se lit en filtre.
    pilote_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=False, index=True
    )
    envoye_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    statut: Mapped[str] = mapped_column(RelanceStatut, nullable=False)


class LoginLink(Base):
    """Lot « La connexion de secours » (R325, migration 0038) -- un lien
    d'entrée à usage unique. `token_hash` est le SHA-256 hexadécimal du jeton :
    le jeton lui-même n'est jamais stocké. `source` dit d'où vient le lien
    (`discord` : la commande `/readyroom`, 5 minutes ; `admin` : le Centre,
    24 heures) ; `created_by` est l'administrateur émetteur (nul pour
    `discord`). `expires_at` et `used_at` se posent en Python
    (`app/connexion_secours.py`) : une seule horloge pour émettre et consommer."""

    __tablename__ = "login_links"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    profile_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[str] = mapped_column(LoginLinkSource, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Invitation(Base):
    """Lot « L'accès invité » (v1.0070, migration 0041) -- une personne hors du
    serveur Discord de l'escadre, autorisée par son identifiant Discord à
    voir la Ready Room en lecture seule. `discord_id` est la clé primaire,
    SANS clé étrangère : l'invité n'a pas de profil, son identité ne vit que
    dans sa session et dans cette table. `invite_par` est l'administrateur qui
    a invité (une prolongation ne le change pas). Une invitation est active
    quand `revoque_le` est nul et `jusqua` postérieur à maintenant
    (`app.auth.invitation_active`)."""

    __tablename__ = "invitations"

    discord_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=False
    )
    nom: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    invite_par: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=False
    )
    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    jusqua: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoque_le: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    derniere_entree: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Reglage(Base):
    """Lot « rr-env-epure » (v1.0105, migration 0045) -- un réglage de l'application gardé
    en base, qui n'est plus lu du `.env`. `cle` est le nom du réglage (`app/reglages.py`
    en tient les définitions) ; `valeur` son texte -- le jeton Fernet d'un secret, jamais le
    clair ; `maj_le` l'heure de PostgreSQL à l'écriture, `maj_par` l'agissant (nul pour une
    reprise du `.env`). Une ligne de plus, `_reprise`, marque la reprise unique du premier
    démarrage (sa valeur : l'instant ISO de la reprise). Aucune ligne pour un réglage
    vide : il vaut son défaut."""

    __tablename__ = "reglage"

    cle: Mapped[str] = mapped_column(Text, primary_key=True)
    valeur: Mapped[str] = mapped_column(Text, nullable=False)
    maj_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    maj_par: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )
