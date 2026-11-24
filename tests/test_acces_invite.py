"""Lot « L'accès invité » (`v1.0070`) -- une personne hors du serveur Discord de
l'escadre voit la Ready Room en lecture seule.

Neuf tests, un par règle du cadrage (R15), sans base ni réseau : le mur se
rejoue avec le `TestClient` de FastAPI sur `app.main.app` et un cookie de
session signé comme `SessionMiddleware` le signe (le lifespan ne tourne pas, le
mur répond avant le routage et ne lit pas la base) ; le reste, ce sont des
fonctions pures ou des sources lues.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
import warnings
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : il
# fausserait la ligne de `pytest`. On n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

import itsdangerous

from app.auth import (
    _ouvrir_session_invite,
    echeance_initiale,
    echeance_prolongee,
    identifiant_discord_valide,
    invitation_active,
)
from app.capabilities import est_invite, has_command_access, is_admin, require_debrief_access
from app.config import settings
from app.main import app, ecriture_refusee

RACINE = Path(__file__).resolve().parent.parent
MURMUR = {"detail": "Accès invité : lecture seule."}
LECTURE = ("GET", "HEAD", "OPTIONS")
ECRITURE = ("POST", "PUT", "PATCH", "DELETE")

# Un invité, tel que `get_current_user` le rend, et un membre sans rôle.
INVITE = {
    "id": "402871516337258497", "name": "Tobias", "roles": [], "lang": "fr",
    "avatar": None, "squadron": None, "invite": True,
    "invite_jusqua": "2026-12-04T10:00:00+00:00",
}
MEMBRE = {"id": "198347261540937728", "name": "Kestrel", "roles": []}


def _cookie(session: dict) -> str:
    """Le cookie de session, signé comme `SessionMiddleware` le signe."""
    donnees = b64encode(json.dumps(session).encode("utf-8"))
    return itsdangerous.TimestampSigner(str(settings.SESSION_SECRET)).sign(donnees).decode("utf-8")


def _routes_ecriture():
    """Les couples (méthode, chemin) de `app.routes` dont la méthode n'est ni
    GET, ni HEAD, ni OPTIONS -- les paramètres de chemin remplis."""
    couples = []
    for route in app.routes:
        for methode in sorted(set(getattr(route, "methods", None) or ()) - set(LECTURE)):
            couples.append((methode, re.sub(r"\{[^}]+\}", "1", route.path)))
    return couples


def test_le_mur_route_par_route():
    session = {"id": INVITE["id"], "invite": True, "roles": [], "exp": "2999-01-01T00:00:00+00:00"}
    en_tetes = {"cookie": f"session={_cookie(session)}"}
    client = TestClient(app, follow_redirects=False)
    eprouvees = 0
    for methode, chemin in _routes_ecriture():
        if (methode, chemin) == ("POST", "/auth/logout"):
            continue  # v1.0083, R7 : le mur laisse passer la déconnexion (vérifiée ci-dessous)
        reponse = client.request(methode, chemin, headers=en_tetes)
        assert reponse.status_code == 403, (methode, chemin)
        assert reponse.json() == MURMUR, (methode, chemin)
        eprouvees += 1
    assert eprouvees == 56
    assert client.post("/auth/logout", headers=en_tetes).status_code == 204
    # Le même cookie, en lecture, n'est pas arrêté par le mur.
    reponse = client.get("/outils/mission-plan", headers=en_tetes)
    assert reponse.status_code == 307


def test_ecriture_refusee():
    session = {"id": "1", "invite": True}
    for methode in ECRITURE:
        assert ecriture_refusee(session, methode) is True
    for methode in LECTURE:
        assert ecriture_refusee(session, methode) is False
    assert ecriture_refusee({"id": "1", "roles": []}, "POST") is False
    assert ecriture_refusee({"id": "1", "invite": False}, "POST") is False
    assert ecriture_refusee(None, "POST") is False


def test_invitation_active():
    maintenant = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    active = SimpleNamespace(revoque_le=None, jusqua=maintenant + timedelta(days=1))
    echue = SimpleNamespace(revoque_le=None, jusqua=maintenant - timedelta(seconds=1))
    revoquee = SimpleNamespace(revoque_le=maintenant, jusqua=maintenant + timedelta(days=1))
    assert invitation_active(active, maintenant) is True
    assert invitation_active(echue, maintenant) is False
    assert invitation_active(revoquee, maintenant) is False
    assert invitation_active(None, maintenant) is False


def test_les_echeances():
    maintenant = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    assert echeance_initiale(maintenant) == maintenant + timedelta(days=30)
    assert echeance_initiale(maintenant) == datetime(2026, 12, 4, 12, 0, tzinfo=timezone.utc)
    jusqua = datetime(2026, 12, 4, 12, 0, tzinfo=timezone.utc)
    assert echeance_prolongee(jusqua) == jusqua + timedelta(days=30)
    assert echeance_prolongee(jusqua) == datetime(2027, 1, 3, 12, 0, tzinfo=timezone.utc)


def test_identifiant_discord_valide():
    for bon in ("1" * 17, "1" * 18, "1" * 20, "  402871516337258497  "):
        assert identifiant_discord_valide(bon) is True, bon
    for mauvais in ("1" * 16, "1" * 21, "40287151633725849a", "", "   ", "4028715 16337258497"):
        assert identifiant_discord_valide(mauvais) is False, mauvais


def test_la_session_de_l_invite():
    requete = SimpleNamespace(session={})
    maintenant = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    compte = {"id": "402871516337258497", "username": "tobi_dev", "global_name": "Tobias", "avatar": "abc123"}
    _ouvrir_session_invite(requete, compte, maintenant)
    attendu = {
        "id": "402871516337258497", "name": "Tobias", "roles": [], "lang": "fr",
        "avatar": "abc123", "squadron": None,
        "exp": (maintenant + timedelta(days=settings.SESSION_TTL_DAYS)).isoformat(),
        "invite": True,
    }
    assert requete.session == attendu
    assert len(requete.session) == 8
    # Sans `global_name`, le nom est le `username` ; sans avatar, `None`.
    autre = SimpleNamespace(session={})
    _ouvrir_session_invite(autre, {"id": "5" * 18, "username": "tobi_dev"}, maintenant)
    assert autre.session["name"] == "tobi_dev" and autre.session["avatar"] is None


def test_les_portes_de_lecture():
    assert est_invite(INVITE) is True
    assert est_invite(MEMBRE) is False
    assert est_invite({"id": "1", "roles": [], "invite": False}) is False
    assert est_invite(None) is False
    assert not is_admin(INVITE)
    # Sans base : les deux portes laissent passer l'invité avant toute lecture.
    assert asyncio.run(has_command_access(None, INVITE)) is True
    assert asyncio.run(require_debrief_access(INVITE, None)) is INVITE


def test_les_textes_de_l_ecran():
    js = (RACINE / "app" / "static" / "app.js").read_text(encoding="utf-8")
    textes = {
        "invite_bandeau": ("Accès invité · démonstration en lecture seule — jusqu'au {date}", "Guest access · read-only demonstration — until {date}"),
        "invite_lecture_seule": ("Accès invité : lecture seule.", "Guest access: read only."),
        "cc_inv_title": ("Invités — démonstration", "Guests — demonstration"),
        "cc_inv_hint": (
            "Une personne hors du serveur Discord de l'escadre, autorisée par son identifiant Discord, pour lui montrer la Ready Room. Elle voit tout ce qu'un chef voit, <b>strictement en lecture seule</b>, et n'apparaît dans aucun tableau. Elle entre par « Se connecter avec Discord ».",
            "Someone outside the wing's Discord server, allowed in by their Discord ID, to show them the Ready Room. They see everything a leader sees, <b>strictly read-only</b>, and appear in no table. They sign in with \"Sign in with Discord\".",
        ),
        "cc_inv_hint_duree": ("Trente jours, prolongeables. Une révocation prend effet à son geste suivant.", "Thirty days, renewable. A revocation takes effect at their next action."),
        "cc_inv_id_label": ("Identifiant Discord", "Discord ID"),
        "cc_inv_verifier": ("Vérifier", "Check"),
        "cc_inv_compte": ("Compte Discord : <b>{nom}</b> (@{username}) ·", "Discord account: <b>{nom}</b> (@{username}) ·"),
        "cc_inv_inviter": ("Inviter pour 30 jours", "Invite for 30 days"),
        "cc_inv_col_invite": ("Invité", "Guest"),
        "cc_inv_col_id": ("Identifiant", "ID"),
        "cc_inv_col_par": ("Invité par", "Invited by"),
        "cc_inv_col_jusqua": ("Jusqu'au", "Until"),
        "cc_inv_col_entree": ("Dernière entrée", "Last sign-in"),
        "cc_inv_prolonger": ("Prolonger de 30 jours", "Extend by 30 days"),
        "cc_inv_revoquer": ("Révoquer", "Revoke"),
        "cc_inv_vide": ("Aucun invité.", "No guests."),
        "cc_inv_jamais": ("jamais", "never"),
        "cc_jr_a_invites_ajout": ("Invité ajouté", "Guest added"),
        "cc_jr_a_invites_prolongation": ("Invitation prolongée", "Guest access extended"),
        "cc_jr_a_invites_revocation": ("Invitation révoquée", "Guest access revoked"),
        "cc_jr_a_invites_entree": ("Entrée d'un invité", "Guest signed in"),
    }
    assert len(textes) == 22
    for cle, (fr, en) in textes.items():
        # La clé figure deux fois (français, anglais), chacune avec son texte.
        assert len(re.findall(rf"(?<!\w){cle}\s*:", js)) == 2, cle
        for valeur in (fr, en):
            assert f"{cle}:{json.dumps(valeur, ensure_ascii=False)}" in js, (cle, valeur)
    html = (RACINE / "app" / "static" / "index.html").read_text(encoding="utf-8")
    ordre = [html.index(f'id="{i}"') for i in ("blk-conn", "blk-invites", "blk-debrief")]
    assert ordre == sorted(ordre)
    assert html.count('class="guest-strip hidden"') == 2


def test_les_textes_du_serveur():
    def source(chemin):
        return (RACINE / chemin).read_text(encoding="utf-8")

    auth = source("app/auth.py")
    assert 'detail="Accès retiré"' in auth
    main = source("app/main.py")
    assert "Accès invité : lecture seule." in main
    api = source("app/command/api.py")
    for message in (
        "Réservé à l'administrateur.",
        "Identifiant Discord invalide : 17 à 20 chiffres.",
        "Ce compte est déjà connu de la Ready Room : c'est un membre, pas un invité.",
        "Discord ne répond pas : réessaie dans un instant.",
        "Aucun compte Discord ne porte cet identifiant.",
        "Cette personne est déjà invitée : prolonge son invitation.",
        "Invitation introuvable ou échue.",
    ):
        assert message in api, message
    for action in ("invites.ajout", "invites.prolongation", "invites.revocation"):
        assert f'"{action}"' in api, action
    assert '"invites.entree"' in auth
