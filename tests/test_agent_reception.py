"""Lot « La réception du .rrlog de l'agent » (`v1.0089`, `rr-agent-reception`) -- la route
`POST /api/agent/rrlog` et les trois routes du Centre qui tiennent son jeton.

Douze tests, un par règle du cadrage (R18), hors ligne : la base est une fausse session
(`FausseBase`) que les dépendances de FastAPI remplacent -- elle comprend les quelques
instructions SQLAlchemy que les routes émettent --, `DEBRIEF_STORAGE_DIR` est un dossier
temporaire, et la route se rejoue avec le `TestClient` de `app.main.app` (ou directement
en ASGI quand le test doit pouvoir dire que le corps n'a pas été lu).
"""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import os
import re
import sys
import tracemalloc
import warnings
import zlib
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import itsdangerous
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : on n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.elements import TextClause

from app import agent
from app.auth import get_current_user
from app.capabilities import require_command_access
from app.config import settings
from app.db import get_db
from app.defense import plafond_du_corps
from app.main import app
from app.models import AgentJeton, AgentRrlog, CommandJournal, Profile

CHEMIN = "/api/agent/rrlog"
ADMIN = {"id": "111", "name": "Kestrel", "roles": []}
MEMBRE = {"id": "222", "name": "Odin", "roles": []}
ADJOINT = {"id": "333", "name": "Hunter", "roles": []}
ENTETE_H = "H\trrlog\t4\t0.2.0\tCHARLIE-33 Training\tSYRIA\t1985-06-14\t43200\t2026-11-14T22:41:00Z\n"


def cookie_de_session(user: dict) -> str:
    """Le cookie de session d'un membre, signé comme `SessionMiddleware` le signe (la garde du corps exige
    une session aux routes du Centre ; les dépendances, elles, sont remplacées)."""
    session = {"id": user["id"], "roles": [], "exp": "2999-01-01T00:00:00+00:00"}
    donnees = b64encode(json.dumps(session).encode("utf-8"))
    return "session=" + itsdangerous.TimestampSigner(str(settings.SESSION_SECRET)).sign(donnees).decode("utf-8")


