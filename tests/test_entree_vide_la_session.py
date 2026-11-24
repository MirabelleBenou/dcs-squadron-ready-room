"""Lot « L'entrée vide la session » (`v1.0071`, ARC-01) -- une entrée n'hérite
jamais des clés d'une autre : invité puis membre, ou membre puis invité, la
session ne garde que ce que pose la dernière fonction d'entrée.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.auth import _ouvrir_session, _ouvrir_session_invite
from app.main import ecriture_refusee

MAINTENANT = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
COMPTE_INVITE = {"id": "402871516337258497", "username": "tobi_dev", "global_name": "Tobias", "avatar": "abc123"}
PROFIL = SimpleNamespace(
    id=402871516337258497, global_name="Tobias", username="tobi_dev", locale="fr", avatar_hash="abc123",
)
CLES_MEMBRE = {"id", "name", "roles", "lang", "avatar", "squadron", "exp"}


def test_invite_puis_membre():
    requete = SimpleNamespace(session={})
    _ouvrir_session_invite(requete, COMPTE_INVITE, MAINTENANT)
    requete.session["_state_discord_x"] = "etranger"
    _ouvrir_session(requete, PROFIL, ["role"], "CHARLIE-33", MAINTENANT)
    assert set(requete.session) == CLES_MEMBRE
    assert "invite" not in requete.session and "_state_discord_x" not in requete.session
    assert not ecriture_refusee(requete.session, "POST")


def test_membre_puis_invite():
    requete = SimpleNamespace(session={})
    _ouvrir_session(requete, PROFIL, ["role"], "CHARLIE-33", MAINTENANT)
    requete.session["_state_discord_x"] = "etranger"
    _ouvrir_session_invite(requete, COMPTE_INVITE, MAINTENANT)
    assert set(requete.session) == CLES_MEMBRE | {"invite"}
    assert len(requete.session) == 8
    assert requete.session["invite"] is True and requete.session["squadron"] is None
    assert "_state_discord_x" not in requete.session
