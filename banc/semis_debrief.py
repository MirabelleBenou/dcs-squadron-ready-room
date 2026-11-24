"""Semis du Débrief -- banc v5, jamais dans une archive de l'application.
À lancer APRÈS prepare_base.sh (semis.py et semis_e.py), depuis la copie d'essai (cwd), environnement de test
chargé : prepare_debrief.sh le fait. Rejouable (il remet d'abord à zéro ses propres lignes) et déterministe.

Pose DEUX sessions de débrief tirées de la fixture « Bataille de Francfort » (celle du banc, identique à l'octet à
celle de l'archive) : deux campagnes, 20 vols par session, des évènements tirés des `stats` de chaque vol, une durée de
5298 s (v6), l'empreinte du moteur de l'appli servie, et le droit `debrief.access` du rôle Pilote.
  copie 1 : la fixture telle quelle, campagne « Foothold Germany » (identifiant de la fixture), 17/08/2026 ;
  copie 2 : identifiants dérivés par uuid5, « Fulda Gap », 20/09/2026 (+34 jours), titre technique sans nom saisi.
Hunter (200000000000000005) n'a aucun vol : c'est le dossier vide.
Sortie : UNE ligne de synthèse."""
import asyncio, json, os, sys, uuid
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, ".")
from sqlalchemy import delete, func, select
from app.db import AsyncSessionLocal
from app.debrief.revision import ENGINE_REVISION
from app.debrief_models import Campaign, DebriefEvent, DebriefFlight, DebriefSession
from app.models import RoleCapability

FIXTURE = "89f20c83-54ec-4fd4-bf0c-1700463ff155.json"
HERE = os.path.dirname(os.path.abspath(__file__))
# Espace de noms des identifiants dérivés : fixe, jamais changé (le semis reste déterministe).
NS = uuid.UUID("5b1f2c7e-0a43-5d6e-9c11-7e0b4a2f8d35")
PILOTE = "111111111111111111"
# Banc v6 : la durée des deux sessions, en secondes -- celle de la Bataille de Francfort en production depuis le v1.0041
# (de la première arrivée à la dernière sortie, en temps de mission). La fixture, elle, n'en porte pas.
DUREE_S = 5298
# pilote de la fixture -> profil du banc (id, nom du profil : il devient le `pilot_callsign` du vol)
PROFILS = {
    "800000000000000002": (100000000000000001, "MistyKestrel42"),
    "8000000000000000001": (200000000000000003, "Viper"),
    "800000000000000006": (200000000000000004, "Ghost"),
    "800000000000000003": (200000000000000010, "Rover"),
    "800000000000000004": (200000000000000001, "Dragoon-1"),
    "800000000000000005": (200000000000000006, "Fog"),
}
# Les évènements d'un vol, tirés de ses `stats` : gravité de menace -> type du moteur. Jamais un des six types
# mécaniques (`_MECHANICAL_EVENT_TYPES`, app/debrief/api.py) : sans cela le vol ne serait pas « réel ».
TYPE_MENACE = {"visé": "shot", "touché": "hit", "abattu": "hit"}
UTC = timezone.utc


def derive(base: uuid.UUID) -> uuid.UUID:
    return uuid.uuid5(NS, str(base))


def evenements(session_id, vol_id, vol: dict) -> list:
    """Les évènements d'UN vol : destructions (initiateur), menaces (cible), fin de vol (initiateur)."""
    st, obj, appareil = vol["stats"], vol["object_id"], vol["aircraft_type"]
    fin = float(vol.get("t_end") or 0)
    lignes = []

    def ajoute(type_, t, **champs):
        lignes.append(DebriefEvent(
            id=uuid.uuid5(NS, f"{session_id}:{vol_id}:{len(lignes)}:{type_}"),
            session_id=session_id, type=type_, t=float(t), **champs))

    for k in st.get("kills") or []:
        ajoute("kill", k["t"], initiator_object_id=obj, initiator_unit_type=appareil,
               target_object_id=k.get("target_object_id"), target_unit_type=k.get("target_unit_type"),
               weapon=k.get("weapon"))
    for m in st.get("threat_log") or []:
        type_ = TYPE_MENACE.get(m.get("gravite"))
        if type_:
            ajoute(type_, m["t"], initiator_object_id=m.get("initiator_object_id"),
                   initiator_unit_type=m.get("initiator_unit_type"), target_object_id=obj,
                   target_unit_type=appareil, weapon=m.get("weapon"))
    for drapeau, type_ in ((st.get("crashed"), "crash"), (st.get("ejected"), "eject"),
                           (st.get("pilot_dead"), "pilot dead"), (int(st.get("landings") or 0) > 0, "land")):
        if drapeau:
            ajoute(type_, fin, initiator_object_id=obj, initiator_unit_type=appareil)
    return lignes


