# 1 · Prerequisites { #prerequisites }

This chapter lists everything you need **before** installing the Squadron Ready Room: skills, accounts, the server, the
network address and — if you want to connect a DCS server — the Windows machine that runs it. Read it to the end and
tick the list in [§1.7](#checklist): the following chapters assume it is complete.

## 1.1 · Skills { #skills }

You do not need to be a developer. You need to be comfortable with:

- opening an SSH session on a Linux server and pasting commands into it;
- editing a text file on that server (`nano` is enough);
- administering the wing's Discord server, or working with the person who does: you will create roles, invite a bot
  and copy IDs.

## 1.2 · Accounts { #accounts }

| account | what it is for | required? |
|---|---|---|
| A **Discord server** where you have the *Manage Server* permission | members sign in with Discord; the Ready Room reads their roles on that server | yes |
| The **Discord Developer Portal** (your usual Discord account) | you create the Ready Room's Discord application there | yes |
| A **domain name** of your own, **or** a **Tailscale** account | to give the Ready Room a public HTTPS address ([§1.4](#network)) | one of the two |
| An **Anthropic API** account with **prepaid credit** | only to have mission report narratives written | no |

A GitHub account is **not** needed: the release is downloaded from its public page.

## 1.3 · The Ready Room server { #server }

The Ready Room runs as two containers — the application and its PostgreSQL 16 database — under Docker Compose, on a
single Linux machine that stays on: a small rented server (VPS), a virtual machine, or a computer at home.

### Hardware { #hardware }

| | minimum | comfortable |
|---|---|---|
| processor | 1 vCPU, 64-bit x86 (`x86_64`) | 2 vCPU |
| memory | 2 GB | 4 GB |
| disk | 20 GB free | 40 GB or more if your pilots upload many Tacview files (`.acmi`) |

The database stays small; what grows is the raw debriefing files and the backups the Ready Room takes by itself. Keep a
copy of the backups **off** the server (chapter 11).

!!! note "Other processors"
    64-bit ARM machines (Raspberry Pi 4 or 5, hosting providers' ARM servers) have not been tried. The images used
    exist for ARM: it may work, but without help from this guide.

### Operating system { #operating-system }

| system | status |
|---|---|
| **Debian 13** (trixie), 64-bit | **tried** — the Ready Room of its developers runs there |
| Debian 12 (bookworm), Ubuntu 24.04 LTS, Ubuntu 22.04 LTS, 64-bit | supported: same Docker packages, same steps (chapter 2) |
| another Linux distribution supported by Docker Engine | should work; the guide's commands are written for Debian and Ubuntu |
| Windows or macOS (Docker Desktop, WSL) | **not supported** for a server that must run day and night |

If you can, start from a fresh, up-to-date system, without a desktop environment.

### Software { #software }

You install it in chapter 2; nothing else is needed on the server:

- **Docker Engine** 24 or later, with the **Compose plugin** (`docker compose`, version 2), from Docker's package
  repository — not your distribution's older `docker.io` package;
- `curl` and `tar` (usually already there);
- `openssl`, to make the secrets (present on Debian and Ubuntu).

You need **neither** Python, **nor** PostgreSQL, **nor** a web server on the machine: all of that runs in the
containers.

### Access { #access }

An account with `sudo` rights on the server. Your account only needs `sudo` to install and to prepare the Ready Room
folder; after that, it drives it with `docker compose`.

## 1.4 · Network and the HTTPS address { #network }

The Ready Room must be reachable at **a public `https://` address**. Discord refuses to sign members in through a
plain `http://` address, and the Ready Room's session cookie only travels over HTTPS.

That address serves three parties:

- your members' browsers and phones;
- **Discord**, which calls the Ready Room back when a member clicks a button or types `/readyroom`;
- the **agent** on your DCS server, which sends its mission files (chapter 10).

Choose one of these options now. You will set it up in [§2.5](02-prepare-the-server.md#address), before Discord, which
needs it, and chapter 6 will connect it to the Ready Room:

| option | what you need | ports to open on the server |
|---|---|---|
| **A — your domain name** and the Caddy proxy shipped with the Ready Room (automatic certificate) | a domain or subdomain (for example `readyroom.example.org`) pointing to the server | 80 and 443 (TCP), 443/UDP |
| **B — Tailscale Funnel** (no domain, no open port) | a free Tailscale account; the address looks like `https://<machine>.<tailnet>.ts.net` | none |
| C — a Cloudflare tunnel | a domain managed by Cloudflare | none |

This guide describes these three options; they are not the only ones. Any other means will do — another proxy, another
tunnel — as long as it serves the application, which listens on `127.0.0.1:8000`, over HTTPS at a public address.

In every case, keep SSH (port 22, or yours) open for yourself.

!!! warning "Warning"
    **Choose the address for good.** It is written into the Ready Room's configuration, into the Discord application
    and, later, into the DCS server's agent. Changing it is possible, but it must then be changed everywhere.

### Outbound connections { #outbound }

The server must be able to reach, over HTTPS:

- while **building** the application (first start and every update): Docker Hub, the Debian package mirrors,
  `apt.postgresql.org` and `www.postgresql.org` (the PostgreSQL client), the Python package index (`pypi.org`,
  `files.pythonhosted.org`); `github.com` and its download domains, `codeload.github.com` and
  `*.githubusercontent.com` (the release and the suites);
- while **running**: `discord.com` and `cdn.discordapp.com`; `maps.dcsolympus.com` (the DCS map tiles, served by
  default); if needed, `api.anthropic.com` (report narratives).

## 1.5 · The DCS server (for the agent) { #dcs-server }

This part is **optional**: the Ready Room works without it, and your pilots can always upload their debriefing files
themselves. The agent is meant for the machine that runs the wing's DCS server: it records each mission and sends the
file to the Ready Room.

| | requirement |
|---|---|
| system | the Windows that runs your DCS server: **Windows 10 or 11, 64-bit**, or Windows Server — the agent adds no requirement to DCS's own |
| DCS World | a dedicated server, or a client hosting the missions |
| PowerShell | Windows PowerShell **5.1**, built into these systems — nothing to install |
| rights | an administrator account **once**, to register the upload task; the task then runs as the account that runs DCS |
| upload at shutdown (optional) | the Local Group Policy Editor (`gpedit.msc`): **Pro**, Enterprise, Education or Server editions — not Home |
| network | outbound HTTPS to the Ready Room's address ([§1.4](#network)); nothing inbound |

!!! warning "In this release"
    The agent is not published yet: it will come with its own first release, `RRA-V1.0.0`
    ([chapter 10](10-dcs-agent.md)). The Ready Room already **stores** the files an agent sends, but does not yet build
    debriefings from them: that comes in a later release.

## 1.6 · Optional services { #optional-services }

All of them are switched on **after** installation, in **Command Center › Configuration**, without restarting:

| feature | what you need | without it |
|---|---|---|
| the weekly schedule digest in a Discord channel | a webhook on that channel ([§3.7](03-discord-application.md#webhook)) | nothing is posted |
| attendance buttons in Discord, the `/readyroom` command, the member roll call | the *Server Members Intent* switch and the interactions address of the bot ([§3.4](03-discord-application.md#bot)) | members reply on the web page only |
| mission report narratives | an Anthropic API key with prepaid credit | reports keep their facts; no narrative is written |
| Mission Plan and Mission Tools served by the Ready Room | the two HTML files, placed in a server folder ([§5.5](05-configure.md#host-folders)) | the tiles open the public versions |

The bot itself is not optional: its token is required to link roles (chapter 8, [§7.6](07-first-start.md#discord-settings)).

!!! note "Time zone"
    The Ready Room counts its days and hours in **the wing's time zone** — Europe/Paris by default. You will set it at
    first start ([§7.5](07-first-start.md#time-zone)).

## 1.7 · Checklist { #checklist }

Tick each line before moving on to chapter 2.

- [ ] An SSH session opens on the server, with an account that has `sudo`.
- [ ] The server runs Debian 12 or 13, or Ubuntu 22.04 or 24.04, 64-bit, with at least 2 GB of memory and 20 GB of
      free disk.
- [ ] The *Manage Server* permission on the wing's Discord server is at hand (yours, or that of the person working
      with you).
- [ ] The Discord account that will create the application signs in to the Developer Portal.
- [ ] The means of making the Ready Room reachable over HTTPS is chosen (A, B, C, or another, [§1.4](#network)), and
      what it needs is ready.
- [ ] The server reaches the Internet over HTTPS ([§1.4](#outbound)).
- [ ] *(optional)* The administrator of the DCS server's Windows machine is known, and the machine meets
      [§1.5](#dcs-server).
- [ ] *(optional)* An Anthropic API key, with credit, is ready for narratives.
