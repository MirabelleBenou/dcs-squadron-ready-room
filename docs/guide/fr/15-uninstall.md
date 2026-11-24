# 15 · Désinstaller { #uninstall }

Ce chapitre retire la Ready Room du serveur, de Discord et du serveur DCS. Lisez-le jusqu'au bout avant de commencer :
une étape efface la base pour de bon.

## 15.1 · Garder une dernière sauvegarde { #last-backup }

1. **Centre de Commandement › Archives › Sauvegarder maintenant**.
2. Copiez `backups/` et `.env` hors du serveur ([§11.3](11-backup-and-restore.md#off-server-copy)).

Avec elles, une Ready Room réinstallée plus tard ([chapitres 4 à 7](04-get-the-ready-room.md#get-the-ready-room))
retrouve tout par la restauration du [§11.4](11-backup-and-restore.md#restore-database).

## 15.2 · Arrêter la Ready Room { #stop }

```sh
cd /opt/readyroom
docker compose down
```

Les conteneurs s'arrêtent et sont retirés ; **la base et les volumes restent**. `docker compose up -d` la relance telle
qu'elle était.

Option B : retirez aussi l'exposition par Tailscale Funnel :

```sh
sudo tailscale funnel reset
```

(Cette commande retire toute exposition Funnel de la machine : si vous en avez posé d'autres, refaites-les ensuite.)

## 15.3 · Effacer les données { #delete-data }

!!! warning "Attention"
    Ce qui suit **efface la base, les écussons et les dépôts bruts**, sans retour possible autrement que par une
    sauvegarde copiée hors du serveur ([§15.1](#last-backup)).

```sh
cd /opt/readyroom
docker compose down -v
```

`-v` retire les volumes de la Ready Room : `readyroom_pgdata`, `readyroom_crests`, `readyroom_debrief_raw`, et, pour
l'option A, `readyroom_caddy_data` et `readyroom_caddy_config`.

Puis retirez le dossier et les images :

```sh
cd /
sudo rm -rf /opt/readyroom
docker image prune -a
```

!!! note
    `docker image prune -a` retire toutes les images Docker qui ne servent à aucun conteneur, pas seulement celles de
    la Ready Room. Si d'autres applications tournent sous Docker sur ce serveur, sautez cette commande.

!!! success "Vérifier"
    `docker volume ls --filter name=readyroom` ne liste plus rien.

## 15.4 · Retirer l'application Discord { #remove-discord-app }

1. Dans votre serveur Discord, liste des membres : clic droit sur le bot de la Ready Room, **Expulser** — le bot quitte
   le serveur et `/readyroom` disparaît.
2. Supprimez le webhook du digest, s'il existe : **Paramètres du salon › Intégrations › Webhooks**.
3. Au portail développeur (<https://discord.com/developers/applications>), l'application, page **General
   Information**, **Delete App** — seulement si vous ne comptez pas réinstaller : une application supprimée ne se
   récupère pas, et une réinstallation demanderait de refaire le chapitre 3.

## 15.5 · Retirer l'agent du serveur DCS { #remove-agent }

Sur le PC du serveur DCS : arrêtez l'envoi, puis retirez le hook, comme au [§10.6](10-dcs-agent.md#settings).

## 15.6 · Où vous en êtes { #where-you-are }

- [ ] Une dernière sauvegarde et `.env` sont copiés hors du serveur, si vous voulez pouvoir revenir.
- [ ] `docker compose ps` ne montre plus rien de la Ready Room.
- [ ] Le bot a quitté votre serveur Discord.
- [ ] La tâche **ReadyRoom - envoi** et `readyroom_agent.lua` sont retirés du serveur DCS.
