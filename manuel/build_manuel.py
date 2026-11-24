#!/usr/bin/env python3.12
"""Lot « Le Manuel Pilote, le socle » : le build du manuel.

    python3.12 -B manuel/build_manuel.py             construit (depuis la racine du dépôt)
    python3.12 -B manuel/build_manuel.py --verifier  n'écrit rien ; code 1 si la sortie ou revisions.json diffèrent

Lit `manuel/contenu/` (la couverture, les quatre sections et l'annexe A, dix-sept planches SVG, et `vues.json`, la table qui
traduit chaque écran de l'application en ancre du manuel : le contenu est du CdP, posé tel quel), `manuel/manuel.css`, `manuel/manuel.js`, `VERSION`, `app/static/app.js` (le dictionnaire `I18N`, lu sous
`node` comme le fait le rituel du banc) et `app/static/index.html` (les écrans à couvrir). Écrit
`app/manuel/manuel.html` (un fichier unique : CSS, JS, planches SVG et table des écrans inlinés) et `manuel/revisions.json`.

Déterministe : aucune date, aucun hasard, ordre fixe, fins de ligne LF, UTF-8. Bibliothèque standard seulement
(plus `node`, pour lire `I18N` et pour `node --check`). Un contrôle qui échoue arrête le build : code 1, un message
qui nomme le fichier et l'élément, rien d'écrit.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CONTENU = RACINE / "manuel" / "contenu"
SORTIE = RACINE / "app" / "manuel" / "manuel.html"
REVISIONS = RACINE / "manuel" / "revisions.json"
APP_JS = RACINE / "app" / "static" / "app.js"
INDEX_HTML = RACINE / "app" / "static" / "index.html"

# Les vingt-trois pièces du contenu, dans l'ordre des pages ; hors `vues.json` (la table des écrans, qui n'est pas une
# page : `controler_vues`), aucun autre fichier de `manuel/contenu/` n'est lu.
VUES = "vues.json"
COUVERTURE = "00_couverture.html"
SECTIONS = ("10_section_0.html", "20_section_I.html", "30_section_II.html", "40_section_III.html",
            "50_annexe_A.html")
FIGURES = ("fig_0-1.svg", "fig_1-1.svg", "fig_1-2.svg", "fig_1-3.svg", "fig_1-4.svg",
           "fig_2-1.svg", "fig_2-2.svg", "fig_2-3.svg", "fig_2-4.svg", "fig_2-5.svg", "fig_2-6.svg", "fig_2-7.svg",
           "fig_3-1.svg", "fig_3-2.svg", "fig_3-3.svg", "fig_3-4.svg", "fig_A-1.svg")
PIECES = (COUVERTURE,) + SECTIONS + tuple("figures/" + f for f in FIGURES)

IMG = "/static/assets/img/"
PHOTOS = {  # data-photo -> (clair/sombre : fichier sombre, fichier Greaseboard)
    "planif": ("tile-planning.jpg", "tile-planning-light.jpg"),
    "debrief": ("tile-debrief.jpg", "tile-debrief-light.jpg"),
    "command": ("tile-command.webp", "tile-command-light.webp"),
}
STATIONS = (("s1", "I", "planif", "station_planif"), ("s2", "II", "debrief", "station_debrief"),
            ("s3", "III", "command", "station_command"))

# Seule URL externe admise, avec les espaces de noms du W3C : l'avatar Discord de la pastille du compte (addendum 1).
AVATAR_DISCORD = "https://cdn.discordapp.com/avatars/"
RE_CLE = re.compile(r"\[\[([A-Za-z0-9_]+)\]\]")
RE_REF = re.compile(r"\(\((\d+)\)\)")
VOID = {"br", "img", "hr", "meta", "link", "input", "wbr", "col", "area", "base", "embed", "source", "track"}


class ErreurBuild(Exception):
    """Un contrôle du build a échoué : le message nomme le fichier et l'élément."""


def duo(fr: str, en: str) -> str:
    return f'<span data-lang="fr">{fr}</span><span data-lang="en">{en}</span>'


# ───────────────────────────── lecture de I18N ─────────────────────────────

_NODE_I18N = r"""
const fs=require("fs"), s=fs.readFileSync(process.argv[1],"utf8");
const i=s.indexOf("const I18N = {"); let j=s.indexOf("{",i), d=0, k=j;
for(;k<s.length;k++){ if(s[k]==="{")d++; else if(s[k]==="}"){d--; if(d===0){k++;break;}} }
const o=(0,eval)("("+s.slice(j,k)+")");
process.stdout.write(JSON.stringify({fr:o.fr,en:o.en}));
"""


