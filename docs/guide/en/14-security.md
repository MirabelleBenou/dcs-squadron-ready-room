# 14 · Security and data { #security }

This chapter says what the Ready Room exposes, which secrets protect it and how to change them, what it keeps and
what goes to other services.

## 14.1 · What is exposed { #exposed }

- **A single HTTPS address**, the one from chapter 6. The application itself listens only on `127.0.0.1:8000`: it can
  be reached only through the HTTPS proxy on the same server. The database has no open port.
- **The only way in is through Discord**: an account on the wing's Discord server, with a role that opens access
  ([§8.1](08-first-settings.md#app-access)), or a founding administrator. Without a session, only the sign-in page is
  visible.
- **The API's automatic documentation is closed**: nothing describes the API to a visitor.
- **Guests** see read-only, thirty days at most without an extension
  ([§8.6](08-first-settings.md#guests-and-rescue-link)).
- **The backup sign-in link** opens a session once, within 24 hours; the `/readyroom` link, five minutes.
- **The DCS server's agent** gets in only with its token, and can only upload files.

## 14.2 · Secrets and their rotation { #secrets }

| secret | where it lives | to change it | effect |
|---|---|---|---|
| `SESSION_SECRET` | `.env` | new value ([§5.2](05-configure.md#required-variables)), then `docker compose up -d --force-recreate app` | all sessions close: everyone signs in again |
| `CONFIG_KEY` | `.env` | new key ([§5.4](05-configure.md#config-key)), then `docker compose up -d --force-recreate app` | the secrets in **Configuration** become unreadable: enter them again |
| `POSTGRES_PASSWORD` | `.env` | do not change it after the first start | the database keeps the one it was created with: the application could no longer connect to it |
| bot token | **Configuration** | Discord portal, **Bot** page, **Reset Token**, then **Configuration › Bot token** | the new one works at once; the old one is worthless |
| *Client Secret* | `.env` | Discord portal, **OAuth2** page, **Reset Secret**, then `.env` and `docker compose up -d --force-recreate app` | the Discord sign-in resumes with the new one |
| manual update token | **Configuration** | **Configuration**, group **Discord — digest** | your scripts must carry the new one |
| agent token | **Archives › DCS server** | **Replace the token** ([§10.3](10-dcs-agent.md#agent-token)) | the old one stops at once; copy the new one into `readyroom_envoi.json` |

!!! warning "Warning"
    A leaked secret is changed **right away**, in the order of this table. A `.env` published by mistake (a
    repository, a screenshot, a message) has leaked all of them: change them all.

## 14.3 · Data kept { #data-kept }

The Ready Room keeps, in its database:

- **for each member**: their Discord ID, their username and display name, their avatar, their roles as last read,
  their squadron, the dates of their first and last sign-in, their preferences (language, aircraft);
- **their activity**: their answers to the schedule, their flights and missions in the reports;
- **the debriefing files** uploaded by pilots or sent by the agent, which carry the names of the connected players.

A member who loses access leaves the roster at the next roll call: their profile is **archived**, not erased — their
flights and missions stay in the wing's history (**Archives › Archived members**).

## 14.4 · What goes to other services { #third-parties }

| service | when | what |
|---|---|---|
| **Discord** | always | members' sign-in; the roll call (the server's members and roles); the bot's and webhook's messages in your channels |
| **Anthropic** | only if the narrative is set up ([§8.7](08-first-settings.md#optional-settings)) | the sheet of each mission to narrate — pilots' callsigns, aircraft, events — so that the model writes its narrative |
| **the tile server** (DCS Olympus by default) | only for a tile missing from the server | the address of the requested tile, from your server's address |
| **Let's Encrypt** | option A only | the domain name, for the certificate |

No other service receives anything: no usage statistics, no telemetry.

## 14.5 · Keep the server up to date { #keep-updated }

- **The system**: apply your distribution's security updates (on Debian or Ubuntu,
  `sudo apt update && sudo apt upgrade`), and reboot when they ask for it.
- **Docker**: it is updated with the system if it comes from Docker's repository
  ([§2.3](02-prepare-the-server.md#install-docker)).
- **The database image** (`postgres:16`): `docker compose pull db`, then `docker compose up -d`; the database stays in
  its volume.
- **The Ready Room**: every release ([chapter 12](12-update.md#update)).
- **SSH access**: by key rather than by password.

## 14.6 · Where you are { #where-you-are }

- [ ] `.env` is readable only by you (`ls -l .env`: `-rw-------`), and its copy is kept apart
      ([§11.3](11-backup-and-restore.md#off-server-copy)).
- [ ] The system's security updates are applied.
