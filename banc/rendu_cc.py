"""Rendu du Centre de Commandement -- écrans Droits et Membres -- et du scénario des relances (banc v4).
Instrument du banc, pour le dev comme pour le CdP. À jouer sous servir_cc.sh, sur une base de
prepare_cc.sh : vrai backend, vrai app.js, faux Discord, horloge du scénario (02/10/2026, 12:00 à
Paris) côté serveur ET navigateur -- le rendu ne dépend pas du jour où l'on rend.

1 · ÉTAT 0, toute version : avant tout appel, aux trois largeurs du porteur, chaque bloc visible de
    l'écran Droits (R-<id>_<palier>.png) et de l'écran Membres (M-<id>_<palier>.png), nommés par leur
    identifiant -- un bloc qui descend garde son nom --, et les deux pages entières (pour le regard,
    jamais comparées).
2 · LE SCÉNARIO, seulement si GET /api/command/rights porte la clé « relances » (contrat du cadrage) :
      étape 0  aucun rôle destinataire ; un appel au bouton
      étape 1  le rôle Officier choisi (PUT /api/command/rights/relances) ; un appel
      étape 2  un appel, sans changement
      étape 3  Rover perd sa seule réponse ; un appel
      étape 4  Kerberos répond pour le 29/09 ; un appel
    Après chaque étape : la liste lue sur GET /api/command/relances, les MP reçus par le faux Discord ;
    le bloc #cc-mbr-relances capturé (S<étape>-relances_large.png ; aux trois largeurs après les
    étapes 1 et 4), le bloc #blk-relances de l'écran Droits aux trois largeurs après l'étape 1, et chaque
    MP rendu en image, au téléphone (MP_<n>-e<étape>-<destinataire>-<statut>.png).
Usage : python3.12 -B rendu_cc.py <sortie>. Écrit les PNG et mesures.json, imprime un tableau."""
import html, json, os, re, subprocess, sys, unicodedata
from base64 import b64encode
from datetime import datetime, timedelta, timezone

import itsdangerous
from playwright.sync_api import sync_playwright

SORTIE = sys.argv[1]
H = "/home/claude/rr/harness"
URL = "http://127.0.0.1:8000"
MPJ = "/tmp/faux_discord.log.mp.jsonl"
HEURE = datetime(2026, 10, 2, 10, 0, tzinfo=timezone.utc)          # l'horloge du scénario
OFFICIER = "444444444444444444"
SECRET = [l.split("=", 1)[1].strip() for l in open("/home/claude/rr/test.env", encoding="utf-8")
          if l.startswith("SESSION_SECRET=")][0]


class Signataire(itsdangerous.TimestampSigner):
    def get_timestamp(self):   # signé « avant » l'horloge figée du serveur : un âge négatif est refusé
        return int((HEURE - timedelta(hours=1)).timestamp())


SESSION = {"id": "100000000000000001", "name": "MistyKestrel42", "roles": ["700000000000000101", "111111111111111111"],
           "lang": "fr", "avatar": None, "squadron": "CHARLIE-33", "exp": (HEURE + timedelta(days=30)).isoformat()}
COOKIE = Signataire(SECRET).sign(b64encode(json.dumps(SESSION).encode())).decode()
APPAREILS = [("large", 1150, 1100, 2.5), ("intermediaire", 720, 2400, 2.5), ("compact", 393, 2400, 2.75)]
# Banc v6 : le pied de version est masqué lui aussi -- une version qui change ne doit plus faire bouger un pixel.
MASQUE = ".topbar, .topbar-nav, #app-version-footer { visibility: hidden !important; }"
NOMS = {m["user"]["id"]: m["user"].get("global_name") or m["user"]["username"]
        for m in json.load(open(f"{H}/membres.json", encoding="utf-8"))}
ERREURS = []


