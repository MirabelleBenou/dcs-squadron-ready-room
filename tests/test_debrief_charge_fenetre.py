"""Lot « La liste des missions par année » (`rr-v1.1.0+1`), hors ligne -- ni base, ni réseau : les routes sont appelées
avec une base factice qui répond à partir de tables en mémoire (même patron que `test_debrief_liste_groupee.py`).

1. `test_liste_annee_par_defaut` -- sans paramètre : l'année la plus récente qui a une session datée, et les sessions
   sans date ; la réponse porte `annee` ;
2. `test_liste_annee_explicite_et_tout` -- `annee=AAAA`, `annee=tout`, et l'intervalle `du`/`au` ;
3. `test_liste_parametres_invalides_422` -- une valeur invalide, `du` sans `au`, `annee` avec `du`/`au` ;
4. `test_periodes` -- `GET /sessions/periodes` : années, simulateurs, escadrilles (celles de la liste), sans date ;
5. `test_carnet_resume` -- `_carnet_resume` : 20 lignes au plus et `carnet_total`, le reste du dossier intact ;
6. `test_carnet_entier_nature_invalide_422` -- `GET /dossier/carnet` : la nature, le carnet entier, le 422.

La base factice ne sait pas lire du SQL : elle évalue la clause `WHERE` de la requête des sessions sur ses lignes
(`_evalue`, logique à trois valeurs comme SQL), de sorte que le filtre testé est celui que PostgreSQL recevra. Le
compte des requêtes réelles est mesuré à part, au banc à 100 sessions."""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
from fastapi import HTTPException
from sqlalchemy.sql import operators as op
from sqlalchemy.sql.elements import BindParameter, BooleanClauseList, Extract, Grouping, Null
from sqlalchemy.sql.selectable import ScalarSelect

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import api
from app.debrief.api import _carnet_resume, get_dossier_carnet, list_periodes, list_sessions


def _session(titre, jour=None, sim="dcs"):
    return NS(
        id=uuid.uuid4(), title=titre, display_name=None, mission_date=jour,
        acmi_present=False, sim=sim, duration_s=None, campaign_id=None,
        nature="mission", stats_engine_rev=None,
    )


def _vol(session_id, object_id, pid=None):
    return NS(
        id=uuid.uuid4(), session_id=session_id, object_id=object_id,
        pilote_profile_id=pid, pilot_callsign=None, identity_state="anonyme", stats={"kills": []},
    )


class _Resultat:
    def __init__(self, lignes):
        self._lignes = lignes

    def all(self):
        return list(self._lignes)

    def scalars(self):
        return NS(all=lambda: list(self._lignes))


def _evalue(e, ligne, toutes):
    """Évalue un morceau de clause SQL sur une session : les seuls éléments que posent `_clause_periode` (comparaisons,
    `IS NULL`, `EXTRACT(year …)`, le plus récent `max(mission_date)`, `AND`, `OR`). `None` = inconnu, comme SQL."""
    if isinstance(e, BindParameter):
        return e.value
    if isinstance(e, Null):
        return None
    if isinstance(e, Grouping):
        return _evalue(e.element, ligne, toutes)
    if isinstance(e, Extract):
        v = _evalue(e.expr, ligne, toutes)
        return None if v is None else v.year
    if isinstance(e, ScalarSelect):  # (SELECT max(mission_date) FROM debrief_session)
        dates = [s.mission_date for s in toutes if s.mission_date]
        return max(dates) if dates else None
    if isinstance(e, BooleanClauseList):
        vals = [_evalue(c, ligne, toutes) for c in e.clauses]
        if e.operator is op.and_:
            return False if any(v is False for v in vals) else (None if any(v is None for v in vals) else True)
        return True if any(v is True for v in vals) else (None if any(v is None for v in vals) else False)
    if hasattr(e, "operator"):
        gauche, droite = _evalue(e.left, ligne, toutes), _evalue(e.right, ligne, toutes)
        if e.operator is op.is_:
            return gauche is None and droite is None
        if gauche is None or droite is None:
            return None
        return {op.ge: gauche >= droite, op.le: gauche <= droite, op.lt: gauche < droite, op.eq: gauche == droite}[e.operator]
    return getattr(ligne, e.name)  # une colonne : `mission_date`


