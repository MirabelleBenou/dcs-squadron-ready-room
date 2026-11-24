"""Lot « rr-release-auto » (`v1.0118`) -- la grille de version : `release.py` (R2) et l'affichage de la version (R3).

R2 : `release.py` tourne sur des fichiers temporaires (jamais ceux du dépôt) sous les deux régimes : `VERSION` en `1.0xxx`
(comportement d'avant, à l'octet) et `VERSION` en `RR-V<x.y.z>[+<n>]`, avec `--release`. R3 : `app.js`, `login.html` et
`lien.html` portent la même règle d'affichage, vérifiée par sa présence (pas de navigateur).
"""
from __future__ import annotations

import datetime
import importlib.util
import re
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
AUJOURDHUI = datetime.date.today().isoformat()

CHANGELOG = (
    "# Changelog\n\nIntro.\n\n## Unreleased\n\n"
    "### v1.0117 — 2026-11-22\n- a\n\n### v1.0116 — 2026-11-21\n- b\n"
)


def _charge_release():
    spec = importlib.util.spec_from_file_location("release_grille_sous_test", RACINE / "release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Dossier:
    """Une copie temporaire de VERSION et CHANGELOG.md, et un `lance(*args)` qui joue `release.main()`."""

    def __init__(self, tmp_path, monkeypatch, capsys, version="1.0117", changelog=CHANGELOG):
        self.rel = _charge_release()
        self.v, self.c = tmp_path / "VERSION", tmp_path / "CHANGELOG.md"
        self.v.write_bytes(version.encode("utf-8"))
        self.c.write_bytes(changelog.encode("utf-8"))
        monkeypatch.setattr(self.rel, "VERSION_FILE", self.v)
        monkeypatch.setattr(self.rel, "CHANGELOG_FILE", self.c)
        self.monkeypatch, self.capsys = monkeypatch, capsys

    def lance(self, *args):
        self.monkeypatch.setattr(sys, "argv", ["release.py", *args])
        code = self.rel.main()
        sortie = self.capsys.readouterr()
        return code, sortie.out, sortie.err

    def etat(self):
        return self.v.read_bytes(), self.c.read_bytes()


@pytest.fixture
def dossier(tmp_path, monkeypatch, capsys):
    return Dossier(tmp_path, monkeypatch, capsys)


def _stub(label):
    return f"### {label} — {AUJOURDHUI}\n- <à compléter>\n\n"


# ---------------------------------------------------------------- R2 : le format 1.0xxx ne change pas

def test_dev_sans_argument_comme_avant(dossier):
    code, out, err = dossier.lance()
    assert code == 0 and err == ""
    assert out == "Version : 1.0117 → 1.0118\nZip cible : readyroom_v1_0118.zip\n"
    v, c = dossier.etat()
    assert v == b"1.0118"
    marque = "## Unreleased\n\n"
    k = CHANGELOG.index(marque) + len(marque)
    assert c == (CHANGELOG[:k] + _stub("v1.0118") + CHANGELOG[k:]).encode("utf-8")


def test_dev_set_et_force_gardent_leur_sens(dossier):
    assert dossier.lance("--set", "1.0200")[0] == 0 and dossier.v.read_bytes() == b"1.0200"
    code, _, err = dossier.lance("--set", "1.0100")
    assert code == 1 and "downgrade" in err and dossier.v.read_bytes() == b"1.0200"
    assert dossier.lance("--set", "1.0100", "--force")[0] == 0 and dossier.v.read_bytes() == b"1.0100"


def test_dev_plafond_inchange(dossier):
    dossier.v.write_bytes(b"1.9999")
    code, _, err = dossier.lance()
    assert code == 1 and "plafond" in err and dossier.v.read_bytes() == b"1.9999"


# ---------------------------------------------------------------- R2 : --release

def test_release_pose_la_ligne_sous_unreleased(dossier):
    code, out, err = dossier.lance("--release", "RR-V1.0.0")
    assert code == 0 and err == "" and out == "Version : 1.0117 → RR-V1.0.0\n"
    v, c = dossier.etat()
    assert v == b"RR-V1.0.0"
    marque = "## Unreleased\n\n"
    k = CHANGELOG.index(marque) + len(marque)
    attendu = CHANGELOG[:k] + f"## RR-V1.0.0 — {AUJOURDHUI}\n\n" + CHANGELOG[k:]
    assert c == attendu.encode("utf-8")
    # les sections ### déjà là passent sous la release ; « ## Unreleased » reste, vide
    texte = c.decode("utf-8")
    assert texte.index("## Unreleased") < texte.index("## RR-V1.0.0") < texte.index("### v1.0117")
    assert re.search(r"## Unreleased\n\n## RR-V1\.0\.0 — ", texte)


@pytest.mark.parametrize("tag", ["MT-V1.0.0", "rr-v1.0.0", "RR-V1.0", "RR-V1.0.0.1", "RR-V1.0.0+1", "V1.0.0", "1.0.0",
                                 "RR-V1.0.x", "RR-V1.0.0 ", "release/RR-V1.0.0", ""])
def test_release_tag_hors_format_refuse(dossier, tag):
    avant = dossier.etat()
    code, out, err = dossier.lance("--release", tag)
    assert code == 1 and out == "" and "RR-V<x.y.z>" in err
    assert dossier.etat() == avant


def test_release_sans_unreleased_refuse(tmp_path, monkeypatch, capsys):
    d = Dossier(tmp_path, monkeypatch, capsys, changelog=CHANGELOG.replace("## Unreleased", "## En attente"))
    avant = d.etat()
    code, _, err = d.lance("--release", "RR-V1.0.0")
    assert code == 1 and "Unreleased" in err and d.etat() == avant


@pytest.mark.parametrize("version,tag", [("RR-V1.0.0", "RR-V1.0.0"), ("RR-V1.0.0+4", "RR-V1.0.0"), ("RR-V1.2.0", "RR-V1.1.9"),
                                         ("RR-V1.2.0+1", "RR-V1.1.99"), ("RR-V2.0.0", "RR-V1.99.99"), ("RR-V1.10.0", "RR-V1.9.0")])
def test_release_pas_plus_haute_refuse(tmp_path, monkeypatch, capsys, version, tag):
    d = Dossier(tmp_path, monkeypatch, capsys, version=version)
    avant = d.etat()
    code, out, err = d.lance("--release", tag)
    assert code == 1 and out == "" and "plus haut" in err
    assert d.etat() == avant


def test_release_comparaison_numerique(tmp_path, monkeypatch, capsys):
    # 1.10.0 est plus haut que 1.9.0 (comparaison numérique, pas de texte)
    d = Dossier(tmp_path, monkeypatch, capsys, version="RR-V1.9.0")
    assert d.lance("--release", "RR-V1.10.0")[0] == 0
    assert d.v.read_bytes() == b"RR-V1.10.0"


def test_release_apres_des_numeros_de_dev(tmp_path, monkeypatch, capsys):
    d = Dossier(tmp_path, monkeypatch, capsys, version="RR-V1.0.0+3")
    assert d.lance("--release", "RR-V1.0.1")[0] == 0
    assert d.v.read_bytes() == b"RR-V1.0.1"


def test_release_ne_se_combine_pas_avec_set_ni_force(dossier):
    avant = dossier.etat()
    assert dossier.lance("--release", "RR-V1.0.0", "--set", "1.0200")[0] == 1
    assert dossier.lance("--release", "RR-V1.0.0", "--force")[0] == 1
    assert dossier.etat() == avant


# ---------------------------------------------------------------- R2 : les numéros de dev après la release

def test_suite_des_numeros_de_dev(dossier):
    assert dossier.lance("--release", "RR-V1.0.0")[0] == 0
    code, out, _ = dossier.lance()
    assert code == 0 and out == "Version : RR-V1.0.0 → RR-V1.0.0+1\n"
    assert dossier.v.read_bytes() == b"RR-V1.0.0+1"
    code, out, _ = dossier.lance()
    assert code == 0 and out == "Version : RR-V1.0.0+1 → RR-V1.0.0+2\n"
    assert dossier.v.read_bytes() == b"RR-V1.0.0+2"
    texte = dossier.c.read_text(encoding="utf-8")
    haut = texte[texte.index("## Unreleased"):texte.index("\n## RR-V1.0.0 — ") + 1]
    assert haut == (f"## Unreleased\n\n### RR-V1.0.0+2 — {AUJOURDHUI}\n- <à compléter>\n\n"
                    f"### RR-V1.0.0+1 — {AUJOURDHUI}\n- <à compléter>\n\n")
    assert texte.index("\n## RR-V1.0.0 — ") < texte.index("### v1.0117")


def test_dev_apres_release_sans_unreleased_refuse(tmp_path, monkeypatch, capsys):
    d = Dossier(tmp_path, monkeypatch, capsys, version="RR-V1.0.0",
                changelog=CHANGELOG.replace("## Unreleased", "## En attente"))
    avant = d.etat()
    code, _, err = d.lance()
    assert code == 1 and "Unreleased" in err and d.etat() == avant


@pytest.mark.parametrize("args", [("--set", "1.0200"), ("--force",), ("--set", "1.0200", "--force")])
@pytest.mark.parametrize("version", ["RR-V1.0.0", "RR-V1.0.0+2"])
def test_set_et_force_refusent_sous_rr_v(tmp_path, monkeypatch, capsys, version, args):
    d = Dossier(tmp_path, monkeypatch, capsys, version=version)
    avant = d.etat()
    code, _, err = d.lance(*args)
    assert code == 1 and "--set" in err and d.etat() == avant


def test_docstring_dit_les_trois_usages():
    doc = _charge_release().__doc__
    for mot in ("release.py --release RR-V<x.y.z>", "RR-V<x.y.z>+<n+1>", "--set X.YY", "1.0xxx"):
        assert mot in doc


# ---------------------------------------------------------------- R3 : l'affichage de la version

def _lit(chemin):
    return (RACINE / chemin).read_text(encoding="utf-8")


def test_app_js_une_fonction_unique():
    js = _lit("app/static/app.js")
    assert js.count("function versionAffichee(") == 1
    corps = js[js.index("function versionAffichee("):]
    corps = corps[:corps.index("\n}\n") + 3]
    assert 'startsWith("RR-V")' in corps and "`v${v}`" in corps
    # le pied et les éléments `data-rr-version` passent par elle ; plus aucun `v${data.version}` en dur
    assert "el.textContent = versionAffichee(data.version)" in js
    assert 'forEach((e) => { e.textContent = versionAffichee(data.version); })' in js
    assert "`v${data.version}`" not in js


@pytest.mark.parametrize("gabarit", ["app/templates/login.html", "app/templates/lien.html"])
def test_gabarits_portent_la_meme_regle(gabarit):
    html = _lit(gabarit)
    assert "indexOf('RR-V') === 0 ? v : 'v' + v" in html
    assert "'Squadron Ready Room · v'+d.version" not in html
    assert "'Squadron Ready Room · ' + (" in html


def test_la_regle_donne_le_bon_affichage():
    # La règle des trois fichiers, rejouée en Python : RR-V… tel quel, sinon un `v` devant.
    def affiche(version):
        v = str(version)
        return v if v.startswith("RR-V") else "v" + v
    assert affiche("RR-V1.0.0+3") == "RR-V1.0.0+3"
    assert affiche("RR-V1.0.0") == "RR-V1.0.0"
    assert affiche("1.0118") == "v1.0118"


def test_la_version_servie_reste_lisible_en_1_0xxx():
    assert re.fullmatch(r"1\.0\d{3}", _lit("VERSION").strip()) or re.fullmatch(r"RR-V\d+\.\d+\.\d+(\+\d+)?", _lit("VERSION").strip())
