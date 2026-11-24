"""Lot « rr-socle-proprete » (v1.0111) : le socle sans branches mortes -- trois tests, sans base ni
réseau.

1. `test_taches_gardees` -- une tâche lancée par `taches.lancer` est dans l'ensemble tant qu'elle
   tourne, n'y est plus à sa fin.
2. `test_aucune_tache_nue` -- par l'arbre syntaxique, aucun appel `asyncio.create_task` dans `app/`
   hors de `app/taches.py`.
3. `test_reglages_muets_partis` -- `Settings` n'a plus les cinq réglages muets ni leurs cinq
   propriétés, et aucun fichier de `app/` ni de `alembic/versions/` ne lit `settings.<l'un des dix>`.
"""
from __future__ import annotations

import ast
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import taches
from app.config import Settings

RACINE = Path(__file__).resolve().parent.parent

CHAMPS_MUETS = (
    "ALLOWED_ROLE_IDS",
    "EVENT_EDITOR_ROLE_IDS",
    "EVENT_EDITOR_IDS",
    "SQUADRON_ROLES",
    "DORMANT_SQUADRON_NAMES",
)
PROPRIETES_MUETTES = (
    "allowed_role_ids_list",
    "event_editor_role_ids_set",
    "event_editor_ids_set",
    "squadron_roles_map",
    "dormant_squadron_names_list",
)


def test_taches_gardees():
    async def scenario():
        feu = asyncio.Event()

        async def attendre():
            await feu.wait()

        avant = set(taches._TACHES)
        tache = taches.lancer(attendre())
        assert isinstance(tache, asyncio.Task)
        await asyncio.sleep(0)
        assert tache in taches._TACHES and not tache.done()   # gardée tant qu'elle tourne
        feu.set()
        await tache
        await asyncio.sleep(0)                                 # le rappel de fin passe au tour suivant
        assert tache not in taches._TACHES                     # retirée à sa fin
        assert set(taches._TACHES) == avant

    asyncio.run(scenario())


def _est_create_task(noeud: ast.AST) -> bool:
    """Un appel `asyncio.create_task(…)`, ou `create_task(…)` importé nu."""
    if not isinstance(noeud, ast.Call):
        return False
    f = noeud.func
    if isinstance(f, ast.Attribute):
        return f.attr == "create_task" and isinstance(f.value, ast.Name) and f.value.id == "asyncio"
    return isinstance(f, ast.Name) and f.id == "create_task"


def test_aucune_tache_nue():
    nues = []
    for chemin in sorted((RACINE / "app").rglob("*.py")):
        if chemin == RACINE / "app" / "taches.py":
            continue
        arbre = ast.parse(chemin.read_text(encoding="utf-8"), filename=str(chemin))
        nues += [f"{chemin.relative_to(RACINE)}:{n.lineno}" for n in ast.walk(arbre) if _est_create_task(n)]
    assert nues == []


def test_reglages_muets_partis():
    for nom in CHAMPS_MUETS:
        assert nom not in Settings.model_fields, nom
    for nom in PROPRIETES_MUETTES:
        assert not hasattr(Settings, nom), nom
    lecture = re.compile(r"settings\.(?:%s)\b" % "|".join(CHAMPS_MUETS + PROPRIETES_MUETTES))
    lecteurs = []
    fichiers = list((RACINE / "app").rglob("*.py")) + list((RACINE / "alembic" / "versions").glob("*.py"))
    for chemin in sorted(fichiers):
        for n, ligne in enumerate(chemin.read_text(encoding="utf-8").splitlines(), 1):
            if lecture.search(ligne):
                lecteurs.append(f"{chemin.relative_to(RACINE)}:{n}")
    assert lecteurs == []