def sha(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def rrlog(corps: str = ENTETE_H + "J\t0\t2026-11-14T22:41:00Z\tconnexion\t2\tPilote\tucid\trouge\t\n") -> bytes:
    return corps.encode("utf-8")


# --- La fausse base ---------------------------------------------------------------


class _Resultat:
    def __init__(self, lignes):
        self._lignes = lignes

    def scalars(self):
        return self

    def all(self):
        return list(self._lignes)

    def first(self):
        return self._lignes[0] if self._lignes else None


class FausseBase:
    """Une session SQLAlchemy asynchrone qui tient en mémoire : `add`, `commit` (dont le conflit
    d'unicité, à la demande), `rollback`, `get`, et les `select` / `update` des routes."""

    def __init__(self):
        self.jetons: list = []
        self.recus: list = []
        self.journal: list = []
        self.profils = {int(ADMIN["id"]): SimpleNamespace(global_name="Kestrel", username="kestrel")}
        self.en_attente: list = []
        self.ajoutes: list = []      # tout ce que `add` a reçu
        self.tables: set = set()     # les tables que les instructions ont touchées
        self.conflit = False         # `"flush"` ou `"commit"` : le prochain flush / commit lève un conflit d'unicité
        self.sur_rollback = None     # un geste joué une fois, au prochain `rollback` (une révocation « entre-temps »)
        self.verrous: list = []      # les paramètres de chaque verrou de transaction demandé
        self.commits = 0
        self.rollbacks = 0
        self._id = 0

    def _prochain(self) -> int:
        self._id += 1
        return self._id

    def add(self, objet):
        self.ajoutes.append(objet)
        self.en_attente.append(objet)

    async def get(self, modele, cle):
        assert modele is Profile
        return self.profils.get(cle)

    def _perdre_la_course(self):
        """Le gagnant de la course a déjà sa ligne (commitée) ; la nôtre est refusée par la contrainte d'unicité."""
        for objet in self.en_attente:
            if isinstance(objet, AgentRrlog):
                self.recus.append(AgentRrlog(
                    id=self._prochain(), sha256=objet.sha256, fichier="gagnant.rrlog", chemin=objet.chemin,
                    taille_gz=1, taille=1, recu_le=objet.recu_le, jeton_id=objet.jeton_id, etat="en_attente"))
        self.en_attente = []
        raise IntegrityError("INSERT INTO agent_rrlog", {}, Exception("duplicate key"))

    async def flush(self):
        if self.conflit == "flush":
            self.conflit = False
            self._perdre_la_course()

    async def commit(self):
        if self.conflit:
            self.conflit = False
            self._perdre_la_course()
        for objet in self.en_attente:
            if isinstance(objet, AgentJeton):
                objet.id = self._prochain()
                if objet.emis_le is None:
                    objet.emis_le = datetime.now(timezone.utc)
                self.jetons.append(objet)
            elif isinstance(objet, AgentRrlog):
                objet.id = self._prochain()
                self.recus.append(objet)
            elif isinstance(objet, CommandJournal):
                self.journal.append(objet)
        self.en_attente = []
        self.commits += 1

    async def rollback(self):
        self.en_attente = []
        self.rollbacks += 1
        geste, self.sur_rollback = self.sur_rollback, None
        if geste:
            geste()

    async def execute(self, instruction, parametres=None):
        if isinstance(instruction, TextClause):     # le verrou de transaction des émissions (A5)
            self.verrous.append((str(instruction), parametres))
            return _Resultat([])
        params = instruction.compile().params
        if getattr(instruction, "is_update", False):
            self.tables.add(instruction.table.name)
            if "revoque_le" in params:
                for j in self.jetons:
                    if j.revoque_le is None:
                        j.revoque_le = params["revoque_le"]
            elif "dernier_envoi_le" in params:
                for j in self.jetons:
                    if j.id == params["id_1"]:
                        j.dernier_envoi_le = params["dernier_envoi_le"]
            return _Resultat([])
        entite = instruction.column_descriptions[0]["entity"]
        self.tables.add(entite.__tablename__)
        if entite is AgentJeton:
            return _Resultat([j for j in self.jetons if j.revoque_le is None])
        assert entite is AgentRrlog
        empreintes = [v for v in params.values() if isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v)]
        lignes = [r for r in self.recus if not empreintes or r.sha256 == empreintes[0]]
        lignes.sort(key=lambda r: (r.recu_le, r.id), reverse=True)
        limite = params.get("param_1")
        return _Resultat(lignes[:limite] if limite else lignes)