def slug(t):
    t = unicodedata.normalize("NFD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:40] or "bloc"


def ouvrir(p, l, h, dpr):
    ctx = p.chromium.launch().new_context(viewport={"width": l, "height": h}, device_scale_factor=dpr)
    ctx.clock.set_fixed_time(HEURE)
    ctx.add_cookies([{"name": "session", "value": COOKIE, "url": URL}])
    page = ctx.new_page()
    page.on("pageerror", lambda e: ERREURS.append(str(e)))
    page.goto(URL + "/")
    page.wait_for_selector("#station-command-open", state="attached", timeout=15000)
    for _ in range(40):   # app.js vit dans une IIFE : les vrais boutons, recliqués jusqu'à /api/me chargé
        page.evaluate("document.querySelector('#station-command-open').click()")
        if page.evaluate("(() => { const s = document.querySelector('#screen-app');"
                         " return s.dataset.module === 'command' && !s.classList.contains('hidden'); })()"):
            break
        page.wait_for_timeout(250)
    page.add_style_tag(content=MASQUE)
    return page


def vers(page, ecran):
    page.evaluate(f"document.querySelector('[data-module-nav=\"command\"] button[data-cc-nav=\"{ecran}\"]').click()")
    if ecran == "droits":
        page.wait_for_selector("#cc-droits-content:not(.hidden)", timeout=15000)
    else:
        page.wait_for_selector("#cc-mbr-tbody tr", timeout=15000)
    page.wait_for_timeout(500)
    page.evaluate("document.fonts.ready")


VISIBLES = """(sel) => [...document.querySelectorAll(sel)].map((el, i) => ({i, id: el.id,
  cls: (el.getAttribute('class') || '').split(' ')[0], vu: el.getClientRects().length > 0 &&
  el.getBoundingClientRect().height > 0 && getComputedStyle(el).visibility !== 'hidden'}))"""


def blocs(page, sel, prefixe, palier):
    noms = []
    for b in page.evaluate(VISIBLES, sel):
        if not b["vu"]:
            continue
        el = page.query_selector_all(sel)[b["i"]]
        nom = f"{prefixe}-{b['id'] or slug(b['cls'])}_{palier}.png"
        el.scroll_into_view_if_needed()
        el.screenshot(path=os.path.join(SORTIE, nom), animations="disabled")
        noms.append(nom)
    return noms


def api(page, methode, chemin, corps=None):
    r = page.evaluate("""async ([m, u, b]) => { const r = await fetch(u, {method: m,
        headers: {'Content-Type': 'application/json'}, body: b});
        return [r.status, await r.text()]; }""", [methode, chemin, json.dumps(corps) if corps is not None else None])
    try:
        return r[0], json.loads(r[1])
    except ValueError:
        return r[0], r[1]


def sql(requete):
    subprocess.run(["psql", "-h", "127.0.0.1", "-U", "readyroom", "-d", "readyroom", "-qAtc", requete],
                   env={**os.environ, "PGPASSWORD": "readyroom"}, check=True, capture_output=True)


def mp_lus():
    try:
        return [json.loads(l) for l in open(MPJ, encoding="utf-8") if l.strip()]
    except FileNotFoundError:
        return []


def appel_au_bouton(page):
    page.click("#cc-appel-btn")
    page.wait_for_function("document.querySelector('#cc-appel-btn') && !document.querySelector('#cc-appel-btn').disabled",
                           timeout=60000)
    page.wait_for_timeout(1200)


def liste(page):
    st, j = api(page, "GET", "/api/command/relances")
    if st != 200 or not isinstance(j, dict):
        return f"GET /api/command/relances : HTTP {st}", None
    morceaux = []
    for g in j.get("retards", []):
        morceaux.append(f"{g.get('escadrille')} " + ", ".join(
            f"{p.get('nom')} ({p.get('derniere_reponse') or 'aucune'})" for p in g.get("pilotes", [])))
    n = sum(len(g.get("pilotes", [])) for g in j.get("retards", []))
    return f"{n} · " + (" · ".join(morceaux) if morceaux else "personne"), j


def capture_bloc(page, sel, nom):
    el = page.query_selector(sel)
    if not el:
        return f"{sel} absent"
    el.scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    el.screenshot(path=os.path.join(SORTIE, nom), animations="disabled")
    return nom


def rendre_mp(p, lignes, etape_de):
    page = p.chromium.launch().new_page(viewport={"width": 393, "height": 900}, device_scale_factor=2.75)
    noms = []
    for m in lignes:
        corps = m.get("corps") or {}
        texte = corps.get("content") or ""
        for e in corps.get("embeds") or []:
            texte += "\n\n" + "\n".join(x for x in (e.get("title"), e.get("description")) if x)
        t = html.escape(texte)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t).replace("\n", "<br>")
        qui = NOMS.get(m["destinataire"], m["destinataire"])
        refus = ('<div class="refus">Refusé par Discord (code 50007) : ce MP n\'est pas arrivé.</div>'
                 if m["statut"] == "refuse" else "")
        page.set_content(f"""<html><head><style>
body{{margin:0;background:#313338;font-family:'DejaVu Sans',sans-serif;color:#dbdee1}}
.mp{{width:393px;padding:14px 16px;box-sizing:border-box}}
.qui{{font-weight:bold;color:#f2f3f5;font-size:15px;margin-bottom:6px}}
.qui span{{font-weight:normal;color:#949ba4;font-size:11.5px;margin-left:6px}}
.txt{{font-size:14.5px;line-height:1.4;word-wrap:break-word}}
.refus{{margin-top:10px;padding:6px 8px;border-left:4px solid #da373c;background:#3a2a2c;color:#f0b6b8;font-size:12.5px}}
</style></head><body><div class="mp"><div class="qui">Ready Room<span>MP à {html.escape(qui)}
· 02/10/2026 12:00</span></div><div class="txt">{t}</div>{refus}</div></body></html>""")
        nom = f"MP_{m['n']}-e{etape_de[m['n']]}-{slug(qui)}-{m['statut']}.png"
        page.query_selector(".mp").screenshot(path=os.path.join(SORTIE, nom))
        noms.append(nom)
    return noms


