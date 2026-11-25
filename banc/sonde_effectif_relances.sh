#!/bin/sh
# Ready Room -- sonde « L'effectif complet » et « Les relances ». LECTURE SEULE.
#   A · qui entrerait si l'appel listait tout le serveur Discord (règle R183) ;
#   B · qui serait en retard de planning : pilotes d'escadrille sans aucune
#       réponse (présent, peut-être, absent) aux occurrences des 28 derniers
#       jours, s'il y en a eu (décision du 2 octobre : a2, 4 semaines, Free
#       Agents exclus).
# Rien n'est écrit : transaction PostgreSQL en lecture seule, et seulement des
# lectures (GET) vers Discord.
# Usage, depuis n'importe quel dossier :  sh sonde_effectif_relances.sh
cd ~/readyroom || exit 1
docker compose exec -T -e PYTHONIOENCODING=utf-8 app python -B - <<'PYEOF'
import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func, select, text

from app.appel import peut_entrer
from app.auth import _app_access_role_ids
from app.config import settings
from app.db import AsyncSessionLocal
from app.discord_rsvp import _bot_request
from app.events import _load_events_and_overrides
from app.models import Presence, Profile, Squadron, SquadronMembership
from app.recurrence import REFERENCE_TZ, UnsupportedRecurrenceRule, expand
from app.squadron import _resolve_squadron_id

FENETRE_J = 28  # 4 semaines (décision du 2 octobre)
PAGE = 1000     # maximum de Discord par page
PAGES_MAX = 50
DEPARTS = (10007, 10013)  # membre inconnu, compte supprimé


def nom_membre(m):
    u = m.get("user") or {}
    return m.get("nick") or u.get("global_name") or u.get("username") or "?"


def nom_profil(p):
    return p.global_name or p.username


def jjmm(dt):
    return dt.astimezone(REFERENCE_TZ).strftime("%d/%m") if dt else "jamais"


def code_de(r):
    try:
        corps = r.json()
    except ValueError:
        return None
    return corps.get("code") if isinstance(corps, dict) else None


async def lister():
    """Tous les membres du serveur, page par page : (membres, None) ou (None, motif)."""
    membres, apres = [], "0"
    for _ in range(PAGES_MAX):
        r = await _bot_request(
            "GET", f"/guilds/{settings.DISCORD_GUILD_ID}/members?limit={PAGE}&after={apres}"
        )
        if r is None:
            return None, "Discord injoignable"
        if r.status_code != 200:
            code = code_de(r)
            motif = f"réponse HTTP {r.status_code}" + (f" (code {code})" if code is not None else "")
            if r.status_code == 403:
                motif += " -- l'interrupteur « Server Members Intent » n'est sans doute pas activé"
            return None, motif
        try:
            page = r.json()
        except ValueError:
            return None, "réponse illisible"
        if not isinstance(page, list):
            return None, "réponse inattendue"
        membres += page
        if len(page) < PAGE:
            break
        apres = str(max(int(m["user"]["id"]) for m in page))
    else:
        return None, f"plus de {PAGES_MAX} pages"
    if not membres:
        return None, "liste vide -- l'interrupteur « Server Members Intent » n'est sans doute pas activé"
    return membres, None


async def partie_a(db):
    """Rend le nombre d'arrivants d'escadrille (None si la partie A s'arrête)."""
    print("=== A · L'effectif complet : qui entrerait si l'appel listait le serveur ===")
    membres, motif = await lister()
    if motif:
        print(f"  Arrêt : {motif}. Rien à conclure sur la partie A.")
        return None
    humains = [m for m in membres if not (m.get("user") or {}).get("bot")]
    print(f"  Discord : {len(membres)} membres listés, dont {len(membres) - len(humains)} bot(s).")

    profils = {p.id: p for p in (await db.execute(select(Profile))).scalars().all()}
    listes = {int(m["user"]["id"]) for m in humains}
    connus = [p for p in profils.values() if p.archived_at is None]
    partis = []
    for p in sorted((p for p in connus if p.id not in listes), key=lambda p: nom_profil(p).casefold()):
        r = await _bot_request("GET", f"/guilds/{settings.DISCORD_GUILD_ID}/members/{p.id}")
        if r is not None and r.status_code == 404 and code_de(r) in DEPARTS:
            partis.append(p)
            continue
        etat = "rien (Discord injoignable)" if r is None else f"HTTP {r.status_code}"
        print(f"  Arrêt : {nom_profil(p)} manque à la liste, sa lecture directe répond {etat}"
              " -- liste incomplète, rien à conclure sur la partie A.")
        return None
    if partis:
        print(f"  Profils connus non archivés : {len(connus)} -- {len(connus) - len(partis)} dans la liste,"
              f" {len(partis)} parti(s) du serveur depuis le dernier appel : "
              + ", ".join(nom_profil(p) for p in partis))
    else:
        print(f"  Profils connus non archivés : {len(connus)} -- tous dans la liste ✓")

    porte = await _app_access_role_ids(db)
    escadrilles = (await db.execute(select(Squadron.id, Squadron.designation).order_by(Squadron.id))).all()
    arrivants, ecartes = defaultdict(list), 0
    for m in humains:
        uid = int(m["user"]["id"])
        if uid in profils:
            continue
        roles = {str(x) for x in m.get("roles", [])}
        sq = await _resolve_squadron_id(db, roles)
        if sq is not None:
            arrivants[sq].append(nom_membre(m))
        elif peut_entrer(uid, roles, porte):
            arrivants["FA"].append(nom_membre(m))
        else:
            ecartes += 1

    print(f"  Entreraient : {sum(len(v) for v in arrivants.values())}")
    for sq_id, designation in escadrilles:
        if arrivants.get(sq_id):
            noms = sorted(arrivants[sq_id], key=str.casefold)
            print(f"    {designation} · {len(noms)} : " + ", ".join(noms))
    if arrivants.get("FA"):
        noms = sorted(arrivants["FA"], key=str.casefold)
        print(f"    Free Agents · {len(noms)} : " + ", ".join(noms))
    print(f"  Laissés de côté (ni rôle d'escadrille ni droit d'entrée) : {ecartes}")
    return sum(len(v) for k, v in arrivants.items() if k != "FA")


