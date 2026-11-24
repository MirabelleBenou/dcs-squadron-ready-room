"""Configuration centrale, chargée depuis les variables d'environnement (.env).

Lot « rr-env-epure » : l'environnement et le `.env` ne portent plus que ce qu'exige le
premier démarrage (`_AMORCAGE`) ; les quatorze réglages gardés en base sont lus par
`app/reglages.py` (`charger_au_demarrage`), tout le reste est une valeur fixe."""
import logging
from functools import lru_cache
from typing import Annotated
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

logger = logging.getLogger(__name__)

# Lot « rr-env-epure » : les seules variables lues dans l'environnement et le `.env`.
_AMORCAGE = frozenset(
    {
        "BASE_URL",
        "DISCORD_CLIENT_ID",
        "DISCORD_CLIENT_SECRET",
        "DISCORD_GUILD_ID",
        "SESSION_SECRET",
        "ADMIN_IDS",
        "CONFIG_KEY",
        "DATABASE_URL",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
    }
)


class _SourceFiltree(PydanticBaseSettingsSource):
    """Lot « rr-env-epure » : enveloppe une source de `pydantic-settings` (environnement
    ou `.env`) et ne rend que les clés de `_AMORCAGE`."""

    def __init__(self, settings_cls, source):
        super().__init__(settings_cls)
        self._source = source

    def get_field_value(self, field, field_name):
        return self._source.get_field_value(field, field_name)

    def __call__(self):
        return {k: v for k, v in self._source().items() if k in _AMORCAGE}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Lot « rr-env-epure » : l'initialisation, puis l'environnement et le `.env`
        réduits à `_AMORCAGE`."""
        return (
            init_settings,
            _SourceFiltree(settings_cls, env_settings),
            _SourceFiltree(settings_cls, dotenv_settings),
        )

    # URL publique de l'app (Tailscale Funnel). Source UNIQUE de vérité pour
    # construire le redirect_uri OAuth — jamais depuis request.url.
    BASE_URL: str

    # Application Discord (OAuth2 sans bot)
    DISCORD_CLIENT_ID: str
    DISCORD_CLIENT_SECRET: str
    DISCORD_GUILD_ID: str
    # v0.35 -- tag wing à retirer des noms affichés (callsign), variantes
    # gérées par le matcher partagé (cf. name_strip_tokens ci-dessous).
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    WING_TAG: str = "Ready Room"

    # Session
    SESSION_SECRET: str
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    SESSION_TTL_DAYS: int = 30

    # Fuseau de référence de l'escadron
    # Réglage en base (lot « rr-fuseau-reglage ») : `app/recurrence.fuseau_reference()` le lit à chaque usage.
    REFERENCE_TZ: str = "Europe/Paris"

    # Lot R2 -- Rapport de mission (app/llm.py, la porte unique vers un
    # modèle de langage). OPTIONNELLES par construction (défaut chaîne
    # vide, jamais requises) : la Ready Room démarre et fonctionne
    # normalement sans elles, seule la rédaction du Récit se refuse
    # (verdict "porte_fermee", cf. app/llm.py). Ne JAMAIS les déclarer
    # requises -- cf. l'annexe A du guide (docs/guide/en/a-environment.md) pour le détail.
    # Plus lues du `.env` (rr-env-epure) : en base.
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = ""
    ANTHROPIC_EFFORT: str = "medium"

    # Base de données. Lot « rr-env-epure » : `DATABASE_URL` est facultative ; vide, le
    # validateur ci-dessous la compose des `POSTGRES_*`.
    DATABASE_URL: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    # Lot « rr-env-epure » : la clé (Fernet) qui chiffre les secrets des réglages gardés
    # en base. Vide ou invalide : l'entrée du conteneur refuse de démarrer
    # (`python -B -m app.reglages`).
    CONFIG_KEY: str = ""
    # Lot « rr-env-epure » : les administrateurs nommés dans l'application (lignes
    # `account_capability` de capacité `admin`), posés par `charger_au_demarrage` et par
    # les routes de `app/command/api.py` ; jamais lus de l'environnement.
    ADMINS_NOMMES: Annotated[frozenset[str], NoDecode] = frozenset()

    # Lot 7 — Notifications Discord sortantes (webhook classique, cf.
    # BRIEF_SONNET_ReadyRoom_Lot7_Notifications_Discord). Aucune de ces
    # variables ne bloque le démarrage si absente : `post_digest()` se
    # contente de logger et de ne rien poster (cf. VIGILANCE brief).
    # Plus lues du `.env` (rr-env-epure) : en base.
    DISCORD_WEBHOOK_URL: str | None = None
    DISCORD_DIGEST_TOKEN: str = ""
    DISCORD_DIGEST_LOCALE: str = "en"

    # Extension 2a.1 -- digest évergreen (édition en direct + remplacement
    # automatique de l'ancien message), cf. BRIEF_SONNET_ReadyRoom_v0.22 §2.
    # Aucune de ces variables ne bloque le démarrage si absente.
    # Plus lues du `.env` (rr-env-epure) : valeurs fixes.
    DISCORD_DIGEST_REFRESH_ENABLED: bool = True
    DISCORD_DIGEST_REFRESH_DEBOUNCE_SECONDS: int = 10
    DISCORD_DIGEST_CLEANUP_IDS: str = ""

    # Comptes admin : CSV d'IDs de comptes Discord autorisés à éditer/
    # supprimer N'IMPORTE QUEL événement (en plus du créateur). Vide par
    # défaut -> aucun admin. Ne bloque jamais le démarrage.
    # Lot « rr-env-epure » : ce sont les administrateurs FONDATEURS, toujours administrateurs ;
    # l'entrée du conteneur en exige au moins un (`app/reglages.py`). Les autres se nomment
    # dans l'application (`ADMINS_NOMMES`).
    ADMIN_IDS: str = ""

    # Lot 2b-1 -- Phase 2b (RSVP interactif Discord, socle bot REST +
    # interactions signées), cf. BRIEF_SONNET_ReadyRoom_Lot2b-1 §2. Aucune
    # de ces variables ne bloque le démarrage si absente : tant que
    # `DISCORD_RSVP_ENABLED` est `False` (défaut), le bot 2b reste dormant
    # et le digest webhook 2a n'est pas affecté.
    # Plus lues du `.env` (rr-env-epure) : en base.
    DISCORD_RSVP_ENABLED: bool = False
    DISCORD_BOT_TOKEN: str | None = None
    DISCORD_PUBLIC_KEY: str | None = None
    DISCORD_NOTIFY_CHANNEL_ID: str | None = None
    DISCORD_RSVP_HORIZON_DAYS: int = 14

    # v0.80 -- horizon d'application d'un RSVP `scope=series` (jours, à
    # partir de max(occ_date, today)). Borné par MAX_WINDOW_DAYS = 120 du
    # moteur de récurrence : ne jamais dépasser 120.
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    PRESENCE_SERIES_HORIZON_DAYS: int = 90

    # Lot D1 -- module Debriefing : répertoire de conservation des fichiers
    # bruts (ACMI + debrief.log) déposés, cf. BRIEF_SONNET_ReadyRoom_Debrief_
    # D1_data_engine §5. Monté sur un volume Docker nommé dédié (cf.
    # docker-compose.yml) pour survivre aux redéploiements -- le brut permet
    # le re-parse de l'historique après évolution du moteur. À répercuter
    # dans l'annexe A du guide : docs/guide/en/a-environment.md.
    # Signalé dans le rapport de livraison, cf. brief.
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    DEBRIEF_STORAGE_DIR: str = "/data/debrief_raw"

    # Lot 3.2e, volet ② -- module Centre de Commandement : répertoire de
    # conservation des écussons d'escadrille normalisés (PNG, cf.
    # app/crests.py), un fichier par escadrille (`{squadron_id}.png`).
    # Monté sur un volume Docker nommé DÉDIÉ (cf. docker-compose.yml),
    # distinct de DEBRIEF_STORAGE_DIR : les écussons sont irremplaçables
    # (contrairement aux dépôts bruts du Débrief, rejouables), les mêmes
    # règles de sauvegarde ne s'y appliquent pas (addendum CC v1.2 §10.4).
    # À répercuter dans l'annexe A du guide : docs/guide/en/a-environment.md.
    # Signalé dans le rapport de livraison, cf. brief.
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    CREST_STORAGE_DIR: str = "/data/crests"

    # Lot « L'écran Archives du Centre » : répertoire des sauvegardes. C'est le
    # montage `./backups` de docker-compose.yml, où `entrypoint.sh` écrit en
    # dur (`/backups`) ; en production, il ne change pas. L'écran Archives y
    # liste les sauvegardes du déploiement et y écrit les manuelles
    # (app/sauvegardes.py). Ligne à l'annexe A du guide (docs/guide/en/a-environment.md).
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    BACKUP_DIR: str = "/backups"
    # Lot « Les suites servies par la Ready Room » : dossier des suites
    # Mission Plan et Mission Tools (`dcs_mission_plan.html`,
    # `dcs_mission_tools.html`), servies par `app/main.py` derrière la règle
    # d'accès de l'application. Montage lié en lecture seule, rempli par
    # le porteur sur l'hôte (`SUITES_HOST_DIR`, `docker-compose.yml`). Aucun contrôle au
    # démarrage : un dossier absent ne bloque rien.
    # Ligne à l'annexe A du guide : docs/guide/en/a-environment.md.
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    SUITES_DIR: str = "/data/suites"

    # Lot « Le miroir des tuiles DCS » : tuiles de la couche « Carte DCS » du
    # Route Planner (archives de DCS Olympus extraites, `<clé>/<z>/<x>/<y>.png`),
    # servies par `app/tuiles_dcs.py` aux seuls membres connectés. Montage lié
    # en lecture seule de `TILES_HOST_DIR` (`docker-compose.yml`). Aucun
    # contrôle au démarrage : un dossier absent ne bloque rien.
    # Ligne à l'annexe A du guide : docs/guide/en/a-environment.md.
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    TILES_DIR: str = "/data/tiles"
    # Lot « Le miroir des tuiles DCS » : tuiles venues d'Olympus et gardées par
    # la route, même arborescence que `TILES_DIR`. Montage lié en écriture de
    # `TILES_CACHE_HOST_DIR` (`docker-compose.yml`). Aucun contrôle au
    # démarrage. Ligne à l'annexe A du guide (docs/guide/en/a-environment.md).
    # Plus lue du `.env` (rr-env-epure) : valeur fixe.
    TILES_CACHE_DIR: str = "/data/tiles-cache"
    # Lot « Le miroir des tuiles DCS » : serveur d'Olympus interrogé quand une
    # tuile n'est ni dans `TILES_DIR` ni dans `TILES_CACHE_DIR`
    # (`<url>/<clé>/<z>/<x>/<y>.png`). Ligne à l'annexe A du guide (docs/guide/en/a-environment.md).
    # Plus lue du `.env` (rr-env-epure) : en base.
    TILES_UPSTREAM: str = "https://maps.dcsolympus.com/maps"

    # Lot « rr-public-sans-escadre » : la clé de l'escadre des suites (`wing.id` de
    # `/outils/wing-config.json`). En base (rr-public-sans-escadre) : vide = tirée de la désignation.
    WING_ID: str = ""

    @model_validator(mode="after")
    def _composer_database_url(self):
        """Lot « rr-env-epure » : `DATABASE_URL` vide -> composée des `POSTGRES_*` (le
        service `db` du docker-compose), chaque part échappée ; sans l'un des trois,
        refus de démarrer."""
        if not self.DATABASE_URL:
            if not (self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB):
                raise ValueError(
                    "DATABASE_URL, ou POSTGRES_USER, POSTGRES_PASSWORD et POSTGRES_DB, requis"
                )
            self.DATABASE_URL = (
                "postgresql+asyncpg://"
                f"{quote(self.POSTGRES_USER, safe='')}:{quote(self.POSTGRES_PASSWORD, safe='')}"
                f"@db:5432/{quote(self.POSTGRES_DB, safe='')}"
            )
        return self

    @property
    def admin_ids_set(self) -> set[str]:
        """IDs de comptes admin, comparés en str (snowflakes) : les fondateurs
        (`ADMIN_IDS`) unis aux administrateurs nommés dans l'application
        (`ADMINS_NOMMES`, lot « rr-env-epure »)."""
        fondateurs = {i.strip() for i in self.ADMIN_IDS.split(",") if i.strip()}
        return fondateurs | set(self.ADMINS_NOMMES)

    # NB (Lot 2.2b) : `name_strip_tokens` a été RETIRÉE d'ici. Elle lisait
    # WING_TAG + squadron_roles_map + dormant_squadron_names_list, tous
    # trois désormais semés en base (tables `wing`/`squadron`, cf. brief
    # §7) -- une property de `Settings` (sans accès base) ne peut plus
    # produire la liste correcte. Remplacée par `get_name_strip_tokens(db)`
    # dans `app/squadron.py` (même contrat exact : dédup insensible à la
    # casse, tri par longueur décroissante -- porte P4).

    @property
    def session_max_age_seconds(self) -> int:
        return self.SESSION_TTL_DAYS * 24 * 60 * 60

    @property
    def digest_cleanup_ids_list(self) -> list[str]:
        """IDs de messages Discord à purger une fois (backlog déjà accumulé
        avant l'extension), cf. brief §2 -- CSV brut, jamais bloquant."""
        return [i.strip() for i in self.DISCORD_DIGEST_CLEANUP_IDS.split(",") if i.strip()]

    @property
    def rsvp_bot_ready(self) -> bool:
        """Garde-fou Phase 2b (cf. brief Lot 2b-1 §2) : le bot RSVP n'est
        opérationnel que si le flag est activé ET que le token bot ET le
        salon de notification sont renseignés. `DISCORD_PUBLIC_KEY` n'est
        volontairement PAS inclus ici : la vérification de signature (7a)
        se fait indépendamment, avant même de consulter ce garde-fou (une
        interaction mal signée doit toujours renvoyer 401, même si le bot
        n'est pas prêt par ailleurs)."""
        return bool(
            self.DISCORD_RSVP_ENABLED
            and self.DISCORD_BOT_TOKEN
            and self.DISCORD_NOTIFY_CHANNEL_ID
        )

    @property
    def bot_token_present(self) -> bool:
        """Garde token-seule (cf. AMENDEMENT_Lot2b-3_Garde_Suppression §A) --
        distincte de `rsvp_bot_ready` : une SUPPRESSION de message bot ne
        dépend que du token (elle reçoit `channel_id` en argument), pas du
        flag `DISCORD_RSVP_ENABLED` ni du salon de notification. Sert
        uniquement à la garde de `delete_message` (cutover 2b-3, sens
        `false`) -- `post_message`/`edit_message` restent gardées par
        `rsvp_bot_ready` (on ne PROJETTE la surface 2b que si elle est
        active ; on peut la NETTOYER dès que le token est là)."""
        return bool(self.DISCORD_BOT_TOKEN)

    @property
    def digest_locale(self) -> str:
        """Locale effective du digest Discord, validée contre `{fr, en}`
        (repli `en` sur toute valeur inconnue, cf. brief Lot 7 §2)."""
        value = (self.DISCORD_DIGEST_LOCALE or "").strip().lower()
        return value if value in ("fr", "en") else "en"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
