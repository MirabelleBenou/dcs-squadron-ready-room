"""Lot « rr-public-licence » (v1.0117) -- la licence, le crédit et l'origine des fichiers de présentation.

Trois tests, sans fixture ni base : le crédit est à l'écran, la licence porte le terme de l'article 7(b), et chaque
image, police et figure est nommée dans `ASSETS.md` ou dans `LICENSES.md`.
"""
from __future__ import annotations

import re
from pathlib import Path

_RACINE = Path(__file__).resolve().parent.parent

_ATTRIBUTION = "Based on Squadron Ready Room by MirabelleBenou and the 4th VEAW virtual wing"
_DEPOT = "https://github.com/MirabelleBenou/dcs-squadron-ready-room"


def _lire(relatif: str) -> str:
    return (_RACINE / relatif).read_text(encoding="utf-8")


def test_credit_a_l_ecran():
    attendu = f'{_ATTRIBUTION} — <a href="{_DEPOT}"'
    for relatif in ("app/static/index.html", "app/templates/login.html"):
        assert _lire(relatif).count(attendu) == 1, f"{relatif} : la ligne de crédit n'est pas là une fois"


def test_licence_7b():
    licence = _lire("LICENSE")
    assert licence.startswith("GNU AFFERO GENERAL PUBLIC LICENSE"), "LICENSE ne commence pas par l'AGPL"
    assert "Additional terms under section 7(b)" in licence, "le paragraphe de l'article 7(b) manque"
    assert f"“{_ATTRIBUTION} — {_DEPOT}”" in licence, "l'attribution entre guillemets typographiques manque"


def _fichiers(relatif: str, suffixe: str | None = None, sauf: tuple[str, ...] = ()) -> list[Path]:
    dossier = _RACINE / relatif
    return sorted(
        p for p in dossier.rglob("*")
        if p.is_file() and p.name not in sauf and (suffixe is None or p.suffix == suffixe)
    )


def test_assets_tous_nommes():
    manques: list[str] = []
    assets = _lire("ASSETS.md")
    for dossier, sauf in (
        ("app/static/assets/img", ("SOURCES.txt",)),
        ("app/static/assets/marque", ()),
        ("manuel/contenu/figures", ()),
    ):
        for fichier in _fichiers(dossier, sauf=sauf):
            if f"`{fichier.name}`" not in assets:
                manques.append(f"ASSETS.md ne nomme pas {fichier.relative_to(_RACINE).as_posix()}")
    polices = _RACINE / "app/static/assets/fonts"
    licences = (polices / "LICENSES.md").read_text(encoding="utf-8")
    for fichier in _fichiers("app/static/assets/fonts", ".woff2"):
        if f"`{fichier.name}`" not in licences:
            manques.append(f"LICENSES.md ne nomme pas {fichier.name}")
    for lie in re.findall(r"\]\(([^)]+)\)", licences):
        if "://" in lie or lie.startswith("#"):
            continue
        if not (polices / lie).is_file():
            manques.append(f"LICENSES.md lie {lie}, absent du dossier des polices")
    assert not manques, "origine non dite :\n" + "\n".join(manques)
