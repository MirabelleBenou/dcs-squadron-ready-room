"""Lot « La plume » (`v1.0045`) -- la fiche du récit et ses plafonds.

Neuf tests, un par règle du cadrage (§3 à §5) : les libellés du Centre et
l'empreinte, le nouvel appareil, l'enchaînement, la clôture avant la fin, la
série sans compte, les coups regroupés, les camps retirés, les plafonds.
Lot « Les quatre dernières dettes » (`v1.0046`) : deux de plus, les cibles des
séries et les cinq remplacements de la consigne.

Fixtures : « Bataille de Francfort » (`89f20c83`), la session de production du
27 juillet (`e29ea43b`), et `996a3529`, le cas réel du regroupement des coups
(six paragraphes « à 22:19 » faits des tirs des mêmes M-113). Aucune base,
aucune clé API : `build_report_facts` est pure, appelée avec deux arguments
positionnels, et le troisième -- `libelles` -- quand le test en a besoin.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import llm
from app.debrief import api as debrief_api
from app.debrief import lexique
from app.debrief import report_facts
from app.debrief.report_facts import build_report_facts

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
FRANCFORT = _FIXTURES / "89f20c83-54ec-4fd4-bf0c-1700463ff155.json"
E29 = _FIXTURES / "e29ea43b-2029-47c3-88cb-225596bf1dca.json"
S996 = _FIXTURES / "996a3529-58c3-4451-a866-f0af208e9609.json"

_SHTURM = "9M114 Shturm (AT-6 Spiral)"
_LIBELLES = {
    "types": {"Grad_FDDM": "PC de tir Grad", "F-4E-45MC": "Phantom"},
    "armes": {_SHTURM: "Shturm"},
}


def _fiche(chemin: Path, libelles: dict | None = None) -> dict:
    fixture = json.loads(chemin.read_text(encoding="utf-8"))
    if libelles is None:
        return build_report_facts(fixture["flights"], fixture)
    return build_report_facts(fixture["flights"], fixture, libelles)


def _fiche_sans_regroupement(chemin: Path) -> dict:
    """La même fiche, la passe du §3.6 neutralisée : l'état « avant »."""
    with patch.object(report_facts, "_regrouper_coups", lambda coups: list(coups)):
        return _fiche(chemin)


def _cles_a_toute_profondeur(noeud) -> list[str]:
    cles: list[str] = []
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            cles.append(cle)
            cles.extend(_cles_a_toute_profondeur(valeur))
    elif isinstance(noeud, list):
        for element in noeud:
            cles.extend(_cles_a_toute_profondeur(element))
    return cles


def _roles(fact: dict) -> list[tuple[str, str | None]]:
    """(clé du drapeau, nom) pour chaque protagoniste d'un fait."""
    if fact["kind"] == "duel":
        return [
            ("auteur_nouvel_appareil", fact.get("auteur_nom")),
            ("victime_nouvel_appareil", fact.get("victime_nom")),
        ]
    return [("nouvel_appareil", fact.get("nom"))]


def _vol(object_id: str, kills: list[dict], phases: list[dict]) -> dict:
    """Un vol nommé minimal, de la forme de `_flight_to_dict`."""
    return {
        "object_id": object_id,
        "coalition": "2",
        "aircraft_type": "Mi-24P",
        "identity_state": "nomme",
        "pilot_callsign": f"Pilote{object_id}",
        "pilote_profile_id": f"p{object_id}",
        "t_start": 0.0,
        "t_end": 1000.0,
        "stats": {"kills": kills, "phases": phases, "threat_log": []},
    }


