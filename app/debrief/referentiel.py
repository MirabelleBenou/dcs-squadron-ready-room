"""Lot « Les référentiels : types et armes » -- la catégorie d'une cible,
telle que l'écran Référentiels du Centre peut la forcer.

La catégorie d'une cible se calcule À L'AFFICHAGE (jamais dans le moteur) :
`categorie_cible` rend la catégorie forcée du type si l'écran en a posé une,
sinon celle de `categorize.categorize` -- le moteur, `categorize.py` compris,
ne change pas. Les bilans (`_graveyard_to_dict`, `_bilan_des_vols`) la lisent
donc à chaque requête : une catégorie forcée s'applique à tout l'historique,
sans recalcul ni redémarrage.

`FORCEES` est un dictionnaire EN MÉMOIRE : clé DCS -> catégorie forcée, vide
par défaut. Il est rempli au démarrage (`lifespan`, `app/main.py`) et après
chaque écriture du référentiel (`charger`).

⚠ Valable tant que la production tourne en un seul processus
(`entrypoint.sh` : un `uvicorn`, sans `--workers`). À revoir avant tout
passage à plusieurs : une écriture ne rechargerait que le processus qui l'a
reçue.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.debrief import categorize
from app.debrief_models import DebriefUnitCategory, ReferentielArme

# Les catégories admises, dans cet ordre (celui de l'écran) : les valeurs de
# `categorize.py`.
CATEGORIES: list[str] = [
    "Avion",
    "Hélicoptère",
    "Défense AA",
    "Char",
    "Artillerie",
    "Blindé léger",
    "Infanterie",
    "Véhicule",
    "Navire",
    "Static",
    "Inconnu",
]

# clé DCS -> catégorie forcée. Vide par défaut ; relu par `charger`.
FORCEES: dict[str, str] = {}


def categorie_cible(unit_type: str | None) -> str:
    """La catégorie sous laquelle un type de cible se range dans les bilans :
    la catégorie forcée si elle est posée, sinon celle de `categorize`."""
    if unit_type and unit_type in FORCEES:
        return FORCEES[unit_type]
    return categorize.categorize(unit_type)[1]


async def charger(db: AsyncSession) -> None:
    """Relit les `categorie_forcee` non nulles de `debrief_unit_category` dans
    `FORCEES`. La lecture se fait d'abord ; le remplacement du dictionnaire
    ensuite, d'un seul geste (aucun `await` entre le vidage et le remplissage :
    une requête concurrente ne voit jamais un dictionnaire à moitié vide)."""
    rows = (
        await db.execute(
            select(
                DebriefUnitCategory.unit_type, DebriefUnitCategory.categorie_forcee
            ).where(DebriefUnitCategory.categorie_forcee.is_not(None))
        )
    ).all()
    nouvelles = {cle: cat for cle, cat in rows}
    FORCEES.clear()
    FORCEES.update(nouvelles)


async def lire_libelles(db: AsyncSession) -> dict[str, dict[str, str]]:
    """Lot « La plume » §3.1 -- la SEULE lecture des libellés de l'écran
    Référentiels du Centre : `{"types": {clé: libellé}, "armes": {clé:
    libellé}}`, les seules clés à libellé non vide. Rendue telle quelle par
    `GET /api/referentiels/libelles` (`app/api.py`) et passée à
    `report_facts.build_report_facts` par `_build_report_facts_for_session`
    (`app/debrief/api.py`) : deux lectures écrites deux fois finiraient par
    diverger."""
    types = {
        cle: libelle
        for cle, libelle in (
            await db.execute(
                select(DebriefUnitCategory.unit_type, DebriefUnitCategory.libelle).where(
                    DebriefUnitCategory.libelle.is_not(None)
                )
            )
        ).all()
        if libelle
    }
    armes = {
        cle: libelle
        for cle, libelle in (
            await db.execute(
                select(ReferentielArme.cle, ReferentielArme.libelle).where(
                    ReferentielArme.libelle.is_not(None)
                )
            )
        ).all()
        if libelle
    }
    return {"types": types, "armes": armes}
