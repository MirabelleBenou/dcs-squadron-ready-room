"""Lot « Le Manuel Pilote : le bouton ? » (`v1.0063`) -- le « ? » de la barre ouvre le manuel à la
section de l'écran affiché ; l'App donne l'id de l'écran (`#vue=<id>`), le manuel le traduit en
ancre par `manuel/contenu/vues.json`. Le lien s'ouvre dans un onglet neuf (`_blank`, `v1.0064`). Quatre tests, hors ligne (ni base, ni réseau).

1. `test_bouton` -- `index.html` porte le lien `#help-btn`, avant `#settings-wrap`.
2. `test_textes` -- `app.js` porte les deux textes de `help_btn`, l'adresse `#vue=` et l'onglet neuf `"_blank"`, sans
   plus aucun `rr-manuel` dans `app.js` ni dans `index.html`.
3. `test_table_controlee` -- `controler_vues` accepte une table juste et refuse un écran manquant,
   une ancre absente et un écran en trop.
4. `test_manuel_porte_la_table` -- le manuel buildé porte `#m-vues`, égal à `vues.json`, et lit `vue=`.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RACINE = Path(__file__).resolve().parent.parent
INDEX = (RACINE / "app" / "static" / "index.html").read_text(encoding="utf-8")
APP_JS = (RACINE / "app" / "static" / "app.js").read_text(encoding="utf-8")
MANUEL_HTML = (RACINE / "app" / "manuel" / "manuel.html").read_text(encoding="utf-8")
MANUEL_JS = (RACINE / "manuel" / "manuel.js").read_text(encoding="utf-8")
VUES = RACINE / "manuel" / "contenu" / "vues.json"


def _build():
    """Le module du build, chargé comme le fait `test_manuel.py` (aucun .pyc dans manuel/)."""
    spec = importlib.util.spec_from_file_location("build_manuel_aide", RACINE / "manuel" / "build_manuel.py")
    build = importlib.util.module_from_spec(spec)
    sys.modules["build_manuel_aide"] = build
    avant = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(build)
    finally:
        sys.dont_write_bytecode = avant
    return build


def test_bouton():
    m = re.search(r'<a id="help-btn"[^>]*>', INDEX)
    assert m, "lien #help-btn absent"
    balise = m.group(0)
    for attr in ('href="/manuel/"', 'target="_blank"', 'data-i18n-title="help_btn"', 'data-i18n-aria="help_btn"'):
        assert attr in balise, attr
    assert m.start() < INDEX.index('id="settings-wrap"')


def test_textes():
    assert APP_JS.count('help_btn:"Manuel — cet écran"') == 1
    assert APP_JS.count('help_btn:"Manual — this screen"') == 1
    assert "#vue=" in APP_JS
    assert '"_blank"' in APP_JS
    assert "rr-manuel" not in APP_JS
    assert "rr-manuel" not in INDEX


def test_table_controlee():
    build = _build()
    sections = [
        {"attrs": {"data-couvre": "view-a view-b"}, "h3": [("1-1", "1", "A"), ("1-2", "2", "B")]},
        {"attrs": {"data-couvre": "modal-c"}, "h3": [("2-1", "1", "C")]},
        {"attrs": {"data-couvre": ""}, "h3": [("A-1", "1", "Annexe")]},
    ]
    juste = {"view-a": "1-1", "view-b": "A-1", "modal-c": "2-1"}
    with tempfile.TemporaryDirectory() as d:
        build.CONTENU = Path(d)

        def poser(table):
            (Path(d) / "vues.json").write_text(json.dumps(table), encoding="utf-8")

        poser(juste)
        assert build.controler_vues(sections) == juste
        # un écran couvert sans entrée
        poser({"view-a": "1-1", "view-b": "1-2"})
        with pytest.raises(build.ErreurBuild, match="modal-c"):
            build.controler_vues(sections)
        # une ancre qui n'est le <h3> d'aucune section qui couvre l'écran
        poser({**juste, "view-b": "9-9"})
        with pytest.raises(build.ErreurBuild, match="view-b"):
            build.controler_vues(sections)
        poser({**juste, "modal-c": "1-1"})
        with pytest.raises(build.ErreurBuild, match="modal-c"):
            build.controler_vues(sections)
        # un écran en trop
        poser({**juste, "view-z": "1-1"})
        with pytest.raises(build.ErreurBuild, match="view-z"):
            build.controler_vues(sections)


def test_manuel_porte_la_table():
    m = re.search(r'<script type="application/json" id="m-vues">(.*?)</script>', MANUEL_HTML, re.S)
    assert m, "#m-vues absent de app/manuel/manuel.html"
    assert json.loads(m.group(1)) == json.loads(VUES.read_text(encoding="utf-8"))
    assert 'indexOf("vue=")' in MANUEL_JS
    assert 'indexOf("vue=")' in MANUEL_HTML
