#!/bin/sh
# reception.sh <phase> <livraison.zip> <maquette_validee.zip|-> <attendu/> -- la réception à froid du CdP (banc v6).
# Une phase par commande (le bac à sable coupe une commande à 300 s) ; chacune tient sous 270 s, mesurées.
# Phases, dans l'ordre :
#   statique      déballage à froid, rituel, mesure commune, pyflakes, node, pytest sur copie, .pyc
#   centre-base   rend le Centre de la base, si rendus_cc/base manque (sinon ne fait rien)
#   centre        rend le Centre de la livraison (mesure)
#   de-base       rend D et E de la base, si rendus/base manque
#   de            rend D et E de la livraison
#   verdict       réimprime les écarts, fait les comparaisons, rend le verdict
# Une phase n'affiche que ses écarts, puis UNE ligne « PHASE <nom> · aucun écart · <n> s » (ou « <k> écart(s) »).
# Elle garde ses écarts pour « verdict », qui les réimprime puis rend « RÉCEPTION · … · aucun écart » (ou
# « ÉCARTS ci-dessus »). Code de sortie de verdict : 0 sans écart, 1 avec. Code 2 : la phase ne peut pas se jouer
# (banc, base déballée, PostgreSQL 16, libfaketime, entrées absentes, ou phase jouée avant celle dont elle dépend).
# Préalables : la base déballée à froid dans /home/claude/dev/base, le banc dans /home/claude/rr/harness.
# <attendu/> porte la prédiction du cadrage, écrite par le CdP :
#   rituel.txt       la sortie attendue du rituel sur /home/claude/dev/mesure, ligne pour ligne
#   commune.txt      la sortie attendue de « mesure_commune.py base mesure »
#   pytest.txt       le compte attendu, ex. « 33 passed »
#   rendu_cc.txt     (facultatif) les lignes « === Scénario… » à « === Erreurs JS » de rendu_cc.py
#   immobiles_cc.txt (facultatif) un motif par ligne : les rendus du Centre identiques à la base
#   de_immobile      (facultatif, vide) : présent, D et E se comparent à la base, tout entiers
#   empreinte.txt    (facultatif) l'empreinte du code de la livraison (app, alembic, tests), calculée par la commande de
#                    l'étape 6 du prompt du dev ; présent, « statique » la compare et compte un écart si elle diffère (porte P13)
# v5 -- la maquette est FACULTATIVE : « - » prend sa place ; « verdict » ne la cherche pas et ne compte aucun écart pour elle.
# v5 -- PostgreSQL 16 n'est exigé que par les phases qui rendent (centre-base, centre, de-base, de) ;
#       « statique » et « verdict » s'en passent, et une phase sautée n'exige rien.
# v6 -- libfaketime n'est exigée que par les phases qui s'en servent : centre-base et centre (prepare_cc.sh, servir_cc.sh,
#       pg_faux.sh : LD_PRELOAD). de-base et de (prepare_base.sh, servir.sh, pg_up.sh) n'en appellent jamais.
# v6 -- Python : la variable PY (par défaut python3.12), jamais python3.
# v7 — phase « statique » : pip-audit (2.10.1) sur le requirements.txt de la livraison, juste après le compte pytest ;
#       une vulnérabilité (ou un service injoignable : code non nul) est l'écart « pip-audit ». Sortie dans « $ST/audit.txt ».
# rendu_cc.txt ou immobiles_cc.txt présent : les phases centre-base et centre se jouent ; sinon elles se sautent.
# de_immobile présent : les phases de-base et de se jouent ; sinon elles se sautent.
# rendus_cc/base et rendus/base se rendent UNE fois et se gardent : les supprimer quand la base change.
H=/home/claude/rr/harness; D=/home/claude/dev; ST=/tmp/reception_etat
PY="${PY:-python3.12}"
LIB=/usr/lib/x86_64-linux-gnu/faketime/libfaketimeMT.so.1
arret() { echo "ARRÊT · $1"; exit 2; }
[ $# -eq 4 ] || arret "usage : sh reception.sh <phase> <livraison.zip> <maquette_validee.zip|-> <attendu/>"
PH="$1"
case "$PH" in statique|centre-base|centre|de-base|de|verdict) ;; *) arret "phase inconnue « $PH »" ;; esac
[ -f "$2" ] || arret "livraison absente : $2"
[ "$3" = "-" ] || [ -f "$3" ] || arret "maquette validée absente : $3 (« - » : aucune maquette)"
[ -d "$4" ] || arret "dossier d'attendus absent : $4"
Z="$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"
MV=""; [ "$3" = "-" ] || MV="$(cd "$(dirname "$3")" && pwd)/$(basename "$3")"
AT="$(cd "$4" && pwd)"
for f in rituel.txt commune.txt pytest.txt; do [ -f "$AT/$f" ] || arret "attendu manquant : $AT/$f"; done
[ -f "$H/rituel_reprise.sh" ] && [ -f "$H/cssrules.py" ] || arret "le banc n'est pas dans $H"
[ -d "$D/base/app" ] || arret "la base n'est pas déballée dans $D/base"
# v5 : exigé par les seules phases qui rendent, au moment où elles rendent.
exige_rendu() {
  command -v pg_lsclusters >/dev/null 2>&1 && pg_lsclusters | grep -q '^16 ' || arret "PostgreSQL 16 absent (README du banc)"
}
# v6 : libfaketime, seulement pour les phases du Centre (horloge du scénario : LD_PRELOAD).
exige_faketime() {
  [ -f "$LIB" ] || arret "libfaketime absente : apt-get install -y faketime"
}
mkdir -p "$ST"; touch "$ST/ecarts.txt"
T0=$(date +%s); N=0
BESOIN_CC=0; { [ -f "$AT/rendu_cc.txt" ] || [ -f "$AT/immobiles_cc.txt" ]; } && BESOIN_CC=1
BESOIN_DE=0; [ -f "$AT/de_immobile" ] && BESOIN_DE=1

