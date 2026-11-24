"""Lot « Les relances » : la règle du retard, la décision « qui prévenir de
quoi », le texte du MP et son envoi (`app/relances.py`), hors ligne -- ni
base, ni réseau. Les fonctions pures reçoivent des données en mémoire ; les
événements et les exceptions sont de vrais `Event` et `OccurrenceOverride`,
jamais écrits en base.

1. `test_jeu_libre_compte` -- une occurrence de jeu libre est effective ;
2. `test_peut_etre_compte` · 3. `test_absent_compte` -- toute réponse compte ;
4. `test_reponse_a_venir_compte` -- une réponse à une occurrence à venir ;
5. `test_occurrence_annulee_ne_compte_pas` -- une exception « annulée »
   retire l'occurrence, et la réponse qu'elle portait avec elle ;
6. `test_moins_de_28_jours` · 7. `test_free_agent` · 8. `test_profil_archive`
   · 9. `test_fenetre_sans_occurrence` -- qui n'est pas jugé ;
10. `test_deja_prevenu_aucun_mp` · 11. `test_nouvel_episode_apres_une_reponse`
    · 12. `test_refuse_vaut_prevenu` · 13. `test_echec_ne_vaut_pas_prevenu`
    · 14. `test_jamais_repondu_un_envoi_suffit` -- R4 ;
15. `test_texte_du_mp` -- les textes A et B du cadrage, au caractère près ;
16. `test_coupe_a_2000_caracteres` -- la coupe par la fin ;
17. `test_ordre_des_retards` -- alphabétique, sans tenir compte de la casse ;
18. `test_envoyer_mp` -- `envoye`, `refuse`, `echec`, et la forme des requêtes ;
19. `test_la_passe_suit_l_appel` -- R3 : après un appel réussi seulement, et
    une erreur de la passe ne change rien à l'appel.

Lot « Les relances nominatives » (R4 à R6) -- les destinataires, rôles ou
comptes, et la passe qui tourne à l'enregistrement du réglage :

20. `test_destinataires_une_seule_fois` -- un porteur de rôle choisi aussi par
    son nom ne compte qu'une fois ;
21. `test_destinataire_archive_exclu` -- ni par un rôle, ni par son nom ;
22. `test_destinataires_dans_l_ordre_des_identifiants` · 23.
    `test_destinataires_roles_ou_comptes` -- l'union, et personne sans choix ;
24. `test_la_passe_tourne_apres_un_enregistrement_reussi` -- après
    l'écriture, sous le verrou de l'appel, et jamais sur un refus ;
25. `test_la_passe_ne_tourne_pas_sans_jeton` -- ni base, ni Discord ;
26. `test_l_erreur_de_la_passe_n_echoue_pas_l_enregistrement` -- la route
    répond, l'écriture tient ;
27. `test_profile_ids_absent_vaut_liste_vide` -- le banc v4 n'envoie que
    `role_ids` ;
28. `test_profil_inconnu_ou_non_numerique_refuse` -- 400, et rien ne s'écrit.

Lot « Correctif des relances nominatives » (R1, R3) -- les comptes vivent dans
`account_capability` :

29. `test_compte_archive_garde_sans_etre_destinataire` -- 200, gardé avec
    `granted_by` égal à l'administrateur, jamais destinataire.
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi import HTTPException

import app.appel as appel
import app.command.api as command_api
import app.relances as relances
from app.models import Event, OccurrenceOverride
from app.relances import (Candidat, Retard, deja_prevenu, en_retard, envoyer_mp, nouveaux_noms,
                          par_escadrille, reponses_depuis, retenir_destinataires, texte_mp)

PARIS = ZoneInfo("Europe/Paris")
JOUR = date(2026, 10, 2)
DEBUT, FIN = JOUR - timedelta(days=28), JOUR - timedelta(days=1)
ANCIEN = JOUR - timedelta(days=100)


def _event(type_="entrainement", jour=date(2026, 9, 24), recurrence=None):
    return Event(id=uuid.uuid4(), type=type_, title="Événement", description="", game_label=None, map_name=None,
                 start_at=datetime.combine(jour, datetime.min.time()).replace(hour=20, minute=30, tzinfo=PARIS),
                 duration_min=None, recurrence=recurrence, created_by=1)


def _candidat(pid=1, nom="Pilote", escadrille="CHARLIE-33", depuis=ANCIEN, archive=False, reponses=(), derniere=None):
    return Candidat(id=pid, nom=nom, escadrille=escadrille, depuis=depuis, archive=archive,
                    reponses=frozenset(reponses), derniere=derniere)


def _retard(pid, nom, escadrille, derniere=None):
    return Retard(pid, nom, escadrille, derniere)


def _a(annee, mois, jour, heure=10):
    return datetime(annee, mois, jour, heure, 0, tzinfo=PARIS)


OCC_FENETRE = ("e1", date(2026, 9, 24))
OCC_AVENIR = ("e1", date(2026, 10, 8))


def test_jeu_libre_compte():
    jeu = _event("jeulibre", date(2026, 9, 20))
    occs = relances._occurrences(DEBUT, FIN, ([jeu], {}))
    assert occs == {(str(jeu.id), date(2026, 9, 20))}
    muet, repondu = _candidat(1), _candidat(2, reponses=occs)
    assert [r.id for r in en_retard(JOUR, [muet, repondu], occs, set())] == [1]


def test_peut_etre_compte():
    rep = reponses_depuis([("e1", date(2026, 9, 24), "maybe")])
    assert en_retard(JOUR, [_candidat(reponses=rep)], {OCC_FENETRE}, set()) == []


def test_absent_compte():
    rep = reponses_depuis([("e1", date(2026, 9, 24), "absent")])
    assert en_retard(JOUR, [_candidat(reponses=rep)], {OCC_FENETRE}, set()) == []
    # et présent aussi : l'état n'entre pas dans la règle
    rep = reponses_depuis([("e1", date(2026, 9, 24), "present")])
    assert en_retard(JOUR, [_candidat(reponses=rep)], {OCC_FENETRE}, set()) == []


def test_reponse_a_venir_compte():
    rep = reponses_depuis([("e1", date(2026, 10, 8), "present")])
    assert en_retard(JOUR, [_candidat(reponses=rep)], {OCC_FENETRE}, {OCC_AVENIR}) == []
    # la même réponse à une occurrence qui n'est pas effective ne sauve personne
    assert len(en_retard(JOUR, [_candidat(reponses=rep)], {OCC_FENETRE}, set())) == 1


def test_occurrence_annulee_ne_compte_pas():
    serie = _event(recurrence={"freq": "weekly", "interval": 1, "weekdays": [3]}, jour=date(2026, 9, 3))
    annulee = date(2026, 9, 24)
    ov = OccurrenceOverride(event_id=serie.id, occ_date=annulee, status="cancelled", patch=None)
    occs = relances._occurrences(DEBUT, FIN, ([serie], {serie.id: {annulee: ov}}))
    # les jeudis de la fenêtre (10/09, 17/09, 24/09, 01/10), sans le 24/09 annulé
    assert {j for _e, j in occs} == {date(2026, 9, 10), date(2026, 9, 17), date(2026, 10, 1)}
    # une réponse à l'occurrence annulée ne compte pas : le pilote est en retard
    rep = reponses_depuis([(str(serie.id), annulee, "present")])
    assert [r.id for r in en_retard(JOUR, [_candidat(reponses=rep)], occs, set())] == [1]
    # et une fenêtre dont toutes les occurrences sont annulées : personne n'est jugé
    seule = _event(jour=annulee)
    ov = OccurrenceOverride(event_id=seule.id, occ_date=annulee, status="cancelled", patch=None)
    assert relances._occurrences(DEBUT, FIN, ([seule], {seule.id: {annulee: ov}})) == set()


def test_moins_de_28_jours():
    neuf = _candidat(1, depuis=JOUR - timedelta(days=27))
    juste = _candidat(2, depuis=JOUR - timedelta(days=28))
    assert [r.id for r in en_retard(JOUR, [neuf, juste], {OCC_FENETRE}, set())] == [2]


def test_free_agent():
    libre = _candidat(1, escadrille=None, depuis=None)
    assert en_retard(JOUR, [libre], {OCC_FENETRE}, set()) == []


def test_profil_archive():
    assert en_retard(JOUR, [_candidat(archive=True)], {OCC_FENETRE}, set()) == []


def test_fenetre_sans_occurrence():
    # des occurrences à venir ne suffisent pas à juger : la fenêtre décide
    assert en_retard(JOUR, [_candidat()], set(), {OCC_AVENIR}) == []


def _envoi(dest, pilote, quand, statut):
    return (dest, pilote, quand, statut)


def test_deja_prevenu_aucun_mp():
    r = _retard(7, "thorn", "CHARLIE-33", _a(2026, 8, 14))
    envois = [_envoi(1, 7, _a(2026, 10, 2), "envoye")]
    assert deja_prevenu(envois, 1, r)
    assert nouveaux_noms(envois, 1, [r]) == []          # sans nouveau nom, aucun MP
    assert nouveaux_noms(envois, 2, [r]) == [r]         # un autre destinataire reste à prévenir


def test_nouvel_episode_apres_une_reponse():
    # prévenu le 02/09, puis il répond le 10/09 et retombe en retard : signalé de nouveau
    r = _retard(7, "thorn", "CHARLIE-33", _a(2026, 9, 10))
    envois = [_envoi(1, 7, _a(2026, 9, 2), "envoye")]
    assert not deja_prevenu(envois, 1, r)
    assert nouveaux_noms(envois, 1, [r]) == [r]
    # l'envoi daté après sa dernière réponse, lui, vaut prévenu
    assert deja_prevenu(envois + [_envoi(1, 7, _a(2026, 10, 2), "envoye")], 1, r)


def test_refuse_vaut_prevenu():
    r = _retard(7, "thorn", "CHARLIE-33", _a(2026, 8, 14))
    assert deja_prevenu([_envoi(1, 7, _a(2026, 10, 2), "refuse")], 1, r)


def test_echec_ne_vaut_pas_prevenu():
    r = _retard(7, "thorn", "CHARLIE-33", _a(2026, 8, 14))
    envois = [_envoi(1, 7, _a(2026, 10, 2), "echec")]
    assert not deja_prevenu(envois, 1, r)
    assert nouveaux_noms(envois, 1, [r]) == [r]         # la passe suivante réessaie


def test_jamais_repondu_un_envoi_suffit():
    r = _retard(7, "Jamais", "CHARLIE-33", None)
    assert deja_prevenu([_envoi(1, 7, _a(2026, 1, 1), "envoye")], 1, r)
    assert not deja_prevenu([_envoi(1, 8, _a(2026, 10, 2), "envoye")], 1, r)   # un autre pilote
    assert not deja_prevenu([_envoi(2, 7, _a(2026, 10, 2), "envoye")], 1, r)   # un autre destinataire


RETARDS_A = [
    _retard(6, "Fog", "ALPHA-11", _a(2026, 9, 12)),
    _retard(1, "Jamais", "CHARLIE-33"),
    _retard(2, "Kerberos", "CHARLIE-33", _a(2026, 8, 20)),
    _retard(3, "thorn", "CHARLIE-33", _a(2026, 8, 14)),
    _retard(4, "Odin", "T-14"),
]
TEXTE_A = """**Relances de planning**
Pilotes d'escadrille sans aucune réponse au planning depuis quatre semaines :

