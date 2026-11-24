# C · L'aide-mémoire des commandes { #commands }

Une ligne par geste, avec le chapitre qui l'explique. Sauf mention contraire, chaque commande se tape sur le serveur,
dans le dossier de la Ready Room :

```sh
cd /opt/readyroom
```

## C.1 · Démarrer, arrêter, lire { #run }

```sh
docker compose up -d --build                    # démarrer, ou appliquer une release (§7.1, §12.2)
docker compose ps                               # l'état des conteneurs (§7.1)
docker compose logs -f app                      # suivre le journal ; Ctrl+C pour quitter (§7.2)
docker compose logs --since 1h app              # le journal de la dernière heure (§13)
docker compose up -d --force-recreate app       # relire .env après une modification (§7.2)
docker compose restart caddy                    # option A : relancer Caddy (§13.10)
docker compose down                             # arrêter, sans rien effacer (§15.2)
curl -s https://<adresse>/api/version ; echo    # la release en service (§7.3)
```

## C.2 · Ce qui tourne tout seul { #background-tasks }

```sh
docker compose logs --since 48h app | grep -E "Appel \(|roll:|Sauvegarde automatique"   # l'appel, le passage de 6 h, les sauvegardes (§9.4)
docker compose logs app | grep "Commande /readyroom"                                   # la déclaration de /readyroom (§13.4)
docker compose logs app | grep "Digest Discord"                                        # le digest (§13.5)
```

## C.3 · Les messages Discord à la main { #discord-triggers }

Le jeton est celui de **Configuration › Discord — le digest › Jeton des mises à jour manuelles**
([§9.5](09-running-on-its-own.md#manual-triggers)). Chaque commande affiche le code de la réponse : `204`, fait ;
`403`, jeton refusé.

```sh
# Le passage de 6 h, tout de suite : le digest, ou les messages de présence
curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H "X-Digest-Token: <jeton>" http://127.0.0.1:8000/discord/rsvp/roll

# Le digest seul, reposté — seulement si « Réponses dans Discord » est éteint
curl -sS -o /dev/null -w '%{http_code}\n' -X POST -H "X-Digest-Token: <jeton>" http://127.0.0.1:8000/api/internal/digest
```

## C.4 · Sauvegarder et restaurer { #backup-commands }

```sh
ls -lt backups/                                 # les sauvegardes, la plus récente d'abord (§11.4)
df -h                                           # l'espace disque (§9.4, §13.1)
```

L'archive des dépôts bruts ([§11.2](11-backup-and-restore.md#raw-deposits)) :

```sh
docker run --rm -v readyroom_debrief_raw:/data:ro -v "$(pwd)/backups":/backup \
  alpine sh -c 'tar czf /backup/debrief_raw_$(date +%Y%m%d-%H%M).tar.gz -C /data .'
```

La copie hors du serveur, **depuis votre ordinateur** ([§11.3](11-backup-and-restore.md#off-server-copy)) :

```sh
scp -r <utilisateur>@<serveur>:/opt/readyroom/backups ./readyroom-backups
```

La restauration de la base se fait en six étapes, sans en sauter une : elles sont au
[§11.4](11-backup-and-restore.md#restore-database), et ne se résument pas ici. Les écussons : le
[§11.5](11-backup-and-restore.md#restore-crests). L'essai à blanc : le [§11.6](11-backup-and-restore.md#restore-dry-run).

## C.5 · Mettre à jour { #update-commands }

```sh
cat VERSION; echo                               # la release installée (§12.1)
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<release>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1  # par-dessus le dossier en place (§12.2)
rm readyroom.tar.gz
docker compose up -d --build
```

Mission Plan et Mission Tools, si la Ready Room les sert : à l'installation et à chaque mise à jour (§4.3, §12.2) :

```sh
curl -fL -o data/suites/dcs_mission_plan.html https://github.com/MirabelleBenou/dcs-mission-plan/releases/latest/download/dcs_mission_plan.html
curl -fL -o data/suites/dcs_mission_tools.html https://github.com/MirabelleBenou/dcs-mission-tools/releases/latest/download/dcs_mission_tools.html
```

Avec Git (§12.2) :

```sh
git fetch --depth 1 origin tag <release>
git checkout <release>
docker compose up -d --build
```

Revenir en arrière : le [§12.4](12-update.md#roll-back), qui commence par `rm -rf app alembic`.

## C.6 · Sécurité et système { #system-commands }

```sh
ls -l .env                                      # doit montrer -rw------- (§14.6)
sudo apt update && sudo apt upgrade             # les mises à jour du système, Debian ou Ubuntu (§14.5)
docker compose pull db && docker compose up -d  # la dernière image de postgres:16 (§14.5)
```

## C.7 · Désinstaller { #uninstall-commands }

```sh
docker compose down -v                          # ATTENTION : efface la base, les écussons et les dépôts bruts (§15.3)
docker volume ls --filter name=readyroom        # les volumes qui restent (§15.3)
```

## C.8 · Sur le PC du serveur DCS { #agent-commands }

Dans PowerShell, depuis le dossier de `envoi\` ([chapitre 10](10-dcs-agent.md#dcs-agent)) :

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\installer_envoi.ps1 -Compte <DOMAINE\compte>   # installer la tâche, en administrateur (§10.4)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\readyroom_envoi.ps1                           # une passe d'envoi, tout de suite (§10.5)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\installer_envoi.ps1 -Desinstaller             # retirer la tâche, en administrateur (§10.6)
```
