"""Lot « Le rattachement des dépôts » (v1.0052, R326) -- le rattachement d'un
`debrief.log` par son contenu, et les règles pures du déplacement et de la
fusion.

Module PUR : ni base, ni réseau. Il ne décide d'aucune statistique et reste
hors de `revision._MODULES` -- il ne dit que « quelle session » et « comment
le fichier l'a rejointe ». Le moteur (`engine.ingest_file`) et les routes
(`app/debrief/api.py`) l'appellent.

Pourquoi le contenu d'abord : DCS laisse parfois, dans l'en-tête du journal
(`mission_file_path`, `mission_file_mark`), la mission d'exemple chargée
avant de rejoindre le serveur (`.\\Mods\\aircraft\\…\\Missions\\quickStart/…miz`),
alors que les évènements sont ceux de la vraie mission. Deux journaux d'une
même mission partagent leurs faits (mêmes tirs, décollages, destructions, du
même objet, à la seconde près) ; deux missions différentes, presque aucun.
L'en-tête n'est plus qu'un repli (`engine._resolve_session`, inchangée).
"""
from __future__ import annotations

import re

# --- Les seuils, mesurés en production (sonde du CdP, R326) -----------------
# 14 sessions, 42 journaux : la part des faits communs entre deux journaux vaut
# 0,61 au pire dans une même session, 0,11 au mieux entre deux sessions
# différentes -- même quand c'est le même template rejoué un autre soir. Des
# en-têtes valides ont jusqu'à 207 h d'âge au moment du dépôt (d'où une fenêtre
# en jours, et non en heures).
SEUIL_FAITS = 20          # `n` minimal : en deçà, trop peu de faits pour juger
SEUIL_TAUX = 0.5          # entre 0,11 (sessions différentes) et 0,61 (même session)
TOLERANCE_S = 1.0         # |Δt| admis entre deux faits « communs »
FENETRE_JOURS = 14        # les sessions candidates : créées dans les 14 jours

# Les types de faits comparés : ce que tous les journaux d'une mission voient
# de la même façon, au même instant de mission.
FAITS = frozenset({
    "shot", "hit", "kill", "takeoff", "land", "dead", "crash", "eject",
    "pilot dead", "engine startup",
})

# Valeurs de `debrief_upload.rattachement` (migration 0039).
TITRE, CONTENU, MANUEL = "titre", "contenu", "manuel"


def faits_du_journal(events) -> list[tuple[str, str, float]]:
    """Les faits d'une liste d'évènements (du parseur, ou des lignes
    `DebriefEvent` de la base -- mêmes attributs `type`,
    `initiator_object_id`, `t`) : `(type, initiateur, t)` pour chaque
    évènement d'un type de `FAITS`, dont `t` est connu et dont l'initiateur
    n'est ni vide ni `"0"`. Dans l'ordre d'entrée."""
    out: list[tuple[str, str, float]] = []
    for e in events:
        if e.type not in FAITS or e.t is None:
            continue
        oid = e.initiator_object_id
        if oid is None or str(oid).strip() in ("", "0"):
            continue
        out.append((e.type, oid, float(e.t)))
    return out


def taux_communs(a, b) -> tuple[int, int]:
    """`(n, d)` entre deux listes de faits. Fenêtre commune `[lo, hi]` ;
    `fa` = faits de `a` dans la fenêtre, `fb` = faits de `b` dans la fenêtre
    élargie d'une seconde de chaque côté ; `n` = faits de `fa` qui ont dans
    `fb` un fait de même type et même objet à `TOLERANCE_S` près ;
    `d = min(|fa|, |fb|)`. `(0, 0)` sans fenêtre commune."""
    if not a or not b:
        return 0, 0
    lo = max(min(f[2] for f in a), min(f[2] for f in b))
    hi = min(max(f[2] for f in a), max(f[2] for f in b))
    if hi <= lo:
        return 0, 0
    fa = [f for f in a if lo <= f[2] <= hi]
    fb = [f for f in b if lo - 1 <= f[2] <= hi + 1]
    par_cle: dict[tuple[str, str], list[float]] = {}
    for typ, oid, t in fb:
        par_cle.setdefault((typ, oid), []).append(t)
    n = 0
    for typ, oid, t in fa:
        if any(abs(u - t) <= TOLERANCE_S for u in par_cle.get((typ, oid), ())):
            n += 1
    return n, min(len(fa), len(fb))


