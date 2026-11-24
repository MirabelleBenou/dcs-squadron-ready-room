#!/usr/bin/env python3
"""Parseur de blocs a profondeur — Squadron Ready Room.

INSTRUMENT DE MESURE DU CdP. C'est lui qui produit toutes les grandeurs CSS
citees dans le checkpoint et dans les portes des briefs. Une porte chiffree ne
s'ecrit jamais sans avoir ete mesuree ici, sur le zip, jamais d'apres un rapport.

  python3 cssrules.py <fichier.css>     mesure et affiche
  python3 cssrules.py --check <f.css>   compare aux valeurs de reference v0.98

PIEGE DOCUMENTE — le compte de l'etage module. La sonde porte sur le litteral
`#screen-app[data-module="debrief"]`. Une sonde par sous-chaine sur le seul
`[data-module="debrief"]` attrape en plus deux regles de NEGATION
(`#screen-app:not([data-module="debrief"]) …`) et surevalue de 2. C'est l'erreur
qui a fait ecrire 94 au lieu de 92 dans le brief du lot 1.4c-2.


Regle = bloc { } dont le prelude n'est pas une at-rule enveloppe (@media,
@supports, @layer, @container, @keyframes) et qui n'est pas une etape de
@keyframes. Les @font-face SONT des at-rules a declarations : le checkpoint
v0.87 les compte hors total (9 @font-face). On expose les deux comptes.

Usage: cssrules.py <fichier.css> [...]
"""
import re
import sys
from collections import OrderedDict

ENVELOPPES = ("@media", "@supports", "@layer", "@container", "@keyframes",
              "@-webkit-keyframes", "@document", "@scope")


def strip_comments(src: str) -> str:
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def parse(src: str):
    """Retourne la liste des regles : (prelude, chaine_d_enveloppes)."""
    src = strip_comments(src)
    regles = []
    pile = []          # preludes des blocs ouverts
    buf = []
    i = 0
    n = len(src)
    while i < n:
        c = src[i]
        if c in "\"'":
            q = c
            buf.append(c)
            i += 1
            while i < n:
                buf.append(src[i])
                if src[i] == "\\":
                    i += 2
                    if i <= n:
                        continue
                if src[i] == q:
                    i += 1
                    break
                i += 1
            continue
        if c == "{":
            prelude = " ".join("".join(buf).split())
            pile.append(prelude)
            buf = []
            i += 1
            continue
        if c == "}":
            if pile:
                prelude = pile.pop()
                dans_keyframes = any(
                    p.lower().startswith(("@keyframes", "@-webkit-keyframes"))
                    for p in pile)
                est_enveloppe = prelude.lower().startswith(ENVELOPPES)
                if not est_enveloppe and not dans_keyframes:
                    regles.append((prelude, tuple(pile)))
            buf = []
            i += 1
            continue
        if c == ";" and not pile:
            buf = []          # @import / @charset au niveau racine
            i += 1
            continue
        buf.append(c)
        i += 1
    return regles


def mesure(chemin, sondes):
    src = open(chemin, encoding="utf-8").read()
    regles = parse(src)
    fontface = [r for r in regles if r[0].lower().startswith("@font-face")]
    autres_at = [r for r in regles
                 if r[0].startswith("@") and not r[0].lower().startswith("@font-face")]
    total_hors_at = len(regles) - len(fontface) - len(autres_at)

    res = OrderedDict()
    res["total (regles, @font-face et at-rules exclues)"] = total_hors_at
    res["  dont @font-face"] = len(fontface)
    res["  dont autres at-rules a declarations"] = len(autres_at)

    for nom, motif in sondes:
        cpt = 0
        for prelude, env in regles:
            if prelude.startswith("@"):
                continue
            contexte = " ".join(env) + " " + prelude
            if motif(prelude, env, contexte):
                cpt += 1
        res[nom] = cpt

    # accolades
    sans_com = strip_comments(src)
    res["accolades { }"] = f"{src.count('{')}/{src.count('}')} brut · " \
                           f"{sans_com.count('{')}/{sans_com.count('}')} hors commentaires"
    return res


def branche(prelude, cible):
    """Vrai si AU MOINS une branche du selecteur groupe porte la cible."""
    return any(cible in b for b in prelude.split(","))


def toutes_branches(prelude, cible):
    return all(cible in b for b in prelude.split(",") if b.strip())


