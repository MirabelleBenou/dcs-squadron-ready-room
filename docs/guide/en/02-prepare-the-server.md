# 2 · Prepare the server { #prepare-the-server }

This chapter updates the system, closes the firewall, installs Docker and sets up the Ready Room's HTTPS address. All
commands are typed in an SSH session on the server.

## 2.1 · Update the system { #update-system }

```sh
sudo apt update && sudo apt full-upgrade -y
```

If the update changed the kernel, reboot (`sudo reboot`) and open the SSH session again.

!!! note "An administration account"
    If you are logged in as `root`, first create an account of your own, give it `sudo`, then work with it:
    ```sh
    adduser <name>
    usermod -aG sudo <name>
    ```

## 2.2 · Firewall { #firewall }

```sh
sudo apt install -y ufw
sudo ufw allow OpenSSH
```

**Option A only** (your domain name and Caddy), also open the web ports:

```sh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 443/udp
```

Then switch the firewall on:

```sh
sudo ufw enable
sudo ufw status
```

!!! success "Check"
    `ufw status` shows `Status: active`, `OpenSSH` as `ALLOW`, and for option A, `80/tcp`, `443/tcp` and `443/udp`.

!!! warning "Warning"
    Docker opens the ports its containers publish by itself, **bypassing `ufw`**. The Ready Room only publishes its
    application on `127.0.0.1:8000`, invisible from outside: never change that line of `docker-compose.yml`.

## 2.3 · Install Docker { #install-docker }

Install Docker from **Docker's package repository**, not the distribution's `docker.io` package (its Compose plugin is
missing or old). First remove anything that could get in the way (harmless if nothing is installed):

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

Then give your account the right to drive Docker, and **close and reopen the SSH session** for it to take effect:

```sh
sudo usermod -aG docker $USER
```

!!! warning "Warning"
    The `docker` group is worth `root` rights on the machine. Only grant it to the accounts that administer the server.

## 2.4 · Check Docker { #check-docker }

```sh
docker run --rm hello-world
docker compose version
```

!!! success "Check"
    The first command prints `Hello from Docker!`; the second, `Docker Compose version v2.` followed by a number.

!!! failure "If it does not work"
    `permission denied … docker.sock`: the SSH session was not reopened after the `usermod` of §2.3.
    `docker: 'compose' is not a docker command`: the `docker-compose-plugin` package is missing; go back to §2.3.

## 2.5 · Set up the HTTPS address { #address }

Discord (chapter 3) and the configuration (chapter 5) need the Ready Room's final address. Set it up now, according to
the option chosen in [§1.4](01-prerequisites.md#network). Write it down: it is `https://<address>` in the rest of the
guide, **without a trailing `/`**.

=== "A — domain name"

    At your domain provider, create an **A** record (and **AAAA** if the server has an IPv6 address) pointing the chosen
    name (for example `readyroom.example.org`) to the server's public IP address. To read that address:

    ```sh
    curl -4 -s https://ifconfig.me ; echo
    ```

    Wait until the name resolves (from a few minutes to a few hours):

    ```sh
    getent hosts <chosen name>
    ```

    The Ready Room's address is `https://<chosen name>`. The certificate will come by itself at first start
    (chapter 7).

=== "B — Tailscale Funnel"

    Install Tailscale and attach the server to your account (the command prints a link to open in a browser):

    ```sh
    curl -fsSL https://tailscale.com/install.sh | sh
    sudo tailscale up
    ```

    In the Tailscale admin console, enable **HTTPS** (*DNS › HTTPS Certificates*) and allow **Funnel** for this
    machine (Tailscale takes you there on the first `tailscale funnel`, in chapter 6). Read the machine's full name:

    ```sh
    tailscale status --json | grep -m1 '"DNSName"'
    ```

    The Ready Room's address is `https://<machine>.<tailnet>.ts.net` — the `DNSName` shown, without the final dot.

=== "C — Cloudflare tunnel"

    Create the tunnel in your Cloudflare dashboard (*Zero Trust › Networks › Tunnels*) and follow its instructions to
    install `cloudflared` on the server. Point the chosen public name to `http://localhost:8000`. The Ready Room's
    address is `https://<chosen name>`. This guide does not go further into this option.

!!! success "Check"
    You have written down an address that starts with `https://` and does not end with `/`.