async def partie_b(db, arrivants_escadrille):
    print(f"=== B · Les relances : aucune réponse aux occurrences des {FENETRE_J} derniers jours ===")
    aujourdhui = datetime.now(REFERENCE_TZ).date()
    debut, fin = aujourdhui - timedelta(days=FENETRE_J), aujourdhui - timedelta(days=1)
    events, overrides = await _load_events_and_overrides(db, debut, fin)
    occs = []
    for e in events:
        try:
            occs += expand(e, overrides.get(e.id, {}), debut, fin)
        except UnsupportedRecurrenceRule:
            continue
    cles = {(o.event_id, o.occ_date) for o in occs}
    types = " · ".join(f"{t} {n}" for t, n in sorted(Counter(o.type for o in occs).items()))
    print(f"  Fenêtre : du {debut:%d/%m} au {fin:%d/%m} · {len(occs)} occurrence(s)"
          + (f" ({types})" if types else ""))

    pilotes = (await db.execute(
        select(Profile, Squadron.id, Squadron.designation, SquadronMembership.started_at)
        .join(SquadronMembership, SquadronMembership.profile_id == Profile.id)
        .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
        .where(SquadronMembership.ended_at.is_(None), Squadron.status == "actif",
               Profile.archived_at.is_(None))
    )).all()
    ids = [p.id for p, _i, _d, _s in pilotes]
    repondu, derniere = Counter(), {}
    if ids:
        for pid, eid, jour in (await db.execute(
            select(Presence.profile_id, Presence.event_id, Presence.occ_date)
            .where(Presence.profile_id.in_(ids), Presence.occ_date >= debut, Presence.occ_date <= fin)
        )).all():
            if (str(eid), jour) in cles:
                repondu[pid] += 1
        derniere = dict((await db.execute(
            select(Presence.profile_id, func.max(Presence.updated_at))
            .where(Presence.profile_id.in_(ids)).group_by(Presence.profile_id)
        )).all())

    print(f"  Pilotes d'escadrille : {len(pilotes)}")
    if not occs:
        print("  Aucune occurrence sur la fenêtre : personne n'est en retard.")
    else:
        par_escadrille = defaultdict(list)
        for p, sq_id, designation, depuis in pilotes:
            par_escadrille[(sq_id, designation)].append((p, depuis))
        lignes, total = [], 0
        for sq_id, designation in sorted(par_escadrille):
            effectif = par_escadrille[(sq_id, designation)]
            retard = sorted(((p, d) for p, d in effectif if repondu[p.id] == 0),
                            key=lambda x: nom_profil(x[0]).casefold())
            total += len(retard)
            lignes.append(f"    {designation} · {len(effectif)} pilote(s), {len(retard)} en retard")
            for p, depuis in retard:
                note = ""
                if depuis is not None and depuis.astimezone(REFERENCE_TZ).date() > debut:
                    note = f" · dans l'escadrille depuis le {jjmm(depuis)}"
                lignes.append(f"      {nom_profil(p)} -- dernière réponse : {jjmm(derniere.get(p.id))}{note}")
        print(f"  En retard aujourd'hui : {total}")
        print("\n".join(lignes))
    if arrivants_escadrille:
        print(f"  + {arrivants_escadrille} arrivant(s) d'escadrille de la partie A :"
              " aucune réponse, par construction.")


async def main():
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        version = open("VERSION", encoding="utf-8").read().strip()
        migration = (await db.execute(text("SELECT version_num FROM alembic_version"))).scalar()
        print(f"Sonde effectif & relances · Ready Room {version} · migration {migration}"
              f" · {datetime.now(REFERENCE_TZ):%d/%m/%Y}")
        print()
        arrivants = await partie_a(db)
        print()
        await partie_b(db, arrivants or 0)
        await db.rollback()


asyncio.run(main())
PYEOF
