"""Lot « rr-public-guide-1 » (v1.0122) -- l'annexe A du guide d'installation tient les variables et les réglages.

Les trois tables de l'annexe A (`docs/guide/{en,fr}/a-environment.md`, repérées par leur ancre `{ #app-variables }`,
`{ #compose-variables }`, `{ #settings }`) sont comparées au code : `app.config._AMORCAGE`, les variables
`${..._HOST_DIR}` de `docker-compose.yml` et `app.reglages.DEFINITIONS`. Une variable ou un réglage ajouté sans sa ligne
fait échouer la livraison ; une ligne qui nomme ce que le code ne lit plus aussi.

Le test lit `docs/` à la racine du dépôt. L'archive de déploiement n'en a pas (`docs/` est `export-ignore`) : il se saute.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app import config, reglages

_RACINE = Path(__file__).resolve().parent.parent
_GUIDE = _RACINE / "docs" / "guide"
_LANGUES = ("en", "fr")
_NOM = re.compile(r"^`([A-Za-z0-9_]+)`")
_SEPARATEUR = re.compile(r"^\|[\s:|-]+\|\s*$")


def _annexe(langue: str) -> str:
    # Seule l'absence de `docs/` (l'archive de déploiement) saute le test ; `docs/` présent, une annexe manquante échoue.
    if not (_RACINE / "docs").is_dir():
        pytest.skip("docs/ absent : archive de déploiement, le guide n'y est pas")
    chemin = _GUIDE / langue / "a-environment.md"
    assert chemin.is_file(), f"annexe A introuvable : {chemin.relative_to(_RACINE)}"
    return chemin.read_text(encoding="utf-8")


def _noms(texte: str, ancre: str, langue: str) -> list[str]:
    """Les noms de la première colonne de la table qui suit le titre portant l'ancre."""
    lignes = texte.splitlines()
    debut = next((i for i, l in enumerate(lignes) if l.startswith("#") and "{ #" + ancre + " }" in l), None)
    assert debut is not None, f"[{langue}] ancre « {ancre} » introuvable dans l'annexe A"
    table: list[str] = []
    for ligne in lignes[debut + 1:]:
        if ligne.startswith("|"):
            table.append(ligne)
        elif table:
            break
    # L'en-tête et le séparateur passés, chaque ligne porte un nom entre accents graves en première cellule.
    assert len(table) > 2 and _SEPARATEUR.match(table[1]), f"[{langue}] la table de « {ancre} » n'a pas d'en-tête et de lignes"
    noms: list[str] = []
    for ligne in table[2:]:
        premiere = ligne.strip().strip("|").split("|")[0].strip()
        trouve = _NOM.match(premiere)
        assert trouve, f"[{langue}] « {ancre} » : ligne sans nom entre accents graves en première cellule : {ligne}"
        noms.append(trouve.group(1))
    return noms


def _variables_compose() -> set[str]:
    compose = (_RACINE / "docker-compose.yml").read_text(encoding="utf-8")
    return {"COMPOSE_FILE"} | set(re.findall(r"\$\{([A-Z_]+_HOST_DIR)", compose))


def test_annexe_a_variables_app():
    for langue in _LANGUES:
        noms = _noms(_annexe(langue), "app-variables", langue)
        manquantes = sorted(config._AMORCAGE - set(noms))
        assert not manquantes, f"[{langue}] §A.1 sans ligne pour : {manquantes}"


def test_annexe_a_variables_compose():
    attendues = _variables_compose()
    for langue in _LANGUES:
        noms = _noms(_annexe(langue), "compose-variables", langue)
        manquantes = sorted(attendues - set(noms))
        assert not manquantes, f"[{langue}] §A.2 sans ligne pour : {manquantes}"


def test_annexe_a_reglages():
    for langue in _LANGUES:
        noms = _noms(_annexe(langue), "settings", langue)
        manquants = sorted({d.cle for d in reglages.DEFINITIONS} - set(noms))
        assert not manquants, f"[{langue}] §A.3 sans ligne pour : {manquants}"


def test_annexe_a_aucune_ligne_perimee():
    sources = {
        "app-variables": set(config._AMORCAGE),
        "compose-variables": _variables_compose(),
        "settings": {d.cle for d in reglages.DEFINITIONS},
    }
    for langue in _LANGUES:
        texte = _annexe(langue)
        for ancre, connus in sources.items():
            noms = _noms(texte, ancre, langue)
            inconnus = sorted(set(noms) - connus)
            assert not inconnus, f"[{langue}] « {ancre} » nomme ce que le code ne lit plus : {inconnus}"
            doublons = sorted({n for n in noms if noms.count(n) > 1})
            assert not doublons, f"[{langue}] « {ancre} » nomme deux fois : {doublons}"
