"""Empreinte du moteur de statistiques — Lot Fraîcheur v0.9939, brief §3/§4 ;
formule revue au lot « Le passage moteur » (v1.0003).

Les statistiques d'un débriefing (`DebriefFlight.stats`, events, graveyard)
sont **stockées** en base par `recompute_session()`, jamais recalculées à la
lecture. Un changement de comportement du moteur de fusion ne se voit donc
sur AUCUNE session déjà en base tant que personne ne clique « Recalc. » à la
main. Ce module donne à l'application les moyens de savoir, sans intervention
humaine, quelles sessions ont été calculées par une version du moteur
différente de celle qui tourne aujourd'hui.

**Cinq modules produisent les statistiques**, pas seulement `engine.py` :
`debriefer.py` décide de ce que les journaux contiennent (un changement chez
lui change les statistiques sans toucher au moteur), `acmi.py` fait de même
côté ACMI, `categorize.py` décide de la catégorie d'une cible, `lexique.py`
ramène deux noms d'une même arme à un seul (`_ALIAS_ARME`) : un alias change
la fusion des faits (lot « Polish du moteur du Débrief », v1.0039 -- faute de
quoi une session ne se recalculait pas quand un alias était ajouté). Une
empreinte qui ne porterait que sur `engine.py` serait un trou.

**Les docstrings sortent de l'empreinte** : une correction de commentaire ne
change aucun calcul et ne doit déclencher aucun recalcul. Elles sont retirées
par parcours d'AST (pas par une regex sur le texte), puis chaque arbre est
décrit par `ast.dump` -- sa structure, jamais une réécriture du code : deux
fichiers identiques à la ponctuation, à l'indentation ou aux commentaires
près produisent donc la même empreinte.

**Ordre de concaténation fixe** : `engine.py`, `debriefer.py`, `acmi.py`,
`categorize.py`, `lexique.py` (venu en dernier, v1.0039), chaque bloc préfixé
du nom de fichier avant hachage --
inverser l'ordre changerait l'empreinte sans qu'aucun calcul n'ait changé.

**`ast.dump`, plus `ast.unparse`** (lot « Le passage moteur ») : `ast.unparse`
réécrit le code, et sa réécriture change d'un correctif de Python à l'autre --
mesuré, une seule f-string d'`engine.py` change de guillemets entre 3.12.6 et
3.12.9. La production (3.12.14) calculait donc `db9b98d9404d` quand le rituel
de reprise (3.12.3) lisait `997fa6da365e` pour le même code, et une
reconstruction d'image pouvait périmer toutes les sessions d'un coup.
`ast.dump` décrit l'arbre, dont la forme ne change pas d'un correctif à
l'autre : même empreinte sur les sept correctifs mesurés, de 3.12.0 à 3.12.13.
**Elle ne bouge plus qu'à un changement de version mineure** (3.13 : autre
valeur, mesurée) -- un recalcul complet, une fois, à ce moment-là.

**Coût mesuré : environ 50 ms**, une seule fois, à l'import de ce module
(calcul de `ENGINE_REVISION` ci-dessous).
"""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path

# Ordre de concaténation FIXE -- ne jamais réordonner (cf. docstring module).
# Lot « Polish du moteur du Débrief » (v1.0039) : `lexique.py` en cinquième et
# dernier module ; l'ordre des quatre autres ne bouge pas.
_MODULES: tuple[str, ...] = ("engine.py", "debriefer.py", "acmi.py", "categorize.py", "lexique.py")

_DEBRIEF_DIR = Path(__file__).resolve().parent


def _strip_docstrings(tree: ast.AST) -> ast.AST:
    """Retire, en place, le premier `Expr` de chaque Module/ClassDef/
    FunctionDef/AsyncFunctionDef lorsque c'est une constante de type `str`
    (donc une docstring) -- jamais par motif de ligne ou de texte."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body.pop(0)
    return tree


def _compute_engine_revision() -> str:
    """Lit les cinq modules, retire leurs docstrings par AST, décrit
    chaque arbre par `ast.dump` (sa structure, jamais une réécriture du
    code -- cf. docstring du module), concatène en préfixant chaque bloc du
    nom de fichier (ordre `_MODULES`), hache en SHA-256, garde les 12
    premiers caractères hexadécimaux."""
    parts: list[str] = []
    for name in _MODULES:
        src = (_DEBRIEF_DIR / name).read_text(encoding="utf-8")
        tree = ast.parse(src)
        tree = _strip_docstrings(tree)
        structure = ast.dump(tree)
        parts.append(name + structure)
    blob = "".join(parts)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


# Calculée une seule fois, à l'import (coût mesuré : environ 50 ms).
ENGINE_REVISION: str = _compute_engine_revision()


def is_stale(stats_engine_rev: str | None) -> bool:
    """**Le** prédicat de péremption -- écrit une seule fois, appelé partout
    (api.py, engine.py). `NULL` (`None`) est périmé : c'est l'état de toute
    session calculée avant que cette empreinte n'existe (brief §4)."""
    return stats_engine_rev != ENGINE_REVISION
