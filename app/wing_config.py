"""Lot « La config d'escadre de Mission Plan fabriquée par le Centre » (v1.0091) --
la configuration d'escadre que lisent les modules de Mission Plan
(`wing_config_v1`), fabriquée par la Ready Room depuis l'Escadre et ses
escadrilles actives qui ont un callsign, au lieu d'un fichier déposé à la main.

`fabriquer` est une fonction pure : elle ne lit ni la base ni le disque (les
écussons lui arrivent par `lire_logo`). La route `/outils/wing-config.json`
(`app/main.py`) lit la base, appelle `en_memoire` et sert les octets.

La table des appareils (codes du Centre -> types DCS) et les livrées du jeu
vivent dans `app/static/dcs_types_livrees.json`, lu une seule fois à l'import :
c'est la source unique, pour le serveur et pour l'écran (`app.js`).
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Callable

from PIL import Image

_STATIC = Path(__file__).resolve().parent / "static"
_LOGO_REPLI = _STATIC / "assets" / "img" / "emblem-default.png"

MANAGED_BY = "Ready Room"
# La limite d'HQ pour un logo (`LOGO_MAX_SIZE`) : plus grand, il est réduit.
LOGO_COTE_MAX = 256


def _lire_table() -> dict:
    with open(_STATIC / "dcs_types_livrees.json", encoding="utf-8") as f:
        return json.load(f)


_TABLE = _lire_table()
# Les codes du Centre, comparés sans casse (un appareil saisi en « Autre… » peut
# n'en différer que par elle).
_TYPES_PAR_CODE = {code.casefold(): list(types) for code, types in _TABLE["types"].items()}


def _types_dcs(appareil: str) -> list[str]:
    """Les types DCS d'un appareil de l'escadrille : un code de la table donne
    ses types (aucun pour JTAC et LotATC) ; un appareil hors de la table passe
    tel quel -- un mod saisi en « Autre… » (`A-4E-C`) est un type DCS."""
    cle = appareil.strip().casefold()
    if cle in _TYPES_PAR_CODE:
        return _TYPES_PAR_CODE[cle]
    return [appareil.strip()] if appareil.strip() else []


def _sans_doublon(valeurs) -> list[str]:
    vus: list[str] = []
    for v in valeurs:
        if v not in vus:
            vus.append(v)
    return vus


def _png_en_data_url(octets: bytes | None) -> str | None:
    """Un PNG en data URL ; réduit à 256 px au plus (proportions gardées,
    `LANCZOS`) quand son plus grand côté les dépasse, sinon gardé à l'octet.
    Un fichier illisible vaut « pas de logo » (`None`), jamais une erreur."""
    if not octets:
        return None
    try:
        with Image.open(io.BytesIO(octets)) as image:
            image.load()
            if max(image.size) > LOGO_COTE_MAX:
                if image.mode not in ("RGB", "RGBA", "L", "LA"):
                    image = image.convert("RGBA")
                image.thumbnail((LOGO_COTE_MAX, LOGO_COTE_MAX), Image.LANCZOS)
                sortie = io.BytesIO()
                image.save(sortie, format="PNG", optimize=True)
                octets = sortie.getvalue()
    except Exception:
        return None
    return "data:image/png;base64," + base64.b64encode(octets).decode("ascii")


def _lire_logo_repli() -> str:
    """Le logo de l'escadre quand elle n'a pas d'emblème : celui de l'App, lu et
    mis en data URL une fois, à l'import. Un fichier absent ou illisible fait
    échouer l'import : jamais un `wing.logo` vide en mémoire."""
    data_url = _png_en_data_url(_LOGO_REPLI.read_bytes())
    if not data_url:
        raise RuntimeError(f"logo de repli illisible : {_LOGO_REPLI}")
    return data_url


_LOGO_REPLI_DATA = _lire_logo_repli()


def _texte(valeur: Any) -> str:
    return "" if valeur is None else str(valeur).strip()


def cle_escadre(cle, designation) -> str:
    """Lot « rr-public-sans-escadre » : la clé de l'escadre que Mission Plan et HQ gardent
    dans le navigateur des membres (`wing.id`). Le réglage `WING_ID` s'il est renseigné
    (espaces de bord retirés) ; sinon la désignation, chaque suite de blancs devenue un
    seul `-` ; sinon « Wing »."""
    cle = _texte(cle)
    if cle:
        return cle
    mots = _texte(designation).split()
    return "-".join(mots) if mots else "Wing"


def retenues(escadrilles) -> list:
    """Les escadrilles qui entrent dans la config : `actif`, avec un callsign
    non vide une fois ses espaces de bord retirés, par `id` croissant."""
    return sorted(
        (e for e in escadrilles if e.status == "actif" and _texte(e.callsign)),
        key=lambda e: e.id,
    )


