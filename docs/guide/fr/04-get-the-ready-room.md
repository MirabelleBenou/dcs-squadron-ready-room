# 4 · Obtenir la Ready Room { #get-the-ready-room }

## 4.1 · Préparer le dossier { #folder }

La Ready Room vit dans un dossier à elle, qui gardera aussi ses sauvegardes. Ce guide prend `/opt/readyroom` :

```sh
sudo mkdir -p /opt/readyroom
sudo chown "$USER": /opt/readyroom
cd /opt/readyroom
```

!!! warning "Attention"
    **Ne déplacez pas ce dossier une fois la Ready Room démarrée.** Les sauvegardes (`backups/`) et les dossiers de
    l'hôte (`data/`) y sont rangés par des chemins relatifs : déplacé, le dossier démarre sans eux. Le projet Docker
    Compose, lui, s'appelle toujours `readyroom`, quel que soit le dossier : la base ne se perd pas, mais ne lancez
    jamais deux copies de la Ready Room sur le même serveur.

## 4.2 · Télécharger la release { #download }

Sur la page des releases, <https://github.com/MirabelleBenou/dcs-squadron-ready-room/releases>, relevez le nom de la
dernière release (par exemple `RR-V1.0.0`), puis :

```sh
cd /opt/readyroom
curl -fL -o readyroom.tar.gz https://github.com/MirabelleBenou/dcs-squadron-ready-room/archive/refs/tags/<release>.tar.gz
tar -xzf readyroom.tar.gz --strip-components=1
rm readyroom.tar.gz
```

!!! note "Avec Git"
    Si vous préférez Git : `git clone --depth 1 --branch <release> https://github.com/MirabelleBenou/dcs-squadron-ready-room.git /opt/readyroom`
    (le dossier doit être vide).

!!! success "Vérifier"
    `cat VERSION` affiche le numéro de la release ; `ls` montre `docker-compose.yml`, `.env.example` (avec `ls -a`)
    et `init-env.sh`.

## 4.3 · Facultatif : Mission Plan et Mission Tools { #suites }

L'accueil de la Ready Room porte deux tuiles, **Mission Plan** et **Mission Tools**, les suites de préparation de
mission. Ce qu'elles ouvrent dépend de cette étape :

- **sans elle**, la version publique en ligne des suites : elle marche, mais ne connaît ni votre escadre ni ses
  escadrilles ;
- **avec elle**, les suites servies par la Ready Room, derrière sa connexion : elles reçoivent l'identité de l'escadre,
  ses escadrilles et leurs écussons.

Ce sont deux fichiers, ceux de la dernière release de chaque suite, à télécharger dans `data/suites` :

```sh
cd /opt/readyroom
mkdir -p data/suites
curl -fL -o data/suites/dcs_mission_plan.html https://github.com/MirabelleBenou/dcs-mission-plan/releases/latest/download/dcs_mission_plan.html
curl -fL -o data/suites/dcs_mission_tools.html https://github.com/MirabelleBenou/dcs-mission-tools/releases/latest/download/dcs_mission_tools.html
```

!!! success "Vérifier"
    `ls -lh data/suites` montre les deux fichiers, de plusieurs mégaoctets chacun.

!!! note
    Si vous placez ce dossier ailleurs (`SUITES_HOST_DIR`, [§5.5](05-configure.md#host-folders)), téléchargez les deux
    fichiers dans ce dossier-là. L'étape se fait aussi plus tard, sans redémarrer la Ready Room.

## 4.4 · Ce que contient le dossier { #contents }

| fichier ou dossier | à quoi il sert |
|---|---|
| `docker-compose.yml` | les deux conteneurs, `app` et `db`, et leurs volumes |
| `compose.caddy.yml` | le proxy HTTPS de l'option A (chapitre 6) |
| `.env.example` | le modèle du fichier de configuration |
| `init-env.sh` | écrit votre `.env` en posant les questions (chapitre 5) |
| `Dockerfile`, `entrypoint.sh`, `app/`, `alembic/`, `requirements.txt` | l'application elle-même, construite au premier démarrage |
| `VERSION`, `CHANGELOG.md` | le numéro de la release et ce qui a changé |
| `LICENSE`, `README.md` | la licence et la présentation |

Le démarrage créera à côté `backups/` (les sauvegardes) ; `data/` (les dossiers de l'hôte, [§5.5](05-configure.md#host-folders))
existe déjà si vous avez fait le [§4.3](#suites).
Ce guide n'est pas dans le dossier : il est en ligne et joint en PDF à chaque release.