SONDES = [
    ('#screen-app[data-module="debrief"]',
     lambda p, e, c: branche(p, '#screen-app[data-module="debrief"]')),
    ('#screen-app[data-module="command"]',
     lambda p, e, c: branche(p, '#screen-app[data-module="command"]')),
    ("#view-missions", lambda p, e, c: branche(p, "#view-missions")),
    ("#view-session", lambda p, e, c: branche(p, "#view-session")),
    ("#view-flight", lambda p, e, c: branche(p, "#view-flight")),
    ("#modal-deposer", lambda p, e, c: branche(p, "#modal-deposer")),
    ("#modal-report", lambda p, e, c: branche(p, "#modal-report")),
    ('palier compact (html[data-layout="compact"])',
     lambda p, e, c: 'data-layout="compact"' in c),
    ('palier intermediate',
     lambda p, e, c: 'data-layout="intermediate"' in c),
    ('palier large',
     lambda p, e, c: 'data-layout="large"' in c),
    ('palier wide',
     lambda p, e, c: 'data-layout="wide"' in c),
]

# --- Sondes de negation (lot E1, v0.9929) -------------------------------------
# Une sonde de palier travaille par SOUS-CHAINE : `html:not([data-layout="X"])`
# contient `data-layout="X"` et se fait donc compter par la sonde du palier X,
# alors que la regle ne s'y applique JAMAIS. Mesure : au v0.9918 le palier large
# affichait 38 regles dont 24 negations -- il n'en avait que 14 de dediees.
# Le lot E1 a converti les 23 dernieres negations en selecteurs positifs.
# Ces quatre compteurs doivent rester a ZERO : un retour a une valeur non nulle
# signale une regle ecrite en negation, donc une sonde de palier qui ment.
NEGATIONS = [
    ('negations compact', 'compact'),
    ('negations intermediate', 'intermediate'),
    ('negations large', 'large'),
    ('negations wide', 'wide'),
]