def fabriquer(
    escadre, escadrilles, lire_logo: Callable[[Any], bytes | None], cle: str = ""
) -> bytes:
    """La config d'escadre, en octets (JSON compact, UTF-8). `escadre` est la
    ligne `wing` (ou `None`), `escadrilles` les lignes `squadron` ; `lire_logo`
    rend les octets PNG d'un écusson -- `"wing"` pour l'emblème de l'escadre,
    l'`id` de l'escadrille pour le sien -- ou `None` ; `cle` est le réglage `WING_ID`
    (vide : la clé se tire de la désignation, `cle_escadre`)."""
    sigle = _texte(getattr(escadre, "sigle", None))
    designation = _texte(getattr(escadre, "designation", None))
    court = sigle or designation or "Wing"
    emblem_sha = getattr(escadre, "emblem_sha", None)
    logo_escadre = _png_en_data_url(lire_logo("wing")) if emblem_sha else None

    squadrons: list[dict] = []
    liveries: dict[str, dict] = {}       # par nom sans casse : {"name", "aircraft"}
    par_defaut: dict[str, str] = {}
    for esc in retenues(escadrilles):
        id_esc = _texte(esc.designation)
        # Le nom complet tel quel, sinon la désignation ; le surnom est sa colonne.
        nom = _texte(esc.full_name) or id_esc
        surnom = _texte(esc.nickname)
        appareils = [a for a in (esc.aircraft or []) if isinstance(a, str)]
        fiche = {
            "id": id_esc,
            "name": nom,
            "nickname": surnom,
            "callsign": _texte(esc.callsign),
            "aircraft": _sans_doublon(t for a in appareils for t in _types_dcs(a)),
        }
        logo = _png_en_data_url(lire_logo(esc.id)) if esc.crest_sha else None
        if logo:
            fiche["logo"] = logo
        squadrons.append(fiche)

        for livree in esc.liveries or []:
            types = _sans_doublon(
                t for a in (livree.get("aircraft") or []) for t in _types_dcs(str(a))
            )
            nom_livree = str(livree.get("name") or "")
            if livree.get("jeu"):
                # Une livrée du jeu ne part que vers les types dont la liste du jeu la contient.
                types = [t for t in types if nom_livree in _TABLE["livrees"].get(t, [])]
            if not types or not nom_livree.strip():
                continue
            entree = liveries.setdefault(
                nom_livree.casefold(), {"name": nom_livree, "aircraft": []}
            )
            entree["aircraft"] = _sans_doublon(entree["aircraft"] + types)

        for appareil, nom_defaut in (esc.default_liveries or {}).items():
            for type_dcs in _types_dcs(str(appareil)):
                par_defaut.setdefault(type_dcs, str(nom_defaut))

    config = {
        "configSchemaVersion": 1,
        "managedBy": MANAGED_BY,
        "wing": {
            "id": cle_escadre(cle, designation),
            "shortName": court,
            "fullName": _texte(getattr(escadre, "full_name", None)),
            "appTitle": "HQ",
            "logo": logo_escadre or _LOGO_REPLI_DATA,
            "hqStamp": "HQ ░ " + court,
        },
        "squadrons": squadrons,
        "liveries": list(liveries.values()),
        "defaultLiveries": par_defaut,
    }
    return json.dumps(config, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


# --- La mémoire : les octets fabriqués sont gardés tant que les données lues
# ne changent pas ; la route sert ainsi la même config à chaque appel sans
# refaire les réductions d'image.
_memoire: dict[str, Any] = {"empreinte": None, "octets": None}


def _empreinte(escadre, escadrilles, logo_present: Callable[[Any], bool], cle: str = "") -> str:
    """L'empreinte des données lues : champs de l'escadre et des escadrilles,
    `emblem_sha`, `crest_sha`, présence des fichiers d'écusson, livrées, et la
    clé de l'escadre (un réglage changé refabrique)."""
    donnees = {
        "cle": cle,
        "escadre": [
            getattr(escadre, c, None)
            for c in ("designation", "sigle", "full_name", "emblem_sha")
        ] + [bool(logo_present("wing"))],
        "escadrilles": [
            [
                e.id, e.designation, e.callsign, e.full_name, e.nickname, e.status, e.crest_sha,
                bool(logo_present(e.id)), e.aircraft, e.liveries, e.default_liveries,
            ]
            for e in escadrilles
        ],
    }
    brut = json.dumps(donnees, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(brut.encode("utf-8")).hexdigest()


def en_memoire(
    escadre,
    escadrilles,
    lire_logo: Callable[[Any], bytes | None],
    logo_present: Callable[[Any], bool],
    cle: str = "",
) -> bytes:
    """Les octets de `fabriquer`, gardés tant que l'empreinte des données lues
    ne change pas ; sinon, on refabrique."""
    escadrilles = list(escadrilles)
    empreinte = _empreinte(escadre, escadrilles, logo_present, cle)
    if _memoire["empreinte"] != empreinte or _memoire["octets"] is None:
        _memoire["octets"] = fabriquer(escadre, escadrilles, lire_logo, cle)
        _memoire["empreinte"] = empreinte
    return _memoire["octets"]
