"""Lot « rr-changelog-unreleased » (`v1.0102`), repris par le lot « rr-release-v1-0-0 » -- `release.py` et le CHANGELOG.

Une seule fonction de test, sur des fichiers temporaires (jamais ceux du
dépôt) : la mise à jour de version (sans argument) n'écrit plus le CHANGELOG
(`CHANGELOG.md` inchangé à l'octet, plus de stub `- <à compléter>`) ; sans
`## Unreleased`, `main()` rend 1 et n'écrit rien (`VERSION` et `CHANGELOG.md`
inchangés à l'octet).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent


def _charge_release():
    spec = importlib.util.spec_from_file_location("release_sous_test", RACINE / "release.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_release_n_ecrit_pas_le_changelog(tmp_path, monkeypatch, capsys):
    release = _charge_release()
    piece = (RACINE / "CHANGELOG.md").read_bytes()  # copie de la pièce : l'original n'est jamais écrit

    vfile, cfile = tmp_path / "VERSION", tmp_path / "CHANGELOG.md"
    for chemin, contenu in ((vfile, b"1.0102"), (cfile, piece)):
        chemin.write_bytes(contenu)
    monkeypatch.setattr(release, "VERSION_FILE", vfile)
    monkeypatch.setattr(release, "CHANGELOG_FILE", cfile)
    monkeypatch.setattr(sys, "argv", ["release.py"])

    # 1. Avec « ## Unreleased » : la version avance, le CHANGELOG reste identique à l'octet (aucun stub).
    assert release.main() == 0
    capsys.readouterr()
    assert vfile.read_bytes() == b"1.0103"
    assert cfile.read_bytes() == piece

    # 2. Sans « ## Unreleased » : code 1, message en français, rien d'écrit.
    sans = piece.replace(b"## Unreleased", b"## En attente")
    vfile.write_bytes(b"1.0102")
    cfile.write_bytes(sans)
    assert release.main() == 1
    assert "Unreleased" in capsys.readouterr().err
    assert vfile.read_bytes() == b"1.0102"
    assert cfile.read_bytes() == sans
