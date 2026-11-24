"""Brief SONNET Lot « L'appareil de l'escadrille » : la normalisation des
appareils qu'une escadrille déclare au Centre (`_normalize_aircraft`,
app/command/api.py), hors ligne -- pas de base, pas de réseau.

1. `test_normalisation` -- espaces de bord retirés, vides retirés, doublons
   retirés sans tenir compte de la casse, ordre de saisie gardé.
2. `test_rien_de_declare` -- une liste vide, absente ou faite de vides
   s'enregistre NULL.
3. `test_limites` -- quatre appareils passent ; cinq, ou un nom de 41
   caractères, sont refusés en 422.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.command.api import _normalize_aircraft


def test_normalisation() -> None:
    assert _normalize_aircraft([" Mi-24P ", "Mi-8", "", "mi-24p", "Mi-8 "]) == ["Mi-24P", "Mi-8"]


def test_rien_de_declare() -> None:
    assert _normalize_aircraft([]) is None
    assert _normalize_aircraft(None) is None
    assert _normalize_aircraft(["  ", ""]) is None


def test_limites() -> None:
    assert _normalize_aircraft(["A", "B", "C", "D"]) == ["A", "B", "C", "D"]
    with pytest.raises(HTTPException) as refus:
        _normalize_aircraft(["A", "B", "C", "D", "E"])
    assert refus.value.status_code == 422
    with pytest.raises(HTTPException) as refus:
        _normalize_aircraft(["x" * 41])
    assert refus.value.status_code == 422