def test_libelles_du_centre() -> None:
    fiche = _fiche(E29, _LIBELLES)
    facts = fiche["facts"]

    cles_type = ("target_unit_type", "initiator_unit_type", "aircraft_type")
    vus_grad = 0
    vus_lexique = 0
    for fact in facts:
        for cle in cles_type:
            if f"{cle}_libelle" not in fact:
                continue
            brute = fact.get(cle)
            if brute == "Grad_FDDM":
                assert fact[f"{cle}_libelle"] == "PC de tir Grad"
                vus_grad += 1
            elif brute == "F-4E-45MC":
                assert fact[f"{cle}_libelle"] == "Phantom"
            else:
                assert fact[f"{cle}_libelle"] == lexique.resoudre(brute), (cle, brute)
                vus_lexique += 1
    assert vus_grad > 0 and vus_lexique > 0

    anonymes = sorted({
        nom for fact in facts for _, nom in _roles(fact)
        if nom and "anonyme" in nom
    })
    assert anonymes, "aucun vol anonyme dans la fiche"
    assert all(nom.startswith("Vol Phantom anonyme n° ") for nom in anonymes), anonymes

    shturm_faits = [f for f in facts if f.get("weapon") == _SHTURM]
    shturm_coups = [
        c for f in facts for c in f.get("coups_recus") or [] if c.get("weapon") == _SHTURM
    ]
    assert len(shturm_faits) == 4 and len(shturm_coups) == 1
    assert all(f["weapon_libelle"] == "Shturm" for f in shturm_faits + shturm_coups)

    for fact in facts:
        porteurs = [fact] if "weapon" in fact else []
        porteurs += list(fact.get("coups_recus") or [])
        for porteur in porteurs:
            assert "weapon_libelle" in porteur, porteur
            if porteur["weapon"] != _SHTURM:
                assert porteur["weapon_libelle"] == porteur["weapon"]


def test_libelle_change_l_empreinte() -> None:
    sha = _fiche(E29, _LIBELLES)["report_facts_sha"]
    change = {
        "types": {**_LIBELLES["types"], "Grad_FDDM": "PC Grad"},
        "armes": dict(_LIBELLES["armes"]),
    }
    assert _fiche(E29, change)["report_facts_sha"] != sha

    sans = _fiche(E29)["report_facts_sha"]
    absent = {"types": {"Cle-absente-de-la-fiche": "Rien"}, "armes": {"Arme-absente": "Rien"}}
    assert _fiche(E29, absent)["report_facts_sha"] == sans


def test_nouvel_appareil() -> None:
    fiche = _fiche(FRANCFORT)
    vrais = sum(
        1 for fact in fiche["facts"] for cle, _ in _roles(fact) if fact[cle] is True
    )
    assert vrais == 11

    cles = set(_cles_a_toute_profondeur(fiche))
    assert "machine" not in cles and "machines" not in cles

    vus: set[str] = set()
    for fact in fiche["facts"]:
        roles = _roles(fact)
        for cle, nom in roles:
            assert isinstance(fact[cle], bool)
            if nom is None or nom not in vus:
                assert fact[cle] is False, (cle, nom)
        vus.update(nom for _, nom in roles if nom is not None)


def test_enchaine() -> None:
    facts = _fiche(FRANCFORT)["facts"]
    assert facts[0]["enchaine"] is False
    enchaines = 0
    for precedent, fact in zip(facts, facts[1:]):
        assert isinstance(fact["enchaine"], bool)
        if not fact["enchaine"]:
            continue
        enchaines += 1
        assert fact["dire_heure"] is False
        fin = precedent.get("t_end")
        fin = fin if fin is not None else precedent["t"]
        assert 0 <= fact["t"] - fin < 90
    assert enchaines == 12


def test_cloture_avant_fin() -> None:
    assert _fiche(FRANCFORT)["ouverture_cloture"]["dernier_atterrissage_avant_fin"] is True

    mission = {"id": "m", "title": "Essai", "reference_time": None}
    kill = {"t": 100.0, "weapon": "Canon", "target_object_id": "x", "target_unit_type": "BMP-1"}

    sans_atterrissage = build_report_facts(
        [_vol("1", [kill], [{"t": 50.0, "type": "takeoff"}])], mission,
    )
    assert sans_atterrissage["facts"]
    assert sans_atterrissage["ouverture_cloture"]["dernier_atterrissage_avant_fin"] is False

    atterrissage_apres = build_report_facts(
        [_vol("1", [kill], [{"t": 50.0, "type": "takeoff"}, {"t": 200.0, "type": "land"}])],
        mission,
    )
    assert atterrissage_apres["facts"]
    assert atterrissage_apres["ouverture_cloture"]["dernier_atterrissage_avant_fin"] is False


