# 6 · Expose the Ready Room over HTTPS { #https }

The application listens on the server itself, at `127.0.0.1:8000`, invisible from outside. This chapter connects the
HTTPS address set up in [§2.5](02-prepare-the-server.md#address) to that listener.

## 6.1 · Why HTTPS { #why-https }

Discord refuses an `http://` redirect address, and the Ready Room's session cookie is marked *Secure*: a browser only
sends it back over HTTPS. Without HTTPS, nobody can sign in.

## 6.2 · Option A — your domain name and Caddy { #option-a }

Caddy, shipped with the Ready Room (`compose.caddy.yml`), receives traffic on ports 80 and 443, obtains a Let's
Encrypt certificate for the name in `BASE_URL` by itself, and renews it. It starts with the Ready Room if `.env`
contains this line — `init-env.sh` wrote it if you chose option A:

```text
COMPOSE_FILE=docker-compose.yml:compose.caddy.yml
```

If it is missing, add it:

```sh
echo 'COMPOSE_FILE=docker-compose.yml:compose.caddy.yml' >> .env
```

There is nothing else to do before the first start. Just check that the name resolves
([§2.5](02-prepare-the-server.md#address)) and that ports 80 and 443 are open ([§2.2](02-prepare-the-server.md#firewall)),
including at your hosting provider if it has its own firewall.

!!! failure "If it does not work"
    In chapter 7, `docker compose logs caddy` shows a certificate error (*challenge failed*, *timeout*): the name does
    not point to this server yet, or port 80 is closed somewhere. Fix it, then `docker compose restart caddy`.

## 6.3 · Option B — Tailscale Funnel { #option-b }

Tailscale, installed in [§2.5](02-prepare-the-server.md#address), publishes the application's listener at
`https://<machine>.<tailnet>.ts.net`, with its certificate, without any open port:

```sh
sudo tailscale funnel --bg 8000
```

The first time, the command may print a link to the Tailscale console to allow Funnel on this machine: open it,
accept, then run the command again. The setting survives reboots.

```sh
tailscale funnel status
```

!!! success "Check"
    `funnel status` shows your `https://…ts.net` address (*Funnel on*) forwarding to `http://127.0.0.1:8000`.

!!! note "A delay at first"
    A new Funnel address can take a few minutes to become reachable from the Internet.

## 6.4 · Option C — a Cloudflare tunnel { #option-c }

The tunnel installed in [§2.5](02-prepare-the-server.md#address) must forward to `http://localhost:8000`. Two settings
matter for the Ready Room: keep the `X-Forwarded-For` and `X-Forwarded-Proto` headers, and do not buffer
`text/event-stream` responses (the schedule updates live through that stream). This guide does not go further into
this option.

## 6.5 · Check { #check-https }

The application is not running yet: the check is done at first start, in [§7.3](07-first-start.md#check-version).
