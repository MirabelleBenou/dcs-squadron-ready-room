"""Contrôle de la chaîne (brief FR source unique §5, « à défaut de clé » ;
correctif §④ : rendu visible par `pytest`) -- on ne peut pas jouer une
rédaction réelle (aucune clé Anthropic dans cet environnement), donc on
simule `llm.rediger` en succès et `llm.traduire` en échec, et on vérifie
le comportement NEUF du lot (geste ③) : `texte_fr` est écrit, `texte_en`
vaut `None`, et l'invalidation a été publiée.

Portée assumée, écrite dans le rapport de livraison : aucune base Postgres
réelle n'est disponible dans cet environnement d'exécution. Ce test
remplace `AsyncSessionLocal` par une session factice en mémoire (get/add/
delete/commit, sans SQL) et `_build_report_facts_for_session` par la
fiche réelle de la fixture Bataille de Francfort (déjà vérifiée au
rituel) -- il exerce donc l'ORCHESTRATION de `_redact_report_task`
(l'objet du geste ③), pas la couche SQL elle-même (inchangée par ce lot).

Aucune dépendance neuve (correctif §④ : pas de `pytest-asyncio`, absent de
`requirements.txt`) -- stdlib uniquement (`asyncio`, `unittest.mock`) plus
`pytest` lui-même pour la collecte. Les fonctions `test_*` sont
SYNCHRONES : elles appellent `asyncio.run(...)` elles-mêmes, pytest n'a
besoin d'aucun plugin async pour les collecter et les exécuter. Le bloc
`__main__` reste pour quand la pile de test n'est pas installée
(`python3 tests/test_chaine_deux_temps.py`).
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "89f20c83-54ec-4fd4-bf0c-1700463ff155.json"

from app.debrief import api as debrief_api
from app.debrief.report_facts import build_report_facts
from app.debrief_models import DebriefReport, DebriefReportRun, DebriefSession


class FakeAsyncSession:
    """Session factice en mémoire -- get/add/delete/commit, sans SQL, sans
    connexion réseau. Un seul store partagé pour toute la durée du test
    (comme la vraie session, ouverte une fois pour toute la tâche)."""

    def __init__(self, store: dict):
        self.store = store

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, model, pk):
        return self.store.get((model, pk))

    def add(self, obj):
        self.store[(type(obj), obj.session_id)] = obj

    async def delete(self, obj):
        self.store.pop((type(obj), obj.session_id), None)

    async def commit(self):
        pass


def _charger_fiche_francfort(session_id: uuid.UUID) -> dict:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    fiche = build_report_facts(fixture["flights"], fixture)
    fiche["mission_id"] = str(session_id)  # aligne la fiche sur la session factice
    return fiche


async def _run_chaine_traduction_echoue() -> None:
    session_id = uuid.uuid4()
    store: dict = {}
    store[(DebriefSession, session_id)] = DebriefSession(id=session_id, title="Test")
    fiche = _charger_fiche_francfort(session_id)

    publish_calls = []

    async def fake_rediger(f, langue):
        assert langue == "fr"
        return "Texte français de test.", {"verdict": "ok"}

    async def fake_traduire(texte_fr, f):
        assert texte_fr == "Texte français de test."
        return None, {"verdict": "echec_delai_depasse"}

    def fake_publish_invalidate(kind, key):
        publish_calls.append((kind, key))

    with (
        patch.object(debrief_api, "AsyncSessionLocal", lambda: FakeAsyncSession(store)),
        patch.object(debrief_api, "_build_report_facts_for_session", AsyncMock(return_value=fiche)),
        patch.object(debrief_api.llm, "rediger", fake_rediger),
        patch.object(debrief_api.llm, "traduire", fake_traduire),
        patch.object(debrief_api, "publish_invalidate", fake_publish_invalidate),
    ):
        await debrief_api._redact_report_task(session_id, auteur_id=None)

    report = store.get((DebriefReport, session_id))
    assert report is not None, "aucun DebriefReport écrit"
    assert report.texte_fr == "Texte français de test.", f"texte_fr = {report.texte_fr!r}"
    assert report.texte_en is None, f"texte_en = {report.texte_en!r} (attendu None)"
    assert len(publish_calls) >= 2, f"invalidation publiée {len(publish_calls)} fois (attendu >= 2)"
    assert all(c == ("report", str(session_id)) for c in publish_calls)
    assert (DebriefReportRun, session_id) not in store, "le verrou n'a pas été nettoyé par le finally"


def test_chaine_deux_temps() -> None:
    """Scénario central (correctif §④) : `rediger` réussit, `traduire`
    échoue -- `texte_fr` écrit, `texte_en` reste `None`, invalidation
    publiée, verrou nettoyé par le `finally`."""
    asyncio.run(_run_chaine_traduction_echoue())


async def _run_echec_francais() -> None:
    session_id = uuid.uuid4()
    store: dict = {}
    store[(DebriefSession, session_id)] = DebriefSession(id=session_id, title="Test 2")
    fiche = _charger_fiche_francfort(session_id)

    async def fake_rediger_echec(f, langue):
        return None, {"verdict": "echec_delai_depasse"}

    traduire_calls = []

    async def fake_traduire_jamais_appele(texte_fr, f):
        traduire_calls.append(texte_fr)
        return "ne devrait jamais arriver ici", {"verdict": "ok"}

    publish_calls = []

    def fake_publish_invalidate(kind, key):
        publish_calls.append((kind, key))

    with (
        patch.object(debrief_api, "AsyncSessionLocal", lambda: FakeAsyncSession(store)),
        patch.object(debrief_api, "_build_report_facts_for_session", AsyncMock(return_value=fiche)),
        patch.object(debrief_api.llm, "rediger", fake_rediger_echec),
        patch.object(debrief_api.llm, "traduire", fake_traduire_jamais_appele),
        patch.object(debrief_api, "publish_invalidate", fake_publish_invalidate),
    ):
        await debrief_api._redact_report_task(session_id, auteur_id=None)

    assert (DebriefReport, session_id) not in store, "un rapport a été écrit malgré l'échec FR"
    assert traduire_calls == [], "traduire() a été appelée alors que le français a échoué"


def test_echec_francais() -> None:
    """Second scénario, garde-fou : la rédaction française échoue --
    aucun rapport ne doit être écrit du tout, et `traduire` ne doit
    jamais être appelée (la règle de repli du Lot R2 ne disparaît pas,
    brief §2③)."""
    asyncio.run(_run_echec_francais())


if __name__ == "__main__":
    test_chaine_deux_temps()
    print("OK -- test_chaine_deux_temps")
    test_echec_francais()
    print("OK -- test_echec_francais")
