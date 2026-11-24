"""Lot « La Planification en grand écran » (`v1.0077`) -- le roster de la fiche est trié par nom affiché.

Une seule fonction de test, sans base ni réseau : `trier_roster` est une fonction pure.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.events import trier_roster


def test_roster_trie_par_nom_sans_casse_puis_par_profile_id():
    roster = {
        "present": [
            {"profile_id": "3", "name": "viper"},
            {"profile_id": "2", "name": "Ghost"},
            {"profile_id": "1", "name": "ghost"},
        ],
        "maybe": [],
        "absent": [{"profile_id": "4", "name": None}],
    }
    trie = trier_roster(roster)
    # « Ghost » et « ghost » se valent sans casse : le profile_id les départage ; « viper » vient après.
    assert [p["profile_id"] for p in trie["present"]] == ["1", "2", "3"]
    # Un état vide reste vide.
    assert trie["maybe"] == []
    # Un nom absent (None) compte comme vide et ne casse pas le tri.
    assert [p["profile_id"] for p in trie["absent"]] == ["4"]
