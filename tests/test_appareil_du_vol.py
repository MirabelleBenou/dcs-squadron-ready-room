"""Brief SONNET Lot « L'appareil du vol » : trois invariants statiques, hors
ligne -- pas de base, pas de navigateur.

1. `test_urls_css_resolues` -- chaque url(/static/...) de styles.css désigne un
   fichier présent : aucune règle ne pointe vers un asset retiré (les deux
   rr_wire_*.webp sortent du paquet avec ce lot).
2. `test_sept_silhouettes_se_repondent` -- les clés de AIRCRAFT_SILHOUETTE dans
   app.js, les classes .wire.ac-* de styles.css, les silhouettes pleines
   rr_ac_<appareil>.png et les filaires rr_ac_<appareil>_filaire.png désignent
   les sept mêmes appareils. Les filaires ne sont appelés par aucune règle :
   ils sont livrés pour plus tard, à la demande du porteur.
3. `test_silhouettes_sont_des_masques` -- chaque pleine est un PNG RGBA de
   700 px de large dont l'alpha porte une silhouette, ni vide ni pleine ;
   chaque filaire, un PNG RGBA de 1 400 px de large dont l'alpha porte un
   trait fin.
"""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
SEPT = {"mi24", "mi8", "f4e", "f1", "uh1", "f16", "f5"}


def test_urls_css_resolues() -> None:
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    urls = {u.split("?")[0] for u in re.findall(r"url\((/static/[^)]+)\)", css)}
    manquants = sorted(u for u in urls if not (STATIC / u.removeprefix("/static/")).is_file())
    assert urls and not manquants, manquants


def test_sept_silhouettes_se_repondent() -> None:
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    table = js[js.index("const AIRCRAFT_SILHOUETTE = ["):]
    table = table[: table.index("];")]
    cles = set(re.findall(r'\[/\^[^/]+/, "(\w+)"\]', table))
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    classes = set(re.findall(r"\.wire\.ac-(\w+)\{", css))
    noms = {p.stem.removeprefix("rr_ac_") for p in (STATIC / "assets" / "img").glob("rr_ac_*.png")}
    pleines = {n for n in noms if not n.endswith("_filaire")}
    filaires = {n.removesuffix("_filaire") for n in noms if n.endswith("_filaire")}
    assert cles == classes == pleines == filaires == SEPT


def test_silhouettes_sont_des_masques() -> None:
    for nom, largeur, bornes in (("{}", 700, (0.2, 0.6)), ("{}_filaire", 1400, (0.01, 0.15))):
        for ac in sorted(SEPT):
            im = Image.open(STATIC / "assets" / "img" / f"rr_ac_{nom.format(ac)}.png")
            assert im.mode == "RGBA" and im.width == largeur, (ac, nom, im.mode, im.size)
            histogramme = im.getchannel("A").histogram()
            couverture = sum(histogramme[128:]) / (im.width * im.height)
            assert bornes[0] < couverture < bornes[1], (ac, nom, couverture)
