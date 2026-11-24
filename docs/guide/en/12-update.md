# 12 · Update { #update }

An update replaces the Ready Room's code with that of a new release; **`.env`, `backups/` and `data/` stay**: they are
not in the release. The database is upgraded at start-up, after a backup taken by the Ready Room itself.

All commands are typed in an SSH session, from the Ready Room's folder:

```sh
cd /opt/readyroom
```

## 12.1 · Before you start { #before-updating }

1. On the releases page, read the `CHANGELOG` of the new release and of those you skip: any step required on your side
   is written there.
2. Note the installed release: `cat VERSION`.
3. **Command Center › Archives › Back up now**, then download **Database** and **Crests**
   ([§11.3](11-backup-and-restore.md#off-server-copy)).

## 12.2 · Update { #update-steps }

**With the release archive** (you installed with [§4.2](04-get-the-ready-room.md#download)):

```sh
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<release>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1
rm readyroom.tar.gz
docker compose up -d --build
```

The archive unpacks **over the folder in place**: it replaces the code, without touching `.env`, `backups/` or `data/`.

**With Git** (you installed with `git clone`):

```sh
git fetch --depth 1 origin tag <release>
git checkout <release>
docker compose up -d --build
```

**Mission Plan and Mission Tools**, if the Ready Room serves them, are updated separately, with the two commands of
[§4.3](04-get-the-ready-room.md#suites), which fetch their latest release; your members get the new version on their next load, without restarting the Ready
Room:

```sh
curl -fL -o data/suites/dcs_mission_plan.html https://github.com/MirabelleBenou/dcs-mission-plan/releases/latest/download/dcs_mission_plan.html
curl -fL -o data/suites/dcs_mission_tools.html https://github.com/MirabelleBenou/dcs-mission-tools/releases/latest/download/dcs_mission_tools.html
```

!!! note "A file removed by a release"
    With the archive, a file that the new release has removed stays in the folder. It has no effect: the application no
    longer reads it.

## 12.3 · Check { #check-update }

```sh
docker compose logs -f app
```

If the release changes the database, you see, before start-up:

```text
[entrypoint] Migration pending (current: …, target: …): backup before applying.
[entrypoint] Backup OK (…).
[entrypoint] Migrations applied (alembic upgrade head OK).
[entrypoint] Starting the application...
```

Otherwise, the application starts straight away: that is normal.

!!! success "Check"
    `cat VERSION` and `curl -s https://<address>/api/version` give the new release; **Archives** shows a backup of
    origin **Migration** if the database changed.

!!! failure "If it does not work"
    - `[entrypoint] Failure: …`: the reason follows; a backup that fails stops everything **before** the database
      changes — fix it (most often, disk space: `df -h`), then `docker compose up -d`.
    - A new required variable is missing: the `CHANGELOG` names it; add it to `.env` ([appendix A](a-environment.md)),
      then `docker compose up -d --force-recreate app`.

## 12.4 · Roll back { #roll-back }

**If the database has not changed** (no `Migration pending` line in [§12.3](#check-update)), simply reinstall the
previous release, noted in [§12.1](#before-updating):

```sh
rm -rf app alembic
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<previous release>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1
rm readyroom.tar.gz
docker compose up -d --build
```

With Git: `git fetch --depth 1 origin tag <previous release>`, `git checkout <previous release>`, then `docker compose
up -d --build`.

!!! warning "Warning"
    The line `rm -rf app alembic` removes only the code; it is **mandatory** to roll back with the archive: without it,
    the description of a newer database change would stay in `alembic/`, and the Ready Room would try to apply it again.
    It touches neither `.env`, nor `backups/`, nor `data/`.

**If the database has changed**, the old release cannot read it: you must also go back to the previous database.

1. Reinstall the previous release as above, **without the last line** (`docker compose up -d --build`).
2. Restore the backup of origin **Migration** taken during the update — `ls -lt backups/readyroom_rev-*.dump`, the most
   recent — with the procedure of [§11.4](11-backup-and-restore.md#restore-database), **replacing its step 6** with
   `docker compose up -d --build`: the application is rebuilt on the old release.

!!! warning "Warning"
    Going back to the previous database erases what was entered since the update.

## 12.5 · Where you are { #where-you-are }

- [ ] `/api/version` gives the new release.
- [ ] The Ready Room opens and shows your data.

Chapter 13 lists faults and their remedies.
