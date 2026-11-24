"""Lot « Un dépôt à la fois » (`v1.0072`) -- ARC-02, ARC-05, ARC-07, ARC-23 : un
seul dépôt du Débrief se joue à la fois (verrou de module), hors de la boucle
d'évènements, avec un déposant vérifié, sans fichier orphelin ni type d'unité en
conflit ; le recalcul des périmées passe sur ses échecs.

Six tests, sans base ni réseau : doublures `SimpleNamespace`, `AsyncMock`,
`monkeypatch`.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.debrief import categorize, engine


def _fichiers(racine: Path) -> list[Path]:
    return [p for p in racine.rglob("*") if p.is_file()]


def _base_perimees(n: int):
    """Une base doublée qui liste `n` sessions périmées (empreinte ancienne)."""
    ids = [uuid.uuid4() for _ in range(n)]
    resultat = SimpleNamespace(all=lambda: [(i, "ancienne") for i in ids])
    db = SimpleNamespace(
        execute=AsyncMock(return_value=resultat),
        get=AsyncMock(return_value=object()),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )
    return db, ids


def test_deux_depots_se_suivent(monkeypatch):
    monkeypatch.setattr(engine, "_verrou_depot", asyncio.Lock())
    journal: list[str] = []

    async def faux_corps(db, **kw):
        journal.append("entree")
        await asyncio.sleep(0.01)
        journal.append("sortie")
        return {}

    monkeypatch.setattr(engine, "_ingest_file_sous_verrou", faux_corps)

    async def go():
        args = dict(kind="acmi", depositor_profile_id=None, filename="a.acmi", raw_bytes=b"x")
        await asyncio.gather(
            engine.ingest_file(None, **args), engine.ingest_file(None, **args)
        )

    asyncio.run(go())
    assert journal == ["entree", "sortie", "entree", "sortie"]


def test_perimees_sous_le_verrou(monkeypatch):
    monkeypatch.setattr(engine, "_verrou_depot", asyncio.Lock())
    db, ids = _base_perimees(3)
    vus: list[bool] = []
    journal: list[str] = []
    taches: list[asyncio.Task] = []

    async def depot():
        async with engine._verrou_depot:
            journal.append("depot")

    async def faux_recalcul(db_, sid):
        vus.append(engine._verrou_depot.locked())
        journal.append("recalcul")
        if not taches:
            # Un dépôt arrive pendant la première session : il doit passer
            # entre deux sessions (verrou relâché), pas après toute la boucle.
            taches.append(asyncio.create_task(depot()))
            await asyncio.sleep(0)

    monkeypatch.setattr(engine, "recompute_session", faux_recalcul)

    async def go():
        rendu = await engine.recompute_stale_sessions(db)
        await taches[0]
        return rendu, engine._verrou_depot.locked()

    rendu, verrou_pris = asyncio.run(go())
    assert vus == [True, True, True]
    assert verrou_pris is False
    assert rendu == (3, 0)
    assert journal == ["recalcul", "depot", "recalcul", "recalcul"]


def test_perimees_session_disparue(monkeypatch):
    monkeypatch.setattr(engine, "_verrou_depot", asyncio.Lock())
    db, ids = _base_perimees(3)
    db.get = AsyncMock(side_effect=lambda modele, sid: None if sid == ids[1] else object())
    appels = AsyncMock()
    monkeypatch.setattr(engine, "recompute_session", appels)
    avertis = MagicMock()
    monkeypatch.setattr(engine.logger, "warning", avertis)

    rendu = asyncio.run(engine.recompute_stale_sessions(db))
    assert rendu == (2, 0)
    assert appels.await_count == 2
    assert db.rollback.await_count == 0
    assert avertis.call_count == 0


def test_un_echec_n_arrete_pas_la_boucle(monkeypatch):
    monkeypatch.setattr(engine, "_verrou_depot", asyncio.Lock())
    db, ids = _base_perimees(3)
    recalculees: list[uuid.UUID] = []

    async def faux_recalcul(db_, sid):
        if sid == ids[1]:
            raise FileNotFoundError("brut absent")
        recalculees.append(sid)

    monkeypatch.setattr(engine, "recompute_session", faux_recalcul)
    rendu = asyncio.run(engine.recompute_stale_sessions(db))
    assert rendu == (2, 1)
    assert db.rollback.await_count == 1
    assert db.commit.await_count == 2
    assert recalculees == [ids[0], ids[2]]


def test_deposant_inconnu(monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "_verrou_depot", asyncio.Lock())
    monkeypatch.setattr(settings, "DEBRIEF_STORAGE_DIR", str(tmp_path))
    db = SimpleNamespace(get=AsyncMock(return_value=None))

    with pytest.raises(engine.IngestError) as exc:
        asyncio.run(
            engine.ingest_file(
                db,
                kind="debrief",
                depositor_profile_id=42,
                filename="debrief.log",
                raw_bytes=b"contenu",
            )
        )
    assert str(exc.value) == "depositor inconnu : 42"
    assert _fichiers(tmp_path) == []


def test_echec_tardif_aucun_fichier(monkeypatch, tmp_path):
    monkeypatch.setattr(engine, "_verrou_depot", asyncio.Lock())
    monkeypatch.setattr(settings, "DEBRIEF_STORAGE_DIR", str(tmp_path))
    session = SimpleNamespace(
        id=uuid.uuid4(),
        title="Mission",
        display_name=None,
        wing_note=None,
        campaign_id=None,
        reference_time=None,
        mission_date=None,
        acmi_present=False,
    )
    monkeypatch.setattr(
        engine.acmi_mod,
        "parse_acmi",
        lambda p: SimpleNamespace(
            meta=SimpleNamespace(title="Mission", recording_time=None)
        ),
    )
    monkeypatch.setattr(engine, "_resolve_session", AsyncMock(return_value=session))

    async def echec(db_, sid):
        raise RuntimeError("recalcul en échec")

    monkeypatch.setattr(engine, "recompute_session", echec)
    db = SimpleNamespace(
        get=AsyncMock(return_value=object()),
        scalar=AsyncMock(return_value=None),
        add=MagicMock(),
        flush=AsyncMock(),
        commit=AsyncMock(),
    )

    with pytest.raises(RuntimeError):
        asyncio.run(
            engine.ingest_file(
                db,
                kind="acmi",
                depositor_profile_id=None,
                filename="vol.acmi",
                raw_bytes=b"octets",
            )
        )
    assert _fichiers(tmp_path) == []


def test_types_d_unites_sans_heurt():
    notes: list = []
    lecture = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: []))

    async def execute(stmt):
        if not notes and not getattr(execute, "lu", False):
            execute.lu = True
            return lecture
        notes.append(stmt)
        return None

    db = SimpleNamespace(execute=execute, flush=AsyncMock())
    types = {"Su-27", "A-10C", "Mi-24P"}
    asyncio.run(engine._persist_unit_categories(db, types))

    assert len(notes) == 3
    compiles = [s.compile(dialect=postgresql.dialect()) for s in notes]
    assert [c.params["unit_type"] for c in compiles] == sorted(types)
    for c in compiles:
        assert "ON CONFLICT (unit_type) DO NOTHING" in str(c)
        # Les valeurs sont celles de `categorize.categorize` (A2).
        ut = c.params["unit_type"]
        assert (
            c.params["display_name"],
            c.params["category"],
            c.params["resolved_from"],
        ) == categorize.categorize(ut)
