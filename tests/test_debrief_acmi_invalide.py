"""Lot « Les petites corrections de l'Escadre » (R1) : un dépôt ACMI qui n'est pas
une archive lisible rend 422 (jamais 500) et n'écrit aucune ligne ; un ACMI
valide répond comme avant.

Trois tests, sans base ni réseau : fausse base, dépendances remplacées, dossier
de stockage neuf (même patron que `tests/test_agent_reception.py`)."""
from __future__ import annotations

import io
import json
import sys
import warnings
import zipfile
from base64 import b64encode
from pathlib import Path
from types import SimpleNamespace

import itsdangerous
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from starlette.testclient import TestClient

from app.auth import get_current_user
from app.config import settings
from app.db import get_db
from app.debrief import acmi as acmi_mod
from app.debrief import engine
from app.main import app

MEMBRE = {"id": "111", "name": "Kestrel", "roles": []}
DETAIL = "Parsing impossible : le fichier n'est pas une archive ACMI de Tacview (zip attendu)."
ACMI_MINIMAL = (
    "﻿FileType=text/acmi/tacview\nFileVersion=2.2\n"
    "0,ReferenceTime=2026-11-01T18:00:00Z,Title=Essai,RecordingTime=2026-11-01T18:30:00Z\n"
    "#0.00\n"
)


class FausseBase:
    """Une base qui ne trouve rien et note tout ce qu'on lui demande d'écrire."""

    def __init__(self):
        self.ajouts = []

    def add(self, objet):
        self.ajouts.append(objet)

    async def scalar(self, *a, **k):
        return None

    async def get(self, *a, **k):
        return None

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def flush(self):
        pass


def _cookie() -> str:
    session = {"id": MEMBRE["id"], "roles": [], "exp": "2999-01-01T00:00:00+00:00"}
    donnees = b64encode(json.dumps(session).encode("utf-8"))
    return "session=" + itsdangerous.TimestampSigner(str(settings.SESSION_SECRET)).sign(donnees).decode("utf-8")


@pytest.fixture
def banc(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DEBRIEF_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "ADMIN_IDS", MEMBRE["id"])
    db = FausseBase()

    async def _db():
        return db

    async def _acces():
        return MEMBRE

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _acces
    try:
        yield SimpleNamespace(
            db=db, tmp=tmp_path,
            client=TestClient(app, follow_redirects=False, headers={"cookie": _cookie()}),
        )
    finally:
        app.dependency_overrides.clear()


def _zip(contenu: str) -> bytes:
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("x.txt.acmi", contenu)
    return tampon.getvalue()


def _deposer(banc, octets: bytes):
    return banc.client.post(
        "/api/debrief/upload",
        data={"kind": "acmi"},
        files={"file": ("essai.zip.acmi", octets, "application/octet-stream")},
    )


def test_un_octet_rend_422(banc):
    r = _deposer(banc, b"x")
    assert r.status_code == 422
    assert r.json() == {"detail": DETAIL}
    assert banc.db.ajouts == []        # ni debrief_upload ni debrief_session


def test_zip_sans_acmi_lisible_rend_422(banc):
    # Les données sont incompressibles : couper au milieu emporte l'annuaire de l'archive.
    bruit = "".join(chr(33 + (i * 7919) % 90) for i in range(4000))
    entier = _zip(ACMI_MINIMAL + bruit)
    coupe = entier[: len(entier) // 2]
    with pytest.raises(Exception) as lue:
        acmi_mod.parse_acmi(io.BytesIO(coupe))
    # La branche qui joue : celle de `zipfile.BadZipFile` (ou de ses sœurs, `zlib.error`, `EOFError`).
    assert isinstance(lue.value, (zipfile.BadZipFile, EOFError)) or type(lue.value).__name__ == "error"
    r = _deposer(banc, coupe)
    assert r.status_code == 422
    assert r.json() == {"detail": DETAIL}
    assert banc.db.ajouts == []


def test_acmi_valide_inchange(banc, monkeypatch):
    # Le moteur réel veut PostgreSQL : on le remplace par un moteur qui lit pour de bon l'archive.
    async def ingest(db, **kw):
        lu = acmi_mod.parse_acmi(io.BytesIO(kw["raw_bytes"]))
        return {
            "session_id": "00000000-0000-0000-0000-000000000001", "title": lu.meta.title,
            "mission_date": None, "acmi_present": True, "n_uploads": 1, "n_flights": 0, "n_kills": 0,
        }

    monkeypatch.setattr(engine, "ingest_file", ingest)
    r = _deposer(banc, _zip(ACMI_MINIMAL))
    assert r.status_code == 200
    assert set(r.json()) == {
        "session_id", "title", "mission_date", "acmi_present", "n_uploads", "n_flights", "n_kills",
        "display_title", "nature",
    }
    assert r.json()["title"] == "Essai"