@pytest.fixture
def banc(tmp_path, monkeypatch):
    """La fausse base, un dossier de stockage neuf, un client ; les dépendances remplacées."""
    monkeypatch.setattr(settings, "DEBRIEF_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "ADMIN_IDS", ADMIN["id"])
    db = FausseBase()
    acteur = {"user": ADMIN}

    async def _db():
        return db

    async def _acces():
        return acteur["user"]

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _acces
    app.dependency_overrides[require_command_access] = _acces
    try:
        yield SimpleNamespace(
            db=db, dossier=tmp_path / "_agent", acteur=acteur,
            client=TestClient(app, follow_redirects=False),   # l'agent : aucun cookie
            centre=TestClient(app, follow_redirects=False, headers={"cookie": cookie_de_session(ADMIN)}),
        )
    finally:
        app.dependency_overrides.clear()


def en_tant_que(banc, user: dict) -> None:
    banc.acteur["user"] = user
    banc.centre.headers["cookie"] = cookie_de_session(user)


def donner_un_jeton(db: FausseBase, revoque: bool = False) -> str:
    """Pose un jeton au registre et rend le clair."""
    clair, empreinte = agent.nouveau_jeton()
    db.jetons.append(
        AgentJeton(
            id=db._prochain(), empreinte=empreinte, emis_le=datetime.now(timezone.utc), emis_par=ADMIN["id"],
            revoque_le=datetime.now(timezone.utc) if revoque else None, dernier_envoi_le=None,
        )
    )
    return clair


def envoyer(banc, corps: bytes, empreinte: str | None, jeton: str, nom: str | None = "rr_essai.rrlog", **plus):
    en_tetes = {"Authorization": f"Bearer {jeton}", "Content-Type": "application/gzip"}
    if nom is not None:
        en_tetes["X-RR-Fichier"] = nom
    if empreinte is not None:
        en_tetes["X-RR-Sha256"] = empreinte
    en_tetes.update(plus)
    return banc.client.post(CHEMIN, content=corps, headers=en_tetes)


def aucun_fichier(banc) -> bool:
    return not banc.dossier.exists() or not any(banc.dossier.iterdir())


def appeler_asgi(en_tetes: dict, recevoir) -> tuple[int, dict]:
    """Appelle l'application en ASGI, `recevoir` étant ce que le corps lit : permet de dire qu'il n'a pas été lu."""
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST", "scheme": "http",
        "path": CHEMIN, "raw_path": CHEMIN.encode(), "query_string": b"", "root_path": "",
        "headers": [(k.lower().encode(), v.encode()) for k, v in en_tetes.items()],
        "client": ("127.0.0.1", 50000), "server": ("testserver", 80),
    }
    reponse = {"status": None, "corps": b""}

    async def envoyer_(message):
        if message["type"] == "http.response.start":
            reponse["status"] = message["status"]
        elif message["type"] == "http.response.body":
            reponse["corps"] += message.get("body", b"")

    asyncio.run(app(scope, recevoir, envoyer_))
    return reponse["status"], json.loads(reponse["corps"] or b"{}")


# --- 1 · le jeton d'abord ------------------------------------------------------------


def test_jeton_refuse_401(banc):
    valide = donner_un_jeton(banc.db)
    revoque = donner_un_jeton(banc.db, revoque=True)
    inconnu = "rra_" + "A" * 43
    refus = {"detail": "Jeton refusé."}
    gz = gzip.compress(rrlog())
    for autorisation in (None, "", f"Basic {valide}", valide, "Bearer", "Bearer abc", f"Bearer {valide[4:]}",
                         f"Bearer {inconnu}", f"Bearer {revoque}", f"bearer {valide}"):
        en_tetes = {"X-RR-Fichier": "rr_essai.rrlog", "X-RR-Sha256": sha(rrlog())}
        if autorisation is not None:
            en_tetes["Authorization"] = autorisation
        r = banc.client.post(CHEMIN, content=gz, headers=en_tetes)
        assert r.status_code == 401 and r.json() == refus, autorisation
    # Le jeton juste, mais l'agent oublie tout le reste : ce n'est plus un 401.
    assert envoyer(banc, gz, None, valide, nom=None).status_code == 422

    # Le corps n'est jamais lu quand le jeton est refusé : un corps qui lève à la lecture ne change rien.
    async def lit_et_leve():
        raise AssertionError("le corps a été lu")

    for autorisation in (None, f"Bearer {inconnu}", f"Bearer {revoque}"):
        en_tetes = {"X-RR-Fichier": "rr_essai.rrlog", "X-RR-Sha256": sha(rrlog())}
        if autorisation is not None:
            en_tetes["Authorization"] = autorisation
        statut, corps = appeler_asgi(en_tetes, lit_et_leve)
        assert (statut, corps) == (401, refus), autorisation
    assert aucun_fichier(banc) and not banc.db.recus

    # Addendum 2 (A3) : un jeton révoqué ENTRE l'acceptation et l'écriture → 401, rien d'écrit, aucun temporaire.
    def revoquer_entre_temps():
        for j in banc.db.jetons:
            j.revoque_le = datetime.now(timezone.utc)

    contenu = rrlog()
    banc.db.sur_rollback = revoquer_entre_temps
    r = envoyer(banc, gzip.compress(contenu), sha(contenu), valide)
    assert r.status_code == 401 and r.json() == refus
    assert aucun_fichier(banc) and not banc.db.recus and banc.db.commits == 0
    assert not any(isinstance(o, AgentRrlog) for o in banc.db.ajoutes)