class _FauxDb:
    """Répond selon la table que nomme la requête ; compte chaque `execute`. `periodes` : la requête des années,
    des simulateurs ; `escadrilles` : les vols, évènements et profils, lus comme la liste les lit."""

    def __init__(self, sessions, vols=(), evenements=(), profils=()):
        self.sessions, self.vols, self.evenements, self.profils = list(sessions), list(vols), list(evenements), list(profils)
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
        if "GROUP BY" in sql and "FROM debrief_session" in sql:  # les années et leur compte
            comptes: dict = {}
            for s in self.sessions:
                cle = Decimal(s.mission_date.year) if s.mission_date else None
                comptes[cle] = comptes.get(cle, 0) + 1
            return _Resultat(list(comptes.items()))
        if "DISTINCT" in sql and "FROM debrief_session" in sql:  # les simulateurs
            return _Resultat([(sim,) for sim in {s.sim for s in self.sessions}])
        if "FROM debrief_session" in sql:  # la liste, filtrée par la clause de la requête
            clause = requete.whereclause
            gardees = self.sessions if clause is None else [
                s for s in self.sessions if _evalue(clause, s, self.sessions) is True
            ]
            return _Resultat(gardees)
        if "FROM debrief_upload" in sql:
            return _Resultat([])  # ni dépôts comptés, ni « À vérifier »
        if "FROM debrief_flight" in sql:
            ids = self._ids(requete)
            retenus = [v for v in self.vols if not ids or v.session_id in ids]
            if "debrief_flight.stats" in sql:  # l'entité entière (la liste)
                return _Resultat(retenus)
            return _Resultat([NS(session_id=v.session_id, object_id=v.object_id, pilote_profile_id=v.pilote_profile_id)
                              for v in retenus if v.pilote_profile_id is not None])  # trois colonnes (les périodes)
        if "FROM debrief_event" in sql:
            ids = {i for i in self._ids(requete) if isinstance(i, uuid.UUID)}
            return _Resultat([e for e in self.evenements if not ids or e[0] in ids])
        if "FROM profiles" in sql:
            ids = self._ids(requete)
            lignes = [p for p in self.profils if p[0] in ids]
            return _Resultat(lignes if "global_name" in sql else [(p[0], p[1]) for p in lignes])
        if "FROM campaign" in sql:
            return _Resultat([])
        raise AssertionError(f"requête inattendue : {sql}")


def _lister(db, **params):
    return asyncio.run(list_sessions(user={}, db=db, **params))


def _titres(reponse):
    return {s["display_title"] for s in reponse["sessions"]}


def _monde():
    """Deux sessions de 2026, une de 2025, une sans date."""
    return _FauxDb([
        _session("Mission A", date(2026, 3, 1)),
        _session("Mission D", date(2026, 1, 10)),
        _session("Mission B", date(2025, 6, 1)),
        _session("Mission C"),
    ])


def test_liste_annee_par_defaut():
    reponse = _lister(_monde())
    assert reponse["annee"] == "2026"
    assert _titres(reponse) == {"Mission A", "Mission D", "Mission C"}
    # La réponse gagne `annee` et rien d'autre ; la forme de chaque session ne change pas : ses clés d'avant, rien de plus.
    assert set(reponse) == {"annee", "sessions"}
    assert set(reponse["sessions"][0]) == {
        "id", "title", "display_title", "mission_date", "acmi_present", "sim", "n_uploads", "n_flights", "n_kills", "duration_s",
        "doc_ratio", "n_pilots", "squadrons", "n_named", "n_anon", "named_sample", "campaign", "nature", "stats_stale", "a_verifier",
    }
    # Sans aucune session datée : les seules sessions sans date, `annee` nulle ; sans aucune session : rien.
    seules = _lister(_FauxDb([_session("Mission C")]))
    assert seules["annee"] is None and _titres(seules) == {"Mission C"}
    vide = _lister(_FauxDb([]))
    assert vide["annee"] is None and vide["sessions"] == []


