# 4 · Get the Ready Room { #get-the-ready-room }

## 4.1 · Prepare the folder { #folder }

The Ready Room lives in a folder of its own, which will also hold its backups. This guide uses `/opt/readyroom`:

```sh
sudo mkdir -p /opt/readyroom
sudo chown "$USER": /opt/readyroom
cd /opt/readyroom
```

!!! warning "Warning"
    **Do not move this folder once the Ready Room has started.** Backups (`backups/`) and host folders (`data/`) are
    kept there through relative paths: once moved, the folder starts without them. The Docker Compose project itself is
    always called `readyroom`, whatever the folder: the database is not lost, but never run two copies of the Ready
    Room on the same server.

## 4.2 · Download the release { #download }

On the releases page, <https://github.com/MirabelleBenou/dcs-squadron-ready-room/releases>, note the name of the latest
release (for example `RR-V1.0.0`), then:

```sh
cd /opt/readyroom
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<release>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1
rm readyroom.tar.gz
```

!!! note "With Git"
    If you prefer Git: `git clone --depth 1 --branch <release> https://github.com/MirabelleBenou/dcs-squadron-ready-room.git /opt/readyroom`
    (the folder must be empty).

!!! success "Check"
    `cat VERSION; echo` prints the release number; `ls` shows `docker-compose.yml` and `init-env.sh`, and `ls -a` also shows
    `.env.example`.

Then create the folders the Ready Room plugs in, so that they belong to you and not to `root`:

```sh
mkdir -p backups data/suites data/tiles data/tiles-cache
```

## 4.3 · Optional: Mission Plan and Mission Tools { #suites }

The Ready Room's home page has two tiles, **Mission Plan** and **Mission Tools**, the mission-planning suites. What
they open depends on this step:

- **without it**, the public online version of the suites: it works, but knows neither your wing nor its squadrons;
- **with it**, the suites served by the Ready Room, behind its sign-in: they receive the wing's identity, its
  squadrons and their crests.

They are two files, those of each suite's latest release, to download into `data/suites`:

```sh
cd /opt/readyroom
mkdir -p data/suites
curl -fL -o data/suites/dcs_mission_plan.html https://github.com/MirabelleBenou/dcs-mission-plan/releases/latest/download/dcs_mission_plan.html
curl -fL -o data/suites/dcs_mission_tools.html https://github.com/MirabelleBenou/dcs-mission-tools/releases/latest/download/dcs_mission_tools.html
```

!!! success "Check"
    `ls -lh data/suites` shows both files, several megabytes each.

!!! note
    If you put this folder elsewhere (`SUITES_HOST_DIR`, [§5.5](05-configure.md#host-folders)), download both files
    into that folder. This step can also be done later, without restarting the Ready Room. If `data/suites` was created by Docker (owned by `root`): `sudo chown -R "$USER": data`.

## 4.4 · What the folder contains { #contents }

| file or folder | what it is for |
|---|---|
| `docker-compose.yml` | the two containers, `app` and `db`, and their volumes |
| `compose.caddy.yml` | the HTTPS proxy of option A (chapter 6) |
| `.env.example` | the template of the configuration file |
| `init-env.sh` | writes your `.env` by asking questions (chapter 5) |
| `Dockerfile`, `entrypoint.sh`, `app/`, `alembic/`, `requirements.txt` | the application itself, built at first start |
| `VERSION`, `CHANGELOG.md` | the release number and what changed |
| `LICENSE`, `README.md` | the licence and the overview |
| `tests/`, `tools/`, `manuel/`, `release.py`, `ASSETS.md`, `README.fr.md` | for the maintainers and the credits; nothing to do |

`backups/` (the backups) and `data/` (the host folders,
[§5.5](05-configure.md#host-folders)) are the folders created at the end of [§4.2](#download). The release archive does not contain this guide (a `git clone` does, under `docs/`). It is online, and attached as a PDF to every release.
