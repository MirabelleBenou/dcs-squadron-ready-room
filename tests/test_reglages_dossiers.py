"""Lot « rr-centre-config-montages » (v1.0124) : le compte des fichiers des dossiers branchés (`app/reglages.py`, section 6).
Sur `tmp_path`, sans base ni serveur."""
from types import SimpleNamespace

from app import reglages


def test_absent(tmp_path):
    assert reglages.compter_fichiers(str(tmp_path / "absent")) is None


def test_vide(tmp_path):
    assert reglages.compter_fichiers(str(tmp_path)) == 0


def test_arbre_et_liens(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b").mkdir()
    (tmp_path / "un.txt").write_text("1")
    (tmp_path / "a" / "deux.txt").write_text("2")
    (tmp_path / "a" / "b" / "trois.txt").write_text("3")
    (tmp_path / "lien_fichier").symlink_to(tmp_path / "un.txt")
    (tmp_path / "lien_dossier").symlink_to(tmp_path / "a", target_is_directory=True)
    assert reglages.compter_fichiers(str(tmp_path)) == 3


def test_plafond_et_etat(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("x")
    assert reglages.compter_fichiers(str(tmp_path), plafond=3) == 3
    reglages_hote = SimpleNamespace(
        SUITES_DIR=str(tmp_path), TILES_DIR=str(tmp_path / "absent"), TILES_CACHE_DIR=str(tmp_path),
    )
    etat = reglages.etat_dossiers(reglages_hote)
    assert [d["id"] for d in etat] == ["suites", "tuiles", "tuiles_gardees"]
    tuiles = etat[1]
    assert tuiles["present"] is False and tuiles["fichiers"] is None
