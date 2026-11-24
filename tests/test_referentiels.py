"""Lot « Les référentiels : types et armes » : l'import et la catégorie
forcée, hors ligne -- ni base, ni réseau.

1. `test_import_illisible` -- contrat faux, version 2, `types` absent :
   `ValueError`.
2. `test_import_bilan` -- sur un existant de trois types et deux armes :
   libellés posés, inchangés, une catégorie forcée, une catégorie remise à
   l'automatique (`null`), un type neuf inséré avec la catégorie de
   `categorize`.
3. `test_import_vide_ne_change_rien` -- `libelle` absent, `null` et `""` :
   aucun changement.
4. `test_import_refus` -- clé vide, libellé de 61 caractères, catégorie
   « Sous-marin », clé en double : quatre refus, le reste passe.
5. `test_categorie_cible` -- `FORCEES` vide : la catégorie de `categorize` ;
   `FORCEES = {"Container brown": "Static"}` : « Static ».
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.command.api import _analyser_import, _types_affiches
from app.debrief import referentiel

CONTRAT = "readyroom_referentiel_types_armes"

# Trois types vus (le premier porte un libellé, le deuxième une catégorie
# forcée), deux armes dont une a un libellé.
TYPES = {
    "T-55": {"libelle": "T-55", "categorie_forcee": None},
    "SAU Msta": {"libelle": None, "categorie_forcee": "Char"},
    "Container brown": {"libelle": None, "categorie_forcee": None},
}
ARMES = {"defa_553": "DEFA 553", "M-61": None}


def _fichier(types=None, armes=None, **autre):
    return {"contrat": CONTRAT, "version": 1,
            "types": [] if types is None else types,
            "armes": [] if armes is None else armes, **autre}


def test_import_illisible():
    with pytest.raises(ValueError):
        _analyser_import(_fichier(contrat="autre"), TYPES, ARMES)
    with pytest.raises(ValueError):
        _analyser_import(_fichier(version=2), TYPES, ARMES)
    sans_types = _fichier()
    del sans_types["types"]
    with pytest.raises(ValueError):
        _analyser_import(sans_types, TYPES, ARMES)
    with pytest.raises(ValueError):
        _analyser_import(_fichier(armes="pas une liste"), TYPES, ARMES)


def test_import_bilan():
    fichier = _fichier(
        types=[
            {"cle": "T-55", "libelle": "T-55"},                         # inchangé
            {"cle": "Container brown", "libelle": "Conteneur", "categorie": "Static"},  # posé + forcée
            {"cle": "SAU Msta", "libelle": "2S19 Msta", "categorie": None},  # posé + remise à l'automatique
            {"cle": "BMP-1", "libelle": "BMP-1"},                        # neuf : inséré
        ],
        armes=[
            {"cle": "defa_553", "libelle": "DEFA 553"},                  # inchangée
            {"cle": "M-61", "libelle": "M61 Vulcan"},                    # posée
        ],
    )
    r = _analyser_import(fichier, TYPES, ARMES)
    b = r["bilan"]
    assert b["types"] == {"poses": 3, "inchanges": 1, "forcees": 2}
    assert b["armes"] == {"poses": 1, "inchanges": 1}
    assert b["refuses"] == []
    par_cle = {w["cle"]: w for w in r["ecritures"]["types"]}
    assert set(par_cle) == {"Container brown", "SAU Msta", "BMP-1"}  # T-55 n'écrit rien
    assert par_cle["Container brown"]["categorie_forcee"] == "Static"
    assert par_cle["SAU Msta"]["categorie_forcee"] is None  # remise à l'automatique
    neuf = par_cle["BMP-1"]
    assert neuf["nouveau"] is True and neuf["libelle"] == "BMP-1"
    # le type neuf porte ce que le moteur aurait écrit
    from app.debrief import categorize
    assert (neuf["display_name"], neuf["category"], neuf["resolved_from"]) == categorize.categorize("BMP-1")
    assert [w["cle"] for w in r["ecritures"]["armes"]] == ["M-61"]


def test_import_vide_ne_change_rien():
    fichier = _fichier(
        types=[
            {"cle": "T-55"},
            {"cle": "SAU Msta", "libelle": None},
            {"cle": "Container brown", "libelle": ""},
            {"cle": "BMP-1", "libelle": ""},  # neuf, rien à poser : aucune ligne
        ],
        armes=[{"cle": "defa_553", "libelle": ""}, {"cle": "M-61", "libelle": None}, {"cle": "M-39"}],
    )
    r = _analyser_import(fichier, TYPES, ARMES)
    assert r["ecritures"] == {"types": [], "armes": []}
    assert r["bilan"]["types"] == {"poses": 0, "inchanges": 4, "forcees": 0}
    assert r["bilan"]["armes"] == {"poses": 0, "inchanges": 3}
    assert r["bilan"]["refuses"] == []


def test_import_refus():
    fichier = _fichier(
        types=[
            {"cle": "", "libelle": "Vide"},                                   # clé vide
            {"cle": "T-55", "libelle": "x" * 61},                             # libellé trop long
            {"cle": "BMP-1", "libelle": "BMP-1", "categorie": "Sous-marin"},  # catégorie inconnue
            {"cle": "BMP-2", "libelle": "BMP-2"},                             # passe
            {"cle": "BMP-2", "libelle": "Autre"},                             # clé en double
        ],
    )
    r = _analyser_import(fichier, TYPES, ARMES)
    assert len(r["bilan"]["refuses"]) == 4
    assert [x["cle"] for x in r["bilan"]["refuses"]] == ["", "T-55", "BMP-1", "BMP-2"]
    assert all(x["raison"] for x in r["bilan"]["refuses"])
    assert r["bilan"]["types"]["poses"] == 1
    assert [w["cle"] for w in r["ecritures"]["types"]] == ["BMP-2"]
    assert r["ecritures"]["types"][0]["libelle"] == "BMP-2"  # la première occurrence, pas la seconde


def test_categorie_cible():
    try:
        referentiel.FORCEES.clear()
        assert referentiel.categorie_cible("Container brown") == "Inconnu"
        assert referentiel.categorie_cible("T-55") == "Char"
        assert referentiel.categorie_cible(None) == "Inconnu"
        referentiel.FORCEES.update({"Container brown": "Static"})
        assert referentiel.categorie_cible("Container brown") == "Static"
        assert referentiel.categorie_cible("T-55") == "Char"  # les autres ne bougent pas
    finally:
        referentiel.FORCEES.clear()


def test_types_affiches():
    """Lot « Les référentiels n'affichent que les types vus » : une clé vue
    est gardée ; une clé non vue l'est seulement si elle porte un libellé ou
    une catégorie forcée."""
    def ligne(cle, libelle=None, forcee=None):
        return SimpleNamespace(unit_type=cle, libelle=libelle, categorie_forcee=forcee)

    lignes = [
        ligne("T-55"),                                   # vue
        ligne("AGM_65B"),                                # non vue, rien : écartée
        ligne("AIM-7M", libelle="AIM-7M"),               # non vue, libellé : gardée
        ligne("Container brown", forcee="Static"),       # non vue, catégorie forcée : gardée
    ]
    gardees = _types_affiches(lignes, {"T-55"})
    assert [r.unit_type for r in gardees] == ["T-55", "AIM-7M", "Container brown"]
