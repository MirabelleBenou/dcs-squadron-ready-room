# C · Command cheat sheet { #commands }

One line per action, with the chapter that explains it. Unless stated otherwise, each command is typed on the server,
in the Ready Room's folder:

```sh
cd /opt/readyroom
```

## C.1 · Start, stop, read { #run }

```sh
docker compose up -d --build                    # start, or apply a release (§7.1, §12.2)
docker compose ps                               # the containers' state (§7.1)
docker compose logs -f app                      # follow the log; Ctrl+C to quit (§7.2)
docker compose logs --since 1h app              # the log of the last hour (§13)
docker compose up -d --force-recreate app       # read .env again after a change (§7.2)
docker compose restart caddy                    # option A: restart Caddy (§13.10)
docker compose down                             # stop, without erasing anything (§15.2)
curl -s https://<address>/api/version ; echo    # the release in service (§7.3)
```

## C.2 · What runs on its own { #background-tasks }

```sh
docker compose logs --since 48h app | grep -E "Appel \(|roll:|Sauvegarde automatique"   # the roll call, the 6 a.m. pass, backups (§9.4)
docker compose logs app | grep "Commande /readyroom"                                   # the registration of /readyroom (§13.4)
docker compose logs app | grep "Digest Discord"                                        # the digest (§13.5)
```

## C.3 · Discord messages by hand { #discord-triggers }

The token is the one in **Configuration › Discord — digest › Manual update token**
([§9.5](09-running-on-its-own.md#manual-triggers)). Each command prints the response code: `204`, done; `403`, token
refused.

```sh
# The 6 a.m. pass, right now: the digest, or the attendance messages
curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H "X-Digest-Token: <token>" http://127.0.0.1:8000/discord/rsvp/roll

# The digest alone, posted again — only if "Replies in Discord" is off
curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H "X-Digest-Token: <token>" http://127.0.0.1:8000/api/internal/digest
```

## C.4 · Back up and restore { #backup-commands }

```sh
ls -lt backups/                                 # the backups, most recent first (§11.4)
df -h                                           # disk space (§9.4, §13.1)
```

The archive of the raw uploads ([§11.2](11-backup-and-restore.md#raw-deposits)):

```sh
docker run --rm -v readyroom_debrief_raw:/data:ro -v "$(pwd)/backups":/backup \
  alpine sh -c 'tar czf /backup/debrief_raw_$(date +%Y%m%d-%H%M).tar.gz -C /data .'
```

The copy off the server, **from your computer** ([§11.3](11-backup-and-restore.md#off-server-copy)):

```sh
scp -r <user>@<server>:/opt/readyroom/backups ./readyroom-backups
```

Restoring the database takes six steps, none to be skipped: they are in
[§11.4](11-backup-and-restore.md#restore-database), and are not summed up here. The crests:
[§11.5](11-backup-and-restore.md#restore-crests). The risk-free test: [§11.6](11-backup-and-restore.md#restore-dry-run).

## C.5 · Update { #update-commands }

```sh
cat VERSION                                     # the installed release (§12.1)
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<release>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1  # over the folder in place (§12.2)
rm readyroom.tar.gz
docker compose up -d --build
```

Mission Plan and Mission Tools, if the Ready Room serves them: at installation and at each update (§4.3, §12.2):

```sh
curl -fL -o data/suites/dcs_mission_plan.html https://github.com/MirabelleBenou/dcs-mission-plan/releases/latest/download/dcs_mission_plan.html
curl -fL -o data/suites/dcs_mission_tools.html https://github.com/MirabelleBenou/dcs-mission-tools/releases/latest/download/dcs_mission_tools.html
```

With Git (§12.2):

```sh
git fetch --depth 1 origin tag <release>
git checkout <release>
docker compose up -d --build
```

Rolling back: [§12.4](12-update.md#roll-back), which starts with `rm -rf app alembic`.

## C.6 · Security and system { #system-commands }

```sh
ls -l .env                                      # must show -rw------- (§14.6)
sudo apt update && sudo apt upgrade             # system updates, Debian or Ubuntu (§14.5)
docker compose pull db && docker compose up -d  # the latest postgres:16 image (§14.5)
```

## C.7 · Uninstall { #uninstall-commands }

```sh
docker compose down -v                          # WARNING: erases the database, the crests and the raw uploads (§15.3)
docker volume ls --filter name=readyroom        # the volumes that remain (§15.3)
```

## C.8 · On the DCS server's PC { #agent-commands }

In PowerShell, from the `envoi\` folder ([chapter 10](10-dcs-agent.md#dcs-agent)):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\installer_envoi.ps1 -Compte <DOMAIN\account>   # install the task, as administrator (§10.4)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\readyroom_envoi.ps1                            # one upload pass, right now (§10.5)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\installer_envoi.ps1 -Desinstaller              # remove the task, as administrator (§10.6)
```
