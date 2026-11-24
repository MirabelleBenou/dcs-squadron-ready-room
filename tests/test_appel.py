"""Lot « L'appel » : la lecture des réponses de Discord, le prédicat de la
porte, la collecte tout-ou-rien et le compte rendu (`app/appel.py`), hors
ligne -- ni base, ni réseau.

1. `test_lecture` -- 200 rend les rôles ; 404 « membre inconnu » (10007) ou
   « compte supprimé » (10013) rend None ; tout autre 404, un 500, un 429, un
   401, un corps illisible ou un Discord injoignable interrompent l'appel.
2. `test_peut_entrer` -- présent et porteur d'un rôle de la porte ; parti,
   ou présent sans rôle de la porte : jamais.
3. `test_collecte_tout_ou_rien` -- tout se lit, dans l'ordre ; une lecture
   qui interrompt remonte telle quelle, et rien n'est rendu.
4. `test_compte_rendu` -- le cas réel du 30 septembre : Kerberos sort,
   Fog-fr et Hunter-fr passent au ALPHA-11, personne ne revient ; puis un
   retour et un passage en Free Agent.
5. `test_arrivees` -- lot « L'effectif complet » (R195), le cas réel du
   2 octobre : BANSHEE arrive au CHARLIE-33 ; puis une arrivée en Free Agent.
6. `test_liste_incomplete` -- un absent de la liste que sa lecture directe
   dit présent la contredit ; un parti (None) ou un archivé, jamais.
7. `test_lister_serveur` -- les pages s'enchaînent par le plus grand
   identifiant ; un refus, une liste vide, un Discord injoignable rendent
   un motif, jamais une exception.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.appel as appel
from app.appel import (FA, HORS, AppelInterrompu, collecter, compte_rendu, lecture,
                       liste_incomplete, lister_serveur, peut_entrer)


def test_lecture():
    assert lecture(200, {"roles": [111, "222"]}) == {"111", "222"}
    assert lecture(200, {"user": {"id": "1"}}) == set()
    assert lecture(404, {"code": 10007}) is None
    assert lecture(404, {"code": 10013}) is None
    for statut, corps in ((404, {"code": 10004}), (500, {}), (429, {"retry_after": 1}),
                          (401, {"code": 0}), (200, None), (None, None)):
        with pytest.raises(AppelInterrompu):
            lecture(statut, corps)


def test_peut_entrer():
    porte = {"900", "901"}
    assert peut_entrer(424242, {"900"}, porte)
    assert peut_entrer(424242, {"111", "901"}, porte)
    assert not peut_entrer(424242, {"111"}, porte)
    assert not peut_entrer(424242, set(), porte)
    assert not peut_entrer(424242, None, porte)


def test_collecte_tout_ou_rien():
    lus = []

    async def lire(pid):
        lus.append(pid)
        return {str(pid)}

    assert asyncio.run(collecter([3, 1, 2], lire, pause=0)) == {3: {"3"}, 1: {"1"}, 2: {"2"}}
    assert lus == [3, 1, 2]

    async def lire_coupe(pid):
        if pid == 2:
            raise AppelInterrompu("Discord injoignable")
        return set()

    with pytest.raises(AppelInterrompu):
        asyncio.run(collecter([1, 2, 3], lire_coupe, pause=0))


def test_compte_rendu():
    noms = {1: "Kerberos", 2: "Hunter-fr", 3: "Fog-fr", 4: "Scorpio", 5: "Golem"}
    avant = {1: FA, 2: FA, 3: FA, 4: FA, 5: "ALPHA-11"}
    apres = {1: HORS, 2: "ALPHA-11", 3: "ALPHA-11", 4: FA, 5: "ALPHA-11"}
    assert compte_rendu(avant, apres, noms) == {
        "sortent": ["Kerberos"],
        "bougent": [{"vers": "ALPHA-11", "noms": ["Fog-fr", "Hunter-fr"]}],
        "reviennent": [],
        "arrivent": [],
    }
    assert compte_rendu({1: HORS, 5: "ALPHA-11"}, {1: FA, 5: FA}, noms) == {
        "sortent": [],
        "bougent": [{"vers": None, "noms": ["Golem"]}],
        "reviennent": ["Kerberos"],
        "arrivent": [],
    }


def test_arrivees():
    noms = {1: "CHARLIE-33 | thorn", 2: "Golem", 9: "CHARLIE-33 | BANSHEE", 10: "Nomad"}
    avant = {1: "CHARLIE-33", 2: "ALPHA-11"}
    apres = {1: "CHARLIE-33", 2: "ALPHA-11", 9: "CHARLIE-33"}
    assert compte_rendu(avant, apres, noms) == {
        "sortent": [], "bougent": [], "reviennent": [],
        "arrivent": [{"vers": "CHARLIE-33", "noms": ["CHARLIE-33 | BANSHEE"]}],
    }
    assert compte_rendu(avant, {**apres, 10: FA}, noms)["arrivent"] == [
        {"vers": "CHARLIE-33", "noms": ["CHARLIE-33 | BANSHEE"]},
        {"vers": None, "noms": ["Nomad"]},
    ]


def test_liste_incomplete():
    avant = {1: "CHARLIE-33", 2: FA, 3: HORS}
    assert not liste_incomplete({1, 2}, avant, {1: {"7"}, 2: {"8"}, 3: None})
    assert not liste_incomplete({1}, avant, {1: {"7"}, 2: None, 3: None})
    assert not liste_incomplete({1, 2}, avant, {1: {"7"}, 2: {"8"}, 3: {"9"}})
    assert liste_incomplete({1}, avant, {1: {"7"}, 2: {"8"}, 3: None})


class _Reponse:
    def __init__(self, statut, corps):
        self.status_code, self._corps = statut, corps

    def json(self):
        return self._corps


def test_lister_serveur(monkeypatch):
    serveur = [{"user": {"id": str(i), "username": f"u{i}"}, "roles": []} for i in (5, 3, 8, 1, 9)]
    demandes = []

    async def faux(methode, chemin, **_):
        demandes.append(chemin)
        apres = int(chemin.split("after=")[1])
        return _Reponse(200, sorted((m for m in serveur if int(m["user"]["id"]) > apres),
                                    key=lambda m: int(m["user"]["id"]))[:2])

    monkeypatch.setattr(appel, "_bot_request", faux)
    monkeypatch.setattr(appel, "PAGE", 2)
    membres, motif = asyncio.run(lister_serveur())
    assert motif is None and [m["user"]["id"] for m in membres] == ["1", "3", "5", "8", "9"]
    assert [c.split("after=")[1] for c in demandes] == ["0", "3", "8"]
    for reponse, attendu in ((_Reponse(403, {"code": 50001}), "HTTP 403"),
                             (_Reponse(200, []), "liste vide"),
                             (_Reponse(200, {"code": 0}), "réponse illisible"),
                             (None, "Discord injoignable")):
        async def un(methode, chemin, reponse=reponse, **_):
            return reponse
        monkeypatch.setattr(appel, "_bot_request", un)
        assert asyncio.run(lister_serveur()) == (None, attendu)