# --- 2 · le plafond de 32 Mio ----------------------------------------------------------


def test_plafond_32_mio(banc):
    jeton = donner_un_jeton(banc.db)
    assert plafond_du_corps(CHEMIN) == 33_554_432
    refus = {"detail": "Requête trop volumineuse."}
    en_tetes = {"Authorization": f"Bearer {jeton}", "X-RR-Fichier": "rr_essai.rrlog", "X-RR-Sha256": sha(rrlog())}

    # `Content-Length` de 32 Mio + 1 : 413 avant toute lecture du corps.
    async def lit_et_leve():
        raise AssertionError("le corps a été lu")

    statut, corps = appeler_asgi({**en_tetes, "Content-Length": str(33_554_432 + 1)}, lit_et_leve)
    assert (statut, corps) == (413, refus)
    # Pile 32 Mio annoncés : le plafond n'est pas dépassé (la route répond, ici par le gzip invalide).
    morceaux_vides = iter([{"type": "http.request", "body": b"", "more_body": False}])

    async def vide():
        return next(morceaux_vides)

    statut, _ = appeler_asgi({**en_tetes, "Content-Length": "33554432"}, vide)
    assert statut == 422

    # Sans `Content-Length`, par morceaux : les octets se comptent à la lecture (un gzip valide, 33 Mio stockés).
    gros = gzip.compress(os.urandom(33 * 1024 * 1024), compresslevel=0)
    assert len(gros) > 33_554_432
    pas = 1024 * 1024
    morceaux = [gros[i:i + pas] for i in range(0, len(gros), pas)]
    servis = iter(morceaux)

    async def par_morceaux():
        try:
            reste = next(servis)
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.request", "body": reste, "more_body": True}

    statut, corps = appeler_asgi(en_tetes, par_morceaux)
    assert (statut, corps) == (413, refus)
    assert aucun_fichier(banc) and not banc.db.recus


# --- 3 · les en-têtes -------------------------------------------------------------------


def test_entetes_422(banc):
    jeton = donner_un_jeton(banc.db)
    contenu = rrlog()
    gz = gzip.compress(contenu)
    bon_sha = sha(contenu)
    mauvais_noms = [
        None, "", "%zz", "abc%", "%FF%FE", "%C3", "a%2Fb", "a%2fb", "a%5Cb", "a%00b", "a%0Ab", "a%0Db", "a%7Fb",
        "a" * 256, "%C3%A9" * 256, "../x",
        "rr_été.rrlog".encode("utf-8"),     # addendum 2 (A4) : des octets bruts, non encodés en pourcent
    ]
    for nom in mauvais_noms:
        r = envoyer(banc, gz, bon_sha, jeton, nom=nom)
        assert r.status_code == 422, repr(nom)
        assert jeton not in r.text and "detail" in r.json()
    mauvais_sha = [
        None, "", bon_sha.upper(), bon_sha[:63], bon_sha + "0", "g" * 64, " " + bon_sha[1:], bon_sha[:-1] + "G",
    ]
    for valeur in mauvais_sha:
        r = envoyer(banc, gz, valeur, jeton)
        assert r.status_code == 422, repr(valeur)
        assert jeton not in r.text and "detail" in r.json()
    assert aucun_fichier(banc) and not banc.db.recus
    # Les limites permises : 255 caractères, un nom accentué encodé en pourcent.
    assert envoyer(banc, gz, bon_sha, jeton, nom="a" * 255).status_code == 201


# --- 4 · le gzip ------------------------------------------------------------------------


