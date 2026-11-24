"""Lot « Les quatre dernières dettes » (`v1.0046`) -- un impact vu par deux
journaux est un seul impact.

Trois invariants de `engine._merge_events`, sur des évènements fabriqués comme
dans `test_lot_fusion.py` -- ni base, ni ACMI, ni clé API :

1. `test_impact_vu_par_deux_journaux` -- deux journaux, le même `hit`, l'un
   avec l'arme `12.7mm`, l'autre sans, 0,02 s plus tard : un seul évènement,
   arme `12.7mm`, vu dans les deux journaux -- dans les deux ordres de
   journaux (l'ordre de fusion suit le `sha256`).
2. `test_meme_journal_garde_deux_impacts` -- un seul journal porte les deux
   mêmes `hit`, avec et sans arme : deux évènements (la règle du même journal,
   multi-impacts).
3. `test_deux_armes_nommees_restent_distinctes` -- deux journaux, le même `hit`
   sous deux armes nommées différentes : deux évènements.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import engine
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload

_TIREUR = "16778241"
_CIBLE = "16781569"


def _upload(sha: str) -> DebriefUpload:
    return DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log")


def _hit(index: int, t: float, weapon: str | None) -> DebriefEvent:
    return DebriefEvent(
        index=index,
        t=t,
        type="hit",
        initiator_object_id=_TIREUR,
        initiator_pilot_name=None,
        initiator_unit_type=None,
        initiator_mission_id=None,
        initiator_coalition=None,
        target_object_id=_CIBLE,
        target_pilot_name=None,
        target_unit_type=None,
        weapon=weapon,
        event_id=str(index),
        linked_event_id=None,
        target_slot=None,
        target_mission_id=None,
    )


def _log(*events: DebriefEvent) -> DebriefLogData:
    return DebriefLogData(header=DebriefHeader(), events=list(events), graveyard=[])


def _hits(pairs) -> list[engine.MergedEvent]:
    return [e for e in engine._merge_events(pairs) if e.type == "hit"]


def test_impact_vu_par_deux_journaux() -> None:
    # Dans les deux ordres : le journal qui porte l'arme passe d'abord, puis
    # en second (les journaux se fusionnent dans l'ordre de leur `sha256`).
    for sha_arme, sha_vide in (("a", "b"), ("b", "a")):
        avec_arme = (_upload(sha_arme), _log(_hit(1, 100.0, "12.7mm")))
        sans_arme = (_upload(sha_vide), _log(_hit(1, 100.02, None)))
        hits = _hits([avec_arme, sans_arme])
        assert len(hits) == 1, f"ordre {sha_arme}/{sha_vide} : {len(hits)} impacts (attendu 1)"
        (impact,) = hits
        assert impact.weapon == "12.7mm", f"ordre {sha_arme}/{sha_vide} : arme {impact.weapon!r}"
        assert impact.seen_in == ["a", "b"], f"ordre {sha_arme}/{sha_vide} : vu dans {impact.seen_in}"


def test_meme_journal_garde_deux_impacts() -> None:
    journal = (_upload("a"), _log(_hit(1, 100.0, "12.7mm"), _hit(2, 100.02, None)))
    hits = _hits([journal])
    assert len(hits) == 2, f"{len(hits)} impacts (attendu 2 : la règle du même journal)"


def test_deux_armes_nommees_restent_distinctes() -> None:
    a = (_upload("a"), _log(_hit(1, 100.0, "12.7mm")))
    b = (_upload("b"), _log(_hit(1, 100.02, "30mm HE")))
    hits = _hits([a, b])
    assert len(hits) == 2, f"{len(hits)} impacts (attendu 2 : deux armes nommées)"
    assert sorted(e.weapon for e in hits) == ["12.7mm", "30mm HE"]
