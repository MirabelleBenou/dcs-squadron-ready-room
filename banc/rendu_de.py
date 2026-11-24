"""Rendu des écrans D et E du Débrief -- instrument du banc, pour le dev comme pour le CdP.
Lecture seule. Vrai backend (servir.sh) sur PostgreSQL 16, vrai app.js, aux largeurs et dans
l'orientation des appareils du porteur : tablette paysage 1 150 px, tablette portrait 720 px,
téléphone 393 px. Capture BLOC PAR BLOC -- chaque enfant direct du montage de D et de E --, la
barre de l'application et pied de version masqués (visibility:hidden, la mise en page ne bouge pas) ; une page entière
de E en plus, pour le regard, jamais comparée. Mesure la géométrie de l'organigramme de chaque E
et vérifie que ses cases ouvrent F, au clic et à la touche Entrée.
Usage : python3.12 -B rendu_de.py <sortie> [large,intermediaire,compact]
Écrit <sortie>/*.png et <sortie>/mesures.json ; imprime un tableau."""
import json, os, re, sys, unicodedata
from base64 import b64encode
from datetime import datetime, timedelta, timezone
import itsdangerous
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8000"
SECRET = [l.split("=", 1)[1].strip() for l in open("/home/claude/rr/test.env", encoding="utf-8")
          if l.startswith("SESSION_SECRET=")][0]
SESSION = {"id": "100000000000000001", "name": "MistyKestrel42", "roles": ["700000000000000101", "111111111111111111"],
           "lang": "fr", "avatar": None, "squadron": "CHARLIE-33",
           "exp": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}
COOKIE = itsdangerous.TimestampSigner(SECRET).sign(b64encode(json.dumps(SESSION).encode())).decode()
# (nom, largeur, hauteur, densité) -- paysage pour la tablette en large, portrait sinon : des règles
# CSS dépendent de l'orientation. Hautes fenêtres : rien ne se superpose aux blocs.
APPAREILS = [("large", 1150, 1100, 2.5), ("intermediaire", 720, 2400, 2.5), ("compact", 393, 2400, 2.75)]
# Banc v6 : le pied de version est masqué lui aussi -- une version qui change ne doit plus faire bouger un pixel.
MASQUE = ".topbar, .topbar-nav, #app-version-footer { visibility: hidden !important; }"