Q=0
emit() { if [ "$Q" = 1 ]; then cat >>"$ST/ecarts.txt"; else tee -a "$ST/ecarts.txt"; fi; }
ecart() { echo "ÉCART · $1" | emit; N=$((N+1)); }
montre() { sed 's/^/    /' "$1" | head -40 | emit; }
fin() {
  [ "$N" = 0 ] && R="aucun écart" || R="$N écart(s)"
  echo "PHASE $PH · $R · $(( $(date +%s) - T0 )) s"; touch "$ST/fait_$PH"; exit 0
}
saute() { echo "PHASE $PH · sautée · 0 s"; touch "$ST/fait_$PH"; exit 0; }
besoin() { [ -f "$ST/fait_$1" ] || arret "la phase « $PH » demande la phase « $1 », jouée avant"; }
# D et E se rendent à l'heure réelle (B1) : le cluster des rendus du Centre tourne sous l'horloge du scénario.
pg_reel() {
  if pg_lsclusters | grep -q ' online '; then
    pg_ctlcluster 16 main stop >/dev/null 2>&1 \
      || su postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main stop -m fast" >/dev/null 2>&1
  fi
  sh "$H/pg_up.sh" >/dev/null
  [ "$(su postgres -c "psql -Atc 'select current_date'" 2>/dev/null)" = "$(date +%F)" ] \
    || arret "PostgreSQL n'est pas revenu à l'heure réelle"
}
rendre_centre() {
  rm -rf "$D/rendus_cc/$1"
  { sh "$H/prepare_cc.sh" "$D/$1" && sh "$H/servir_cc.sh" "$D/$1" "$PY" -B "$H/rendu_cc.py" "$D/rendus_cc/$1"; } \
    >"$ST/rendu_cc_$1.txt" 2>&1 || { ecart "rendu du Centre ($1) en échec"; montre "$ST/rendu_cc_$1.txt"; rm -rf "$D/rendus_cc/$1"; }
}
rendre_de() {
  rm -rf "$D/rendus/$1"
  { sh "$H/prepare_base.sh" "$D/$1" && sh "$H/servir.sh" "$D/$1" "$PY" -B "$H/rendu_de.py" "$D/rendus/$1"; } \
    >"$ST/rendu_de_$1.txt" 2>&1 || { ecart "rendu de D et E ($1) en échec"; montre "$ST/rendu_de_$1.txt"; rm -rf "$D/rendus/$1"; }
}
px() { "$PY" -B -W ignore "$H/compare_px.py" "$@" 2>/dev/null; }

