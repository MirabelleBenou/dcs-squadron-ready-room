# 15 · Uninstall { #uninstall }

This chapter removes the Ready Room from the server, from Discord and from the DCS server. Read it to the end before
you start: one step erases the database for good.

## 15.1 · Keep a last backup { #last-backup }

1. **Command Center › Archives › Back up now**.
2. Archive the raw uploads ([§11.2](11-backup-and-restore.md#raw-deposits)).
3. Copy `backups/` and `.env` off the server ([§11.3](11-backup-and-restore.md#off-server-copy)).

With them, a Ready Room reinstalled later ([chapters 4 to 7](04-get-the-ready-room.md#get-the-ready-room)) gets
everything back through [§11.4](11-backup-and-restore.md#restore-database) (database), [§11.5](11-backup-and-restore.md#restore-crests) (crests) and §11.5 again for the raw uploads.

## 15.2 · Stop the Ready Room { #stop }

```sh
cd /opt/readyroom
docker compose down
```

The containers stop and are removed; **the database and the volumes stay**. `docker compose up -d` starts it again as
it was.

Option B: also remove the Tailscale Funnel exposure:

```sh
sudo tailscale funnel reset
```

(This command removes every Funnel exposure on the machine: if you set up others, set them up again afterwards.)

## 15.3 · Erase the data { #delete-data }

!!! warning "Warning"
    What follows **erases the database, the crests and the raw uploads**, with no way back other than a backup copied
    off the server ([§15.1](#last-backup)).

```sh
cd /opt/readyroom
docker compose down -v
```

`-v` removes the Ready Room's volumes: `readyroom_pgdata`, `readyroom_crests`, `readyroom_debrief_raw`, and, for
option A, `readyroom_caddy_data` and `readyroom_caddy_config`.

Then remove the folder and the images:

```sh
cd /
sudo rm -rf /opt/readyroom
docker image prune -a
```

!!! note
    `docker image prune -a` removes every Docker image that no container uses, not only the Ready Room's. If other
    applications run under Docker on this server, skip this command.

!!! success "Check"
    `docker volume ls --filter name=readyroom` no longer lists anything.

## 15.4 · Remove the Discord application { #remove-discord-app }

1. In your Discord server, member list: right-click on the Ready Room's bot, **Kick** — the bot leaves the server and
   `/readyroom` disappears.
2. Delete the digest webhook, if there is one: **Edit Channel › Integrations › Webhooks**.
3. In the Developer Portal (<https://discord.com/developers/applications>), the application, **General Information**
   page, **Delete App** — only if you do not plan to reinstall: a deleted application cannot be recovered, and a
   reinstallation would mean doing chapter 3 again.

## 15.5 · Remove the agent from the DCS server { #remove-agent }

On the DCS server's PC: stop the sender, then remove the hook, as in [§10.6](10-dcs-agent.md#settings).

## 15.6 · Where you are { #where-you-are }

- [ ] A last backup and `.env` are copied off the server, if you want to be able to come back.
- [ ] `docker compose ps` no longer shows anything of the Ready Room.
- [ ] The bot has left your Discord server.
- [ ] The task **ReadyRoom - envoi** and `readyroom_agent.lua` are removed from the DCS server.
