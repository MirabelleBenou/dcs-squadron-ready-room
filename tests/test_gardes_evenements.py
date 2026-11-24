"""Lot « La série juste » (v1.0104, ARC-20) : les droits de créer et de modifier un évènement, tels qu'ils sont.
Sans base, sans réseau : les lectures de la base sont remplacées par des doublures."""
import asyncio

from app import capabilities as cap
from app.config import settings


def _poser(monkeypatch, demandees, *, base, capacite_role=False, capacite_compte=False, admins=""):
    async def base_fait_autorite(db):
        return base

    async def a_la_capacite(db, roles, capacite):
        demandees.append(capacite)
        return capacite_role

    async def compte_a_la_capacite(db, profile_id, capacite):
        demandees.append(capacite)
        return capacite_compte

    monkeypatch.setattr(cap, "_event_create_base_authoritative", base_fait_autorite)
    monkeypatch.setattr(cap, "has_capability", a_la_capacite)
    monkeypatch.setattr(cap, "has_account_capability", compte_a_la_capacite)
    monkeypatch.setattr(settings, "ADMIN_IDS", admins)


def test_creer(monkeypatch):
    membre = {"id": "42", "roles": ["r1"]}
    # (réglages, attendu) : une table de cas.
    cas = [
        # administrateur : toujours, même quand la base fait autorité sans lui
        (dict(base=True, admins="42"), True),
        # la base fait autorité : la capacité du rôle, ou celle du compte, ouvre ; sinon fermé…
        (dict(base=True, capacite_role=True), True),
        (dict(base=True, capacite_compte=True), True),
        (dict(base=True), False),
        # la base est muette : personne, hors administrateur (v1.0111 : plus de repli sur l'`.env`)
        (dict(base=False), False),
        (dict(base=False, admins="42"), True),
        # la base muette ignore les capacités doublées
        (dict(base=False, capacite_role=True, capacite_compte=True), False),
    ]
    demandees = []   # les doublures notent la capacité demandée : toujours `event.create`
    for reglages, attendu in cas:
        _poser(monkeypatch, demandees, **reglages)
        assert asyncio.run(cap.can_create_event(None, membre)) is attendu, reglages
    assert demandees and set(demandees) == {"event.create"}


def test_modifier(monkeypatch):
    demandees = []

    async def a_la_capacite(db, roles, capacite):
        demandees.append(capacite)
        return capacite_accordee

    monkeypatch.setattr(cap, "has_capability", a_la_capacite)
    # (compte, administrateurs, créateur, capacité accordée, attendu)
    cas = [
        ({"id": "42", "roles": []}, "42", 7, False, True),    # administrateur
        ({"id": "7", "roles": []}, "", 7, False, True),       # créateur
        ({"id": "8", "roles": ["r1"]}, "", 7, True, True),    # `event.edit_any`
        ({"id": "8", "roles": ["r1"]}, "", 7, False, False),  # un autre
    ]
    for membre, admins, createur, capacite_accordee, attendu in cas:
        monkeypatch.setattr(settings, "ADMIN_IDS", admins)
        assert asyncio.run(cap.can_edit_event(None, membre, createur)) is attendu, membre
    assert set(demandees) == {"event.edit_any"}
