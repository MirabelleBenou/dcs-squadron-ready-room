"""Fiche de faits du Rapport de mission — Lot R1, brief §1-§7 / cadrage R72-R82.

Transforme la liste des vols d'une session en une **fiche de faits** : jointe,
repliée, groupée, filtrée, comptée, signée. **Ne fabrique aucune prose** — la
rédaction (modèle de langage) est le lot R2, hors périmètre ici.

Fonction pivot : `build_report_facts(flights, mission)`. **Pure.** Aucun accès
base, aucun objet ORM, aucun `await` -- elle prend les dictionnaires tels que
`_flight_to_dict` (app/debrief/api.py) les sérialise déjà, et rend un
dictionnaire. C'est ce qui la rend recettable hors ligne, sur une fixture,
sans serveur ni Postgres.

Le groupement des menaces "touché" (`_aggregate_threat_log`) est un **port**
de `aggregateThreatLog()` (app/static/app.js) : même fenêtre (5 s), même clé
de regroupement (`initiator_object_id` + `weapon` + `gravite`). Un portage
divergent ferait diverger la fiche de ce que l'onglet Brut affiche côté
client -- et personne ne le verrait (brief §3, avertissement).

Passe d'assemblage, dans l'ordre (brief §3) :
    1. faits bruts       -- abattages, pertes, coups (menaces "touché" seules,
                             déjà agrégées en salves comme le fait le client)
    2. duels              -- un abattage + la perte de sa victime, ±120 s
    3. coups absorbés      -- un coup expliqué par la perte/duel qui suit, ≤90 s
    4. coups isolés écartés -- un coup de compte 1 sans autre coup ≤180 s
    5. salves d'abattages  -- même auteur/cible/arme, consécutifs, ≤180 s
    6. (Lot « La plume » : l'ordinal de machine est retiré ; le drapeau
       `nouvel_appareil` le remplace, posé dans l'ordre final des faits)
    7. empreinte           -- SHA-256 tronqué à 12 caractères, même idiome que
                              `ENGINE_REVISION` (app/debrief/revision.py)

Lot R3 §3⑤⑥, deux passes ajoutées après le tri chronologique (avant l'étape 7
ci-dessus) -- sur chaque fait déjà assemblé (Lot « La plume » : le nom de
camp, jamais lu, est retiré ; reste l'heure) :
    · quand / heure -- temps écoulé et heure de mission, calculés en Python,
      jamais par le modèle de langage (app/llm.py ne fait qu'employer "heure")

**N'appartient délibérément PAS** aux quatre modules hachés par
`revision.ENGINE_REVISION` (`engine.py`, `debriefer.py`, `acmi.py`,
`categorize.py`) : ce module neuf ne doit faire périmer aucune session
existante (brief §5, porte centrale).

Lot Récit A (brief SONNET du 9 septembre 2026) -- « la fiche parle
français » : NE TOUCHE PAS À LA PLUME, prépare la matière. Trois ajouts,
après le tri chronologique par `t`, avant l'empreinte (étape 7) :
    · libellés lisibles (`lexique.resoudre`) posés à côté de chaque clé DCS
      brute (`target_unit_type`, `initiator_unit_type`), jamais à sa place ;
    · `_group_salves` élargi : regroupe par CATÉGORIE (`lexique.categorie`)
      plutôt que par type exact -- la somme des compteurs `n` après
      regroupement égale toujours le nombre d'abattages avant (conservation
      des faits, brief §6 sonde L) ;
    · `paragraphes` : la fiche coupée en segments (silence/plancher/plafond,
      brief §5), chacun portant quatre marqueurs de saillance déterministes
      (`fratricide`, `perte_membre`, `duel`, `serie`) -- le modèle de langage
      n'en calcule aucun, il les lira au lot Récit B.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

from app.debrief import lexique
from app.recurrence import fuseau_reference

# R85 (brief R2 §2②, recette R1) -- les quatre fenêtres ci-dessous s'appliquent
# STRICTEMENT en `<`, jamais en `<=` : le brief disait "à moins de", et le
# brief fait foi contre le prototype du CdP qui les appliquait en inclusif.
# Aucune des huit valeurs de recette (Francfort) ne discrimine sur la borne --
# c'est précisément pour ça qu'il faut la figer maintenant, en commentaire,
# pour qu'un lot ultérieur ne l'inverse pas "par propreté" : un écart
# qu'aucune donnée ne révèle est un écart qui se réveille sur la session
# suivante. Le code ci-dessous est DÉJÀ conforme (`<` partout) -- ce
# commentaire fige l'existant, il ne change aucun calcul.
FEN_DUEL = 120.0    # abattage <-> perte de la même victime -- strict (<)
FEN_ABSORB = 90.0   # un coup encaissé explique la perte qui le suit -- strict (<)
FEN_SERIE = 180.0   # deux coups sur la même victime font une série -- strict (<)
FEN_SALVE = 180.0   # abattages répétés, même auteur/cible/arme -- strict (<)

# Fenêtre de regroupement des menaces "touché" -- identique à WINDOW_S dans
# aggregateThreatLog() (app/static/app.js). Ne PAS confondre avec les
# fenêtres ci-dessus : celle-ci groupe les entrées brutes de threat_log en
# "coups", les autres opèrent ensuite sur ces coups déjà groupés.
# R85, exception réelle -- reste INCLUSIVE (<=), parce qu'aggregateThreatLog()
# l'est côté client (app.js). On porte l'existant, on ne le corrige pas.
_AGG_WINDOW_S = 5.0

_GRAVITE_TOUCHE = "touché"
_PHASE_TYPES_PERTE = ("crash", "pilot dead")


# --- Étape 1a : port de aggregateThreatLog() (app.js) -----------------------


def _aggregate_threat_log(log: list[dict] | None) -> list[dict]:
    """Port fidèle de `aggregateThreatLog()` (app/static/app.js) : regroupe
    les entrées `threat_log` consécutives (triées par `t`) partageant le même
    `initiator_object_id`, `weapon` et `gravite`, à moins de 5 s d'écart entre
    deux impacts consécutifs. Ne filtre PAS par gravité -- exactement comme
    côté client, le filtre sur "touché" s'applique après, par l'appelant."""
    groups: list[dict] = []
    for th in sorted(log or [], key=lambda e: e.get("t") or 0):
        last = groups[-1] if groups else None
        if (
            last is not None
            and last["initiator_object_id"] == th.get("initiator_object_id")
            and last["weapon"] == th.get("weapon")
            and last["gravite"] == th.get("gravite")
            and (th.get("t") or 0) - last["t_end"] <= _AGG_WINDOW_S
        ):
            last["t_end"] = th.get("t") or 0
            last["count"] += 1
        else:
            groups.append({
                "t": th.get("t") or 0,
                "t_end": th.get("t") or 0,
                "count": 1,
                "initiator_object_id": th.get("initiator_object_id"),
                "initiator_unit_type": th.get("initiator_unit_type"),
                "weapon": th.get("weapon"),
                "gravite": th.get("gravite"),
            })
    return groups


def _perte_time(stats: dict) -> float | None:
    """La plus précoce des phases `crash`/`pilot dead` (brief §3 étape 1) --
    `eject` n'entre PAS dans ce calcul, seuls les deux types nommés comptent."""
    times = [p["t"] for p in stats.get("phases", []) if p.get("type") in _PHASE_TYPES_PERTE]
    return min(times) if times else None


# --- Étape 1 : faits bruts ---------------------------------------------------


