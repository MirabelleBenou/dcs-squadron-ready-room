"""Lot « Le banc et les droits » (`RR-V1.0.0+1`, ARC-21) -- la carte des droits, en
données, gardée par un test : pour chaque route de l'application et chacun de dix
rôles, qui entre et qui est refusé.

Deux pièces de données, à côté de ce fichier :
- `droits_routes.tsv` : une ligne par route et méthode, une colonne par rôle. Une
  case vaut `401` ou `403` (un refus : le code exact, et aucune table ne change),
  `307` (une redirection, sa `Location` se lit), `L` (une lecture permise : la porte
  passe, ni 401 ni 403), `E` (une écriture permise : non jouée, son effet est
  l'affaire des tests de chaque module) ou `exclu` (non jouée : OAuth Discord, le
  flux) ;
- `droits_entrees.json` : pour les routes qui demandent une entrée valide pour
  atteindre leur garde (sans elle, un 422 masque le refus), le corps, la chaîne de
  requête ou les en-têtes. Les marques `{event_id}`, `{session_id}`… se remplacent
  comme dans le chemin.

Deux fonctions de test :
- `test_chaque_route_a_sa_ligne` (sans base) : l'ensemble des routes de la table
  égale celui de `app.routes` -- une route neuve sans sa ligne fait échouer la suite ;
- `test_droits_sur_postgresql` : joue chaque refus, chaque redirection et chaque
  lecture permise contre une vraie base PostgreSQL, dont l'adresse est dans
  `RR_TEST_PG_URL`. Sans elle, le volet est sauté : la carte se joue au banc, phase
  `droits`.

Le volet PostgreSQL sème lui-même le minimum dont chaque case a besoin. Les rôles,
leurs identifiants et le cookie signé sont ceux de l'instrument du pré-cadrage.

Aucun réseau : les routes qui appellent Discord (`discord-roles`, `invites/verifier`…)
passent leur porte, puis leur appel part vers `discord.com` même sans jeton de bot
(`_bot_request`). Le volet ferme donc `httpx.AsyncClient.send` : l'appel échoue comme sans
réseau, l'application attrape `httpx.HTTPError`, et rien ne sort de la machine."""
from __future__ import annotations

import asyncio
import base64
import csv
import json
import os
import subprocess
import sys
import warnings
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : il
# fausserait la ligne de `pytest`. On n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

from fastapi.routing import APIRoute
from itsdangerous import TimestampSigner

TABLE = Path(__file__).resolve().parent / "droits_routes.tsv"
ENTREES = Path(__file__).resolve().parent / "droits_entrees.json"

ROLES = ["anon", "inv", "mbr", "crea", "edany", "sessed", "deb", "adj", "chef", "adm"]
VALEURS = {"401", "403", "307", "L", "E", "exclu"}

# Les identifiants de la carte (ceux de l'instrument du pré-cadrage).
PILOTE = "111111111111111111"  # le rôle Discord que porte tout membre
ROLE = {"crea": "810000000000000001", "edany": "810000000000000002", "sessed": "810000000000000003",
        "deb": "810000000000000004", "chef": "810000000000000005"}
ADM, HUNTER, INV, AUTRE = 100000000000000001, 200000000000000005, 500000000000000001, 200000000000000003
# Un profil par rôle de la carte : (identifiant, rôles Discord du profil).
PROFILS = {"mbr": (600000000000000000, [PILOTE]),
           "crea": (600000000000000001, [PILOTE, ROLE["crea"]]),
           "edany": (600000000000000002, [PILOTE, ROLE["edany"]]),
           "sessed": (600000000000000003, [PILOTE, ROLE["deb"], ROLE["sessed"]]),
           "deb": (600000000000000004, [PILOTE, ROLE["deb"]]),
           "chef": (600000000000000005, [PILOTE, ROLE["chef"]])}
# Les capacités des rôles Discord (`role_capabilities`).
CAPACITES = [(PILOTE, "app.access"), (ROLE["crea"], "event.create"), (ROLE["edany"], "event.edit_any"),
             (ROLE["sessed"], "session.edit"), (ROLE["deb"], "debrief.access"), (ROLE["chef"], "command.access")]


def _lire_table() -> dict[tuple[str, str], dict[str, str]]:
    with open(TABLE, encoding="utf-8", newline="") as f:
        lignes = list(csv.reader(f, delimiter="\t"))
    assert lignes[0] == ["methode", "chemin"] + ROLES, "en-tête de la table des droits"
    table: dict[tuple[str, str], dict[str, str]] = {}
    for ligne in lignes[1:]:
        assert len(ligne) == 2 + len(ROLES), f"ligne mal formée : {ligne}"
        cle = (ligne[0], ligne[1])
        assert cle not in table, f"ligne en double : {cle}"
        table[cle] = dict(zip(ROLES, ligne[2:]))
    return table


