# 14 · Sécurité et données { #security }

Ce chapitre dit ce que la Ready Room expose, quels secrets la protègent et comment les changer, ce qu'elle garde et
ce qui part vers d'autres services.

## 14.1 · Ce qui est exposé { #exposed }

- **Une seule adresse HTTPS**, celle du chapitre 6. L'application elle-même n'écoute que sur `127.0.0.1:8000` : elle
  n'est joignable que par le proxy HTTPS du même serveur. La base n'a aucun port ouvert.
- **On n'entre que par Discord** : un compte du serveur Discord de l'escadre, avec un rôle qui ouvre l'accès
  ([§8.1](08-first-settings.md#app-access)), ou un administrateur fondateur. Sans session, on ne voit que la page de
  connexion.
- **La documentation automatique de l'API est fermée** : rien ne décrit l'API à un visiteur.
- **Les invités** voient en lecture seule, trente jours au plus sans prolongation
  ([§8.6](08-first-settings.md#guests-and-rescue-link)).
- **Le lien de connexion de secours** ouvre une session une seule fois, pendant 24 heures ; le lien de `/readyroom`,
  cinq minutes.
- **L'agent du serveur DCS** n'entre que par son jeton, et ne peut que déposer des fichiers.

## 14.2 · Les secrets et leur rotation { #secrets }

| secret | où il vit | le changer | effet |
|---|---|---|---|
| `SESSION_SECRET` | `.env` | nouvelle valeur ([§5.2](05-configure.md#required-variables)), puis `docker compose up -d --force-recreate app` | toutes les sessions se ferment : chacun se reconnecte |
| `CONFIG_KEY` | `.env` | nouvelle clé ([§5.4](05-configure.md#config-key)), puis `docker compose up -d --force-recreate app` | les secrets de **Configuration** deviennent illisibles : ressaisissez-les |
| `POSTGRES_PASSWORD` | `.env` | ne le changez pas après le premier démarrage | la base garde celui de sa création : l'application ne s'y connecterait plus |
| jeton du bot | **Configuration** | portail Discord, page **Bot**, **Reset Token**, puis **Configuration › Jeton du bot** | le nouveau sert aussitôt ; l'ancien ne vaut plus rien |
| *Client Secret* | `.env` | portail Discord, page **OAuth2**, **Reset Secret**, puis `.env` et `docker compose up -d --force-recreate app` | la connexion Discord reprend avec le nouveau |
| jeton des mises à jour manuelles | **Configuration** | **Configuration**, groupe **Discord — le digest** | vos scripts doivent porter le nouveau |
| jeton de l'agent | **Archives › Serveur DCS** | **Remplacer le jeton** ([§10.3](10-dcs-agent.md#agent-token)) | l'ancien cesse aussitôt ; reportez le nouveau dans `readyroom_envoi.json` |

!!! warning "Attention"
    Un secret qui a fui se change **tout de suite**, dans l'ordre de ce tableau. Un `.env` publié par erreur (un dépôt,
    une capture d'écran, un message) les a tous fait fuir : changez-les tous.

## 14.3 · Les données gardées { #data-kept }

La Ready Room garde, dans sa base :

- **pour chaque membre** : son identifiant Discord, son nom d'utilisateur et son nom affiché, son avatar, ses rôles au
  dernier relevé, son escadrille, ses dates de première et de dernière connexion, ses préférences (langue, appareils) ;
- **son activité** : ses réponses au planning, ses vols et ses missions dans les rapports ;
- **les fichiers de débriefing** déposés par les pilotes ou envoyés par l'agent, qui portent les noms des joueurs
  connectés.

Un membre qui perd l'accès sort de l'effectif à l'appel suivant : son profil est **archivé**, pas effacé — ses vols et
ses missions restent dans l'historique de l'escadre (**Archives › Membres archivés**).

## 14.4 · Ce qui part vers d'autres services { #third-parties }

| service | quand | quoi |
|---|---|---|
| **Discord** | toujours | la connexion des membres ; l'appel (membres et rôles du serveur) ; les messages du bot et du webhook dans vos salons |
| **Anthropic** | seulement si le Récit est réglé ([§8.7](08-first-settings.md#optional-settings)) | la fiche de chaque mission à raconter — indicatifs des pilotes, appareils, évènements — pour que le modèle en rédige le récit |
| **le serveur de tuiles** (DCS Olympus par défaut) | seulement pour une tuile absente du serveur | l'adresse de la tuile demandée, depuis l'adresse de votre serveur |
| **Let's Encrypt** | option A seulement | le nom de domaine, pour le certificat |

Aucun autre service ne reçoit rien : ni statistique d'usage, ni télémétrie.

## 14.5 · Tenir le serveur à jour { #keep-updated }

- **Le système** : appliquez les mises à jour de sécurité de votre distribution (sur Debian ou Ubuntu,
  `sudo apt update && sudo apt upgrade`), et redémarrez quand elles le demandent.
- **Docker** : il se met à jour avec le système s'il vient du dépôt de Docker ([§2.3](02-prepare-the-server.md#install-docker)).
- **L'image de la base** (`postgres:16`) : `docker compose pull db`, puis `docker compose up -d` ; la base reste dans son
  volume.
- **La Ready Room** : chaque release ([chapitre 12](12-update.md#update)).
- **L'accès SSH** : par clé plutôt que par mot de passe.

## 14.6 · Où vous en êtes { #where-you-are }

- [ ] `.env` n'est lisible que par vous (`ls -l .env` : `-rw-------`), et sa copie est rangée à part ([§11.3](11-backup-and-restore.md#off-server-copy)).
- [ ] Les mises à jour de sécurité du système s'appliquent.
