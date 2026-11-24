"""Rendu de l'écran A du Débrief (le dossier du pilote) -- instrument du banc v5, pour le dev comme pour le CdP.
Lecture seule. Vrai backend (servir.sh) sur une base préparée par prepare_debrief.sh, vrai app.js, aux appareils de
rendu_de.py : tablette paysage 1 150 px, tablette portrait 720 px, téléphone 393 px ; la barre de l'application et le
pied de version sont masqués de la même façon (le MASQUE de rendu_de.py, que cet instrument importe). Quatre pilotes, chacun avec sa session forgée : MistyKestrel42 (admin), Viper, Ghost et
Hunter (le dossier vide) -- A ne montre que le dossier du compte connecté.

Le contrat de l'écran A, que le lot suivant tiendra :
  - l'onglet « Pilotes » est button[data-nav="pilotes"], dans la nav du Débrief ;
  - A vit dans #view-pilotes, sur une .sheet ; ses blocs sont les enfants directs de #pilotes-mount ;
  - le lien vers F porte data-ouvre-membre="<id du pilote>".

A présent : chaque bloc en A_<pilote>_<i>-<bloc>_<palier>.png, la feuille entière en A_<pilote>_page_<palier>.png (pour
le regard, jamais comparée), et le lien vers F se clique : il doit ouvrir F du même pilote.
A absent (l'onglet n'a pas data-nav="pilotes") : l'instrument l'écrit, et rend F de chaque pilote, ouvert depuis sa
case dans l'organigramme de D, en F_<pilote>_<i>-<bloc>_<palier>.png et F_<pilote>_page_<palier>.png.

Le thème : « clair » par défaut ; « sombre » passe color_scheme au navigateur (l'application suit le thème du système)
et suffixe les fichiers en _sombre.
Le tableau, imprimé par palier, se lit sur GET /api/debrief/dossier avec la session du pilote ; il est suivi des erreurs
JS et s'écrit aussi dans mesures.json.

Usage : python3.12 -B rendu_a.py <sortie> [large,intermediaire,compact] [clair|sombre]
Joué par servir.sh : sh servir.sh <appli> python3.12 -B rendu_a.py <sortie> [paliers] [thème]
Écrit <sortie>/*.png et <sortie>/mesures.json ; imprime un tableau. Code 1 : erreur JS, ou F qui ne s'ouvre pas."""
import json, os, re, sys
from base64 import b64encode
from datetime import datetime, timedelta, timezone
import itsdangerous
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rendu_de import APPAREILS, MASQUE, SECRET, URL, blocs, vers_d

PILOTE_ROLE = "111111111111111111"
# (nom, identifiant, rôles Discord, escadrille) -- les profils du banc (semis.py)
PILOTES = [
    ("MistyKestrel42", "100000000000000001", ["700000000000000101", PILOTE_ROLE], "CHARLIE-33"),
    ("Viper", "200000000000000003", ["700000000000000101", PILOTE_ROLE], "CHARLIE-33"),
    ("Ghost", "200000000000000004", ["700000000000000103", PILOTE_ROLE], "BRAVO-22"),
    ("Hunter", "200000000000000005", ["700000000000000102", PILOTE_ROLE], "ALPHA-11"),
]
COLONNES = ["pilote", "vols", "fiables", "air", "sol", "perdus", "éjections", "ratio", "armes", "menaces",
            "appareils", "carnet", "campagnes", "blocs", "F:lien"]
ONGLET_A = '[data-module-nav="debrief"] button[data-nav="pilotes"]'
ABSENT = "Écran A : absent de cette version — F rendu à la place"


def cookie(nom, pid, roles, esc):
    session = {"id": pid, "name": nom, "roles": roles, "lang": "fr", "avatar": None, "squadron": esc,
               "exp": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}
    return itsdangerous.TimestampSigner(SECRET).sign(b64encode(json.dumps(session).encode())).decode()


def ouvrir(browser, pilote, l, h, dpr, scheme, err):
    """Le Débrief ouvert pour ce pilote, par les vrais boutons (app.js vit dans une IIFE : on reclique jusqu'à /api/me)."""
    nom, pid, roles, esc = pilote
    ctx = browser.new_context(viewport={"width": l, "height": h}, device_scale_factor=dpr, color_scheme=scheme)
    ctx.add_cookies([{"name": "session", "value": cookie(nom, pid, roles, esc), "url": URL}])
    page = ctx.new_page()
    page.on("pageerror", lambda e: err.append(f"{nom} : {e}"))
    page.goto(URL + "/")
    page.wait_for_selector("#station-debrief-open", state="attached", timeout=15000)
    for _ in range(40):
        page.evaluate("document.querySelector('#station-debrief-open').click()")
        if page.evaluate("(() => { const s = document.querySelector('#screen-app');"
                         " return s.dataset.module === 'debrief' && !s.classList.contains('hidden'); })()"):
            break
        page.wait_for_timeout(250)
    page.add_style_tag(content=MASQUE)
    return ctx, page


