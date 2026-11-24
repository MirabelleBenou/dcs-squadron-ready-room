"""Calcul de référence des retards de planning (banc v4) -- LECTURE SEULE, jamais dans une archive.
La règle telle que le cadrage du lot « Les relances » l'écrit (R196, et le choix 2a1 du 03/10) :
un pilote est en retard s'il est dans une escadrille ACTIVE, profil non archivé, depuis au moins
28 jours ; si la fenêtre [aujourd'hui - 28 j, aujourd'hui - 1 j] compte au moins une occurrence
effective ; et s'il n'a répondu (présent, peut-être, absent) à AUCUNE occurrence effective, ni de la
fenêtre, ni à venir (aujourd'hui compris, 90 jours). Occurrences effectives : expand(), annulations
exclues, tous types. Dernière réponse : la plus récente date de création d'une réponse.
Depuis la copie d'essai, environnement de test chargé. Usage : python3 -B retards_ref.py [AAAA-MM-JJ]"""
import asyncio, sys
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, ".")
from sqlalchemy import func, select, text
from app.db import AsyncSessionLocal
from app.events import _load_events_and_overrides
from app.models import Presence, Profile, Squadron, SquadronMembership
from app.recurrence import REFERENCE_TZ, UnsupportedRecurrenceRule, expand

FENETRE_J, HORIZON_J = 28, 90


async def occurrences(db, debut, fin):
    events, overrides = await _load_events_and_overrides(db, debut, fin)
    occs = []
    for e in events:
        try:
            occs += expand(e, overrides.get(e.id, {}), debut, fin)
        except UnsupportedRecurrenceRule:
            continue
    return {(str(o.event_id), o.occ_date) for o in occs}


async def main():
    jour = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(REFERENCE_TZ).date()
    debut, fin = jour - timedelta(days=FENETRE_J), jour - timedelta(days=1)
    async with AsyncSessionLocal() as db:
        await db.execute(text("SET TRANSACTION READ ONLY"))
        fenetre = await occurrences(db, debut, fin)
        a_venir = await occurrences(db, jour, jour + timedelta(days=HORIZON_J))
        pilotes = (await db.execute(
            select(Profile.id, Profile.global_name, Profile.username, Squadron.id, Squadron.designation,
                   SquadronMembership.started_at)
            .join(SquadronMembership, SquadronMembership.profile_id == Profile.id)
            .join(Squadron, Squadron.id == SquadronMembership.squadron_id)
            .where(SquadronMembership.ended_at.is_(None), Squadron.status == "actif",
                   Profile.archived_at.is_(None)))).all()
        ids = [p[0] for p in pilotes]
        rep = defaultdict(int)
        for pid, eid, j in (await db.execute(
                select(Presence.profile_id, Presence.event_id, Presence.occ_date)
                .where(Presence.profile_id.in_(ids), Presence.occ_date >= debut))).all():
            if (str(eid), j) in fenetre or (str(eid), j) in a_venir:
                rep[pid] += 1
        derniere = dict((await db.execute(
            select(Presence.profile_id, func.max(Presence.created_at))
            .where(Presence.profile_id.in_(ids)).group_by(Presence.profile_id))).all())
        await db.rollback()
    print(f"jour {jour:%d/%m/%Y} · fenêtre {debut:%d/%m} → {fin:%d/%m} · {len(fenetre)} occurrence(s) effective(s)"
          f" · {len(a_venir)} à venir")
    if not fenetre:
        print("aucune occurrence sur la fenêtre : personne n'est en retard")
        return
    par = defaultdict(list)
    for pid, gname, uname, sq_id, desig, depuis in pilotes:
        if depuis.astimezone(REFERENCE_TZ).date() > jour - timedelta(days=FENETRE_J):
            continue
        if rep[pid] == 0:
            d = derniere.get(pid)
            par[(sq_id, desig)].append((gname or uname, d.astimezone(REFERENCE_TZ).strftime("%d/%m") if d else None))
    n = sum(len(v) for v in par.values())
    print(f"en retard : {n}")
    for (sq_id, desig), lst in sorted(par.items()):
        print(f"  {desig} : " + " · ".join(f"{nom} ({d or 'aucune réponse'})"
                                           for nom, d in sorted(lst, key=lambda x: x[0].casefold())))

asyncio.run(main())
