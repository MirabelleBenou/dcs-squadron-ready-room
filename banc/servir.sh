#!/bin/sh
# servir.sh <dossier_appli> <commande…> : PG16 en ligne, uvicorn lancé depuis <dossier_appli> (env de test,
# SANS jeton bot : l'appel ne tourne pas et n'écrit rien pendant le rendu), joue la commande, arrête uvicorn.
# Le bac à sable tue les processus entre deux appels d'outil : tout se joue dans UNE commande.
A="${1:?usage: servir.sh <dossier_appli> <commande…>}"; shift
PY="${PY:-python3.12}"   # banc v6 : Python 3.12, sans shim PATH
sh /home/claude/rr/harness/pg_up.sh >/dev/null || exit 1
( cd "$A" || exit 1
  set -a; . /home/claude/rr/test.env; set +a; unset DISCORD_BOT_TOKEN
  exec "$PY" -B -m uvicorn app.main:app --host 127.0.0.1 --port 8000 ) >/tmp/uv.log 2>&1 &
UV=$!
i=0; until curl -s -o /dev/null http://127.0.0.1:8000/ || [ $i -ge 60 ]; do sleep 0.5; i=$((i+1)); done
cd /home/claude/rr && "$@"; RC=$?
kill $UV 2>/dev/null; wait $UV 2>/dev/null
grep -q "Traceback" /tmp/uv.log && { echo "uvicorn : TRACEBACK dans /tmp/uv.log"; RC=1; }
exit $RC