def _raw_facts(flights: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Les faits bruts, par vol, dans l'ordre : abattages, perte (si
    applicable), coups (menaces "touché" déjà groupées) -- brief §3 étape 1."""
    abattages: list[dict] = []
    pertes: list[dict] = []
    coups: list[dict] = []

    for f in flights:
        oid = f.get("object_id")
        coalition = f.get("coalition")
        stats = f.get("stats") or {}

        for k in stats.get("kills", []):
            abattages.append({
                "t": k.get("t") or 0,
                "auteur_object_id": oid,
                "coalition": coalition,
                "target_object_id": k.get("target_object_id"),
                "target_unit_type": k.get("target_unit_type"),
                "weapon": k.get("weapon"),
            })

        phases = stats.get("phases", [])
        has_crash = any(p.get("type") == "crash" for p in phases)
        has_pilot_dead = any(p.get("type") == "pilot dead" for p in phases)
        if has_crash or has_pilot_dead:
            t = _perte_time(stats)
            if t is None:
                t = f.get("t_end")
            pertes.append({
                "t": t,
                "object_id": oid,
                "coalition": coalition,
                "ejected": bool(stats.get("ejected")),
                "coups_recus": [],
            })

        for g in _aggregate_threat_log(stats.get("threat_log")):
            if g["gravite"] != _GRAVITE_TOUCHE:
                continue
            coups.append({
                "t": g["t"],
                "t_end": g["t_end"],
                "count": g["count"],
                "object_id": oid,
                "coalition": coalition,
                "initiator_object_id": g["initiator_object_id"],
                "initiator_unit_type": g["initiator_unit_type"],
                "weapon": g["weapon"],
            })

    return abattages, pertes, coups


# --- Étape 2 : duels ---------------------------------------------------------


def _join_duels(
    abattages: list[dict], pertes: list[dict], by_object_id: dict[str, dict],
) -> tuple[list[dict], set[int], set[int]]:
    """Un abattage dont `target_object_id` est l'`object_id` d'un vol de la
    session, et dont la perte de ce vol tombe à moins de `FEN_DUEL`, devient
    un fait `duel` (brief §3 étape 2). `t` du duel = celui de l'abattage (le
    coup de feu), pas celui de la perte -- c'est l'instant qui fait sens pour
    l'absorption des coups à l'étape 3."""
    pertes_by_object: dict[str, list[int]] = defaultdict(list)
    for i, p in enumerate(pertes):
        pertes_by_object[p["object_id"]].append(i)

    consumed_pertes: set[int] = set()
    consumed_abattages: set[int] = set()
    duels: list[dict] = []

    for ai, a in enumerate(abattages):
        target = a["target_object_id"]
        if target not in by_object_id:
            continue
        best: tuple[int, float] | None = None
        for pi in pertes_by_object.get(target, []):
            if pi in consumed_pertes:
                continue
            p = pertes[pi]
            if p["t"] is None:
                continue
            diff = abs(p["t"] - a["t"])
            if diff < FEN_DUEL and (best is None or diff < best[1]):
                best = (pi, diff)
        if best is not None:
            pi = best[0]
            p = pertes[pi]
            consumed_pertes.add(pi)
            consumed_abattages.add(ai)
            duels.append({
                "t": a["t"],
                "auteur_object_id": a["auteur_object_id"],
                "auteur_coalition": a["coalition"],
                "victime_object_id": p["object_id"],
                "victime_coalition": p["coalition"],
                "target_unit_type": a["target_unit_type"],
                "weapon": a["weapon"],
                "ejected": p["ejected"],
                "coups_recus": [],
            })

    return duels, consumed_abattages, consumed_pertes


# --- Étapes 3 et 4 : coups absorbés / coups isolés écartés ------------------


def _resolve_coups(coups: list[dict], pertes: list[dict], duels: list[dict]) -> list[dict]:
    """Étape 3 : un coup suivi, à moins de `FEN_ABSORB`, d'une perte ou d'un
    duel portant sur le même vol, disparaît en tant que fait et se range dans
    `coups_recus` de celui-ci. Étape 4 : un coup restant, de compte 1, sans
    autre coup sur le même vol à moins de `FEN_SERIE`, est écarté."""
    losses_by_object: dict[str, list[tuple[float, tuple[str, int]]]] = defaultdict(list)
    for i, p in enumerate(pertes):
        if p["t"] is not None:
            losses_by_object[p["object_id"]].append((p["t"], ("perte", i)))
    for i, du in enumerate(duels):
        losses_by_object[du["victime_object_id"]].append((du["t"], ("duel", i)))

    absorbed: set[int] = set()
    for ci, c in enumerate(coups):
        best: tuple[float, tuple[str, int]] | None = None
        for t, ref in losses_by_object.get(c["object_id"], []):
            diff = t - c["t"]
            if 0 <= diff < FEN_ABSORB and (best is None or diff < best[0]):
                best = (diff, ref)
        if best is not None:
            kind, idx = best[1]
            target = pertes[idx] if kind == "perte" else duels[idx]
            # R84 (recette R1, corrigé en R2 §2①) -- le coup absorbé se
            # marque `fatal` s'il est, SUR UN DUEL SEULEMENT, le coup qui a
            # fait l'abattage (même auteur, même arme que le duel). Une
            # perte seule n'a pas d'auteur à comparer : `fatal` y est
            # toujours False. La clé est TOUJOURS posée, jamais omise --
            # une absence et un `False` ne se distinguent pas à la lecture.
            # Ne retire rien, ne réordonne rien : `coups_recus` ne change
            # pas de taille, seul le contenu de chaque coup s'enrichit.
            if kind == "duel":
                duel_ref = duels[idx]
                c["fatal"] = (
                    c["initiator_object_id"] == duel_ref["auteur_object_id"]
                    and c["weapon"] == duel_ref["weapon"]
                )
            else:
                c["fatal"] = False
            target["coups_recus"].append(c)
            absorbed.add(ci)

    remaining = [c for i, c in enumerate(coups) if i not in absorbed]

    by_object: dict[str, list[dict]] = defaultdict(list)
    for c in remaining:
        by_object[c["object_id"]].append(c)

    dropped_ids = {id(c) for c in remaining if _is_isolated(c, by_object[c["object_id"]])}
    return [c for c in remaining if id(c) not in dropped_ids]


def _is_isolated(c: dict, siblings: list[dict]) -> bool:
    if c["count"] != 1:
        return False
    return not any(
        s is not c and abs(s["t"] - c["t"]) < FEN_SERIE
        for s in siblings
    )


# --- Lot « La plume » §3.6 : les coups d'un même tireur se regroupent -------


def _regrouper_coups(coups: list[dict]) -> list[dict]:
    """Passe posée APRÈS `_resolve_coups` (absorption et coups isolés
    inchangés), avant l'identité des coups. Une session alignait six
    paragraphes « à 22:19 » faits des tirs des mêmes M-113 : deux coups de
    MÊME vol touché (`object_id`), MÊME tireur (`initiator_object_id`) et
    MÊME arme (`weapon`) se fondent quand le second commence strictement
    moins de `FEN_SERIE` après la fin (`t_end`) du coup qui les réunit déjà.

    Parcours par `t` croissant (tri stable : à `t` égal, l'ordre rendu par
    `_resolve_coups`). Le coup fondu garde le `t` et les autres champs du
    premier ; `count` est la somme, `t_end` le plus grand des deux. D'autres
    coups peuvent s'intercaler sans rien rompre. Un coup dont le tireur est
    inconnu (`initiator_object_id` à `None`) ne se fond jamais : deux tireurs
    inconnus ne sont pas un tireur. Le port `_aggregate_threat_log` ne change
    pas. Rend les coups restants dans l'ordre du parcours."""
    resultat: list[dict] = []
    ouverts: dict[tuple, dict] = {}
    for c in sorted(coups, key=lambda c: c["t"]):
        if c["initiator_object_id"] is None:
            resultat.append(c)
            continue
        cle = (c["object_id"], c["initiator_object_id"], c["weapon"])
        groupe = ouverts.get(cle)
        if groupe is not None and c["t"] - groupe["t_end"] < FEN_SERIE:
            groupe["count"] += c["count"]
            groupe["t_end"] = max(groupe["t_end"], c["t_end"])
        else:
            resultat.append(c)
            ouverts[cle] = c
    return resultat


# --- Étape 5 : salves d'abattages -------------------------------------------


def _group_salves(abattages: list[dict]) -> list[dict]:
    """Deux abattages consécutifs (chronologiquement, PAR AUTEUR) de même
    auteur, **même catégorie** (`lexique.categorie(target_unit_type)`,
    lot Récit A brief §5 -- élargi depuis le `target_unit_type` exact du
    lot précédent), même arme, séparés de moins de `FEN_SALVE` : un seul
    fait, compteur `n` (brief §3 étape 5).

    `target_unit_type` du fait groupé reste celui du PREMIER abattage de la
    salve, jamais réécrit -- la catégorie ne remplace rien, elle élargit
    seulement le critère de regroupement (brief lot Récit A : "aucune unité
    détruite n'est jamais perdue", et le type exact reste consultable sur le
    fait groupé pour un lot ultérieur qui en aurait besoin)."""
    by_auteur: dict[str, list[dict]] = defaultdict(list)
    for a in abattages:
        by_auteur[a["auteur_object_id"]].append(a)

    grouped: list[dict] = []
    for _, items in by_auteur.items():
        last: dict | None = None
        last_categorie: str | None = None
        for a in sorted(items, key=lambda a: a["t"]):
            a_categorie = lexique.categorie(a["target_unit_type"])
            if (
                last is not None
                and last_categorie == a_categorie
                and last["weapon"] == a["weapon"]
                and (a["t"] - last["t_end"]) < FEN_SALVE
            ):
                last["t_end"] = a["t"]
                last["n"] += 1
            else:
                last = {
                    "t": a["t"],
                    "t_end": a["t"],
                    "n": 1,
                    "auteur_object_id": a["auteur_object_id"],
                    "coalition": a["coalition"],
                    "target_object_id": a["target_object_id"],
                    "target_unit_type": a["target_unit_type"],
                    "weapon": a["weapon"],
                }
                last_categorie = a_categorie
                grouped.append(last)
    return grouped


# --- R88 (recette R1 -> dette portée à R2, brief §2③) : identité et type ----
# --- d'appareil, LUS sur le vol, jamais résolus ni inventés ici -------------


_SEGMENT_SEP_RE = re.compile(r"\s(\||I)\s")


