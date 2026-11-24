"""Modèle de données — Module Debriefing (Lot D1), cf.
SPEC_READY_ROOM_Debrief_Fusion_v1 (v1.1) et BRIEF_SONNET_ReadyRoom_Debrief_D1.

6 tables, migration `0007_debrief_core`. Fichier dédié (ne gonfle pas
`app/models.py`) ; `Base` réutilisée depuis `app.db`. Conventions identiques
au reste du projet (Mapped / mapped_column, JSONB, DateTime timezone-aware).

Rappel produit (spec §1) : une session de vol = 1 ACMI + N debrief.log de la
même mission. L'information est monotone croissante ; aucune table de ce
module n'est jamais mutée par suppression, uniquement par enrichissement
(le moteur de fusion, app/debrief/engine.py, recalcule tout à chaque upload).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base

# Lot 2.3 -- DEUX statuts seulement, cf. brief §3. Sans rapport avec
# `EventType` ('campagne', app/models.py:33) : les deux objets « Campagne »
# coexistent sans parenté (brief §2), la charnière est en phase 7.
CampaignStatus = SAEnum("en_cours", "close", name="campaign_status")

# Lot « Mission ou training » (migration 0035) : la nature d'une session,
# sur le patron de `SquadronStatus` (app/models.py).
SessionNature = SAEnum("mission", "training", name="session_nature")


class Campaign(Base):
    """Une campagne (Lot 2.3, cf. brief §3). Entité de la couche débrief --
    vit ici et non dans `app/models.py`, à côté de `DebriefSession` qui la
    référence. Sans rapport avec `EventType.campagne` (Planification) : les
    deux objets « Campagne » coexistent sans parenté (brief §2), la
    charnière est en phase 7.

    `id` en UUID et non en entier, contrairement à `Squadron` : aucune
    règle de résolution "première correspondance dans l'ordre de la table"
    ici -- on suit la convention de la couche débrief (UUID partout).

    `map_name` et non `theater` : la notion existe déjà sous ce nom côté
    Planification (app/models.py:88) -- éviter l'homonymie entre deux
    modules pour une même chose.

    Lot 3.4 : `conflict`, `started_on`, `ended_on` sont RETIRÉES (migration
    0019, arbitrage du porteur du 22 août -- dormantes sans emploi depuis leur
    création, cf. brief §4). Restent deux champs dormants -- `map_name`
    (saisi, jamais affiché dans ce lot) et `description` (saisie, affichée
    seulement sur l'écran Campagnes du Débriefing, pas dans ce lot) : ni
    l'un ni l'autre n'a d'interface au-delà de sa saisie."""

    __tablename__ = "campaign"
    __table_args__ = (
        # Fonctionnel, insensible à la casse (brief §3) : deux campagnes de
        # même nom à la casse près, sur le même simulateur, sont refusées ;
        # sur deux simulateurs différents, acceptées.
        Index(
            "ux_campaign_sim_lower_name",
            "sim",
            text("lower(name)"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    map_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        CampaignStatus, nullable=False, default="en_cours"
    )
    sim: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="dcs", default="dcs"
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class DebriefSession(Base):
    """Une session de vol = une mission multijoueur reconstituée par
    accumulation d'uploads (1 ACMI + N debriefs). Cf. spec §1/§3."""

    __tablename__ = "debrief_session"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Titre mission : ACMI `Title` en priorité, sinon `mission_file_path`
    # d'un debrief (cf. app/debrief/engine.py::_derive_session_title).
    # Technique, dérivé, écrasé sans condition par l'ACMI -- jamais affiché
    # (Lot 2.1 §2). Le nom affiché est display_name (repli embelli sinon) --
    # cf. app/debrief/display.py, jamais dérivé ici.
    title: Mapped[str] = mapped_column(Text, nullable=False)
    # Nom saisi par un déposant (Lot 2.1, migration 0010) : None tant que
    # personne ne l'a défini -- ne remplace jamais `title`, qui reste seul
    # utilisé par `_resolve_session` pour le rattachement des dépôts.
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Note libre pour l'escadre, jointe à la session (Lot 2.1, migration
    # 0010). Aucun effet sur le rattachement ni sur le calcul de stats.
    wing_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reference_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_s: Mapped[int | None] = mapped_column(nullable=True)
    acmi_present: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sim: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="dcs", default="dcs"
    )
    # Rattachement à une campagne (Lot 2.3, migration 0012) : nullable, et
    # c'est un état normal, pas un défaut -- spec Carrière §6, "sessions
    # hors campagne = état normal". Aucune valeur par défaut, aucun
    # rattachement automatique.
    # Lot « rr-socle-proprete » (migration 0046) : indexée, la colonne se lit en filtre.
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign.id"), nullable=True, index=True
    )
    # Lot « Mission ou training » (migration 0035) : mission par défaut,
    # training sur décision d'un éditeur ou du déposant. N'entre dans aucun
    # calcul du moteur.
    nature: Mapped[str] = mapped_column(
        SessionNature, nullable=False, default="mission", server_default="mission"
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
    # Lot Fraîcheur v0.9939, migration 0021 (brief §4) : empreinte du moteur
    # de statistiques (`app/debrief/revision.py::ENGINE_REVISION`) au moment
    # du dernier recalcul de CETTE session. `NULL` = calculée avant que
    # l'empreinte n'existe -- donc périmée, comme toute session déjà en base
    # au premier démarrage après ce lot. Le prédicat de péremption
    # (`stats_engine_rev != ENGINE_REVISION`, NULL compris) vit uniquement
    # dans `revision.is_stale()` -- jamais réécrit ici ni ailleurs.
    stats_engine_rev: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Lot « Les heures de jour et de nuit » (v1.0068, migration 0040) : l'heure
    # du jour de la mission à `t = 0`, en secondes depuis minuit (`ta - t` de
    # l'évènement `mission start`) ; `NULL` tant qu'aucun journal ne la porte.
    horloge_mission_s: Mapped[float | None] = mapped_column(Float, nullable=True)


class DebriefUpload(Base):
    """Un fichier brut déposé (ACMI ou debrief.log). `sha256` unique = clé
    anti-doublon stricte (spec §7.1) : un re-dépôt du même fichier est un
    no-op applicatif, jamais une nouvelle ligne."""

    __tablename__ = "debrief_upload"
    __table_args__ = (
        Index("ix_debrief_upload_session_id", "session_id"),
        # Lot « Le rattachement des dépôts » (migration 0039) : les trois
        # provenances d'un fichier.
        CheckConstraint(
            "rattachement IN ('titre','contenu','manuel')",
            name="ck_debrief_upload_rattachement",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debrief_session.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # 'acmi' | 'debrief'
    # Nullable pour 'acmi' (déposé par n'importe qui, identité non requise) ;
    # NOT NULL applicatif pour 'debrief' (identité déclarée obligatoire à
    # l'upload — enforcé dans app/debrief/api.py, pas en contrainte SQL pour
    # ne pas dupliquer une colonne polymorphe en deux tables).
    depositor_profile_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    raw_stored_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Lot « Le rattachement des dépôts » (v1.0052, migration 0039, R326) : la
    # provenance du fichier, lue à l'écran Session. `rattachement` : comment il
    # a rejoint sa session -- `titre` (l'en-tête, `_resolve_session`),
    # `contenu` (ses faits, `app/debrief/rattachement.py`) ou `manuel`
    # (déplacé, ou venu d'une fusion). `entete_titre` : le titre tiré de
    # l'en-tête au dépôt. `entete_exemple` : l'en-tête désigne une mission
    # d'exemple de DCS. `deplace_par_profile_id` : qui l'a déplacé à la main.
    rattachement: Mapped[str] = mapped_column(
        Text, nullable=False, default="titre", server_default="titre"
    )
    entete_titre: Mapped[str | None] = mapped_column(Text, nullable=True)
    entete_exemple: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    deplace_par_profile_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )


class DebriefFlight(Base):
    """Un vol = une vie = un `object_id` (debrief) et/ou une vie ACMI
    (`acmi_track_id`). Granularité = la vie (décision du porteur, spec §1.2) —
    jamais découpée en sorties takeoff→land (hors périmètre v1, spec §9)."""

    __tablename__ = "debrief_flight"
    __table_args__ = (
        Index("ix_debrief_flight_session_id", "session_id"),
        Index("ix_debrief_flight_session_object", "session_id", "object_id"),
        # Lot « Les heures de jour et de nuit » (migration 0040) : deux
        # valeurs permises pour chacune des deux périodes.
        CheckConstraint("periode IN ('jour','nuit')", name="ck_debrief_flight_periode"),
        CheckConstraint(
            "periode_corrigee IN ('jour','nuit')", name="ck_debrief_flight_periode_corrigee"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debrief_session.id"), nullable=False
    )
    # Deux espaces d'id disjoints (spec §2.2/§4.5) : ne JAMAIS comparer par
    # égalité. object_id = pivot debrief ; acmi_track_id = espace ACMI,
    # relié uniquement via nom + fenêtres temporelles (§4.5).
    object_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    acmi_track_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    aircraft_type: Mapped[str] = mapped_column(Text, nullable=False)
    coalition: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Lot « rr-socle-proprete » (migration 0046) : indexée, la colonne se lit en filtre.
    pilote_profile_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True, index=True
    )
    pilot_callsign: Mapped[str | None] = mapped_column(Text, nullable=True)
    identity_state: Mapped[str] = mapped_column(Text, nullable=False, default="anonyme")
    identity_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    t_start: Mapped[float | None] = mapped_column(Float, nullable=True)
    t_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    slot_mission: Mapped[str | None] = mapped_column(Text, nullable=True)
    mission_id_dcs: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Cache dérivé (spec §6) : takeoffs, landings, shots, hits, kills, temps
    # de vol, alt_max, précision, journal des menaces… Recalculé à chaque
    # upload par le moteur de fusion, jamais édité à la main (hors override
    # d'identité via POST .../identify, qui ne touche pas ce champ).
    stats: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Lot « Les heures de jour et de nuit » (v1.0068, migration 0040) :
    # `periode` est celle que calcule le moteur (`'jour'` ou `'nuit'`, à
    # l'heure de la mission du décollage) ; `periode_corrigee` est la
    # correction à la main, que le moteur ne lit ni n'écrit jamais.
    periode: Mapped[str | None] = mapped_column(Text, nullable=True)
    periode_corrigee: Mapped[str | None] = mapped_column(Text, nullable=True)


class DebriefEvent(Base):
    """Union dédupliquée des events de tous les debriefs de la session (spec
    §5). Clé de dédup inter-fichiers = `(type, initiator_object_id,
    target_object_id, weapon, t±0.5s)` — appliquée dans le moteur, PAS en
    contrainte SQL (fenêtre temporelle, pas une égalité stricte)."""

    __tablename__ = "debrief_event"
    __table_args__ = (
        Index("ix_debrief_event_session_initiator", "session_id", "initiator_object_id"),
        Index("ix_debrief_event_session_target", "session_id", "target_object_id"),
        Index("ix_debrief_event_session_type", "session_id", "type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debrief_session.id"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    t: Mapped[float] = mapped_column(Float, nullable=False)
    initiator_object_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_object_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiator_unit_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_unit_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    weapon: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Traçabilité multi-fichiers (spec §5) : liste des upload_id ayant vu cet
    # event fusionné, et chaînage intra-fichier event_id/linked_event_id
    # (JAMAIS utilisés en clé inter-fichiers — locaux à chaque debrief.log).
    seen_in: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    event_id_by_upload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    linked_event_id_by_upload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict
    )


class DebriefGraveyard(Base):
    """Épaves/destructions de la session (bloc `graveyard` des debrief.log),
    union dédupliquée sur (type, x, y) arrondi au mètre (spec §5). Sans
    tueur — l'attribution passe exclusivement par DebriefEvent.kill."""

    __tablename__ = "debrief_graveyard"
    __table_args__ = (Index("ix_debrief_graveyard_session_id", "session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debrief_session.id"), nullable=False
    )
    unit_type: Mapped[str] = mapped_column(Text, nullable=False)
    coalition: Mapped[str | None] = mapped_column(Text, nullable=True)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    alt: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    seen_in: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class ProfileDcsAlias(Base):
    """Un nom retenu : rattache un SEGMENT de callsign ACMI
    (`_extract_name_segment()`, `app/debrief/engine.py`) à un profil, de
    façon durable (Lot « Le nom qu'on retient » v0.9917, migration 0020,
    brief §3). Alimentée par `POST .../flights/{id}/identify` quand un
    admin désigne un membre (`_record_alias()`, `app/debrief/api.py`) ;
    consultée par `_attach_profiles_by_name()` en premier, avant la règle
    de segment existante (brief §4, Geste ②).

    `alias_segment` UNIQUE, normalisé en minuscules À L'ÉCRITURE (jamais
    par un index fonctionnel ici -- contrairement à `campaign.name`,
    migration 0012, la valeur d'origine n'a pas besoin d'être préservée
    pour l'affichage) : l'unicité est en base, pas dans le code -- deux
    membres ne peuvent jamais retenir le même nom (brief §7 P2)."""

    __tablename__ = "profile_dcs_alias"
    __table_args__ = (
        Index("ix_profile_dcs_alias_profile_id", "profile_id"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    profile_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    alias_segment: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DebriefUnitCategory(Base):
    """Table de complétion locale des types DCS absents du référentiel
    `object_db_v2_index.json` (spec §6.5). Alimentée automatiquement à
    l'ingestion, jamais bloquante — un type inconnu ne stoppe rien."""

    __tablename__ = "debrief_unit_category"

    unit_type: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False, default="Inconnu")
    resolved_from: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    # Lot « Les référentiels : types et armes » : cette table porte aussi le
    # référentiel des types. Le moteur n'écrit que les quatre colonnes
    # ci-dessus ; ces deux-là ne sont posées que par l'écran Référentiels du
    # Centre. `libelle` : le nom affiché à la place de la clé DCS (NULL = la
    # clé brute). `categorie_forcee` : NULL = automatique (`categorize`), sinon
    # une valeur de `referentiel.CATEGORIES`.
    libelle: Mapped[str | None] = mapped_column(Text, nullable=True)
    categorie_forcee: Mapped[str | None] = mapped_column(Text, nullable=True)


class ReferentielArme(Base):
    """Lot « Les référentiels : types et armes » : le libellé d'un nom d'arme
    DCS. Pas de table des armes « vues » (elles se lisent dans
    `debrief_event.weapon`) : on ne stocke que la clé et son libellé. Un
    libellé NULL est une ligne sans effet -- la clé s'affiche telle quelle."""

    __tablename__ = "referentiel_arme"

    cle: Mapped[str] = mapped_column(Text, primary_key=True)
    libelle: Mapped[str | None] = mapped_column(Text, nullable=True)


class DebriefReport(Base):
    """Rapport de mission rédigé par le modèle de langage (Lot R2 -- « la
    porte, la rédaction, le rendu », brief §4 / cadrage R78-R81). UN
    rapport par session, remplacé à la réécriture -- R81, aucun historique,
    aucune table de plus. `session_id` sert directement de clé primaire :
    l'unicité EST la contrainte (un `id` séparé aurait permis, par erreur
    d'implémentation future, plusieurs lignes pour la même session).

    `texte_fr` / `texte_en` peuvent être NULL indépendamment tant qu'ils
    n'ont jamais été rédigés avec succès (jamais de texte de secours -- la
    porte rend `None` en cas d'échec, jamais une chaîne vide, brief §3).

    `report_facts_sha` -- même idiome que `ENGINE_REVISION`
    (app/debrief/revision.py) : capturé AU MOMENT de la rédaction, il
    diverge dès que la fiche de faits change (cadrage §6, quatre causes) --
    le rapport reste affiché, tamponné « À CORRIGER » (R80), jamais
    recalculé de force ni effacé. Le prédicat de divergence n'est PAS
    stocké : recalculé à la lecture (GET), comme `revision.is_stale`."""

    __tablename__ = "debrief_report"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debrief_session.id"), primary_key=True
    )
    texte_fr: Mapped[str | None] = mapped_column(Text, nullable=True)
    texte_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_facts_sha: Mapped[str] = mapped_column(Text, nullable=False)
    redige_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    # Profil Discord de celui qui a cliqué Rédiger/Réécrire (`user["id"]`,
    # même identité que `Profile.id` -- brief §4 : "l'auteur du geste").
    # Nullable : ne doit jamais bloquer l'écriture du rapport si l'appelant
    # ne peut pas être résolu en profil pour une raison quelconque.
    auteur_profile_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )


class LlmCallLog(Base):
    """Journal d'appel de la porte unique (`app/llm.py::rediger`) -- Lot
    R2, brief §3. UNE ligne par appel TENTÉ, y compris les échecs et les
    refus de plafond (mensuel comme par session) : c'est l'instrument qui
    dira, dans six mois, si les plafonds sont bien réglés. Jamais réécrite,
    jamais purgée par ce lot -- la rétention est une décision
    d'exploitation, hors périmètre ici.

    Les DEUX plafonds (mensuel, par session) se COMPTENT en interrogeant
    cette table -- jamais un compteur en mémoire de processus (brief §3) :
    un redémarrage du service ne doit remettre aucun compteur à zéro.
    `session_id` nullable par prudence (ne jamais faire échouer une
    écriture de log sur une contrainte), mais renseigné dans tous les cas
    réels (porté par `fiche["mission_id"]`, brief §3 -- la fiche est
    auto-suffisante, R88)."""

    __tablename__ = "llm_call_log"
    __table_args__ = (
        Index("ix_llm_call_log_session_id", "session_id"),
        Index("ix_llm_call_log_called_at", "called_at"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debrief_session.id"), nullable=True
    )
    called_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    langue: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 'ok' | 'echec_transport' | 'echec_delai_depasse' |
    # 'echec_http_indisponible' | 'echec_http_refuse' |
    # 'echec_http_sans_texte' | 'echec_recit_tronque' |
    # 'refus_plafond_mensuel' | 'refus_plafond_session' | 'porte_fermee'
    # -- cf. app/llm.py. Correctif R2e §3 : l'ancien 'echec_http' unique
    # recouvrait les trois causes _indisponible/_refuse/_sans_texte.
    # Lot R3 §2③ : 'echec_recit_tronque' ajouté (récit coupé par
    # `stop_reason: "max_tokens"`).
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    # Correctif R2e §3 : observation, jamais une clé/un en-tête/un
    # fragment de requête. `http_status` dès qu'une réponse est reçue ;
    # `stop_reason` dès que le corps de cette réponse a pu être lu.
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Lot FR source unique §2⑥ (migration 0025, cadrage R125) -- distingue
    # une rédaction d'une traduction : 'redaction' | 'traduction',
    # NULLABLE. Les lignes antérieures à ce lot (40 au 10 septembre 2026)
    # restent sans valeur -- honnête : on ne sait pas rétroactivement ce
    # qu'elles étaient. Sans cette colonne, une traduction à ~1500 jetons
    # et une rédaction à ~15000 portaient la même étiquette `langue='en'`,
    # et toute moyenne tirée de ce journal aurait été fausse.
    etape: Mapped[str | None] = mapped_column(Text, nullable=True)


class DebriefReportRun(Base):
    """Rédaction en vol (Lot R6 -- « la rédaction en tâche de fond »).

    Une ligne = une rédaction en vol. `session_id` sert directement de clé
    primaire, même idiome que `DebriefReport` ci-dessus : l'unicité EST la
    contrainte, ce qui rend l'atomicité de la pose gratuite -- deux
    rédactions simultanées sur une même session deviennent impossibles par
    contrainte, pas par vigilance.

    La ligne est supprimée à la fin de la tâche de fond quel que soit le
    résultat (succès ou échec) ; la péremption (`REDACTION_PEREMPTION_MIN`,
    app/debrief/api.py) n'est qu'un filet pour le cas où le processus meurt
    avant d'atteindre ce nettoyage.
    """

    __tablename__ = "debrief_report_run"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("debrief_session.id"), primary_key=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Même prudence que LlmCallLog.session_id : ne jamais faire échouer une
    # écriture d'état sur une contrainte.
    lance_par_profile_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("profiles.id"), nullable=True
    )