# Valeurs de reference, mesurees sur readyroom_v0_92.zip le 9 aout 2026 par
# Opus-CDP-ReadyRoom-v11, apres acceptation du lot 1.6 (modale Rapport).
# Servent a verifier que l'instrument n'a pas derive, pas a valider un livrable.
#
# Historique, pour lire un ecart sans rouvrir le depot :
#   v0.89 -> v0.90 : total 735 -> 745, catalogue 98 -> 107 (+14 chassis, -5
#   bandeau mort), missions 42 -> 41 (-3 .page-head, +2 .mg), session 98 -> 99
#   (+1 regle transitoire .nato, A RETIRER AU LOT 1.4d), compact 93 -> 99.
#   v0.90 -> v0.91 : total 745 -> 705 (-40, portage de Session au vocabulaire
#   maquette), catalogue 107 -> 108 (+1 .subsec compact), session 99 -> 58
#   (-41 : 97 regles d'ancien vocabulaire substituees, dont le retrait de la
#   regle transitoire .nato), compact 99 -> 108. Missions, Vol et les deux
#   modales inchangees : 41 / 36 / 68 / 10.
#   v0.91 -> v0.92 : total 705 -> 707 (+6 regles creees, -2 absorbees par le
#   chassis compact groupe, -1 .report-line .t.dead couleur semantique eteinte,
#   -1 .field .fline vocabulaire mort). report 10 -> 35 (+22 branches ajoutees
#   a des regles existantes, +6 creees, -2 absorbees, -1 .t.dead : AUCUNE regle
#   de chassis dupliquee). deposer 68 -> 67 (-1 .fline). compact 108 -> 107
#   (-2 absorbees, +1 .btn/.btn-sm). Catalogue, missions, session, vol : figes.
#   Phase 1 du plan v4 close sur ce lot.
#   v0.92 -> v0.93 : lot 2.1 (nommage + note). total 707 -> 709 : DEUX regles
#   creees seulement -- #modal-deposer .field textarea (min-height/resize) et
#   html[data-layout="compact"] #view-flight .kick (clamp 2 lignes). session
#   58 -> 65 : AUCUNE regle creee, +7 rebranchements des regles .field de
#   #modal-deposer vers #view-session (selecteurs groupes comptes dans les deux
#   branches). vol 36 -> 37 et compact 107 -> 108 : le clamp .kick. deposer
#   67 -> 68 : la textarea. Catalogue, missions, report, intermediate, large :
#   figes. Phase 2 ouverte sur ce lot.
REFERENCE = {
    "total (regles, @font-face et at-rules exclues)": 754,
    '#screen-app[data-module="debrief"]': 108,
    '#screen-app[data-module="command"]': 43,
    "#view-missions": 41,
    "#view-session": 65,
    "#view-flight": 37,
    "#modal-deposer": 68,
    "#modal-report": 35,
    'palier compact (html[data-layout="compact"])': 109,
}
#   v0.93 -> v0.94 : lot 2.2a (sauvegarde au deploiement). AUCUNE valeur ne
#   change : le lot ne touche aucun fichier sous app/ -- perimetre limite a
#   Dockerfile, docker-compose.yml, entrypoint.sh, RUN.md, release.py,
#   CHANGELOG.md, .gitignore. Les huit comptes restent ceux de la v0.93.
#   v0.94 -> v0.95 : lot 2.2b (escadrille en donnee). AUCUNE valeur ne change :
#   le lot ne touche aucun fichier de app/static/ -- 33 fichiers aux empreintes
#   identiques. Les huit comptes restent ceux de la v0.93, inchanges depuis.
#   v0.95 -> v0.96 : lot 2.3 (campagne en entite). total 709 -> 711 : DEUX
#   regles creees -- .camp au catalogue (styles.css:460) et sa variante au
#   palier compact (styles.css:579). catalogue 108 -> 109 (+1 .camp), compact
#   108 -> 109 (+1 .camp compacte). Missions, session, vol, deposer, report :
#   figes. Phase 2 close sur ce lot.
#   v0.96 -> v0.97 : lot 3.1 (socle du Centre de Commandement). AUCUNE valeur
#   ne change : le lot ne livre aucun ecran et ne touche aucun fichier de
#   app/static/ -- `diff -rq` entre v0.96 et v0.97 ne rapporte aucune
#   difference (porte P7, verifiee en recette). Phase 3 ouverte sur ce lot.
#
#   v0.97 -> v0.98 : lot 3.2a (la porte du Centre de Commandement). catalogue
#   109 -> 110 : la regle compacte de .camp (styles.css:579) est portee au
#   perimetre du catalogue -- DETTE 8 SOLDEE, les deux regles .camp sont
#   desormais scopees symetriquement. Le TOTAL NE BOUGE PAS et le compact
#   reste a 109 : la regle porte toujours le palier, elle est simplement
#   comptee par les deux sondes. L'elargissement de .stations-grid 760 ->
#   840px est lui aussi une declaration modifiee : zero delta. La tuile du CC
#   ne coute AUCUNE regle neuve -- .hidden, .station-badge-construction et
#   .btn:disabled existaient deja. Les deux regles de fond vivent dans le
#   <style> inline d'index.html : hors instrument par construction.
#
#   NEUVIEME SONDE, posee au lot 3.2b-1 (arbitrage A-2 du 16 aout) :
#   `#screen-app[data-module="command"]`, valeur de depart 0. Sans elle les
#   regles du Centre de Commandement n'apparaitraient que dans le TOTAL, qui
#   deviendrait un fourre-tout muet -- une derive de 15 regles au CC serait
#   indiscernable d'une derive de 15 regles ailleurs. MEME PIEGE QUE LE
#   CATALOGUE : la sonde porte sur le litteral COMPLET. Une sonde par
#   sous-chaine sur `[data-module="command"]` attraperait les regles de
#   negation `#screen-app:not([data-module="command"])`.
#
#   BLOC REFERENCE EN DERIVE ENTRE V0.98 ET V0.9903 (trois lots : 3.2b-2/c/d
#   premier temps), jamais reporte avant ce lot -- observation faite au lot
#   3.2d second temps (19 aout 2026, Opus-CDP-ReadyRoom), SANS EFFET sur les
#   portes des briefs concernes : chaque porte est un delta contre la version
#   precedente, remesure en seance a chaque fois, jamais contre ce bloc.
#   `--check` etait deja hors service avant meme ce lot.
#
#   v0.9903 -> v0.9904 (lot 3.2d, second temps -- accès à l'application,
#   19 aout 2026) : total 748 -> 749 (+1, R14 creee). command 35 -> 36
#   (+1 : la meme R14, `#screen-app[data-module="command"] .cc-chip .qual`,
#   litteral complet -- composition verifiee a l'enumeration : les 35
#   d'origine + R14, cf. bundle de preuve). TOUT LE RESTE FIGE : debrief
#   108, missions 41, session 65, vol 37, deposer 68, report 35, compact
#   109. Bloc porte aux valeurs de sortie de ce lot par Sonnet, sur
#   instruction explicite du brief (§3.2) -- livrable UNIQUEMENT dans le
#   bundle de preuve, jamais dans l'archive applicative.
#   v0.9904 -> v0.9905 (lot 3.2e, volet ① -- les propriétés, 20 aout 2026) :
#   total 749 -> 750 (+1, la regle .sqn-role .absent, styles.css, ecran
#   Escadrilles). command 36 -> 37 (+1 : la meme regle, litteral complet
#   #screen-app[data-module="command"] table.cc-table td.sqn-role .absent
#   -- composition verifiee a l'enumeration : les 36 d'origine + cette
#   regle, cf. bundle de preuve). TOUT LE RESTE FIGE : debrief 108,
#   missions 41, session 65, vol 37, deposer 68, report 35, compact 109.
#   Bloc porte aux valeurs de sortie de ce lot par Sonnet, sur instruction
#   explicite du brief (§12) -- livrable UNIQUEMENT dans le bundle de
#   preuve, jamais dans l'archive applicative.
#
#   v0.9905 -> v0.9906 (correctif P21, 20 aout 2026) : AUCUNE valeur ne
#   change -- le correctif ne touche que app/static/app.js (logique de
#   chargement JS), zero regle CSS creee, deplacee ou modifiee. Les neuf
#   valeurs ci-dessus restent celles de la v0.9905.
#   v0.9906 -> v0.9907 (lot 3.2e, volet ② -- l'ecusson, 21 aout 2026) :
#   total 750 -> 753 (+3, R16/R17/R18 : .sqn-crest, .sqn-crest.empty,
#   .sqn-crest.lg, styles.css, ecran Escadrilles). command 37 -> 40 (+3 :
#   les MEMES trois regles, litteral complet #screen-app[data-
#   module="command"] -- composition verifiee a l'enumeration : les 37
#   d'origine + ces trois regles, cf. bundle de preuve, script
#   d'enumeration nominative). TOUT LE RESTE FIGE : debrief 108, missions
#   41, session 65, vol 37, deposer 68, report 35, compact 109. Bloc
#   porte aux valeurs de sortie de ce lot par Sonnet, sur instruction
#   explicite du brief (§11, P37) -- livrable UNIQUEMENT dans le bundle
#   de preuve, jamais dans l'archive applicative.
#
#   v0.9907 -> v0.9908 (lot 3.3 « Les Droits », 21 aout 2026) : total
#   753 -> 756 (+3, R19/R20/R21 : .cc-office, .cc-office.porte,
#   table.cc-table td.cc-num, styles.css, ecran Droits -- bloc 5 et
#   tableau de reference). command 40 -> 43 (+3 : les MEMES trois
#   regles, litteral complet #screen-app[data-module="command"] --
#   composition verifiee a l'enumeration : les 40 d'origine + ces trois
#   regles, cf. bundle de preuve). TOUT LE RESTE FIGE : debrief 108,
#   missions 41, session 65, vol 37, deposer 68, report 35, compact 109.
#   Bloc porte aux valeurs de sortie de ce lot par Sonnet, sur
#   instruction explicite du brief (§9①) -- livrable UNIQUEMENT en
#   fichier separe (hors bundle de preuve, hors archive applicative),
#   motif : deplier plusieurs megaoctets pour atteindre quelques
#   kilooctets coute du contexte a chaque reprise.
#
#   v0.9908 -> v0.9909 (correctif, 22 aout 2026) : LES NEUF SONDES SONT
#   INCHANGEES -- total 756, debrief 108, command 43, missions 41,
#   session 65, vol 37, deposer 68, report 35, compact 109. Le correctif
#   ne touche ni app/static/styles.css ni aucune autre feuille : deux
#   attributs `data-i18n` deviennent `data-i18n-html` dans index.html,
#   une passe est ajoutee a `setLang()` (app/static/app.js) -- zero regle
#   CSS creee, deplacee ou modifiee. Confirme par --check ci-dessous
#   contre ce meme bloc REFERENCE, valeurs identiques a la v0.9908.
#
#   v0.9909 -> v0.9910 (lot 3.4 « Campagnes », 22 aout 2026) : LES NEUF
#   SONDES SONT INCHANGEES -- total 756, debrief 108, command 43,
#   missions 41, session 65, vol 37, deposer 68, report 35, compact 109.
#   Un ecran entier (#view-cc-campagnes : table + etats + bloc de
#   formulaire creation/edition + zone de suppression sous garde) et deux
#   rangees neuves au bloc 5 de l'ecran Droits sont livres SANS TOUCHER
#   app/static/styles.css -- `diff` entre les deux versions du fichier est
#   vide, verifie ligne a ligne, pas seulement par cet instrument. Tout le
#   mobilier reemploye existait deja : .cc-block, .cc-row, .cc-set,
#   .cc-act, .cc-hint, .cc-sub, .cc-wrap, .cc-table, .cc-state, .cc-office,
#   .cc-num, .sqn-role, .arm, .deny (bloc 5/tableau de reference, 3.3).
#   Confirme par --check ci-dessous contre ce meme bloc REFERENCE, valeurs
#   identiques a la v0.9909 -- et par mesure croisee directe des deux
#   fichiers styles.css (v0.9909 et v0.9910), sorties strictement
#   identiques, cf. bundle de preuve du lot.
#
#   v0.9910 -> v0.9911 (correctif, 22 aout 2026) : total 756 -> 754 (-2).
#   DELTA NEGATIF PAR GENERALISATION, PAS PAR SUPPRESSION DE
#   FONCTIONNALITE : les trois regles litterales qui isolaient chacune une
#   vue #view-cc-* du Centre de Commandement (#view-cc-escadrilles
#   styles.css:984, #view-cc-membres styles.css:2480, #view-cc-droits
#   styles.css:2540) sont remplacees par UNE SEULE regle par prefixe
#   d'identifiant, #screen-app:not([data-module="command"])
#   [id^="view-cc-"]{display:none !important;} -- qui couvre desormais
#   aussi #view-cc-campagnes (lot 3.4), restee non isolee faute
#   d'enumeration mise a jour dans cette liste-la (cf. brief correctif
#   §2). command NE BOUGE PAS -- 43, INCHANGEE : elle porte le litteral
#   positif #screen-app[data-module="command"], que la forme en negation
#   :not(...) ne contient pas. TOUT LE RESTE FIGE : debrief 108, missions
#   41, session 65, vol 37, deposer 68, report 35, compact 109. Effet
#   prototype dans une copie de la feuille et passe a l'instrument avant
#   execution (cf. brief §3, tableau des sondes), pas deduit. Bloc porte
#   aux valeurs de sortie de ce correctif par Sonnet, sur instruction
#   explicite du brief (§6) -- livrable UNIQUEMENT en fichier separe (hors
#   bundle de preuve, hors archive applicative).
#
#   v0.9911 -> v0.9912 (brief « Acces au module Debriefing », 22 aout
#   2026) : LES NEUF SONDES SONT INCHANGEES -- total 754, debrief 108,
#   command 43, missions 41, session 65, vol 37, deposer 68, report 35,
#   compact 109. Ce lot ne touche PAS app/static/styles.css : `diff`
#   entre les deux versions du fichier est vide, verifie octet pour
#   octet, pas seulement par cet instrument. Le sixieme bloc de l'ecran
#   Droits (« Acces au module Debriefing ») reemploie integralement le
#   gabarit .cc-block/.cc-row deja habille huit fois sur cet ecran --
#   aucune regle neuve, aucune requise. Confirme par --check ci-dessous
#   contre ce meme bloc REFERENCE, valeurs identiques a la v0.9911.
VERSION_REFERENCE = "0.9912"


