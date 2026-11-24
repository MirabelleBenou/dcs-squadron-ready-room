"""Lot « rr-public-guide-1 » (v1.0122) -- `init-env.sh` écrit le `.env` du premier démarrage, et rien d'autre.

Chaque test copie le script dans un dossier temporaire et lui parle par l'entrée standard, une réponse par ligne.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

from cryptography.fernet import Fernet

from app import defense

_RACINE = Path(__file__).resolve().parent.parent
_SCRIPT = _RACINE / "init-env.sh"
_EXEMPLE = _RACINE / ".env.example"

_CLIENT_ID = "123456789012345678"
_GUILD_ID = "234567890123456789"
_ADMINS = "345678901234567890,456789012345678901"
_SECRET = "s3cr3t_valeur-du-client"   # un `-` et un `_` : le jeu des secrets Discord
_URL = "https://readyroom.example.org"

_REFUS_ENV = ".env already exists: rename it first (mv .env .env.old)."


def _dossier(tmp_path: Path) -> Path:
    shutil.copy(_SCRIPT, tmp_path / "init-env.sh")
    return tmp_path


def _joue(dossier: Path, lignes: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sh", "init-env.sh"], cwd=dossier, input="".join(l + "\n" for l in lignes),
        capture_output=True, text=True, timeout=60,
    )


def _reponses(option: str) -> list[str]:
    return [_URL, option, _CLIENT_ID, _GUILD_ID, _SECRET, _ADMINS]


def _valeurs(texte: str) -> list[tuple[str, str]]:
    """Les lignes de valeur (`NOM=valeur`, non commentées), dans l'ordre."""
    return [tuple(l.split("=", 1)) for l in texte.splitlines() if re.match(r"[A-Z][A-Z0-9_]*=", l)]


def test_refuse_env_existant(tmp_path):
    dossier = _dossier(tmp_path)
    contenu = b"BASE_URL=https://deja.example.org\r\nCONFIG_KEY=\x00\xff garde\n"
    (dossier / ".env").write_bytes(contenu)
    r = _joue(dossier, _reponses("A"))
    assert r.returncode == 1
    assert _REFUS_ENV in r.stdout + r.stderr
    assert (dossier / ".env").read_bytes() == contenu


def test_refuse_saisies_invalides(tmp_path):
    dossier = _dossier(tmp_path)
    # Adresses refusées : sans https, avec / final, avec espace, avec un guillemet, avec un port (Compose interpole le .env).
    mauvaises = ["http://readyroom.example.org", _URL + "/", "https://a b.example.org", 'https://ready"room.example.org',
                 _URL + ":8443"]
    r = _joue(dossier, mauvaises + [_URL, "C", "A", "12345", _CLIENT_ID, "abcdefghijklmnopqr", _GUILD_ID,
                                   "avec espace", "pa$$word-ok", _SECRET, "345678901234567890,",
                                   "345678901234567890, 4", "345678901234567890,ab", _ADMINS])
    assert r.returncode == 0, r.stderr
    # Chaque réponse refusée a été redemandée : 5 adresses, 1 option, 2 identifiants, 2 secrets (espace, `$`), 3 listes.
    assert (r.stdout + r.stderr).count("Not accepted") == 5 + 1 + 2 + 2 + 3
    valeurs = dict(_valeurs((dossier / ".env").read_text(encoding="utf-8")))
    assert valeurs["BASE_URL"] == _URL
    assert valeurs["DISCORD_CLIENT_ID"] == _CLIENT_ID and valeurs["DISCORD_GUILD_ID"] == _GUILD_ID
    assert valeurs["DISCORD_CLIENT_SECRET"] == _SECRET and valeurs["ADMIN_IDS"] == _ADMINS

    # Une entrée qui s'achève sur une réponse refusée : code 1, aucun .env.
    for fin in ([_URL, "A", "abc"], [_URL, "A", _CLIENT_ID, _GUILD_ID, _SECRET, "http://pas-un-id"], ["http://x"]):
        autre = tmp_path / "autre"
        autre.mkdir(exist_ok=True)
        for p in autre.iterdir():
            p.unlink()
        shutil.copy(_SCRIPT, autre / "init-env.sh")
        r = _joue(autre, fin)
        assert r.returncode == 1, fin
        assert not (autre / ".env").exists(), fin


