# 1 · Les prérequis { #prerequisites }

Ce chapitre dit tout ce qu'il faut **avant** d'installer la Squadron Ready Room : les compétences, les comptes, le
serveur, l'adresse réseau et — si vous voulez brancher un serveur DCS — la machine Windows qui le fait tourner.
Lisez-le jusqu'au bout et cochez la liste du [§1.7](#checklist) : les chapitres suivants la supposent complète.

## 1.1 · Les compétences { #skills }

Il n'est pas nécessaire d'être développeur. Il faut être à l'aise pour :

- ouvrir une session SSH sur un serveur Linux et y coller des commandes ;
- modifier un fichier texte sur ce serveur (`nano` suffit) ;
- administrer le serveur Discord de l'escadre, ou travailler avec la personne qui le fait : vous créerez des rôles,
  inviterez un bot et copierez des identifiants.

## 1.2 · Les comptes { #accounts }

| compte | à quoi il sert | obligatoire ? |
|---|---|---|
| Un **serveur Discord** où vous avez la permission *Gérer le serveur* | les membres se connectent avec Discord ; la Ready Room lit leurs rôles sur ce serveur | oui |
| Le **portail développeur de Discord** (votre compte Discord habituel) | vous y créez l'application Discord de la Ready Room | oui |
| Un **nom de domaine** à vous, **ou** un compte **Tailscale** | pour donner à la Ready Room une adresse HTTPS publique ([§1.4](#network)) | l'un des deux |
| Un compte **API Anthropic** avec du **crédit prépayé** | seulement pour faire rédiger le récit des rapports de mission | non |

Un compte GitHub n'est **pas** nécessaire : la release se télécharge depuis sa page publique.

## 1.3 · Le serveur de la Ready Room { #server }

La Ready Room tourne en deux conteneurs — l'application et sa base PostgreSQL 16 — sous Docker Compose, sur une seule
machine Linux qui reste allumée : un petit serveur loué (VPS), une machine virtuelle ou un ordinateur à la maison.

### Le matériel { #hardware }

| | minimum | confortable |
|---|---|---|
| processeur | 1 vCPU, x86 64 bits (`x86_64`) | 2 vCPU |
| mémoire | 2 Go | 4 Go |
| disque | 20 Go libres | 40 Go ou plus si vos pilotes déposent beaucoup de fichiers Tacview (`.acmi`) |

La base reste petite ; ce qui grossit, ce sont les fichiers bruts des débriefings et les sauvegardes que la Ready Room
prend d'elle-même. Gardez une copie des sauvegardes **hors** du serveur (chapitre 11).

!!! note "Les autres processeurs"
    Les machines ARM 64 bits (Raspberry Pi 4 ou 5, serveurs ARM des hébergeurs) n'ont pas été essayées. Les images
    utilisées existent pour ARM : cela peut marcher, mais sans aide de ce guide.

### Le système d'exploitation { #operating-system }

| système | statut |
|---|---|
| **Debian 13** (trixie), 64 bits | **essayé** — c'est là que tourne la Ready Room de ceux qui la développent |
| Debian 12 (bookworm), Ubuntu 24.04 LTS, Ubuntu 22.04 LTS, 64 bits | pris en charge : mêmes paquets Docker, mêmes gestes (chapitre 2) |
| une autre distribution Linux prise en charge par Docker Engine | devrait marcher ; les commandes du guide sont écrites pour Debian et Ubuntu |
| Windows ou macOS (Docker Desktop, WSL) | **non pris en charge** pour un serveur qui doit tourner jour et nuit |

Prenez si possible un système neuf et à jour, sans environnement graphique.

### Les logiciels { #software }

Vous les installez au chapitre 2 ; il ne faut rien d'autre sur le serveur :

- **Docker Engine** 24 ou plus récent, avec le **greffon Compose** (`docker compose`, version 2), depuis le dépôt de
  paquets de Docker — pas le paquet `docker.io`, plus ancien, de votre distribution ;
- `curl` et `tar` (en général déjà présents) ;
- `openssl`, pour fabriquer les secrets (présent sur Debian et Ubuntu).

Il ne faut **ni** Python, **ni** PostgreSQL, **ni** serveur web sur la machine : tout cela tourne dans les conteneurs.

### L'accès { #access }

Un compte qui a les droits `sudo` sur le serveur. Votre compte n'a besoin de `sudo` que pour installer et pour
préparer le dossier de la Ready Room ; ensuite, il la pilote par `docker compose`.

## 1.4 · Le réseau et l'adresse HTTPS { #network }

La Ready Room doit être joignable à **une adresse publique en `https://`**. Discord refuse de connecter les membres
par une adresse en `http://` simple, et le cookie de session de la Ready Room ne voyage qu'en HTTPS.

Cette adresse sert à trois acteurs :

- les navigateurs et téléphones de vos membres ;
- **Discord**, qui rappelle la Ready Room quand un membre clique un bouton ou tape `/readyroom` ;
- l'**agent** de votre serveur DCS, qui envoie ses fichiers de mission (chapitre 10).

Choisissez dès maintenant l'une de ces options. Vous l'établirez au [§2.5](02-prepare-the-server.md#address), avant
Discord, qui en a besoin, et le chapitre 6 la branchera sur la Ready Room :

| option | il vous faut | ports à ouvrir sur le serveur |
|---|---|---|
| **A — votre nom de domaine** et le proxy Caddy fourni avec la Ready Room (certificat automatique) | un domaine ou sous-domaine (par exemple `readyroom.example.org`) qui pointe vers le serveur | 80 et 443 (TCP), 443/UDP |
| **B — Tailscale Funnel** (ni domaine, ni port ouvert) | un compte Tailscale gratuit ; l'adresse ressemble à `https://<machine>.<tailnet>.ts.net` | aucun |
| C — un tunnel Cloudflare | un domaine géré par Cloudflare | aucun |

Ce guide décrit ces trois options ; elles ne sont pas les seules. Tout autre moyen convient — un autre proxy, un autre
tunnel —, s'il sert en HTTPS, à une adresse publique, l'application qui écoute sur `127.0.0.1:8000`.

Dans tous les cas, gardez SSH (port 22, ou le vôtre) ouvert pour vous.

!!! warning "Attention"
    **Choisissez l'adresse pour de bon.** Elle est écrite dans la configuration de la Ready Room, dans l'application
    Discord et, plus tard, chez l'agent du serveur DCS. En changer reste possible, mais il faut la changer partout.

### Les connexions sortantes { #outbound }

Le serveur doit pouvoir joindre, en HTTPS :

- pendant la **construction** de l'application (premier démarrage et chaque mise à jour) : Docker Hub, les miroirs de
  paquets Debian, `apt.postgresql.org` et `www.postgresql.org` (le client PostgreSQL), l'index des paquets Python
  (`pypi.org`, `files.pythonhosted.org`) ; `github.com` et ses domaines de téléchargement, `codeload.github.com` et
  `*.githubusercontent.com` (la release et les suites) ;
- pendant le **fonctionnement** : `discord.com` et `cdn.discordapp.com` ; `maps.dcsolympus.com` (les tuiles de la
  carte DCS, servies par défaut) ; au besoin `api.anthropic.com` (récits des rapports).

## 1.5 · Le serveur DCS (pour l'agent) { #dcs-server }

Cette partie est **facultative** : la Ready Room marche sans elle, et vos pilotes peuvent toujours déposer eux-mêmes
leurs fichiers de débriefing. L'agent est fait pour la machine qui fait tourner le serveur DCS de l'escadre : il
enregistre chaque mission et envoie le fichier à la Ready Room.

| | exigence |
|---|---|
| système | le Windows qui fait tourner votre serveur DCS : **Windows 10 ou 11, 64 bits**, ou Windows Server — l'agent n'ajoute aucune exigence à celles de DCS |
| DCS World | un serveur dédié, ou un client qui héberge les missions |
| PowerShell | Windows PowerShell **5.1**, intégré à ces systèmes — rien à installer |
| droits | un compte administrateur **une fois**, pour enregistrer la tâche d'envoi ; la tâche tourne ensuite avec le compte qui fait tourner DCS |
| envoi à l'extinction (facultatif) | l'éditeur de stratégie de groupe locale (`gpedit.msc`) : éditions **Pro**, Entreprise, Éducation ou Server — pas Famille |
| réseau | HTTPS sortant vers l'adresse de la Ready Room ([§1.4](#network)) ; rien d'entrant |

!!! warning "Dans cette release"
    L'agent n'est pas encore publié : il viendra avec sa propre première release, `RRA-V1.0.0`
    ([chapitre 10](10-dcs-agent.md)). La Ready Room **range** déjà les fichiers qu'un agent envoie, mais n'en tire pas
    encore de débriefing : cela viendra dans une release suivante.

## 1.6 · Les services facultatifs { #optional-services }

Tous s'allument **après** l'installation, à l'écran **Centre de Commandement › Configuration**, sans redémarrer :

| fonction | il vous faut | sans elle |
|---|---|---|
| le digest hebdomadaire du planning dans un salon Discord | un webhook sur ce salon ([§3.7](03-discord-application.md#webhook)) | rien n'est posté |
| les boutons de présence dans Discord, la commande `/readyroom`, l'appel des membres | l'interrupteur *Server Members Intent* et l'adresse des interactions du bot ([§3.4](03-discord-application.md#bot)) | les membres répondent sur la page web seulement |
| le récit des rapports de mission | une clé API Anthropic avec du crédit prépayé | les rapports gardent leurs faits ; le récit n'est pas rédigé |
| Mission Plan et Mission Tools servis par la Ready Room | les deux fichiers HTML, posés dans un dossier du serveur ([§5.5](05-configure.md#host-folders)) | les tuiles ouvrent les versions publiques |

Le bot lui-même n'est pas facultatif : son jeton est obligatoire pour relier les rôles (chapitre 8, [§7.6](07-first-start.md#discord-settings)).

!!! note "Le fuseau horaire"
    La Ready Room compte ses jours et ses heures dans **le fuseau de l'escadre** — Europe/Paris par défaut. Vous le
    réglerez dès le premier démarrage ([§7.5](07-first-start.md#time-zone)).

## 1.7 · La liste à cocher { #checklist }

Cochez chaque ligne avant de passer au chapitre 2.

- [ ] Une session SSH s'ouvre sur le serveur, avec un compte qui a `sudo`.
- [ ] Le serveur tourne sous Debian 12 ou 13, ou Ubuntu 22.04 ou 24.04, en 64 bits, avec au moins 2 Go de mémoire et
      20 Go de disque libre.
- [ ] La permission *Gérer le serveur* du serveur Discord de l'escadre est acquise (la vôtre, ou celle de la personne
      qui vous accompagne).
- [ ] Le compte Discord qui créera l'application se connecte au portail développeur.
- [ ] Le moyen de rendre la Ready Room joignable en HTTPS est choisi (A, B, C, ou un autre, [§1.4](#network)), et ce
      qu'il demande est prêt.
- [ ] Le serveur joint Internet en HTTPS ([§1.4](#outbound)).
- [ ] *(facultatif)* L'administrateur de la machine Windows du serveur DCS est connu, et la machine remplit le
      [§1.5](#dcs-server).
- [ ] *(facultatif)* Une clé de l'API Anthropic, avec du crédit, est prête pour les récits.