def _short_name_segment(raw: str | None) -> str | None:
    """Segment nom humain d'un indicatif -- MÊME règle exacte que
    `shortCallsign()` (app/static/app.js) et `engine._extract_name_segment()`
    (app/debrief/engine.py) : coupe sur le DERNIER séparateur ('|' ou 'I'
    majuscule isolé, entouré d'espaces des deux côtés) et garde ce qui suit ;
    repli sur la chaîne entière si aucun séparateur. Troisième copie de la
    MÊME règle, à dessein : `report_facts.py` ne dépend d'aucun autre module
    de l'application (recette hors ligne, sans serveur, brief §1) -- importer
    `engine.py` chargerait `app.config`, qui EXIGE des variables
    d'environnement absentes en recette. Toute évolution de la règle doit
    être répercutée sur LES TROIS copies."""
    if not raw:
        return None
    matches = list(_SEGMENT_SEP_RE.finditer(raw))
    segment = raw[matches[-1].end():] if matches else raw
    segment = segment.strip()
    return segment or None


def _rangs_anonymes(flights: list[dict]) -> dict[str, int]:
    """`object_id` -> rang, pour les vols anonymes dont le TYPE est porté
    par plusieurs vols anonymes de la session (lot « Le vol anonyme
    numéroté » v1.0000). Deux vols anonymes de même type portaient jusqu'ici
    le même libellé, « Vol F-4E anonyme » : le récit en faisait un seul
    personnage, qui s'éjectait puis continuait d'abattre. Les vols sont
    numérotés dans l'ordre de `t_start`, celui du tableau des vols. Un type
    porté par un seul vol anonyme ne reçoit AUCUN rang -- « Vol F-16C
    anonyme » reste tel quel. Ne dit rien du pilote : deux appareils, pas
    deux personnes (R74)."""
    par_type: dict[str, list[dict]] = defaultdict(list)
    for f in flights:
        if f.get("identity_state") == "anonyme" and f.get("object_id"):
            par_type[f.get("aircraft_type")].append(f)
    rangs: dict[str, int] = {}
    for _, fls in par_type.items():
        if len(fls) < 2:
            continue
        for i, f in enumerate(sorted(fls, key=lambda f: f.get("t_start") or 0), start=1):
            rangs[f["object_id"]] = i
    return rangs


# --- Lot « La plume » §3.1 : le libellé du Centre ----------------------------
#
# `libelles` a la forme que rend `GET /api/referentiels/libelles` (lue par
# `referentiel.libelles`) : `{"types": {clé: libellé}, "armes": {clé:
# libellé}}`. La fiche reste pure : elle ne lit que ce dictionnaire.


def _libelle_type(cle: str | None, libelles_types: dict) -> str | None:
    """Le nom d'un type : le libellé du Centre s'il existe et n'est pas vide,
    sinon `lexique.resoudre`, comme avant le lot."""
    libelle = libelles_types.get(cle) if cle is not None else None
    return libelle if libelle else lexique.resoudre(cle)


def _libelle_arme(weapon: str | None, libelles_armes: dict) -> str | None:
    """Le nom d'une arme : le libellé du Centre s'il existe et n'est pas vide,
    sinon la valeur de `weapon` elle-même (`None` compris)."""
    libelle = libelles_armes.get(weapon) if weapon is not None else None
    return libelle if libelle else weapon


def _report_flight_name(f: dict | None, libelles_types: dict | None = None) -> str | None:
    """Port de `reportFlightName()` (app/static/app.js) : un vol anonyme se
    nomme par son type d'appareil, un vol nommé ou rattachable par le
    segment court de son indicatif -- MÊME condition exacte que le client
    (`identity_state == "anonyme"`), rien d'autre. La fiche n'a pas de
    paramètre de langue (une seule fiche par session, indépendante de la
    langue -- brief §3/§6) : le libellé anonyme est fixé en français, langue
    de travail du reste du dépôt (commentaires). Le rédacteur
    (app/llm.py) le retraduit à la volée pour `langue="en"`, exactement
    comme il rédige le reste en anglais à partir des mêmes faits. *Choix du
    CdP, à confirmer par le porteur -- signalé au rapport de livraison.*

    Lot Le groupement §2② -- le libellé (`lexique.resoudre`) remplace la
    clé DCS brute dans ce nom affiché ("Vol F-4E anonyme", jamais "Vol
    F-4E-45MC anonyme") ; repli sur la clé brute si le lexique ne la
    connaît pas (jamais "Vol ? anonyme" quand une clé existe, même non
    résolue).

    Lot « Le vol anonyme numéroté » v1.0000 -- le libellé porte son rang
    quand plusieurs vols anonymes partagent le type : « Vol F-4E anonyme
    n° 1 ». Le rang est posé sur la copie du vol par `by_object_id`
    (`_rang_anonyme`), jamais sur le vol de la réponse API.

    Lot « La plume » §3.1 -- le type se nomme d'abord par le libellé du
    Centre (`libelles_types`), puis par le lexique."""
    if f is None:
        return None
    if f.get("identity_state") == "anonyme":
        aircraft_type = f.get("aircraft_type")
        nom_type = _libelle_type(aircraft_type, libelles_types or {})
        libelle = f"Vol {nom_type or aircraft_type or '?'} anonyme"
        rang = f.get("_rang_anonyme")
        return f"{libelle} n° {rang}" if rang else libelle
    # Correctif « Le nom du membre » v1.0021 (R3) : l'indicatif observé
    # l'emporte ; à défaut, le nom du membre rattaché (`pilote_nom`, servi par
    # l'API). Ce module reste pur : il ne fait que lire la clé.
    return _short_name_segment(f.get("pilot_callsign") or f.get("pilote_nom"))


def _apply_identity(
    fact: dict, prefix: str, f: dict | None, libelles_types: dict | None = None,
) -> None:
    """Pose `{prefix}nom` et `{prefix}pilote_profile_id` (R88) à partir du
    vol déjà résolu par `by_object_id`. `prefix` vaut `""` (perte, abattage,
    coup) ou `"auteur_"`/`"victime_"` (duel). Ne résout rien : lit
    `identity_state` / `pilot_callsign` / `pilote_profile_id` tels que le vol
    les porte déjà -- cadrage §5, aucune résolution d'identité neuve.
    `pilote_profile_id` est `None` pour un vol anonyme, par construction
    (jamais rattaché à un profil) -- aucun cas particulier à écrire ici."""
    fact[f"{prefix}nom"] = _report_flight_name(f, libelles_types)
    fact[f"{prefix}pilote_profile_id"] = f.get("pilote_profile_id") if f else None


# --- Lot R5 §2 : les drapeaux « à dire » -------------------------------------
#
# Remplace, côté modèle de langage, un suivi qu'on lui demandait de tenir
# lui-même (R4 : « le camp à la première apparition seulement », « l'appareil
# redit seulement s'il change ») -- brief §1 : ce suivi est déterministe, il
# n'a jamais eu sa place dans la consigne de rédaction. Calculé ICI, en
# parcourant les faits déjà triés par `t` (brief §2) ; app/llm.py n'a plus
# qu'à LIRE ces deux booléens, jamais à les déduire.


def _dire_flags(
    nom: str | None,
    aircraft_type: str | None,
    dernier_appareil: dict[str, str],
) -> bool:
    """`dire_appareil` pour UN protagoniste d'UN fait (Lot « La plume » §3.7 :
    `dire_camp`, jamais lu, n'est plus calculé).

    Identité = le NOM D'AFFICHAGE (`nom`), JAMAIS l'`object_id` (brief §2 :
    Golem aligne onze `object_id` pour un seul pilote -- c'est lui que le
    lecteur suit, pas ses carlingues). `dernier_appareil` est
    partagé par l'appelant à travers tous les faits de la fiche, dans
    l'ordre chronologique -- c'est ce qui porte la mémoire d'un fait à
    l'autre, PAS une boucle locale à cette fonction.

    `dire_appareil` : vrai à la première apparition, ET à chaque fois que
    l'appareil diffère du dernier connu POUR CE NOM -- mais UNIQUEMENT là
    où `aircraft_type` est fourni pour ce protagoniste sur CE fait (brief
    §2, avertissement : le fait "coup" n'en porte pas ; sur un "duel",
    seule la victime en porte un -- arbitrage R3, inchangé). Là où
    `aircraft_type` est absent, le drapeau est faux, et l'état connu pour
    ce nom n'est PAS mis à jour (rien de nouveau n'a été appris)."""
    if nom is None:
        return False

    if aircraft_type is None:
        dire_appareil = False
    else:
        dire_appareil = dernier_appareil.get(nom) != aircraft_type
        dernier_appareil[nom] = aircraft_type

    return dire_appareil


