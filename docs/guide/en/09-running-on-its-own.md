# 9 · What runs on its own { #running-on-its-own }

The Ready Room needs no scheduled task on the server: no `cron`, no timer. Three jobs run inside the application
itself, as long as the `app` container is up. This chapter says which ones, when, and how to check that they ran.

## 9.1 · The roll call { #roll-call-schedule }

The roll call ([§8.4](08-first-settings.md#roll-call)) starts **one minute after each start**, then **every 24
hours**. It counts by interval, not at a fixed time: a restart shifts it. At the end of each successful roll call, the
**planning reminders** ([§8.5](08-first-settings.md#rights)) go out to their recipients.

## 9.2 · The daily 6 a.m. pass { #daily-pass }

Every day at **6 a.m. in the wing's time zone** ([§7.5](07-first-start.md#time-zone)), daylight saving included, the
Ready Room refreshes its messages in Discord: the digest, or the attendance messages if **Replies in Discord** is on
([§7.6](07-first-start.md#discord-settings)). It also does so at each start, and the digest follows every change to
the schedule without waiting for the next day.

## 9.3 · Automatic backups { #automatic-backups }

**Command Center › Archives**, block **Backups**, line **Automatic backup**, two lists:

1. the frequency: **Every 24 h** by default; also 6, 12 or 48 hours, **Every 7 days**, or **Off**;
2. the retention: **Keep the last 7** by default; also 3, 14 or 30.

The choice is saved at once. Every hour, the Ready Room checks the age of the last automatic backup, and takes one
when the interval has passed; the oldest one beyond the retention is deleted. A backup takes **the database and the
crests**, like the **Back up now** button; what it does not take is in
[§11.1](11-backup-and-restore.md#what-a-backup-holds).

!!! warning "Warning"
    **Off** leaves only the backups you take by hand and those taken before each migration. Do not switch it off
    without another backup of the machine.

## 9.4 · Check that they ran { #check-tasks }

| job | on screen | in the log |
|---|---|---|
| the roll call | **Members**: "Last roll call · *date* · *time*" | `Appel (demarrage) : …`, then `Appel (quotidien) : …` |
| the 6 a.m. pass | your Discord messages, up to date in the morning | `roll: … posted, … edited, … deleted` (attendance messages only) |
| backups | **Archives**: "Last: *date* · *time*", and a line of origin **Automatic** in the list | `Sauvegarde automatique : …` |

To read the log:

```sh
cd /opt/readyroom
docker compose logs --since 48h app | grep -E "Appel \(|roll:|Sauvegarde automatique"
```

!!! failure "If it does not work"
    - **Archives** shows "Last attempt failed (…): …": the reason follows; most often, the disk is full (`df -h`).
    - No `Appel (…)` line for more than a day: `docker compose ps` — `app` must be `Up`; otherwise, see
      [§7.2](07-first-start.md#logs).
    - The log shows `Passage quotidien Discord : erreur non bloquante`: the pass failed that day; the reason follows,
      on the next lines. The next day's pass runs normally.

## 9.5 · Run them by hand { #manual-triggers }

All three jobs can also be run by hand:

- **the roll call**: **Members › Call the roll**;
- **a backup**: **Archives › Back up now**;
- **the Discord messages**, without waiting for 6 a.m.: a command, from the server, protected by a token.

The token is set once: **Configuration › Server settings**, group **Discord — digest**, **Manual update token**,
**Enter**, a long random string that you keep (for example `openssl rand -hex 32`), **Save**. Left empty, manual
updates are refused; the 6 a.m. pass does not need it. Both commands are in [appendix C](c-commands.md#discord-triggers).

!!! success "Check"
    The command prints `204` and the Discord messages are up to date. `403`: the token is not the one saved.

## 9.6 · Where you are { #where-you-are }

- [ ] **Members** shows a last roll call less than 24 hours old.
- [ ] **Archives** shows the frequency and retention you want, and a first **Automatic** backup.
- [ ] *(optional)* The manual update token is saved and kept.

Chapter 10 connects your DCS server.
