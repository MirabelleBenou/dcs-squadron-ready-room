"""Lot « La carte des destructions » : le calcul de la carte d'une session.

Ce module lit la base, il n'y écrit rien, et il est HORS de l'empreinte du moteur
(`revision._MODULES`) : ni statistique, ni fiche de vol, ni récit n'en dépendent.

- `dcs_vers_lonlat` : la projection des coordonnées de DCS (x = nord, y = est, en
  mètres) vers la longitude et la latitude WGS84 -- Mercator transverse inverse,
  série de Krüger à l'ordre 6 (Karney 2011), en Python pur ;
- `theatre_de` : le théâtre d'une session, reconnu par les noms d'aérodrome de ses
  décollages et atterrissages (table `app/data/aerodromes_dcs.json`) ;
- `camp` : le camp lisible d'une coalition de DCS ;
- `construire_carte` : la réponse de `GET /api/debrief/sessions/{id}/carte`, **fonction
  pure** -- elle reçoit des objets déjà lus (la route ne fait que quatre lectures,
  quel que soit le nombre d'évènements) et rend un dictionnaire.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from functools import lru_cache
from pathlib import Path

from app.debrief import categorize, referentiel

_TABLE_AERODROMES = Path(__file__).resolve().parent.parent / "data" / "aerodromes_dcs.json"

# --- La projection -----------------------------------------------------------------------
# Ellipsoïde WGS84 ; échelle 0,9996 ; latitude d'origine 0.
_A = 6378137.0
_F = 1.0 / 298.257223563
_K0 = 0.9996
_E2 = _F * (2.0 - _F)
_E = math.sqrt(_E2)
_N = _F / (2.0 - _F)

# Par théâtre : (méridien central, faux est, faux nord). `x` DCS = nord, `y` DCS = est :
# nord = x − faux nord, est = y − faux est.
_PROJECTION: dict[str, tuple[float, float, float]] = {
    "syria": (39.0, 282801.00000003993, -3879865.9999999935),
    "germanycw": (21.0, 35427.619999985734, -6061633.128000011),
    "caucasus": (33.0, -99516.9999999732, -4998114.999999984),
}

# Rayon rectifiant et coefficients β de Karney (2011, éq. 35), jusqu'à n^6.
_RAYON = _A / (1.0 + _N) * (1.0 + _N**2 / 4.0 + _N**4 / 64.0 + _N**6 / 256.0)
_BETA = (
    _N / 2.0 - 2.0 * _N**2 / 3.0 + 37.0 * _N**3 / 96.0 - _N**4 / 360.0
    - 81.0 * _N**5 / 512.0 + 96199.0 * _N**6 / 604800.0,
    _N**2 / 48.0 + _N**3 / 15.0 - 437.0 * _N**4 / 1440.0 + 46.0 * _N**5 / 105.0
    - 1118711.0 * _N**6 / 3870720.0,
    17.0 * _N**3 / 480.0 - 37.0 * _N**4 / 840.0 - 209.0 * _N**5 / 4480.0
    + 5569.0 * _N**6 / 90720.0,
    4397.0 * _N**4 / 161280.0 - 11.0 * _N**5 / 504.0 - 830251.0 * _N**6 / 7257600.0,
    4583.0 * _N**5 / 161280.0 - 108847.0 * _N**6 / 3991680.0,
    20648693.0 * _N**6 / 638668800.0,
)


def _tau_depuis_tau_prime(tau_p: float) -> float:
    """τ = tan φ à partir de τ' = tan χ (latitude conforme) : itération de Newton
    (Karney 2011, éq. 19-21). Converge en deux ou trois tours."""
    tau = tau_p
    for _ in range(8):
        sigma = math.sinh(_E * math.atanh(_E * tau / math.sqrt(1.0 + tau * tau)))
        tau_p_i = tau * math.sqrt(1.0 + sigma * sigma) - sigma * math.sqrt(1.0 + tau * tau)
        delta = (
            (tau_p - tau_p_i) / math.sqrt(1.0 + tau_p_i * tau_p_i)
            * (1.0 + (1.0 - _E2) * tau * tau) / ((1.0 - _E2) * math.sqrt(1.0 + tau * tau))
        )
        tau += delta
        if abs(delta) < 1e-14:
            break
    return tau


def dcs_vers_lonlat(theatre: str, x: float, y: float) -> tuple[float, float]:
    """`(lon, lat)` en degrés, pour un point `(x, y)` des coordonnées de DCS."""
    meridien, faux_est, faux_nord = _PROJECTION[theatre]
    xi = (x - faux_nord) / (_K0 * _RAYON)      # DCS x = nord
    eta = (y - faux_est) / (_K0 * _RAYON)      # DCS y = est
    xi_p, eta_p = xi, eta
    for j, beta in enumerate(_BETA, start=1):
        xi_p -= beta * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        eta_p -= beta * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    tau_p = math.sin(xi_p) / math.sqrt(math.sinh(eta_p) ** 2 + math.cos(xi_p) ** 2)
    lat = math.degrees(math.atan(_tau_depuis_tau_prime(tau_p)))
    lon = meridien + math.degrees(math.atan2(math.sinh(eta_p), math.cos(xi_p)))
    return lon, lat


# --- Le théâtre ----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def aerodromes_par_theatre() -> dict[str, dict[str, tuple[float, float]]]:
    """La table des aérodromes : théâtre → nom → `(x, y)` en coordonnées de DCS."""
    with _TABLE_AERODROMES.open("r", encoding="utf-8") as fh:
        brut = json.load(fh)
    return {t: {nom: (xy[0], xy[1]) for nom, xy in noms.items()} for t, noms in brut.items()}


def theatre_de(lieux) -> str | None:
    """Le théâtre d'une session : celui dont la table nomme le plus des `lieux` (un par
    évènement, compte d'évènements). Aucun lieu reconnu, ou une égalité au premier rang :
    `None`. Aucune autre source."""
    table = aerodromes_par_theatre()
    compte: Counter = Counter()
    for lieu in lieux:
        if not lieu:
            continue
        for theatre, noms in table.items():
            if lieu in noms:
                compte[theatre] += 1
    if not compte:
        return None
    classes = compte.most_common()
    if len(classes) > 1 and classes[0][1] == classes[1][1]:
        return None
    return classes[0][0]


# --- Le camp ---------------------------------------------------------------------------------
def camp(valeur) -> str:
    """`"blue"`, `"red"` ou `"neutral"` : `"2"`/`"blue"` → bleu, `"1"`/`"red"` → rouge, toute
    autre valeur (`None` compris) → neutre. Valeur détourée et passée en minuscules."""
    v = str(valeur if valeur is not None else "").strip().lower()
    if v in ("2", "blue"):
        return "blue"
    if v in ("1", "red"):
        return "red"
    return "neutral"


# --- La carte --------------------------------------------------------------------------------
TYPES_EVENEMENTS_CARTE = ("kill", "hit", "takeoff", "land", "eject", "pilot dead")
# Deux sièges d'un même équipage : une chute à 10 s au plus d'une chute déjà gardée.
_FENETRE_SIEGES_S = 10.0


def _nom_affichage(unit_type: str | None) -> str:
    """Le nom d'affichage de `categorize` ; la séquence `\\"` du référentiel y devient `"`."""
    return categorize.categorize(unit_type)[0].replace('\\"', '"')


