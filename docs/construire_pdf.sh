#!/bin/sh
# Lot « rr-public-guide-1 » : construit le PDF du guide d'installation, dans une langue.
#
#   sh docs/construire_pdf.sh <langue> <version> <sortie.pdf>        langue : en | fr
#
# La navigation de docs/mkdocs.yml est la seule source de l'ordre des chapitres. Les pages de la langue sont
# assemblées par Pandoc en un seul HTML, que WeasyPrint met en page avec docs/guide/pdf.css (A4, polices de
# app/static/assets/fonts/ embarquées). Outils attendus dans le PATH : pandoc, weasyprint (variable WEASYPRINT pour
# un autre chemin), awk, sed.
set -eu

usage() {
    echo "Usage: sh docs/construire_pdf.sh <en|fr> <version> <output.pdf>" >&2
    exit 2
}

[ "$#" -eq 3 ] || usage
LANGUE=$1
VERSION=$2
SORTIE=$3
case "$LANGUE" in
    en) TITRE="Installation Guide" ; LANGUE_NOM="English" ;;
    fr) TITRE="Guide d'installation" ; LANGUE_NOM="Français" ;;
    *) usage ;;
esac
# La version ne porte que des chiffres et des points (elle entre dans un nom de fichier et dans le CSS écrit plus bas).
case "$VERSION" in
    '' | *[!0-9.]*) echo "version must hold only digits and dots: $VERSION" >&2; exit 1 ;;
esac

DOCS=$(cd "$(dirname "$0")" && pwd)
GUIDE=$DOCS/guide
YML=$DOCS/mkdocs.yml
WEASYPRINT=${WEASYPRINT:-weasyprint}

for outil in pandoc awk sed; do
    command -v "$outil" >/dev/null 2>&1 || { echo "$outil not found" >&2; exit 1; }
