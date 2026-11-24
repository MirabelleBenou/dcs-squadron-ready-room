# B · Les fichiers, les volumes et les ports { #files-volumes-ports }

Où la Ready Room range ce qu'elle garde, et par où on la joint. Un test de la Ready Room compare les tables de cette
annexe à `docker-compose.yml` et `compose.caddy.yml` : un volume, un montage ou un port ajouté sans sa ligne ici fait
échouer la release.

## B.1 · Le dossier de la Ready Room { #folder-contents }

Dans `/opt/readyroom` ([§4.1](04-get-the-ready-room.md#folder)), à côté du code de la release :

| fichier ou dossier | contenu | irremplaçable ? |
|---|---|---|
| `.env` | la configuration et ses secrets, dont `CONFIG_KEY` ([annexe A](a-environment.md)) | **oui** : sans `CONFIG_KEY`, les secrets de **Configuration** sont à ressaisir |
| `backups/` | les sauvegardes ([§11.1](11-backup-and-restore.md#what-a-backup-holds)) | **oui**, tant qu'elles ne sont pas copiées ailleurs |
| `data/` | les dossiers de l'hôte par défaut : suites, tuiles, tuiles gardées | non : ils se retrouvent à leur source ([§4.3](04-get-the-ready-room.md#suites)) |

## B.2 · Les volumes Docker { #volumes }

| volume | contenu | irremplaçable ? | sauvegardé par |
|---|---|---|---|
| `readyroom_pgdata` | la base : membres, escadrilles, planning, rapports, réglages | **oui** | les sauvegardes de la Ready Room (`.dump`) |
| `readyroom_crests` | les écussons des escadrilles et l'emblème de l'escadre | **oui** | les sauvegardes de la Ready Room (`_ecussons.tar.gz`) |
| `readyroom_debrief_raw` | les dépôts bruts du module Escadre et les fichiers de l'agent | **oui** : rien ne garantit qu'ils existent ailleurs | l'archive du [§11.2](11-backup-and-restore.md#raw-deposits) |
| `readyroom_caddy_data` | option A : les certificats de Caddy | non : Caddy les redemande | — |
| `readyroom_caddy_config` | option A : la configuration de Caddy | non : Caddy la réécrit | — |

## B.3 · Les montages { #mounts }

Les dossiers de l'hôte que voit le conteneur `app` :

| dans le conteneur | sur l'hôte | accès | contenu |
|---|---|---|---|
| `/backups` | `./backups` | lecture et écriture | les sauvegardes |
| `/data/suites` | `SUITES_HOST_DIR` (défaut `./data/suites`) | lecture seule | Mission Plan et Mission Tools |
| `/data/tiles` | `TILES_HOST_DIR` (défaut `./data/tiles`) | lecture seule | facultatif : des tuiles de la carte DCS que vous avez déjà, servies d'abord |
| `/data/tiles-cache` | `TILES_CACHE_HOST_DIR` (défaut `./data/tiles-cache`) | lecture et écriture | les tuiles gardées par la Ready Room |

## B.4 · Les ports { #ports }

| port | service | ouvert à | à quoi il sert |
|---|---|---|---|
| `127.0.0.1:8000` | `app` | ce serveur seulement | l'application, que joint le proxy HTTPS |
| `80` | `caddy` (option A) | Internet | le certificat Let's Encrypt, et la redirection vers HTTPS |
| `443` | `caddy` (option A) | Internet | la Ready Room en HTTPS |
| `443/udp` | `caddy` (option A) | Internet | HTTPS par HTTP/3 |

La base (`db`) n'a aucun port ouvert hors de Docker. Avec l'option B, aucun port n'est ouvert : Tailscale Funnel joint
`127.0.0.1:8000` de lui-même.

## B.5 · Ce qu'il faut garder ailleurs { #keep-elsewhere }

Quatre choses ne se retrouvent nulle part si le serveur disparaît : **la base**, **les écussons**, **les dépôts bruts**
et **`.env`**. Les deux premières sont dans chaque sauvegarde ; les dépôts bruts s'archivent à part
([§11.2](11-backup-and-restore.md#raw-deposits)) ; `.env` se copie à part. Le
[§11.3](11-backup-and-restore.md#off-server-copy) dit comment.
