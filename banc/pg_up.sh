#!/bin/sh
pg_lsclusters | grep -q ' online ' || { pg_ctlcluster 16 main start >/dev/null 2>&1; sleep 2; }
pg_lsclusters | grep -q ' online ' && echo "pg16 en ligne" || echo "pg16 HORS LIGNE"
