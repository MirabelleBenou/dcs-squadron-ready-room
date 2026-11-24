"""Lot « L'écran Archives du Centre » : la sauvegarde manuelle et l'écran
Archives, hors ligne -- ni base, ni réseau, ni `pg_dump`. Lot « Les
sauvegardes automatiques » : la forme `readyroom_auto-*`, sa purge, l'échéance
et le réglage, dans le même fichier.

1. `test_nom_valide` -- les cinq formes passent ; `..`, `.part`, un autre
   suffixe, `x.dump`, un `/` dans la révision et un horodatage à quatre chiffres
   d'une automatique sont refusés.
2. `test_lister` -- un `rev` de déploiement, deux manuelles (une avec écussons,
   une sans), une archive d'écussons orpheline, un `.part` et un `notes.txt` :
   trois entrées, dans l'ordre des dates posées par `os.utime`.
3. `test_purge` -- douze manuelles avec écussons et trois `rev` : les deux
   manuelles les plus anciennes partent avec leurs archives, les trois `rev`
   restent.
4. `test_archive_ecussons` -- les fichiers à la racine de l'archive ; un dossier
   absent donne une archive vide.
5. `test_commande_pg_dump` -- le mot de passe ne figure pas sur la ligne de
   commande, il passe par `PGPASSWORD`.
6. `test_derniere_escadrille` -- la désignation de l'appartenance close la plus
   récente.
7. `test_lister_automatique` -- une automatique avec écussons, une manuelle, un
   `rev` et une archive d'écussons automatique orpheline : trois entrées,
   l'automatique porte son origine, sa révision et son archive.
8. `test_purge_automatiques` -- neuf automatiques, trois manuelles, deux `rev` :
   chaque purge ne touche que ses propres fichiers.
9. `test_echeance` -- désactivée, jamais faite, 23 h 59 min, 24 h pile.
10. `test_valider_reglage` -- les vingt-quatre couples permis ; trois refus.
11. `test_etiquette_revision` -- la révision nettoyée, `vierge` sans révision.
"""
from __future__ import annotations

import os
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import sauvegardes, sauvegardes_auto
from app.command.api import _derniere_escadrille


def test_nom_valide():
    for bon in (
        "readyroom_rev-0033_20261010-1402.dump",
        "readyroom_rev-vierge_20261010-1402.dump",
        "readyroom_manuel-0034_20261010-163112.dump",
        "readyroom_manuel-0034_20261010-163112_ecussons.tar.gz",
        "readyroom_auto-0037_20261015-071200.dump",
        "readyroom_auto-0037_20261015-071200_ecussons.tar.gz",
    ):
        assert sauvegardes.nom_valide(bon), bon
    for mauvais in (
        "../readyroom_rev-0033_20261010-1402.dump",
        "readyroom_rev-0033_20261010-1402.dump.part",
        "readyroom_manuel-0034_20261010-163112.sql",
        "x.dump",
        "readyroom_rev-00/33_20261010-1402.dump",
        "readyroom_auto-0037_20261015-0712.dump",
    ):
        assert not sauvegardes.nom_valide(mauvais), mauvais


def _poser(dossier: Path, nom: str, octets: int, instant: datetime | None = None) -> Path:
    p = dossier / nom
    p.write_bytes(b"x" * octets)
    if instant is not None:
        t = instant.timestamp()
        os.utime(p, (t, t))
    return p