def main(argv):
    check = "--check" in argv
    fichiers = [a for a in argv if not a.startswith("-")]
    for chemin in fichiers:
        print(f"\n=== {chemin} ===")
        res = mesure(chemin, SONDES)
        for k, v in res.items():
            print(f"{v:>10}  {k}")
        # Compteurs de negation (lot E1) : doivent tous valoir 0. Une valeur non
        # nulle signale une regle ecrite `:not([data-layout="X"])`, comptee par
        # la sonde du palier X alors qu'elle ne s'y applique pas.
        regles = parse(open(chemin, encoding="utf-8").read())
        total_neg = 0
        for libelle, palier in NEGATIONS:
            n = sum(1 for pre, env in regles
                    if f':not([data-layout="{palier}"]' in " ".join(env) + " " + pre)
            total_neg += n
            print(f"{n:>10}  {libelle}" + ("" if n == 0 else "   <-- SONDE FAUSSEE"))
        if total_neg:
            print(f"\n  !! {total_neg} negation(s) de palier : les comptes ci-dessus"
                  f" surestiment les paliers concernes.")
        if check:
            print(f"\n--- controle contre la reference v{VERSION_REFERENCE} ---")
            ecarts = 0
            for k, attendu in REFERENCE.items():
                obtenu = res.get(k)
                if obtenu == attendu:
                    print(f"  OK      {k} = {attendu}")
                else:
                    ecarts += 1
                    print(f"  ECART   {k} : attendu {attendu}, obtenu {obtenu}")
            print("  --> instrument conforme" if not ecarts
                  else f"  --> {ecarts} ecart(s) : soit le CSS a change, soit l'instrument a derive")


if __name__ == "__main__":
    main(sys.argv[1:])
