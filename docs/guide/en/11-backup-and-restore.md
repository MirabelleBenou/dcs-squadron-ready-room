# 11 · Back up and restore { #backup-and-restore }

The Ready Room backs up its own database; this chapter says what its backups contain, what must be kept separately, how
to put a copy off the server, and how to restore. **No restore is done from the application**: it is done on the
command line, on the server, in the Ready Room's folder.

All commands in this chapter are typed in an SSH session, from that folder:

```sh
cd /opt/readyroom
```

## 11.1 · What a backup holds { #what-a-backup-holds }

A Ready Room backup is **two files** in `backups/`:

| file | contents |
|---|---|
| `readyroom_<origin>-<revision>_<date>.dump` | **the database**: members, squadrons, schedule, attendance, reports, settings |
| `readyroom_<origin>-<revision>_<date>_ecussons.tar.gz` | **the crests** of the squadrons and the wing's emblem |

They come about in three ways, which **Command Center › Archives**, block **Backups**, shows in the **Origin** column:

- **Manual**: the **Back up now** button; the last ten are kept;
- **Automatic**: according to the setting of [§9.3](09-running-on-its-own.md#automatic-backups);
- **Migration**: taken by the Ready Room itself before each change to its database, during an update; the database
  only, without crests; the last ten are kept.

**What a backup does not take**:

- **the `.env` file**: without it, and above all without its `CONFIG_KEY`, the secrets saved in **Configuration**
  (bot token, Anthropic API key, webhook URL…) can no longer be read; keep a copy of it separately
  ([§11.3](#off-server-copy));
- **the raw uploads of the Wing module** (the debriefing files uploaded, and those from the agent): they live in the
  `readyroom_debrief_raw` volume, which [§11.2](#raw-deposits) archives separately;
- **the map tiles** and the suite files: they can be fetched again from their source.

!!! warning "Warning"
    A backup that stays on the server disappears with it. Put a copy elsewhere ([§11.3](#off-server-copy)).

## 11.2 · Raw uploads { #raw-deposits }

Nothing guarantees that a lost raw upload can be found elsewhere: a pilot has no reason to keep their files, and the
DCS server only has those from its agent, purged after 30 days. Archive them separately:

```sh
docker run --rm \
  -v readyroom_debrief_raw:/data:ro \
  -v "$(pwd)/backups":/backup \
  alpine sh -c 'tar czf /backup/debrief_raw_$(date +%Y%m%d-%H%M).tar.gz -C /data .'
```

!!! success "Check"
    `ls -lh backups/debrief_raw_*` shows the archive, with a non-zero size.

## 11.3 · A copy off the server { #off-server-copy }

**The simplest**, from your browser: **Archives**, block **Backups**, on a backup's line, **Database**, then
**Crests**: both files download to your computer.

**For the whole folder**, from your computer (not from the server), with the user and address of your SSH session:

```sh
scp -r <user>@<server>:/opt/readyroom/backups ./readyroom-backups
scp <user>@<server>:/opt/readyroom/.env ./readyroom-env
```

!!! warning "Warning"
    The copy of `.env` holds all the Ready Room's secrets, `CONFIG_KEY` included. Keep it **apart from the backups**
    ([§5.4](05-configure.md#config-key)): in your password manager, never in the same folder as `backups/`, never in a
    shared folder.

## 11.4 · Restore the database { #restore-database }

Restoring **replaces the whole database** with the chosen backup. It is done **in this order, without skipping a
step**: an error at step 5 leaves the database empty, and the backup from step 2 brings it back.

1. Choose the file: `ls -lt backups/*.dump`. Note its name.
2. First back up the current database:

    ```sh
    docker compose run --rm --entrypoint sh app -c \
      'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
       -f /backups/before_restore_$(date +%Y%m%d-%H%M).dump'
    ```

3. Stop the application; the database keeps running:

    ```sh
    docker compose stop app
    ```

4. Recreate the database, empty:

    ```sh
    docker compose exec db sh -c 'dropdb --force -U "$POSTGRES_USER" "$POSTGRES_DB"'
    docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$POSTGRES_DB"'
    ```

5. Restore, replacing `<file>` with the name from step 1:

    ```sh
    docker compose run --rm --entrypoint sh app -c \
      'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
       --single-transaction /backups/<file>.dump'
    ```

6. Start the application again:

    ```sh
    docker compose up -d app
    ```

!!! success "Check"
    Step 5 ends without any `error` line. `docker compose logs app` shows `Application startup complete`, and the
    Ready Room shows the data as of the backup's date.

!!! warning "Warning"
    **Never add `--clean` to `pg_restore`.** On a database that an update has changed since the backup, `--clean`
    leaves remnants of the newer version behind: the database is mixed and the application no longer starts. The
    database recreated empty at step 4 does not have this flaw.

!!! failure "If it does not work"
    - Step 5 stops on an error: nothing was written (`--single-transaction`); the database is empty. Redo steps 4 and
      5 with the `before_restore_…` backup from step 2.
    - `app` restarts in a loop after step 6: the backup comes from a **newer** version than the one installed;
      install at least that version ([§12](12-update.md#update)), then start again.

## 11.5 · Restore the crests { #restore-crests }

After the database, if the crests or the emblem are missing (an empty slot in their place, never a broken image):

```sh
docker compose stop app
docker run --rm \
  -v readyroom_crests:/data \
  -v "$(pwd)/backups":/backup \
  alpine sh -c 'rm -rf /data/* && tar xzf /backup/<file>_ecussons.tar.gz -C /data'
docker compose up -d app
```

Raw uploads are restored the same way, with the `readyroom_debrief_raw` volume and a `debrief_raw_….tar.gz` archive.

!!! warning "Warning"
    These commands **replace the whole content** of the volume with that of the archive.

## 11.6 · Test a backup without risk { #restore-dry-run }

To know that a backup restores, without touching the live database: restore it into a throwaway database, then
compare.

```sh
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" readyroom_test'
docker compose exec app sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d readyroom_test \
   --single-transaction /backups/<file>.dump'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d readyroom_test \
  -c "select count(*) from profiles;" -c "select count(*) from events;"'
docker compose exec db sh -c 'dropdb -U "$POSTGRES_USER" readyroom_test'
```

!!! success "Check"
    The restore ends without `error`, and the two counts (members, events) are the ones you expect.

## 11.7 · Where you are { #where-you-are }

- [ ] **Archives** shows recent **Automatic** backups.
- [ ] A copy of `backups/` and of `.env` exists off the server.
- [ ] *(recommended)* A backup has been tested without risk ([§11.6](#restore-dry-run)).

Chapter 12 updates the Ready Room.