def test_lister(tmp_path):
    def u(jour, h):
        return datetime(2026, 10, jour, h, 0, tzinfo=timezone.utc)

    _poser(tmp_path, "readyroom_rev-0033_20261010-1402.dump", 300, u(10, 14))
    _poser(tmp_path, "readyroom_manuel-0034_20261011-080000.dump", 500, u(11, 8))
    _poser(tmp_path, "readyroom_manuel-0034_20261011-080000_ecussons.tar.gz", 40, u(11, 8))
    _poser(tmp_path, "readyroom_manuel-0034_20261009-100000.dump", 200, u(9, 10))
    _poser(tmp_path, "readyroom_manuel-0034_20261001-100000_ecussons.tar.gz", 40, u(1, 10))  # orpheline
    _poser(tmp_path, "readyroom_manuel-0034_20261011-090000.dump.part", 10, u(11, 9))
    _poser(tmp_path, "notes.txt", 5, u(11, 12))

    entrees = sauvegardes.lister(tmp_path)
    assert [e["fichier_base"] for e in entrees] == [
        "readyroom_manuel-0034_20261011-080000.dump",
        "readyroom_rev-0033_20261010-1402.dump",
        "readyroom_manuel-0034_20261009-100000.dump",
    ]
    neuve, deploiement, ancienne = entrees
    assert neuve["origine"] == "manuelle" and neuve["revision"] == "0034"
    assert neuve["base_octets"] == 500 and neuve["ecussons_octets"] == 40
    assert neuve["fichier_ecussons"] == "readyroom_manuel-0034_20261011-080000_ecussons.tar.gz"
    assert neuve["date"] == u(11, 8).isoformat()
    assert deploiement["origine"] == "migration" and deploiement["revision"] == "0033"
    assert deploiement["base_octets"] == 300
    assert deploiement["fichier_ecussons"] is None and deploiement["ecussons_octets"] is None
    assert ancienne["origine"] == "manuelle" and ancienne["base_octets"] == 200
    assert ancienne["fichier_ecussons"] is None and ancienne["ecussons_octets"] is None
    assert sauvegardes.lister(tmp_path / "absent") == []


def test_purge(tmp_path):
    manuelles = [f"readyroom_manuel-0034_202610{jour:02d}-100000" for jour in range(1, 13)]
    for base in manuelles:
        _poser(tmp_path, base + ".dump", 10)
        _poser(tmp_path, base + "_ecussons.tar.gz", 5)
    revs = [f"readyroom_rev-00{n}_20260901-1000.dump" for n in (31, 32, 33)]
    for nom in revs:
        _poser(tmp_path, nom, 10)

    retires = sauvegardes.purger_manuelles(tmp_path)

    assert sorted(retires) == sorted(
        [manuelles[0] + ".dump", manuelles[0] + "_ecussons.tar.gz",
         manuelles[1] + ".dump", manuelles[1] + "_ecussons.tar.gz"]
    )
    restants = sorted(p.name for p in tmp_path.iterdir())
    attendus = sorted(
        revs + [b + s for b in manuelles[2:] for s in (".dump", "_ecussons.tar.gz")]
    )
    assert restants == attendus


def test_archive_ecussons(tmp_path):
    source = tmp_path / "crests"
    (source / "_tmp").mkdir(parents=True)
    (source / "wing.png").write_bytes(b"w")
    (source / "3.png").write_bytes(b"3")
    (source / "_tmp" / "3.abc.tmp").write_bytes(b"t")
    cible = tmp_path / "e.tar.gz"
    sauvegardes.archiver_ecussons(source, cible)
    with tarfile.open(cible) as tar:
        assert sorted(tar.getnames()) == ["3.png", "wing.png"]
        assert tar.extractfile("wing.png").read() == b"w"

    vide = tmp_path / "vide.tar.gz"
    sauvegardes.archiver_ecussons(tmp_path / "absent", vide)
    with tarfile.open(vide) as tar:
        assert tar.getnames() == []


def test_commande_pg_dump():
    argv, env = sauvegardes.commande_pg_dump("postgresql+asyncpg://u:secret@db:5432/rr", "/b/x.dump.part")
    assert argv[0] == "pg_dump"
    assert not any("secret" in a for a in argv)
    assert "-Fc" in argv
    for drapeau, valeur in (("-h", "db"), ("-p", "5432"), ("-U", "u"), ("-d", "rr"), ("-f", "/b/x.dump.part")):
        assert argv[argv.index(drapeau) + 1] == valeur
    assert env["PGPASSWORD"] == "secret"


def test_derniere_escadrille():
    assert _derniere_escadrille([]) is None
    t = lambda mois: datetime(2026, mois, 1, tzinfo=timezone.utc)
    assert _derniere_escadrille([(t(3), "CHARLIE-33"), (t(9), "ALPHA-11"), (t(6), "BRAVO-22")]) == "ALPHA-11"


