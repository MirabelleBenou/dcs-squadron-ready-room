"""Correctif R119 (brief `BRIEF_SONNET_CORRECTIF_WING_NOTE_v1`) : la note à
l'escadre est saisie, stockée, éditable -- mais `_build_report_facts_for_session`
ne la transmettait jamais à `build_report_facts` faute de clé dans le dict
`mission`. Le défaut était silencieux : `mission.get("wing_note")` valait
toujours `None`, sans qu'aucune erreur ne le signale (app/llm.py s'en passe
sans le signaler quand la note est nulle).

⛔ Un test qui passe par `build_report_facts()` directement ne prouve RIEN :
cette fonction marchait déjà, y compris quand le défaut était présent. Le
maillon manquant est le dict construit dans `api.py` -- seul un test qui
traverse `_build_report_facts_for_session` peut voir ce défaut. C'est
pourquoi ce test appelle `_build_report_facts_for_session` elle-même, pas
`build_report_facts`.

Patron repris de `tests/test_chaine_deux_temps.py` : fonctions `test_*`
synchrones, `asyncio.run` interne, `FakeAsyncSession` en mémoire -- sans
base Postgres réelle. Ici, `_build_report_facts_for_session` interroge la
base à deux endroits (les vols de la session, puis les évènements
significatifs via `_significant_object_ids`) ; on fournit donc à la fausse
session de quoi répondre à la première requête (aucun vol -- une fiche
sans vol suffit à prouver le geste, la note n'a besoin d'aucun vol pour
traverser le dict `mission`), et on substitue `_significant_object_ids`
elle-même (fonction déjà couverte ailleurs, hors sujet ici) plutôt que de
répliquer sa requête SQL.
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import api as debrief_api
from app.debrief_models import DebriefSession


class _FakeScalars:
    """Résultat minimal imitant `Result.scalars().all()` de SQLAlchemy."""

    def __init__(self, items: list):
        self._items = items

    def all(self):
        return self._items


class _FakeExecuteResult:
    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        return _FakeScalars(self._items)

    def all(self):
        # Lot « La plume » §7 -- la lecture des libellés du Centre
        # (`referentiel.lire_libelles`) lit `Result.all()` : aucun libellé.
        return []


class FakeAsyncSession:
    """Session factice en mémoire -- ne répond qu'aux requêtes que
    `_build_report_facts_for_session` exécute elle-même (la liste des
    vols, et -- Lot « La plume » -- la lecture des libellés du Centre, vide) ;
    `_significant_object_ids`, qui exécute sa propre requête, est
    substituée séparément (voir plus bas) plutôt que simulée ici."""

    def __init__(self):
        pass

    async def execute(self, stmt):
        return _FakeExecuteResult([])  # aucun vol -- non pertinent pour ce défaut


async def _construire_fiche(wing_note: str | None) -> dict:
    session = DebriefSession(
        id=uuid.uuid4(),
        title="Session de test R119",
        display_name=None,
        reference_time=None,
        wing_note=wing_note,
    )
    db = FakeAsyncSession()
    with patch.object(debrief_api, "_significant_object_ids", AsyncMock(return_value=set())):
        return await debrief_api._build_report_facts_for_session(db, session)


def test_wing_note() -> None:
    """Un seul test, trois assertions (brief §3) : la note traverse
    `_build_report_facts_for_session` jusqu'à `ouverture_cloture["wing_note"]`,
    n'apparaît nulle part ailleurs dans la fiche (en particulier pas dans
    `facts`), et une session sans note laisse le champ à `None` (jamais une
    chaîne vide -- repli 4 de `_apply_ouverture_cloture`)."""
    chaine = "NOTE-DISTINCTIVE-R119-8f3c1e"
    fiche = asyncio.run(_construire_fiche(chaine))

    assert fiche["ouverture_cloture"]["wing_note"] == chaine, (
        f"wing_note = {fiche['ouverture_cloture'].get('wing_note')!r}"
    )

    blob = json.dumps(fiche, ensure_ascii=False)
    occurrences = blob.count(chaine)
    assert occurrences == 1, (
        f"la chaîne apparaît {occurrences} fois dans la fiche (attendu 1) -- "
        "elle a dû fuiter ailleurs, notamment dans facts"
    )
    assert chaine not in json.dumps(fiche.get("facts"), ensure_ascii=False), (
        "la note à l'escadre est apparue dans `facts`"
    )

    fiche_sans_note = asyncio.run(_construire_fiche(None))
    assert fiche_sans_note["ouverture_cloture"]["wing_note"] is None, (
        f"wing_note = {fiche_sans_note['ouverture_cloture'].get('wing_note')!r} "
        "(attendu None, jamais une chaîne vide)"
    )


if __name__ == "__main__":
    test_wing_note()
    print("OK -- test_wing_note")