def test_serie_sans_compte() -> None:
    series = duels = 0
    for chemin in (FRANCFORT, E29):
        for paragraphe in _fiche(chemin)["paragraphes"]:
            for entree in paragraphe["marqueurs"]["serie"] or []:
                series += 1
                assert "rafale" not in entree and "acteur" in entree
            for entree in paragraphe["marqueurs"]["duel"] or []:
                duels += 1
                assert "echanges" in entree
    assert series > 0 and duels > 0


def test_coups_regroupes() -> None:
    avant = _fiche_sans_regroupement(S996)
    apres = _fiche(S996)
    coups_avant = [f for f in avant["facts"] if f["kind"] == "coup"]
    coups_apres = [f for f in apres["facts"] if f["kind"] == "coup"]
    assert (len(avant["facts"]), len(apres["facts"])) == (60, 14)
    assert (len(coups_avant), len(coups_apres)) == (56, 10)
    assert (len(avant["paragraphes"]), len(apres["paragraphes"])) == (8, 2)
    assert [p["n_faits"] for p in apres["paragraphes"]] == [9, 5]
    assert sum(c["count"] for c in coups_avant) == sum(c["count"] for c in coups_apres)

    avant = _fiche_sans_regroupement(E29)
    apres = _fiche(E29)
    coups_avant = [f for f in avant["facts"] if f["kind"] == "coup"]
    coups_apres = [f for f in apres["facts"] if f["kind"] == "coup"]
    assert (len(coups_avant), len(coups_apres)) == (21, 16)
    assert apres["counts"]["coups_regroupes"] == 5
    assert sum(c["count"] for c in coups_avant) == sum(c["count"] for c in coups_apres)

    for chemin in (S996, E29):
        coups = sorted(
            (f for f in _fiche(chemin)["facts"] if f["kind"] == "coup"), key=lambda c: c["t"],
        )
        for i, premier in enumerate(coups):
            if premier["initiator_object_id"] is None:
                continue
            for second in coups[i + 1:]:
                if (
                    second["object_id"] == premier["object_id"]
                    and second["initiator_object_id"] == premier["initiator_object_id"]
                    and second["weapon"] == premier["weapon"]
                ):
                    assert second["t"] - premier["t_end"] >= 180

    inconnus = [
        {"t": 10.0, "t_end": 10.0, "count": 1, "object_id": "1",
         "initiator_object_id": None, "initiator_unit_type": None, "weapon": None},
        {"t": 20.0, "t_end": 20.0, "count": 1, "object_id": "1",
         "initiator_object_id": None, "initiator_unit_type": None, "weapon": None},
    ]
    assert len(report_facts._regrouper_coups(inconnus)) == 2


def test_camps_retires() -> None:
    noms = ("camp_nom", "dire_camp", "coalition")
    for chemin in (FRANCFORT, E29):
        fiche = _fiche(chemin)
        assert "camps" not in fiche
        for cle in _cles_a_toute_profondeur(fiche):
            assert cle != "camps"
            assert not any(cle == nom or cle.endswith("_" + nom) for nom in noms), cle
    assert "bleu" not in llm._PROMPT_TRADUCTION_TEMPLATE
    assert not hasattr(report_facts, "_compute_camps")
    assert not hasattr(report_facts, "_apply_camp_noms")


def test_plafonds() -> None:
    assert llm._TIMEOUT_S == 600.0
    assert llm._MAX_TOKENS == 64000
    assert llm.MONTHLY_CALL_CAP == 300
    assert debrief_api.REDACTION_PEREMPTION_MIN == 26
    chaine = (
        2 * llm._TIMEOUT_S + llm._RETRY_DELAY_S
        + 2 * llm._TIMEOUT_TRADUCTION_S + llm._RETRY_DELAY_S
    )
    assert chaine == 1323.0
    assert debrief_api.REDACTION_PEREMPTION_MIN * 60 - chaine > 3 * 60