def test_liste_annee_explicite_et_tout():
    db = _monde()
    # Une année plus ancienne : ses seules sessions, sans celle qui n'a pas de date.
    ancienne = _lister(db, annee="2025")
    assert ancienne["annee"] == "2025" and _titres(ancienne) == {"Mission B"}
    # L'année la plus récente, demandée explicitement, garde les sessions sans date.
    recente = _lister(db, annee="2026")
    assert recente["annee"] == "2026" and _titres(recente) == {"Mission A", "Mission D", "Mission C"}
    # Une année sans session : rien (pas même la session sans date).
    assert _lister(db, annee="2024") == {"annee": "2024", "sessions": []}
    # Tout : la réponse d'avant.
    tout = _lister(db, annee="tout")
    assert tout["annee"] == "tout" and _titres(tout) == {"Mission A", "Mission D", "Mission B", "Mission C"}
    # Un intervalle, bornes comprises, sans les sessions sans date ; aucune année servie.
    intervalle = _lister(db, du="2026-01-10", au="2026-03-01")
    assert intervalle["annee"] is None and _titres(intervalle) == {"Mission A", "Mission D"}
    assert _titres(_lister(db, du="2026-01-11", au="2026-02-28")) == set()


def test_liste_parametres_invalides_422():
    db = _monde()
    invalides = [
        {"annee": "26"}, {"annee": "20266"}, {"annee": "deux"}, {"annee": "2026a"},
        {"du": "2026-01-01"}, {"au": "2026-01-31"},
        {"annee": "2026", "du": "2026-01-01", "au": "2026-01-31"}, {"annee": "tout", "du": "2026-01-01", "au": "2026-01-31"},
        {"du": "2026-13-01", "au": "2026-01-31"}, {"du": "2026-01-01", "au": "2026-02-30"},
        {"du": "20260101", "au": "2026-01-31"}, {"du": "2026-1-1", "au": "2026-01-31"},
    ]
    for params in invalides:
        with pytest.raises(HTTPException) as erreur:
            _lister(db, **params)
        assert erreur.value.status_code == 422, params
    assert db.requetes == 0  # refusées avant toute requête


def test_periodes():
    s26a, s26b, s26c = _session("a", date(2026, 3, 1)), _session("b", date(2026, 1, 10), "bms"), _session("c", date(2026, 2, 2))
    s25a, s25b = _session("d", date(2025, 6, 1)), _session("e", date(2025, 7, 1))
    s24, sans1, sans2 = _session("f", date(2024, 12, 31)), _session("g"), _session("h")
    vols = [
        _vol(s26a.id, 1, pid=7), _vol(s26a.id, 2, pid=8), _vol(s25a.id, 1, pid=9), _vol(s24.id, 1, pid=10),
        _vol(s26b.id, 5, pid=11),   # un vol vide (aucun évènement significatif) : son escadrille ne compte pas
        _vol(sans1.id, 1, pid=12),  # pilote sans escadrille : rien
    ]
    evenements = [(s26a.id, 1, 99), (s26a.id, 2, None), (s25a.id, None, 1), (s24.id, 1, None), (sans1.id, 1, None)]
    profils = [(7, "CHARLIE-33", "Wren", "wren"), (8, "ALPHA-11", "Fog", "fog"), (9, "ALPHA-11", "Ghost", "ghost"),
               (10, "BRAVO-22", "Viper", "viper"), (11, "ZULU-99", "Vide", "vide"), (12, None, "Sans", "sans")]
    monde = [s26a, s26b, s26c, s25a, s25b, s24, sans1, sans2]
    db = _FauxDb(monde, vols, evenements, profils)
    periodes = asyncio.run(list_periodes(user={}, db=db))
    assert list(periodes) == ["annees", "sims", "escadrilles", "sans_date"]
    assert periodes["annees"] == [{"annee": "2026", "n": 3}, {"annee": "2025", "n": 2}, {"annee": "2024", "n": 1}]
    assert periodes["sims"] == ["bms", "dcs"]
    assert periodes["escadrilles"] == ["ALPHA-11", "BRAVO-22", "CHARLIE-33"]
    assert periodes["sans_date"] == 2
    # Les escadrilles sont celles que la liste résout (la même fonction) : l'union des `squadrons` de toutes ses sessions.
    liste = _lister(_FauxDb(monde, vols, evenements, profils), annee="tout")
    assert sorted({sq for s in liste["sessions"] for sq in s["squadrons"]}) == periodes["escadrilles"]
    # Un nombre fixe de requêtes, quel que soit le nombre de sessions.
    # (Le monde de la seconde mesure porte, lui aussi, des vols et des évènements significatifs par session : une
    # boucle de requêtes par session ferait échouer l'égalité.)
    en_plus = [_session(f"x{i}", date(2023, 1, 1 + i)) for i in range(5)]
    vols_plus = vols + [_vol(x.id, 1, pid=7 + i % 3) for i, x in enumerate(en_plus)]
    evenements_plus = evenements + [(x.id, 1, 99) for x in en_plus]
    plus = _FauxDb(monde + en_plus, vols_plus, evenements_plus, profils)
    resultat_plus = asyncio.run(list_periodes(user={}, db=plus))
    assert resultat_plus["escadrilles"] == ["ALPHA-11", "BRAVO-22", "CHARLIE-33"] and resultat_plus["annees"][-1] == {"annee": "2023", "n": 5}
    assert plus.requetes == db.requetes