os.makedirs(SORTIE, exist_ok=True)
mesures = {"etat0": {}, "etapes": [], "mp": []}
with sync_playwright() as p:
    print("=== État 0 · avant tout appel")
    for palier, l, h, dpr in APPAREILS:
        page = ouvrir(p, l, h, dpr)
        vers(page, "droits")
        r = blocs(page, "#view-cc-droits > .section-head, #cc-droits-content > *", "R", palier)
        page.query_selector("#view-cc-droits").screenshot(path=os.path.join(SORTIE, f"R_page_{palier}.png"))
        vers(page, "membres")
        m = blocs(page, "#view-cc-membres > *", "M", palier)
        page.query_selector("#view-cc-membres").screenshot(path=os.path.join(SORTIE, f"M_page_{palier}.png"))
        mesures["etat0"][palier] = {"droits": r, "membres": m}
        print(f"  {palier:13s} Droits : " + " ".join(re.sub(r"^R-|_\w+\.png$", "", x) for x in r))
        print(f"  {' ':13s} Membres : " + " ".join(re.sub(r"^M-|_\w+\.png$", "", x) for x in m))
        page.context.browser.close()

    page = ouvrir(p, *APPAREILS[0][1:])
    st, droits = api(page, "GET", "/api/command/rights")
    if not (st == 200 and isinstance(droits, dict) and "relances" in droits):
        print("=== Relances : absentes de cette version (GET /api/command/rights sans clé « relances »)")
    else:
        print("=== Scénario des relances")
        print("  étape · MP reçus par le faux Discord · retards (GET /api/command/relances)")
        etape_de, vu = {}, 0
        etapes = [
            ("aucun rôle destinataire", None),
            ("rôle Officier choisi", lambda: api(page, "PUT", "/api/command/rights/relances", {"role_ids": [OFFICIER]})),
            ("sans changement", None),
            ("Rover perd sa réponse", lambda: sql("DELETE FROM presences WHERE profile_id = 200000000000000010")),
            ("Kerberos répond", lambda: sql(
                "INSERT INTO presences (id, event_id, occ_date, profile_id, state, created_at, updated_at) "
                "SELECT gen_random_uuid(), id, DATE '2026-09-29', 200000000000000002, 'present', "
                "TIMESTAMPTZ '2026-10-02 11:30+02', TIMESTAMPTZ '2026-10-02 11:30+02' "
                "FROM events WHERE title = 'Entraînement'")),
        ]
        vers(page, "membres")
        for k, (titre, geste) in enumerate(etapes):
            retour = geste() if geste else None
            if retour is not None and isinstance(retour, tuple) and retour[0] != 200:
                print(f"  étape {k} : le geste répond HTTP {retour[0]} : {retour[1]}")
            if k == 1:   # le réglage a changé : une page neuve le lit
                page.context.browser.close()
                page = ouvrir(p, *APPAREILS[0][1:]); vers(page, "membres")
            appel_au_bouton(page)
            nouveaux = mp_lus()[vu:]
            vu += len(nouveaux)
            for m in nouveaux:
                etape_de[m["n"]] = k
            env = sum(1 for m in nouveaux if m["statut"] == "envoye")
            ref = sum(1 for m in nouveaux if m["statut"] == "refuse")
            dest = ", ".join(f"{NOMS.get(m['destinataire'], m['destinataire'])}"
                             f"{' (refus)' if m['statut'] == 'refuse' else ''}" for m in nouveaux) or "—"
            txt, j = liste(page)
            print(f"  {k} {titre:24s}· {env} envoyé(s), {ref} refusé(s) : {dest}")
            print(f"  {' ':27s}· retards {txt}")
            cap = capture_bloc(page, "#cc-mbr-relances", f"S{k}-relances_large.png")
            mesures["etapes"].append({"etape": k, "titre": titre, "envoyes": env, "refuses": ref,
                                      "destinataires": dest, "retards": txt, "charge": j, "capture": cap})
            if k in (1, 4):
                for palier, l, h, dpr in APPAREILS[1:]:
                    pg = ouvrir(p, l, h, dpr); vers(pg, "membres")
                    capture_bloc(pg, "#cc-mbr-relances", f"S{k}-relances_{palier}.png")
                    pg.context.browser.close()
            if k == 1:
                for palier, l, h, dpr in APPAREILS:
                    pg = ouvrir(p, l, h, dpr); vers(pg, "droits")
                    capture_bloc(pg, "#blk-relances", f"S1-blk-relances_{palier}.png")
                    pg.context.browser.close()
        mesures["mp"] = mp_lus()
        images = rendre_mp(p, mesures["mp"], etape_de)
        print(f"  MP rendus : {len(images)}")
    print(f"=== Erreurs JS : {len(ERREURS)}" + (" · " + " | ".join(sorted(set(ERREURS)))[:400] if ERREURS else ""))
json.dump(mesures, open(os.path.join(SORTIE, "mesures.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