def test_gzip_invalide_422(banc):
    jeton = donner_un_jeton(banc.db)
    contenu = rrlog()
    gz = gzip.compress(contenu)
    for corps in (b"", b"ceci n'est pas du gzip", contenu, gz[:-10], gz[:12], gz + b"zzzz", gz + gz):
        r = envoyer(banc, corps, sha(contenu), jeton)
        assert r.status_code == 422, corps[:20]
        assert jeton not in r.text
    assert aucun_fichier(banc) and not banc.db.recus


# --- 5 · la bombe -----------------------------------------------------------------------


def test_bombe_413(banc):
    jeton = donner_un_jeton(banc.db)
    compresseur = zlib.compressobj(9, zlib.DEFLATED, 16 + zlib.MAX_WBITS)
    zeros = b"\0" * (1024 * 1024)
    morceaux = [compresseur.compress(zeros) for _ in range(130)]
    morceaux.append(compresseur.flush())
    bombe = b"".join(morceaux)
    del morceaux
    assert len(bombe) < 1024 * 1024
    tracemalloc.start()
    try:
        r = envoyer(banc, bombe, "0" * 64, jeton)
        _, pic = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert r.status_code == 413
    # La décompression ne rend jamais plus que `max_length` : la mémoire ne prend pas 128 Mio.
    assert pic < 24 * 1024 * 1024, pic
    assert aucun_fichier(banc) and not banc.db.recus


# --- 6 · le sha256 faux ------------------------------------------------------------------


def test_sha_faux_422(banc):
    jeton = donner_un_jeton(banc.db)
    contenu = rrlog()
    r = envoyer(banc, gzip.compress(contenu), sha(b"autre chose"), jeton)
    assert r.status_code == 422 and jeton not in r.text
    # Le sha256 du fichier compressé n'est pas celui du fichier.
    r = envoyer(banc, gzip.compress(contenu), sha(gzip.compress(contenu)), jeton)
    assert r.status_code == 422
    assert aucun_fichier(banc) and not banc.db.recus


# --- 7 · la première ligne ----------------------------------------------------------------


def test_premiere_ligne_422(banc):
    jeton = donner_un_jeton(banc.db)
    etrangeres = [
        b"", b"\n", b"X\trrlog\t4\n", b"H\tautre\t4\n", b"H\trrlog\tquatre\n", b"H\trrlog\n", b"H\trrlog\t\n",
        b"H rrlog 4\n", b"hello world\n" + b"x" * 100, b"H\trrlog\t4\xff\xfe\n", b"\xef\xbb\xbfH\trrlog\t4\n",
        b"J\t0\t2026-11-14T22:41:00Z\tconnexion\n" + ENTETE_H.encode(),
        # Addendum 2 (A2) : un caractère de contrôle autre que la tabulation dans la ligne `H`.
        ENTETE_H.replace("CHARLIE-33", "CHARLIE\x00-33").encode(), ENTETE_H.replace("SYRIA", "SY\x7fRIA").encode(),
        ENTETE_H.replace("SYRIA", "SY\x1bRIA").encode(), ENTETE_H.replace("0.2.0", "0.2\r.0").encode(),
    ]
    for contenu in etrangeres:
        r = envoyer(banc, gzip.compress(contenu), sha(contenu), jeton)
        assert r.status_code == 422, contenu[:30]
        assert jeton not in r.text
    # Une première ligne sans fin de ligne, mais sans rien de plus long qu'un en-tête : refusée aussi.
    contenu = b"H\trrlog\t4\t0.2.0" + b"x" * 70_000
    assert envoyer(banc, gzip.compress(contenu), sha(contenu), jeton).status_code == 422
    assert aucun_fichier(banc) and not banc.db.recus


# --- 8 · reçu : 201 ------------------------------------------------------------------------


