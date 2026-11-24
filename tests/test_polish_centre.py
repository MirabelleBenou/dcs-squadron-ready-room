"""Lot « Polish du Centre » : le journal des modifications, le diagnostic d'accès et
`_callsign`, hors ligne -- ni base, ni réseau.

1. `test_ecarts_scalaires` -- un champ changé donne `avant`/`apres` ; un champ égal ne
   donne rien ; `None` vers une valeur donne `avant: None`.
2. `test_ecarts_listes` -- `["a","b"]` -> `["b","c"]` donne `ajoutes ["c"]` et
   `retires ["a"]` ; deux listes égales ne donnent rien.
3. `test_lisibles` -- `profile_ids` et `profile_id` sont nommés ; un identifiant
   inconnu reste tel quel ; `role_ids` n'est pas touché.
4. `test_diagnostic_adjoint_et_compte` -- le cas de Hunter, sur l'état de la base du
   banc : égal aux `droits` de la maquette validée.
5. `test_diagnostic_admin` -- huit droits par `admin` ; `relances.destinataire` à
   `None` sans rôle ni compte.
7. `test_callsign_sans_limite` -- trois préfixes empilés s'en vont tous ; un nom fait
   de préfixes seuls rend le nom d'origine.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.command.acces import DROITS, diagnostic
from app.command.journal import ecarts, lisibles
from app.events import _callsign

PILOTE = "111111111111111111"
OFFICIER = "444444444444444444"
SQN_ALPHA = "700000000000000102"
HUNTER = 200000000000000005
PORTEUR = 100000000000000001


def _etat(**surcharges) -> dict:
    """L'état du banc après `etat_banc_pol.sql` : le rôle Pilote porte `debrief.access`
    et `session.edit`, le rôle Officier `command.access` et `campaign.manage`, Hunter
    est nommé pour `event.create` ; la porte de l'application vient de la base."""
    etat = {
        "admins": {str(PORTEUR)},
        "app_roles": {PILOTE, "222222222222222222"},
        "roles_par_droit": {
            "debrief.access": {PILOTE},
            "session.edit": {PILOTE},
            "command.access": {OFFICIER},
            "campaign.manage": {OFFICIER},
        },
        "comptes_par_droit": {"event.create": {HUNTER}},
        "adjoint_de": None,
    }
    etat.update(surcharges)
    return etat


def test_ecarts_scalaires():
    assert ecarts({"a": 1, "b": 2}, {"a": 1, "b": 3}) == [{"champ": "b", "avant": 2, "apres": 3}]
    assert ecarts({"a": 1}, {"a": 1}) == []
    assert ecarts({}, {"a": "x"}) == [{"champ": "a", "avant": None, "apres": "x"}]
    assert ecarts({"a": None}, {"a": "x"}) == [{"champ": "a", "avant": None, "apres": "x"}]
    # l'ordre des lignes est celui d'`apres`
    assert [l["champ"] for l in ecarts({}, {"z": 1, "a": 2})] == ["z", "a"]


def test_ecarts_listes():
    assert ecarts({"l": ["a", "b"]}, {"l": ["b", "c"]}) == [
        {"champ": "l", "ajoutes": ["c"], "retires": ["a"]}
    ]
    assert ecarts({"l": ["a", "b"]}, {"l": ["a", "b"]}) == []
    assert ecarts({"l": ["a", "b"]}, {"l": ["b", "a"]}) == []
    # les éléments sont rendus en texte
    assert ecarts({"l": []}, {"l": [1]}) == [{"champ": "l", "ajoutes": ["1"], "retires": []}]


def test_lisibles():
    noms = {"1": "Viper", "2": "Ghost"}
    lignes = [
        {"champ": "profile_ids", "ajoutes": ["1", "9"], "retires": ["2"]},
        {"champ": "profile_id", "avant": None, "apres": "1"},
        {"champ": "role_ids", "ajoutes": ["1"], "retires": []},
        {"champ": "period", "avant": "1", "apres": "2"},
    ]
    assert lisibles(lignes, noms) == [
        {"champ": "profile_ids", "ajoutes": ["Viper", "9"], "retires": ["Ghost"]},
        {"champ": "profile_id", "avant": None, "apres": "Viper"},
        {"champ": "role_ids", "ajoutes": ["1"], "retires": []},
        {"champ": "period", "avant": "1", "apres": "2"},
    ]
    assert lignes[0]["ajoutes"] == ["1", "9"]   # les lignes reçues ne sont pas modifiées


# Les `droits` de Hunter dans la maquette validée (`MAQ_POL.acces`).
_HUNTER_MAQUETTE = [
    {"cle": "app.access", "accorde": True, "source": {"type": "role", "role_id": PILOTE}},
    {"cle": "command.access", "accorde": True, "source": {"type": "adjoint", "escadrille": "ALPHA-11"}},
    {"cle": "debrief.access", "accorde": True, "source": {"type": "role", "role_id": PILOTE}},
    {"cle": "event.create", "accorde": True, "source": {"type": "compte"}},
    {"cle": "event.edit_any", "accorde": False, "source": None},
    {"cle": "session.edit", "accorde": True, "source": {"type": "role", "role_id": PILOTE}},
    {"cle": "campaign.manage", "accorde": False, "source": None},
    {"cle": "campaign.delete", "accorde": False, "source": None},
    {"cle": "relances.destinataire", "accorde": False, "source": None},
]


def test_diagnostic_adjoint_et_compte():
    droits = diagnostic(HUNTER, [PILOTE, SQN_ALPHA], False, _etat(adjoint_de="ALPHA-11"))
    assert droits == _HUNTER_MAQUETTE
    assert [d["cle"] for d in droits] == list(DROITS)


def test_diagnostic_admin():
    droits = diagnostic(PORTEUR, [], False, _etat())
    par_cle = {d["cle"]: d for d in droits}
    admins = [d for d in droits if d["source"] == {"type": "admin"}]
    assert len(admins) == 8
    assert all(d["accorde"] for d in admins)
    assert par_cle["relances.destinataire"] == {"cle": "relances.destinataire", "accorde": False, "source": None}
    # un administrateur désigné nommément reçoit les relances, comme tout compte
    avec_compte = diagnostic(PORTEUR, [], False, _etat(comptes_par_droit={"relances.destinataire": {PORTEUR}}))
    assert avec_compte[-1]["source"] == {"type": "compte"}
    # un archivé n'est jamais destinataire
    assert diagnostic(PORTEUR, [], True, _etat(comptes_par_droit={"relances.destinataire": {PORTEUR}}))[-1]["source"] is None


def test_callsign_sans_limite():
    rx = re.compile(r"^\s*\[?\s*(?:1st EXAW|CHARLIE-33|BRAVO-22)\s*\]?\s*\|?\s*", re.I)
    assert _callsign("[1st EXAW] CHARLIE-33 | BRAVO-22 | Viper", rx) == "Viper"
    assert _callsign("[1st EXAW] CHARLIE-33 | BRAVO-22 | CHARLIE-33 | Ghost", rx) == "Ghost"
    assert _callsign("CHARLIE-33 | [1st EXAW]", rx) == "CHARLIE-33 | [1st EXAW]"
    assert _callsign("Viper", rx) == "Viper"
    assert _callsign("Viper", None) == "Viper"