def _seconde(t: float | None) -> int:
    return int(round(t or 0.0))


def construire_carte(entete: dict, vols, evenements, cimetiere, noms: dict) -> dict:
    """La réponse de `GET /sessions/{id}/carte`, à partir d'objets déjà lus :

    - `entete` : `id`, `display_title`, `mission_date`, `duration_s` (tels que
      `GET /sessions/{id}` les rend) ;
    - `vols` : TOUS les vols de la session (`DebriefFlight`), sans le filtre des vols vides ;
    - `evenements` : les évènements de la session des types `kill`, `hit`, `takeoff`, `land`,
      `eject`, `pilot dead`, et ceux qui portent un `place` ;
    - `cimetiere` : les lignes de `debrief_graveyard` ;
    - `noms` : `profile_id` → nom du membre (`_noms_membres_bulk`).
    Pure : aucune lecture, aucune écriture."""
    evenements = list(evenements)
    theatre = theatre_de([e.place for e in evenements if e.place])
    rep = {
        "id": entete["id"],
        "display_title": entete["display_title"],
        "mission_date": entete["mission_date"],
        "duration_s": entete["duration_s"],
        "theatre": theatre,
        "camp_ami": None,
        "vols": {},
        "epaves": [],
        "tirs": [],
        "touches": [],
        "aerodromes": [],
        "sans_lieu": 0,
        "chutes": [],
    }
    if theatre is None:
        return rep

    vols = list(vols)
    # --- L'acteur d'un évènement : le vol dont `object_id` est son `initiator_object_id`.
    vol_par_oid: dict[str, object] = {}
    for f in vols:
        if f.object_id is not None:
            vol_par_oid.setdefault(str(f.object_id), f)
    cites: set[str] = set()

    def vol_de(e) -> str | None:
        f = vol_par_oid.get(str(e.initiator_object_id)) if e.initiator_object_id is not None else None
        if f is None:
            return None
        cites.add(str(f.id))
        return str(f.id)

    # --- Le camp ami : le camp le plus nombreux des vols nommés de la session.
    pour_camp = Counter(
        camp(f.coalition) for f in vols
        if f.identity_state == "nomme" and camp(f.coalition) in ("blue", "red")
    )
    ordre = pour_camp.most_common()
    if ordre and not (len(ordre) > 1 and ordre[0][1] == ordre[1][1]):
        rep["camp_ami"] = ordre[0][0]

    # --- Les épaves : une par ligne du cimetière.
    epaves = []
    for g in cimetiere:
        lon, lat = dcs_vers_lonlat(theatre, g.x, g.y)
        epaves.append({
            "type": g.unit_type,
            "nom": _nom_affichage(g.unit_type),
            "categorie": referentiel.categorie_cible(g.unit_type),
            "camp": camp(g.coalition),
            "lon": round(lon, 6),
            "lat": round(lat, 6),
            "alt": None if g.alt is None else int(round(g.alt)),
        })
    groupes = Counter((e["type"], e["camp"]) for e in epaves)
    for e in epaves:
        e["homonymes"] = groupes[(e["type"], e["camp"])]
    epaves.sort(key=lambda e: (e["camp"], e["type"], e["lon"], e["lat"]))
    rep["epaves"] = epaves

    # --- Les évènements, par type, dans l'ordre du temps.
    ordonnes = sorted(
        (e for e in evenements if e.type in TYPES_EVENEMENTS_CARTE),
        key=lambda e: (e.t, e.type, str(e.initiator_object_id), str(e.target_object_id)),
    )

    for e in ordonnes:
        if e.type == "kill":
            rep["tirs"].append({
                "t": _seconde(e.t),
                "vol": vol_de(e),
                "tireur_type": _nom_affichage(e.initiator_unit_type),
                "tireur_camp": camp(e.initiator_coalition),
                "cible": e.target_unit_type,
                "cible_camp": camp(e.target_coalition),
                "arme": e.weapon,
            })
        elif e.type == "hit" and e.target_unit_type:
            rep["touches"].append({
                "t": _seconde(e.t),
                "vol": vol_de(e),
                "tireur_type": _nom_affichage(e.initiator_unit_type),
                "cible": e.target_unit_type,
                "cible_camp": camp(e.target_coalition),
            })

    # --- Les aérodromes : décollages (`dec`) et atterrissages (`att`) dont le lieu est connu.
    table = aerodromes_par_theatre()[theatre]
    par_nom: dict[str, dict] = {}
    for e in ordonnes:
        if e.type not in ("takeoff", "land"):
            continue
        if not e.place or e.place not in table:
            rep["sans_lieu"] += 1
            continue
        a = par_nom.get(e.place)
        if a is None:
            lon, lat = dcs_vers_lonlat(theatre, *table[e.place])
            a = par_nom[e.place] = {"nom": e.place, "lon": lon, "lat": lat, "dec": [], "att": []}
        a["dec" if e.type == "takeoff" else "att"].append({
            "t": _seconde(e.t),
            "vol": vol_de(e),
            "type": _nom_affichage(e.initiator_unit_type),
        })
    rep["aerodromes"] = [par_nom[n] for n in sorted(par_nom)]

    # --- Les éjections et les pilotes tués.
    gardees: list[tuple[float, object]] = []   # (t, clé d'équipage) des chutes gardées
    for e in ordonnes:
        if e.type not in ("eject", "pilot dead"):
            continue
        f = vol_par_oid.get(str(e.initiator_object_id)) if e.initiator_object_id is not None else None
        vol = str(f.id) if f is not None else None
        c = camp(e.initiator_coalition)
        cle = ("vol", vol) if vol is not None else ("ia", e.initiator_unit_type, c)
        if any(cle == k and abs(e.t - t) <= _FENETRE_SIEGES_S for t, k in gardees):
            continue
        gardees.append((e.t, cle))
        if vol is not None:
            cites.add(vol)
        unique = [
            p for p in epaves
            if p["type"] == e.initiator_unit_type and p["camp"] == c and p["homonymes"] == 1
        ]
        place = unique[0] if unique else None
        rep["chutes"].append({
            "quoi": "ejection" if e.type == "eject" else "tue",
            "t": _seconde(e.t),
            "vol": vol,
            "type": _nom_affichage(e.initiator_unit_type),
            "camp": c,
            "lon": place["lon"] if place else None,
            "lat": place["lat"] if place else None,
        })

    # --- Les vols cités, et eux seuls.
    for f in vols:
        if str(f.id) in cites:
            rep["vols"][str(f.id)] = {
                "pilot_callsign": f.pilot_callsign,
                "pilote_nom": noms.get(f.pilote_profile_id),
                "identity_state": f.identity_state,
                "aircraft_type": f.aircraft_type,
            }
    return rep
