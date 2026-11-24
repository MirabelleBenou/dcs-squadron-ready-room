"""Lot « rr-centre-config-modele-effort » (`v1.0108`) -- cinq tests de `reglages.lister_modeles()`
(la liste des modèles actifs d'Anthropic de la page Configuration), sans réseau : un
`httpx.MockTransport` posé dans `reglages._TRANSPORT`, la clé de l'API posée par `monkeypatch`
sur `settings`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import reglages
from app.config import settings



def _niveaux(*actifs: str) -> dict:
    return {n: {"supported": n in actifs} for n in ("low", "medium", "high", "xhigh", "max")}


def _modele(id_, nom, efforts, max_tokens, supporte=True, cycle=None):
    m = {
        "id": id_,
        "type": "model",
        "capabilities": {"effort": {"supported": supporte, **_niveaux(*efforts)}},
        "max_tokens": max_tokens,
    }
    if nom is not None:
        m["display_name"] = nom
    if cycle is not None:
        m["lifecycle"] = cycle
    return m


def _lister(monkeypatch, transport, cle="cle-d-essai-factice"):
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", cle)
    monkeypatch.setattr(reglages, "_TRANSPORT", transport)
    return asyncio.run(reglages.lister_modeles())


def test_sans_cle(monkeypatch):
    appels = []
    transport = httpx.MockTransport(lambda r: appels.append(r) or httpx.Response(200, json={"data": []}))
    assert _lister(monkeypatch, transport, cle="") == {"disponible": False, "raison": "cle", "modeles": []}
    assert appels == []


def test_filtre_et_ordre(monkeypatch):
    tous = ("low", "medium", "high", "xhigh", "max")
    vues = []

    def servir(requete: httpx.Request) -> httpx.Response:
        vues.append(requete)
        return httpx.Response(200, json={"has_more": True, "data": [
            _modele("modele-a", "Modèle A", tous, 128000, cycle="active"),
            _modele("modele-b", None, ("max", "low", "high", "medium"), None),
            _modele("modele-c", "Modèle C", tous, 128000, supporte=False),
            _modele("modele-d", "Modèle D", tous, 32000),
            _modele("modele-f", "Modèle F", tous, 128000, cycle="deprecated"),
            {"id": "modele-e", "display_name": "Modèle E", "capabilities": None, "max_tokens": 128000},
        ]})

    resultat = _lister(monkeypatch, httpx.MockTransport(servir))
    assert resultat == {"disponible": True, "raison": None, "modeles": [
        {"id": "modele-a", "nom": "Modèle A", "efforts": list(tous)},
        {"id": "modele-b", "nom": "modele-b", "efforts": ["low", "medium", "high", "max"]},
    ]}
    assert len(vues) == 1
    r = vues[0]
    assert r.method == "GET" and r.url.host == "api.anthropic.com" and r.url.path == "/v1/models"
    assert r.headers["x-api-key"] == "cle-d-essai-factice"
    assert r.headers["anthropic-version"] == "2026-10-21"
    assert r.url.params["limit"] == "100" and "lifecycle" not in r.url.params


def test_statut_refuse(monkeypatch):
    cle = "cle-d-essai-factice"
    corps = {"type": "error", "error": {"type": "invalid_request_error", "message": f"boom {cle}"}}
    transport = httpx.MockTransport(lambda r: httpx.Response(400, json=corps))
    assert _lister(monkeypatch, transport, cle=cle) == {
        "disponible": False, "raison": "erreur", "modeles": [],
        "detail": "HTTP 400 · invalid_request_error · boom ***",
    }


def test_transport_coupe(monkeypatch):
    def couper(requete: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("coupé", request=requete)

    assert _lister(monkeypatch, httpx.MockTransport(couper)) == {
        "disponible": False, "raison": "erreur", "modeles": [], "detail": "ConnectError",
    }


def test_corps_illisible(monkeypatch):
    a = _lister(monkeypatch, httpx.MockTransport(lambda r: httpx.Response(200, content=b"pas du JSON")))
    assert a["raison"] == "erreur" and a["detail"] and a["disponible"] is False and a["modeles"] == []
    b = _lister(monkeypatch, httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    assert b["raison"] == "erreur" and b["detail"] == "réponse sans liste"