def _routes_de_l_application() -> set[tuple[str, str]]:
    from app.main import app

    return {(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods if m != "HEAD"}


def test_chaque_route_a_sa_ligne():
    """Sans base : la table égale `app.routes`, chaque case est l'une des six valeurs, chaque
    entrée vise une ligne de la table."""
    table = _lire_table()
    routes = _routes_de_l_application()
    sans_ligne = sorted(routes - set(table))
    sans_route = sorted(set(table) - routes)
    assert not sans_ligne, "routes sans ligne dans tests/droits_routes.tsv : " + ", ".join(
        f"{m} {p}" for m, p in sans_ligne)
    assert not sans_route, "lignes de tests/droits_routes.tsv sans route : " + ", ".join(
        f"{m} {p}" for m, p in sans_route)
    for cle, cases in table.items():
        for role, valeur in cases.items():
            assert valeur in VALEURS, f"{cle[0]} {cle[1]} {role} : « {valeur} » n'est pas une valeur permise"
    entrees = json.loads(ENTREES.read_text(encoding="utf-8"))
    inconnues = [k for k in entrees if tuple(k.split(" ", 1)) not in table]
    assert not inconnues, f"entrées sans ligne dans la table : {inconnues}"


# --- Le volet PostgreSQL ------------------------------------------------------------------------


def _dsn_asyncpg(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _cookie(role: str, secret: str) -> str | None:
    """Le cookie `session` que signe `SessionMiddleware` : `b64(json)` signé par `itsdangerous`."""
    if role == "anon":
        return None
    exp = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    if role == "inv":
        session = {"id": str(INV), "name": "Invité", "roles": [], "lang": "fr", "avatar": None,
                   "squadron": None, "exp": exp, "invite": True}
    else:
        pid = {"adj": HUNTER, "adm": ADM}.get(role) or PROFILS[role][0]
        session = {"id": str(pid), "name": role, "roles": [], "lang": "fr", "avatar": None,
                   "squadron": None, "exp": exp}
    donnees = base64.b64encode(json.dumps(session).encode())
    return TimestampSigner(secret).sign(donnees).decode()


async def _semer(url: str) -> dict[str, str]:
    """Le minimum dont chaque case a besoin pour atteindre sa garde, sur une base migrée et vide :
    dix rôles (profils, rôles Discord, capacités, l'adjoint d'une escadrille, une invitation active,
    l'administrateur) et les objets que nomment les chemins et les entrées."""
    import asyncpg

    c = await asyncpg.connect(_dsn_asyncpg(url))
    try:
        if await c.fetchval("SELECT count(*) FROM profiles"):
            pytest.fail("RR_TEST_PG_URL : la base doit être neuve (migrée, sans profil)")
        # Les profils : l'administrateur, l'adjoint, un profil neutre (créateur de l'évènement, cible
        # des chemins `{profile_id}`), puis un par rôle. Un profil ne porte que le rôle Pilote et ses rôles.
        profils = [(ADM, "carte-adm", [PILOTE]), (HUNTER, "carte-adj", [PILOTE]), (AUTRE, "carte-autre", [PILOTE])]
        profils += [(pid, "carte-" + nom, roles) for nom, (pid, roles) in PROFILS.items()]
        for pid, nom, roles in profils:
            await c.execute(
                "INSERT INTO profiles(id, username, global_name, locale, tz, roles_snapshot) "
                "VALUES($1, $2, $2, 'fr', 'Europe/Paris', $3::jsonb)", pid, nom, json.dumps(roles))
        # Les capacités des rôles Discord.
        for role_id, capacite in CAPACITES:
            await c.execute("INSERT INTO role_capabilities(role_id, capability) VALUES($1, $2)", role_id, capacite)
        # Une invitation active (l'invité n'a pas de profil).
        await c.execute(
            "INSERT INTO invitations(discord_id, nom, username, invite_par, jusqua) "
            "VALUES($1, 'Invité carte', 'invite-carte', $2, now() + interval '10 days')", INV, ADM)
        # Deux escadrilles actives : celle des chemins `{squadron_id}`, et celle dont Hunter est adjoint
        # (il n'est donc pas adjoint de celle que visent les chemins). L'escadre est celle des migrations.
        wing_id = await c.fetchval("SELECT id FROM wing ORDER BY id LIMIT 1")
        ids: dict[str, str] = {}
        for cle, designation in (("squadron_id", "CHARLIE-33"), ("squadron_adj", "ALPHA-11")):
            ids[cle] = str(await c.fetchval(
                "INSERT INTO squadron(designation, status, wing_id) VALUES($1, 'actif', $2) RETURNING id",
                designation, wing_id))
        await c.execute(
            "INSERT INTO squadron_membership(id, profile_id, squadron_id, started_at, role) "
            "VALUES(gen_random_uuid(), $1, $2, now(), 'deputy')", HUNTER, int(ids["squadron_adj"]))
        # Un évènement unique, créé par le profil neutre : aucun des dix rôles n'en est le créateur.
        ids["event_id"] = str(await c.fetchval(
            "INSERT INTO events(id, type, title, description, start_at, created_by) "
            "VALUES(gen_random_uuid(), 'entrainement', 'Évènement carte', '', '2026-12-01T18:00:00+00', $1) "
            "RETURNING id", AUTRE))
        ids["occ_date"] = "2026-12-01"
        ids["profile_id"] = str(AUTRE)
        # Une campagne, une session de Débrief avec un vol, un dépôt.
        ids["campaign_id"] = str(await c.fetchval(
            "INSERT INTO campaign(id, name, status) VALUES(gen_random_uuid(), 'Campagne carte', 'en_cours') "
            "RETURNING id"))
        ids["session_id"] = str(await c.fetchval(
            "INSERT INTO debrief_session(id, title, acmi_present) "
            "VALUES(gen_random_uuid(), 'Session carte', false) RETURNING id"))
        ids["flight_id"] = str(await c.fetchval(
            "INSERT INTO debrief_flight(id, session_id, aircraft_type, identity_state, stats) "
            "VALUES(gen_random_uuid(), $1::uuid, 'Mi-24P', 'anonyme', '{}'::jsonb) RETURNING id", ids["session_id"]))
        ids["upload_id"] = str(await c.fetchval(
            "INSERT INTO debrief_upload(id, session_id, kind, filename, sha256) "
            "VALUES(gen_random_uuid(), $1::uuid, 'acmi', 'carte.acmi', 'carte-sha256') RETURNING id",
            ids["session_id"]))
        return ids
    finally:
        await c.close()


async def _comptes(c) -> dict[str, int]:
    """Le nombre de lignes de chaque table du schéma `public`."""
    tables = [r[0] for r in await c.fetch("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")]
    requete = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM \"{t}\"" for t in tables)
    return {r[0]: r[1] for r in await c.fetch(requete)}


def _remplir(texte: str, ids: dict[str, str]) -> str:
    valeurs = {**ids, "discord_id": str(INV), "cle": "WING_ID", "fichier": "inexistant.dump",
               "z": "0", "x": "0", "y": "0"}
    for k, v in valeurs.items():
        texte = texte.replace("{" + k + "}", v)
    return texte


def _location_attendue(methode: str, chemin: str, role: str) -> tuple[str, str]:
    """(forme, valeur) de la `Location` d'un 307 : `("egal", …)` ou `("debut", …)`."""
    if chemin in ("/outils/mission-plan", "/outils/mission-tools", "/manuel"):
        return "egal", chemin + "/"  # sans barre finale : le même chemin suivi de `/`, pour tous
    if role == "anon":
        return "egal", "/"  # sans session : la page de connexion
    return "debut", "https://"  # une session, aucune suite déposée : le repli GitHub


def test_droits_sur_postgresql(monkeypatch, tmp_path):
    """Chaque refus rend son code et ne change aucune table ; chaque redirection rend sa `Location` ;
    chaque lecture permise passe la porte. Les écarts s'accumulent : un seul échec, avec la liste."""
    url = os.environ.get("RR_TEST_PG_URL")
    if not url:
        pytest.skip("RR_TEST_PG_URL absent : la carte des droits se joue au banc, phase droits")

    import asyncpg
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    import app.auth as auth
    import app.db as appdb
    from app.config import settings
    from app.main import app

    table = _lire_table()
    entrees = json.loads(ENTREES.read_text(encoding="utf-8"))

    # 1. La base : migrée à la tête, puis semée. `alembic` lit `DATABASE_URL` : un sous-processus.
    env = {**os.environ, "DATABASE_URL": url, "PYTHONDONTWRITEBYTECODE": "1"}
    migration = subprocess.run([sys.executable, "-B", "-m", "alembic", "upgrade", "head"], cwd=RACINE, env=env,
                               capture_output=True, text=True, timeout=110)
    assert migration.returncode == 0, "alembic upgrade head : " + migration.stderr[-1500:]
    boucle = asyncio.new_event_loop()
    try:
        ids = boucle.run_until_complete(_semer(url))

        # 2. L'application sur cette base : une connexion par requête (le `TestClient` ouvre une boucle par
        # requête), l'administrateur de la carte, aucun dossier hors du dossier temporaire, aucun réseau.
        moteur = create_async_engine(url, poolclass=NullPool)
        ancien_lien = appdb.AsyncSessionLocal.kw["bind"]
        monkeypatch.setattr(appdb, "engine", moteur)
        appdb.AsyncSessionLocal.configure(bind=moteur)
        monkeypatch.setattr(settings, "ADMIN_IDS", str(ADM))
        for nom in ("DEBRIEF_STORAGE_DIR", "CREST_STORAGE_DIR", "BACKUP_DIR", "SUITES_DIR", "TILES_DIR",
                    "TILES_CACHE_DIR"):
            monkeypatch.setattr(settings, nom, str(tmp_path / nom))
        monkeypatch.setattr(settings, "TILES_UPSTREAM", "http://127.0.0.1:9")
        monkeypatch.setattr(settings, "DISCORD_BOT_TOKEN", None)

        async def _reseau_ferme(self, *args, **kwargs):
            raise httpx.ConnectError("réseau fermé : la carte des droits ne sort pas de la machine")

        # Les routes qui appellent Discord (`discord-roles`, `invites/verifier`…) passent leur porte, puis
        # leur appel échoue ici, comme sans réseau : l'application l'attrape (`httpx.HTTPError`).
        monkeypatch.setattr(httpx.AsyncClient, "send", _reseau_ferme)
        auth.invalidate_app_access_cache()

        client = TestClient(app, base_url="https://t", raise_server_exceptions=False, follow_redirects=False)
        secret = str(settings.SESSION_SECRET)
        cookies = {role: _cookie(role, secret) for role in ROLES}
        compteur = boucle.run_until_complete(asyncpg.connect(_dsn_asyncpg(url)))
        ecarts: list[str] = []
        joues: Counter = Counter()
        non_joues: Counter = Counter()
        try:
            for (methode, chemin), cases in table.items():
                entree = entrees.get(f"{methode} {chemin}", {})
                url_route = _remplir(chemin, ids)
                if "query" in entree:
                    url_route += "?" + _remplir(entree["query"], ids)
                for role in ROLES:
                    attendu = cases[role]
                    if attendu in ("E", "exclu"):
                        non_joues[attendu] += 1
                        continue
                    options: dict = {"headers": dict(entree.get("headers", {}))}
                    if cookies[role]:
                        options["headers"]["Cookie"] = f"session={cookies[role]}"
                    if "json" in entree:
                        options["json"] = json.loads(_remplir(json.dumps(entree["json"]), ids))
                    if "files" in entree:
                        options["files"] = {k: (v[0], v[1].encode()) for k, v in entree["files"].items()}
                    if "data" in entree:
                        options["data"] = entree["data"]
                    client.cookies.clear()
                    refus = attendu in ("401", "403")
                    avant = boucle.run_until_complete(_comptes(compteur)) if refus else None
                    try:
                        reponse = client.request(methode, url_route, **options)
                    except Exception as e:  # une exception de l'application est un écart, pas un arrêt
                        ecarts.append(f"{methode} {chemin} {role} : {attendu} → exception {type(e).__name__}")
                        continue
                    joues[attendu] += 1
                    recu = str(reponse.status_code)
                    if refus:
                        if recu != attendu:
                            ecarts.append(f"{methode} {chemin} {role} : {attendu} → {recu}")
                        apres = boucle.run_until_complete(_comptes(compteur))
                        changees = sorted(t for t in apres if apres[t] != avant.get(t, 0))
                        if changees:
                            ecarts.append(f"{methode} {chemin} {role} : {attendu}, tables changées : "
                                          + ", ".join(changees))
                    elif attendu == "307":
                        forme, voulue = _location_attendue(methode, chemin, role)
                        location = reponse.headers.get("location", "")
                        bon = location == voulue if forme == "egal" else location.startswith(voulue)
                        if recu != "307" or not bon:
                            ecarts.append(f"{methode} {chemin} {role} : 307 {forme} « {voulue} » → {recu} « {location} »")
                    else:  # L
                        if recu in ("401", "403"):
                            ecarts.append(f"{methode} {chemin} {role} : L (ni 401 ni 403) → {recu}")
        finally:
            boucle.run_until_complete(compteur.close())
            boucle.run_until_complete(moteur.dispose())
            appdb.AsyncSessionLocal.configure(bind=ancien_lien)
            auth.invalidate_app_access_cache()
    finally:
        boucle.close()

    # Visible avec `pytest -s` : le compte des cases jouées, par valeur de la table.
    print(f"droits : {sum(joues.values())} cases jouées · 401 : {joues['401']} · 403 : {joues['403']} · "
          f"307 : {joues['307']} · L : {joues['L']} · non jouées : E {non_joues['E']}, exclu {non_joues['exclu']}")
    assert not ecarts, f"{len(ecarts)} écart(s) à la carte des droits :\n" + "\n".join(ecarts)