**ALPHA-11**
- Fog — dernière réponse le 12/09 · nouveau
**CHARLIE-33**
- Jamais — aucune réponse · nouveau
- Kerberos — dernière réponse le 20/08 · nouveau
- thorn — dernière réponse le 14/08 · nouveau
**T-14**
- Odin — aucune réponse · nouveau

La liste à jour est au Centre de Commandement, écran Membres."""
TEXTE_B = """**Relances de planning**
Pilotes d'escadrille sans aucune réponse au planning depuis quatre semaines :

**ALPHA-11**
- Fog — dernière réponse le 12/09
**BRAVO-22**
- Rover — aucune réponse · nouveau
**CHARLIE-33**
- Jamais — aucune réponse
- Kerberos — dernière réponse le 20/08
- thorn — dernière réponse le 14/08
**T-14**
- Odin — aucune réponse

La liste à jour est au Centre de Commandement, écran Membres."""


def test_texte_du_mp():
    assert texte_mp(RETARDS_A, {6, 1, 2, 3, 4}) == TEXTE_A
    avec_rover = sorted(RETARDS_A + [_retard(10, "Rover", "BRAVO-22")],
                        key=lambda r: (r.escadrille.casefold(), r.nom.casefold()))
    assert texte_mp(avec_rover, {10}) == TEXTE_B
    assert texte_mp(RETARDS_A, set()).count("nouveau") == 0


def test_coupe_a_2000_caracteres():
    pilotes = [_retard(100 + i, f"Pilote-{i:03d}-" + "x" * 20, ("CHARLIE-33", "T-14")[i // 60], _a(2026, 8, 14))
               for i in range(120)]
    texte = texte_mp(pilotes, {p.id for p in pilotes})
    assert len(texte) <= 2000
    lignes = texte.split("\n")
    assert lignes[0] == "**Relances de planning**"
    assert lignes[-1] == "La liste à jour est au Centre de Commandement, écran Membres."
    gardes = [l for l in lignes if l.startswith("- Pilote-")]
    coupe = lignes[-3]
    assert coupe == f"- … et {120 - len(gardes)} autres : voir le Centre"
    # on retire par la fin : les lignes gardées sont les premières, dans l'ordre
    assert gardes == [f"- {p.nom} — dernière réponse le 14/08 · nouveau" for p in pilotes[:len(gardes)]]
    assert 0 < len(gardes) < 120
    # un texte qui tient n'est jamais coupé
    court = texte_mp(RETARDS_A, set())
    assert "autres" not in court and len(court) < 2000
    # une escadrille dont tous les pilotes sont partis perd son titre
    assert "**T-14**" not in texte


def test_ordre_des_retards():
    cs = [_candidat(1, "thorn"), _candidat(2, "Jamais"), _candidat(3, "kerberos"),
          _candidat(4, "Odin", escadrille="t-14"), _candidat(5, "Fog", escadrille="ALPHA-11"),
          _candidat(6, "Zed", escadrille="CHARLIE-33")]
    r = en_retard(JOUR, cs, {OCC_FENETRE}, set())
    assert [(x.escadrille, x.nom) for x in r] == [("ALPHA-11", "Fog"), ("CHARLIE-33", "Jamais"), ("CHARLIE-33", "kerberos"),
                                                    ("CHARLIE-33", "thorn"), ("CHARLIE-33", "Zed"), ("t-14", "Odin")]
    assert [e for e, _ in par_escadrille(r)] == ["ALPHA-11", "CHARLIE-33", "t-14"]


class _Reponse:
    def __init__(self, statut, corps):
        self.status_code, self._corps = statut, corps

    def json(self):
        if isinstance(self._corps, Exception):
            raise self._corps
        return self._corps


def test_envoyer_mp(monkeypatch):
    demandes = []

    def faux(ouverture, depot):
        async def _requete(methode, chemin, json_body=None):
            demandes.append((methode, chemin, json_body))
            return ouverture if chemin == "/users/@me/channels" else depot
        return _requete

    ok = _Reponse(200, {"id": "9123"})
    cas = [
        (ok, _Reponse(200, {"id": "5"}), "envoye"),
        (_Reponse(403, {"code": 50007}), None, "refuse"),            # à l'ouverture du canal
        (ok, _Reponse(403, {"code": 50007}), "refuse"),              # au dépôt
        (_Reponse(403, {"code": 50001}), None, "echec"),             # un autre 403
        (ok, _Reponse(403, {"code": 50001}), "echec"),
        (ok, _Reponse(500, {}), "echec"),
        (_Reponse(500, {}), None, "echec"),
        (_Reponse(200, ValueError("illisible")), None, "echec"),     # canal sans identifiant
        (None, None, "echec"),                                       # Discord injoignable
        (ok, None, "echec"),
    ]
    for ouverture, depot, attendu in cas:
        demandes.clear()
        monkeypatch.setattr(relances, "_bot_request", faux(ouverture, depot))
        assert asyncio.run(envoyer_mp(123, "texte")) == attendu
    # la forme des requêtes : par `_bot_request`, corps {"content": …}, sans embed
    demandes.clear()
    monkeypatch.setattr(relances, "_bot_request", faux(ok, _Reponse(200, {"id": "5"})))
    asyncio.run(envoyer_mp(123, "texte"))
    assert demandes == [("POST", "/users/@me/channels", {"recipient_id": "123"}),
                        ("POST", "/channels/9123/messages", {"content": "texte"})]


def test_la_passe_suit_l_appel(monkeypatch):
    appels = []

    def installer(compte_rendu, passe_leve=False):
        async def faux_appel(source):
            return dict(compte_rendu)

        async def fausse_passe():
            appels.append("passe")
            if passe_leve:
                raise RuntimeError("la passe casse")
            return {}
        monkeypatch.setattr(appel, "_appel", faux_appel)
        monkeypatch.setattr(relances, "passe", fausse_passe)
        monkeypatch.setattr(appel, "_dernier", None)

    ok = {"at": "x", "source": "bouton", "erreur": None, "liste": "serveur non listé"}
    installer(ok)
    assert asyncio.run(appel.faire_appel("bouton")) == ok and appels == ["passe"]   # `liste` n'est pas une erreur
    appels.clear()
    installer({**ok, "erreur": "pas de jeton bot"})
    assert asyncio.run(appel.faire_appel("bouton"))["erreur"] == "pas de jeton bot" and appels == []
    installer({**ok, "erreur": "Discord injoignable"})
    asyncio.run(appel.faire_appel("quotidien"))
    assert appels == []                                                             # appel interrompu : pas de passe
    # une erreur de la passe se journalise : le compte rendu de l'appel ne change pas
    appels.clear()
    installer(ok, passe_leve=True)
    assert asyncio.run(appel.faire_appel("bouton")) == ok and appels == ["passe"]


# ---------------------------------------------------------------------------
# Lot « Les relances nominatives » : les destinataires (R4) et la passe à
# l'enregistrement du réglage (R5)
# ---------------------------------------------------------------------------

def _profil(pid, roles=(), archive=False):
    """`(id, archivé, roles_snapshot)`, la forme que lit `retenir_destinataires`."""
    return (pid, archive, list(roles))


def test_destinataires_une_seule_fois():
    # 7 porte le rôle choisi ET est choisi par son nom : une seule fois
    profils = [_profil(7, roles=["10"]), _profil(8, roles=["99"])]
    assert retenir_destinataires(profils, {"10"}, {7}) == [7]


def test_destinataire_archive_exclu():
    profils = [_profil(1, roles=["10"], archive=True), _profil(2, archive=True), _profil(3, roles=["10"])]
    assert retenir_destinataires(profils, {"10"}, {2}) == [3]    # archivé : ni par son rôle, ni par son nom


def test_destinataires_dans_l_ordre_des_identifiants():
    profils = [_profil(30, roles=["10"]), _profil(5), _profil(12, roles=["10"]), _profil(2)]
    assert retenir_destinataires(profils, {"10"}, {5, 2}) == [2, 5, 12, 30]


def test_destinataires_roles_ou_comptes():
    profils = [_profil(1, roles=["10"]), _profil(2), _profil(3)]
    assert retenir_destinataires(profils, {"10"}, set()) == [1]      # un rôle seul
    assert retenir_destinataires(profils, set(), {2}) == [2]         # un compte seul
    assert retenir_destinataires(profils, {"10"}, {2}) == [1, 2]     # les deux
    assert retenir_destinataires(profils, set(), set()) == []        # aucun choix : personne
    assert retenir_destinataires([(4, False, None)], {"10"}, set()) == []   # snapshot absent : pas de rôle


class _Resultat:
    def __init__(self, valeurs):
        self._valeurs = list(valeurs)

    def scalars(self):
        return self

    def all(self):
        return self._valeurs


class _FauxDb:
    """Une base qui note chaque geste dans `journal`, dans l'ordre. `valides` :
    les identifiants de profils que la lecture de validation rend (non archivés
    et connus)."""

    def __init__(self, journal, valides=()):
        self.journal, self.valides = journal, list(valides)
        self.objets, self.requetes = [], []

    async def execute(self, stmt):
        texte = str(stmt)
        self.requetes.append(texte)
        if texte.startswith("SELECT"):
            self.journal.append("lecture")
            return _Resultat(self.valides)
        self.journal.append("effacement")
        return None

    def add(self, objet):
        self.objets.append(objet)
        self.journal.append(f"ajout {type(objet).__name__}")

    async def commit(self):
        self.journal.append("commit")


def _installer_route(monkeypatch, journal, passe_leve=False):
    """La route de production, la passe simulée : elle note si le verrou de
    l'appel est pris pendant qu'elle tourne."""
    async def fausse_passe():
        journal.append(f"passe verrou={appel._verrou.locked()}")
        if passe_leve:
            raise RuntimeError("la passe casse")
        return {}
    monkeypatch.setattr(relances, "passe", fausse_passe)
    monkeypatch.setattr(command_api, "is_admin", lambda user: user["id"] == "999")


ADMIN = {"id": "999"}                      # numérique : `granted_by` en prend l'entier


def test_la_passe_tourne_apres_un_enregistrement_reussi(monkeypatch):
    journal = []
    _installer_route(monkeypatch, journal)
    corps = command_api.RelancesPayload(role_ids=["10"], profile_ids=["7", "8"])
    rep = asyncio.run(command_api.put_relances(corps, ADMIN, _FauxDb(journal, valides=[7, 8])))
    assert rep == {"relances": {"role_ids": ["10"], "profile_ids": ["7", "8"]}}
    # l'écriture d'abord, le commit, puis la passe -- sous le verrou de l'appel
    assert journal[-2:] == ["commit", "passe verrou=True"]
    assert journal.count("ajout AccountCapability") == 2 and journal.count("ajout RoleCapability") == 1
    assert not appel._verrou.locked()                                # le verrou est rendu
    # un refus (403 hors administrateur) ne lance pas la passe et n'écrit rien
    journal.clear()
    with pytest.raises(HTTPException) as e:
        asyncio.run(command_api.put_relances(corps, {"id": "autre"}, _FauxDb(journal, valides=[7, 8])))
    assert e.value.status_code == 403 and journal == []


def test_la_passe_ne_tourne_pas_sans_jeton(monkeypatch):
    def pas_de_base(*a, **k):
        raise AssertionError("la passe sans jeton ne doit pas ouvrir la base")

    async def pas_de_discord(*a, **k):
        raise AssertionError("la passe sans jeton ne doit pas parler à Discord")
    monkeypatch.setattr(relances.settings, "DISCORD_BOT_TOKEN", "")
    monkeypatch.setattr(relances, "AsyncSessionLocal", pas_de_base)
    monkeypatch.setattr(relances, "_bot_request", pas_de_discord)
    assert asyncio.run(relances.passe()) == {"envoye": 0, "refuse": 0, "echec": 0}


def test_l_erreur_de_la_passe_n_echoue_pas_l_enregistrement(monkeypatch):
    journal = []
    _installer_route(monkeypatch, journal, passe_leve=True)
    corps = command_api.RelancesPayload(role_ids=[], profile_ids=["7"])
    rep = asyncio.run(command_api.put_relances(corps, ADMIN, _FauxDb(journal, valides=[7])))
    assert rep == {"relances": {"role_ids": [], "profile_ids": ["7"]}}      # la route répond 200
    assert "commit" in journal and journal[-1] == "passe verrou=True"        # l'écriture tient, la passe a bien tourné
    assert not appel._verrou.locked()


def test_profile_ids_absent_vaut_liste_vide(monkeypatch):
    assert command_api.RelancesPayload(role_ids=["10"]).profile_ids == []   # le banc v4 n'envoie que `role_ids`
    journal = []
    _installer_route(monkeypatch, journal)
    base = _FauxDb(journal)
    rep = asyncio.run(command_api.put_relances(command_api.RelancesPayload(role_ids=["10"]), ADMIN, base))
    assert rep == {"relances": {"role_ids": ["10"], "profile_ids": []}}
    # aucun compte à valider : aucune lecture des profils (les lectures de l'état d'avant, faites par le journal
    # des modifications, portent sur `role_capabilities` et `account_capability`)
    assert not any("FROM profiles" in requete for requete in base.requetes)
    assert journal.count("effacement") == 2                                  # les deux listes sont remplacées en entier
    assert "ajout AccountCapability" not in journal


def test_profil_inconnu_ou_non_numerique_refuse(monkeypatch):
    journal = []
    _installer_route(monkeypatch, journal)
    for corps, message in (
        (command_api.RelancesPayload(role_ids=["10"], profile_ids=["7", "666"]), "Compte inconnu : 666"),
        (command_api.RelancesPayload(role_ids=["10"], profile_ids=["pas-un-nombre"]), "Compte inconnu : pas-un-nombre"),
    ):
        journal.clear()
        with pytest.raises(HTTPException) as e:
            asyncio.run(command_api.put_relances(corps, ADMIN, _FauxDb(journal, valides=[7])))
        assert e.value.status_code == 422 and e.value.detail == message
        assert "commit" not in journal and "effacement" not in journal and not any(j.startswith("passe") for j in journal)


def test_compte_archive_garde_sans_etre_destinataire(monkeypatch):
    journal = []
    _installer_route(monkeypatch, journal)
    db = _FauxDb(journal, valides=[7, 8])                                    # 8 : un compte archivé, que la base connaît
    corps = command_api.RelancesPayload(role_ids=[], profile_ids=["7", "8"])
    rep = asyncio.run(command_api.put_relances(corps, ADMIN, db))
    assert rep == {"relances": {"role_ids": [], "profile_ids": ["7", "8"]}}  # 200 : le compte archivé est gardé
    assert not any("archived_at" in r for r in db.requetes)                  # la validation ne filtre plus l'archivage
    comptes = [o for o in db.objets if type(o).__name__ == "AccountCapability"]
    assert [(o.profile_id, o.capability, o.granted_by) for o in comptes] == [
        (7, "relances.destinataire", 999), (8, "relances.destinataire", 999)]  # granted_by : l'administrateur
    # jamais destinataire : ni par son nom, ni par un rôle
    assert retenir_destinataires([_profil(7), _profil(8, archive=True)], set(), {7, 8}) == [7]