def test_recu_201(banc):
    jeton = donner_un_jeton(banc.db)
    contenu = rrlog()
    gz = gzip.compress(contenu)
    nom = "rr_%C3%A9t%C3%A9_1985.rrlog"
    r = envoyer(banc, gz, sha(contenu), jeton, nom=nom)
    assert r.status_code == 201 and r.json() == {"statut": "recu"}
    # Le corps gzip tel que reçu, à l'octet, sous `_agent/<sha256>.rrlog.gz` ; aucun fichier temporaire.
    rangé = banc.dossier / f"{sha(contenu)}.rrlog.gz"
    assert rangé.read_bytes() == gz
    assert [p.name for p in banc.dossier.iterdir()] == [rangé.name]
    # Une ligne au registre, les champs de `H` lus.
    assert len(banc.db.recus) == 1
    ligne = banc.db.recus[0]
    assert (ligne.sha256, ligne.fichier, ligne.chemin) == (sha(contenu), "rr_été_1985.rrlog", f"_agent/{sha(contenu)}.rrlog.gz")
    assert (ligne.taille_gz, ligne.taille) == (len(gz), len(contenu))
    assert (ligne.format, ligne.agent_version, ligne.mission, ligne.theatre) == (4, "0.2.0", "CHARLIE-33 Training", "SYRIA")
    assert (ligne.date_mission, ligne.depart_reel, ligne.etat) == ("1985-06-14", "2026-11-14T22:41:00Z", "en_attente")
    assert ligne.session_id is None and ligne.jeton_id == banc.db.jetons[0].id
    # Le dernier envoi du jeton est posé, à l'heure du serveur (UTC).
    envoi = banc.db.jetons[0].dernier_envoi_le
    assert envoi is not None and abs(datetime.now(timezone.utc) - envoi) < timedelta(seconds=30)
    # Un champ manquant ou vide reste `None`.
    court = "H\trrlog\t4\t0.2.0\t\tSYRIA\n".encode()
    assert envoyer(banc, gzip.compress(court), sha(court), jeton).status_code == 201
    vide = banc.db.recus[1]
    assert (vide.mission, vide.theatre, vide.date_mission, vide.depart_reel) == (None, "SYRIA", None, None)
    # Aucune écriture dans `debrief_session` ni `debrief_upload`.
    assert not any(t.startswith("debrief_") for t in banc.db.tables)
    assert all(not type(o).__tablename__.startswith("debrief_") for o in banc.db.ajoutes)


# --- 9 · déjà reçu : 200 ---------------------------------------------------------------------


def test_deja_recu_200(banc):
    jeton = donner_un_jeton(banc.db)
    contenu = rrlog()
    gz = gzip.compress(contenu)
    assert envoyer(banc, gz, sha(contenu), jeton).status_code == 201
    banc.db.jetons[0].dernier_envoi_le = None
    # Le même fichier, recompressé autrement : même sha256, rien de plus au disque ni au registre.
    r = envoyer(banc, gzip.compress(contenu, compresslevel=1, mtime=12345), sha(contenu), jeton, nom="autre_nom.rrlog")
    assert r.status_code == 200 and r.json() == {"statut": "deja_recu"}
    assert len(banc.db.recus) == 1 and banc.db.recus[0].fichier == "rr_essai.rrlog"
    assert [p.name for p in banc.dossier.iterdir()] == [f"{sha(contenu)}.rrlog.gz"]
    assert (banc.dossier / f"{sha(contenu)}.rrlog.gz").read_bytes() == gz
    # Seule la date du dernier envoi bouge.
    assert banc.db.jetons[0].dernier_envoi_le is not None


# --- 10 · deux envois simultanés ----------------------------------------------------------------


