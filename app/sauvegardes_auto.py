"""Lot « Les sauvegardes automatiques » -- l'application prend elle-même des
sauvegardes, à intervalle réglé.

Sur le patron de la boucle de l'appel (`app/appel.py`) : une tâche de fond
lancée par le lifespan (`app/main.py`), qui contrôle toutes les heures l'âge de
la dernière sauvegarde automatique. Par intervalle, jamais à heure fixe :
l'horloge de la VM n'est pas réglée. Un redéploiement ne remet pas le compte à
zéro, puisque l'âge se lit sur les fichiers de `BACKUP_DIR`.

Le réglage -- la fréquence et la rétention -- vit en base (table
`sauvegarde_auto_reglage`, une ligne au plus) ; sans ligne, `DEFAUT`. Une
sauvegarde automatique prend, comme le bouton de l'écran Archives, la base et
les écussons (`sauvegardes.sauvegarder`, origine `"auto"`).

Les fonctions pures (`valider_reglage`, `echeance`) se testent hors ligne
(tests/test_archives.py). Rien ici ne restaure.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select, text

from app import sauvegardes
from app.config import settings
from app.db import AsyncSessionLocal
from app.models import SauvegardeAutoReglage

logger = logging.getLogger(__name__)

# L'appel part à 60 s : les deux boucles ne démarrent pas ensemble.
DELAI_DEMARRAGE_S = 300
CONTROLE_S = 3600
# Les fréquences permises, en heures ; `0` vaut « désactivée ».
FREQUENCES_H = (0, 6, 12, 24, 48, 168)
# Les rétentions permises : le nombre d'automatiques gardées.
RETENTIONS = (3, 7, 14, 30)
DEFAUT = {"intervalle_h": 24, "garder": 7}

# La dernière tentative échouée, en mémoire de processus (déploiement
# mono-processus, comme l'appel) : `None` après une réussite.
_echec: Optional[dict] = None


def dernier_echec() -> Optional[dict]:
    """`{"date": <iso UTC>, "raison": <texte court>}` après une tentative
    échouée, `None` après une réussite (ou avant toute tentative)."""
    return _echec


def valider_reglage(intervalle_h, garder) -> dict:
    """Pure. Rend `{"intervalle_h", "garder"}` si les deux valeurs sont permises,
    sinon lève `ValueError` portant le message à l'écran. Un booléen est
    refusé : `True` n'est pas un nombre d'heures."""
    if type(intervalle_h) is not int or intervalle_h not in FREQUENCES_H:
        raise ValueError("Fréquence non reconnue.")
    if type(garder) is not int or garder not in RETENTIONS:
        raise ValueError("Rétention non reconnue.")
    return {"intervalle_h": intervalle_h, "garder": garder}


def echeance(derniere: Optional[datetime], maintenant: datetime, intervalle_h: int) -> bool:
    """Pure. Vrai quand une sauvegarde automatique est due : jamais si la
    fonction est désactivée (`intervalle_h == 0`) ; toujours sans sauvegarde
    précédente ; sinon quand la dernière a au moins `intervalle_h` heures."""
    if intervalle_h == 0:
        return False
    if derniere is None:
        return True
    return maintenant - derniere >= timedelta(hours=intervalle_h)


async def lire_reglage(db) -> dict:
    """Le réglage effectif : la ligne `id = 1`, ou `DEFAUT` sans ligne."""
    ligne = (
        await db.execute(select(SauvegardeAutoReglage).where(SauvegardeAutoReglage.id == 1))
    ).scalars().first()
    if ligne is None:
        return dict(DEFAUT)
    return {"intervalle_h": ligne.intervalle_h, "garder": ligne.garder}


def _poser_echec(raison: str) -> None:
    global _echec
    _echec = {"date": datetime.now(timezone.utc).isoformat(), "raison": raison}


async def passe(maintenant: Optional[datetime] = None) -> str:
    """Un contrôle. Rend `"desactivee"`, `"pas_encore"`, `"faite"`, `"en_cours"`
    ou `"echec"`.

    1. lit le réglage (sa propre session) ; désactivé -> `"desactivee"` ;
    2. cherche la dernière automatique dans `BACKUP_DIR` ; pas d'échéance ->
       `"pas_encore"` ;
    3. lit la révision Alembic en cours ;
    4. prend la sauvegarde (origine `"auto"`, rétention du réglage)."""
    global _echec
    maintenant = maintenant or datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        reglage = await lire_reglage(db)
    if reglage["intervalle_h"] == 0:
        return "desactivee"

    derniere = None
    for e in sauvegardes.lister(settings.BACKUP_DIR):
        if e["origine"] == "automatique":  # `lister` rend la plus récente d'abord
            derniere = datetime.fromisoformat(e["date"])
            break
    if not echeance(derniere, maintenant, reglage["intervalle_h"]):
        return "pas_encore"

    async with AsyncSessionLocal() as db:
        version = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalars().first()
    revision = sauvegardes.etiquette_revision(version)
    try:
        entree = await sauvegardes.sauvegarder(
            settings.BACKUP_DIR, settings.DATABASE_URL, settings.CREST_STORAGE_DIR,
            revision, origine="auto", garder=reglage["garder"],
        )
    except sauvegardes.SauvegardeEnCours:
        return "en_cours"  # rien ne change : le contrôle suivant reprendra
    except sauvegardes.SauvegardeEchec as exc:
        _poser_echec(str(exc))
        logger.warning("Sauvegarde automatique : échec (%s)", exc)
        return "echec"
    _echec = None
    logger.info("Sauvegarde automatique : %s", entree["fichier_base"])
    return "faite"


async def boucle() -> None:
    """Tâche de fond lancée par le lifespan (`app/main.py`) : un contrôle après
    `DELAI_DEMARRAGE_S`, puis toutes les `CONTROLE_S` secondes, sans fin. Jamais
    fatale : une erreur inattendue se journalise et se montre à l'écran
    Archives comme un échec ; un échec se retente au contrôle suivant, puisque
    l'échéance reste vraie."""
    await asyncio.sleep(DELAI_DEMARRAGE_S)
    while True:
        try:
            await passe()
        except Exception:
            logger.exception("Sauvegarde automatique : erreur non bloquante")
            _poser_echec("erreur inattendue")
        await asyncio.sleep(CONTROLE_S)
