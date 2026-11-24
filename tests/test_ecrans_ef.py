"""Lot « Les écrans E et F » : l'activité et le bilan par escadrille, au jour
du vol (`_unites_au_jour_du_vol`, R188), et la synthèse d'un membre
(`_synthese_membre`), hors ligne -- ni base, ni réseau.

1. `test_unites_au_jour_du_vol` -- un vol compte pour l'escadrille de son
   pilote au jour du vol ; un vol d'avant l'entrée, ou de Free Agent, ne
   compte pour aucune ; le bilan additionne les sessions, fratricides à part.
2. `test_escadre_porte_les_unites` -- la charge de D porte, par escadrille,
   callsign, nom complet, activité et bilan ; nuls sans vol.
3. `test_synthese_membre` -- participation, appareils par missions, barrettes
   au rang de création, quatre dernières missions de la plus récente.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _escadre_payload, _synthese_membre, _unites_au_jour_du_vol


def _m(pid, sq, debut, fin=None):
    return NS(profile_id=pid, squadron_id=sq, started_at=datetime(*debut, tzinfo=timezone.utc),
              ended_at=datetime(*fin, tzinfo=timezone.utc) if fin else None)


def _v(pid, session, t, kills=(), coa="2", obj=None, ac="Mi-24P"):
    return NS(pilote_profile_id=pid, session_id=session, t_start=0, t_end=t, coalition=coa, object_id=obj,
              aircraft_type=ac, stats={"kills": [dict(k) for k in kills]})


APPARTENANCES = {
    1: [_m(1, 10, (2026, 7, 6))],
    2: [_m(2, 10, (2026, 7, 6))],
    3: [_m(3, 20, (2026, 9, 30))],
}
T72 = {"target_unit_type": "T-72B", "target_coalition": "1"}
BTR = {"target_unit_type": "BTR-80", "target_coalition": "1"}
AMI = {"target_unit_type": "Ural-375", "target_coalition": "2"}


def test_unites_au_jour_du_vol():
    vols = [
        (_v(1, "s1", 3600, [T72, BTR]), date(2026, 7, 6)),
        (_v(2, "s1", 1800, [AMI]), date(2026, 7, 6)),
        (_v(3, "s1", 3600, [T72]), date(2026, 7, 6)),
        (_v(None, "s1", 3600, [T72]), date(2026, 7, 6)),
        (_v(4, "s2", 3600, [T72]), date(2026, 8, 10)),
        (_v(1, "s2", 1800, [T72]), date(2026, 8, 10)),
    ]
    u = _unites_au_jour_du_vol(vols, APPARTENANCES, {})
    assert set(u) == {10}
    assert u[10]["activite"] == {"missions": 2, "heures": 1.5, "heures_jour": 1.5, "heures_nuit": 0.0, "sorties": 3, "pilotes": 2}
    assert u[10]["bilan"] == {
        "kills_by_category": [
            {"category": "Char", "display_name": "Char", "count": 2},
            {"category": "Blindé léger", "display_name": "Blindé léger", "count": 1},
        ],
        "n_kills_validated": 3,
        "n_fratricides": 1,
    }


def test_escadre_porte_les_unites():
    sqs = [NS(id=10, designation="CHARLIE-33", status="actif", aircraft=["Mi-24P"], crest_sha=None,
              callsign="Dragoon", full_name="Example Helicopter Regiment 33"),
           NS(id=20, designation="ALPHA-11", status="actif", aircraft=None, crest_sha=None,
              callsign=None, full_name=None)]
    unites = _unites_au_jour_du_vol([(_v(1, "s1", 3600, [T72]), date(2026, 7, 6))], APPARTENANCES, {})
    p = _escadre_payload(NS(designation="1st EXAW"), sqs, [], ["dcs"], {}, unites)
    charlie, sqn = p["squadrons"]
    assert (charlie["callsign"], charlie["full_name"]) == ("Dragoon", "Example Helicopter Regiment 33")
    assert charlie["activite"] == {"missions": 1, "heures": 1.0, "heures_jour": 1.0, "heures_nuit": 0.0, "sorties": 1, "pilotes": 1}
    assert charlie["bilan"]["n_kills_validated"] == 1
    assert sqn["activite"] == {"missions": 0, "heures": 0.0, "heures_jour": 0.0, "heures_nuit": 0.0, "sorties": 0, "pilotes": 0}
    assert sqn["bilan"] == {"kills_by_category": [], "n_kills_validated": 0, "n_fratricides": 0}


def _s(sid, jour, titre, camp=None, nom=None):
    return NS(id=sid, mission_date=jour, title=titre, display_name=nom, campaign_id=camp)


def test_synthese_membre():
    s1 = _s("a", date(2026, 7, 6), "m1", "C1")
    s2 = _s("b", date(2026, 7, 27), "m2", "C1", "Mission du 27/07")
    s3 = _s("c", date(2026, 8, 17), "m3", "C2", "Bataille de Francfort")
    s4 = _s("d", date(2026, 8, 20), "m4")
    s5 = _s("e", date(2026, 9, 1), "m5")
    vols = [(_v(1, "a", 3600), s1), (_v(1, "b", 1800, ac="Mi-8MTV2"), s2), (_v(1, "c", 3600), s3),
            (_v(1, "c", 1800), s3), (_v(1, "d", 900), s4), (_v(1, "e", 900), s5)]
    f = _synthese_membre(vols, {"C1": (1, "Foothold Germany"), "C2": (2, "Verrou Baltique")})
    assert f["participation"] == {"missions": 5, "heures": 3.5, "heures_jour": 3.5, "heures_nuit": 0.0, "appareils": 2, "depuis": "2026-07-06"}
    assert f["appareils"] == [{"type": "Mi-24P", "missions": 4, "heures": 3.0},
                              {"type": "Mi-8MTV2", "missions": 1, "heures": 0.5}]
    assert [(c["name"], c["rang"], c["missions"]) for c in f["campagnes"]] == [
        ("Foothold Germany", 1, 2), ("Verrou Baltique", 2, 1)]
    assert [(m["date"], m["titre"], m["campagne"]) for m in f["missions"]] == [
        ("2026-09-01", "m5", None), ("2026-08-20", "m4", None),
        ("2026-08-17", "Bataille de Francfort", "Verrou Baltique"), ("2026-07-27", "Mission du 27/07", "Foothold Germany")]