done
command -v "$WEASYPRINT" >/dev/null 2>&1 || { echo "$WEASYPRINT not found" >&2; exit 1; }
[ -d "$GUIDE/$LANGUE" ] || { echo "no folder $GUIDE/$LANGUE" >&2; exit 1; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
trap 'exit 1' INT TERM

# --- 1. L'ordre : les fichiers de `nav`, dans l'ordre de mkdocs.yml -----------------------------------------
# Une ligne `- …` de `nav` qui n'est pas un simple `- fichier.md` fait échouer le script : jamais un chapitre sauté en silence.
awk '
    /^nav:[[:space:]]*$/ { dans = 1; next }
    dans && /^[[:space:]]+-[[:space:]]+[^[:space:]]+\.md[[:space:]]*$/ { sub(/^[[:space:]]+-[[:space:]]+/, ""); sub(/[[:space:]]+$/, ""); print; next }
    dans && /^[[:space:]]*-/ { print "unexpected nav line: " $0 > "/dev/stderr"; erreur = 1; next }
    dans && /^[^[:space:]#]/ { dans = 0 }
    END { exit erreur }
' "$YML" > "$TMP/ordre.txt" || { echo "cannot read the navigation of $YML" >&2; exit 1; }
[ -s "$TMP/ordre.txt" ] || { echo "no navigation found in $YML" >&2; exit 1; }

# --- 2. Les renvois d'une page à l'autre deviennent des renvois internes -----------------------------------
# `<fichier>.md#ancre` -> `#ancre` ; `<fichier>.md` seul -> l'ancre du titre `#` du fichier ; `../images/` -> `images/`.
: > "$TMP/renvois.sed"
while IFS= read -r fichier; do
    id=$(sed -n '1s/^#.*{[[:space:]]*#\([A-Za-z0-9_-]*\)[[:space:]]*}[[:space:]]*$/\1/p' "$GUIDE/$LANGUE/$fichier")
    [ -n "$id" ] || { echo "$fichier: first line has no { #anchor }" >&2; exit 1; }
    motif=$(printf '%s' "$fichier" | sed 's/[.]/\\./g')
    printf 's|](%s#|](#|g\ns|](%s)|](#%s)|g\n' "$motif" "$motif" "$id" >> "$TMP/renvois.sed"
done < "$TMP/ordre.txt"
printf 's|](\\.\\./images/|](images/|g\n' >> "$TMP/renvois.sed"
cp -R "$GUIDE/images" "$TMP/images"

# --- 3. Les repères (!!!) et les onglets (===) de MkDocs deviennent des blocs que Pandoc comprend -----------
# `!!! type "Titre"` + contenu indenté de 4 espaces -> `::: {.admonition .type}` ; `=== "Titre"` -> `::: {.tab}`.
# Les onglets se rendent l'un sous l'autre, chacun précédé de son titre.
convertit() {
    awk '
        function ferme() { if (bloc) { print ""; print ":::"; print ""; bloc = 0 } }
        {
            ligne = $0
            if (!bloc && ligne ~ /^```/) { clos = !clos }
            if (clos && !bloc) { print ligne; next }
            if (bloc) {
                if (ligne == "" ) { print ""; next }
                if (substr(ligne, 1, 4) == "    ") { print substr(ligne, 5); next }
                ferme()
            }
            if (ligne ~ /^```/) { print ligne; next }
            if (ligne ~ /^!!! [A-Za-z]+/) {
                type = ligne; sub(/^!!! /, "", type); titre = ""
                if (match(type, /[[:space:]]+"/)) {
                    titre = substr(type, RSTART + RLENGTH); sub(/"[[:space:]]*$/, "", titre)
                    type = substr(type, 1, RSTART - 1)
                }
                if (titre == "") titre = toupper(substr(type, 1, 1)) substr(type, 2)
                print ""; print "::: {.admonition .adm-" type "}"; print ""
                print "::: {.admonition-title}"; print titre; print ":::"; print ""
                bloc = 1; next
            }
            if (ligne ~ /^=== "/) {
                titre = ligne; sub(/^=== "/, "", titre); sub(/"[[:space:]]*$/, "", titre)
                print ""; print "::: {.tab}"; print ""
                print "::: {.tab-title}"; print titre; print ":::"; print ""
                bloc = 1; next
            }
            print ligne
        }
        END { ferme() }
    '
}

: > "$TMP/guide.md"
while IFS= read -r fichier; do
    sed -f "$TMP/renvois.sed" "$GUIDE/$LANGUE/$fichier" | convertit >> "$TMP/guide.md"
    printf '\n\n' >> "$TMP/guide.md"
done < "$TMP/ordre.txt"

# --- 4. La couverture, le gabarit et le pied de version ----------------------------------------------------
cat > "$TMP/couverture.html" <<EOT
<section id="cover">
<img class="insigne" src="images/insigne-ready-room.svg" alt="">
<p class="marque">Squadron Ready Room</p>
<p class="titre-guide">$TITRE</p>
<p class="version-guide">Version $VERSION</p>
<p class="langue-guide">$LANGUE_NOM</p>
</section>
EOT

# Pas d'attribut `lang` sur <html> : avec lang="fr", fontconfig écarte les polices 400 de l'application (il leur juge
# une couverture du français incomplète) et met tout le texte en semi-gras ; sans lui, la graisse demandée est tenue.
cat > "$TMP/gabarit.html" <<'EOT'
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>$pagetitle$</title>
</head>
<body>
$for(include-before)$
$include-before$
$endfor$
<nav id="TOC" role="doc-toc">
<p class="toc-title">$toc-title$</p>
$table-of-contents$
</nav>
$body$
</body>
</html>
EOT

case "$LANGUE" in
    en) SOMMAIRE="Contents"; PAGE="Page" ;;
    fr) SOMMAIRE="Sommaire"; PAGE="Page" ;;
esac
cat > "$TMP/meta.css" <<EOT
@page { @top-left { content: "Squadron Ready Room · $TITRE"; } @bottom-left { content: "$PAGE " counter(page); } @bottom-right { content: "Version $VERSION"; } }
@page :first { @top-left { content: none; } @top-right { content: none; } @bottom-left { content: none; } @bottom-right { content: none; } }
EOT

# --- 5. Pandoc, puis WeasyPrint ---------------------------------------------------------------------------------
pandoc -f markdown-smart-tex_math_dollars-raw_html -t html5 --no-highlight --toc --toc-depth=2 \
    --template="$TMP/gabarit.html" --include-before-body="$TMP/couverture.html" \
    -V toc-title="$SOMMAIRE" --metadata pagetitle="Squadron Ready Room — $TITRE" \
    -o "$TMP/guide.html" "$TMP/guide.md"

# Chaque mot d'un bloc de code est enveloppé dans <span class="m"> (pdf.css : nowrap) : une commande ne se coupe qu'aux espaces.
awk 'BEGIN { RS = "\001" }
    function enveloppe(bloc,    debut, fin, texte) {
        debut = index(bloc, "<code")
        if (debut == 0) return bloc
        texte = substr(bloc, debut)
        debut = debut + index(texte, ">")
        fin = index(bloc, "</code>")
        if (fin == 0) return bloc
        texte = substr(bloc, debut, fin - debut)
        gsub(/[^ \t\n]+/, "<span class=\"m\">&</span>", texte)
        return substr(bloc, 1, debut - 1) texte substr(bloc, fin)
    }
    {
        sortie = ""; reste = $0
        while ((i = index(reste, "<pre")) > 0) {
            sortie = sortie substr(reste, 1, i - 1); reste = substr(reste, i)
            j = index(reste, "</pre>")
            if (j == 0) break
            sortie = sortie enveloppe(substr(reste, 1, j + 5)); reste = substr(reste, j + 6)
        }
        printf "%s%s", sortie, reste
    }' "$TMP/guide.html" > "$TMP/guide-code.html"
mv "$TMP/guide-code.html" "$TMP/guide.html"

"$WEASYPRINT" -s "$GUIDE/pdf.css" -s "$TMP/meta.css" "$TMP/guide.html" "$SORTIE"
echo "$SORTIE"
