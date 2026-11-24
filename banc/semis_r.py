"""Semis des relances -- banc seulement, jamais dans une archive (banc v4, lot « Les relances »).
À lancer APRÈS semis.py et semis_e.py, depuis la copie d'essai (cwd), environnement de test chargé
(prepare_cc.sh le fait). Déterministe. Scénario du 02/10/2026 : fenêtre du 04/09 au 01/10.

1 · Des réponses, pour que la liste ressemble à la production (un retard par escadrille au plus, sauf
    au CHARLIE-33) et que chaque cas de la règle R196 ait son pilote :
      thorn (CHARLIE-33)     dernière réponse le 14/08, hors fenêtre         -> en retard (comme en production)
      Odin (T-14)        aucune réponse                                  -> en retard
      Corsair (ALPHA-11)  sa seule réponse : un jeu libre, le 25/09       -> à jour : le jeu libre compte
      Lancer (BRAVO-22)   sa seule réponse : « peut-être », le 29/09      -> à jour : peut-être compte
      tous les autres profils du semis des organigrammes : présents le 24/09
    Du semis de base : Jamais (aucune réponse), Kerberos (20/08) et Fog (une réponse à une occurrence
    annulée) en retard ; Viper à jour par sa seule réponse à venir ; Hunter pas encore jugé (27/09) ;
    Nomad Free Agent ; Ancien archivé.
2 · Le rôle « Officier » (444444444444444444), porté par MistyKestrel42, Ghost, Fog et Ancien (archivé).
    Fog refuse les MP (<mode>.refus).
3 · Le faux Discord fidèle à la base : tout profil non archivé, avec ses rôles -- sinon l'appel
    archiverait les profils du semis des organigrammes, absents de la liste. Aucun arrivant.
Usage : python3 -B semis_r.py <membres.json> <fichier_mode>"""
import asyncio, json, sys, uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, ".")
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db import AsyncSessionLocal
from app.models import Event, Presence, Profile

PARIS = ZoneInfo("Europe/Paris")
OFFICIER = "444444444444444444"
PORTEURS = (100000000000000001, 200000000000000004, 200000000000000006, 200000000000000008)
REFUSE = 200000000000000006   # Fog


def t(d, h=10, m=0):
    return datetime.combine(d, datetime.min.time()).replace(hour=h, minute=m, tzinfo=PARIS)


async def main():
    async with AsyncSessionLocal() as db:
        ev = {e.title: e.id for e in (await db.execute(select(Event))).scalars()}
        e1, e3 = ev["Entraînement"], ev["Jeu libre"]
        noms = {p.global_name: p.id for p in (await db.execute(
            select(Profile).where(Profile.id >= 400000000000000001))).scalars()}
        lignes = []

        def rep(nom, eid, jour, etat, cree):
            lignes.append(dict(id=uuid.uuid4(), event_id=eid, occ_date=jour, profile_id=noms[nom], state=etat,
                               created_at=cree, updated_at=cree))
        rep("thorn", e3, date(2026, 8, 14), "present", t(date(2026, 8, 14)))
        rep("Corsair", e3, date(2026, 9, 25), "present", t(date(2026, 9, 24)))
        rep("Lancer", e1, date(2026, 9, 29), "maybe", t(date(2026, 9, 28)))
        for nom in sorted(noms):
            if nom not in ("thorn", "Odin", "Corsair", "Lancer"):
                rep(nom, e1, date(2026, 9, 24), "present", t(date(2026, 9, 23)))
        await db.execute(pg_insert(Presence).values(lignes))
        for pid in PORTEURS:
            p = await db.get(Profile, pid)
            await db.execute(update(Profile).where(Profile.id == pid)
                             .values(roles_snapshot=sorted(set(p.roles_snapshot or []) | {OFFICIER})))
        await db.commit()
        profils = (await db.execute(select(Profile).where(Profile.archived_at.is_(None))
                                    .order_by(Profile.id))).scalars().all()
    ms = [{"user": {"id": str(p.id), "username": p.username, "global_name": p.global_name, "avatar": None},
           "nick": None, "roles": list(p.roles_snapshot or []), "joined_at": "2026-07-01T00:00:00+00:00"}
          for p in profils]
    json.dump(ms, open(sys.argv[1], "w"), indent=1)
    open(sys.argv[2] + ".refus", "w").write(f"{REFUSE}\n")
    print(f"semis des relances : {len(lignes)} réponses · rôle Officier sur {len(PORTEURS)} profils"
          f" · faux Discord : {len(ms)} membres · refus de MP : Fog")

asyncio.run(main())
