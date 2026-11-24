# 12 · Mettre à jour { #update }

Une mise à jour remplace le code de la Ready Room par celui d'une nouvelle release ; **`.env`, `backups/` et `data/`
restent** : ils ne sont pas dans la release. La base, elle, est mise à niveau au démarrage, après une sauvegarde prise
par la Ready Room elle-même.

Toutes les commandes se tapent dans une session SSH, depuis le dossier de la Ready Room :

```sh
cd /opt/readyroom
```

## 12.1 · Avant de commencer { #before-updating }

1. Sur la page des releases, lisez le `CHANGELOG` de la nouvelle release et de celles que vous sautez : un geste à faire de
   votre part y est écrit.
2. Notez la release installée : `cat VERSION; echo`.
3. **Centre de Commandement › Archives › Sauvegarder maintenant**, puis téléchargez **Base** et **Écussons**
   ([§11.3](11-backup-and-restore.md#off-server-copy)).

## 12.2 · Mettre à jour { #update-steps }

**Avec l'archive de la release** (vous avez installé au [§4.2](04-get-the-ready-room.md#download)) :

```sh
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<release>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1
rm readyroom.tar.gz
docker compose up -d --build
```

L'archive se décompresse **par-dessus le dossier en place** : elle remplace le code, sans toucher à `.env`, `backups/`
ni `data/`.

**Avec Git** (vous avez installé par `git clone`) :

```sh
git fetch --depth 1 origin tag <release>
git checkout <release>
docker compose up -d --build
```

**Mission Plan et Mission Tools**, si la Ready Room les sert, se mettent à jour à part, par les deux commandes du
[§4.3](04-get-the-ready-room.md#suites), qui prennent leur dernière release ; vos membres reçoivent la nouvelle version au chargement suivant, sans
redémarrer la Ready Room :

```sh
curl -fL -o data/suites/dcs_mission_plan.html https://github.com/MirabelleBenou/dcs-mission-plan/releases/latest/download/dcs_mission_plan.html
curl -fL -o data/suites/dcs_mission_tools.html https://github.com/MirabelleBenou/dcs-mission-tools/releases/latest/download/dcs_mission_tools.html
```

!!! note "Un fichier retiré par une release"
    Avec l'archive, un fichier que la nouvelle release a retiré reste dans le dossier. Il est sans effet : l'application
    ne le lit plus.

## 12.3 · Vérifier { #check-update }

```sh
docker compose logs -f app
```

Si la release change la base, vous voyez passer, avant le démarrage :

```text
[entrypoint] Migration pending (current: …, target: …): backup before applying.
[entrypoint] Backup OK (…).
[entrypoint] Migrations applied (alembic upgrade head OK).
[entrypoint] Starting the application...
```

Sinon, l'application démarre directement : c'est normal.

!!! success "Vérifier"
    `cat VERSION; echo` et `curl -s https://<adresse>/api/version` donnent la nouvelle release ; **Archives** montre une
    sauvegarde d'origine **Migration** si la base a changé.

!!! failure "Si ça ne marche pas"
    - `[entrypoint] Failure: …` : la raison suit ; une sauvegarde qui échoue arrête tout **avant** que la base ne
      change — corrigez (le plus souvent, l'espace disque : `df -h`), puis `docker compose up -d`.
    - Une nouvelle variable obligatoire manque : le `CHANGELOG` la nomme ; ajoutez-la à `.env`
      ([annexe A](a-environment.md)), puis `docker compose up -d --force-recreate app`.

## 12.4 · Revenir en arrière { #roll-back }

**Si la base n'a pas changé** (aucune ligne `Migration pending` au [§12.3](#check-update)), réinstallez simplement la
release d'avant, notée au [§12.1](#before-updating) :

```sh
rm -rf app alembic
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<release d'avant>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1
rm readyroom.tar.gz
docker compose up -d --build
```

Avec Git : `git fetch --depth 1 origin tag <release d'avant>`, `git checkout <release d'avant>`, puis `docker compose
up -d --build`.

!!! warning "Attention"
    La ligne `rm -rf app alembic` ne retire que le code ; elle est **obligatoire** pour revenir en arrière avec
    l'archive : sans elle, la description d'un changement de base plus récent resterait dans `alembic/`, et la Ready
    Room tenterait de l'appliquer de nouveau. Elle ne touche ni à `.env`, ni à `backups/`, ni à `data/`.

**Si la base a changé**, l'ancienne release ne sait pas la lire : il faut aussi revenir à la base d'avant.

1. Réinstallez la release d'avant comme ci-dessus, **sans la dernière ligne** (`docker compose up -d --build`).
2. Restaurez la sauvegarde d'origine **Migration** prise à la mise à jour — `ls -lt backups/readyroom_rev-*.dump`, la
   plus récente — par la procédure du [§11.4](11-backup-and-restore.md#restore-database), **en remplaçant son étape 6**
   par `docker compose up -d --build` : l'application se reconstruit sur l'ancienne release.

!!! warning "Attention"
    Revenir à la base d'avant efface ce qui a été saisi depuis la mise à jour.

## 12.5 · Où vous en êtes { #where-you-are }

- [ ] `/api/version` donne la nouvelle release.
- [ ] La Ready Room s'ouvre et affiche vos données.

Le chapitre 13 recense les pannes et leurs remèdes.
