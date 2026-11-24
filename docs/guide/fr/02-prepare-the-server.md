# 2 · Préparer le serveur { #prepare-the-server }

Ce chapitre met le système à jour, ferme le pare-feu, installe Docker et établit l'adresse HTTPS de la Ready Room.
Toutes les commandes se tapent dans une session SSH sur le serveur.

## 2.1 · Mettre le système à jour { #update-system }

```sh
sudo apt update && sudo apt full-upgrade -y
```

Si la mise à jour a changé le noyau, redémarrez (`sudo reboot`) et rouvrez la session SSH.

!!! note "Un compte d'administration"
    Si vous êtes connecté en `root`, créez d'abord un compte à vous et donnez-lui `sudo`, puis travaillez avec lui :
    ```sh
    adduser <nom>
    usermod -aG sudo <nom>
    ```

## 2.2 · Le pare-feu { #firewall }

```sh
sudo apt install -y ufw
sudo ufw allow OpenSSH
```

**Option A seulement** (votre nom de domaine et Caddy), ouvrez aussi le web :

```sh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
```

Puis allumez le pare-feu :

```sh
sudo ufw enable
sudo ufw status
```

!!! success "Vérifier"
    `ufw status` montre `Status: active`, `OpenSSH` en `ALLOW`, et pour l'option A, `80/tcp`, `443/tcp` et `443/udp`.

!!! warning "Attention"
    Docker ouvre lui-même les ports que publient ses conteneurs, **sans passer par `ufw`**. La Ready Room ne publie son
    application que sur `127.0.0.1:8000`, invisible de l'extérieur : ne changez jamais cette ligne de
    `docker-compose.yml`.

## 2.3 · Installer Docker { #install-docker }

Installez Docker depuis **le dépôt de paquets de Docker**, pas le paquet `docker.io` de la distribution (son greffon
Compose est absent ou ancien). Retirez d'abord ce qui pourrait gêner (sans effet si rien n'est installé) :

```sh
for p in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt remove -y $p; done
```

=== "Debian"

    ```sh
    sudo apt install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

=== "Ubuntu"

    ```sh
    sudo apt install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    ```

Donnez ensuite à votre compte le droit de piloter Docker, puis **fermez et rouvrez la session SSH** pour qu'il prenne
effet :

```sh
sudo usermod -aG docker $USER
```

!!! warning "Attention"
    Le groupe `docker` vaut les droits de `root` sur la machine. Ne l'accordez qu'aux comptes qui administrent le
    serveur.

## 2.4 · Vérifier Docker { #check-docker }

```sh
docker run --rm hello-world
docker compose version
```

!!! success "Vérifier"
    La première commande affiche `Hello from Docker!` ; la seconde, `Docker Compose version v2.` suivi d'un numéro.

!!! failure "Si ça ne marche pas"
    `permission denied … docker.sock` : la session SSH n'a pas été rouverte après le `usermod` du §2.3.
    `docker: 'compose' is not a docker command` : le paquet `docker-compose-plugin` manque ; reprenez le §2.3.

## 2.5 · Établir l'adresse HTTPS { #address }

Discord (chapitre 3) et la configuration (chapitre 5) ont besoin de l'adresse définitive de la Ready Room. Établissez-la
maintenant, selon l'option choisie au [§1.4](01-prerequisites.md#network). Notez-la : c'est `https://<adresse>` dans
la suite du guide, **sans `/` final**.

=== "A — nom de domaine"

    Chez votre fournisseur de domaine, créez un enregistrement **A** (et **AAAA** si le serveur a une adresse IPv6) qui
    fait pointer le nom choisi (par exemple `readyroom.example.org`) vers l'adresse IP publique du serveur. Pour lire
    cette adresse :

    ```sh
    curl -4 -s https://ifconfig.me ; echo
    ```

    Attendez que le nom réponde (de quelques minutes à quelques heures) :

    ```sh
    getent hosts <nom choisi>
    ```

    L'adresse de la Ready Room est `https://<nom choisi>`. Le certificat viendra tout seul au premier démarrage
    (chapitre 7).

=== "B — Tailscale Funnel"

    Installez Tailscale et rattachez le serveur à votre compte (la commande affiche un lien à ouvrir dans un
    navigateur) :

    ```sh
    curl -fsSL https://tailscale.com/install.sh | sh
    sudo tailscale up
    ```

    Dans la console d'administration de Tailscale, activez **HTTPS** (*DNS › HTTPS Certificates*) et autorisez
    **Funnel** pour cette machine (Tailscale vous y mène au premier `tailscale funnel`, au chapitre 6). Lisez le nom
    complet de la machine :

    ```sh
    tailscale status --json | grep -m1 '"DNSName"'
    ```

    L'adresse de la Ready Room est `https://<machine>.<tailnet>.ts.net` — le `DNSName` affiché, sans le point final.

=== "C — tunnel Cloudflare"

    Créez le tunnel dans votre tableau de bord Cloudflare (*Zero Trust › Networks › Tunnels*) et suivez ses
    instructions pour installer `cloudflared` sur le serveur. Faites pointer le nom public choisi vers
    `http://localhost:8000`. L'adresse de la Ready Room est `https://<nom choisi>`. Ce guide ne détaille pas cette
    option.

!!! success "Vérifier"
    Vous avez noté une adresse qui commence par `https://` et ne finit pas par `/`.
