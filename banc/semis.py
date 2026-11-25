"""Semis du banc d'essai -- lancé depuis la copie d'essai (cwd), env de test chargé.
Scénario du 02/10/2026 : fenêtre 04/09 -> 01/10. Écrit aussi membres.json (faux Discord)."""
import asyncio, json, sys, uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

sys.path.insert(0, ".")
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db import AsyncSessionLocal
from app.models import Event, OccurrenceOverride, Presence, Profile, RoleCapability, Squadron, SquadronMembership

PARIS = ZoneInfo("Europe/Paris")
R_CHARLIE, R_BRAVO, R_ALPHA = "700000000000000101", "700000000000000103", "700000000000000102"
PILOTE, PROBA, VISITEUR = "111111111111111111", "222222222222222222", "333333333333333333"

def t(d, h=20, m=30):
    return datetime.combine(d, datetime.min.time()).replace(hour=h, minute=m, tzinfo=PARIS)

P = {  # id : (nom, rôles Discord, escadrille, depuis)
    100000000000000001: ("MistyKestrel42", [R_CHARLIE, PILOTE], "CHARLIE-33", date(2026, 8, 1)),
    200000000000000001: ("Dragoon-1", [R_CHARLIE, PILOTE], "CHARLIE-33", date(2026, 8, 1)),
    200000000000000002: ("Kerberos", [R_CHARLIE, PILOTE], "CHARLIE-33", date(2026, 8, 1)),
    200000000000000003: ("Viper", [R_CHARLIE, PILOTE], "CHARLIE-33", date(2026, 8, 1)),
    200000000000000004: ("Ghost", [R_BRAVO, PILOTE], "BRAVO-22", date(2026, 8, 1)),
    200000000000000005: ("Hunter", [R_ALPHA, PILOTE], "ALPHA-11", date(2026, 9, 27)),
    200000000000000006: ("Fog", [R_ALPHA, PILOTE], "ALPHA-11", date(2026, 8, 1)),
    200000000000000007: ("Nomad", [PILOTE], None, None),
    200000000000000009: ("Jamais", [R_CHARLIE, PILOTE], "CHARLIE-33", date(2026, 8, 1)),
    200000000000000010: ("Rover", [R_BRAVO, PILOTE], "BRAVO-22", date(2026, 8, 1)),
}
ANCIEN = 200000000000000008

