#!/bin/sh
# prepare_debrief.sh <dossier_appli> : base d'essai NEUVE avec le Débrief semé (banc v5).
# Lance prepare_base.sh <appli> (inchangé : base recréée, migrations, semis.py, semis_e.py), puis semis_debrief.py
# depuis <appli>, l'environnement de test chargé : deux sessions de la fixture « Bataille de Francfort », deux
# campagnes, 40 vols, leurs évènements, et le droit debrief.access du rôle Pilote. Rejouable, déterministe.
A="${1:?usage: prepare_debrief.sh <dossier_appli>}"
H=/home/claude/rr/harness
PY="${PY:-python3.12}"   # banc v6 : Python 3.12, sans shim PATH
sh "$H/prepare_base.sh" "$A" || exit 1
cd "$A" || exit 1
set -a; . /home/claude/rr/test.env; set +a
"$PY" -B "$H/semis_debrief.py" || exit 1