def slug(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "bloc"

def ouvrir(p, l, h, dpr, err):
    ctx = p.chromium.launch().new_context(viewport={"width": l, "height": h}, device_scale_factor=dpr)
    ctx.add_cookies([{"name": "session", "value": COOKIE, "url": URL}])
    page = ctx.new_page()
    page.on("pageerror", lambda e: err.append(str(e)))
    page.goto(URL + "/")
    page.wait_for_selector("#station-debrief-open", state="attached", timeout=15000)
    for _ in range(40):   # app.js vit dans une IIFE : les vrais boutons, recliqués jusqu'à /api/me chargé
        page.evaluate("document.querySelector('#station-debrief-open').click()")
        if page.evaluate("(() => { const s = document.querySelector('#screen-app');"
                         " return s.dataset.module === 'debrief' && !s.classList.contains('hidden'); })()"):
            break
        page.wait_for_timeout(250)
    page.add_style_tag(content=MASQUE)
    return page

def vers_d(page):
    page.evaluate("document.querySelector('[data-module-nav=\"debrief\"] button[data-nav=\"escadrilles\"]').click()")
    page.wait_for_selector("#escadrilles-mount .og", timeout=15000)
    page.evaluate("document.fonts.ready")

def blocs(page, mount, prefixe, sortie, palier):
    n = page.evaluate(f"document.querySelectorAll('{mount} > *').length")
    noms = []
    for i in range(n):
        el = page.query_selector(f"{mount} > :nth-child({i + 1})")
        sec = el.query_selector(".sec")
        nom = f"{prefixe}_{i}-{slug(sec.inner_text() if sec else el.get_attribute('class'))}_{palier}.png"
        el.screenshot(path=os.path.join(sortie, nom), animations="disabled")
        noms.append(nom)
    return noms

GEO = """(designation) => {
  const fr = [...document.querySelectorAll('#escadrille-mount > .framed')]
    .find(f => f.querySelector('.sec') && f.querySelector('.sec').textContent.trim() === 'Organigramme');
  if (!fr) return null;
  const R = el => { const r = el.getBoundingClientRect(); return {x: r.left, y: r.top, w: r.width, h: r.height}; };
  const cases = [...fr.querySelectorAll('[data-ouvre-membre]')].map(el => ({
    id: el.dataset.ouvreMembre, nom: (el.querySelector('.og-cs') || el).textContent.trim(),
    role: el.querySelector('.og-role') ? el.querySelector('.og-role').textContent.trim() : '', ...R(el)}));
  return {cadre: R(fr), cases};
}"""

def geometrie(g, ordre_serveur):
    cases = g["cases"]
    chef = next((c for c in cases if c["role"] == "Chef"), None)
    sous = [c for c in cases if c is not chef]
    cols = []
    for c in sorted(sous, key=lambda c: (c["x"], c["y"])):
        if cols and abs(cols[-1][0]["x"] - c["x"]) <= 2:
            cols[-1].append(c)
        else:
            cols.append([c])
    lecture = [c["id"] for col in cols for c in sorted(col, key=lambda c: c["y"])]
    attendu = [str(m["id"]) for m in ordre_serveur if m.get("role") != "leader"]
    largeurs = sorted({round(c["w"], 1) for c in sous})
    return {
        "cases": len(cases), "chef": chef["nom"] if chef else None,
        "colonnes": [len(c) for c in cols],
        "ordre_ok": lecture == attendu,
        "chef_l": round(chef["w"], 1) if chef else None, "sous_l": largeurs,
        "retrait": round(min(c["x"] for c in sous) - chef["x"], 1) if chef and sous else None,
        "chef_au_dessus": (chef["y"] + chef["h"] <= min(c["y"] for c in sous) + 0.5) if chef and sous else None,
        "cadre_h": round(g["cadre"]["h"], 1),
    }

def ouvre_f(page, par_entree=False):
    sel = "#escadrille-mount [data-ouvre-membre]"
    if par_entree:
        page.focus(sel); page.keyboard.press("Enter")
    else:
        page.evaluate(f"document.querySelector('{sel}').click()")
    try:
        page.wait_for_selector("#view-membre:not(.hidden) #membre-mount .idbar", timeout=8000)
        return True
    except Exception:
        return False

def main():
    sortie = sys.argv[1]; os.makedirs(sortie, exist_ok=True)
    paliers = (sys.argv[2] if len(sys.argv) > 2 else "large,intermediaire,compact").split(",")
    mesures = {}
    with sync_playwright() as p:
        for palier, l, h, dpr in [a for a in APPAREILS if a[0] in paliers]:
            err = []
            page = ouvrir(p, l, h, dpr, err)
            vers_d(page)
            charge = page.evaluate("fetch('/api/debrief/escadre').then(r => r.json())")
            ordres = {s["designation"]: s.get("members") or [] for s in charge.get("squadrons", [])}
            m = mesures[palier] = {"D": blocs(page, "#escadrilles-mount", "D", sortie, palier), "E": {}}
            m["D_retrait"] = page.evaluate("""(() => { const col = [...document.querySelectorAll('#escadrilles-mount .og-col')]
                .find(c => c.querySelector('.og-mem [data-ouvre-membre]'));
                return col ? Math.round((col.querySelector('.og-mem [data-ouvre-membre]').getBoundingClientRect().left
                                         - col.getBoundingClientRect().left) * 10) / 10 : null; })()""")
            escs = page.evaluate("[...document.querySelectorAll('#escadrilles-mount a.es-ob')]"
                                 ".map(a => a.querySelector('.es-tag').textContent.trim())")
            for k, esc in enumerate(escs):
                page.evaluate("""(esc) => [...document.querySelectorAll('#escadrilles-mount a.es-ob')]
                    .find(a => a.querySelector('.es-tag').textContent.trim() === esc).click()""", esc)
                page.wait_for_function("""(esc) => { const v = document.querySelector('#view-escadrille');
                    const t = document.querySelector('#escadrille-mount .esq-ttl .callsign');
                    return v && !v.classList.contains('hidden') && t && t.textContent.trim() === esc; }""", arg=esc, timeout=15000)
                page.evaluate("document.fonts.ready")
                e = m["E"][esc] = {"blocs": blocs(page, "#escadrille-mount", f"E_{esc}", sortie, palier)}
                page.query_selector("#view-escadrille .sheet").screenshot(
                    path=os.path.join(sortie, f"E_{esc}_page_{palier}.png"), animations="disabled")
                g = page.evaluate(GEO, esc)
                e["geo"] = geometrie(g, ordres.get(esc, [])) if g else None
                e["F_clic"] = ouvre_f(page) if g and g["cases"] else None
                if k == 0 and g and g["cases"]:
                    vers_d(page)
                    page.evaluate("""(esc) => [...document.querySelectorAll('#escadrilles-mount a.es-ob')]
                        .find(a => a.querySelector('.es-tag').textContent.trim() === esc).click()""", esc)
                    page.wait_for_selector("#escadrille-mount [data-ouvre-membre]", timeout=15000)
                    e["F_entree"] = ouvre_f(page, par_entree=True)
                vers_d(page)
            m["erreurs_js"] = err
    json.dump(mesures, open(os.path.join(sortie, "mesures.json"), "w"), indent=1, ensure_ascii=False)
    for palier, m in mesures.items():
        print(f"== {palier} · retrait des membres de D {m['D_retrait']} px · erreurs JS {m['erreurs_js'] or 'aucune'}")
        print(f"   {'escadrille':9s} cases chef           colonnes     ordre larg.chef larg.sous     retrait dessus F:clic F:entrée cadre_h")
        for esc, e in m["E"].items():
            g = e["geo"] or {}
            print(f"   {esc:9s} {g.get('cases', 0):5d} {str(g.get('chef')):14s} {str(g.get('colonnes')):12s} {str(g.get('ordre_ok')):5s}"
                  f" {str(g.get('chef_l')):9s} {str(g.get('sous_l')):13s} {str(g.get('retrait')):7s} {str(g.get('chef_au_dessus')):6s}"
                  f" {str(e.get('F_clic')):6s} {str(e.get('F_entree', '')):8s} {g.get('cadre_h')}")

if __name__ == "__main__":
    main()
