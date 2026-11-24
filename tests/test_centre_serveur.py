"""Lot « Le Centre côté serveur » (v1.0093), hors ligne comme `test_archives.py` :
ni base, ni réseau.

1. `test_lister_quatre_familles` -- un `.dump` de chaque famille, l'archive
   d'écussons du déployeur et une orpheline : quatre entrées, aux origines
   `migration`, `manuelle`, `automatique`, `deploiement`.
2. `test_purges_epargnent_le_deployeur` -- les deux purges, à `garder=0`,
   laissent les `readyroom_deploiement-*`.
3. `test_nom_valide_deploiement` -- les deux formes du déployeur ; six refus,
   dont un saut de ligne final.
4. `test_bornes_escadrille` -- 24 / 32 / 100 passent, 25 / 33 / 101 sont refusés.
5. `test_identifiant_pris` -- casse, espaces, sommeil, `sauf_id`.
6. `test_import_sans_heurt` -- `ON CONFLICT` des deux instructions d'import.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import sauvegardes
from app.command.api import (
    _bornes_escadrille,
    _identifiant_pris,
    _insertion_arme,
    _insertion_type,
)

DEP = "readyroom_deploiement-0044_20261115-205209"


def _poser(dossier: Path, nom: str, octets: int, jour: int = 1) -> Path:
    p = dossier / nom
    p.write_bytes(b"x" * octets)
    t = datetime(2026, 11, jour, 10, 0, tzinfo=timezone.utc).timestamp()
    os.utime(p, (t, t))
    return p


def test_lister_quatre_familles(tmp_path):
    _poser(tmp_path, "readyroom_rev-0043_20261110-1402.dump", 100, 10)
    _poser(tmp_path, "readyroom_manuel-0043_20261111-080000.dump", 200, 11)
    _poser(tmp_path, "readyroom_auto-0043_20261112-080000.dump", 300, 12)
    _poser(tmp_path, f"{DEP}.dump", 400, 15)
    _poser(tmp_path, f"{DEP}_ecussons.tar.gz", 40, 15)
    _poser(tmp_path, "readyroom_deploiement-0043_20261101-100000_ecussons.tar.gz", 40, 1)  # orpheline
    entrees = sauvegardes.lister(tmp_path)
    assert [e["origine"] for e in entrees] == ["deploiement", "automatique", "manuelle", "migration"]
    assert len({e["fichier_base"] for e in entrees}) == 4
    dep = entrees[0]
    assert dep["fichier_base"] == f"{DEP}.dump" and dep["revision"] == "0044"
    assert dep["fichier_ecussons"] == f"{DEP}_ecussons.tar.gz" and dep["ecussons_octets"] == 40
    assert all(
        e["fichier_ecussons"] is None for e in entrees if e["origine"] != "deploiement"
    )
    assert not any("20261101" in e["fichier_base"] for e in entrees)


def test_purges_epargnent_le_deployeur(tmp_path):
    _poser(tmp_path, f"{DEP}.dump", 400)
    _poser(tmp_path, f"{DEP}_ecussons.tar.gz", 40)
    _poser(tmp_path, "readyroom_manuel-0043_20261111-080000.dump", 200)
    _poser(tmp_path, "readyroom_auto-0043_20261112-080000.dump", 300)
    sauvegardes.purger_manuelles(tmp_path, garder=0)
    sauvegardes.purger_automatiques(tmp_path, garder=0)
    assert sorted(p.name for p in tmp_path.iterdir()) == [f"{DEP}.dump", f"{DEP}_ecussons.tar.gz"]


def test_nom_valide_deploiement():
    assert sauvegardes.nom_valide(f"{DEP}.dump")
    assert sauvegardes.nom_valide(f"{DEP}_ecussons.tar.gz")
    for mauvais in (
        f"../{DEP}.dump",
        f"a/{DEP}.dump",
        f"{DEP}..dump",
        f"{DEP}.dump.part",
        "readyroom_deploiement-0044_20261115-2052.dump",
        f"{DEP}.dump\n",
    ):
        assert not sauvegardes.nom_valide(mauvais), mauvais


def test_bornes_escadrille():
    assert _bornes_escadrille("a" * 24, "b" * 32, "c" * 100) is None
    assert _bornes_escadrille(None, None, None) is None
    assert _bornes_escadrille("a" * 25, None, None) == "L'identifiant dépasse 24 caractères."
    assert _bornes_escadrille("a", "b" * 33, None) == "Le callsign dépasse 32 caractères."
    assert _bornes_escadrille("a", "b", "c" * 101) == "Le nom complet dépasse 100 caractères."
    # le premier refus, dans l'ordre
    assert _bornes_escadrille("a" * 25, "b" * 33, "c" * 101) == "L'identifiant dépasse 24 caractères."


def test_identifiant_pris():
    escs = [(3, "T-14"), (1, "ALPHA-11"), (2, "Escadrille en sommeil"), (4, "  Rapace ")]
    assert _identifiant_pris("  alpha-11 ", escs) == "ALPHA-11"
    assert _identifiant_pris("rapace", escs) == "  Rapace "  # espaces de bord stockés : ignorés, la désignation rendue telle quelle
    # en sommeil : compte -- la fonction reçoit toutes les escadrilles ; le statut se prouve au contrôle du v1.0093 (patch_doublon_sommeil)
    assert _identifiant_pris("ESCADRILLE EN SOMMEIL", escs) == "Escadrille en sommeil"
    assert _identifiant_pris("ALPHA-11", escs, sauf_id=1) is None                           # elle-même
    assert _identifiant_pris("T-15", escs) is None
    # la première AUTRE, par id croissant
    doubles = [(5, "x"), (2, "X")]
    assert _identifiant_pris("x", doubles) == "X"
    assert _identifiant_pris("x", doubles, sauf_id=2) == "x"


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_import_sans_heurt():
    base = {"cle": "F-16C", "display_name": "F-16C", "category": "Avion", "resolved_from": "table"}
    avec_libelle = _sql(_insertion_type({**base, "libelle": "Viper"}))
    assert "ON CONFLICT (unit_type) DO UPDATE" in avec_libelle and "libelle = excluded.libelle" in avec_libelle
    assert "display_name = excluded" not in avec_libelle and "category = excluded" not in avec_libelle
    forcee = _sql(_insertion_type({**base, "categorie_forcee": "Avion"}))
    assert "ON CONFLICT (unit_type) DO UPDATE" in forcee and "categorie_forcee = excluded.categorie_forcee" in forcee
    sans = _sql(_insertion_type(base))
    assert "ON CONFLICT (unit_type) DO NOTHING" in sans
    arme = _sql(_insertion_arme({"cle": "AIM-9M", "libelle": "Sidewinder"}))
    assert "ON CONFLICT (cle) DO UPDATE" in arme and "libelle = excluded.libelle" in arme
