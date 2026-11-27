"""Brief SONNET Lot « L'appareil du vol » : quatre invariants statiques, hors
ligne -- pas de base, pas de navigateur.

1. `test_urls_css_resolues` -- chaque url(/static/...) de styles.css désigne un
   fichier présent : aucune règle ne pointe vers un asset retiré (les deux
   rr_wire_*.webp sortent du paquet avec ce lot).
2. `test_silhouettes_se_repondent` -- les clés de AIRCRAFT_SILHOUETTE dans
   app.js, les classes .wire.ac-* et .filaire.ac-* de styles.css, les silhouettes
   pleines rr_ac_<appareil>.png, les filaires rr_ac_<appareil>_filaire.png et les
   valeurs de SILHOUETTE_DU_CENTRE désignent le même ensemble, non vide.
3. `test_silhouettes_sont_des_masques` -- chaque pleine est un PNG RGBA de
   700 px de large dont l'alpha porte une silhouette, ni vide ni pleine ;
   chaque filaire, un PNG RGBA de 1 400 px de large dont l'alpha porte un
   trait fin.
4. `test_types_du_centre_ont_un_profil` -- chaque code de dcs_types_livrees.json
   ayant des types DCS a son profil dans SILHOUETTE_DU_CENTRE, et chacun de ses types DCS trouve la
   même clé par les préfixes de AIRCRAFT_SILHOUETTE ; un code sans type DCS
   n'a pas d'entrée ; aucune clé de SILHOUETTE_DU_CENTRE hors de la table.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
IMG = STATIC / "assets" / "img"


def _table_js(js: str, nom: str, ouvre: str, ferme: str) -> str:
    debut = js.index(f"const {nom} = {ouvre}")
    corps = js[debut:]
    return corps[: corps.index(ferme)]


def _profils() -> set[str]:
    """L'ensemble des profils, lu dans le paquet : les pleines et les filaires."""
    noms = {p.stem.removeprefix("rr_ac_") for p in IMG.glob("rr_ac_*.png")}
    pleines = {n for n in noms if not n.endswith("_filaire")}
    filaires = {n.removesuffix("_filaire") for n in noms if n.endswith("_filaire")}
    assert pleines == filaires, sorted(pleines ^ filaires)
    return pleines


def _prefixes(js: str) -> list[tuple[str, str]]:
    table = _table_js(js, "AIRCRAFT_SILHOUETTE", "[", "];")
    return re.findall(r'\[/\^([^/]+)/, "(\w+)"\]', table)


def _du_centre(js: str) -> dict[str, str]:
    table = _table_js(js, "SILHOUETTE_DU_CENTRE", "{", "};")
    return dict(re.findall(r'"([^"]+)": "(\w+)"', table))


def test_urls_css_resolues() -> None:
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    urls = {u.split("?")[0] for u in re.findall(r"url\((/static/[^)]+)\)", css)}
    manquants = sorted(u for u in urls if not (STATIC / u.removeprefix("/static/")).is_file())
    assert urls and not manquants, manquants


def test_silhouettes_se_repondent() -> None:
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    cles = {cle for _, cle in _prefixes(js)}
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    classes = set(re.findall(r"\.wire\.ac-(\w+)\{", css))
    classes_filaires = set(re.findall(r"\.filaire\.ac-(\w+)\{", css))
    du_centre = set(_du_centre(js).values())
    profils = _profils()
    assert profils and cles == classes == classes_filaires == profils == du_centre


def test_silhouettes_sont_des_masques() -> None:
    for nom, largeur, bornes in (("{}", 700, (0.2, 0.6)), ("{}_filaire", 1400, (0.01, 0.15))):
        for ac in sorted(_profils()):
            im = Image.open(STATIC / "assets" / "img" / f"rr_ac_{nom.format(ac)}.png")
            assert im.mode == "RGBA" and im.width == largeur, (ac, nom, im.mode, im.size)
            histogramme = im.getchannel("A").histogram()
            couverture = sum(histogramme[128:]) / (im.width * im.height)
            assert bornes[0] < couverture < bornes[1], (ac, nom, couverture)


def test_types_du_centre_ont_un_profil() -> None:
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    prefixes = [(re.compile("^" + p), cle) for p, cle in _prefixes(js)]
    du_centre = _du_centre(js)
    table = json.loads((STATIC / "dcs_types_livrees.json").read_text(encoding="utf-8"))["types"]
    assert table and du_centre
    assert set(du_centre) <= set(table), sorted(set(du_centre) - set(table))
    for code, types in table.items():
        if not types:
            assert code not in du_centre, code
            continue
        assert code in du_centre, code
        for type_dcs in types:
            cle = next((c for rx, c in prefixes if rx.match(type_dcs)), None)
            assert cle == du_centre[code], (code, type_dcs, cle)
