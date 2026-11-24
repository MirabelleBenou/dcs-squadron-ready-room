"""Lot « La connexion de secours » (R325) : les deux portes de secours, hors ligne
-- ni base, ni réseau.

1. `test_jeton` -- deux jetons diffèrent, chacun d'au moins 43 caractères URL-safe ;
   l'empreinte est le SHA-256 hexadécimal (64 caractères) du jeton.
2. `test_url` -- `BASE_URL` avec ou sans `/` final donne la même URL, jeton dans le
   fragment.
3. `test_reponse_commande` -- la réponse à l'interaction, clé pour clé.
4. `test_commande` -- la définition de la commande ; sa description tient en 100
   caractères.
5. `test_page_de_refus` -- `noaccess.html` : le motif, l'échappement du nom, la phrase
   `/readyroom` si et seulement si `commande` est vrai.
6. `test_gardes_de_l_emission` -- la route d'émission du Centre : non administrateur
   `403` sans toucher la base ; profil absent `404`.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import connexion_secours as cs
from app import langue
from app.auth import templates
from app.command.api import post_member_lien_secours
from app.config import settings


def test_jeton():
    a, b = cs.nouveau_jeton(), cs.nouveau_jeton()
    assert a != b
    for jeton in (a, b):
        assert re.fullmatch(r"[A-Za-z0-9_-]{43,}", jeton)
        empreinte = cs.empreinte(jeton)
        assert re.fullmatch(r"[0-9a-f]{64}", empreinte)
        assert empreinte == hashlib.sha256(jeton.encode()).hexdigest()


def test_url(monkeypatch):
    attendu = "https://rr.example.org/auth/lien#abc"
    monkeypatch.setattr(settings, "BASE_URL", "https://rr.example.org/")
    assert cs.url_du_lien("abc") == attendu
    monkeypatch.setattr(settings, "BASE_URL", "https://rr.example.org")
    assert cs.url_du_lien("abc") == attendu


def test_reponse_commande():
    url = "https://x/auth/lien#t"
    assert cs.reponse_commande(url, "fr") == {
        "type": 4,
        "data": {
            "flags": 68,
            "content": "Ton lien d'entrée dans la Ready Room : valable 5 minutes, une seule fois. Ne le partage pas.",
            "components": [
                {
                    "type": 1,
                    "components": [
                        {
                            "type": 2,
                            "style": 5,
                            "label": "Entrer dans la Ready Room",
                            "url": url,
                        }
                    ],
                }
            ],
            "allowed_mentions": {"parse": []},
        },
    }


def test_commande():
    commande = cs.commande_readyroom()
    assert commande == {
        "name": "readyroom",
        "type": 1,
        "description": "Get a link to enter the Ready Room when Discord sign-in fails",
        "description_localizations": {
            "fr": "Recevoir un lien pour entrer dans la Ready Room, si la connexion Discord ne passe pas"
        },
    }
    assert len(commande["description"]) <= 100


def _page(**contexte) -> str:
    base = {
        "nom": "Pilote", "identifiant": "pilote", "motif": "sans_role", "commande": False,
        "lang": "fr", "t": langue.textes("fr"),
    }
    base.update(contexte)
    return templates.get_template("noaccess.html").render(**base)


def test_page_de_refus():
    non_membre = "Ce compte n'est pas membre du serveur Discord de l'escadre."
    sans_role = "Ce compte n'a aucun rôle qui ouvre la Ready Room."
    page = _page(motif="non_membre")
    assert non_membre in page and sans_role not in page
    page = _page(motif="sans_role")
    assert sans_role in page and non_membre not in page
    # Le nom est échappé, jamais rendu tel quel.
    page = _page(nom="<b>X</b>")
    assert "&lt;b&gt;X&lt;/b&gt;" in page and "<b>X</b>" not in page
    # La phrase de la commande, si et seulement si `commande` est vrai.
    phrase = "Tu peux aussi taper /readyroom dans le serveur Discord de l'escadre"
    assert phrase in _page(commande=True)
    assert phrase not in _page(commande=False)


class _BaseInterdite:
    """Un faux `db` qui refuse tout : la garde doit tomber avant la base."""

    def __getattr__(self, nom):
        raise AssertionError(f"accès à la base avant la garde : {nom}")


class _BaseSansProfil:
    async def get(self, *_args, **_kwargs):
        return None


def test_gardes_de_l_emission(monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_IDS", "100000000000000001")
    with pytest.raises(HTTPException) as e:
        asyncio.run(post_member_lien_secours(7, {"id": "200000000000000009"}, _BaseInterdite()))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        asyncio.run(post_member_lien_secours(7, {"id": "100000000000000001"}, _BaseSansProfil()))
    assert e.value.status_code == 404