def _apply_dire_flags(facts: list[dict]) -> None:
    """Pose, sur chaque fait de `facts` (dans l'ordre final), le drapeau
    `dire_appareil` par protagoniste mentionné -- `dire_appareil` pour les
    faits à un seul protagoniste (perte, abattage, coup),
    `auteur_dire_appareil`/`victime_dire_appareil` pour le duel -- même
    convention de préfixe que `_apply_identity` ci-dessus (Lot « La plume »
    §3.7 : le drapeau de camp n'est plus calculé).

    Le drapeau est TOUJOURS présent sur chaque protagoniste, jamais omis
    (brief §2 : une clé absente et une clé fausse ne se distinguent pas à la
    lecture). Aucun champ existant n'est retiré ni modifié."""
    dernier_appareil: dict[str, str] = {}

    for fact in facts:
        if fact["kind"] == "duel":
            # L'auteur (tireur) d'un duel ne porte jamais d'`aircraft_type`
            # sur CE fait (seule la victime en porte un, arbitrage R3) --
            # son drapeau appareil est donc toujours faux, et son état
            # connu n'est pas altéré par ce passage.
            fact["auteur_dire_appareil"] = _dire_flags(
                fact.get("auteur_nom"), None, dernier_appareil,
            )
            fact["victime_dire_appareil"] = _dire_flags(
                fact.get("victime_nom"), fact.get("aircraft_type"),
                dernier_appareil,
            )
        else:
            fact["dire_appareil"] = _dire_flags(
                fact.get("nom"), fact.get("aircraft_type"),
                dernier_appareil,
            )


# --- Lot « La plume » §3.2 : le nouvel appareil, à la place de l'ordinal -----


def _apply_nouvel_appareil(facts: list[dict]) -> None:
    """Pose `nouvel_appareil` (perte, abattage, coup) ou
    `auteur_nouvel_appareil`/`victime_nouvel_appareil` (duel), dans l'ordre
    FINAL des faits (après la permutation des paragraphes, comme
    `dire_appareil`). Identité par le NOM (`nom`, `auteur_nom`,
    `victime_nom`) ; appareil par l'`object_id` du rôle : le tireur pour un
    abattage (`auteur_object_id`), le vol perdu ou touché pour une perte ou
    un coup (`object_id`), chacun des deux pour un duel.

    Vrai si et seulement si ce nom est déjà apparu dans un fait PRÉCÉDENT et
    que le dernier `object_id` vu pour ce nom diffère de celui-ci. Un nom
    `None` : faux, et rien n'est retenu. Les drapeaux d'un fait se lisent sur
    l'état laissé par les faits précédents ; le fait met ensuite à jour le
    dernier `object_id` vu pour chacun de ses noms (auteur, puis victime)."""
    dernier_object_id: dict[str, str | None] = {}
    for fact in facts:
        if fact["kind"] == "duel":
            roles = [
                ("auteur_nouvel_appareil", fact.get("auteur_nom"), fact.get("auteur_object_id")),
                ("victime_nouvel_appareil", fact.get("victime_nom"), fact.get("victime_object_id")),
            ]
        elif fact["kind"] == "abattage":
            roles = [("nouvel_appareil", fact.get("nom"), fact.get("auteur_object_id"))]
        else:
            roles = [("nouvel_appareil", fact.get("nom"), fact.get("object_id"))]
        for cle, nom, object_id in roles:
            fact[cle] = (
                nom is not None
                and nom in dernier_object_id
                and dernier_object_id[nom] != object_id
            )
        for _, nom, object_id in roles:
            if nom is not None:
                dernier_object_id[nom] = object_id


# --- Lot Récit C §3 : la séquence par proximité -------------------------------
#
# Niveau intermédiaire entre le fait et le paragraphe (brief §2③) : deux
# faits consécutifs séparés de moins de `_SEUIL_SEQUENCE_S` appartenaient à
# la même séquence. Rendait 14 heures explicites sur 35 faits (Francfort) --
# mesuré trop bavard par le porteur (brief Lot Récit D §4), et remplacé pour
# `dire_heure` par une règle ancrée sur les paragraphes.
# Lot « La plume » §3.3 -- le seuil reprend du service : il borne le drapeau
# `enchaine` (`_apply_enchaine`), qui réserve « dans la foulée » aux faits
# qui suivent le précédent de moins de 90 s.
_SEUIL_SEQUENCE_S = 90.0   # 90 s -- lu par _apply_enchaine (strict, <)

# --- Lot Récit D §4 : dire_heure devient une règle de paragraphe -------------
#
# Nouvelle borne, mesurée sur Francfort (brief §4, tableau de dimensionnement) :
# 5 heures explicites sur 35 faits, contre 14 avant. Le seuil de 10 min sature
# vite sur cette session (le paragraphe fait l'essentiel du travail) mais joue
# sur une mission plus longue ou plus étalée -- conservé pour cette raison.
_SEUIL_HEURE_S = 600.0   # 10 min -- écart au fait précédent, dire_heure = vrai


def _apply_dire_heure(facts: list[dict], paragraphes_indices: list[list[int]]) -> None:
    """Pose `dire_heure` sur chaque fait de `facts` (déjà trié par `t`) --
    vrai au premier fait de chaque paragraphe, OU si l'écart avec le fait
    chronologiquement précédent atteint `_SEUIL_HEURE_S`, faux ailleurs
    (brief Lot Récit D §4 -- remplace la règle par séquence de 90 s du Lot
    Récit C §3, qui ne dépendait que du temps, jamais du paragraphe). Même
    patron que `dire_appareil` ci-dessus (brief Lot R5 §2) : le
    modèle LIT ce drapeau, il ne décide jamais lui-même si deux faits sont
    proches. `paragraphes_indices` est le résultat de `_split_paragraphes`,
    calculé une seule fois par `build_report_facts` et passé ici tel quel --
    cette fonction ne redécoupe rien (brief §1 : ne touche pas au
    découpage)."""
    premiers_de_paragraphe = {
        indices[0] for indices in paragraphes_indices if indices
    }
    dernier_t: float | None = None
    for i, fact in enumerate(facts):
        t = fact["t"]
        fact["dire_heure"] = (
            i in premiers_de_paragraphe
            or dernier_t is None
            or (t - dernier_t) >= _SEUIL_HEURE_S
        )
        dernier_t = t


def _fin_fait(fact: dict) -> float:
    """La fin d'un fait : son `t_end` s'il en porte un, sinon son `t`."""
    t_end = fact.get("t_end")
    return t_end if t_end is not None else fact["t"]


def _apply_enchaine(facts: list[dict]) -> None:
    """Lot « La plume » §3.3 -- pose `enchaine` sur chaque fait (dans l'ordre
    final) : vrai si et seulement si le fait n'est pas le premier de la
    fiche, que son `dire_heure` vaut faux, et que l'écart entre son `t` et la
    fin du fait précédent (`_fin_fait`) est positif ou nul et strictement
    inférieur à `_SEUIL_SEQUENCE_S`. La consigne réserve « dans la foulée »
    aux faits qui le portent."""
    precedent: dict | None = None
    for fact in facts:
        if precedent is None or fact["dire_heure"]:
            fact["enchaine"] = False
        else:
            ecart = fact["t"] - _fin_fait(precedent)
            fact["enchaine"] = 0 <= ecart < _SEUIL_SEQUENCE_S
        precedent = fact


# --- Lot Récit A §4 : la fiche parle français --------------------------------


def _apply_libelles(fact: dict, libelles_types: dict, libelles_armes: dict) -> None:
    """Pose le libellé lisible (`lexique.resoudre`) à côté de la clé DCS
    brute -- jamais à sa place :
    le code brut n'est jamais retiré. Trois clés portent une clé technique
    à traduire (corrigé Lot Le groupement §2② -- la docstring précédente
    affirmait "seuls deux faits", c'était faux et c'est l'origine du
    défaut) : `target_unit_type` (abattage, duel -- la cible du tir),
    `initiator_unit_type` (coup -- l'auteur de la menace, pas forcément un
    vol de la session), et `aircraft_type` (abattage, perte, duel --
    l'appareil du pilote lui-même, posé plus haut dans `build_report_facts`
    quel que soit le `kind` du fait -- un `coup` n'en porte jamais).

    Lot « La plume » §3.1 -- un type se nomme d'abord par le libellé du
    Centre (`_libelle_type`), puis par le lexique ; une arme reçoit
    `weapon_libelle` à côté de CHAQUE clé `weapon`, sur le fait et sur chaque
    élément de `coups_recus` (`_libelle_arme`) -- `weapon` reste."""
    if fact["kind"] in ("abattage", "duel"):
        fact["target_unit_type_libelle"] = _libelle_type(fact.get("target_unit_type"), libelles_types)
    elif fact["kind"] == "coup":
        fact["initiator_unit_type_libelle"] = _libelle_type(fact.get("initiator_unit_type"), libelles_types)
    if "aircraft_type" in fact:
        fact["aircraft_type_libelle"] = _libelle_type(fact.get("aircraft_type"), libelles_types)
    if "weapon" in fact:
        fact["weapon_libelle"] = _libelle_arme(fact.get("weapon"), libelles_armes)
    for coup in fact.get("coups_recus") or []:
        coup["weapon_libelle"] = _libelle_arme(coup.get("weapon"), libelles_armes)


# --- Lot R3 §3⑥ : chaque fait porte son heure --------------------------------


