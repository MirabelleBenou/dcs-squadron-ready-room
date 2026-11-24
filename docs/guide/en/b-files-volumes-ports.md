# B · Files, volumes and ports { #files-volumes-ports }

Where the Ready Room stores what it keeps, and how it is reached. A Ready Room test compares the tables of this
appendix with `docker-compose.yml` and `compose.caddy.yml`: a volume, mount or port added without its line here makes
the release fail.

## B.1 · The Ready Room's folder { #folder-contents }

In `/opt/readyroom` ([§4.1](04-get-the-ready-room.md#folder)), next to the release's code:

| file or folder | contents | irreplaceable? |
|---|---|---|
| `.env` | the configuration and its secrets, `CONFIG_KEY` included ([appendix A](a-environment.md)) | **yes**: without `CONFIG_KEY`, the secrets in **Configuration** must be entered again |
| `backups/` | the backups ([§11.1](11-backup-and-restore.md#what-a-backup-holds)) | **yes**, as long as they are not copied elsewhere |
| `data/` | the default host folders: suites, tiles, kept tiles | no: they can be fetched again from their source ([§4.3](04-get-the-ready-room.md#suites)) |

## B.2 · Docker volumes { #volumes }

| volume | contents | irreplaceable? | backed up by |
|---|---|---|---|
| `readyroom_pgdata` | the database: members, squadrons, schedule, reports, settings | **yes** | the Ready Room's backups (`.dump`) |
| `readyroom_crests` | the squadrons' crests and the wing's emblem | **yes** | the Ready Room's backups (`_ecussons.tar.gz`) |
| `readyroom_debrief_raw` | the raw uploads of the Wing module and the agent's files | **yes**: nothing guarantees they exist elsewhere | the archive of [§11.2](11-backup-and-restore.md#raw-deposits) |
| `readyroom_caddy_data` | option A: Caddy's certificates | no: Caddy requests them again | — |
| `readyroom_caddy_config` | option A: Caddy's configuration | no: Caddy rewrites it | — |

## B.3 · Mounts { #mounts }

The host folders that the `app` container sees:

| in the container | on the host | access | contents |
|---|---|---|---|
| `/backups` | `./backups` | read and write | the backups |
| `/data/suites` | `SUITES_HOST_DIR` (default `./data/suites`) | read-only | Mission Plan and Mission Tools |
| `/data/tiles` | `TILES_HOST_DIR` (default `./data/tiles`) | read-only | optional: DCS map tiles you already have, served first |
| `/data/tiles-cache` | `TILES_CACHE_HOST_DIR` (default `./data/tiles-cache`) | read and write | the tiles kept by the Ready Room |

## B.4 · Ports { #ports }

| port | service | open to | what it is for |
|---|---|---|---|
| `127.0.0.1:8000` | `app` | this server only | the application, reached by the HTTPS proxy |
| `80` | `caddy` (option A) | the Internet | the Let's Encrypt certificate, and the redirect to HTTPS |
| `443` | `caddy` (option A) | the Internet | the Ready Room over HTTPS |
| `443/udp` | `caddy` (option A) | the Internet | HTTPS over HTTP/3 |

The database (`db`) has no port open outside Docker. With option B, no port is open: Tailscale Funnel reaches
`127.0.0.1:8000` by itself.

## B.5 · What to keep elsewhere { #keep-elsewhere }

Four things cannot be found anywhere else if the server disappears: **the database**, **the crests**, **the raw
uploads** and **`.env`**. The first two are in every backup; the raw uploads are archived separately
([§11.2](11-backup-and-restore.md#raw-deposits)); `.env` is copied separately.
[§11.3](11-backup-and-restore.md#off-server-copy) says how.
