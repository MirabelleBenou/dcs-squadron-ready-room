"""Maquette du lot « L'effectif complet » : le vrai écran Membres du Centre,
servi par le vrai backend répété (uvicorn sur la copie de répétition, PG16,
faux Discord), rendu par le vrai app.js répété. Usage :
  python3 maquette.py <dossier_sortie> <fichier_mode>"""
import json, sys, time
from base64 import b64encode
from datetime import datetime, timedelta, timezone

import itsdangerous
from playwright.sync_api import sync_playwright

SORTIE, MODE = sys.argv[1], sys.argv[2]
URL = "http://127.0.0.1:8000"
SECRET = [l.split("=", 1)[1].strip() for l in open("/home/claude/rr/test.env", encoding="utf-8")
          if l.startswith("SESSION_SECRET=")][0]
session = {"id": "100000000000000001", "name": "MistyKestrel42", "roles": ["700000000000000101", "111111111111111111"],
           "lang": "fr", "avatar": None, "squadron": "CHARLIE-33",
           "exp": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()}
cookie = itsdangerous.TimestampSigner(SECRET).sign(b64encode(json.dumps(session).encode())).decode()

# Largeurs mesurées sur les captures du porteur : tablette paysage (large),
# tablette portrait (intermédiaire), téléphone (compact).
APPAREILS = [("large", 1150, 760, 2.5), ("intermediaire", 720, 1000, 2.5), ("compact", 393, 850, 2.75)]


def ouvrir(p, nom, l, h, dpr):
    ctx = p.chromium.launch().new_context(viewport={"width": l, "height": h}, device_scale_factor=dpr)
    ctx.add_cookies([{"name": "session", "value": cookie, "url": URL}])
    page = ctx.new_page()
    erreurs = []
    page.on("pageerror", lambda e: erreurs.append(str(e)))
    page.goto(URL + "/")
    page.wait_for_selector("#station-command-open", state="attached", timeout=15000)
    # app.js vit dans une IIFE : on passe par les vrais boutons. La tuile du
    # Centre ne répond qu'une fois /api/me chargé -- on reclique jusque-là.
    for _ in range(40):
        page.evaluate("document.querySelector('#station-command-open').click()")
        if page.evaluate("(() => { const s = document.querySelector('#screen-app');"
                         " return s.dataset.module === 'command' && !s.classList.contains('hidden'); })()"):
            break
        page.wait_for_timeout(250)
    page.evaluate("document.querySelector('[data-module-nav=\"command\"] button[data-cc-nav=\"membres\"]').click()")
    page.wait_for_selector("#cc-mbr-appel .cc-appel", timeout=15000)
    return page, erreurs


def capture(page, chemin):
    zone = page.query_selector("#view-cc-membres")
    page.evaluate("document.querySelector('#view-cc-membres').scrollIntoView()")
    page.wait_for_timeout(400)
    zone.screenshot(path=chemin)


with sync_playwright() as p:
    t0 = time.monotonic()
    # 1 · le cas réel : un appel au bouton, BANSHEE arrive au CHARLIE-33
    page, err = ouvrir(p, *APPAREILS[0])
    page.click("#cc-appel-btn")
    page.wait_for_function("!document.querySelector('#cc-appel-btn').disabled", timeout=30000)
    page.wait_for_timeout(300)
    print("bilan (large) :", page.inner_text("#cc-mbr-appel .cc-appel-bilan"), "| erreurs JS :", err)
    capture(page, f"{SORTIE}/arrivee_large_1150.png")
    for nom, l, h, dpr in APPAREILS[1:]:
        page, err = ouvrir(p, nom, l, h, dpr)
        print(f"bilan ({nom}) :", page.inner_text("#cc-mbr-appel .cc-appel-bilan"), "| erreurs JS :", err)
        capture(page, f"{SORTIE}/arrivee_{nom}_{l}.png")
    print(f"cas réel capturé en {time.monotonic() - t0:.0f} s")
    # 2 · la liste refusée (403) : attendre la fin de l'appel de démarrage (60 s)
    while time.monotonic() - t0 < 75:
        time.sleep(1)
    open(MODE, "w").write("403")
    page, err = ouvrir(p, *APPAREILS[2])
    page.click("#cc-appel-btn")
    page.wait_for_function("!document.querySelector('#cc-appel-btn').disabled", timeout=30000)
    page.wait_for_timeout(300)
    print("bilan (403, compact) :", page.inner_text("#cc-mbr-appel .cc-appel-bilan"), "| erreurs JS :", err)
    capture(page, f"{SORTIE}/refus403_compact_393.png")