def taux(n: int, d: int) -> float:
    """`min(1, n / d)`, `0` si `d = 0`."""
    return min(1.0, n / d) if d else 0.0


def choisir(candidats):
    """`candidats` : des `(session, n, d)`. Ne garde que `n ≥ SEUIL_FAITS` et
    un taux `≥ SEUIL_TAUX` ; rend la session au meilleur taux, à égalité celle
    au plus grand `n`, puis la session créée le plus récemment (`created_at`) ;
    `None` si aucune ne passe."""
    retenus = [(s, n, d) for s, n, d in candidats if n >= SEUIL_FAITS and taux(n, d) >= SEUIL_TAUX]
    if not retenus:
        return None
    def cle(c):
        cree = getattr(c[0], "created_at", None)
        return (taux(c[1], c[2]), c[1], cree.timestamp() if cree is not None else float("-inf"))
    return max(retenus, key=cle)[0]


def entete_exemple(chemin: str | None) -> bool:
    """Vrai si le chemin de mission de l'en-tête désigne une mission
    d'exemple de DCS : aux séparateurs normalisés (le journal double les `\\`)
    et en minuscules, il contient un segment `mods` (`\\mods\\` au milieu, ou
    commence par `.\\mods\\`)."""
    if not chemin:
        return False
    c = re.sub(r"[\\/]+", "\\\\", str(chemin)).lower()
    return "\\mods\\" in c or c.startswith(".\\mods\\")


def rattachement_du_depot(par_contenu: bool, cle_session: str | None, cle_entete: str | None) -> str:
    """La provenance d'un journal au dépôt : `contenu` si la session vient du
    contenu ET que la clé de son titre diffère de celle de l'en-tête ; `titre`
    sinon (le contenu n'a fait que confirmer l'en-tête, ou l'en-tête a
    décidé)."""
    return CONTENU if par_contenu and cle_session != cle_entete else TITRE


def overrides_a_recopier(source, cible) -> list:
    """Les identifications manuelles (`manuel`, `detache`) de la mission de
    départ à recopier dans la cible : toutes, sauf pour un objet -- même
    `object_id`, ou même `acmi_track_id` -- où la cible en porte déjà une :
    celle de la cible l'emporte. `source` et `cible` : des vols (attributs
    `object_id`, `acmi_track_id`), déjà réduits à leurs identifications
    manuelles. Dans l'ordre de `source`."""
    oids = {v.object_id for v in cible if v.object_id}
    pistes = {v.acmi_track_id for v in cible if v.acmi_track_id}
    return [
        v for v in source
        if not (v.object_id and v.object_id in oids)
        and not (v.acmi_track_id and v.acmi_track_id in pistes)
    ]


def libelle_fichier(kind: str, deposant: str | None) -> str:
    """« Débrief — Viper », « ACMI — — » : le fichier tel que le journal du
    Centre le nomme."""
    return f"{'ACMI' if kind == 'acmi' else 'Débrief'} — {deposant or '—'}"


def etats_deplacer(fichier: str, mission_source: str, mission_cible: str) -> tuple[dict, dict]:
    """`(avant, apres)` du geste « déplacer », à passer à `journal.ecarts` :
    une ligne `fichier` (posée) et une ligne `mission` (source → cible)."""
    return {"mission": mission_source}, {"fichier": fichier, "mission": mission_cible}


def etats_fusionner(mission_absorbee: str, n_fichiers: int) -> tuple[dict, dict]:
    """`(avant, apres)` du geste « fusionner », à passer à `journal.ecarts` :
    une ligne `absorbee` -- « <titre> (<n> fichier(s)) »."""
    mot = "fichier" if n_fichiers == 1 else "fichiers"
    return {}, {"absorbee": f"{mission_absorbee} ({n_fichiers} {mot})"}