def _fmt_heure(reference_time: str | None, t: float | None) -> str | None:
    """"heure" -- heure de mission, `reference_time` (ISO, fuseau inclus)
    + `t` secondes, dite dans le fuseau de l'escadrille (`REFERENCE_TZ` ;
    lot « L'heure et la durée » v0.9995, UTC jusque-là), au format "HH:MM"
    (brief R3 §3⑥, arbitré par le porteur).
    `None` si `reference_time` est absent (session sans horodatage de
    référence) ou si `t` est absent : on écrit alors sans horodatage
    plutôt qu'une heure inventée -- jamais de valeur de repli."""
    if reference_time is None or t is None:
        return None
    try:
        ref = datetime.fromisoformat(reference_time)
    except (ValueError, TypeError):
        return None
    return (ref + timedelta(seconds=t)).astimezone(fuseau_reference()).strftime("%H:%M")


def _apply_temporal_fields(fact: dict, reference_time: str | None) -> None:
    """Pose "heure" (si `reference_time` est disponible) sur un fait --
    calculée en Python, jamais par le modèle de langage (brief R3 §3⑥ :
    la consigne emploie "heure" telle quelle, ne la recalcule jamais).

    Lot « Le quand muet » v0.9999 : "quand" -- la durée écoulée depuis le
    début de mission -- n'est plus posé. Trois générations successives des
    17, 18 et 19 septembre ne l'ont jamais cité : le récit raconte à
    l'heure, jamais en durée. La consigne ne le mentionnait nulle part."""
    fact["heure"] = _fmt_heure(reference_time, fact["t"])


# --- Étape 7 : empreinte -----------------------------------------------------


# --- Lot Récit D §5 : l'ouverture et la clôture du rapport -------------------
#
# `flight.stats.phases` est déjà calculé et stocké par le moteur
# (app/debrief/engine.py) -- brief §5 : « rien de tout cela ne se
# recalcule ». Cette passe ne fait que LIRE les phases à travers les vols
# de la session, sans toucher au moteur.
_LANDING_TYPES = ("land", "pilot landing")   # le moteur reconnaît les deux -- brief §5


def _phases_t(flight: dict, type_: str) -> list[float]:
    phases = flight.get("stats", {}).get("phases") or []
    return [p["t"] for p in phases if p.get("type") == type_]


def _nom_si_identifie(f: dict | None) -> str | None:
    """Nom à citer pour l'ouverture/la clôture -- `None` pour un vol
    anonyme (brief §5, repli 3 : « décollage anonyme => pas de nom »,
    jamais un pilote inventé), sinon le même nom court que le reste de la
    fiche (`_report_flight_name`)."""
    if f is None or f.get("identity_state") == "anonyme":
        return None
    return _report_flight_name(f)


def _apply_ouverture_cloture(
    flights: list[dict], reference_time: str | None, wing_note: str | None,
    facts: list[dict],
) -> dict:
    """Pose l'ouverture (démarrage, premier décollage) et la clôture
    (dernier atterrissage ENREGISTRÉ -- jamais « fin de mission », brief
    §5 repli 1) du rapport. Un décollage anonyme ne porte pas de nom
    (repli 3) ; une session sans aucun atterrissage relevé ne porte pas de
    clôture, `dernier_atterrissage_heure` reste `None` (repli 2) ;
    `wing_note` absente laisse simplement son champ à `None` (repli 4) --
    la consigne (app/llm.py) décide comment s'en passer.

    Lot « La plume » §3.4 -- `dernier_atterrissage_avant_fin` : vrai si et
    seulement si un dernier atterrissage existe, que la fiche a au moins un
    fait, et que cet atterrissage précède strictement la plus grande fin de
    fait (`_fin_fait`). On compare les secondes, jamais les heures écrites."""
    decollages: list[tuple[float, dict]] = []
    atterrissages: list[tuple[float, dict]] = []
    for f in flights:
        for t in _phases_t(f, "takeoff"):
            decollages.append((t, f))
        for landing_type in _LANDING_TYPES:
            for t in _phases_t(f, landing_type):
                atterrissages.append((t, f))

    premier_t, premier_f = min(decollages, key=lambda x: x[0]) if decollages else (None, None)
    dernier_t, dernier_f = max(atterrissages, key=lambda x: x[0]) if atterrissages else (None, None)

    return {
        "demarrage_heure": _fmt_heure(reference_time, 0.0),
        "premier_decollage_heure": _fmt_heure(reference_time, premier_t),
        "premier_decollage_nom": _nom_si_identifie(premier_f),
        "dernier_atterrissage_heure": _fmt_heure(reference_time, dernier_t),
        "dernier_atterrissage_nom": _nom_si_identifie(dernier_f),
        "dernier_atterrissage_avant_fin": (
            dernier_t is not None
            and bool(facts)
            and dernier_t < max(_fin_fait(f) for f in facts)
        ),
        "wing_note": wing_note or None,
    }


