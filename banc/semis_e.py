"""Semis des organigrammes -- banc seulement, jamais dans une archive.
À lancer APRÈS semis.py, depuis la copie d'essai (cwd), environnement de test chargé
(prepare_base.sh le fait). Déterministe : mêmes identifiants, mêmes noms, même ordre.

Pose la composition de production du 2/10 et les cas limites d'un organigramme d'unité :
  CHARLIE-33   7 : chef + adjoint + 5        -- composition de production
  BRAVO-22  5 : chef + 4, sans adjoint    -- composition de production
  ALPHA-11  5 : chef + adjoint + 3        -- composition de production
  T-14    14 : chef + adjoint + 12       -- une grande escadrille
  T-SANS   4 : adjoint + 3, sans chef
  T-UN     2 : chef + 1
  T-SEUL   1 : chef seul
  T-MEMB   3 : trois membres, ni chef ni adjoint"""
import asyncio, sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, ".")
from sqlalchemy import select, update
from app.db import AsyncSessionLocal
from app.models import Profile, Squadron, SquadronMembership

PARIS = ZoneInfo("Europe/Paris")
PILOTE = "111111111111111111"
ROLE = {"CHARLIE-33": "700000000000000101", "BRAVO-22": "700000000000000103", "ALPHA-11": "700000000000000102"}
# escadrille : (chef, adjoint, membres) -- noms ; les trois premières complètent le semis de base
AJOUTS = {
    "CHARLIE-33":  (None, None, ["thorn", "BANSHEE"]),
    "BRAVO-22": (None, None, ["Lancer", "Mako", "Sabre"]),
    "ALPHA-11": (None, None, ["Corsair", "Hawk", "Raven"]),
    "T-14":    ("Abel", "Brick", ["Cobra", "Drake", "Flint", "Glint", "Hatch", "Ivory", "Jinx", "Knox", "Lynx", "Moss", "Nash", "Odin"]),
    "T-SANS":  (None, "Orca", ["Pike", "Quill", "Reed"]),
    "T-UN":    ("Stone", None, ["Tusk"]),
    "T-SEUL":  ("Ulric", None, []),
    "T-MEMB":  (None, None, ["Vale", "Wren", "Yarrow"]),
}
# têtes posées sur les profils du semis de base
# Banc v6 (B5) : Hunter, adjoint du ALPHA-11, n'est PAS administrateur (ADMIN_IDS du test.env : MistyKestrel42 seule). Son
# rang d'adjoint lui ouvre le Centre -- « command.access » dans /api/me, GET /api/command/archives en 200 -- et les routes
# réservées aux administrateurs lui répondent 403 (ex. PUT /api/command/archives/automatique). Ne pas changer ce rang.
TETES_BASE = {"CHARLIE-33": (100000000000000001, 200000000000000001),   # MistyKestrel42, Dragoon-1
              "BRAVO-22": (200000000000000004, None),                 # Ghost
              "ALPHA-11": (200000000000000006, 200000000000000005)}   # Fog, Hunter
DEPUIS = datetime(2026, 8, 1, 12, tzinfo=PARIS)

async def main():
    async with AsyncSessionLocal() as db:
        sq = {s.designation: s.id for s in (await db.execute(select(Squadron))).scalars()}
        n_role = 1
        for esc in AJOUTS:
            if esc not in sq:
                ROLE[esc] = f"7000000000000010{n_role:02d}"; n_role += 1
                s = Squadron(designation=esc, status="actif", discord_role_id=ROLE[esc], wing_id=1)
                db.add(s); await db.flush(); sq[esc] = s.id
        pid = 400000000000000001
        for esc, (chef, adj, membres) in AJOUTS.items():
            for nom, role in [(chef, "leader"), (adj, "deputy")] + [(m, "member") for m in membres]:
                if not nom:
                    continue
                db.add(Profile(id=pid, username=nom.lower(), global_name=nom, roles_snapshot=[ROLE[esc], PILOTE],
                               squadron=esc, locale="fr", tz="Europe/Paris"))
                await db.flush()
                db.add(SquadronMembership(profile_id=pid, squadron_id=sq[esc], role=role, started_at=DEPUIS))
                pid += 1
        await db.flush()
        for esc, (chef, adj) in TETES_BASE.items():
            for p, role in ((chef, "leader"), (adj, "deputy")):
                if p:
                    await db.execute(update(SquadronMembership)
                                     .where(SquadronMembership.profile_id == p, SquadronMembership.ended_at.is_(None))
                                     .values(role=role))
        await db.commit()
        print("semis des organigrammes :", pid - 400000000000000001, "profils ajoutés ·", len(AJOUTS), "escadrilles complétées")

asyncio.run(main())