def test_lister_automatique(tmp_path):
    def u(jour, h):
        return datetime(2026, 10, jour, h, 0, tzinfo=timezone.utc)

    _poser(tmp_path, "readyroom_auto-0037_20261015-071200.dump", 400, u(15, 7))
    _poser(tmp_path, "readyroom_auto-0037_20261015-071200_ecussons.tar.gz", 30, u(15, 7))
    _poser(tmp_path, "readyroom_manuel-0037_20261014-100000.dump", 200, u(14, 10))
    _poser(tmp_path, "readyroom_rev-0036_20261010-1402.dump", 300, u(10, 14))
    _poser(tmp_path, "readyroom_auto-0037_20261001-100000_ecussons.tar.gz", 30, u(1, 10))  # orpheline

    entrees = sauvegardes.lister(tmp_path)
    assert [e["fichier_base"] for e in entrees] == [
        "readyroom_auto-0037_20261015-071200.dump",
        "readyroom_manuel-0037_20261014-100000.dump",
        "readyroom_rev-0036_20261010-1402.dump",
    ]
    auto = entrees[0]
    assert auto["origine"] == "automatique" and auto["revision"] == "0037"
    assert auto["base_octets"] == 400 and auto["ecussons_octets"] == 30
    assert auto["fichier_ecussons"] == "readyroom_auto-0037_20261015-071200_ecussons.tar.gz"


def test_purge_automatiques(tmp_path):
    autos = [f"readyroom_auto-0037_202610{jour:02d}-100000" for jour in range(1, 10)]
    for base in autos:
        _poser(tmp_path, base + ".dump", 10)
        _poser(tmp_path, base + "_ecussons.tar.gz", 5)
    manuelles = [f"readyroom_manuel-0037_202610{jour:02d}-110000" for jour in range(1, 4)]
    for base in manuelles:
        _poser(tmp_path, base + ".dump", 10)
        _poser(tmp_path, base + "_ecussons.tar.gz", 5)
    revs = [f"readyroom_rev-00{n}_20260901-1000.dump" for n in (35, 36)]
    for nom in revs:
        _poser(tmp_path, nom, 10)

    retires = sauvegardes.purger_automatiques(tmp_path, 7)
    assert sorted(retires) == sorted(
        [autos[0] + ".dump", autos[0] + "_ecussons.tar.gz",
         autos[1] + ".dump", autos[1] + "_ecussons.tar.gz"]
    )
    fichiers_manuelles = [b + s for b in manuelles for s in (".dump", "_ecussons.tar.gz")]
    fichiers_autos = [b + s for b in autos[2:] for s in (".dump", "_ecussons.tar.gz")]
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(revs + fichiers_manuelles + fichiers_autos)

    retires = sauvegardes.purger_manuelles(tmp_path, 0)
    assert sorted(retires) == sorted(fichiers_manuelles)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(revs + fichiers_autos)


def test_echeance():
    maintenant = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
    echeance = sauvegardes_auto.echeance
    assert echeance(None, maintenant, 0) is False
    assert echeance(maintenant - timedelta(days=30), maintenant, 0) is False
    assert echeance(None, maintenant, 24) is True
    assert echeance(maintenant - timedelta(hours=23, minutes=59), maintenant, 24) is False
    assert echeance(maintenant - timedelta(hours=24), maintenant, 24) is True


def test_valider_reglage():
    couples = [(h, n) for h in sauvegardes_auto.FREQUENCES_H for n in sauvegardes_auto.RETENTIONS]
    assert len(couples) == 24
    for h, n in couples:
        assert sauvegardes_auto.valider_reglage(h, n) == {"intervalle_h": h, "garder": n}
    for h, n in ((5, 7), (24, 8), (True, 7)):
        try:
            sauvegardes_auto.valider_reglage(h, n)
        except ValueError:
            continue
        raise AssertionError((h, n))


def test_etiquette_revision():
    assert sauvegardes.etiquette_revision("0037") == "0037"
    assert sauvegardes.etiquette_revision(None) == "vierge"
    assert sauvegardes.etiquette_revision("") == "vierge"
    assert sauvegardes.etiquette_revision("00/37") == "0037"
