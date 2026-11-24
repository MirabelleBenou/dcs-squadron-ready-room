"""Catégorisation des types DCS bruts — spec §6.5.

Charge `app/data/object_db_v2_index.json` (asset applicatif, copie du
référentiel déjà utilisé par le Ground Unit Swapper) une seule fois, en
cache mémoire au niveau du module. Un type absent du référentiel ne bloque
jamais l'ingestion : il tombe en catégorie 'Inconnu' et alimente la table
de complétion locale `debrief_unit_category` (cf. app/debrief/engine.py).
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_OBJECT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "object_db_v2_index.json"

# Table de projection priorisée (spec §6.5 / brief §2.3) : la première
# catégorie dont un des attributs matche gagne. L'ordre est contractuel --
# notamment Défense AA AVANT Char (une Shilka/Tunguska porte des attributs
# de véhicule blindé mais doit rester classée Défense AA).
#
# ÉCART ASSUMÉ vs l'ordre littéral du brief (Planes puis Helicopters) :
# vérifié sur `object_db_v2_index.json`, 4 types portent SIMULTANÉMENT les
# attributs `Planes` ET `Helicopters` -- dont **Mi-24P** (l'appareil du
# CHARLIE-33 lui-même !), Mi-8MT, Mi-26, UH-1H. Sous l'ordre littéral du brief,
# ces 4 types seraient classés "Avion" au lieu d'"Hélicoptère" (`Planes`
# gagnerait car vérifié avant `Helicopters`). `Helicopters` est le signal
# le plus spécifique ; `Planes` semble être une étiquette générique
# "objet volant" mal nettoyée dans certaines fiches côté source. Hélicoptère
# est donc vérifié AVANT Avion ici -- à confirmer par le porteur/Opus (cf.
# rapport de livraison), écart clairement isolé et documenté.
_CATEGORY_PRIORITY: list[tuple[str, frozenset[str]]] = [
    ("Défense AA", frozenset({"Air Defence", "SAM elements", "AAA"})),
    ("Char", frozenset({"Tanks"})),
    ("Artillerie", frozenset({"Artillery", "MLRS"})),
    ("Blindé léger", frozenset({"IFV", "APC"})),
    ("Infanterie", frozenset({"Infantry"})),
    ("Véhicule", frozenset({"Trucks", "Unarmed vehicles"})),
    ("Navire", frozenset({"Ships"})),
    ("Hélicoptère", frozenset({"Helicopters"})),
    ("Avion", frozenset({"Planes"})),
    ("Static", frozenset({"Fortifications", "Buildings"})),
]

UNKNOWN_CATEGORY = "Inconnu"


@lru_cache(maxsize=1)
def _load_object_db() -> dict:
    try:
        with _OBJECT_DB_PATH.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        # Ne bloque jamais le démarrage : référentiel absent/corrompu -> tout
        # type retombe en Inconnu, journalisé une fois.
        logger.warning("object_db_v2_index.json illisible (%s) -- catégorisation dégradée", exc)
        return {}


def _project_category(attributes: list[str]) -> str:
    attr_set = frozenset(attributes)
    for category, triggers in _CATEGORY_PRIORITY:
        if attr_set & triggers:
            return category
    return UNKNOWN_CATEGORY


def categorize(unit_type: str | None) -> tuple[str, str, str]:
    """`(display_name, category, resolved_from)` pour un type DCS brut.

    - Type dans le référentiel -> `display_name` = `displayName`, catégorie
      projetée depuis `attributes` (première catégorie qui matche, ordre
      `_CATEGORY_PRIORITY`), `resolved_from='object_db'`.
    - Sinon -> `(unit_type, 'Inconnu', 'unknown')`. Jamais bloquant.
    """
    if not unit_type:
        return ("Inconnu", UNKNOWN_CATEGORY, "unknown")

    entry = _load_object_db().get(unit_type)
    if entry is None:
        return (unit_type, UNKNOWN_CATEGORY, "unknown")

    display_name = entry.get("displayName") or unit_type
    category = _project_category(entry.get("attributes") or [])
    return (display_name, category, "object_db")


def is_known_unit_type(name: str) -> bool:
    """Un `name` correspond-il à un type d'unité connu du référentiel ?
    Utilisé par la détection « vrai callsign » (spec §4.4/§3.2) : un
    `*PilotName` qui résout à un type connu n'est pas un callsign."""
    return name in _load_object_db()