case "$PH" in
statique)
  rm -rf "$ST" "$D/rendus_cc/mesure" "$D/rendus/mesure"; mkdir -p "$ST"; touch "$ST/ecarts.txt"
  rm -rf "$D/mesure" && mkdir -p "$D/mesure" && (cd "$D/mesure" && unzip -q "$Z") || arret "déballage impossible : $Z"
  (cd "$H" && bash rituel_reprise.sh "$D/mesure") >"$ST/rituel.txt" 2>&1
  diff "$AT/rituel.txt" "$ST/rituel.txt" >"$ST/d.txt" || { ecart "rituel (attendu < > mesuré)"; montre "$ST/d.txt"; }
  (cd "$D" && "$PY" -B "$H/mesure_commune.py" base mesure) >"$ST/commune.txt" 2>&1
  diff "$AT/commune.txt" "$ST/commune.txt" >"$ST/d.txt" || { ecart "mesure commune (attendu < > mesuré)"; montre "$ST/d.txt"; }
  (cd "$D/mesure" && "$PY" -B -m pyflakes app/) >"$ST/pf.txt" 2>&1 || { ecart "pyflakes"; montre "$ST/pf.txt"; }
  node --check "$D/mesure/app/static/app.js" >"$ST/node.txt" 2>&1 || { ecart "node --check"; montre "$ST/node.txt"; }
  rm -rf "$D/essai" && cp -r "$D/mesure" "$D/essai"
  (cd "$D/essai" && set -a && . ./.env.example && set +a && "$PY" -m pytest -q -p no:cacheprovider tests/ 2>&1 | tail -1) >"$ST/pt.txt"
  rm -rf "$D/essai"
  grep -q "^$(cat "$AT/pytest.txt") in " "$ST/pt.txt" || { ecart "pytest : attendu « $(cat "$AT/pytest.txt") »"; montre "$ST/pt.txt"; }
  "$PY" -m pip_audit -r "$D/mesure/requirements.txt" --progress-spinner off >"$ST/audit.txt" 2>&1 || { ecart "pip-audit"; montre "$ST/audit.txt"; }
  K=$(find "$D/mesure" -name '*.pyc' | wc -l); [ "$K" = 0 ] || ecart "$K .pyc dans mesure après les contrôles"
  if [ -f "$AT/empreinte.txt" ]; then   # v5 : la porte P13, faite à la main jusqu'ici
    EA=$(tr -d ' \r\n' <"$AT/empreinte.txt")
    EM=$(cd "$D/mesure" && find app alembic tests -type f ! -name '*.pyc' | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -c1-12)
    [ "$EM" = "$EA" ] || ecart "empreinte du code (attendu $EA · mesuré $EM)"
  fi
  fin ;;
centre-base)
  [ "$BESOIN_CC" = 1 ] || saute
  exige_rendu; exige_faketime
  [ -f "$D/rendus_cc/base/mesures.json" ] || rendre_centre base
  fin ;;
centre)
  besoin statique; [ "$BESOIN_CC" = 1 ] || saute
  exige_rendu; exige_faketime
  rendre_centre mesure
  fin ;;
de-base)
  [ "$BESOIN_DE" = 1 ] || saute
  exige_rendu
  if [ ! -f "$D/rendus/base/mesures.json" ]; then pg_reel; rendre_de base; fi
  fin ;;
