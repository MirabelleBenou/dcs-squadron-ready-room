#!/bin/sh
# prepare_base.sh <dossier_appli> : base d'essai NEUVE -- PG16, base recréée, migrations de 0001 à la
# tête depuis <dossier_appli>, semis du banc, semis des organigrammes. Rejouable, déterministe.
A="${1:?usage: prepare_base.sh <dossier_appli>}"
H=/home/claude/rr/harness
PY="${PY:-python3.12}"   # banc v6 : Python 3.12, sans shim PATH
sh "$H/pg_up.sh" || exit 1
su postgres -c "psql -qtc \"SELECT 1 FROM pg_roles WHERE rolname='readyroom'\"" | grep -q 1 \
  || su postgres -c "psql -qc \"CREATE ROLE readyroom LOGIN PASSWORD 'readyroom' SUPERUSER\""
su postgres -c "dropdb --if-exists readyroom" && su postgres -c "createdb -O readyroom readyroom" || exit 1
cd "$A" || exit 1
set -a; . /home/claude/rr/test.env; set +a
"$PY" -B -m alembic upgrade head >/tmp/alembic.log 2>&1 || { tail -5 /tmp/alembic.log; exit 1; }
"$PY" -B "$H/semis.py" "$H/membres.json" || exit 1
"$PY" -B "$H/semis_e.py" || exit 1
PGPASSWORD=readyroom psql -h 127.0.0.1 -U readyroom -d readyroom -Atc "SELECT 'migration ' || version_num FROM alembic_version"