async def main():
    chemin = os.path.join(HERE, FIXTURE)
    brut = open(chemin, "rb").read()
    archive = os.path.join("tests", "fixtures", FIXTURE)   # la copie d'essai porte la sienne : elle doit être la même
    if os.path.exists(archive) and open(archive, "rb").read() != brut:
        sys.exit("semis_debrief : la fixture du banc diffère de celle de l'archive (tests/fixtures/)")
    fx = json.loads(brut.decode("utf-8"))
    assert len(fx["flights"]) == 20, "la fixture doit porter 20 vols"

    sid1 = uuid.UUID(fx["id"])
    ref1 = datetime.fromisoformat(fx["reference_time"])
    camp1_id = uuid.UUID(fx["campaign"]["id"])
    ecart = timedelta(days=34)
    copies = [
        dict(sid=sid1, vol=lambda f: uuid.UUID(f["id"]), title=fx["title"], display_name=fx["display_name"],
             date=date(2026, 8, 17), ref=ref1, camp=camp1_id),
        dict(sid=derive(sid1), vol=lambda f: derive(uuid.UUID(f["id"])),
             title="Fulda_Gap_Coldwar_V1.0_20260920-2124", display_name=None,
             date=date(2026, 9, 20), ref=ref1 + ecart, camp=derive(camp1_id)),
    ]
    assert copies[1]["date"] - copies[0]["date"] == ecart

    async with AsyncSessionLocal() as db:
        # Rejouable : on retire d'abord ce que ce semis a pu poser (jamais le reste de la base).
        sids = [c["sid"] for c in copies]
        await db.execute(delete(DebriefEvent).where(DebriefEvent.session_id.in_(sids)))
        await db.execute(delete(DebriefFlight).where(DebriefFlight.session_id.in_(sids)))
        await db.execute(delete(DebriefSession).where(DebriefSession.id.in_(sids)))
        await db.execute(delete(Campaign).where(Campaign.id.in_([c["camp"] for c in copies])))
        await db.execute(delete(RoleCapability).where(
            RoleCapability.role_id == PILOTE, RoleCapability.capability == "debrief.access"))
        await db.flush()

        # Les campagnes d'abord, UNE par transaction, `created_at` explicites et distincts : le rang d'une campagne
        # (la teinte de sa barrette) suit `created_at`, et deux lignes d'une même transaction ont le même now().
        for nom, camp, cree in (("Foothold Germany", copies[0]["camp"], datetime(2026, 8, 15, 10, 0, tzinfo=UTC)),
                                ("Fulda Gap", copies[1]["camp"], datetime(2026, 9, 18, 10, 0, tzinfo=UTC))):
            db.add(Campaign(id=camp, name=nom, sim="dcs", created_at=cree, updated_at=cree))
            await db.commit()

        for c in copies:
            db.add(DebriefSession(
                id=c["sid"], title=c["title"], display_name=c["display_name"], wing_note=fx.get("wing_note"),
                mission_date=c["date"], reference_time=c["ref"], duration_s=DUREE_S,
                acmi_present=fx["acmi_present"], sim=fx["sim"], campaign_id=c["camp"],
                stats_engine_rev=ENGINE_REVISION))
        await db.flush()
        for c in copies:
            for f in fx["flights"]:
                vol_id = c["vol"](f)
                profil = PROFILS.get(f["pilote_profile_id"]) if f.get("pilote_profile_id") else None
                db.add(DebriefFlight(
                    id=vol_id, session_id=c["sid"], object_id=f["object_id"], acmi_track_id=f["acmi_track_id"],
                    aircraft_type=f["aircraft_type"], coalition=f["coalition"],
                    pilote_profile_id=profil[0] if profil else None,
                    pilot_callsign=profil[1] if profil else f["pilot_callsign"],
                    identity_state=f["identity_state"], identity_source=f["identity_source"],
                    t_start=f["t_start"], t_end=f["t_end"], slot_mission=f["slot_mission"],
                    mission_id_dcs=f["mission_id_dcs"], stats=f["stats"]))
        await db.flush()
        for c in copies:
            for f in fx["flights"]:
                db.add_all(evenements(c["sid"], c["vol"](f), f))
        db.add(RoleCapability(role_id=PILOTE, capability="debrief.access"))
        await db.commit()

        n = lambda modele, *cond: db.scalar(select(func.count()).select_from(modele).where(*cond))
        n_s = await n(DebriefSession, DebriefSession.id.in_(sids))
        n_v = await n(DebriefFlight, DebriefFlight.session_id.in_(sids))
        n_e = await n(DebriefEvent, DebriefEvent.session_id.in_(sids))
        n_c = await n(Campaign, Campaign.id.in_([c["camp"] for c in copies]))
    print(f"semis du débrief : sessions {' · '.join(str(s)[:8] for s in sids)} · {n_s} sessions · {n_v} vols · "
          f"{n_e} évènements · {n_c} campagnes · droit debrief.access posé au rôle Pilote ({PILOTE})")


asyncio.run(main())
