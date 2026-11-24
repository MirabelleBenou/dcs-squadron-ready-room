# 5 · Configure { #configure }

The Ready Room reads its start-up configuration from a file, **`.env`**, at the root of its folder. It only holds what
is needed to start: the address, the Discord application, the founding administrators, three secrets and the
database. **Everything else is then set inside the Ready Room**, on screen.

## 5.1 · Write `.env` { #write-env }

The simplest way is the script provided: it asks the questions, makes the secrets and writes the file with the right
permissions. It touches nothing else.

```sh
cd /opt/readyroom
sh init-env.sh
```

Answer with the values collected in chapters 2 and 3. At the end it shows the settings key (`CONFIG_KEY`) **once**:
copy it into your password manager ([§5.4](#config-key)).

!!! note "By hand"
    You can also copy the template and fill it in with `nano`, following [§5.2](#required-variables):
    ```sh
    cp .env.example .env
    chmod 600 .env
    nano .env
    ```

!!! failure "If it does not work"
    `init-env.sh` refuses to replace an existing `.env`: rename the old one (`mv .env .env.old`) if you want to start
    again.

## 5.2 · Required variables { #required-variables }

| variable | what it holds | where it comes from |
|---|---|---|
| `BASE_URL` | the Ready Room's HTTPS address, without a trailing `/` | [§2.5](02-prepare-the-server.md#address) |
| `DISCORD_CLIENT_ID` | the *Application ID* | [§3.2](03-discord-application.md#create-application) |
| `DISCORD_CLIENT_SECRET` | the *Client Secret* | [§3.2](03-discord-application.md#create-application) |
| `DISCORD_GUILD_ID` | your Discord server's ID | [§3.1](03-discord-application.md#developer-mode) |
| `ADMIN_IDS` | the founding administrators | [§5.3](#founders) |
| `SESSION_SECRET` | the secret that signs members' sessions | to be made, below |
| `CONFIG_KEY` | the key that encrypts the secrets kept in the database | to be made, below |
| `POSTGRES_USER`, `POSTGRES_DB` | the database user and name | `readyroom` is fine |
| `POSTGRES_PASSWORD` | the database password | to be made, below |

Secrets are made with `openssl`, one command per secret; paste each result into `.env`:

```sh
openssl rand -base64 48 | tr -d '\n' ; echo      # SESSION_SECRET
openssl rand -base64 32 | tr '+/' '-_'           # CONFIG_KEY
openssl rand -hex 24                             # POSTGRES_PASSWORD
```

!!! warning "Warning"
    `SESSION_SECRET` must be at least 32 characters long and must never keep the example value: otherwise the Ready
    Room refuses to start. Discord IDs are written as digits only, without spaces or quotes.

!!! note "The database"
    `POSTGRES_USER`, `POSTGRES_PASSWORD` and `POSTGRES_DB` create the database at first start, and the application uses
    them to reach it. Changing them **after** the first start does not change the database already created: the Ready
    Room could no longer connect to it.

## 5.3 · Founding administrators { #founders }

`ADMIN_IDS` names **the founding administrators**: at least one Discord ID, several separated by commas, without
spaces:

```text
ADMIN_IDS=<your ID>,<another founder's ID>
```

A founder always gets in and opens everything, whatever their Discord roles: it is the safeguard that stops you
locking yourself out. They must still be **a member of the wing's Discord server**. Other administrators are appointed
later inside the Ready Room (**Command Center › Configuration › Administrators**); a founder cannot be removed there:
remove them by editing `ADMIN_IDS`.

## 5.4 · The settings key { #config-key }

`CONFIG_KEY` encrypts the secrets you will enter on screen (bot token, webhook, Anthropic key…).

!!! warning "Warning"
    **Keep `CONFIG_KEY` apart from the backups**, in your password manager: a database backup with its key next to it
    makes those secrets readable by whoever finds it. **If lost or changed**, the key makes those secrets unreadable:
    they must be entered again in the **Configuration** screen; nothing else is lost.

## 5.5 · Optional: host folders { #host-folders }

Three server folders are plugged into the application. By default they are under `data/` in the Ready Room folder; to
put them elsewhere (a data disk, for example), add these lines to `.env`:

| variable | default | what goes there |
|---|---|---|
| `SUITES_HOST_DIR` | `./data/suites` | `dcs_mission_plan.html` and `dcs_mission_tools.html`, if the Ready Room is to serve Mission Plan and Mission Tools |
| `TILES_HOST_DIR` | `./data/tiles` | the DCS map tiles, extracted from the Olympus archives (read only) |
| `TILES_CACHE_HOST_DIR` | `./data/tiles-cache` | the tiles fetched from Olympus, kept by the Ready Room |

Without these features, keep the defaults: nothing breaks if the folders are empty.

## 5.6 · What does not go into `.env` { #not-in-env }

Everything else is set **inside the Ready Room**, without restarting, by an administrator:

| setting | where | when |
|---|---|---|
| the wing's time zone | **Configuration**: *Time zone* | chapter 7 |
| the wing's name, tag and emblem | **Command Center › Wing** | chapter 8 |
| squadrons, who gets in, who creates events | **Squadrons**, **Rights** | chapter 8 |
| the `/readyroom` command, attendance buttons | **Configuration**: *Discord — replies* | chapter 7 |
| the weekly digest | **Configuration**: *Discord — digest* | chapter 7 |
| mission report narratives | **Configuration**: *Mission report narrative* | chapter 8 |
| another tile server | **Configuration**: *Map tiles* | — |

The full list of variables and settings is in [appendix A](a-environment.md).

## 5.7 · Check { #check-env }

```sh
ls -l .env
grep -n -E 'changeme|change_this|=$' .env
```

!!! success "Check"
    `ls -l` shows `-rw-------` (readable by you only); `grep` prints **nothing** (no example or empty value left).
    Otherwise: `chmod 600 .env`, and complete each line printed.