async def main():
    async with AsyncSessionLocal() as db:
        sq = {}
        for nom, role in (("CHARLIE-33", R_CHARLIE), ("BRAVO-22", R_BRAVO), ("ALPHA-11", R_ALPHA)):
            s = Squadron(designation=nom, status="actif", discord_role_id=role, wing_id=1)
            db.add(s); await db.flush(); sq[nom] = s.id
        db.add(Squadron(designation="Escadrille en sommeil", status="sommeil", discord_role_id=None, wing_id=1))
        for pid, (nom, roles, esc, depuis) in P.items():
            db.add(Profile(id=pid, username=nom.lower(), global_name=nom, roles_snapshot=roles,
                           squadron=esc or "Free Agent", locale="fr", tz="Europe/Paris"))
        db.add(Profile(id=ANCIEN, username="ancien", global_name="Ancien", roles_snapshot=[],
                       squadron="Free Agent", locale="fr", tz="Europe/Paris",
                       archived_at=t(date(2026, 9, 15), 12)))
        await db.flush()
        for pid, (nom, roles, esc, depuis) in P.items():
            if esc:
                db.add(SquadronMembership(profile_id=pid, squadron_id=sq[esc], started_at=t(depuis, 12)))
        db.add(SquadronMembership(profile_id=ANCIEN, squadron_id=sq["CHARLIE-33"], started_at=t(date(2026, 8, 1), 12),
                                  ended_at=t(date(2026, 9, 15), 12)))
        chef = 100000000000000001
        E1 = Event(id=uuid.uuid4(), type="entrainement", title="Entraînement", description="",
                   start_at=t(date(2026, 8, 4)), recurrence={"freq": "weekly", "interval": 1, "weekdays": [1, 3]},
                   created_by=chef)
        E2 = Event(id=uuid.uuid4(), type="mission", title="Mission Francfort", description="",
                   start_at=t(date(2026, 9, 20), 14, 0), created_by=chef)
        E3 = Event(id=uuid.uuid4(), type="jeulibre", game_label="Arma", title="Jeu libre", description="",
                   start_at=t(date(2026, 8, 14), 21, 0), recurrence={"freq": "weekly", "interval": 1, "weekdays": [4]},
                   created_by=chef)
        E4 = Event(id=uuid.uuid4(), type="mission", title="Mission future", description="",
                   start_at=t(date(2026, 10, 5)), created_by=chef)
        E5 = Event(id=uuid.uuid4(), type="mission", title="Mission ancienne", description="",
                   start_at=t(date(2026, 8, 23)), created_by=chef)
        db.add_all([E1, E2, E3, E4, E5]); await db.flush()
        db.add(OccurrenceOverride(event_id=E1.id, occ_date=date(2026, 9, 15), status="cancelled"))
        db.add(OccurrenceOverride(event_id=E3.id, occ_date=date(2026, 9, 18), status="modified",
                                  patch={"type": "mission", "title": "Mission surprise"}))
        await db.flush()

        lignes = []
        def rep(pid, ev, jour, etat, cree):
            lignes.append(dict(event_id=ev.id, occ_date=jour, profile_id=pid, state=etat,
                               created_at=cree, updated_at=cree))
        f1 = 200000000000000001
        rep(f1, E1, date(2026, 9, 8), "present", t(date(2026, 9, 7), 10))
        rep(f1, E1, date(2026, 9, 10), "present", t(date(2026, 9, 9), 10))
        rep(f1, E1, date(2026, 9, 17), "maybe", t(date(2026, 9, 16), 10))
        rep(200000000000000002, E5, date(2026, 8, 23), "present", t(date(2026, 8, 20), 10))
        rep(200000000000000003, E4, date(2026, 10, 5), "present", t(date(2026, 10, 1), 18))
        # Ghost : réponse « toute la série » du 23/08, horizon 90 jours (dates de E1)
        d = date(2026, 8, 23)
        while d <= date(2026, 11, 21):
            if d.weekday() in (1, 3):
                rep(200000000000000004, E1, d, "present", t(date(2026, 8, 23), 9))
            d += timedelta(days=1)
        rep(200000000000000006, E1, date(2026, 9, 15), "present", t(date(2026, 9, 12), 10))  # annulée depuis
        rep(ANCIEN, E1, date(2026, 9, 8), "present", t(date(2026, 9, 7), 11))
        rep(200000000000000010, E2, date(2026, 9, 20), "absent", t(date(2026, 9, 18), 10))
        rep(chef, E3, date(2026, 9, 18), "present", t(date(2026, 9, 17), 10))
        await db.execute(pg_insert(Presence).values(lignes))
        # Banc v8 (lot « Le banc et les droits ») : depuis le `v1.0111` la base fait autorité seule sur l'accès à
        # l'application (`app.access`) ; sans cette ligne, seul l'administrateur entre au banc.
        await db.execute(pg_insert(RoleCapability).values(role_id=PILOTE, capability="app.access")
                         .on_conflict_do_nothing())
        await db.commit()
        print("semis :", len(P) + 1, "profils ·", len(lignes), "réponses")

    # Le faux serveur Discord : les connus non archivés (Ancien est parti) + les arrivants
    def membre(uid, username, roles, nick=None, gname=None, bot=False):
        u = {"id": str(uid), "username": username, "global_name": gname, "avatar": None}
        if bot:
            u["bot"] = True
        return {"user": u, "nick": nick, "roles": roles, "joined_at": "2026-07-01T00:00:00+00:00"}
    ms = [membre(pid, nom.lower(), roles, gname=nom) for pid, (nom, roles, _e, _d) in P.items()]
    ms += [
        membre(300000000000000001, "tapir_u", [R_CHARLIE, PILOTE], nick="Tapir", gname="Tapir_gn"),
        membre(300000000000000002, "lace_u", [R_BRAVO], gname="Lace"),
        membre(300000000000000003, "echo_u", [PILOTE], gname="Echo"),
        membre(300000000000000004, "bravo_u", [R_ALPHA, R_CHARLIE], gname="Bravo"),
        membre(300000000000000005, "visiteur_u", [VISITEUR], gname="Visiteur"),
        membre(300000000000000006, "mee6", [PILOTE], gname="MEE6", bot=True),
        membre(300000000000000008, "delta_u", [PROBA], nick="Delta", gname="Delta_gn"),
    ]
    json.dump(ms, open(sys.argv[1], "w"), indent=1)
    print("faux Discord :", len(ms), "membres")

asyncio.run(main())
