"""Lot « Le Manuel Pilote, le socle » (`v1.0053`) -- le Manuel Pilote, un document
buildé (`manuel/build_manuel.py`) servi par l'application à `/manuel/`, derrière
la règle d'accès de `/`.

Huit tests : cinq du socle, sur le patron de `test_suites_servies.py` : le client est le
`TestClient` de FastAPI sur `app.main.app`, la garde se remplace par
`dependency_overrides[get_current_user_optional]` (vidé après chaque test). Ni
base, ni réseau : le lifespan ne tourne pas. Le quatrième fait échouer `pytest`
dès que le manuel commité n'est plus à jour (un libellé renommé, un écran
ajouté) : le manuel ne peut plus vieillir sans bruit. Les trois derniers (`v1.0123`, `test_version_rr_v` et
`test_credit_couverture` ; puis `test_annexe_b`, lot « annexe B · Aide ») construisent sur une copie.
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : il
# fausserait la ligne de `pytest` (« 1 warning »). On n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

from app.auth import get_current_user_optional
from app.main import app

RACINE = Path(__file__).resolve().parent.parent

# La garde remplacée : un membre connecté, ou personne.
_MEMBRE = lambda: {"id": "1", "name": "Test", "roles": [], "lang": "fr"}  # noqa: E731
_PERSONNE = lambda: None  # noqa: E731


def test_sans_session_retour_accueil():
    app.dependency_overrides[get_current_user_optional] = _PERSONNE
    try:
        client = TestClient(app, follow_redirects=False)
        r = client.get("/manuel/")
        assert r.status_code == 307
        assert r.headers["location"] == "/"
    finally:
        app.dependency_overrides.clear()


def test_manuel_servi():
    app.dependency_overrides[get_current_user_optional] = _MEMBRE
    try:
        client = TestClient(app, follow_redirects=False)
        r = client.get("/manuel/")
        assert r.status_code == 200
        assert r.headers["content-type"] == "text/html; charset=utf-8"
        assert r.content == (RACINE / "app" / "manuel" / "manuel.html").read_bytes()
        etag = r.headers["etag"]
        assert etag.startswith('"') and etag.endswith('"') and len(etag) > 2
    finally:
        app.dependency_overrides.clear()


def test_sans_barre_finale():
    # Sans session : la redirection ne lit pas la session.
    app.dependency_overrides[get_current_user_optional] = _PERSONNE
    try:
        client = TestClient(app, follow_redirects=False)
        r = client.get("/manuel")
        assert r.status_code == 307
        assert r.headers["location"] == "/manuel/"
    finally:
        app.dependency_overrides.clear()


def test_manuel_a_jour():
    r = subprocess.run(
        [sys.executable, "-B", "manuel/build_manuel.py", "--verifier"],
        cwd=RACINE,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_tuile_manuel():
    html = (RACINE / "app" / "static" / "index.html").read_text(encoding="utf-8")
    assert (
        '<a class="external-tile" href="/manuel/" target="_blank" rel="noopener noreferrer">'
        in html
    )
    # `I18N` se lit comme le fait le build : sous `node`, à l'évaluation.
    spec = importlib.util.spec_from_file_location("build_manuel", RACINE / "manuel" / "build_manuel.py")
    build = importlib.util.module_from_spec(spec)
    sys.modules["build_manuel"] = build
    avant = sys.dont_write_bytecode
    sys.dont_write_bytecode = True  # aucun .pyc dans manuel/
    try:
        spec.loader.exec_module(build)
    finally:
        sys.dont_write_bytecode = avant
    i18n = build.lire_i18n()
    assert i18n["fr"]["manual_tile"] == "Manuel Pilote"
    assert i18n["en"]["manual_tile"] == "Pilot’s Manual"


# Lot « Manuel avant le gel » (`v1.0123`) : deux tests, hors ligne, sur une copie (jamais le `VERSION` ni le
# `revisions.json` du dépôt).
def _construire_sur_copie(tmp_path, version, avant=None):
    """Copie le strict nécessaire au build, retire `revisions.json`, pose `version` dans `VERSION`, applique `avant(copie)` s'il est donné, lance le build ; rend (code, sortie, erreur, html)."""
    copie = tmp_path / "copie"
    shutil.copytree(RACINE / "manuel", copie / "manuel", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (copie / "app" / "static").mkdir(parents=True)
    for nom in ("app.js", "index.html"):
        shutil.copy2(RACINE / "app" / "static" / nom, copie / "app" / "static" / nom)
    # Sans `revisions.json` : un premier build, où la révision est la version (le fichier du dépôt, à jour, la garderait).
    (copie / "manuel" / "revisions.json").unlink(missing_ok=True)
    (copie / "VERSION").write_text(version + "\n", encoding="utf-8")
    if avant is not None:
        avant(copie)
    r = subprocess.run([sys.executable, "-B", "manuel/build_manuel.py"], cwd=copie, capture_output=True, text=True)
    sortie = copie / "app" / "manuel" / "manuel.html"
    html = sortie.read_text(encoding="utf-8") if sortie.is_file() else ""
    return r.returncode, r.stdout, r.stderr, html


def test_version_rr_v(tmp_path):
    for version in ("RR-V1.0.0", "RR-V1.0.0+3"):
        code, out, err, html = _construire_sur_copie(tmp_path / version.replace("+", "p"), version)
        assert code == 0, out + err
        assert f"Révision {version}" in html and f"Revision {version}" in html
    for version in ("RR-V1.0", "v1.0121", "1.012"):
        code, out, err, html = _construire_sur_copie(tmp_path / ("x" + version.replace(".", "_")), version)
        assert code == 1 and f"VERSION : « {version} » illisible" in err, out + err
        assert html == ""


def test_credit_couverture(tmp_path):
    phrase = "Based on Squadron Ready Room by MirabelleBenou and the 4th VEAW virtual wing"
    code, out, err, html = _construire_sur_copie(tmp_path / "ok", "1.0123")
    assert code == 0, out + err
    assert html.count(phrase) == 1
    couverture = html[html.index('id="couverture"'):html.index("</section>", html.index('id="couverture"'))]
    assert re.search(r'<div class="cv-credit">[^\n]*' + re.escape(phrase) + r"[^\n]*</div>", couverture)
    lignes = couverture.split("\n")
    i = next(n for n, l in enumerate(lignes) if l.startswith('<div class="cv-notice">'))
    assert lignes[i + 1].startswith('<div class="cv-credit">') and lignes[i + 1].endswith("</div>")
    assert lignes[i + 2].startswith('<div class="mark bot">')

    # Le bloc est obligatoire : sans sa ligne dans la pièce, le build refuse.
    def sans_credit(copie):
        piece = copie / "manuel" / "contenu" / "00_couverture.html"
        texte = piece.read_text(encoding="utf-8")
        piece.write_text(re.sub(r'[^\n]*<div class="cv-credit">.*?</div>[^\n]*\n?', "", texte, flags=re.S), encoding="utf-8")

    code, out, err, html = _construire_sur_copie(tmp_path / "sans", "1.0123", sans_credit)
    assert code == 1 and ".cv-credit absent" in err, out + err


# Lot « annexe B · Aide » : la sixième section du Manuel, ses 29 termes de glossaire et ses 11 cas de dépannage.
def test_annexe_b(tmp_path):
    code, out, err, html = _construire_sur_copie(tmp_path / "ok", "1.0123")
    assert code == 0, out + err
    ids = re.findall(r'<section class="m-section[^"]*" id="(s-[^"]+)"', html)
    assert ids[-2:] == ["s-A", "s-B"], ids
    debut = html.index('id="s-B"')
    section_b = html[debut:html.index("</section>", debut)]
    assert [f"p-B-1-{n:02d}" for n in range(1, 30)] == re.findall(r'id="(p-B-1-\d\d)"', section_b)
    assert [f"p-B-2-{c}" for c in "abcdefghijk"] == re.findall(r'id="(p-B-2-[a-z])"', section_b)

    # L'ordre des sections est contrôlé : une pièce B qui porte `s-C` fait refuser le build.
    def piece_c(copie):
        piece = copie / "manuel" / "contenu" / "60_annexe_B.html"
        texte = piece.read_text(encoding="utf-8")
        assert texte.count('id="s-B"') == 1
        piece.write_text(texte.replace('id="s-B"', 'id="s-C"'), encoding="utf-8")

    code, out, err, html = _construire_sur_copie(tmp_path / "c", "1.0123", piece_c)
    assert code == 1 and "s-A, s-B, dans cet ordre" in err, out + err