def test_conflit_simultane_200(banc):
    jeton = donner_un_jeton(banc.db)
    contenu = rrlog()
    # Addendum 2 (A1) : l'« autre » requête a déjà rangé le fichier (octets différents : autre compression) ; le
    # `flush` -- l'`INSERT` -- perd la course. 200, jamais 500 ; le fichier de l'autre est intact ; aucun temporaire.
    banc.dossier.mkdir(parents=True)
    de_l_autre = gzip.compress(contenu, compresslevel=1, mtime=777)
    rangé = banc.dossier / f"{sha(contenu)}.rrlog.gz"
    rangé.write_bytes(de_l_autre)
    ours = gzip.compress(contenu)
    assert ours != de_l_autre
    banc.db.conflit = "flush"
    r = envoyer(banc, ours, sha(contenu), jeton)
    assert r.status_code == 200 and r.json() == {"statut": "deja_recu"}
    assert banc.db.rollbacks == 2     # l'ouverture de l'envoi (A3), puis le conflit
    assert rangé.read_bytes() == de_l_autre
    assert [p.name for p in banc.dossier.iterdir()] == [rangé.name]
    assert len(banc.db.recus) == 1 and banc.db.recus[0].fichier == "gagnant.rrlog"
    assert banc.db.jetons[0].dernier_envoi_le is not None

    # Le conflit au `commit` : même issue ; le fichier que cette requête vient de ranger reste, la ligne du
    # gagnant le porte ; aucun temporaire.
    autre = rrlog(ENTETE_H + "J\tautre\n")
    banc.db.conflit = "commit"
    r = envoyer(banc, gzip.compress(autre), sha(autre), jeton)
    assert r.status_code == 200 and r.json() == {"statut": "deja_recu"}
    assert sorted(p.name for p in banc.dossier.iterdir()) == sorted([rangé.name, f"{sha(autre)}.rrlog.gz"])
    assert (banc.dossier / f"{sha(autre)}.rrlog.gz").read_bytes() == gzip.compress(autre)

    # Une autre panne de la base, elle, retire le fichier rangé par cette requête (aucune ligne ne le porte) et ne
    # rend pas 200 ; le fichier de l'autre reste.
    troisieme = rrlog(ENTETE_H + "J\ttroisieme\n")

    async def casse():
        raise RuntimeError("base en panne")

    banc.db.commit = casse
    sans_echec = TestClient(app, follow_redirects=False, raise_server_exceptions=False)
    r = sans_echec.post(CHEMIN, content=gzip.compress(troisieme), headers={
        "Authorization": f"Bearer {jeton}", "X-RR-Fichier": "b.rrlog", "X-RR-Sha256": sha(troisieme)})
    assert r.status_code == 500
    assert sorted(p.name for p in banc.dossier.iterdir()) == sorted([rangé.name, f"{sha(autre)}.rrlog.gz"])


# --- 11 · émettre, révoquer ------------------------------------------------------------------------


def _valeurs(objet) -> str:
    return json.dumps({k: str(v) for k, v in vars(objet).items() if not k.startswith("_")})


def test_jeton_emis_revoque(banc):
    c = banc.centre
    r = c.post("/api/command/agent/jeton")
    assert r.status_code == 201
    premier = r.json()["jeton"]
    assert premier.startswith("rra_") and len(premier) == 4 + 43 and r.json()["emis_le"]
    # Seule l'empreinte est gardée.
    assert len(banc.db.jetons) == 1
    ligne = banc.db.jetons[0]
    assert ligne.empreinte == sha(premier.encode()) and ligne.emis_par == ADMIN["id"] and ligne.revoque_le is None
    assert premier not in _valeurs(ligne)
    # Le jeton émis ouvre la route de l'agent.
    contenu = rrlog()
    assert envoyer(banc, gzip.compress(contenu), sha(contenu), premier).status_code == 201
    # Révoquer : 204, puis 409 ; deux lignes au journal, ni le jeton ni l'empreinte dans leurs valeurs.
    assert c.delete("/api/command/agent/jeton").status_code == 204
    r = c.delete("/api/command/agent/jeton")
    assert r.status_code == 409 and r.json() == {"detail": "Aucun jeton actif."}
    assert [(j.action, j.objet, j.lignes, j.par_id) for j in banc.db.journal] == [
        ("agent.jeton.emis", None, [], 111), ("agent.jeton.revoque", None, [], 111)]
    for j in banc.db.journal:
        assert premier not in _valeurs(j) and ligne.empreinte not in _valeurs(j)
    r = envoyer(banc, gzip.compress(contenu), sha(contenu), premier)
    assert r.status_code == 401
    # Une seconde émission révoque la première : l'ancien jeton → 401, le nouveau passe.
    deuxieme = c.post("/api/command/agent/jeton").json()["jeton"]
    troisieme = c.post("/api/command/agent/jeton").json()["jeton"]
    assert len({premier, deuxieme, troisieme}) == 3
    actifs = [j for j in banc.db.jetons if j.revoque_le is None]
    assert len(actifs) == 1 and actifs[0].empreinte == sha(troisieme.encode())
    neuf = rrlog(ENTETE_H + "J\tneuf\n")
    assert envoyer(banc, gzip.compress(neuf), sha(neuf), deuxieme).status_code == 401
    assert envoyer(banc, gzip.compress(neuf), sha(neuf), troisieme).status_code == 201
    for j in banc.db.jetons:
        assert troisieme not in _valeurs(j) and deuxieme not in _valeurs(j)
    for j in banc.db.journal:
        assert not any(clair in _valeurs(j) for clair in (premier, deuxieme, troisieme))
        assert not any(x.empreinte in _valeurs(j) for x in banc.db.jetons)
    # Addendum 2 (A5) : le verrou de transaction est demandé à chaque émission, avant de révoquer et d'insérer.
    assert len(banc.db.verrous) == 3
    assert all("pg_advisory_xact_lock" in texte and p == {"cle": agent.VERROU_JETON} for texte, p in banc.db.verrous)