def norme(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def f_ouvert(page, nom):
    """F est ouvert, et c'est celui de ce pilote (son indicatif, dans la barre d'identité)."""
    try:
        page.wait_for_selector("#view-membre:not(.hidden) #membre-mount .idbar", timeout=8000)
    except Exception:
        return False
    page.evaluate("document.fonts.ready")
    return norme(nom) in norme(page.inner_text("#membre-mount .idbar .callsign"))


def tableau(page, nom, n_blocs, f_lien):
    d = page.evaluate("fetch('/api/debrief/dossier').then(r => r.json())")
    ds = d["dossier"]
    return {
        "pilote": nom, "vols": ds["vols"], "fiables": ds["vols_fiables"], "air": ds["victoires"]["air"],
        "sol": ds["victoires"]["sol"], "perdus": ds["pertes"]["appareils"], "éjections": ds["pertes"]["ejections"],
        "ratio": None if ds["ratio"] is None else float(ds["ratio"]), "armes": len(ds["precision"]), "menaces": len(ds["menaces"]),
        "appareils": len(ds["par_appareil"]), "carnet": len(ds["carnet"]), "campagnes": len(d["campagnes"]),
        "blocs": n_blocs, "F:lien": f_lien,
    }


def rendre_a(page, nom, pid, sortie, palier):
    """A présent : ses blocs, sa feuille, et son lien vers F."""
    page.evaluate(f"document.querySelector('{ONGLET_A}').click()")
    page.wait_for_selector("#view-pilotes:not(.hidden) #pilotes-mount > *", timeout=15000)
    page.evaluate("document.fonts.ready")
    fichiers = blocs(page, "#pilotes-mount", f"A_{nom}", sortie, palier)
    page_png = f"A_{nom}_page_{palier}.png"
    page.query_selector("#view-pilotes .sheet").screenshot(path=os.path.join(sortie, page_png), animations="disabled")
    # le lien vers F : présent, du bon pilote, et il ouvre F de ce pilote
    id_lien = page.evaluate("(() => { const a = document.querySelector('#pilotes-mount [data-ouvre-membre]');"
                            " return a ? a.dataset.ouvreMembre : null; })()")
    lien = False
    if id_lien == pid:
        page.evaluate("document.querySelector('#pilotes-mount [data-ouvre-membre]').click()")
        lien = f_ouvert(page, nom)
    return len(fichiers), lien, fichiers + [page_png]


def rendre_f(page, nom, pid, sortie, palier):
    """A absent : F du pilote, ouvert depuis sa case dans l'organigramme de D (sinon de son escadrille, E)."""
    vers_d(page)
    case = f'#escadrilles-mount [data-ouvre-membre="{pid}"]'
    if not page.query_selector(case):
        return None, None, []
    page.evaluate(f"document.querySelector('{case}').click()")
    ouvert = f_ouvert(page, nom)
    fichiers = blocs(page, "#membre-mount", f"F_{nom}", sortie, palier) if ouvert else []
    page_png = f"F_{nom}_page_{palier}.png"
    if ouvert:
        page.query_selector("#view-membre .sheet").screenshot(path=os.path.join(sortie, page_png), animations="disabled")
    return len(fichiers), ouvert, fichiers + ([page_png] if ouvert else [])


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit("usage : python3.12 -B rendu_a.py <sortie> [large,intermediaire,compact] [clair|sombre]")
    sortie, reste = args[0], args[1:]
    theme = next((a for a in reste if a in ("clair", "sombre")), "clair")
    paliers = next((a for a in reste if a not in ("clair", "sombre")), "large,intermediaire,compact").split(",")
    sfx = "_sombre" if theme == "sombre" else ""
    os.makedirs(sortie, exist_ok=True)
    mesures, mode_a = {}, None
    with sync_playwright() as p:
        for palier, l, h, dpr in [a for a in APPAREILS if a[0] in paliers]:
            err, lignes, fichiers, ouverts_f = [], [], [], {}
            browser = p.chromium.launch()
            for pilote in PILOTES:
                nom, pid, _roles, _esc = pilote
                ctx, page = ouvrir(browser, pilote, l, h, dpr, "dark" if theme == "sombre" else "light", err)
                if mode_a is None:   # le contrat se lit une fois : l'onglet porte-t-il data-nav="pilotes" ?
                    mode_a = bool(page.query_selector(ONGLET_A))
                    print("Écran A : présent" if mode_a else ABSENT)
                if mode_a:
                    n, lien, fs = rendre_a(page, nom, pid, sortie, palier + sfx)
                    f_lien = lien
                else:
                    n, f_ok, fs = rendre_f(page, nom, pid, sortie, palier + sfx)
                    f_lien, ouverts_f[nom] = None, f_ok
                lignes.append(tableau(page, nom, n, f_lien))
                fichiers += fs
                ctx.close()
            browser.close()
            mesures[palier] = {"theme": theme, "ecran_A": mode_a, "tableau": lignes, "erreurs_js": err,
                               "F_depuis_D": ouverts_f or None, "fichiers": fichiers}
    json.dump(mesures, open(os.path.join(sortie, "mesures.json"), "w"), indent=1, ensure_ascii=False)

    echec = False
    for palier, m in mesures.items():
        print(f"== {palier} · {theme} · erreurs JS {m['erreurs_js'] or 'aucune'}")
        print("   " + " ".join(f"{c:>9s}" if c != "pilote" else f"{c:14s}" for c in COLONNES))
        for r in m["tableau"]:
            cases = []
            for c in COLONNES:
                v = r[c]
                if c == "ratio":   # une décimale, comme le dossier : 4.0, 0.5 ou null
                    v = "null" if v is None else f"{v:.1f}"
                elif v is None:
                    v = "—"
                elif isinstance(v, bool):
                    v = str(v).lower()
                cases.append(f"{v!s:14s}" if c == "pilote" else f"{v!s:>9s}")
            print("   " + " ".join(cases))
        if m["F_depuis_D"] is not None:
            print("   F ouvert depuis D : " + " · ".join(f"{n} {'oui' if ok else 'NON'}" for n, ok in m["F_depuis_D"].items()))
        echec = echec or bool(m["erreurs_js"]) or (m["F_depuis_D"] is not None and not all(m["F_depuis_D"].values()))
        if mode_a:
            echec = echec or not all(r["F:lien"] for r in m["tableau"])
    sys.exit(1 if echec else 0)


if __name__ == "__main__":
    main()
