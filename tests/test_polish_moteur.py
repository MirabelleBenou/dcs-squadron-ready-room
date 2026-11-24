"""Lot « Polish du moteur du Débrief » (v1.0039) : quatre invariants
déterministes, hors ligne, sur des évènements fabriqués -- aucun journal réel
dans l'archive, ni base, ni clé API.

1. `test_replication_confirme_humain` -- un vrai indicatif lu dans un journal,
   sans `under control` ni `PLAYER`, fait de l'objet un humain confirmé
   (règle 1).
2. `test_type_d_unite_ne_confirme_pas` -- un nom de pilote égal à un type
   d'unité (celui d'un objet de la session, ou un type connu) ne confirme
   rien (règle 1).
3. `test_alias_armes_fusionnent` -- deux journaux écrivent `L31_120mm_HESH` et
   `L31 (120mm HESH)` au même tir : ce tir ne sort qu'une fois, sous le nom
   canonique, vu par les deux (règle 2).
4. `test_lexique_dans_empreinte` -- `revision._MODULES` se termine par
   `lexique.py` (règle 3).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine, revision
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload


def _ev(index: int, t: float, type: str, *, ioid: str | None = None, ipilot: str | None = None,
        itype: str | None = None, toid: str | None = None, tpilot: str | None = None,
        ttype: str | None = None, weapon: str | None = None) -> DebriefEvent:
    return DebriefEvent(
        index=index, t=t, type=type,
        initiator_object_id=ioid, initiator_pilot_name=ipilot, initiator_unit_type=itype,
        initiator_mission_id=None, initiator_coalition=None,
        target_object_id=toid, target_pilot_name=tpilot, target_unit_type=ttype,
        weapon=weapon, event_id=str(index), linked_event_id=None,
        target_slot=None, target_mission_id=None,
    )


def _paire(sha: str, events: list[DebriefEvent]):
    upload = DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log")
    return upload, DebriefLogData(header=DebriefHeader(), events=events, graveyard=[])


def test_replication_confirme_humain() -> None:
    # Un témoin voit GRIFFON détruire un char : GRIFFON n'a déposé aucun
    # journal, n'est jamais `under control` ni `PLAYER` -- son indicatif seul.
    temoin = _paire("a", [
        _ev(1, 100.0, "kill", ioid="5001", ipilot="GRIFFON", itype="F-4E-45MC",
            toid="9001", ttype="T-72B", weapon="Mk-82"),
    ])
    humains = engine._human_object_ids([temoin])
    assert "5001" in humains
    # La cible, une IA sans indicatif, n'entre pas.
    assert "9001" not in humains


def test_type_d_unite_ne_confirme_pas() -> None:
    # 6001 porte le type « Unite-Essai » (inconnu du catalogue) ; 6002 a pour
    # nom de pilote ce même type. 6003 a pour nom de pilote un type connu.
    journal = _paire("a", [
        _ev(1, 100.0, "shot", ioid="6001", itype="Unite-Essai", weapon="Mk-82"),
        _ev(2, 110.0, "hit", ioid="6002", ipilot="Unite-Essai", toid="9002", ttype="T-72B",
            weapon="Mk-82"),
        _ev(3, 120.0, "hit", ioid="6003", ipilot="T-72B", toid="9003", ttype="BMP-2",
            weapon="Mk-82"),
    ])
    humains = engine._human_object_ids([journal])
    assert "6002" not in humains
    assert "6003" not in humains
    assert humains == set()


def test_alias_armes_fusionnent() -> None:
    ioid = "7001"
    a = _paire("a", [_ev(1, 300.0, "shot", ioid=ioid, itype="Challenger2", weapon="L31_120mm_HESH")])
    b = _paire("b", [_ev(1, 300.0, "shot", ioid=ioid, itype="Challenger2", weapon="L31 (120mm HESH)")])
    merged = engine._merge_events([a, b])
    tirs = [e for e in merged if e.type == "shot" and e.initiator_object_id == ioid]
    assert len(tirs) == 1, f"{len(tirs)} tirs (attendu 1, pas 2)"
    assert tirs[0].weapon == "L31 (120mm HESH)"
    assert set(tirs[0].seen_in) == {"a", "b"}


def test_lexique_dans_empreinte() -> None:
    assert revision._MODULES[-1] == "lexique.py"
    assert revision._MODULES == ("engine.py", "debriefer.py", "acmi.py", "categorize.py", "lexique.py")
