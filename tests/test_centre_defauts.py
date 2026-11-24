"""Lot « Le Centre de Commandement dit ce qu'il fait » : le rang de commandement servi à
l'écran, les textes du Centre et ses attributs, hors ligne -- ni base, ni réseau.

1. `test_chef_et_centre` -- `_chef_a_le_centre` (R3) : administrateur sans le rôle -> vrai ;
   rôle des chefs dans les rôles relevés -> vrai ; sans -> faux ; rôle non configuré, non
   administrateur -> faux.
2. `test_rang_chef_et_adjoint` -- `_command_rank` (R1) et `_deputy_squadron_id` (R2) : une
   appartenance ouverte de rang chef ou adjoint sur une escadrille active.
3. `test_rang_absent` -- simple membre, rien, appartenance close, escadrille en sommeil :
   `None`, et `deputy_squadron_id` nul.
4. `test_textes_du_serveur` -- le refus de R5 ; `put_relances` ne lève plus de 400 (R6).
5. `test_textes_de_l_ecran` -- les neuf clés neuves en français et en anglais ; les cinq
   phrases périmées ont disparu de `app.js` et d'`index.html` (R13).
6. `test_attributs` -- les huit `data-i18n-aria` (R11.3) et les deux `data-i18n-title` (R11.5).
"""
from __future__ import annotations

import inspect
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import api as api_mod
from app.command import api as command_api

STATIC = Path(__file__).resolve().parent.parent / "app" / "static"
APP_JS = (STATIC / "app.js").read_text(encoding="utf-8")
INDEX = (STATIC / "index.html").read_text(encoding="utf-8")

CHEF_ROLE = "900000000000000001"
ADMINS = {"100000000000000001"}


def test_chef_et_centre():
    f = command_api._chef_a_le_centre
    # administrateur, même sans le rôle des chefs
    assert f(100000000000000001, [], CHEF_ROLE, ADMINS) is True
    # le rôle des chefs figure dans les rôles relevés (texte ou nombre)
    assert f(200000000000000001, ["1", CHEF_ROLE], CHEF_ROLE, ADMINS) is True
    assert f(200000000000000001, [int(CHEF_ROLE)], CHEF_ROLE, ADMINS) is True
    # sans le rôle, ou sans relevé
    assert f(200000000000000001, ["1", "2"], CHEF_ROLE, ADMINS) is False
    assert f(200000000000000001, None, CHEF_ROLE, ADMINS) is False
    # rôle des chefs non configuré, non administrateur
    assert f(200000000000000001, ["1", CHEF_ROLE], None, ADMINS) is False
    assert f(200000000000000001, ["1", CHEF_ROLE], "", ADMINS) is False


def test_rang_chef_et_adjoint():
    chef = [("leader", None, "actif", "ALPHA-11")]
    assert api_mod._command_rank(chef) == {"rank": "leader", "squadron": "ALPHA-11"}
    adjoint = [("deputy", None, "actif", "BRAVO-22")]
    assert api_mod._command_rank(adjoint) == {"rank": "deputy", "squadron": "BRAVO-22"}
    # l'identifiant de l'escadrille de l'adjoint (R2) ; un chef n'en a pas
    assert command_api._deputy_squadron_id([("deputy", None, "actif", 7)]) == 7
    assert command_api._deputy_squadron_id([("leader", None, "actif", 7)]) is None
    # l'appartenance ouverte est choisie parmi des appartenances closes
    mix = [("leader", "2026-01-01", "actif", "A"), ("deputy", None, "actif", "B")]
    assert api_mod._command_rank(mix) == {"rank": "deputy", "squadron": "B"}
    assert command_api._deputy_squadron_id([("deputy", "2026-01-01", "actif", 3), ("deputy", None, "actif", 4)]) == 4


def test_rang_absent():
    assert api_mod._command_rank([]) is None
    assert api_mod._command_rank([("member", None, "actif", "ALPHA-11")]) is None
    # appartenance close
    assert api_mod._command_rank([("leader", "2026-01-01", "actif", "ALPHA-11")]) is None
    # escadrille en sommeil
    assert api_mod._command_rank([("leader", None, "sommeil", "ALPHA-11")]) is None
    assert api_mod._command_rank([("deputy", None, "sommeil", "ALPHA-11")]) is None
    # et l'identifiant d'adjoint reste nul dans les mêmes cas
    assert command_api._deputy_squadron_id([]) is None
    assert command_api._deputy_squadron_id([("member", None, "actif", 1)]) is None
    assert command_api._deputy_squadron_id([("deputy", "2026-01-01", "actif", 1)]) is None
    assert command_api._deputy_squadron_id([("deputy", None, "sommeil", 1)]) is None


def test_textes_du_serveur():
    source = inspect.getsource(command_api)
    assert "Ce membre ne porte pas le rôle Discord des chefs au dernier relevé (connexion ou appel)." in source
    assert "à sa dernière connexion" not in source
    relances = inspect.getsource(command_api.put_relances)
    assert "status_code=400" not in relances
    assert relances.count("status_code=422") == 2


CLES_NEUVES = (
    "cc_station_sans_role",
    "cc_station_sans_role_toast",
    "cc_rights_chef_sans_role_opt",
    "cc_rights_chef_sans_role",
    "cc_rights_partial_sans_role",
    "cc_rights_deputy_note",
    "cc_rights_content_camp_reload_hint",
    "cc_camp_field_desc",
    "cc_rights_chip_remove",
)

PERIMES = (
    "redeviennent Free Agents",
    "Elle rattachera ses membres à leur prochaine connexion",
    "seuls les administrateurs entrent",
    "déjà connectés au moins une fois",
    "depuis quatre semaines",
)


def test_textes_de_l_ecran():
    for cle in CLES_NEUVES:
        assert len(re.findall(r'(?m)^\s+%s:"' % re.escape(cle), APP_JS)) == 2, cle
    for phrase in PERIMES:
        assert phrase not in APP_JS, phrase
        assert phrase not in INDEX, phrase


def _balise(motif: str) -> str:
    m = re.search(motif, INDEX)
    assert m, motif
    return m.group(0)


def test_attributs():
    huit = (
        ("cc-sqn-new-desig", "cc_sqn_col_designation"),
        ("cc-sqn-new-callsign", "cc_sqn_col_callsign"),
        ("cc-sqn-new-fullname", "cc_sqn_col_fullname"),
        ("cc-camp-name", "cc_camp_field_name_ph"),
        ("cc-camp-sim", "cc_camp_col_sim"),
        ("cc-camp-theater", "cc_camp_col_theater"),
        ("cc-camp-status", "cc_camp_col_status"),
        ("cc-camp-desc", "cc_camp_field_desc"),
        ("cc-mbr-q", "cc_mbr_search_ph"),
    )
    for ident, cle in huit:
        balise = _balise(r'<(?:input|select)[^>]*\bid="%s"[^>]*>' % re.escape(ident))
        assert 'data-i18n-aria="%s"' % cle in balise, ident
    # 10 : les neuf champs, plus le « ? » de la barre (lot v1.0063).
    assert INDEX.count("data-i18n-aria=") == 10
    for nav, cle in (("referentiels", "cc_ref_title"), ("archives", "cc_arch_title")):
        balise = _balise(r'<button[^>]*data-cc-nav="%s"[^>]*>' % nav)
        assert 'data-i18n-title="%s"' % cle in balise, nav
    # 3 : « Réf » et « Arch », plus le « ? » de la barre (lot v1.0063).
    assert INDEX.count("data-i18n-title=") == 3
