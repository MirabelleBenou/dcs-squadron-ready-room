#!/bin/sh
# Lot « rr-public-guide-1 » : écrit le fichier .env du premier démarrage (docs/guide, chapitre 5).
# POSIX sh, sans Python ni jq ; il n'écrit que `.env`, et ne touche à rien d'autre.
# Le modèle ci-dessous suit .env.example, ligne pour ligne (tests/test_init_env.py le vérifie).

usage() {
    cat <<'EOF'
Usage: sh init-env.sh

Asks a few questions, makes the three secrets and writes the .env file of the
Squadron Ready Room in the current folder, readable by you only (mode 600).
It writes nothing else. It refuses to replace an existing .env.

Questions, in this order (one answer per line):
  BASE_URL                the public HTTPS address, no trailing slash
  option                  A (your domain name, Caddy proxy) or B (Tailscale Funnel or another tunnel: no Caddy)
  DISCORD_CLIENT_ID       the Discord application ID (17 to 20 digits)
  DISCORD_GUILD_ID        your Discord server ID (17 to 20 digits)
  DISCORD_CLIENT_SECRET   the Discord client secret
  ADMIN_IDS               founding administrators: Discord IDs separated by commas

Needs: openssl. Guide: appendix A and chapter 5 (docs/guide).
EOF
}

# Les tests de caractères ci-dessous se lisent en C : pas d'intervalle élargi par la langue de la machine.
LC_ALL=C
export LC_ALL

case "${1-}" in
    --help | -h)
        usage
        exit 0
        ;;
    '') ;;
    *)
        usage >&2
        exit 2
        ;;
esac

if [ -e .env ] || [ -L .env ]; then
    echo ".env already exists: rename it first (mv .env .env.old)." >&2
    exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required and was not found." >&2
    exit 1
fi

# --- Les réponses : une par ligne, reposées tant qu'elles sont refusées ---------------------------

fin_de_saisie() {
    echo "" >&2
    echo "End of input before every answer was accepted: .env not written." >&2
    exit 1
}

# 17 à 20 chiffres.
est_id() {
    case "$1" in
        '' | *[!0-9]*) return 1 ;;
    esac
    [ "${#1}" -ge 17 ] && [ "${#1}" -le 20 ]
}

# Des identifiants de 17 à 20 chiffres séparés par des virgules, sans espace, au moins un.
est_liste_ids() {
    case "$1" in
        '' | ,* | *, | *,,* | *[[:space:]]*) return 1 ;;
    esac
    ancien_ifs=$IFS
    IFS=,
    set -f
    for un in $1; do
        if ! est_id "$un"; then
            set +f
            IFS=$ancien_ifs
            return 1
        fi
    done
    set +f
    IFS=$ancien_ifs
    return 0
}

# `https://` puis un nom d'hôte seul (A-Z a-z 0-9 . -) : ni port, ni chemin, ni / final, ni guillemet, ni espace.
est_base_url() {
    case "$1" in
        https://?*) ;;
        *) return 1 ;;
    esac
    hote=${1#https://}
    case "$hote" in
        *[!A-Za-z0-9.-]*) return 1 ;;
    esac
    return 0
}

# Docker Compose interpole le .env (`$`, guillemets) : un secret ne porte que A-Z a-z 0-9 _ -, le jeu des secrets Discord.
est_secret() {
    case "$1" in
        '' | *[!A-Za-z0-9_-]*) return 1 ;;
    esac
    return 0
}

est_option() {
    case "$1" in
        A | B) return 0 ;;
    esac
    return 1
}

# demande <variable> <verification> <question> <rappel> [secret]
demande() {
    nom=$1
    verif=$2
    question=$3
    rappel=$4
    cache=${5-}
    while :; do
        printf '%s ' "$question"
        if [ -n "$cache" ] && [ -t 0 ]; then
            # L'écho du terminal revient quoi qu'il arrive (fin normale, Ctrl+C, signal).
            trap 'stty echo 2>/dev/null' EXIT
            trap 'stty echo 2>/dev/null; exit 1' INT TERM
            stty -echo 2>/dev/null
        fi
        reponse=
        lu=0
        IFS= read -r reponse || lu=1
        if [ -n "$cache" ] && [ -t 0 ]; then
            stty echo 2>/dev/null
            trap - EXIT INT TERM
            echo ""
        fi
        if [ "$lu" -ne 0 ] && [ -z "$reponse" ]; then
            fin_de_saisie
        fi
        # Un retour chariot de fin de ligne (saisie venue de Windows) n'est pas une réponse.
        reponse=$(printf '%s' "$reponse" | tr -d '\r')
        if "$verif" "$reponse"; then
            eval "$nom=\$reponse"
            return 0
        fi
        echo "  Not accepted: $rappel" >&2
        if [ "$lu" -ne 0 ]; then
            fin_de_saisie
        fi
    done
}

echo "Squadron Ready Room: writing .env (nothing else is touched)."
demande BASE_URL est_base_url "BASE_URL (public HTTPS address, e.g. https://readyroom.example.org):" \
    "it must be https:// followed by a host name only (no port, no path, no trailing /)."
demande OPTION est_option "Option A (your domain name, Caddy proxy) or B (Tailscale Funnel or another tunnel: no Caddy)? [A/B]:" \
    "answer A or B."
demande DISCORD_CLIENT_ID est_id "DISCORD_CLIENT_ID (Application ID, 17 to 20 digits):" \
    "17 to 20 digits, nothing else."
