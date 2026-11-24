# A · Variables and settings { #environment }

The complete reference of what the installation reads. A Ready Room test compares these tables with the code: a
variable or setting added without its line here makes the release fail.

## A.1 · The `.env` file: read by the application { #app-variables }

Read when the `app` container **starts**. After a change: `docker compose up -d --force-recreate app`.

| variable | required | role | example |
|---|---|---|---|
| `BASE_URL` | yes | the public HTTPS address, without a trailing `/`; the only source of Discord's redirect address | `https://readyroom.example.org` |
| `DISCORD_CLIENT_ID` | yes | the Discord application's *Application ID* | `123456789012345678` |
| `DISCORD_CLIENT_SECRET` | yes | its *Client Secret* | — |
| `DISCORD_GUILD_ID` | yes | the ID of the wing's Discord server | `123456789012345678` |
| `ADMIN_IDS` | yes | the founding administrators: Discord IDs separated by commas, at least one | `123456789012345678,234567890123456789` |
| `SESSION_SECRET` | yes | the secret that signs sessions; at least 32 characters, never the example value | `openssl rand -base64 48` |
| `CONFIG_KEY` | yes | the (Fernet) key that encrypts the settings' secrets; keep it out of the backups | 44 characters; the command in [§5.2](05-configure.md#required-variables) |
| `POSTGRES_USER` | yes¹ | the database user | `readyroom` |
| `POSTGRES_PASSWORD` | yes¹ | its password | `openssl rand -hex 24` |
| `POSTGRES_DB` | yes¹ | the database name | `readyroom` |
| `DATABASE_URL` | no | the full database address, if you do not want it built from the three above | `postgresql+asyncpg://readyroom:<password>@db:5432/readyroom` |

¹ Unless `DATABASE_URL` is set; even then, `db` needs all three to create the database.

The application **ignores** any other variable in `.env`. Those from earlier versions that are no longer read are
named in the log at start-up (« Variables retirées du .env, sans effet », *removed variables, no effect*), never their
values: you can delete them.

## A.2 · The `.env` file: read by Docker Compose { #compose-variables }

Read by `docker compose`, never by the application; optional.

| variable | default | role |
|---|---|---|
| `COMPOSE_FILE` | `docker-compose.yml` | `docker-compose.yml:compose.caddy.yml` also starts the Caddy proxy (option A, [§6.2](06-https.md#option-a)) |
| `SUITES_HOST_DIR` | `./data/suites` | the Mission Plan and Mission Tools folder, read only |
| `TILES_HOST_DIR` | `./data/tiles` | the tiles extracted from the Olympus archives, read only |
| `TILES_CACHE_HOST_DIR` | `./data/tiles-cache` | the tiles fetched from Olympus, written by the Ready Room |

## A.3 · Settings, inside the Ready Room { #settings }

In **Command Center › Configuration › Server settings**, by an administrator; they apply **without restarting**.
Emptying a setting gives it back its default. A secret is never shown again: the screen only says **Set**, **Empty** or
**Replaced**.

| setting (technical name) | on screen | group | default | secret |
|---|---|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | Mission report narrative | empty | yes |
| `ANTHROPIC_MODEL` | Writing model | Mission report narrative | empty | |
| `ANTHROPIC_EFFORT` | Writing effort | Mission report narrative | medium | |
| `DISCORD_WEBHOOK_URL` | Digest webhook URL | Discord — digest | none | yes |
| `DISCORD_DIGEST_LOCALE` | Digest language | Discord — digest | English | |
| `DISCORD_DIGEST_TOKEN` | Manual update token | Discord — digest | empty | yes |
| `DISCORD_RSVP_ENABLED` | Replies in Discord | Discord — replies | off | |
| `DISCORD_BOT_TOKEN` | Bot token | Discord — replies | none | yes |
| `DISCORD_PUBLIC_KEY` | Application public key | Discord — replies | none | |
| `DISCORD_NOTIFY_CHANNEL_ID` | Replies channel | Discord — replies | none | |
| `DISCORD_RSVP_HORIZON_DAYS` | Replies horizon (days) | Discord — replies | 14 | |
| `REFERENCE_TZ` | Wing time zone | Time zone | `Europe/Paris` | |
| `TILES_UPSTREAM` | Tile server | Map tiles | `https://maps.dcsolympus.com/maps` | |
| `WING_ID` | Wing key | Suites (Mission Plan) | empty: derived from the wing's designation | |

!!! warning "Warning"
    Secrets are encrypted with `CONFIG_KEY` ([§5.4](05-configure.md#config-key)): without it, they can be neither read
    nor saved. Set the **Wing time zone** at installation: changing it later recalculates nothing already saved.
    Changing the **Wing key** makes members lose the wing settings Mission Plan keeps in their browser.