def _report_facts_sha(fiche_sans_empreinte: dict) -> str:
    """SHA-256 du JSON canonique de la fiche (`sort_keys=True`,
    `separators=(",",":")`, `ensure_ascii=False`), tronqué à 12 caractères --
    même idiome que `ENGINE_REVISION` (app/debrief/revision.py). Calculée sur
    la fiche SANS elle-même, puis ajoutée (brief §3 étape 7)."""
    blob = json.dumps(
        fiche_sans_empreinte, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


# --- Lot Récit A §5 : découpage en paragraphes -------------------------------
#
# Valeurs mesurées sur les quatre récits réels (brief §5), pas choisies :
# le seuil de silence a peu d'effet sur les résultats (4 à 6 min donnent des
# comptes quasi identiques) -- ce sont le plancher et le plafond qui font le
# travail. Fixées ici en constantes, comme FEN_* plus haut.
_SEUIL_SILENCE_S = 360.0   # 6 min -- coupe un nouveau paragraphe
_PLANCHER_FAITS = 4        # sous ce compte, fusion avec le voisin
_PLAFOND_FAITS = 12        # au-dessus, scission au plus grand silence interne


def _scinder_plafond(indices: list[int], facts: list[dict]) -> list[list[int]]:
    """Scinde `indices` (une tranche de `facts`, déjà triée par `t`) au plus
    grand silence interne, récursivement, jusqu'à ce que chaque morceau
    tienne sous `_PLAFOND_FAITS` (brief §5, étape « scinder »). Le point de
    coupe est choisi UNIQUEMENT parmi ceux qui laissent au moins
    `_PLANCHER_FAITS` faits de chaque côté -- une scission ne doit jamais
    créer, elle-même, un morceau sous le plancher que la fusion (passe
    précédente) n'aurait plus l'occasion de corriger. Toujours possible ici
    car `_PLAFOND_FAITS >= 2 * _PLANCHER_FAITS` (12 >= 8)."""
    if len(indices) <= _PLAFOND_FAITS:
        return [indices]
    bornes = range(_PLANCHER_FAITS, len(indices) - _PLANCHER_FAITS + 1)
    best_k = max(
        bornes, key=lambda k: facts[indices[k]]["t"] - facts[indices[k - 1]]["t"],
    )
    gauche, droite = indices[:best_k], indices[best_k:]
    return _scinder_plafond(gauche, facts) + _scinder_plafond(droite, facts)


def _split_paragraphes(facts: list[dict]) -> list[list[int]]:
    """Découpe `facts` (déjà trié par `t`) en paragraphes -- brief §5,
    algorithme en trois passes, dans cet ordre exact :
    1. couper à chaque silence >= `_SEUIL_SILENCE_S` ;
    2. fusionner avec le segment voisin tout segment sous `_PLANCHER_FAITS`
       (voisin suivant s'il existe, sinon le précédent -- seul le dernier
       segment d'une série n'a pas de suivant) ;
    3. scinder au plus grand silence interne tout segment au-dessus de
       `_PLAFOND_FAITS`.
    Une fiche sans fait rend une liste vide ; une fiche à un seul fait rend
    un unique paragraphe, quelle que soit sa taille sous le plancher --
    il n'y a alors aucun voisin avec qui fusionner."""
    n = len(facts)
    if n == 0:
        return []

    segments: list[list[int]] = []
    courant = [0]
    for i in range(1, n):
        if facts[i]["t"] - facts[i - 1]["t"] >= _SEUIL_SILENCE_S:
            segments.append(courant)
            courant = [i]
        else:
            courant.append(i)
    segments.append(courant)

    i = 0
    while i < len(segments) and len(segments) > 1:
        if len(segments[i]) < _PLANCHER_FAITS:
            if i < len(segments) - 1:
                segments[i + 1] = segments[i] + segments[i + 1]
                del segments[i]
            else:
                segments[i - 1] = segments[i - 1] + segments[i]
                del segments[i]
                i -= 1
        else:
            i += 1

    paragraphes: list[list[int]] = []
    for seg in segments:
        paragraphes.extend(_scinder_plafond(seg, facts))
    return paragraphes


def _acteur_destruction(fact: dict) -> str | None:
    """Le nom (identité d'affichage) de l'auteur d'une destruction, pour le
    marqueur "serie" -- un abattage (groupé) ou un duel EN TANT QU'AUTEUR,
    jamais une perte ni un coup, qui ne détruisent rien."""
    if fact["kind"] == "abattage":
        return fact.get("nom")
    if fact["kind"] == "duel":
        return fact.get("auteur_nom")
    return None


def _acteur_touche(fact: dict) -> str | None:
    """Le nom du vol touché par un coup -- interrompt une "serie" pour cet
    acteur (brief §5 : "sans être touché"). Une perte ou un duel où cet
    acteur est VICTIME n'entre pas ici : le brief ne nomme que le coup reçu
    comme rupture, pas la perte elle-même (qui met de toute façon fin à la
    série de cet acteur en le retirant du combat)."""
    if fact["kind"] == "coup":
        return fact.get("nom")
    return None


def _rafales_par_acteur(
    facts_paragraphe: list[dict], indices_paragraphe: list[int] | None = None,
) -> dict[str, tuple[int, list[int]]]:
    """Pour chaque acteur qui enchaîne au moins deux destructions sans
    qu'un coup reçu ne s'intercale, DANS CE PARAGRAPHE (brief Lot Récit C
    §4, marqueur "serie") : le plus long enchaînement atteint. Timeline par
    acteur (identité = nom d'affichage, même convention que `_dire_flags`
    -- brief §2), triée par `t` ; un coup reçu remet le compteur à zéro,
    une perte ne remet rien à zéro explicitement (elle retire l'acteur du
    combat, aucune destruction suivante ne peut donc plus lui être
    attribuée -- rien à faire de spécial ici). Ne retient que les acteurs
    dont le plus long enchaînement atteint au moins deux destructions --
    une seule destruction n'a rien enchaîné, rien à écrire là-dessus.

    Lot Le groupement §2① -- porte désormais aussi les indices (dans la
    `facts` globale de la fiche, pas une position locale au paragraphe) du
    MEILLEUR enchaînement : mémorisés au fil de la marche, figés au moment
    où l'enchaînement courant devient le meilleur, jamais accumulés sur
    toute la marche (le compte est celui du plus long enchaînement, pas du
    total -- brief §2, avertissement). `indices_paragraphe` est la liste
    des indices globaux, un par élément de `facts_paragraphe`, dans le
    même ordre ; `None` (repli local 0..n-1) ne sert qu'à `_a_une_serie`,
    qui ignore les indices et ne teste que la présence d'une série."""
    if indices_paragraphe is None:
        indices_paragraphe = list(range(len(facts_paragraphe)))
    par_acteur: dict[str, list[tuple[float, bool, int]]] = defaultdict(list)
    for f, gi in zip(facts_paragraphe, indices_paragraphe):
        d = _acteur_destruction(f)
        if d is not None:
            par_acteur[d].append((f["t"], True, gi))
        t = _acteur_touche(f)
        if t is not None:
            par_acteur[t].append((f["t"], False, gi))

    rafales: dict[str, tuple[int, list[int]]] = {}
    for acteur, evenements in par_acteur.items():
        evenements.sort(key=lambda e: e[0])
        rafale = 0
        meilleure = 0
        courante: list[int] = []
        meilleurs_indices: list[int] = []
        for _, est_destruction, gi in evenements:
            if est_destruction:
                rafale += 1
                courante.append(gi)
                if rafale > meilleure:
                    meilleure = rafale
                    meilleurs_indices = list(courante)
            else:
                rafale = 0
                courante = []
        if meilleure >= 2:
            rafales[acteur] = (meilleure, meilleurs_indices)
    return rafales


def _a_une_serie(facts_paragraphe: list[dict]) -> bool:
    """Vrai si un même acteur enchaîne au moins deux destructions sans
    qu'un coup reçu ne s'intercale, DANS CE PARAGRAPHE (brief §5, marqueur
    "serie"). Ancre conservée telle quelle (brief Lot Récit C §1) --
    déléguée à `_rafales_par_acteur`, qui porte désormais aussi le détail
    (qui, combien, lesquels) consommé par `_marqueurs_paragraphe`."""
    return bool(_rafales_par_acteur(facts_paragraphe))


def _pertes_repetees(facts_paragraphe: list[dict]) -> dict[str, int]:
    """Combien de fois chaque identité a été perdue DANS CE PARAGRAPHE
    (brief Lot Récit C §4, marqueur "perte_membre" resserré). Une perte
    isolée ne dit rien de spécial -- un vol perdu, c'est la matière même du
    débriefing ; c'est la RÉPÉTITION sur un même nom qui fait le marqueur
    ("perte_membre → qui, combien de fois", brief §4). Ne retient que les
    noms perdus au moins deux fois dans ce paragraphe."""
    par_nom: dict[str, int] = defaultdict(int)
    for f in facts_paragraphe:
        if f["kind"] == "perte":
            nom = f.get("nom")
        elif f["kind"] == "duel":
            nom = f.get("victime_nom")
        else:
            continue
        if nom is not None:
            par_nom[nom] += 1
    return {nom: n for nom, n in par_nom.items() if n >= 2}


def _duels_resserres(
    facts_paragraphe: list[dict], indices_paragraphe: list[int] | None = None,
) -> list[dict]:
    """Les paires d'acteurs qui s'affrontent plus d'une fois DANS CE
    PARAGRAPHE (brief Lot Récit C §4, marqueur "duel" resserré) -- un duel
    isolé ne "se resserre" à personne ; c'est un échange répété, dans un
    sens ou dans l'autre, entre les deux mêmes noms, qui fait le marqueur
    ("le duel se resserre à deux", brief §2④). La paire est NON ORDONNÉE :
    Kraken abat Golem puis Golem abat Kraken compte pour deux échanges de
    la MÊME paire, pas deux duels distincts.

    Lot Le groupement §2① -- porte désormais aussi les indices (`facts`
    globale) des faits `duel` qui composent l'échange, dans l'ordre
    chronologique (`facts_paragraphe` est déjà trié par `t`). `indices_paragraphe`
    -- un indice global par élément de `facts_paragraphe`, même ordre --
    reprend le repli local 0..n-1 quand omis, comme `_rafales_par_acteur`."""
    if indices_paragraphe is None:
        indices_paragraphe = list(range(len(facts_paragraphe)))
    par_paire: dict[frozenset[str], list[int]] = defaultdict(list)
    auteurs_par_paire: dict[frozenset[str], set[str]] = defaultdict(set)
    for f, gi in zip(facts_paragraphe, indices_paragraphe):
        if f["kind"] != "duel":
            continue
        auteur, victime = f.get("auteur_nom"), f.get("victime_nom")
        if auteur is None or victime is None:
            continue
        par_paire[frozenset((auteur, victime))].append(gi)
        auteurs_par_paire[frozenset((auteur, victime))].add(auteur)
    return [
        {"acteurs": sorted(paire), "echanges": len(indices), "facts": indices}
        for paire, indices in par_paire.items()
        if len(indices) >= 2 and len(auteurs_par_paire[paire]) >= 2
    ]


def _fratricides(facts_paragraphe: list[dict]) -> list[dict]:
    """Les duels où auteur et victime partagent la même coalition, DANS CE
    PARAGRAPHE (marqueur "fratricide", inchangé -- brief Lot Récit C §4 ne
    demande de resserrer que "perte_membre" et "duel" ; aucun fratricide
    sur le témoin, rien à resserrer ici). Porte simplement le détail au
    même format que les trois autres marqueurs, pour que le modèle n'ait
    jamais à retourner chercher dans le paragraphe ce que le marqueur
    annonce."""
    return [
        {"auteur": f.get("auteur_nom"), "victime": f.get("victime_nom")}
        for f in facts_paragraphe
        if f["kind"] == "duel"
        and f.get("auteur_coalition") is not None
        and f.get("auteur_coalition") == f.get("victime_coalition")
    ]


def _marqueurs_paragraphe(
    facts_paragraphe: list[dict], indices_paragraphe: list[int],
) -> dict[str, bool | list[dict]]:
    """Les quatre marqueurs de saillance, posés par la fiche -- brief Lot
    Récit C §4 : "le modèle ne juge de rien". Toujours les quatre clés,
    jamais omises (même discipline que `_apply_dire_flags` : une absence
    et un `False` ne se distinguent pas à la lecture). Chaque marqueur vrai
    porte désormais lui-même le détail à écrire -- acteurs concernés, faits
    visés, ampleur (brief §4) -- au lieu d'un `True` nu que le modèle
    devait retrouver dans le paragraphe. `perte_membre` et `duel` sont
    resserrés (répétition sur un même nom / sur une même paire) pour ne
    plus être vrais partout ; `fratricide` et `serie` gardent leur
    condition d'origine, avec le détail en plus.

    Lot Le groupement §2① -- `serie` et `duel` gagnent chacun une clé
    `facts` : les indices (dans la `facts` globale de la fiche) des faits
    qu'ils recouvrent -- ils POINTENT, ils ne recopient rien (brief §2, dix
    caractères plutôt qu'un fait entier). `fratricide` et `perte_membre`
    ne sont pas touchés ici : le brief ne cite que `serie`/`duel` comme
    exemples de marqueurs à faire pointer (§2), et le repère "9 marqueurs"
    du brief (§2, tableau) compte précisément les entrées `serie` + `duel`
    de la fixture Francfort, pas les quatre marqueurs eux-mêmes."""
    fratricides = _fratricides(facts_paragraphe)
    pertes = _pertes_repetees(facts_paragraphe)
    duels = _duels_resserres(facts_paragraphe, indices_paragraphe)
    series = _rafales_par_acteur(facts_paragraphe, indices_paragraphe)
    # Lot « Les quatre dernières dettes » (`v1.0046`) : chaque série porte le
    # nombre exact de ses cibles -- la somme des `n` des faits de son meilleur
    # enchaînement (un fait sans `n` compte pour 1). Calculé ici, avant
    # `_verifier_contiguite_marqueurs` : un marqueur qui perd `facts` garde
    # `cibles`.
    fait_par_indice = dict(zip(indices_paragraphe, facts_paragraphe))
    return {
        "fratricide": fratricides or False,
        "perte_membre": (
            [{"nom": nom} for nom in pertes] or False
        ),
        "duel": duels or False,
        "serie": (
            [
                # Lot « Les quatre dernières dettes » (`v1.0046`) -- la série
                # porte ses cibles, jamais le nombre de ses faits.
                {
                    "acteur": a,
                    "facts": idx,
                    "cibles": sum(fait_par_indice[i].get("n", 1) for i in idx),
                }
                for a, (_, idx) in series.items()
            ]
            or False
        ),
    }


# --- Lot Le réordonnancement §2①-③ : la fiche range, le modèle groupe -------
#
# R131 -- dans un paragraphe, le récit cesse de courir strictement à la
# pendule : les faits qu'un marqueur "serie" ou "duel" rassemble se
# racontent à la suite, même si d'autres évènements s'étaient intercalés
# chronologiquement. R132 -- un bloc s'ancre à la position de son PREMIER
# membre. R133 -- un marqueur qui ne peut pas être rendu contigu perd sa
# clé "facts" (§3, plus bas) : mieux vaut retirer une désignation que
# d'affirmer un groupement qui n'est pas dans l'ordre.


def _blocs_paragraphe(
    indices_paragraphe: list[int], facts: list[dict],
) -> list[list[int]]:
    """Les blocs de faits à rendre contigus dans ce paragraphe (brief §2①) :
    un groupe par entrée "serie" (`_rafales_par_acteur`) ou "duel"
    (`_duels_resserres`) d'au moins deux faits, les groupes qui partagent
    un membre étant fusionnés en un seul bloc. `indices_paragraphe` et
    `facts` sont lus AVANT `_apply_dire_heure`/`_apply_dire_flags` (brief
    §2② -- seuls "nom"/"auteur_nom"/"victime_nom"/"t"/"kind" sont déjà
    posés à ce point, et ce sont les seuls champs que lisent
    `_rafales_par_acteur` et `_duels_resserres`). Chaque bloc rendu est
    trié par ordre chronologique (indices globaux croissants, `facts`
    étant globalement trié par `t` en amont) -- un bloc à un seul membre
    n'est pas un bloc, il est omis."""
    facts_paragraphe = [facts[i] for i in indices_paragraphe]
    groupes: list[set[int]] = []
    for _, indices_serie in _rafales_par_acteur(facts_paragraphe, indices_paragraphe).values():
        if len(indices_serie) >= 2:
            groupes.append(set(indices_serie))
    for duel in _duels_resserres(facts_paragraphe, indices_paragraphe):
        if len(duel["facts"]) >= 2:
            groupes.append(set(duel["facts"]))

    fusionnes: list[set[int]] = []
    for groupe in groupes:
        chevauchants = [b for b in fusionnes if b & groupe]
        for b in chevauchants:
            fusionnes.remove(b)
            groupe = groupe | b
        fusionnes.append(groupe)

    return [sorted(b) for b in fusionnes if len(b) >= 2]


def _permuter_paragraphe(
    indices_paragraphe: list[int], facts: list[dict],
) -> list[int]:
    """Permute les indices d'un paragraphe pour que chaque bloc (brief §2①)
    occupe des positions consécutives -- R132 : ancré à la position de son
    premier membre. Ne change JAMAIS l'ensemble `indices_paragraphe`
    lui-même (même plage de positions dans `facts`), seul l'ORDRE à
    l'intérieur de cette plage bouge -- brief §1 : `_split_paragraphes`
    rend des plages consécutives, donc `paragraphes_indices` reste valide
    après permutation. Parcourt `indices_paragraphe` (déjà croissant, donc
    déjà chronologique) : au premier membre d'un bloc, émet le bloc
    entier ; saute ce qui est déjà émis ; émet le reste en place."""
    blocs = _blocs_paragraphe(indices_paragraphe, facts)
    bloc_par_premier_membre = {bloc[0]: bloc for bloc in blocs}

    resultat: list[int] = []
    deja_emis: set[int] = set()
    for i in indices_paragraphe:
        if i in deja_emis:
            continue
        bloc = bloc_par_premier_membre.get(i)
        if bloc is not None:
            resultat.extend(bloc)
            deja_emis.update(bloc)
        else:
            resultat.append(i)
            deja_emis.add(i)
    return resultat


def _verifier_contiguite_marqueurs(paragraphes: list[dict]) -> None:
    """R133, appliquée après `_build_paragraphes` (brief §2③) : pour
    chaque paragraphe, si les `facts` d'un marqueur "serie" ou "duel"
    n'occupent pas des positions CONSÉCUTIVES dans la liste des faits du
    paragraphe (positions locales -- pas les indices globaux eux-mêmes),
    la clé `facts` de ce marqueur est retirée. Mute `paragraphes` en
    place : c'est la définition de l'invariant, pas un filet -- si un
    marqueur porte `facts`, ses membres SONT contigus, par construction."""
    for paragraphe in paragraphes:
        position_locale = {gi: pos for pos, gi in enumerate(paragraphe["facts"])}
        marqueurs = paragraphe["marqueurs"]
        for cle in ("serie", "duel"):
            entree = marqueurs.get(cle)
            if not entree:
                continue
            for marqueur in entree:
                indices_marqueur = marqueur.get("facts")
                if not indices_marqueur:
                    continue
                positions = sorted(position_locale[gi] for gi in indices_marqueur)
                contigu = all(
                    positions[k + 1] - positions[k] == 1
                    for k in range(len(positions) - 1)
                )
                if not contigu:
                    del marqueur["facts"]


def _build_paragraphes(
    facts: list[dict], paragraphes_indices: list[list[int]],
) -> list[dict]:
    """Assemble les paragraphes finaux : indices dans `facts` (jamais une
    copie des faits -- une seule source de vérité), compte, marqueurs.
    `paragraphes_indices` (résultat de `_split_paragraphes`) est désormais
    calculé une fois par `build_report_facts` et passé ici -- `_apply_dire_heure`
    en a besoin aussi (Lot Récit D §4) ; `_split_paragraphes` lui-même n'est
    pas modifié, seul son point d'appel est déplacé (brief §1). Lot Le
    groupement §2① -- `indices` (les indices GLOBAUX, dans `facts`) est
    maintenant aussi passé à `_marqueurs_paragraphe`, qui en a besoin pour
    que `serie`/`duel` pointent vers `facts` et non vers une position
    locale au paragraphe."""
    paragraphes = []
    for indices in paragraphes_indices:
        pfacts = [facts[i] for i in indices]
        paragraphes.append({
            "facts": indices,
            "n_faits": len(indices),
            "marqueurs": _marqueurs_paragraphe(pfacts, indices),
        })
    return paragraphes


# Lot « La plume » §3.7 -- ne garde que ce qui existe encore : les codes de
# coalition, lus par le marqueur `fratricide` pendant le calcul.
_CLES_CAMP_A_RETIRER = frozenset({
    "coalition", "auteur_coalition", "victime_coalition",
})


def _retirer_cles_a_toute_profondeur(noeud):
    """Lot « Les camps et la plume » -- R145/R146 : retire, où qu'elles se
    trouvent sous `noeud`, les clés de `_CLES_CAMP_A_RETIRER`. Descend dans
    les dicts et les listes (donc aussi dans les éléments de `coups_recus`).
    Ne touche à aucun calcul : ce n'est qu'une projection en sortie."""
    if isinstance(noeud, dict):
        for cle in _CLES_CAMP_A_RETIRER:
            noeud.pop(cle, None)
        for valeur in noeud.values():
            _retirer_cles_a_toute_profondeur(valeur)
    elif isinstance(noeud, list):
        for element in noeud:
            _retirer_cles_a_toute_profondeur(element)


def _retirer_donnees_camp(fiche: dict) -> None:
    """Lot « Les camps et la plume » -- R145/R146 : retire, sous
    `fiche["facts"]` à toute profondeur, les clés de `_CLES_CAMP_A_RETIRER`
    (Lot « La plume » §3.7 : la clé racine `camps` n'est plus calculée). Mute
    `fiche` en place, juste avant le calcul de l'empreinte -- aucun autre
    calcul n'est affecté."""
    _retirer_cles_a_toute_profondeur(fiche.get("facts"))


# --- Fonction pivot -----------------------------------------------------------


def build_report_facts(
    flights: list[dict], mission: dict, libelles: dict | None = None,
) -> dict:
    """Fonction pure -- brief §1. Prend les vols d'une session tels que
    `_flight_to_dict` (app/debrief/api.py) les sérialise déjà, et `mission`
    (les champs de session utiles à la fiche -- au minimum un titre : il
    entre dans l'empreinte, cf. cadrage §6). Ne fait aucun accès base, aucun
    objet ORM, aucun `await`. Rend un dictionnaire, jamais de prose.

    Lot « La plume » §3.1 -- `libelles`, facultatif : les libellés de l'écran
    Référentiels du Centre, de la forme que rend `GET
    /api/referentiels/libelles` (`{"types": {...}, "armes": {...}}`). Absent
    ou `None` : deux tables vides, et la fiche nomme comme avant le lot."""
    libelles = libelles or {}
    libelles_types = libelles.get("types") or {}
    libelles_armes = libelles.get("armes") or {}
    # Lot « Le vol anonyme numéroté » v1.0000 : la table porte des COPIES
    # superficielles, enrichies du rang anonyme. Jamais les dicts de
    # `flights` eux-mêmes -- ils sont sérialisés tels quels dans la réponse
    # API, et une clé privée s'y inviterait.
    _rangs = _rangs_anonymes(flights)
    by_object_id = {
        f["object_id"]: {**f, "_rang_anonyme": _rangs.get(f["object_id"])}
        for f in flights if f.get("object_id")
    }

    abattages, pertes, coups = _raw_facts(flights)
    n_faits_bruts = len(abattages) + len(pertes) + len(coups)

    duels, consumed_abattages, consumed_pertes = _join_duels(abattages, pertes, by_object_id)

    remaining_abattages = [a for i, a in enumerate(abattages) if i not in consumed_abattages]
    remaining_pertes = [p for i, p in enumerate(pertes) if i not in consumed_pertes]

    n_coups_avant = len(coups)
    final_coups = _resolve_coups(coups, remaining_pertes, duels)
    n_coups_absorbes = sum(len(p["coups_recus"]) for p in remaining_pertes) + sum(
        len(du["coups_recus"]) for du in duels
    )
    n_coups_isoles_ecartes = n_coups_avant - n_coups_absorbes - len(final_coups)

    # Lot « La plume » §3.6 -- après `_resolve_coups`, avant l'identité des
    # coups ; `coups_isoles_ecartes` est compté avant, et garde son sens.
    n_coups_avant_regroupement = len(final_coups)
    final_coups = _regrouper_coups(final_coups)
    n_coups_regroupes = n_coups_avant_regroupement - len(final_coups)

    grouped_abattages = _group_salves(remaining_abattages)
    for a in grouped_abattages:
        # R88 ② -- l'abattage restant (non joint en duel) ne concerne que
        # son auteur (le tireur) : la cible n'est pas un vol de la session
        # (sinon elle aurait été jointe en duel à l'étape 2).
        auteur_f = by_object_id.get(a["auteur_object_id"])
        # Lot R3 §3⑦ -- appareil du TIREUR, lu sur son propre vol, jamais
        # déduit d'un autre fait du même pilote : une déduction juste
        # aujourd'hui devient une invention demain pour un pilote qui
        # n'apparaîtrait que dans des abattages (brief §3⑦).
        a["aircraft_type"] = auteur_f.get("aircraft_type") if auteur_f else None
        _apply_identity(a, "", auteur_f, libelles_types)
    for c in final_coups:
        # R88 ② -- le coup restant (non absorbé) ne concerne que le vol
        # touché (`object_id`) : l'auteur du tir (`initiator_object_id`)
        # n'est pas nécessairement un vol de la session, et R88 ne demande
        # pas de le nommer.
        _apply_identity(c, "", by_object_id.get(c["object_id"]), libelles_types)

    for p in remaining_pertes:
        # R88 ① -- aircraft_type sur la perte : lu sur le vol lui-même
        # (celui qui est perdu), jamais inventé.
        pf = by_object_id.get(p["object_id"])
        p["aircraft_type"] = pf.get("aircraft_type") if pf else None
        # R88 ② -- nom + pilote_profile_id, un seul champ chacun (la perte
        # ne concerne qu'un vol).
        _apply_identity(p, "", pf, libelles_types)
    for du in duels:
        # R88 ① -- aircraft_type sur le duel : celui de la VICTIME (le vol
        # qui a été perdu), même lecture que pour "perte" ci-dessus --
        # `target_unit_type` (déjà présent) reste le type déclaré par le
        # tireur dans son propre évènement de tir, distinct par nature ;
        # `aircraft_type` est le type que le vol porte lui-même.
        victime_f = by_object_id.get(du["victime_object_id"])
        du["aircraft_type"] = victime_f.get("aircraft_type") if victime_f else None
        # R88 ② -- deux noms, deux profils : auteur (tireur) et victime,
        # mêmes préfixes que auteur_coalition/victime_coalition déjà posés.
        _apply_identity(du, "auteur_", by_object_id.get(du["auteur_object_id"]), libelles_types)
        _apply_identity(du, "victime_", victime_f, libelles_types)

    facts: list[dict] = []
    for du in duels:
        facts.append({"kind": "duel", **du})
    for p in remaining_pertes:
        facts.append({"kind": "perte", **p})
    for a in grouped_abattages:
        facts.append({"kind": "abattage", **a})
    for c in final_coups:
        facts.append({"kind": "coup", **c})
    facts.sort(key=lambda f: f["t"])

    # Lot Récit D §4 -- calculé ici, une seule fois : `_apply_dire_heure` a
    # besoin des frontières de paragraphe, `_build_paragraphes` (plus bas)
    # réutilise le même résultat au lieu de redécouper. `_split_paragraphes`
    # lui-même n'est pas touché (brief §1), seul son point d'appel remonte.
    paragraphes_indices = _split_paragraphes(facts)

    # Lot Le réordonnancement §2① -- permutation LOCALE à chaque paragraphe :
    # les faits d'un même bloc ("serie"/"duel" fusionnés s'ils partagent un
    # membre) deviennent contigus, ancrés à la position de leur premier
    # membre (R132). `paragraphes_indices` (les PLAGES de positions) ne
    # change pas -- `_split_paragraphes` rend des plages consécutives, donc
    # permuter à l'intérieur d'une plage ne déplace que le CONTENU de
    # `facts`, jamais les plages elles-mêmes. Posée ICI, avant
    # `_apply_dire_heure` et `_apply_dire_flags` (brief §2②, piège de
    # séquencement vérifié) : posée après, ces deux passes calculeraient
    # leurs drapeaux sur un ordre qui n'existe plus.
    nouvel_ordre: list[int] = []
    for indices in paragraphes_indices:
        nouvel_ordre.extend(_permuter_paragraphe(indices, facts))
    facts = [facts[i] for i in nouvel_ordre]

    # Lot Récit C §3 -- remplacée par la règle de paragraphe du Lot Récit D
    # §4 : reste posée dès que `facts` est trié, avant tout le reste.
    _apply_dire_heure(facts, paragraphes_indices)
    # Lot « La plume » §3.3 -- lit `dire_heure`, donc posé juste après.
    _apply_enchaine(facts)

    # Lot R3 §3⑤⑥ -- le code brut ("coalition"/"auteur_coalition"/
    # "victime_coalition") reste posé pendant le calcul (le marqueur
    # `fratricide` le lit) et se retire à la sortie (Lot « La plume » §3.7 :
    # le nom de camp n'est plus posé).
    reference_time = mission.get("reference_time")
    for fact in facts:
        _apply_temporal_fields(fact, reference_time)
        _apply_libelles(fact, libelles_types, libelles_armes)
    # Lot R5 §2 -- pose APRÈS les deux passes ci-dessus (elle lit "nom" et
    # "aircraft_type", déjà posés plus haut dans cette fonction) ; passe
    # SÉQUENTIELLE sur `facts` (déjà trié par `t`) -- contrairement aux deux
    # ci-dessus, elle porte un état d'un fait à l'autre, elle n'est pas
    # indépendante par fait.
    _apply_dire_flags(facts)
    # Lot « La plume » §3.2 -- même ordre final que `_apply_dire_flags`.
    _apply_nouvel_appareil(facts)

    paragraphes = _build_paragraphes(facts, paragraphes_indices)
    # Lot Le réordonnancement §2③ -- R133 : rend l'invariant vrai par
    # construction (retire `facts` des marqueurs qui ne sont pas contigus).
    _verifier_contiguite_marqueurs(paragraphes)

    fiche = {
        "mission_id": mission.get("id"),
        "mission_title": mission.get("display_title") or mission.get("title"),
        "facts": facts,
        "paragraphes": paragraphes,
        "ouverture_cloture": _apply_ouverture_cloture(
            flights, reference_time, mission.get("wing_note"), facts,
        ),
        "counts": {
            "faits_bruts": n_faits_bruts,
            "duels": len(duels),
            "coups_absorbes": n_coups_absorbes,
            "coups_isoles_ecartes": n_coups_isoles_ecartes,
            "coups_regroupes": n_coups_regroupes,
            "abattages_groupes": len(grouped_abattages),
            "faits": len(facts),
        },
    }
    _retirer_donnees_camp(fiche)
    fiche["report_facts_sha"] = _report_facts_sha(fiche)
    return fiche
