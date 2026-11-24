"""Embellisseur de titre de mission -- Lot 2.1 (§4.2).

AUCUN import de `app.debrief.engine`, et `engine.py` n'importe rien d'ici :
séparation physique exigée par le brief (§3/§5.3), pas seulement
conventionnelle. `beautify_mission_title` ne doit JAMAIS entrer dans le
chemin de la clé de rattachement des sessions (`_resolve_session` dans
engine.py) -- contrairement à `_display_mission_name` (engine.py), qui EST
dans ce chemin (candidate_title -> _resolve_session) et que ce module ne
réutilise ni n'élargit.

Ce fichier ne contient que de l'affichage : aucun accès base de données,
aucune connaissance du modèle `DebriefSession`.
"""
from __future__ import annotations

import re

# Marqueurs de date/heure en fin de nom, au-delà du seul -AAAAMMJJ-HHMMSS
# déjà géré par le moteur (côté chemin debrief, via _mission_name_pipeline) :
# ce module traite aussi le chemin ACMI, dont le titre n'est JAMAIS passé
# par ce pipeline (candidate_title = parsed_meta.meta.title brut,
# engine.py). Un séparateur (- ou _), 8 chiffres (date), puis optionnellement
# un second séparateur (- ou _) et 4 à 6 chiffres (heure) -- couvre
# -AAAAMMJJ-HHMMSS, _AAAAMMJJ-HHMM, _AAAAMMJJ_HHMMSS, -AAAAMMJJ seul, et
# variantes de séparateur/longueur d'heure.
_TRAILING_DATE_RE = re.compile(r"[-_]\d{8}(?:[-_]\d{4,6})?$")

_MULTI_DASH_RE = re.compile(r"-{2,}")
_MULTI_SPACE_RE = re.compile(r" {2,}")


def beautify_mission_title(raw: str | None) -> str | None:
    """Titre d'affichage embelli, repli quand `display_name` est vide
    (§4.3). Règles dans l'ordre (§4.2) :
    1. retrait des marqueurs de date/heure en fin de nom ;
    2. `_` -> espace ;
    3. séparateurs répétés et espaces multiples réduits ;
    4. casse d'origine préservée (les capitales sont un geste CSS) ;
    5. jetons de version (V5.2.5) et sigles (GCW) non touchés -- aucune
       règle ci-dessus ne les affecte, par construction ;
    6. repli sur `raw` si le résultat est vide après strip().
    """
    if raw is None:
        return None

    text = raw
    prev = None
    while prev != text:
        prev = text
        text = _TRAILING_DATE_RE.sub("", text)

    text = text.replace("_", " ")
    text = _MULTI_DASH_RE.sub("-", text)
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = text.strip()

    return text or raw
