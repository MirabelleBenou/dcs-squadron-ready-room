"""Brief SONNET Lot « L'écran D » : l'assemblage de l'escadre
(`_escadre_payload`, app/debrief/api.py), hors ligne -- pas de base.
Profils, escadrilles et escadre sont des objets minimaux portant les
attributs lus.

1. `test_escadrilles_et_rangs` -- les escadrilles actives d'abord, puis en
   sommeil, chacune par id ; dans une escadrille, le chef, l'adjoint, puis
   les pilotes par nom sans tenir compte de la casse ; appareils rendus en
   liste, vide si rien n'est déclaré.
2. `test_free_agents` -- un profil sans appartenance ouverte, ou rattaché à
   une escadrille en sommeil, est un Free Agent ; rangés par nom ; les
   identifiants Discord rendus en chaînes.
3. `test_escadre_et_activite` -- désignation de l'escadre (None sans
   escadre), simulateurs et activité rendus tels quels.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief.api import _escadre_payload

ESCADRILLES = [
    NS(id=3, designation="ALPHA-11", status="actif", aircraft=None, crest_sha="c3", callsign="Mamba", full_name=None),
    NS(id=4, designation="ALPHA-21", status="sommeil", aircraft=["F-16C"], crest_sha=None, callsign=None, full_name=None),
    NS(id=1, designation="CHARLIE-33", status="actif", aircraft=["Mi-24P", "Mi-8"], crest_sha="c1",
       callsign="Dragoon", full_name="Example Helicopter Regiment 33"),
]


def profil(pid: int, nom: str) -> NS:
    return NS(id=pid, global_name=nom, username=nom.lower(), avatar_hash=None, cartes_dcs=None)


LIGNES = [
    (profil(11, "thorn"), 1, "member"),
    (profil(12, "сова5"), 1, "leader"),
    (profil(13, "DawNFyX"), 1, "member"),
    (profil(14, "Lace"), 1, "deputy"),
    (profil(21, "Golem"), 3, "leader"),
    (profil(31, "Kraken"), None, None),
    (profil(32, "ancien"), 4, "member"),
    (profil(8000000000000000001, "Big snowflake"), None, None),
]


def test_escadrilles_et_rangs() -> None:
    p = _escadre_payload(NS(designation="1st EXAW"), ESCADRILLES, LIGNES, ["dcs"], {})
    assert [s["designation"] for s in p["squadrons"]] == ["CHARLIE-33", "ALPHA-11", "ALPHA-21"]
    assert all("tag" not in s for s in p["squadrons"])
    charlie = p["squadrons"][0]
    assert [(m["name"], m["role"]) for m in charlie["members"]] == [
        ("сова5", "leader"), ("Lace", "deputy"), ("DawNFyX", "member"), ("thorn", "member"),
    ]
    assert charlie["aircraft"] == ["Mi-24P", "Mi-8"]
    assert p["squadrons"][1]["aircraft"] == []
    assert p["squadrons"][2]["members"] == []


def test_free_agents() -> None:
    p = _escadre_payload(NS(designation="1st EXAW"), ESCADRILLES, LIGNES, ["dcs"], {})
    assert [m["name"] for m in p["free_agents"]] == ["ancien", "Big snowflake", "Kraken"]
    assert "8000000000000000001" in {m["id"] for m in p["free_agents"]}
    assert all(isinstance(m["id"], str) for m in p["free_agents"])


def test_escadre_et_activite() -> None:
    activite = {"hours": 52, "missions": 7, "campaigns": 1}
    p = _escadre_payload(NS(designation="1st EXAW"), ESCADRILLES, LIGNES, ["dcs"], activite)
    assert p["wing"] == {"designation": "1st EXAW"} and p["sims"] == ["dcs"] and p["activity"] == activite
    assert _escadre_payload(None, [], [], [], {})["wing"] == {"designation": None}
