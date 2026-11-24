"""Brief SONNET Lot « Le détecteur et l'hygiène » : trois invariants
déterministes du bilan des destructions partagé (`_bilan_des_vols`,
app/debrief/api.py), hors ligne -- pas de base, pas de clé API, comme
`test_lot_fusion.py`. Un vol est ici un objet minimal qui porte les trois
attributs lus par le calcul : `object_id`, `coalition`, `stats`.

1. `test_bilan_session_francfort_inchange` -- sur la fixture Francfort, qui
   ne contient aucun fratricide, le bilan de session est exactement celui
   que l'ancien agrégat de `get_session` avait servi, figé dans la
   fixture : mêmes catégories, mêmes comptes, même ordre, 38 abattages.

2. `test_bilan_session_somme_des_vols` -- le bilan de session est la somme
   des bilans vol par vol : un seul calcul, un seul critère.

3. `test_fratricide_hors_bilan` -- un abattage est fratricide quand le camp
   de sa cible est celui du tireur : camp porté par l'abattage
   (`target_coalition`), sinon camp d'un autre vol de la session ; le camp
   porté prime sur le repli ; sans camp connu, l'abattage compte.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _bilan_des_vols

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "89f20c83-54ec-4fd4-bf0c-1700463ff155.json"


def _vols_francfort() -> tuple[list[SimpleNamespace], dict]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    vols = [
        SimpleNamespace(object_id=f["object_id"], coalition=f["coalition"], stats=f["stats"])
        for f in fixture["flights"]
    ]
    return vols, fixture


def _camps(vols: list[SimpleNamespace]) -> dict:
    return {str(v.object_id): v.coalition for v in vols if v.object_id is not None}


def test_bilan_session_francfort_inchange() -> None:
    vols, fixture = _vols_francfort()
    bilan = _bilan_des_vols(vols, _camps(vols))
    assert bilan["kills_by_category"] == fixture["kills_by_category"]
    assert bilan["n_kills_validated"] == fixture["n_kills_validated"] == 38
    assert bilan["n_fratricides"] == 0


def test_bilan_session_somme_des_vols() -> None:
    vols, _ = _vols_francfort()
    camps = _camps(vols)
    session = _bilan_des_vols(vols, camps)
    somme: Counter = Counter()
    fratricides = 0
    for v in vols:
        un_vol = _bilan_des_vols([v], camps)
        fratricides += un_vol["n_fratricides"]
        for r in un_vol["kills_by_category"]:
            somme[r["category"]] += r["count"]
    assert {r["category"]: r["count"] for r in session["kills_by_category"]} == dict(somme)
    assert session["n_fratricides"] == fratricides


def test_fratricide_hors_bilan() -> None:
    tireur = SimpleNamespace(object_id="1", coalition="2", stats={"kills": [
        # repli : la cible est un autre vol bleu de la session -> fratricide
        {"target_object_id": "2", "target_unit_type": "F-4E-45MC"},
        # camp porté par l'abattage, cible au sol bleue -> fratricide
        {"target_object_id": "99", "target_coalition": "2", "target_unit_type": "M-1 Abrams"},
        # le camp porté prime sur le repli -> victoire
        {"target_object_id": "2", "target_coalition": "1", "target_unit_type": "F-4E-45MC"},
        # aucun camp connu -> victoire
        {"target_object_id": "98", "target_unit_type": "T-55"},
    ]})
    equipier = SimpleNamespace(object_id="2", coalition="2", stats={"kills": []})
    bilan = _bilan_des_vols([tireur, equipier], {"1": "2", "2": "2"})
    assert bilan["n_fratricides"] == 2
    assert bilan["n_kills_validated"] == 2
    assert {r["category"]: r["count"] for r in bilan["kills_by_category"]} == {"Avion": 1, "Char": 1}
