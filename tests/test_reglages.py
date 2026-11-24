"""Lot « rr-env-epure » (`v1.0105`) -- dix tests des réglages gardés en base (`app/reglages.py`),
du `.env` réduit au premier démarrage (`app/config.py`) et du passage quotidien de 6 h
(`app/discord_rsvp.py`), sans base ni réseau : des fonctions pures, `Settings` lu dans un
environnement posé par `monkeypatch`, et le contrôle du démarrage joué en sous-processus.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography.fernet import Fernet

from app import reglages
from app.config import _AMORCAGE, Settings
from app.discord_rsvp import prochaine_echeance

RACINE = Path(__file__).resolve().parent.parent
CLES = [
    "REFERENCE_TZ", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "ANTHROPIC_EFFORT", "DISCORD_WEBHOOK_URL", "DISCORD_DIGEST_LOCALE",
    "DISCORD_DIGEST_TOKEN", "DISCORD_RSVP_ENABLED", "DISCORD_BOT_TOKEN", "DISCORD_PUBLIC_KEY",
    "DISCORD_NOTIFY_CHANNEL_ID", "DISCORD_RSVP_HORIZON_DAYS", "TILES_UPSTREAM",
    "WING_ID",
]


def test_definitions():
    assert [d.cle for d in reglages.DEFINITIONS] == CLES
    assert sorted(d.cle for d in reglages.DEFINITIONS if d.secret) == [
        "ANTHROPIC_API_KEY", "DISCORD_BOT_TOKEN", "DISCORD_DIGEST_TOKEN", "DISCORD_WEBHOOK_URL",
    ]
    for d in reglages.DEFINITIONS:
        assert d.defaut == Settings.model_fields[d.cle].default, d.cle
        assert d.cle not in _AMORCAGE, d.cle
        assert reglages.PAR_CLE[d.cle] is d
    assert len(reglages.RETIREES) == 17 and len(set(reglages.RETIREES)) == 17
    assert not set(reglages.RETIREES) & _AMORCAGE


def test_env_filtre(monkeypatch):
    monkeypatch.setenv("BASE_URL", "https://rr.example.org")
    for nom, valeur in (
        ("ANTHROPIC_MODEL", "modele-x"), ("REFERENCE_TZ", "UTC"), ("SESSION_TTL_DAYS", "1"),
    ):
        monkeypatch.setenv(nom, valeur)
    s = Settings(_env_file=None)
    assert s.BASE_URL == "https://rr.example.org"
    assert s.ANTHROPIC_MODEL == "" and s.REFERENCE_TZ == "Europe/Paris"
    assert s.SESSION_TTL_DAYS == 30


def test_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "ready")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss/w:rd")
    monkeypatch.setenv("POSTGRES_DB", "rr")
    assert Settings(_env_file=None).DATABASE_URL == "postgresql+asyncpg://ready:p%40ss%2Fw%3Ard@db:5432/rr"
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h:5432/d")
    assert Settings(_env_file=None).DATABASE_URL == "postgresql+asyncpg://u:p@h:5432/d"


def test_admins(monkeypatch):
    monkeypatch.setenv("ADMIN_IDS", "1, 2")
    s = Settings(_env_file=None)
    s.ADMINS_NOMMES = frozenset({"3"})
    assert s.admin_ids_set == {"1", "2", "3"}


def test_convertir():
    d = reglages.PAR_CLE
    ok = [
        ("ANTHROPIC_MODEL", "  modele-x ", "modele-x"),
        ("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/abc", "https://discord.com/api/webhooks/1/abc"),
        ("DISCORD_DIGEST_LOCALE", "FR", "fr"),
        ("DISCORD_RSVP_ENABLED", True, True),
        ("DISCORD_RSVP_ENABLED", "Oui", True),
        ("DISCORD_RSVP_ENABLED", "off", False),
        ("DISCORD_PUBLIC_KEY", "AB" * 32, "ab" * 32),
        ("DISCORD_NOTIFY_CHANNEL_ID", "123456789012345678", "123456789012345678"),
        ("DISCORD_RSVP_HORIZON_DAYS", 1, 1),
        ("DISCORD_RSVP_HORIZON_DAYS", "120", 120),
        ("TILES_UPSTREAM", "https://exemple.org/maps", "https://exemple.org/maps"),
        ("TILES_UPSTREAM", "  https://exemple.org/maps ", "https://exemple.org/maps"),
    ]
    for cle, brut, attendu in ok:
        valeur = reglages.convertir(d[cle], brut)
        assert valeur == attendu and type(valeur) is type(attendu), (cle, brut)
    refus = [
        ("DISCORD_RSVP_HORIZON_DAYS", 0), ("DISCORD_RSVP_HORIZON_DAYS", 121),
        ("DISCORD_RSVP_HORIZON_DAYS", True), ("DISCORD_RSVP_HORIZON_DAYS", "abc"),
        ("DISCORD_RSVP_HORIZON_DAYS", 3.5), ("DISCORD_RSVP_ENABLED", 1), ("DISCORD_RSVP_ENABLED", "peut-etre"),
        ("TILES_UPSTREAM", "http://exemple.org/maps"), ("TILES_UPSTREAM", "https://exemple.org/a b"),
        ("DISCORD_DIGEST_LOCALE", "de"), ("DISCORD_PUBLIC_KEY", "zz" * 32), ("DISCORD_PUBLIC_KEY", "ab" * 31),
        ("DISCORD_NOTIFY_CHANNEL_ID", "123"), ("ANTHROPIC_MODEL", "x" * 501), ("ANTHROPIC_MODEL", 5),
        ("ANTHROPIC_MODEL", ""), ("ANTHROPIC_MODEL", None),
    ]
    for cle, brut in refus:
        try:
            reglages.convertir(d[cle], brut)
        except ValueError:
            continue
        raise AssertionError(f"{cle} aurait dû refuser {brut!r}")
    assert reglages.convertir(d["ANTHROPIC_MODEL"], "x" * 500) == "x" * 500
    assert reglages.est_vide(None) and reglages.est_vide("  ") and not reglages.est_vide(0)
    assert reglages.en_texte(d["DISCORD_RSVP_ENABLED"], True) == "true"
    assert reglages.en_texte(d["DISCORD_RSVP_ENABLED"], False) == "false"
    assert reglages.en_texte(d["DISCORD_RSVP_HORIZON_DAYS"], 30) == "30"
    assert reglages.en_texte(d["ANTHROPIC_MODEL"], "m") == "m"


def test_chiffrement():
    cle = Fernet.generate_key().decode()
    clair = "jeton-secret-1234567890"
    jeton = reglages.chiffrer(cle, clair)
    assert reglages.dechiffrer(cle, jeton) == clair
    assert jeton.startswith("gAAAA") and clair not in jeton
    assert reglages.dechiffrer(Fernet.generate_key().decode(), jeton) is None
    assert reglages.dechiffrer(cle, "pas-un-jeton") is None
    assert reglages.cle_valide(cle) is True
    assert reglages.cle_valide("") is False and reglages.cle_valide("abc") is False


def test_lire_env():
    d = reglages.PAR_CLE
    assert reglages.lire_env(d["ANTHROPIC_MODEL"], {}) is None
    assert reglages.lire_env(d["ANTHROPIC_MODEL"], {"ANTHROPIC_MODEL": ""}) is None
    assert reglages.lire_env(d["ANTHROPIC_MODEL"], {"ANTHROPIC_MODEL": "   "}) is None
    assert reglages.lire_env(d["DISCORD_RSVP_ENABLED"], {"DISCORD_RSVP_ENABLED": "true"}) is True
    assert reglages.lire_env(d["DISCORD_RSVP_HORIZON_DAYS"], {"DISCORD_RSVP_HORIZON_DAYS": "30"}) == 30
    assert reglages.lire_env(d["DISCORD_RSVP_HORIZON_DAYS"], {"DISCORD_RSVP_HORIZON_DAYS": "300"}) is None
    assert reglages.lire_env(d["TILES_UPSTREAM"], {"TILES_UPSTREAM": "http://x.org"}) is None


def test_element():
    d = reglages.PAR_CLE
    quand = datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc)
    e = reglages.element(d["DISCORD_DIGEST_TOKEN"], "clair", True, True, quand, 42)
    assert (e["valeur"], e["defaut"], e["secret"], e["rempli"], e["lisible"]) == (None, None, True, True, True)
    assert (e["maj_le"], e["maj_par"]) == (quand.isoformat(), "42")
    e = reglages.element(d["DISCORD_DIGEST_TOKEN"], None, True, False, None, None)
    assert (e["lisible"], e["maj_le"], e["maj_par"]) == (False, None, None)
    e = reglages.element(d["ANTHROPIC_MODEL"], "modele-x", True, False, None, None)
    assert (e["valeur"], e["defaut"], e["lisible"], e["groupe"], e["type"]) == ("modele-x", "", True, "recit", "texte")
    assert "bornes" not in e and "choix" not in e
    e = reglages.element(d["DISCORD_RSVP_HORIZON_DAYS"], 14, False, True, None, None)
    assert (e["bornes"], e["valeur"], e["defaut"], e["rempli"]) == ([1, 120], 14, 14, False)
    e = reglages.element(d["DISCORD_DIGEST_LOCALE"], "en", False, True, None, None)
    assert e["choix"] == ["fr", "en"]
    assert list(e)[:10] == [
        "cle", "groupe", "type", "secret", "valeur", "defaut", "rempli", "lisible", "maj_le", "maj_par",
    ]


def test_controle():
    def lancer(**variables) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k not in ("CONFIG_KEY", "ADMIN_IDS")}
        env.update(variables)
        return subprocess.run(
            [sys.executable, "-B", "-m", "app.reglages"], cwd=RACINE, env=env, capture_output=True, text=True
        )

    cle = Fernet.generate_key().decode()
    refus = lancer()
    assert refus.returncode == 1 and "CONFIG_KEY" in refus.stderr
    assert lancer(CONFIG_KEY="abc", ADMIN_IDS="100000000000000001").returncode == 1
    refus = lancer(CONFIG_KEY=cle, ADMIN_IDS="")
    assert refus.returncode == 1 and "ADMIN_IDS" in refus.stderr
    assert lancer(CONFIG_KEY=cle, ADMIN_IDS=" , x").returncode == 1
    assert lancer(CONFIG_KEY=cle, ADMIN_IDS="100000000000000001").returncode == 0
    assert reglages.controle_au_demarrage({"CONFIG_KEY": cle, "ADMIN_IDS": "x,2"}) is None


def test_prochaine_echeance():
    def prochaine(iso: str) -> str:
        maintenant = datetime.fromisoformat(iso)
        return prochaine_echeance(maintenant).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")

    assert prochaine("2026-11-21T04:59:00+00:00") == "2026-11-21T05:00Z"
    assert prochaine("2026-11-21T05:00:00+00:00") == "2026-11-22T05:00Z"
    # Le passage à l'heure d'été (le 29 mars 2026) : 6 h à Paris vaut 4 h UTC.
    assert prochaine("2026-03-28T06:00:00+00:00") == "2026-03-29T04:00Z"
