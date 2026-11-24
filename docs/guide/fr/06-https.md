# 6 · Rendre la Ready Room joignable en HTTPS { #https }

L'application écoute sur le serveur lui-même, à `127.0.0.1:8000`, invisible de l'extérieur. Ce chapitre branche
l'adresse HTTPS établie au [§2.5](02-prepare-the-server.md#address) sur cette écoute.

## 6.1 · Pourquoi HTTPS { #why-https }

Discord refuse une adresse de retour en `http://`, et le cookie de session de la Ready Room est marqué *Secure* : un
navigateur ne le renvoie qu'en HTTPS. Sans HTTPS, personne ne peut se connecter.

## 6.2 · Option A — votre nom de domaine et Caddy { #option-a }

Caddy, fourni avec la Ready Room (`compose.caddy.yml`), reçoit le trafic sur les ports 80 et 443, obtient seul un
certificat Let's Encrypt pour le nom de `BASE_URL` et le renouvelle. Il démarre avec la Ready Room si `.env` contient
cette ligne — `init-env.sh` l'a écrite si vous avez choisi l'option A :

```text
COMPOSE_FILE=docker-compose.yml:compose.caddy.yml
```

Si elle manque, ajoutez-la :

```sh
echo 'COMPOSE_FILE=docker-compose.yml:compose.caddy.yml' >> .env
```

Il n'y a rien d'autre à faire avant le premier démarrage. Vérifiez seulement que le nom répond
([§2.5](02-prepare-the-server.md#address)) et que les ports 80 et 443 sont ouverts ([§2.2](02-prepare-the-server.md#firewall)),
y compris chez votre hébergeur s'il a son propre pare-feu.

!!! failure "Si ça ne marche pas"
    Au chapitre 7, `docker compose logs caddy` montre une erreur de certificat (*challenge failed*, *timeout*) : le
    nom ne pointe pas encore vers ce serveur, ou le port 80 est fermé quelque part. Corrigez, puis
    `docker compose restart caddy`.

## 6.3 · Option B — Tailscale Funnel { #option-b }

Tailscale, installé au [§2.5](02-prepare-the-server.md#address), publie l'écoute de l'application à l'adresse
`https://<machine>.<tailnet>.ts.net`, avec son certificat, sans port ouvert :

```sh
sudo tailscale funnel --bg 8000
```

La première fois, la commande peut afficher un lien vers la console de Tailscale pour autoriser Funnel sur cette
machine : ouvrez-le, acceptez, puis relancez la commande. Le réglage survit aux redémarrages.

```sh
tailscale funnel status
```

!!! success "Vérifier"
    `funnel status` montre votre adresse `https://…ts.net` (*Funnel on*) qui renvoie vers `http://127.0.0.1:8000`.

!!! note "Un délai au début"
    Une adresse Funnel neuve peut mettre quelques minutes à être joignable depuis Internet.

## 6.4 · Option C — un tunnel Cloudflare { #option-c }

Le tunnel installé au [§2.5](02-prepare-the-server.md#address) doit renvoyer vers `http://localhost:8000`. Deux
réglages comptent pour la Ready Room : garder les en-têtes `X-Forwarded-For` et `X-Forwarded-Proto`, et ne pas
mettre en tampon les réponses `text/event-stream` (le planning se met à jour en direct par ce flux). Ce guide ne
détaille pas plus cette option.

## 6.5 · Vérifier { #check-https }

L'application ne tourne pas encore : la vérification se fait au premier démarrage, au
[§7.3](07-first-start.md#check-version).
