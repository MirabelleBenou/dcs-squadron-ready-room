"""Garde-fou de taille -- fiche et consigne, SÉPARÉMENT (correctif Lot Le
groupement §2, R119 pour la quatrième fois : la fiche de Francfort est
passée de 7 298 à 16 608 jetons sur la série Récit, à vols inchangés, et
`ENGINE_REVISION` ne l'a jamais vu -- `report_facts.py` n'entre pas dans
son empreinte). Ce n'est PAS un test de correction : les deux grandeurs
épinglées ci-dessous sont *sensées* bouger quand un lot enrichit
délibérément la fiche ou la consigne. Son rôle est l'inverse d'un test
habituel -- FAIRE ÉCHOUER pytest la prochaine fois qu'elles bougent, pour
qu'un humain (ou un CdP) DÉCIDE de mettre à jour la constante ci-dessous
dans le MÊME commit, plutôt que de laisser la dérive s'étaler sur des
mois sans qu'aucune empreinte ne la voie.

Fiche et consigne sont vérifiées par deux fonctions internes séparées,
jamais sur le prompt assemblé (correctif §2, avertissement) : elles grossissent pour
des raisons différentes et ont des propriétaires différents -- la fiche
est le déterministe versé par les lots sur `report_facts.py`, la consigne
est le budget de règles (R117) sur `_PROMPT_TEMPLATE`. Confondues dans une
seule mesure, on ne saurait plus laquelle a bougé à la lecture d'un échec.

Tout est mesuré en CARACTÈRES, jamais converti en jetons (correctif §2,
avertissement : le seul pont disponible est un ratio estimé, qui a déjà
induit le CdP en erreur une fois).

Fixture : "Bataille de Francfort", la même que `test_chaine_deux_temps.py`
et le rituel de reprise -- valeurs mesurées sur `readyroom_v0_9981.zip`.

Lot « La plume » §7 -- le garde-fou épingle DEUX fiches, chacune sans
libellés du Centre : Francfort et la session de production du 27 juillet
(`e29ea43b`). Deux jeux de constantes séparés ; la consigne une fois ; un
seul test pytest, comme avant.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import llm
from app.debrief.report_facts import build_report_facts

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "89f20c83-54ec-4fd4-bf0c-1700463ff155.json"
# Lot « La plume » §7 -- la seconde fiche surveillée.
FIXTURE_E29_PATH = Path(__file__).resolve().parent / "fixtures" / "e29ea43b-2029-47c3-88cb-225596bf1dca.json"

# Constantes déclarées ici, et nulle part ailleurs -- à mettre à jour
# DÉLIBÉRÉMENT, dans le même commit que ce qui les fait bouger.
# Lot « La plume » : 7ae08a71901c -> 0dcb85a5735f, 17980 -> 20933 (+2953),
# consigne 9422 -> 10096 (+674).
# Lot « Les quatre dernières dettes » (`v1.0046`) : -> 3c4de0bed42f, 20999 (+66) ; e29 -> 0025774b6483, 26504 (+77) ; consigne 11300 (+1204).
# Lot « rr-public-anonymiser » (`v1.0114`) : -> fcab834cdd48, 20999 (+0) ; e29 -> 42837fc67792, 26504 (+0) ; consigne 11300 (+0) -- noms fictifs de même longueur.
_REPORT_FACTS_SHA_ATTENDU = "fcab834cdd48"
_N_FAITS_ATTENDU = 35
_N_FAITS_PAR_PARAGRAPHE_ATTENDU = [5, 10, 4, 11, 5]
_TAILLE_FICHE_ATTENDUE = 20999
_TAILLE_CONSIGNE_ATTENDUE = 11300

# Lot « La plume » §7 -- le jeu de la session du 27 juillet (`e29ea43b`).
_REPORT_FACTS_SHA_ATTENDU_E29 = "42837fc67792"
_N_FAITS_ATTENDU_E29 = 56
_N_FAITS_PAR_PARAGRAPHE_ATTENDU_E29 = [11, 5, 11, 10, 10, 5, 4]
_TAILLE_FICHE_ATTENDUE_E29 = 26504


def _construire_fiche(chemin: Path) -> dict:
    fixture = json.loads(chemin.read_text(encoding="utf-8"))
    return build_report_facts(fixture["flights"], fixture)


def _construire_fiche_francfort() -> dict:
    return _construire_fiche(FIXTURE_PATH)


def _verifier_taille_fiche(
    fiche: dict,
    sha_attendu: str = _REPORT_FACTS_SHA_ATTENDU,
    n_faits_attendu: int = _N_FAITS_ATTENDU,
    repartition_attendue: list[int] = _N_FAITS_PAR_PARAGRAPHE_ATTENDU,
    taille_attendue: int = _TAILLE_FICHE_ATTENDUE,
) -> None:
    """Épingle la fiche seule : `report_facts_sha`, le nombre de faits et
    leur répartition par paragraphe, et la taille du JSON compact --
    quatre grandeurs qui bougent TOUTES ensemble dès qu'un lot touche
    `report_facts.py`, ou aucune si le lot ne le touche pas. Lot « La
    plume » : les quatre valeurs attendues se passent en argument, une
    fiche à la fois (Francfort par défaut)."""
    sha = fiche["report_facts_sha"]
    assert sha == sha_attendu, (
        f"report_facts_sha = {sha!r} (attendu {sha_attendu!r}) -- "
        "la fiche a changé. Si c'est le lot en cours qui le voulait, mets à "
        "jour _REPORT_FACTS_SHA_ATTENDU (et les constantes voisines "
        "ci-dessous) dans ce même commit ; sinon, un lot précédent ou ce "
        "lot-ci a touché report_facts.py sans le vouloir."
    )

    n_faits = fiche["counts"]["faits"]
    assert n_faits == n_faits_attendu, (
        f"faits = {n_faits} (attendu {n_faits_attendu}) -- "
        "mets à jour _N_FAITS_ATTENDU si le geste en cours en ajoute ou "
        "en retire délibérément."
    )

    repartition = [p["n_faits"] for p in fiche["paragraphes"]]
    assert repartition == repartition_attendue, (
        f"répartition par paragraphe = {repartition} "
        f"(attendu {repartition_attendue}) -- le découpage en "
        "paragraphes a changé ; mets à jour _N_FAITS_PAR_PARAGRAPHE_ATTENDU "
        "si c'est voulu."
    )

    taille = len(json.dumps(fiche, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    delta = taille - taille_attendue
    assert taille == taille_attendue, (
        f"taille de la fiche (JSON compact) = {taille} caractères "
        f"(attendu {taille_attendue}, delta {delta:+d}) -- la fiche a "
        "grossi ou maigri. Si ce lot le voulait, mets à jour "
        "_TAILLE_FICHE_ATTENDUE dans ce même commit, en indiquant le delta "
        "dans le rapport de livraison ; sinon, cherche ce qui a changé dans "
        "report_facts.py."
    )


def _verifier_taille_consigne() -> None:
    """Épingle la consigne seule (`_PROMPT_TEMPLATE`, jamais le prompt
    assemblé avec une fiche) -- son budget de règles (R117), indépendant
    de toute fixture."""
    taille = len(llm._PROMPT_TEMPLATE)
    delta = taille - _TAILLE_CONSIGNE_ATTENDUE
    assert taille == _TAILLE_CONSIGNE_ATTENDUE, (
        f"taille de _PROMPT_TEMPLATE = {taille} caractères "
        f"(attendu {_TAILLE_CONSIGNE_ATTENDUE}, delta {delta:+d}) -- la "
        "consigne a changé. Si ce lot ajoutait ou reformulait une règle "
        "délibérément, mets à jour _TAILLE_CONSIGNE_ATTENDUE dans ce même "
        "commit, en indiquant le delta dans le rapport de livraison ; "
        "sinon, une règle a bougé par inadvertance dans app/llm.py."
    )


def test_taille_fiche() -> None:
    """Un seul test pytest, deux vérifications INDÉPENDANTES l'une de
    l'autre (correctif §2, avertissement : jamais le prompt assemblé) --
    fiche et consigne restent deux mesures, deux jeux de constantes, deux
    messages d'échec distincts ; seule leur collecte par pytest est
    commune, pour ne pas gonfler le compte de tests d'un lot qui n'ajoute
    qu'un garde-fou. Lot « La plume » : deux fiches, Francfort et
    `e29ea43b`, chacune contre son propre jeu de constantes."""
    fiche = _construire_fiche_francfort()
    _verifier_taille_fiche(fiche)
    fiche_e29 = _construire_fiche(FIXTURE_E29_PATH)
    _verifier_taille_fiche(
        fiche_e29,
        _REPORT_FACTS_SHA_ATTENDU_E29,
        _N_FAITS_ATTENDU_E29,
        _N_FAITS_PAR_PARAGRAPHE_ATTENDU_E29,
        _TAILLE_FICHE_ATTENDUE_E29,
    )
    _verifier_taille_consigne()


if __name__ == "__main__":
    test_taille_fiche()
    print("OK -- test_taille_fiche")
