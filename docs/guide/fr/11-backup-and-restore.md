# 11 · Sauvegarder et restaurer { #backup-and-restore }

La Ready Room sauvegarde elle-même sa base ; ce chapitre dit ce que ses sauvegardes contiennent, ce qu'il faut garder
à part, comment en mettre une copie hors du serveur, et comment restaurer. **Aucune restauration ne se fait depuis
l'application** : elle se fait en ligne de commande, sur le serveur, dans le dossier de la Ready Room.

Toutes les commandes de ce chapitre se tapent dans une session SSH, depuis ce dossier :

```sh
cd /opt/readyroom
```

## 11.1 · Ce que prend une sauvegarde { #what-a-backup-holds }

Une sauvegarde de la Ready Room, ce sont **deux fichiers** dans `backups/` :

| fichier | contenu |
|---|---|
| `readyroom_<origine>-<révision>_<date>.dump` | **la base** : membres, escadrilles, planning, présences, rapports, réglages |
| `readyroom_<origine>-<révision>_<date>_ecussons.tar.gz` | **les écussons** des escadrilles et l'emblème de l'escadre |

Elles naissent de trois façons, que **Centre de Commandement › Archives**, bloc **Sauvegardes**, affiche dans la colonne
**Origine** :

- **Manuelle** : le bouton **Sauvegarder maintenant** ; les dix dernières sont gardées ;
- **Automatique** : selon le réglage du [§9.3](09-running-on-its-own.md#automatic-backups) ;
- **Migration** : prise par la Ready Room elle-même avant chaque changement de sa base, à une mise à jour ; la base
  seule, sans écussons ; les dix dernières sont gardées.

**Ce qu'une sauvegarde ne prend pas** :

- **le fichier `.env`** : sans lui, et surtout sans sa `CONFIG_KEY`, les secrets enregistrés dans **Configuration**
  (jeton du bot, clé de l'API Anthropic, adresse du webhook…) ne se relisent plus ; gardez-en une copie à part
  ([§11.3](#off-server-copy)) ;
- **les dépôts bruts du module Escadre** (les fichiers de débriefing déposés et ceux de l'agent) : ils vivent dans le
  volume `readyroom_debrief_raw`, que le [§11.2](#raw-deposits) archive à part ;
- **les tuiles de la carte** et les fichiers des suites : ils se retrouvent à leur source.

!!! warning "Attention"
    Une sauvegarde qui reste sur le serveur disparaît avec lui. Mettez-en une copie ailleurs ([§11.3](#off-server-copy)).

## 11.2 · Les dépôts bruts { #raw-deposits }

Rien ne garantit qu'un dépôt brut perdu se retrouve ailleurs : un pilote n'a aucune raison de garder ses fichiers, et
le serveur DCS n'a que ceux de son agent, purgés après 30 jours. Archivez-les à part :

```sh
docker run --rm \
  -v readyroom_debrief_raw:/data:ro \
  -v "$(pwd)/backups":/backup \
  alpine sh -c 'tar czf /backup/debrief_raw_$(date +%Y%m%d-%H%M).tar.gz -C /data .'
```

!!! success "Vérifier"
    `ls -lh backups/debrief_raw_*` montre l'archive, d'une taille non nulle.

## 11.3 · Une copie hors du serveur { #off-server-copy }

**Le plus simple**, depuis votre navigateur : **Archives**, bloc **Sauvegardes**, sur la ligne d'une sauvegarde,
**Base**, puis **Écussons** : les deux fichiers se téléchargent sur votre ordinateur.

**Pour tout le dossier**, depuis votre ordinateur (pas depuis le serveur), avec l'utilisateur et l'adresse de votre
session SSH :

```sh
scp -r <utilisateur>@<serveur>:/opt/readyroom/backups ./readyroom-backups
scp <utilisateur>@<serveur>:/opt/readyroom/.env ./readyroom-env
```

!!! warning "Attention"
    La copie de `.env` contient tous les secrets de la Ready Room, dont `CONFIG_KEY`. Rangez-la **à part des
    sauvegardes** ([§5.4](05-configure.md#config-key)) : dans votre gestionnaire de mots de passe, jamais dans le même
    dossier que `backups/`, jamais dans un dossier partagé.

## 11.4 · Restaurer la base { #restore-database }

La restauration **remplace toute la base** par la sauvegarde choisie. Elle se fait **dans cet ordre, sans en sauter
une étape** : une erreur à l'étape 5 laisse la base vide, et c'est la sauvegarde de l'étape 2 qui la rend.

1. Choisissez le fichier : `ls -lt backups/*.dump`. Notez son nom.
2. Sauvegardez d'abord la base actuelle :

    ```sh
    docker compose run --rm --entrypoint sh app -c \
      'PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
       -f /backups/avant_restauration_$(date +%Y%m%d-%H%M).dump'
    ```

3. Arrêtez l'application ; la base reste en marche :

    ```sh
    docker compose stop app
    ```

4. Recréez la base, vide :

    ```sh
    docker compose exec db sh -c 'dropdb --force -U "$POSTGRES_USER" "$POSTGRES_DB"'
    docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" -O "$POSTGRES_USER" "$POSTGRES_DB"'
    ```

5. Restaurez, en remplaçant `<fichier>` par le nom de l'étape 1 :

    ```sh
    docker compose run --rm --entrypoint sh app -c \
      'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
       --single-transaction /backups/<fichier>.dump'
    ```

6. Relancez l'application :

    ```sh
    docker compose up -d app
    ```

!!! success "Vérifier"
    L'étape 5 se termine sans aucune ligne `error`. `docker compose logs app` montre `Application startup complete`, et
    la Ready Room affiche les données de la date de la sauvegarde.

!!! warning "Attention"
    **N'ajoutez jamais `--clean` à `pg_restore`.** Sur une base qu'une mise à jour a fait évoluer depuis la sauvegarde,
    `--clean` laisse des restes de la version récente : la base est mêlée et l'application ne redémarre plus. La base
    recréée vide de l'étape 4 n'a pas ce défaut.

!!! failure "Si ça ne marche pas"
    - L'étape 5 s'arrête sur une erreur : rien n'a été écrit (`--single-transaction`) ; la base est vide. Reprenez les
      étapes 4 et 5 avec la sauvegarde `avant_restauration_…` de l'étape 2.
    - `app` redémarre en boucle après l'étape 6 : la sauvegarde vient d'une version **plus récente** que celle
      installée ; installez au moins cette version ([§12](12-update.md#update)), puis relancez.

## 11.5 · Restaurer les écussons { #restore-crests }

Après la base, si les écussons ou l'emblème manquent (un emplacement vide à leur place, jamais une image cassée) :

```sh
docker compose stop app
docker run --rm \
  -v readyroom_crests:/data \
  -v "$(pwd)/backups":/backup \
  alpine sh -c 'rm -rf /data/* && tar xzf /backup/<fichier>_ecussons.tar.gz -C /data'
docker compose up -d app
```

Les dépôts bruts se restaurent de la même façon, avec le volume `readyroom_debrief_raw` et une archive
`debrief_raw_….tar.gz`.

!!! warning "Attention"
    Ces commandes **remplacent tout le contenu** du volume par celui de l'archive.

## 11.6 · Essayer une sauvegarde à blanc { #restore-dry-run }

Pour savoir qu'une sauvegarde se restaure, sans toucher à la base en service : restaurez-la dans une base jetable, puis
comparez.

```sh
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" readyroom_essai'
docker compose exec app sh -c \
  'PGPASSWORD="$POSTGRES_PASSWORD" pg_restore -h db -U "$POSTGRES_USER" -d readyroom_essai \
   --single-transaction /backups/<fichier>.dump'
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d readyroom_essai \
  -c "select count(*) from profiles;" -c "select count(*) from events;"'
docker compose exec db sh -c 'dropdb -U "$POSTGRES_USER" readyroom_essai'
```

!!! success "Vérifier"
    La restauration se termine sans `error`, et les deux comptes (membres, évènements) sont ceux que vous attendez.

## 11.7 · Où vous en êtes { #where-you-are }

- [ ] **Archives** montre des sauvegardes **Automatique** récentes.
- [ ] Une copie de `backups/` et de `.env` existe hors du serveur.
- [ ] *(conseillé)* Une sauvegarde a été essayée à blanc ([§11.6](#restore-dry-run)).

Le chapitre 12 met la Ready Room à jour.
