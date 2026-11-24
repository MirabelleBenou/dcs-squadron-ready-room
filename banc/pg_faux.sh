#!/bin/sh
# pg_faux.sh : (re)démarre PostgreSQL 16 SOUS HORLOGE DU SCÉNARIO -- le 02/10/2026, 10:00 UTC (12:00 à
# Paris), puis l'heure avance. Banc v4 : les rendus du Centre ne dépendent plus du jour où l'on rend.
# Arrête d'abord un cluster lancé à l'heure réelle. Exige libfaketime (README).
LIB=/usr/lib/x86_64-linux-gnu/faketime/libfaketimeMT.so.1
[ -f "$LIB" ] || { echo "libfaketime absente : apt-get install -y faketime"; exit 1; }
pg_lsclusters | grep -q ' online ' && { pg_ctlcluster 16 main stop >/dev/null 2>&1 || su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main stop -m fast" >/dev/null 2>&1; }
su postgres -c "LD_PRELOAD=$LIB FAKETIME='@2026-10-02 10:00:00' FAKETIME_DONT_FAKE_MONOTONIC=1 /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main -o '-c config_file=/etc/postgresql/16/main/postgresql.conf' -l /tmp/pg_faux.log start" >/dev/null 2>&1
i=0; until pg_lsclusters | grep -q ' online ' || [ $i -ge 20 ]; do sleep 0.5; i=$((i+1)); done
J=$(su postgres -c "psql -Atc 'select current_date'" 2>/dev/null)
[ "$J" = "2026-10-02" ] && echo "pg16 en ligne · horloge du scénario $J" || { echo "pg16 : horloge inattendue ($J)"; exit 1; }