de)
  besoin statique; [ "$BESOIN_DE" = 1 ] || saute
  exige_rendu
  pg_reel; rendre_de mesure
  fin ;;
verdict)
  besoin statique; Q=1
  if [ "$BESOIN_CC" = 1 ]; then
    besoin centre; [ -f "$D/rendus_cc/base/mesures.json" ] || arret "le Centre de la base n'est pas rendu (phase centre-base)"
  fi
  if [ "$BESOIN_DE" = 1 ]; then
    besoin de; [ -f "$D/rendus/base/mesures.json" ] || arret "D et E de la base ne sont pas rendus (phase de-base)"
  fi
  if [ "$BESOIN_CC" = 1 ]; then
    if [ -f "$AT/rendu_cc.txt" ]; then
      sed -n '/^=== Scénario/,/^=== Erreurs JS/p;/^=== Relances/p' "$ST/rendu_cc_mesure.txt" >"$ST/scen.txt"
      diff "$AT/rendu_cc.txt" "$ST/scen.txt" >"$ST/d.txt" || { ecart "scénario des relances (attendu < > mesuré)"; montre "$ST/d.txt"; }
    fi
    if [ -f "$AT/immobiles_cc.txt" ]; then
      while read -r MOTIF; do
        [ -n "$MOTIF" ] || continue
        px "$D/rendus_cc/base" "$D/rendus_cc/mesure" "$MOTIF" '_page_' >"$ST/px.txt" \
          || { ecart "Centre, base → mesure, motif « $MOTIF »"; grep -v ' comparés · ' "$ST/px.txt" | sed 's/^/    /' | emit; }
        grep -q '^0 comparés' "$ST/px.txt" && ecart "Centre, motif « $MOTIF » : aucune image comparée"
      done <"$AT/immobiles_cc.txt"
    fi
  fi
  if [ "$BESOIN_DE" = 1 ]; then
    px "$D/rendus/base" "$D/rendus/mesure" '' '_page_' >"$ST/px.txt" \
      || { ecart "D et E, base → mesure"; grep -v ' comparés · ' "$ST/px.txt" | head -20 | sed 's/^/    /' | emit; }
  fi
  if [ -n "$MV" ]; then   # v5 : « - » = pas de maquette, rien à chercher ni à compter
    rm -rf "$ST/valide" && mkdir -p "$ST/valide" && (cd "$ST/valide" && unzip -qj "$MV") || ecart "maquette validée illisible"
    NOMS=$(cd "$ST/valide" && ls *.png 2>/dev/null | sed 's/[.]/[.]/g' | paste -sd'|' -)
    if [ -z "$NOMS" ]; then ecart "maquette validée : aucune image"
    else
      R="$D/rendus/mesure"; ls "$ST/valide" | grep -q '^R-\|^M-\|^S[0-9]\|^MP_' && R="$D/rendus_cc/mesure"
      [ -d "$R" ] || arret "la maquette désigne $R, qui n'est pas rendu"
      px "$ST/valide" "$R" "^($NOMS)\$" >"$ST/px.txt" \
        || { ecart "maquette validée → rendu de l'archive"; grep -v ' comparés · ' "$ST/px.txt" | sed 's/^/    /' | emit; }
    fi
  fi
  K=$(find "$D/mesure" -name '*.pyc' | wc -l); [ "$K" = 0 ] || ecart "$K .pyc dans mesure après les rendus"
  TOTAL=$(grep -c '^ÉCART' "$ST/ecarts.txt")
  [ "$TOTAL" = 0 ] && { echo "RÉCEPTION · $(basename "$Z") · aucun écart"; exit 0; }
  echo "--- les $TOTAL écart(s) de la réception ---"; cat "$ST/ecarts.txt"
  echo "RÉCEPTION · $(basename "$Z") · ÉCARTS ci-dessus"; exit 1 ;;
esac
