"""Lot « La liste des missions en requêtes groupées » (v1.0090), hors ligne --
ni base, ni réseau : `list_sessions` est appelée avec une base factice qui
compte ses `execute` et répond à partir de tables en mémoire.

1. `test_liste_requetes_independantes_du_nombre_de_sessions` -- le nombre de
   requêtes de `GET /api/debrief/sessions` est le même pour 1 et pour 3
   sessions : le compte des dépôts, les vols et les objets significatifs se
   lisent en une requête chacun pour toute la liste ;
2. `test_liste_valeurs_par_session` -- deux sessions qui diffèrent par le
   nombre de dépôts et de vols significatifs gardent chacune les leurs
   (`n_uploads`, `n_flights`, `n_kills`).

Le compte en requêtes réelles (évènement `before_cursor_execute`, sur
PostgreSQL) est mesuré à part, par l'instrument du lot (`liste_missions.py`).
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import list_sessions


def _session(titre):
    return NS(
        id=uuid.uuid4(), title=titre, display_name=None, mission_date=None,
        acmi_present=False, sim="dcs", duration_s=None, campaign_id=None,
        nature="mission", stats_engine_rev=None,
    )


def _vol(session_id, object_id, kills=0, pid=None, callsign=None):
    return NS(
        id=uuid.uuid4(), session_id=session_id, object_id=object_id,
        pilote_profile_id=pid, pilot_callsign=callsign,
        identity_state="nomme" if callsign else "anonyme",
        stats={"kills": [{}] * kills},
    )


class _Resultat:
    def __init__(self, lignes):
        self._lignes = lignes

    def all(self):
        return list(self._lignes)

    def scalars(self):
        return NS(all=lambda: [ligne for ligne in self._lignes])


class _FauxDb:
    """Répond selon la table que nomme la requête ; compte chaque `execute`."""

    def __init__(self, sessions, depots, vols, evenements, profils=()):
        self.sessions, self.depots, self.vols = sessions, depots, vols
        self.evenements, self.profils = evenements, profils
        self.requetes = 0

    @staticmethod
    def _ids(requete):
        ids = set()
        for valeur in requete.compile().params.values():
            if isinstance(valeur, (list, tuple, set)):
                ids.update(valeur)
        return ids

    async def execute(self, requete):
        self.requetes += 1
        sql = str(requete)
        if "FROM debrief_session" in sql:
            return _Resultat(self.sessions)
        if "FROM debrief_upload" in sql and "count(" in sql:
            ids = self._ids(requete)
            comptes: dict = {}
            for sid in self.depots:
                if sid in ids:
                    comptes[sid] = comptes.get(sid, 0) + 1
            return _Resultat(list(comptes.items()))
        if "FROM debrief_upload" in sql:  # `_sessions_a_verifier`
            return _Resultat([])
        if "FROM debrief_flight" in sql:
            ids = self._ids(requete)
            return _Resultat([v for v in self.vols if v.session_id in ids])
        if "FROM debrief_event" in sql:
            ids = self._ids(requete)
            return _Resultat([e for e in self.evenements if e[0] in ids])
        if "FROM profiles" in sql:
            return _Resultat(list(self.profils))
        if "FROM campaign" in sql:
            return _Resultat([])
        raise AssertionError(f"requête inattendue : {sql}")


def _lister(db):
    return asyncio.run(list_sessions(user={}, db=db))["sessions"]


def _monde(n_sessions):
    """`n_sessions` sessions, chacune avec un dépôt, deux vols (l'un porteur
    d'un évènement significatif, l'autre vide) et un pilote rattaché."""
    sessions = [_session(f"Mission {i}") for i in range(n_sessions)]
    depots, vols, evenements = [], [], []
    for s in sessions:
        depots.append(s.id)
        vols.append(_vol(s.id, 1, kills=1, pid=7, callsign="CHARLIE-33 | Wren"))
        vols.append(_vol(s.id, 2))
        evenements.append((s.id, 1, 99))
    return _FauxDb(sessions, depots, vols, evenements, profils=[(7, "CHARLIE-33", "Wren", "wren")])


def test_liste_requetes_independantes_du_nombre_de_sessions():
    une, trois = _monde(1), _monde(3)
    assert len(_lister(une)) == 1 and len(_lister(trois)) == 3
    assert une.requetes == trois.requetes
    # Sans aucune session : la lecture des sessions, et rien d'autre.
    assert _lister(vide := _monde(0)) == [] and vide.requetes == 2


def test_liste_valeurs_par_session():
    a, b = _session("Mission A"), _session("Mission B")
    db = _FauxDb(
        [a, b],
        depots=[a.id, b.id, b.id, b.id],
        vols=[
            _vol(a.id, 1, kills=2), _vol(a.id, 2),
            _vol(b.id, 1, kills=1), _vol(b.id, 2, kills=3), _vol(b.id, 3), _vol(b.id, 4),
        ],
        evenements=[(a.id, 1, None), (b.id, 1, 2), (b.id, 3, None)],
    )
    par_id = {s["id"]: s for s in _lister(db)}
    sa, sb = par_id[str(a.id)], par_id[str(b.id)]
    assert (sa["n_uploads"], sa["n_flights"], sa["n_kills"]) == (1, 1, 2)
    assert (sb["n_uploads"], sb["n_flights"], sb["n_kills"]) == (3, 3, 4)
