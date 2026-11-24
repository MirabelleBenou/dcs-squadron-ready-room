"""Lot « Le fuseau horaire de l'escadre en réglage » (v1.0120, rr-fuseau-reglage) : le fuseau de
référence est un réglage en base (`REFERENCE_TZ`), lu à chaque usage.

Quatre tests, sans base ni réseau : des fonctions pures, `settings.REFERENCE_TZ` posé par `monkeypatch`.
"""
from __future__ import annotations

import ast
import asyncio
import re
import sys
import zoneinfo
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from app import api as api_module, discord_notify, recurrence, reglages
from app.config import settings
from app.debrief import api as debrief_api
from app.discord_rsvp import prochaine_echeance
from app.recurrence import Occurrence


def _utc(texte: str) -> datetime:
    return datetime.fromisoformat(texte.replace("Z", "+00:00"))


def test_type_fuseau():
    d = reglages.PAR_CLE["REFERENCE_TZ"]
    assert reglages.convertir(d, "Europe/Paris") == "Europe/Paris"
    assert reglages.convertir(d, "America/New_York") == "America/New_York"
    assert reglages.convertir(d, " Asia/Tokyo ") == "Asia/Tokyo"
    assert reglages.en_texte(d, "Asia/Tokyo") == "Asia/Tokyo"
    for mauvais in ("europe/paris", "Mars/Olympus", "Europe/Paris/x", "", "Factory", "localtime", "posixrules"):
        with pytest.raises(ValueError):
            reglages.convertir(d, mauvais)
    e = reglages.element(d, "Europe/Paris", True, True, None, None)
    assert e["type"] == "fuseau" and e["groupe"] == "fuseau" and e["defaut"] == "Europe/Paris"
    assert e["fuseaux"] == sorted(zoneinfo.available_timezones() - reglages.FUSEAUX_REFUSES)
    assert not set(e["fuseaux"]) & {"Factory", "localtime", "posixrules"}


def test_fuseau_suivi_sans_redemarrage(monkeypatch):
    monkeypatch.setattr(settings, "REFERENCE_TZ", "Europe/Paris")
    assert recurrence.fuseau_reference().key == "Europe/Paris"
    assert prochaine_echeance(_utc("2026-01-15T12:00Z")) == _utc("2026-01-16T05:00Z")
    assert debrief_api.jour_de_soiree(_utc("2026-01-16T03:00Z"), None) == date(2026, 1, 16)
    monkeypatch.setattr(settings, "REFERENCE_TZ", "America/New_York")
    assert recurrence.fuseau_reference().key == "America/New_York"
    assert prochaine_echeance(_utc("2026-01-15T12:00Z")) == _utc("2026-01-16T11:00Z")
    assert debrief_api.jour_de_soiree(_utc("2026-01-16T03:00Z"), None) == date(2026, 1, 15)

    # `GET /api/me` rend le fuseau réglé (la base et les lectures de droits sont doublées).
    base = MagicMock()
    base.execute = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    user = {"id": "1", "name": "Essai", "lang": "fr", "roles": []}
    with patch.object(api_module, "has_capability", AsyncMock(return_value=False)), \
            patch.object(api_module, "can_create_event", AsyncMock(return_value=False)), \
            patch.object(api_module, "has_command_access", AsyncMock(return_value=False)), \
            patch.object(api_module, "get_name_strip_tokens", AsyncMock(return_value=[])), \
            patch.object(api_module, "_read_wing_dict", AsyncMock(return_value=None)):
        moi = asyncio.run(api_module.read_me(user=user, db=base))
        assert moi["fuseau"] == "America/New_York"
        monkeypatch.setattr(settings, "REFERENCE_TZ", "Asia/Tokyo")
        assert asyncio.run(api_module.read_me(user=user, db=base))["fuseau"] == "Asia/Tokyo"


def test_pied_du_digest(monkeypatch):
    occ = Occurrence(
        event_id="e1", occ_date=date(2026, 9, 20), start_at_utc=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
        type="mission", game_label="DCS", map_name="Caucase", title="Mission", description="", duration_min=120,
        recurring=False, is_override=False, created_by="1",
    )

    def pied(langue: str) -> str:
        p = discord_notify.build_webhook_payload([(occ, 0, {})], [], "https://rr.example.org", langue, "Ready Room")
        return p["embeds"][0]["footer"]["text"]

    # Le défaut, sans aucun `monkeypatch` du réglage : le texte d'aujourd'hui.
    assert settings.REFERENCE_TZ == "Europe/Paris"
    assert pied("en") == "Timezone Europe/Paris" and pied("fr") == "Fuseau Europe/Paris"
    monkeypatch.setattr(settings, "REFERENCE_TZ", "America/New_York")
    assert pied("en") == "Timezone America/New_York" and pied("fr") == "Fuseau America/New_York"


def test_plus_de_paris_en_dur():
    """Garde d'`ast` sur les `.py` d'`app/` : aucun `ImportFrom` de `app.recurrence` (ou de `recurrence`, import relatif)
    ne nomme `REFERENCE_TZ`, aucun attribut `.REFERENCE_TZ` n'est lu sur un module importé de `app.recurrence` ;
    `app.recurrence` n'a plus l'attribut. Une expression régulière (guillemets simples ou doubles, blancs tolérés)
    écarte `ZoneInfo("Europe/Paris")` des `.py` et `timeZone:"Europe/Paris"` d'`app.js`."""
    assert not hasattr(recurrence, "REFERENCE_TZ")
    zone = re.compile(r"""ZoneInfo\(\s*['"]Europe/Paris['"]\s*\)""")
    for f in sorted((RACINE / "app").rglob("*.py")):
        texte = f.read_text(encoding="utf-8")
        assert not zone.search(texte), f
        arbre = ast.parse(texte)
        modules = set()   # les noms locaux qui désignent le module `app.recurrence`
        for n in ast.walk(arbre):
            if isinstance(n, ast.ImportFrom):
                if n.module in ("app.recurrence", "recurrence"):
                    assert "REFERENCE_TZ" not in [a.name for a in n.names], (f, n.lineno)
                elif n.module == "app" or (n.module is None and n.level):
                    modules |= {a.asname or a.name for a in n.names if a.name == "recurrence"}
            elif isinstance(n, ast.Import):
                modules |= {a.asname or a.name for a in n.names if a.name == "app.recurrence"}
        for n in ast.walk(arbre):
            if isinstance(n, ast.Attribute) and n.attr == "REFERENCE_TZ":
                base = ast.unparse(n.value)
                assert base not in modules and base != "app.recurrence", (f, n.lineno)
    js = (RACINE / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert not re.search(r"""timeZone\s*:\s*['"]Europe/Paris['"]""", js)
