#!/bin/sh
# servir_cc.sh <dossier_appli> <commande…> (banc v4) : PG16 sous horloge du scénario ; faux Discord
# (port 8999, mode « ok », MP reçus dans /tmp/faux_discord.log.mp.jsonl) ; uvicorn depuis <dossier_appli>
# AVEC jeton bot -- l'appel tourne quand le scénario le demande --, horloge figée au 02/10/2026 10:00 UTC ;
# joue la commande (à l'heure réelle : le navigateur reçoit l'heure du scénario par l'instrument) ;
# arrête tout. Le bac à sable tue les processus entre deux appels d'outil : tout se joue dans UNE commande.
A="${1:?usage: servir_cc.sh <dossier_appli> <commande…>}"; shift
H=/home/claude/rr/harness
PY="${PY:-python3.12}"   # banc v6 : Python 3.12, sans shim PATH
LIB=/usr/lib/x86_64-linux-gnu/faketime/libfaketimeMT.so.1
sh "$H/pg_faux.sh" >/dev/null || { echo "PG16 sous horloge du scénario : échec"; exit 1; }
echo ok > "$H/mode"; rm -f /tmp/faux_discord.log /tmp/faux_discord.log.mp.jsonl
"$PY" -B "$H/faux_discord.py" 8999 "$H/mode" "$H/membres.json" /tmp/faux_discord.log >/tmp/fd.log 2>&1 &
FD=$!
( cd "$A" || exit 1
  set -a; . /home/claude/rr/test.env; set +a
  export LD_PRELOAD=$LIB FAKETIME='2026-10-02 10:00:00' FAKETIME_DONT_FAKE_MONOTONIC=1
  exec "$PY" -B "${LANCEUR:-$H/lancer_cc.py}" ) >/tmp/uv.log 2>&1 &
UV=$!
i=0; until curl -s -o /dev/null http://127.0.0.1:8000/ || [ $i -ge 60 ]; do sleep 0.5; i=$((i+1)); done
cd /home/claude/rr && "$@"; RC=$?
kill $UV $FD 2>/dev/null; wait $UV $FD 2>/dev/null
grep -q "Traceback" /tmp/uv.log && { echo "uvicorn : TRACEBACK dans /tmp/uv.log"; RC=1; }
exit $RC