def test_env_produit(tmp_path):
    exemple = _EXEMPLE.read_text(encoding="utf-8").splitlines()
    noms_exemple = [n for n, _ in _valeurs("\n".join(exemple))]
    for option in ("A", "B"):
        dossier = tmp_path / option
        dossier.mkdir()
        _dossier(dossier)
        r = _joue(dossier, _reponses(option))
        assert r.returncode == 0, r.stderr
        chemin = dossier / ".env"
        assert stat.S_IMODE(chemin.stat().st_mode) == 0o600
        texte = chemin.read_text(encoding="utf-8")
        valeurs = dict(_valeurs(texte))
        assert defense.secret_refuse(valeurs["SESSION_SECRET"]) is None
        Fernet(valeurs["CONFIG_KEY"].encode())
        env = {"PATH": os.environ["PATH"], "CONFIG_KEY": valeurs["CONFIG_KEY"], "ADMIN_IDS": valeurs["ADMIN_IDS"]}
        verdict = subprocess.run([sys.executable, "-B", "-m", "app.reglages"], cwd=_RACINE, env=env,
                                 capture_output=True, text=True, timeout=60)
        assert verdict.returncode == 0, verdict.stderr
        assert "changeme" not in texte and "change_this" not in texte
        assert valeurs["POSTGRES_USER"] == "readyroom" and valeurs["POSTGRES_DB"] == "readyroom"
        assert len(valeurs["POSTGRES_PASSWORD"]) == 48
        # Un secret valide qui contient `-` et `_` est relu à l'octet.
        assert valeurs["DISCORD_CLIENT_SECRET"] == _SECRET and valeurs["BASE_URL"] == _URL
        assert f"DISCORD_CLIENT_SECRET={_SECRET}\n".encode() in chemin.read_bytes()
        # A : la ligne COMPOSE_FILE est écrite ; B : elle reste en commentaire.
        assert ("COMPOSE_FILE" in valeurs) == (option == "A")
        if option == "A":
            assert valeurs["COMPOSE_FILE"] == "docker-compose.yml:compose.caddy.yml"
        # Mêmes noms, même ordre que les lignes de valeur de .env.example (plus COMPOSE_FILE en A).
        attendus = noms_exemple + (["COMPOSE_FILE"] if option == "A" else [])
        assert [n for n, _ in _valeurs(texte)] == attendus
        # Mêmes commentaires, au même endroit : seules les lignes de valeur (et COMPOSE_FILE en A) diffèrent.
        ecrit = texte.splitlines()
        assert len(ecrit) == len(exemple)
        for modele, obtenu in zip(exemple, ecrit):
            if re.match(r"[A-Z][A-Z0-9_]*=", modele):
                assert obtenu.split("=", 1)[0] == modele.split("=", 1)[0]
            elif option == "A" and modele == "# COMPOSE_FILE=docker-compose.yml:compose.caddy.yml":
                assert obtenu == modele[2:]
            else:
                assert obtenu == modele
        # À l'écran : la clé des réglages, une fois ; aucun autre secret.
        ecran = r.stdout + r.stderr
        assert ecran.count(valeurs["CONFIG_KEY"]) == 1
        for secret in ("SESSION_SECRET", "POSTGRES_PASSWORD", "DISCORD_CLIENT_SECRET"):
            assert valeurs[secret] not in ecran, secret


def test_aucune_ecriture_hors_env(tmp_path):
    dossier = tmp_path / "ok"
    dossier.mkdir()
    _dossier(dossier)
    r = _joue(dossier, _reponses("B"))
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in dossier.iterdir()) == [".env", "init-env.sh"]
    refus = tmp_path / "refus"
    refus.mkdir()
    _dossier(refus)
    r = _joue(refus, ["http://x"])
    assert r.returncode == 1
    assert sorted(p.name for p in refus.iterdir()) == ["init-env.sh"]
