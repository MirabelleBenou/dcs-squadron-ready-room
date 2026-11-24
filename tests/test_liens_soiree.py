"""Lot « Les liens de la soirée » (v1.0107, rr-debrief-liens-temps-reel) : les adresses que Discord écrit,
le jour d'une session à l'heure de Paris, et la route qui rend la soirée d'un jour.

Cinq tests, sans base de données : les constructeurs de messages sont des fonctions pures ;
la route est appelée directement avec un double de la base (patron de `tests/test_wing_note.py` :
fonctions synchrones, `asyncio.run`, `_significant_object_ids_par_session` substituée plutôt que
sa requête répliquée).
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import discord_notify, discord_rsvp
from app.debrief import api as debrief_api
from app.debrief_models import DebriefFlight, DebriefSession
from app.recurrence import Occurrence

_BASE = "https://rr.example.org"


def _occurrence(event_id: str) -> Occurrence:
    return Occurrence(
        event_id=event_id,
        occ_date=date(2026, 9, 20),
        start_at_utc=datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc),
        type="mission",
        game_label="DCS",
        map_name="Caucase",
        title="Mission Francfort",
        description="",
        duration_min=120,
        recurring=False,
        is_override=False,
        created_by="1",
    )


def _utc(texte: str) -> datetime:
    return datetime.fromisoformat(texte.replace("Z", "+00:00"))


def test_bouton_portail_ouvre_la_fiche_de_l_occurrence() -> None:
    """Le bouton « Portail » d'une occurrence ouvre sa fiche ; une barre oblique finale de `BASE_URL`
    ne double pas la barre de l'adresse."""
    event_id = str(uuid.uuid4())
    attendu = f"{_BASE}/#planif/evenement/{event_id}/2026-09-20"
    for base in (_BASE, _BASE + "/"):
        with patch.object(discord_rsvp.settings, "BASE_URL", base):
            payload = discord_rsvp.build_occurrence_payload(_occurrence(event_id), {})
        bouton = payload["components"][0]["components"][-1]
        assert bouton["style"] == 5 and bouton["label"] == "Portail", bouton
        assert bouton["url"] == attendu, f"BASE_URL={base!r} -> {bouton['url']!r}"


def test_bouton_du_resume_hebdo_ouvre_le_tableau_hebdo() -> None:
    """Le bouton du résumé de la semaine ouvre le Tableau hebdo, avec ou sans barre oblique finale."""
    occ = _occurrence(str(uuid.uuid4()))
    for base in (_BASE, _BASE + "/"):
        payload = discord_notify.build_webhook_payload([(occ, 0, {})], [], base, "fr", "Ready Room")
        bouton = payload["components"][0]["components"][0]
        assert bouton["url"] == f"{_BASE}/#planif/hebdo", f"base={base!r} -> {bouton['url']!r}"


def test_jour_de_soiree_a_l_heure_de_paris() -> None:
    """Le jour d'une session est celui de `reference_time` à Paris : minuit passé à Paris, le lendemain ;
    la veille au soir en UTC, déjà le jour même à Paris (été : UTC+2)."""
    assert debrief_api.jour_de_soiree(_utc("2026-09-20T21:30Z"), None) == date(2026, 9, 20)
    assert debrief_api.jour_de_soiree(_utc("2026-09-20T22:30Z"), None) == date(2026, 9, 21)
    assert debrief_api.jour_de_soiree(_utc("2026-09-19T22:30Z"), None) == date(2026, 9, 20)


def test_jour_de_soiree_sans_heure() -> None:
    """Sans `reference_time`, `mission_date` ; sans l'un ni l'autre, `None`. L'heure prime sur la date."""
    assert debrief_api.jour_de_soiree(None, date(2026, 9, 20)) == date(2026, 9, 20)
    assert debrief_api.jour_de_soiree(None, None) is None
    assert debrief_api.jour_de_soiree(_utc("2026-09-20T22:30Z"), date(2026, 9, 20)) == date(2026, 9, 21)


