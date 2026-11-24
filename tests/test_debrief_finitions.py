"""Lot « Finitions du Débrief » (v1.0075) : trois gardes, sans base.

1. les deux routes de campagnes que rien n'appelait sont retirées ;
2. la suppression d'une session dont le récit se rédige rend 409 (ARC-29) ;
3. un dépôt au-delà du plafond de son type rend 413, lecture arrêtée (ARC-04).
"""

import asyncio
import io
import uuid

import pytest
from fastapi import HTTPException

from app.debrief import api as dapi
from app.main import app


def test_routes_campagnes_mortes_retirees():
    routes = {(m, r.path) for r in app.routes for m in getattr(r, "methods", None) or ()}
    assert ("GET", "/api/debrief/campaigns") in routes
    assert ("POST", "/api/debrief/campaigns") not in routes
    assert ("PATCH", "/api/debrief/campaigns/{campaign_id}") not in routes


def test_suppression_refusee_pendant_la_redaction(monkeypatch):
    sid = uuid.uuid4()
    appels = []

    class _Session:
        id = sid

    async def _session_or_404(db, session_id):
        return _Session()

    async def _etat(db, session_id):
        return True, "x"

    async def _supprimer(db, session):
        appels.append(session)

    monkeypatch.setattr(dapi, "_session_or_404", _session_or_404)
    monkeypatch.setattr(dapi, "_redaction_en_cours_et_par", _etat)
    monkeypatch.setattr(dapi, "_supprimer_session", _supprimer)
    monkeypatch.setattr(dapi, "is_admin", lambda user: True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(dapi.delete_session(sid, user={}, db=None))
    assert exc.value.status_code == 409
    assert exc.value.detail == (
        "Une rédaction est en cours sur cette mission : réessayez quand elle sera finie."
    )
    assert appels == []


def test_depot_au_dela_du_plafond_rend_413(monkeypatch):
    plafond = 100_000
    monkeypatch.setattr(dapi, "PLAFOND_ACMI", plafond)
    lus = []

    class _Fichier:
        """Doublure d'un `UploadFile` : une lecture asynchrone par morceaux."""

        filename = "gros.acmi"

        def __init__(self, octets):
            self._flux = io.BytesIO(octets)

        async def read(self, n=-1):
            morceau = self._flux.read(n)
            lus.append(len(morceau))
            return morceau

    async def _ingest(*a, **k):
        raise AssertionError("ingest_file ne doit pas être appelée")

    monkeypatch.setattr(dapi.engine, "ingest_file", _ingest)
    fichier = _Fichier(b"x" * (plafond * 5))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            dapi.upload_file(
                file=fichier, kind="acmi", depositor=None, mission_name=None,
                wing_note=None, campaign_id=None, nature=None, user={}, db=None,
            )
        )
    assert exc.value.status_code == 413
    assert exc.value.detail == f"Fichier trop lourd : un ACMI fait {plafond // (1024 * 1024)} Mio au plus."
    # la lecture s'arrête au dépassement : pas un morceau de plus
    assert sum(lus) <= plafond + dapi.crests._CHUNK_SIZE
    assert sum(lus) < plafond * 5


def test_plafond_debrief_log_128_mio():
    # Lot « rr-debrief-plafond-depot » (v1.0096) : 128 Mio pour un debrief.log,
    # l'ACMI reste à 256 Mio.
    assert dapi.PLAFOND_DEBRIEF == 128 * 1024 * 1024
    assert dapi.PLAFOND_ACMI == 256 * 1024 * 1024
