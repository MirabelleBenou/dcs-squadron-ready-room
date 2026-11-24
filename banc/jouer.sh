#!/bin/sh
# jouer.sh <shell> <mode> [script]  -- joue la sonde livrée, telle quelle, contre le faux Discord
H=/home/claude/rr/harness
SCRIPT="${3:-/home/claude/rr/sonde/sonde_effectif_relances.sh}"
echo "$2" > "$H/mode"
export HOME="$H/home" ESSAI=/home/claude/rr/essai TEST_ENV=/home/claude/rr/test.env
export FAUX_DISCORD="http://127.0.0.1:8999/api/v10" PATH="$H/bin:$PATH"
cd /tmp && "$1" "$SCRIPT"