class _Resultat:
    """Résultat minimal imitant `Result.scalars().all()` de SQLAlchemy."""

    def __init__(self, items: list):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return self._items


class _BaseDouble:
    """Réponses dans l'ordre des lectures de la route : les sessions candidates, puis les vols."""

    def __init__(self, *reponses: list):
        self._reponses = list(reponses)
        self.requetes = 0

    async def execute(self, stmt):
        self.requetes += 1
        return _Resultat(self._reponses.pop(0))


def test_route_soiree_filtre_trie_et_porte_quatre_cles() -> None:
    """La route, appelée directement : parmi cinq candidates — dont celle de `2026-09-20T22:30Z`, déjà le 21 à Paris —,
    les quatre du 20, dans l'ordre de la règle : `reference_time` croissant (celle du `2026-09-19T22:30Z`, le 20 à Paris,
    avant celle du `2026-09-20T21:30Z`), puis les deux sans heure, à la fin, par `created_at` ; quatre clés chacune ;
    les vols comptés sont les vols significatifs. Les candidates arrivent dans le désordre."""
    def session(ref: str | None, mission_date: date | None, titre: str, duree: int, cree: str) -> DebriefSession:
        return DebriefSession(
            id=uuid.uuid4(),
            title=titre,
            display_name=titre,
            reference_time=_utc(ref) if ref else None,
            mission_date=mission_date,
            duration_s=duree,
            created_at=_utc(cree),
        )

    sans_heure_tard = session(None, date(2026, 9, 20), "Sans heure, tard", 600, "2026-09-21T10:00Z")
    sans_heure_tot = session(None, date(2026, 9, 20), "Sans heure, tôt", 650, "2026-09-21T08:00Z")
    minuit_passe = session("2026-09-20T22:30Z", None, "Minuit passé", 700, "2026-09-21T07:00Z")
    du_soir = session("2026-09-20T21:30Z", None, "Du soir", 5298, "2026-09-21T09:00Z")
    la_veille = session("2026-09-19T22:30Z", None, "La veille UTC", 4200, "2026-09-21T11:00Z")
    vols = [
        DebriefFlight(session_id=du_soir.id, object_id="a"),
        DebriefFlight(session_id=du_soir.id, object_id="b"),   # mécanique : non significatif
        DebriefFlight(session_id=sans_heure_tard.id, object_id="c"),
        DebriefFlight(session_id=sans_heure_tard.id, object_id="d"),
        DebriefFlight(session_id=sans_heure_tard.id, object_id=None),   # sans object_id : écarté
    ]
    significatifs = {du_soir.id: {"a"}, sans_heure_tard.id: {"c", "d"}}
    candidates = [sans_heure_tard, du_soir, minuit_passe, sans_heure_tot, la_veille]
    db = _BaseDouble(candidates, vols)

    with patch.object(debrief_api, "_significant_object_ids_par_session", AsyncMock(return_value=significatifs)):
        rep = asyncio.run(debrief_api.soiree_du_jour(jour=date(2026, 9, 20), user={}, db=db))

    assert rep["jour"] == "2026-09-20", rep["jour"]
    assert [s["display_title"] for s in rep["sessions"]] == [
        "La veille UTC", "Du soir", "Sans heure, tôt", "Sans heure, tard",
    ], [s["display_title"] for s in rep["sessions"]]
    for s in rep["sessions"]:
        assert sorted(s) == ["display_title", "duration_s", "id", "n_flights"], sorted(s)
    assert [(s["id"], s["duration_s"], s["n_flights"]) for s in rep["sessions"]] == [
        (str(la_veille.id), 4200, 0),
        (str(du_soir.id), 5298, 1),
        (str(sans_heure_tot.id), 650, 0),
        (str(sans_heure_tard.id), 600, 2),
    ]