def lire_i18n() -> dict:
    try:
        r = subprocess.run(["node", "-e", _NODE_I18N, str(APP_JS)], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        raise ErreurBuild(f"app/static/app.js : node est introuvable ou a échoué ({e})")
    if r.returncode != 0:
        raise ErreurBuild("app/static/app.js : I18N illisible sous node : " + r.stderr.strip()[:300])
    d = json.loads(r.stdout)
    if not isinstance(d.get("fr"), dict) or not isinstance(d.get("en"), dict):
        raise ErreurBuild("app/static/app.js : I18N sans fr ou sans en")
    return d


# ───────────────────────────── la résolution ─────────────────────────────

class Resolveur(HTMLParser):
    """Résout `[[clé]]` et `((n))` et contrôle la structure (parité fr/en, pas d'élément de même balise dans un
    élément `data-lang`) ; recopie le reste tel quel. Les blocs suivis (`.para`, `.advis`, `figure.plate`)
    sont relevés avec leur HTML résolu. `passif` : ne transforme rien (contrôle de la page assemblée)."""

    def __init__(self, fichier: str, i18n: dict, svg: bool = False, charge_figure=None, passif: bool = False):
        super().__init__(convert_charrefs=False)
        self.fichier = fichier
        self.i18n = i18n
        self.svg = 1 if svg else 0
        self.charge_figure = charge_figure
        self.passif = passif
        self.sortie: list[str] = []
        self.blocs: list[tuple[str, str, str]] = []  # (id, genre, html résolu)
        self.cles: set[str] = set()
        self.pile = [{"tag": None, "lang": None, "pend": None, "bloc": None, "debut": 0, "brut": None}]

    # -- écriture --
    def _ecrire(self, s: str) -> None:
        self.sortie.append(s)

    def texte_resolu(self) -> str:
        return "".join(self.sortie)

    def _erreur(self, msg: str) -> None:
        l, c = self.getpos()
        raise ErreurBuild(f"{self.fichier} (ligne {l}) : {msg}")

    def _langue(self):
        for e in reversed(self.pile):
            if e["lang"]:
                return e["lang"]
        return None

    # -- les balises --
    def _ouvrir(self, tag: str, attrs, brut: str, auto: bool) -> None:
        a = {k: (v if v is not None else "") for k, v in attrs}
        lang = a.get("data-lang")
        if lang is not None and lang not in ("fr", "en"):
            self._erreur(f'<{tag}> : data-lang="{lang}" (fr ou en seulement)')
        for e in self.pile[1:]:
            if e["lang"] and e["tag"] == tag:
                self._erreur(f'<{tag}> dans un élément <{tag} data-lang="{e["lang"]}"> de même balise')
        parent = self.pile[-1]
        if parent["pend"] is not None:
            if lang != "en" or tag != parent["pend"]:
                self._erreur(f'<{parent["pend"]} data-lang="fr"> n\'a pas pour frère suivant un <{parent["pend"]} data-lang="en">')
            parent["pend"] = None
        else:
            if lang == "en":
                self._erreur(f'<{tag} data-lang="en"> sans frère <{tag} data-lang="fr"> avant lui')
            if lang == "fr":
                parent["pend"] = tag
        classes = a.get("class", "").split()
        bloc = None
        if a.get("id") and not auto:
            if tag == "div" and "para" in classes:
                bloc = (a["id"], "para")
            elif tag == "div" and "advis" in classes:
                bloc = (a["id"], "advis")
            elif tag == "figure" and "plate" in classes:
                bloc = (a["id"], "plate")
        debut = len("".join(self.sortie)) if bloc else 0
        brut_ecrit = brut
        inline = None
        if not self.passif and tag == "figure" and "plate" in classes and a.get("data-src"):
            if not a.get("id"):
                self._erreur("<figure class=\"plate\" data-src> sans id")
            brut_ecrit = re.sub(r'\s+data-src="[^"]*"', "", brut)
            inline = self.charge_figure(a["id"], a["data-src"], self)
        self._ecrire(brut_ecrit)
        if inline is not None:
            self._ecrire(inline)
        if tag == "svg":
            self.svg += 1
        if not (auto or tag in VOID):
            m = re.match(r"<([^\s/>]+)", brut)
            self.pile.append({"tag": tag, "lang": lang, "pend": None, "bloc": bloc, "debut": debut,
                              "brut": m.group(1) if m else tag})
        elif tag == "svg" and auto:
            self.svg -= 1

    def handle_starttag(self, tag, attrs):
        self._ouvrir(tag, attrs, self.get_starttag_text(), False)

    def handle_startendtag(self, tag, attrs):
        self._ouvrir(tag, attrs, self.get_starttag_text(), True)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        e = self.pile[-1]
        if e["tag"] != tag:
            self._erreur(f"</{tag}> sans <{tag}> ouvert (en cours : <{e['tag']}>)")
        self.pile.pop()
        if e["pend"] is not None:
            self._erreur(f'<{e["pend"]} data-lang="fr"> sans frère <{e["pend"]} data-lang="en">')
        self._ecrire(f"</{e['brut']}>")
        if tag == "svg":
            self.svg -= 1
        if e["bloc"]:
            h = "".join(self.sortie)[e["debut"]:]
            self.blocs.append((e["bloc"][0], e["bloc"][1], h))

    def handle_data(self, data):
        self._ecrire(data if self.passif else self._texte(data))

    def handle_entityref(self, name):
        self._ecrire(f"&{name};")

    def handle_charref(self, name):
        self._ecrire(f"&#{name};")

    def handle_comment(self, data):
        pass

    def handle_decl(self, decl):
        if not self.passif:
            self._erreur("déclaration inattendue")
        self._ecrire(f"<!{decl}>")

    def _texte(self, data: str) -> str:
        if "[[" not in data and "((" not in data:
            return data
        lang = self._langue()

        def cle(m):
            k = m.group(1)
            fr, en = self.i18n["fr"].get(k), self.i18n["en"].get(k)
            if not isinstance(fr, str) or not fr:
                self._erreur(f"[[{k}]] : clé absente de I18N.fr")
            if not isinstance(en, str) or not en:
                self._erreur(f"[[{k}]] : clé absente de I18N.en")
            if "{wing}" in fr or "{wing}" in en:
                self._erreur(f"[[{k}]] : la valeur dépend de {{wing}}")
            self.cles.add(k)
            if lang:
                v = html.escape(fr if lang == "fr" else en, quote=False)
                return v if self.svg else f'<b class="ui">{v}</b>'
            if self.svg:
                self._erreur(f"[[{k}]] dans une planche, hors de tout élément data-lang")
            return duo(html.escape(fr, quote=False), html.escape(en, quote=False))

        data = RE_CLE.sub(cle, data)
        if not self.svg:
            data = RE_REF.sub(r'<span class="ref">\1</span>', data)
        return data


def resoudre(fichier: str, source: str, i18n: dict, figures_chargees: dict | None = None, svg: bool = False):
    """Résout un fragment ou un fichier ; renvoie le résolveur (sortie, blocs, clés)."""
    def charge(fig_id, src, parent):
        if src not in FIGURES:
            raise ErreurBuild(f"{fichier} : la planche {fig_id} demande « {src} », qui n'est pas une des planches du manuel")
        chemin = CONTENU / "figures" / src
        if not chemin.is_file():
            raise ErreurBuild(f"manuel/contenu/figures/{src} : absent")
        sub = Resolveur("figures/" + src, i18n, svg=True)
        sub.feed(chemin.read_text(encoding="utf-8"))
        sub.close()
        fin(sub)
        parent.cles |= sub.cles
        if figures_chargees is not None:
            figures_chargees[src] = True
        return habiller_svg(sub.texte_resolu().strip(), fig_id, "figures/" + src)

    r = Resolveur(fichier, i18n, svg=svg, charge_figure=charge)
    r.feed(source)
    r.close()
    fin(r)
    return r


def fin(r: Resolveur) -> None:
    if len(r.pile) != 1:
        raise ErreurBuild(f"{r.fichier} : <{r.pile[-1]['tag']}> jamais refermé")
    if r.pile[0]["pend"] is not None:
        raise ErreurBuild(f'{r.fichier} : <{r.pile[0]["pend"]} data-lang="fr"> sans frère <{r.pile[0]["pend"]} data-lang="en">')


def habiller_svg(svg: str, fig_id: str, fichier: str) -> str:
    """Préfixe chaque `id` et chaque `url(#…)` de la planche (`f11-`, `f01-`…) : aucun identifiant ne se répète dans
    la page. Un identifiant qui porte déjà le préfixe de sa planche (le `f01-arr` de la figure 0-1) n'est pas
    préfixé deux fois. L'élément `<svg>` reçoit `class="fig"` en premier attribut."""
    pfx = "f" + re.sub(r"\D", "", fig_id) + "-"

    def p(i: str) -> str:
        return i if i.startswith(pfx) else pfx + i

    svg = re.sub(r'(?<![\w-])id="([^"]*)"', lambda m: f'id="{p(m.group(1))}"', svg)
    svg = re.sub(r"url\(#([^)]*)\)", lambda m: f"url(#{p(m.group(1))})", svg)
    svg = re.sub(r'((?:xlink:)?href)="#([^"]*)"', lambda m: f'{m.group(1)}="#{p(m.group(2))}"', svg)
    m = re.match(r"<svg\b([^>]*)>", svg)
    if not m:
        raise ErreurBuild(f"{fichier} : la planche ne commence pas par <svg>")
    reste = re.sub(r'\s*\bclass="fig"', "", m.group(1))
    if 'class="fig"' not in m.group(1):
        raise ErreurBuild(f'{fichier} : <svg> sans class="fig"')
    return f'<svg class="fig"{reste}>' + svg[m.end():]


# ───────────────────────────── l'assemblage ─────────────────────────────

MARQUE = duo("Diffusion restreinte", "Restricted")
ADVIS = {"note": ("Note", "Note"), "caution": ("Prudence", "Caution"), "warning": ("Attention", "Warning")}


def attrs_de(s: str) -> dict:
    return {k: v for k, v in re.findall(r'([\w-]+)="([^"]*)"', s)}


def lire_piece(nom: str) -> str:
    chemin = CONTENU / nom
    if not chemin.is_file():
        raise ErreurBuild(f"manuel/contenu/{nom} : pièce absente")
    return chemin.read_text(encoding="utf-8")


def decouper_section(nom: str, h: str) -> dict:
    m = re.match(r"\s*<section ([^>]*)>(.*)</section>\s*$", h, re.S)
    if not m:
        raise ErreurBuild(f"{nom} : doit être un seul <section class=\"m-section\">")
    at = attrs_de(m.group(1))
    if at.get("class") != "m-section":
        raise ErreurBuild(f"{nom} : <section> sans class=\"m-section\"")
    for k in ("id", "data-num", "data-couleur", "data-couvre", "data-etat"):
        if k not in at:
            raise ErreurBuild(f"{nom} : <section id=\"{at.get('id')}\"> sans {k}")
    if at["data-etat"] not in ("ecrit", "a-venir"):
        raise ErreurBuild(f"{nom} : data-etat=\"{at['data-etat']}\" (ecrit ou a-venir)")
    if at.get("data-photo") and at["data-photo"] not in PHOTOS:
        raise ErreurBuild(f"{nom} : data-photo=\"{at['data-photo']}\" inconnu")
    inner = m.group(2)
    h2 = re.search(r'<h2 class="m-titre">(.*?)</h2>\s*', inner, re.S)
    if not h2:
        raise ErreurBuild(f"{nom} : <h2 class=\"m-titre\"> absent")
    inner = inner.replace(h2.group(0), "", 1)
    intro = re.search(r'<div class="m-intro">(<div class="para".*?</div>)\s*</div>\s*', inner, re.S)
    if not intro:
        raise ErreurBuild(f"{nom} : <div class=\"m-intro\"> absent")
    inner = inner.replace(intro.group(0), "", 1)
    h3 = re.findall(r'<h3 id="([^"]*)"><span class="hn">(.*?)</span>(.*?)</h3>', inner, re.S)
    return {"nom": nom, "attrs": at, "titre": h2.group(1), "intro": intro.group(1), "corps": inner.strip("\n"), "h3": h3}


def photo_html(photo: str, tampon: bool) -> str:
    sombre, clair = PHOTOS[photo]
    t = ('<span class="cp-stamp">' + duo("À l'usage <br>des officiers", "Officers <br>only") + "</span>") if tampon else ""
    return ('<figure class="taped">'
            f'<img class="th-dark" src="{IMG}{sombre}" alt=""><img class="th-light" src="{IMG}{clair}" alt="">'
            f'<img class="scotch" src="{IMG}rr_scotch_1.webp" alt="">{t}</figure>')


def page_section(s: dict, precedente, suivante, avec_cle_revision: bool, revision: str) -> str:
    at = s["attrs"]
    num = at["data-num"]
    etiquette = " ".join(f'{k}="{v}"' for k, v in at.items() if k != "class")
    photo = photo_html(at["data-photo"], at.get("data-tampon") == "officiers") if at.get("data-photo") else ""
    if at.get("data-tampon") and at["data-tampon"] != "officiers":
        raise ErreurBuild(f"{s['nom']} : data-tampon=\"{at['data-tampon']}\" inconnu")
    hero = (f'<div class="sec-hero{"" if photo else " sans-photo"}">{photo}'
            f'<div class="m-intro">{s["intro"]}</div></div>')
    avenir = ('<div class="m-avenir">' + duo("Chapitre à venir", "Chapter coming soon") + "</div>") if at["data-etat"] == "a-venir" else ""
    pager = ""
    if precedente or suivante:
        p = f'<a class="prev" href="#{precedente["attrs"]["id"]}">‹ {precedente["titre"]}</a>' if precedente else ""
        n = f'<a class="next" href="#{suivante["attrs"]["id"]}">{suivante["titre"]} ›</a>' if suivante else ""
        pager = f'<nav class="m-pager">{p}{n}</nav>'
    cle = ('<span class="revkey"><i></i>' + duo("modifié à cette révision", "changed in this revision") + "</span>"
           ) if avec_cle_revision else '<span class="revkey revkey-none"></span>'
    return (
        f'<section class="m-section sheet m-page" {etiquette}>\n'
        '<div class="perfo"></div>\n'
        f'<div class="mark top">{MARQUE}</div>\n'
        '<header class="runhead"><span>RR-1</span><span>'
        + duo("Manuel pilote — Ready Room", "Pilot’s manual — Ready Room")
        + f'</span><span>Section {num}</span></header>\n'
        f'<div class="sec-band"><span class="sec-no">{num}</span><h2 class="m-titre sec-t">{s["titre"]}</h2></div>\n'
        f'{hero}\n{avenir}\n{s["corps"]}\n{pager}\n'
        '<footer class="runfoot"><span>' + duo(f"Révision {revision}", f"Revision {revision}")
        + f'</span><span class="pg">{num}</span>{cle}</footer>\n'
        f'<div class="mark bot">{MARQUE}</div>\n'
        "</section>")


def page_couverture(h: str, revision: str) -> str:
    m = re.match(r'\s*<section class="m-cover" id="couverture">(.*)</section>\s*$', h, re.S)
    if not m:
        raise ErreurBuild(f"{COUVERTURE} : doit être un seul <section class=\"m-cover\" id=\"couverture\">")
    inner = m.group(1)

    def prendre(motif: str, nom: str) -> str:
        r = re.search(motif, inner, re.S)
        if not r:
            raise ErreurBuild(f"{COUVERTURE} : {nom} absent")
        return r.group(0)

    sub = prendre(r'<div class="cv-sub">.*?</div>', ".cv-sub")
    titre = prendre(r'<div class="cv-title" data-lang="fr">.*?</div><div class="cv-title" data-lang="en">.*?</div>', ".cv-title (fr puis en)")
    toc = prendre(r'<ol class="cv-toc">.*?</ol>', "ol.cv-toc")
    notice = prendre(r'<div class="cv-notice">.*?</div>', ".cv-notice")
    credit = prendre(r'<div class="cv-credit">.*?</div>', ".cv-credit")  # Lot « Manuel avant le gel » : crédit du terme 7(b) de la licence
    plaques = []
    for couleur, num, photo, cle in STATIONS:
        sombre, clair = PHOTOS[photo]
        tampon = ('<span class="cp-stamp">' + duo("À l'usage <br>des officiers", "Officers <br>only") + "</span>") if num == "III" else ""
        plaques.append(
            f'<a class="cv-plate {couleur}" href="#s-{num}">'
            f'<img class="th-dark" src="{IMG}{sombre}" alt=""><img class="th-light" src="{IMG}{clair}" alt="">'
            f'<span class="cp-no">{num}</span><span class="cp-t">[[{cle}]]</span>{tampon}</a>')
    return (
        '<section class="m-cover sheet cover m-page on" id="couverture">\n'
        '<div class="perfo"></div>\n'
        f'<div class="mark top">{MARQUE}</div>\n'
        '<div class="cv-top"><div class="cv-no">RR-1</div><div class="cv-id">'
        '<span>Ready Room<span id="cv-wing"></span></span><br>'
        '<span>' + duo(f"Révision {revision}", f"Revision {revision}") + '</span></div></div>\n'
        '<div class="cv-rule"></div>\n'
        f'{titre}\n{sub}\n'
        '<div class="cv-mid"><img class="cv-emb" src="/static/assets/img/emblem-default.png" alt="">'
        '<div class="cv-stamp">' + duo("Diffusion <br>restreinte", "Restricted <br>distribution") + '</div></div>\n'
        '<div class="cv-plates">' + "".join(plaques) + '</div>\n'
        f'{toc}\n{notice}\n{credit}\n'
        f'<div class="mark bot">{MARQUE}</div>\n'
        "</section>")


# La barre de l'application sur le manuel (addendum 1) : le balisage de `barre.html` (pièce du CdP), où la pastille du
# compte n'a que son repli « ·· » : le nom et l'avatar viennent de `/api/me`, au chargement.
BARRE = r'''<header class="mbar">
<a class="mb-btn mb-icon" href="/" title="Ready Room" aria-label="Ready Room"><span aria-hidden="true">‹</span></a>
<img class="mb-logo" alt="" src="/static/assets/img/emblem-default.png">
<span class="mb-brand"><span data-lang="fr">Manuel pilote</span><span data-lang="en">Pilot’s manual</span></span>
<span class="mb-sp"></span>
<div class="mb-act">
<button type="button" class="mb-btn" id="m-toc-btn" aria-expanded="false" aria-controls="m-toc"><span aria-hidden="true">≡</span><span class="mb-toc-l"><span data-lang="fr">Sommaire</span><span data-lang="en">Contents</span></span></button>
<div class="mb-set"><button type="button" class="mb-btn mb-icon mb-gear" aria-haspopup="true" aria-expanded="false" title="Réglages" aria-label="Réglages"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg></button>
<div class="mb-menu"><span class="mb-lang" role="group" aria-label="Langue · Language"><button type="button" data-set-lang="fr">FR</button><button type="button" data-set-lang="en">EN</button></span><span class="mb-thm" role="group" aria-label="Thème · Theme"><button type="button" data-theme-pref="dark"><span data-lang="fr">Sombre</span><span data-lang="en">Dark</span></button><button type="button" data-theme-pref="light">Greaseboard</button><button type="button" data-theme-pref="system"><span data-lang="fr">Système</span><span data-lang="en">System</span></button></span></div></div>
<div class="mb-chip"><span class="mb-av">··</span><span class="mb-name"></span></div>
</div>
</header>'''


def barre_et_sommaire(sections: list[dict]) -> str:
    barre = BARRE
    li = ['<li class="t1"><a href="#couverture"><span class="tn"></span>' + duo("Couverture", "Cover") + "</a></li>"]
    for s in sections:
        sous = "".join(f'<li class="t2"><a href="#{i}"><span class="tn">{hn}</span>{t}</a></li>' for i, hn, t in s["h3"])
        li.append(f'<li class="t1"><a href="#{s["attrs"]["id"]}"><span class="tn">{s["attrs"]["data-num"]}</span>{s["titre"]}</a>'
                  + (f"<ol>{sous}</ol>" if sous else "") + "</li>")
    toc = ('<aside class="m-toc" id="m-toc" hidden aria-label="Sommaire · Contents">\n'
           '<div class="m-toc-h"><span>' + duo("Sommaire", "Contents") + '</span>'
           '<button type="button" class="toc-x" aria-label="Fermer · Close">×</button></div>\n'
           "<ol>" + "\n".join(li) + "</ol>\n</aside>")
    return barre + "\n" + toc


ZOOM = ('<div id="m-zoom" class="zm" role="dialog" aria-modal="true" hidden>\n'
        '<div class="zm-stage"><div class="zm-box"></div></div>\n'
        '<div class="zm-bar" role="toolbar">'
        '<button type="button" class="zm-btn zm-sym" data-zm="out">&minus;</button>'
        '<button type="button" class="zm-btn" data-zm="fit"></button>'
        '<button type="button" class="zm-btn zm-sym" data-zm="in">+</button></div>\n'
        '<button type="button" class="zm-btn zm-sym zm-close" data-zm="close">&times;</button>\n</div>')


# ───────────────────────────── les révisions ─────────────────────────────

def empreinte(h: str) -> str:
    return hashlib.sha256(h.encode("utf-8")).hexdigest()[:16]


def calculer_revisions(blocs: dict[str, str], version: str, existant: dict | None) -> dict:
    """§5.7 : au premier build, tout est à `version`. Ensuite, au moins un bloc neuf, changé ou disparu fait passer
    `revision` à `version`, et chaque bloc neuf ou changé reçoit `rev = version` ; sinon rien ne bouge."""
    if existant is None:
        return {"edition": version, "revision": version, "blocs": {i: {"h": h, "rev": version} for i, h in blocs.items()}}
    anciens = existant.get("blocs", {})
    changes = {i for i, h in blocs.items() if i not in anciens or anciens[i].get("h") != h}
    disparus = set(anciens) - set(blocs)
    if not changes and not disparus:
        return {"edition": existant["edition"], "revision": existant["revision"],
                "blocs": {i: {"h": h, "rev": anciens[i]["rev"]} for i, h in blocs.items()}}
    return {"edition": existant["edition"], "revision": version,
            "blocs": {i: {"h": h, "rev": (version if i in changes else anciens[i]["rev"])} for i, h in blocs.items()}}


def serialiser_revisions(rev: dict) -> bytes:
    return (json.dumps(rev, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


# ───────────────────────────── les contrôles de la sortie ─────────────────────────────

def controler_couverture(sections: list[dict]) -> None:
    """§5.4.4 : les écrans de l'application (`id="view-…"` d'index.html, plus trois fenêtres) = la réunion des `data-couvre`."""
    src = INDEX_HTML.read_text(encoding="utf-8")
    attendu = set(re.findall(r'(?<![\w-])id="(view-[^"]*|modal-overlay|modal-deposer|modal-report)"', src))
    couverts: set[str] = set()
    for s in sections:
        couverts |= set(s["attrs"]["data-couvre"].split())
    manque, trop = sorted(attendu - couverts), sorted(couverts - attendu)
    if manque or trop:
        raise ErreurBuild("couverture des écrans : manquent au manuel : " + (", ".join(manque) or "rien")
                          + " · en trop dans le manuel : " + (", ".join(trop) or "rien"))


def controler_vues(sections: list[dict]) -> dict:
    """Lot « Manuel : le bouton ? » : `vues.json` (écran de l'application -> ancre du manuel) est lue et contrôlée, puis rendue.
    Chaque écran de la réunion des `data-couvre` y a une entrée ; aucune entrée ne nomme un écran hors de cette réunion ;
    l'ancre d'un écran est l'id d'un `<h3>` de sa section (celle dont le `data-couvre` le nomme) ou d'une section
    à `data-couvre` vide (une annexe)."""
    chemin = CONTENU / VUES
    try:
        table = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ErreurBuild(f"manuel/contenu/{VUES} : illisible ({e})")
    if not isinstance(table, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in table.items()):
        raise ErreurBuild(f"manuel/contenu/{VUES} : doit être un objet « écran » -> « ancre »")
    couverts: dict[str, set[str]] = {}
    libres: set[str] = set()
    for s in sections:
        ecrans = s["attrs"]["data-couvre"].split()
        ancres = {i for i, _, _ in s["h3"]}
        if not ecrans:
            libres |= ancres
        for e in ecrans:
            couverts[e] = ancres
    manque = sorted(set(couverts) - set(table))
    if manque:
        raise ErreurBuild(f"manuel/contenu/{VUES} : écran sans entrée : " + ", ".join(manque))
    trop = sorted(set(table) - set(couverts))
    if trop:
        raise ErreurBuild(f"manuel/contenu/{VUES} : écran hors du manuel : " + ", ".join(trop))
    for ecran in sorted(table):
        if table[ecran] not in couverts[ecran] | libres:
            raise ErreurBuild(f"manuel/contenu/{VUES} : l'écran {ecran} pointe sur « {table[ecran]} », qui n'est le <h3> d'aucune section qui le couvre")
    return table


def controler_sortie(page: str, i18n: dict) -> None:
    ids = re.findall(r'(?<![\w-])id="([^"]*)"', page)
    vus, doubles = set(), []
    for i in ids:
        if i in vus:
            doubles.append(i)
        vus.add(i)
    if doubles:
        raise ErreurBuild("identifiants répétés dans la sortie : " + ", ".join(sorted(set(doubles))))
    for motif in ("[[", "(("):
        if motif in page:
            i = page.index(motif)
            raise ErreurBuild(f"sortie : « {motif} » restant : …{page[max(0, i - 40):i + 40]!r}…")
    for u in re.findall(r"https?://[^\s\"'<>)]*", page):
        if not u.startswith(("http://www.w3.org/", AVATAR_DISCORD)):
            raise ErreurBuild(f"sortie : URL externe {u!r}")
    nfr, nen = page.count('data-lang="fr"'), page.count('data-lang="en"')
    if nfr != nen:
        raise ErreurBuild(f"sortie : parité data-lang rompue (fr {nfr}, en {nen})")
    # la page assemblée repasse au contrôle de structure (parité, balises imbriquées)
    p = Resolveur("app/manuel/manuel.html", i18n, passif=True)
    p.feed(page)
    p.close()
    fin(p)
    scripts = re.findall(r"<script>(.*?)</script>", page, re.S)
    for n, code in enumerate(scripts, 1):
        code = re.sub(r"<!--.*?-->", "", code, flags=re.S)
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / f"script{n}.js"
            f.write_text(code, encoding="utf-8")
            try:
                r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True, timeout=60)
            except (OSError, subprocess.SubprocessError) as e:
                raise ErreurBuild(f"sortie : node --check impossible ({e})")
            if r.returncode != 0:
                raise ErreurBuild(f"sortie : le <script> n°{n} échoue à node --check : {r.stderr.strip()[:300]}")


# ───────────────────────────── le build ─────────────────────────────

def construire() -> tuple[bytes, bytes]:
    for nom in PIECES:
        if not (CONTENU / nom).is_file():
            raise ErreurBuild(f"manuel/contenu/{nom} : pièce absente")
    version = (RACINE / "VERSION").read_text(encoding="utf-8").strip()
    # Lot « Manuel avant le gel » : trois formes entières — `1.0122`, `RR-V1.0.0`, `RR-V1.0.0+3` ; la version passe telle quelle.
    if not (re.fullmatch(r"\d+\.\d{4}", version) or re.fullmatch(r"RR-V\d+\.\d+\.\d+", version)
            or re.fullmatch(r"RR-V\d+\.\d+\.\d+\+\d+", version)):
        raise ErreurBuild(f"VERSION : « {version} » illisible")
    i18n = lire_i18n()

    blocs: dict[str, str] = {}
    cles: set[str] = set()
    figures: dict = {}

    def traiter(nom: str):
        r = resoudre(nom, lire_piece(nom), i18n, figures)
        for i, genre, h in r.blocs:
            if i in blocs:
                raise ErreurBuild(f"{nom} : bloc « {i} » en double")
            blocs[i] = h
        cles.update(r.cles)
        return r.texte_resolu()

    couv = traiter(COUVERTURE)
    sections = [decouper_section(n, traiter(n)) for n in SECTIONS]
    ids = [s["attrs"]["id"] for s in sections]
    if ids != ["s-0", "s-I", "s-II", "s-III", "s-A"]:
        raise ErreurBuild("les sections doivent être s-0, s-I, s-II, s-III, s-A, dans cet ordre : " + ", ".join(ids))
    manquent = [f for f in FIGURES if f not in figures]
    if manquent:
        raise ErreurBuild("planches jamais appelées par le contenu : " + ", ".join(manquent))
    controler_couverture(sections)
    vues = controler_vues(sections)

    hachis = {i: empreinte(h) for i, h in blocs.items()}
    existant = json.loads(REVISIONS.read_text(encoding="utf-8")) if REVISIONS.is_file() else None
    rev = calculer_revisions(hachis, version, existant)
    marques = {i for i, b in rev["blocs"].items() if b["rev"] == rev["revision"] and rev["revision"] != rev["edition"]}

    pages = [resoudre("gabarit (couverture)", page_couverture(couv, rev["revision"]), i18n).texte_resolu()]
    for n, s in enumerate(sections):
        ids_page = set(re.findall(r'(?<![\w-])id="([^"]*)"', s["corps"] + s["intro"]))
        pages.append(page_section(s, sections[n - 1] if n > 0 else None, sections[n + 1] if n + 1 < len(sections) else None,
                                  bool(ids_page & marques), rev["revision"]))
    corps = "\n".join(pages)

    # la barre de révision (une classe `rev`) et le titre des avertissements : après l'empreinte, qui porte sur le HTML résolu
    for i in sorted(marques):
        corps, n = re.subn(r'(<(?:div|figure) class="(?:para|advis|plate)[^"]*)(" id="' + re.escape(i) + r'")', r"\1 rev\2", corps)
        if n != 1:
            raise ErreurBuild(f"bloc « {i} » : barre de révision impossible à poser ({n} occurrences)")

    def titre_advis(m):
        fr, en = ADVIS[m.group(2)]
        return m.group(1) + '<div class="advis-h">' + duo(fr, en) + "</div>"

    corps = re.sub(r'(<div class="advis (note|caution|warning)[^"]*"[^>]*>)', titre_advis, corps)
    chrome = resoudre("gabarit", barre_et_sommaire(sections), i18n).texte_resolu()

    css = (RACINE / "manuel" / "manuel.css").read_text(encoding="utf-8").strip("\n")
    js = (RACINE / "manuel" / "manuel.js").read_text(encoding="utf-8").strip("\n")
    page = (
        '<!doctype html>\n<html lang="fr" data-theme="dark">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>Manuel pilote — Squadron Ready Room</title>\n'
        '<link rel="icon" href="/static/assets/marque/favicon.ico" sizes="16x16 32x32 48x48">\n'
        '<link rel="icon" href="/static/assets/marque/favicon.svg" type="image/svg+xml">\n'
        '<link rel="apple-touch-icon" href="/static/assets/marque/apple-touch-icon.png">\n'
        '<link rel="manifest" href="/static/manifest.webmanifest">\n'
        f"<style>\n{css}\n</style>\n<script>\n{js}\n</script>\n</head>\n"
        f'<body lang="fr"><script type="application/json" id="m-vues">{json.dumps(vues, sort_keys=True)}</script>\n{chrome}\n<main class="chemise">\n{corps}\n</main>\n{ZOOM}\n</body>\n</html>\n')
    page = page.replace("\r\n", "\n")
    controler_sortie(page, i18n)
    return page.encode("utf-8"), serialiser_revisions(rev)


def main(argv: list[str]) -> int:
    verifier = "--verifier" in argv
    inconnus = [a for a in argv if a not in ("--verifier",)]
    if inconnus:
        print("usage : python3.12 -B manuel/build_manuel.py [--verifier]", file=sys.stderr)
        return 2
    try:
        sortie, revisions = construire()
    except ErreurBuild as e:
        print(f"manuel : {e}", file=sys.stderr)
        return 1
    cibles = ((SORTIE, sortie, "app/manuel/manuel.html"), (REVISIONS, revisions, "manuel/revisions.json"))
    if verifier:
        ecarts = []
        for chemin, octets, nom in cibles:
            if not chemin.is_file():
                ecarts.append(f"  absent : {nom}")
            elif chemin.read_bytes() != octets:
                ecarts.append(f"  différent : {nom}")
        if ecarts:
            print("manuel : à reconstruire (python3.12 -B manuel/build_manuel.py)")
            print("\n".join(ecarts))
            return 1
        print("manuel : à jour")
        return 0
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    for chemin, octets, _ in cibles:
        chemin.write_bytes(octets)
    r = json.loads(revisions)
    print(f"manuel : {len(sortie)} octets · édition {r['edition']} · révision {r['revision']} · {len(r['blocs'])} blocs suivis")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
