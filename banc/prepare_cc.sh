#!/bin/sh
# prepare_cc.sh <dossier_appli> : base d'essai NEUVE pour le Centre (banc v4) -- comme prepare_base.sh,
# mais SOUS HORLOGE DU SCÉNARIO (02/10/2026) et avec le semis des relances après les deux autres.
A="${1:?usage: prepare_cc.sh <dossier_appli>}"
H=/home/claude/rr/harness
PY="${PY:-python3.12}"   # banc v6 : Python 3.12, sans shim PATH
LIB=/usr/lib/x86_64-linux-gnu/faketime/libfaketimeMT.so.1
sh "$H/pg_faux.sh" || exit 1
su postgres -c "psql -qtc \"SELECT 1 FROM pg_roles WHERE rolname='readyroom'\"" | grep -q 1 \
  || su postgres -c "psql -qc \"CREATE ROLE readyroom LOGIN PASSWORD 'readyroom' SUPERUSER\""
su postgres -c "dropdb --if-exists readyroom" && su postgres -c "createdb -O readyroom readyroom" || exit 1
cd "$A" || exit 1
set -a; . /home/claude/rr/test.env; set +a
export LD_PRELOAD=$LIB FAKETIME='2026-10-02 10:00:00' FAKETIME_DONT_FAKE_MONOTONIC=1
"$PY" -B -m alembic upgrade head >/tmp/alembic.log 2>&1 || { tail -5 /tmp/alembic.log; exit 1; }
"$PY" -B "$H/semis.py" "$H/membres.json" || exit 1
"$PY" -B "$H/semis_e.py" || exit 1
"$PY" -B "$H/semis_r.py" "$H/membres.json" "$H/mode" || exit 1
unset LD_PRELOAD FAKETIME
PGPASSWORD=readyroom psql -h 127.0.0.1 -U readyroom -d readyroom -Atc "SELECT 'migration ' || version_num FROM alembic_version"
