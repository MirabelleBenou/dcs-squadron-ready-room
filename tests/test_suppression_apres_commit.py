"""Lot « Le Débrief : quatre défauts » (v1.0055, R5/R6) : `_supprimer_session`
n'efface plus le dossier de stockage -- elle rend son chemin, et l'appelant
l'efface après son `commit`. Un invariant déterministe, hors ligne : une fausse
session asynchrone (ni PostgreSQL, ni réseau) et un dossier temporaire.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import api, engine


class _FausseBase:
    """Note les appels ; ne touche à rien."""

    def __init__(self) -> None:
        self.appels: list[str] = []

    async def execute(self, *_args, **_kwargs):
        self.appels.append("execute")

    async def delete(self, *_args, **_kwargs):
        self.appels.append("delete")

    async def flush(self, *_args, **_kwargs):
        self.appels.append("flush")


def test_supprimer_session_rend_le_dossier_sans_l_effacer(tmp_path, monkeypatch):
    sid = uuid.uuid4()
    dossier = tmp_path / str(sid)
    dossier.mkdir()
    (dossier / "brut.acmi").write_text("x", encoding="utf-8")
    monkeypatch.setattr(engine, "_storage_dir", lambda: tmp_path)

    db = _FausseBase()
    rendu = asyncio.run(api._supprimer_session(db, SimpleNamespace(id=sid)))

    assert db.appels[-2:] == ["delete", "flush"]
    assert dossier.exists()
    assert (dossier / "brut.acmi").exists()
    assert rendu == dossier
