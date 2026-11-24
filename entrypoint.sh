#!/bin/sh
set -e

# --- 0. Le secret de session (lot « La défense de l'App exposée », v1.0083) ------
# Avant tout, même avant l'attente de la base : l'App refuse de démarrer sur un
# SESSION_SECRET de moins de 32 caractères ou sur la valeur d'exemple du .env.example
# (`python -B -m app.defense` lit l'environnement, écrit la raison sur la sortie
# d'erreur et sort en 1). Dans un `if`, l'échec n'arrête pas le script avant le message.
if ! RAISON_SECRET=$(python -B -m app.defense 2>&1); then
    echo "[entrypoint] Failure: SESSION_SECRET refused (${RAISON_SECRET})."
    exit 1
fi

# --- 0 bis. La configuration du premier démarrage (lot « rr-env-epure », v1.0105) ---
# Même forme : `python -B -m app.reglages` lit l'environnement, écrit la raison du refus
# sur la sortie d'erreur et sort en 1 -- `CONFIG_KEY` absente ou invalide (la clé qui
# chiffre les secrets des réglages gardés en base), ou `ADMIN_IDS` sans aucun
# administrateur fondateur.
if ! RAISON_CONFIG=$(python -B -m app.reglages 2>&1); then
    echo "[entrypoint] Failure: configuration refused (${RAISON_CONFIG})."
    exit 1
fi

# --- 1. Attente de la base --------------------------------------------------
# pg_isready en boucle bornée. Le service "db" est déjà attendu par Docker
# Compose (depends_on: condition: service_healthy), mais on garde une garde
# active ici -- même budget (30 tentatives x 2s) que portait jusqu'ici la
# boucle "until alembic upgrade head" : une base lente à démarrer est
# attendue, pas déclarée en échec.
echo "[entrypoint] Waiting for the database..."
ATTEMPTS=0
MAX_ATTEMPTS=30
until pg_isready -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
        echo "[entrypoint] Failure: the database did not become available after $MAX_ATTEMPTS attempts."
        exit 1
    fi
    echo "[entrypoint] Database not ready (attempt $ATTEMPTS/$MAX_ATTEMPTS), retrying in 2s..."
    sleep 2
done
echo "[entrypoint] Database ready."

# --- 2. Migration en attente ? ----------------------------------------------
# Comparaison alembic current / alembic heads. Si identiques, rien à
# appliquer : pas de sauvegarde, démarrage direct (silencieux au quotidien).
CURRENT_REV=$(alembic current | awk '{print $1}' | head -n1)
HEAD_REV=$(alembic heads | awk '{print $1}' | head -n1)

if [ "$CURRENT_REV" != "$HEAD_REV" ]; then
    echo "[entrypoint] Migration pending (current: ${CURRENT_REV:-none}, target: $HEAD_REV): backup before applying."

    # --- 3. Sauvegarde, bloquante -------------------------------------------
    # Nommage par révision Alembic de départ, pas par version de paquet :
    # /srv/VERSION est celle du conteneur qui DÉMARRE (donc, en cas de
    # migration en attente, la version CIBLE), alors que le contenu du
    # fichier est l'état D'AVANT migration -- les deux ne coïncident pas.
    # La révision Alembic constatée par `alembic current` juste avant la
    # sauvegarde est le seul identifiant fiable de l'état capturé.
    mkdir -p /backups
    REV_LABEL="${CURRENT_REV:-vierge}"
    STAMP=$(date +%Y%m%d-%H%M)
    BACKUP_FILE="/backups/readyroom_rev-${REV_LABEL}_${STAMP}.dump"

    echo "[entrypoint] Backing up to $BACKUP_FILE..."
    if ! PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h db -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f "$BACKUP_FILE"; then
        echo "[entrypoint] Failure: pg_dump returned an error. Migration not applied, stopping."
        rm -f "$BACKUP_FILE"
        exit 1
    fi
    if [ ! -s "$BACKUP_FILE" ]; then
        echo "[entrypoint] Failure: the backup file is empty ($BACKUP_FILE). Migration not applied, stopping."
        rm -f "$BACKUP_FILE"
        exit 1
    fi
    echo "[entrypoint] Backup OK ($(du -h "$BACKUP_FILE" | cut -f1))."

    # --- 4. Purge : dix sauvegardes conservées, les plus récentes -----------
    # Après une sauvegarde réussie, jamais avant.
    BACKUP_COUNT=$(ls -1 /backups/readyroom_rev-*.dump 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 10 ]; then
        echo "[entrypoint] Purge: $BACKUP_COUNT backups, keeping the 10 most recent."
        ls -1t /backups/readyroom_rev-*.dump | tail -n +11 | xargs rm -f
    fi
else
    echo "[entrypoint] No migration pending ($CURRENT_REV): no backup."
fi

# --- 5. Migration puis démarrage --------------------------------------------
echo "[entrypoint] Applying migrations..."
alembic upgrade head
echo "[entrypoint] Migrations applied (alembic upgrade head OK)."

echo "[entrypoint] Starting the application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips="*"