# --- Lot « Les quatre dernières dettes » (`v1.0046`) ------------------------

# Les cibles de chaque série, dans l'ordre des paragraphes puis des entrées
# (cadrage §3.2), sans libellés du Centre.
_CIBLES_ATTENDUES = {
    FRANCFORT: [2, 3, 2, 2, 2, 2],
    E29: [3, 3, 5, 3, 7, 2, 4],
    S996: [4],
}


def test_cibles_des_series() -> None:
    for chemin, attendu in _CIBLES_ATTENDUES.items():
        cibles = [
            entree["cibles"]
            for paragraphe in _fiche(chemin)["paragraphes"]
            for entree in paragraphe["marqueurs"]["serie"] or []
        ]
        assert cibles == attendu, f"{chemin.name[:8]} : {cibles} (attendu {attendu})"


# Les cinq remplacements de la consigne (cadrage §3.3), ancien puis nouveau.
_REMPLACEMENTS_CONSIGNE = [
    (
        "« dans la foulée » ou « aussitôt » seulement si son drapeau \"enchaine\" vaut true, « peu après » ou « quelques minutes plus tard » sinon",
        "une liaison d'immédiateté (« dans la foulée », « aussitôt », « sans attendre », « dans le même élan ») seulement si son drapeau \"enchaine\" vaut true, « peu après » ou « quelques minutes plus tard » sinon ; une liaison n'est jamais obligatoire -- deux faits enchaînés peuvent se suivre sans mot de liaison, par la seule succession des phrases --, et la même liaison ne revient jamais deux fois dans un paragraphe",
    ),
    (
        "dis-le d'un mot (« reparti sur un nouvel appareil »)",
        "dis-le d'un mot porté par un verbe conjugué ou par l'appareil, jamais par un participe qui s'accorderait à la personne (« MistyKestrel42 repart sur un nouvel appareil », « sur un nouvel appareil, MistyKestrel42… » ; jamais « reparti » ni « repartie »)",
    ),
    (
        "(exemple à proscrire : « trois pilotes abattus en dix-huit minutes » -- c'est une somme).",
        "(exemple à proscrire : « trois pilotes abattus en dix-huit minutes » -- c'est une somme). Cela vaut pour les cibles : ne dénombre jamais toi-même les faits ni les cibles d'un paragraphe, d'une série ou d'un engagement. Le seul nombre permis pour un ensemble de faits est le champ \"cibles\" d'un marqueur \"serie\", déjà calculé : recopie-le tel quel s'il éclaire, jamais un autre ; le dire compte comme la mention de marqueur du paragraphe, une seule au plus (exemples à proscrire : « six cibles au sol neutralisées », « trois blindés dans cet engagement », « la série se poursuit à trois »).",
    ),
    (
        "et pour \"duel\" un compte, \"echanges\")",
        "pour \"duel\" un compte, \"echanges\", et pour \"serie\" le nombre exact de cibles qu'elle détruit, \"cibles\")",
    ),
    (
        "ce qui est proscrit, c'est d'attribuer un genre à une personne nommée, jamais la grammaire générique.",
        "ce qui est proscrit, c'est d'attribuer un genre à une personne nommée, jamais la grammaire générique. De même, aucun participe apposé à une personne nommée : écris « l'appareil de GRIFFON, touché par un AIM-9JULI, … », jamais « Touché par un AIM-9JULI, GRIFFON… ».",
    ),
]


def test_consigne_quatre_dettes() -> None:
    consigne = llm._PROMPT_TEMPLATE
    for _, nouveau in _REMPLACEMENTS_CONSIGNE:
        assert consigne.count(nouveau) == 1, nouveau[:60]
    # Deux nouveaux textes (le compte, le participe) commencent par l'ancien,
    # qu'ils prolongent : l'ancien ne doit plus figurer HORS de son
    # remplacement.
    reste = consigne
    for _, nouveau in _REMPLACEMENTS_CONSIGNE:
        reste = reste.replace(nouveau, "")
    for ancien, _ in _REMPLACEMENTS_CONSIGNE:
        assert ancien not in reste, ancien[:60]