def _ligne(i):
    return {"session_id": f"s{i}", "flight_id": f"v{i}", "date": "2026-01-01", "titre": f"Mission {i}", "stats": {"landings": 1}}


def test_carnet_resume():
    dossier = {
        "vols": 25, "victoires": {"air": 3, "sol": 4}, "menaces": [{"type": "SA-6"}],
        "carnet": [_ligne(i) for i in range(25)],
        "par_nature": {
            "mission": {"vols": 15, "bilan": {"n": 1}, "carnet": [_ligne(i) for i in range(15)]},
            "training": {"vols": 10, "bilan": {"n": 2}, "carnet": [_ligne(i) for i in range(10)]},
        },
    }
    avant = {"carnet": list(dossier["carnet"]), "mission": list(dossier["par_nature"]["mission"]["carnet"])}
    resume = _carnet_resume(dossier)
    assert [len(resume["carnet"]), len(resume["par_nature"]["mission"]["carnet"]), len(resume["par_nature"]["training"]["carnet"])] == [20, 15, 10]
    assert [resume["carnet_total"], resume["par_nature"]["mission"]["carnet_total"], resume["par_nature"]["training"]["carnet_total"]] == [25, 15, 10]
    # Les premières lignes, dans l'ordre d'avant (le plus récent d'abord).
    assert resume["carnet"] == avant["carnet"][:20]
    assert resume["par_nature"]["mission"]["carnet"] == avant["mission"]
    # Le reste du dossier est intact, et le dossier donné n'est pas abîmé.
    for cle in ("vols", "victoires", "menaces"):
        assert resume[cle] == dossier[cle]
    assert resume["par_nature"]["mission"]["bilan"] == {"n": 1} and resume["par_nature"]["training"]["vols"] == 10
    assert len(dossier["carnet"]) == 25 and "carnet_total" not in dossier
    # Un carnet plus court que la coupe, ou une autre coupe.
    assert _carnet_resume({"carnet": [_ligne(0)]}) == {"carnet": [_ligne(0)], "carnet_total": 1}
    assert len(_carnet_resume(dossier, n=5)["carnet"]) == 5


def test_carnet_entier_nature_invalide_422(monkeypatch):
    dossier = {
        "carnet": [_ligne(i) for i in range(25)],
        "par_nature": {"mission": {"carnet": [_ligne(i) for i in range(15)]}, "training": {"carnet": [_ligne(i) for i in range(10)]}},
    }

    async def entier(user, db):
        assert user == {"id": "100000000000000003"}  # la route ne lit que le compte connecté
        return {"id": 3, "dossier": dossier}

    monkeypatch.setattr(api, "_dossier_entier", entier)
    user = {"id": "100000000000000003"}
    with pytest.raises(HTTPException) as erreur:
        asyncio.run(get_dossier_carnet(nature="autre", user=user, db=None))
    assert erreur.value.status_code == 422
    # Les trois natures rendent leur carnet entier, par défaut `tout`.
    assert [len(asyncio.run(get_dossier_carnet(nature=n, user=user, db=None))["carnet"]) for n in ("tout", "mission", "training")] == [25, 15, 10]
    assert asyncio.run(get_dossier_carnet(user=user, db=None)) == {"carnet": dossier["carnet"]}