# --- 12 · le Centre : l'administrateur seul ------------------------------------------------------------


def test_centre_admin_seul(banc):
    c = banc.centre
    for acteur in (MEMBRE, ADJOINT):
        en_tant_que(banc, acteur)
        for methode, chemin in (("GET", "/api/command/agent"), ("POST", "/api/command/agent/jeton"),
                                ("DELETE", "/api/command/agent/jeton")):
            r = c.request(methode, chemin)
            assert r.status_code == 403 and r.json() == {"detail": "Réservé à l'administrateur."}, (acteur["name"], methode)
    # Avant toute lecture en base, et rien d'écrit.
    assert not banc.db.tables and not banc.db.journal and not banc.db.jetons and banc.db.commits == 0

    en_tant_que(banc, ADMIN)
    assert c.get("/api/command/agent").json() == {"jeton": None, "recus": []}
    jeton = donner_un_jeton(banc.db)
    base = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    for i in range(25):
        banc.db.recus.append(AgentRrlog(
            id=100 + i, sha256=f"{i:064x}", fichier=f"rr_{i}.rrlog", chemin=f"_agent/{i}", taille_gz=10, taille=2048 * (i + 1),
            recu_le=base + timedelta(hours=i), jeton_id=1, mission=f"M{i}", theatre="SYRIA", date_mission="1985-06-14",
            etat="en_attente"))
    etat = c.get("/api/command/agent").json()
    assert set(etat) == {"jeton", "recus"}
    assert set(etat["jeton"]) == {"emis_le", "emis_par", "dernier_envoi_le"}
    assert etat["jeton"]["emis_par"] == {"id": ADMIN["id"], "nom": "Kestrel"} and etat["jeton"]["dernier_envoi_le"] is None
    assert jeton not in json.dumps(etat)
    # Les 20 plus récents, le plus récent d'abord, dans la forme de R10.
    assert [x["fichier"] for x in etat["recus"]] == [f"rr_{i}.rrlog" for i in range(24, 4, -1)]
    assert set(etat["recus"][0]) == {"recu_le", "fichier", "mission", "theatre", "date_mission", "taille", "etat"}
    assert etat["recus"][0]["taille"] == 2048 * 25 and etat["recus"][0]["etat"] == "en_attente"
    assert etat["recus"][0]["recu_le"] == (base + timedelta(hours=24)).isoformat()
    # Le dernier envoi, une fois posé, se lit.
    banc.db.jetons[0].dernier_envoi_le = base
    assert c.get("/api/command/agent").json()["jeton"]["dernier_envoi_le"] == base.isoformat()
