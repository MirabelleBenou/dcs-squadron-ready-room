# A · Les variables et les réglages { #environment }

La référence complète de ce que lit l'installation. Un test de la Ready Room compare ces tables au code : une variable
ou un réglage ajouté sans sa ligne ici fait échouer la release.

## A.1 · Le fichier `.env` : lu par l'application { #app-variables }

Lues au **démarrage** du conteneur `app`. Après une modification : `docker compose up -d --force-recreate app`.

| variable | obligatoire | rôle | exemple |
|---|---|---|---|
| `BASE_URL` | oui | l'adresse publique HTTPS, sans `/` final ; la seule source de l'adresse de retour de Discord | `https://readyroom.example.org` |
| `DISCORD_CLIENT_ID` | oui | l'*Application ID* de l'application Discord | `123456789012345678` |
| `DISCORD_CLIENT_SECRET` | oui | son *Client Secret* | — |
| `DISCORD_GUILD_ID` | oui | l'identifiant du serveur Discord de l'escadre | `123456789012345678` |
| `ADMIN_IDS` | oui | les administrateurs fondateurs : identifiants Discord séparés par des virgules, au moins un | `123456789012345678,234567890123456789` |
| `SESSION_SECRET` | oui | le secret qui signe les sessions ; 32 caractères au moins, jamais la valeur d'exemple | `openssl rand -base64 48` |
| `CONFIG_KEY` | oui | la clé (Fernet) qui chiffre les secrets des réglages ; à garder hors des sauvegardes | 44 caractères ; la commande au [§5.2](05-configure.md#required-variables) |
| `POSTGRES_USER` | oui¹ | l'utilisateur de la base | `readyroom` |
| `POSTGRES_PASSWORD` | oui¹ | son mot de passe | `openssl rand -hex 24` |
| `POSTGRES_DB` | oui¹ | le nom de la base | `readyroom` |
| `DATABASE_URL` | non | l'adresse complète de la base, si vous ne voulez pas qu'elle soit composée des trois précédentes | `postgresql+asyncpg://readyroom:<mot de passe>@db:5432/readyroom` |

¹ Sauf si `DATABASE_URL` est posée ; même alors, `db` a besoin des trois pour créer la base.

L'application **ignore** toute autre variable du `.env`. Celles des versions antérieures qui ne se lisent plus sont
nommées au journal au démarrage (« Variables retirées du .env, sans effet »), jamais leur valeur : on peut les ôter.

## A.2 · Le fichier `.env` : lu par Docker Compose { #compose-variables }

Lues par `docker compose`, jamais par l'application ; facultatives.

| variable | défaut | rôle |
|---|---|---|
| `COMPOSE_FILE` | `docker-compose.yml` | `docker-compose.yml:compose.caddy.yml` démarre aussi le proxy Caddy (option A, [§6.2](06-https.md#option-a)) |
| `SUITES_HOST_DIR` | `./data/suites` | le dossier de Mission Plan et Mission Tools, lu seulement |
| `TILES_HOST_DIR` | `./data/tiles` | les tuiles extraites des archives d'Olympus, lues seulement |
| `TILES_CACHE_HOST_DIR` | `./data/tiles-cache` | les tuiles venues d'Olympus, écrites par la Ready Room |

## A.3 · Les réglages, dans la Ready Room { #settings }

À l'écran **Centre de Commandement › Configuration › Paramètres du serveur**, par un administrateur ; ils
s'appliquent **sans redémarrer**. Vider un réglage lui rend son défaut. Un secret n'est jamais réaffiché : l'écran dit
seulement **Renseigné**, **Vide** ou **Remplacé**.

| réglage (nom technique) | à l'écran | groupe | défaut | secret |
|---|---|---|---|---|
| `ANTHROPIC_API_KEY` | Clé de l'API Anthropic | Le Récit du Rapport de mission | vide | oui |
| `ANTHROPIC_MODEL` | Modèle de rédaction | Le Récit du Rapport de mission | vide | |
| `ANTHROPIC_EFFORT` | Effort de rédaction | Le Récit du Rapport de mission | Moyen | |
| `DISCORD_WEBHOOK_URL` | Adresse du webhook du digest | Discord — le digest | aucun | oui |
| `DISCORD_DIGEST_LOCALE` | Langue du digest | Discord — le digest | Anglais | |
| `DISCORD_DIGEST_TOKEN` | Jeton des mises à jour manuelles | Discord — le digest | vide | oui |
| `DISCORD_RSVP_ENABLED` | Réponses dans Discord | Discord — les réponses | Désactivé | |
| `DISCORD_BOT_TOKEN` | Jeton du bot | Discord — les réponses | aucun | oui |
| `DISCORD_PUBLIC_KEY` | Clé publique de l'application | Discord — les réponses | aucun | |
| `DISCORD_NOTIFY_CHANNEL_ID` | Salon des réponses | Discord — les réponses | aucun | |
| `DISCORD_RSVP_HORIZON_DAYS` | Horizon des réponses (jours) | Discord — les réponses | 14 | |
| `REFERENCE_TZ` | Fuseau de l'escadre | Fuseau horaire | `Europe/Paris` | |
| `TILES_UPSTREAM` | Serveur de tuiles | Les tuiles de la carte | `https://maps.dcsolympus.com/maps` | |
| `WING_ID` | Clé de l'escadre | Les suites (Mission Plan) | vide : tirée de la désignation de l'escadre | |

!!! warning "Attention"
    Les secrets sont chiffrés par `CONFIG_KEY` ([§5.4](05-configure.md#config-key)) : sans elle, ils ne peuvent être ni
    lus ni enregistrés. Le **Fuseau de l'escadre** se règle à l'installation : le changer ensuite ne recalcule rien de
    ce qui est déjà enregistré. Changer la **Clé de l'escadre** fait perdre aux membres les réglages d'escadre que Mission Plan
    garde dans leur navigateur.