demande DISCORD_GUILD_ID est_id "DISCORD_GUILD_ID (your Discord server ID, 17 to 20 digits):" \
    "17 to 20 digits, nothing else."
demande DISCORD_CLIENT_SECRET est_secret "DISCORD_CLIENT_SECRET (Client Secret, not shown while you type):" \
    "only letters, digits, - and _." cache
demande ADMIN_IDS est_liste_ids "ADMIN_IDS (founding administrators' Discord IDs, separated by commas, no space):" \
    "at least one ID of 17 to 20 digits; several separated by commas, without spaces."

# --- Les trois secrets ------------------------------------------------------------------------------

SESSION_SECRET=$(openssl rand -base64 48 | tr -d '\n') || exit 1
CONFIG_KEY=$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n') || exit 1
POSTGRES_PASSWORD=$(openssl rand -hex 24) || exit 1
if [ -z "$SESSION_SECRET" ] || [ -z "$CONFIG_KEY" ] || [ -z "$POSTGRES_PASSWORD" ]; then
    echo "openssl did not produce the secrets: .env not written." >&2
    exit 1
fi

if [ "$OPTION" = A ]; then
    COMPOSE_PREFIX=
else
    COMPOSE_PREFIX='# '
fi
POSTGRES_USER=readyroom
POSTGRES_DB=readyroom

# --- Le fichier -----------------------------------------------------------------------------------------

umask 077
export BASE_URL DISCORD_CLIENT_ID DISCORD_CLIENT_SECRET DISCORD_GUILD_ID ADMIN_IDS \
    SESSION_SECRET CONFIG_KEY POSTGRES_USER POSTGRES_PASSWORD POSTGRES_DB COMPOSE_PREFIX

# Le modèle est celui de .env.example ; chaque @NOM@ est remplacé, sans interpréter la valeur
# (awk lit ENVIRON et coupe la ligne à la main : ni `&`, ni barre oblique inverse).
modele() {
    cat <<'EOF'
# --- Squadron Ready Room: what the first start needs. Everything else is set inside the application.
# --- Full reference: appendix A of the installation guide. `sh init-env.sh` writes this file for you.
# --- Public HTTPS address of the Ready Room, without a trailing slash: the only source of Discord's redirect address.
BASE_URL=@BASE_URL@
# --- Discord application (Developer Portal): members' sign-in
DISCORD_CLIENT_ID=@DISCORD_CLIENT_ID@
DISCORD_CLIENT_SECRET=@DISCORD_CLIENT_SECRET@
DISCORD_GUILD_ID=@DISCORD_GUILD_ID@
# --- Founding administrators: Discord account IDs, separated by commas (at least one)
ADMIN_IDS=@ADMIN_IDS@
# --- Session secret (signed cookie)
# At least 32 characters, never this example value: otherwise the Ready Room refuses to start.
# Make one with `openssl rand -base64 48 | tr -d '\n'`
SESSION_SECRET=@SESSION_SECRET@
# --- Settings key: encrypts the secrets kept in the database. Without it, the Ready Room refuses to start.
# Make one with `openssl rand -base64 32 | tr '+/' '-_'` and keep it apart from the backups:
# if lost, the secrets entered in Command Center > Configuration must be entered again.
CONFIG_KEY=@CONFIG_KEY@
# --- Database (the "db" service of docker-compose.yml; the application builds its address from these)
POSTGRES_USER=@POSTGRES_USER@
POSTGRES_PASSWORD=@POSTGRES_PASSWORD@
POSTGRES_DB=@POSTGRES_DB@
# --- Read by Docker Compose only. Option A of the guide (your domain name): also start the Caddy proxy.
@COMPOSE_PREFIX@COMPOSE_FILE=docker-compose.yml:compose.caddy.yml
# --- Host folders plugged into the container (docker-compose.yml). Without these lines: ./data/… of the project.
# SUITES_HOST_DIR=./data/suites
# TILES_HOST_DIR=./data/tiles
# TILES_CACHE_HOST_DIR=./data/tiles-cache
EOF
}

ecrit_env() {
    modele | awk '
        {
            ligne = $0
            sortie = ""
            while ((debut = index(ligne, "@")) > 0) {
                reste = substr(ligne, debut + 1)
                fin = index(reste, "@")
                if (fin == 0) break
                nom = substr(reste, 1, fin - 1)
                if (nom in ENVIRON || nom == "COMPOSE_PREFIX") {
                    sortie = sortie substr(ligne, 1, debut - 1) ENVIRON[nom]
                    ligne = substr(reste, fin + 1)
                } else {
                    sortie = sortie substr(ligne, 1, debut)
                    ligne = reste
                }
            }
            print sortie ligne
        }'
}

# `set -C` : la création échoue si un .env est apparu entre-temps ; jamais d'écrasement (et alors rien n'est retiré).
if ! (set -C; : > .env); then
    echo "Could not create .env: nothing was written." >&2
    exit 1
fi
# Le fichier existe, vide et en 600 (umask 077) : s'il ne peut pas être écrit en entier, on ne le laisse pas à demi fait.
if ! ecrit_env > .env; then
    rm -f .env
    echo "Could not write .env: nothing was written." >&2
    exit 1
fi
chmod 600 .env

echo ""
echo ".env written (mode 600)."
echo ""
echo "CONFIG_KEY, shown once: $CONFIG_KEY"
echo "Copy it into your password manager and keep it apart from the backups:"
echo "if it is lost, the secrets entered in Command Center > Configuration must be entered again."
