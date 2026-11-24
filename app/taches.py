"""Lot « rr-socle-proprete » : les tâches de fond gardées.

La documentation de Python le dit : le gestionnaire d'évènements ne garde que des
références faibles vers les tâches ; une tâche que rien ne référence peut être
ramassée par le ramasse-miettes en cours de route, sans erreur ni trace. Toute
tâche lancée sans être attendue passe donc par `lancer`, qui la garde dans un
ensemble de module jusqu'à sa fin. Hors de ce module, aucun `asyncio.create_task`
dans `app/` (garde : `tests/test_socle_proprete.py`).
"""
import asyncio

# Les tâches vivantes : ajoutées au lancement, retirées à leur fin.
_TACHES: set[asyncio.Task] = set()


def lancer(coroutine) -> asyncio.Task:
    """Crée la tâche, la garde jusqu'à sa fin et la rend (l'appelant peut aussi la
    conserver, pour l'annuler)."""
    tache = asyncio.create_task(coroutine)
    _TACHES.add(tache)
    tache.add_done_callback(_TACHES.discard)
    return tache
