"""Brief SONNET Lot Fusion §3 : trois invariants déterministes, hors ligne,
sur des entrées synthétiques -- pas de clé API, pas de base, comme le fait
déjà `test_chaine_deux_temps.py`.

1. `test_fusion_tirs_meme_arme_noms_divergents` -- geste 1 : deux uploads
   rapportant la MÊME salve de 10 roquettes, l'un nommant l'arme
   `S-13OF Blast/Fragmentation`, l'autre `S-13OF Explosion/fragmentation`,
   fusionnent en 10 événements `shot` canoniques (`S-13OF`), pas 20. Le
   contrôle inverse voisin (même tireur, même fenêtre, deux armes
   RÉELLEMENT distinctes et absentes de la table) ne fusionne pas.

2. `test_coalition_moins_un_cede_au_repli_acmi` -- geste 3 : un
   `object_id` dont le seul `initiator_coalition` observé est `"-1"` mais
   qui est apparié à une piste ACMI porte la coalition ACMI. Les
   coalitions valides (`"0"`, `"1"`, `"2"`) restent retenues normalement,
   sans repli.

3. `test_repli_sauts_annexe_a` -- geste 4 : les deux suites de phases
   réelles de l'Annexe A du brief (Wren5, DawN-FyX35) produisent, au
   caractère près, les sorties attendues -- y compris l'écart de 148,7 s
   qui reste un atterrissage/décollage francs, et la micro-sortie de
   5,1 s qui s'absorbe d'elle-même entre deux sauts.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.debrief import acmi as acmi_mod
from app.debrief import engine
from app.debrief.debriefer import DebriefEvent, DebriefHeader, DebriefLogData
from app.debrief_models import DebriefUpload


def _upload(sha: str) -> DebriefUpload:
    return DebriefUpload(id=sha, sha256=sha, kind="debrief", filename=f"{sha}.log")


def _ev(
    *,
    index: int,
    t: float,
    type: str,
    ioid: str | None = None,
    weapon: str | None = None,
    toid: str | None = None,
    initiator_coalition: str | None = None,
) -> DebriefEvent:
    return DebriefEvent(
        index=index,
        t=t,
        type=type,
        initiator_object_id=ioid,
        initiator_pilot_name=None,
        initiator_unit_type=None,
        initiator_mission_id=None,
        initiator_coalition=initiator_coalition,
        target_object_id=toid,
        target_pilot_name=None,
        target_unit_type=None,
        weapon=weapon,
        event_id=str(index),
        linked_event_id=None,
        target_slot=None,
        target_mission_id=None,
    )


# =============================================================================
# 1. Fusion des tirs (geste 1)
# =============================================================================


def test_fusion_tirs_meme_arme_noms_divergents() -> None:
    ioid = "9001"
    # Cinq rafales de 2 tirs, comme sur la session réelle (5 x 2 = 10,
    # l'emport exact d'un Mi-24P) -- chaque tir est rapporté par LES DEUX
    # uploads, aux mêmes horodatages, mais sous deux noms d'arme différents.
    ts = [100.0 + 0.1 * i for i in range(10)]

    events_a = [
        _ev(index=i, t=t, type="shot", ioid=ioid, weapon="S-13OF Blast/Fragmentation")
        for i, t in enumerate(ts)
    ]
    events_b = [
        _ev(index=i, t=t, type="shot", ioid=ioid, weapon="S-13OF Explosion/fragmentation")
        for i, t in enumerate(ts)
    ]

    # Contrôle inverse, voisin dans le temps et sur le même tireur : deux
    # armes RÉELLEMENT distinctes (absentes de `_ALIAS_ARME`) ne doivent
    # jamais fusionner, même à 0,05 s d'écart.
    events_a.append(_ev(index=100, t=200.0, type="shot", ioid=ioid, weapon="Mk-20 Rockeye"))
    events_b.append(_ev(index=100, t=200.05, type="shot", ioid=ioid, weapon="GBU-8/B"))

    log_a = DebriefLogData(header=DebriefHeader(), events=events_a, graveyard=[])
    log_b = DebriefLogData(header=DebriefHeader(), events=events_b, graveyard=[])
    debrief_pairs = [(_upload("a"), log_a), (_upload("b"), log_b)]

    merged = engine._merge_events(debrief_pairs)
    shots = [e for e in merged if e.type == "shot" and e.initiator_object_id == ioid]

    canon = [e for e in shots if e.weapon == "S-13OF"]
    assert len(canon) == 10, f"{len(canon)} événements S-13OF (attendu 10, pas 20)"
    assert all(len(e.seen_in) == 2 for e in canon), "chaque tir canonique doit être vu par les deux uploads"

    distincts = [e for e in shots if e.weapon != "S-13OF"]
    armes_distinctes = {e.weapon for e in distincts}
    assert armes_distinctes == {"Mk-20 Rockeye", "GBU-8/B"}, (
        f"armes distinctes = {armes_distinctes} (attendu Mk-20 Rockeye et GBU-8/B, non fusionnées)"
    )
    assert len(distincts) == 2, "les deux armes réellement distinctes ne doivent pas fusionner"


# =============================================================================
# 2. Coalition -- `-1` cède au repli ACMI (geste 3)
# =============================================================================


def test_coalition_moins_un_cede_au_repli_acmi() -> None:
    # Wren5 : seul `initiator_coalition` observé = "-1" (valeur DCS "je ne
    # sais pas"), mais apparié à une piste ACMI dont la coalition, dérivée
    # du Color Tacview, est fiable.
    oid_wren = "wren5-oid"
    events_wren = [
        _ev(index=0, t=1592.99, type="under control", ioid=oid_wren),
        _ev(index=1, t=2292.41, type="takeoff", ioid=oid_wren, initiator_coalition="-1"),
    ]

    # Trois autres vols, un par coalition valide -- doivent rester tels
    # quels, sans repli, sans piste ACMI disponible pour eux.
    oids_valides = {"neutre-oid": "0", "rouge-oid": "1", "bleu-oid": "2"}
    events_valides = [
        _ev(index=10 + i, t=3000.0 + i, type="under control", ioid=oid)
        for i, oid in enumerate(oids_valides)
    ] + [
        _ev(
            index=20 + i,
            t=3100.0 + i,
            type="takeoff",
            ioid=oid,
            initiator_coalition=coalition,
        )
        for i, (oid, coalition) in enumerate(oids_valides.items())
    ]

    log = DebriefLogData(
        header=DebriefHeader(), events=events_wren + events_valides, graveyard=[]
    )
    debrief_pairs = [(_upload("a"), log)]

    object_types = {oid_wren: "Mi-24P"}
    acmi_data = acmi_mod.AcmiData(
        objects={
            "707": acmi_mod.AcmiObject(
                track_id="707",
                name="Mi-24P",
                pilot="Wren5",
                coalition="2",
                is_human=True,
                t_spawn=1590.0,
                t_despawn=4800.0,
            )
        }
    )

    flights = engine._build_flights(
        acmi_data=acmi_data,
        debrief_pairs=debrief_pairs,
        object_types=object_types,
        identities={},
    )
    flights_by_oid = {fl.object_id: fl for fl in flights if fl.object_id}

    assert flights_by_oid[oid_wren].acmi_track_id == "707", "Wren5 doit être apparié à la piste ACMI 707"
    assert flights_by_oid[oid_wren].coalition == "2", (
        f"coalition Wren5 = {flights_by_oid[oid_wren].coalition!r} (attendu '2', repli ACMI)"
    )

    for oid, attendu in oids_valides.items():
        assert flights_by_oid[oid].coalition == attendu, (
            f"coalition {oid} = {flights_by_oid[oid].coalition!r} (attendu {attendu!r}, sans repli)"
        )


# =============================================================================
# 3. Repli des sauts au journal de vol (geste 4, Annexe A)
# =============================================================================


def _phases_events(ioid: str, phases: list[tuple[str, float]]) -> list[DebriefEvent]:
    return [
        _ev(index=i, t=t, type=ptype, ioid=ioid)
        for i, (ptype, t) in enumerate(phases)
    ]


def _phases_dict(fl, merged_events, debrief_pairs) -> list[dict]:
    engine._compute_flight_stats([fl], merged_events, None, debrief_pairs)
    return fl.stats["phases"]


def test_repli_sauts_annexe_a() -> None:
    # --- Wren5 (Annexe A) ---------------------------------------------------
    oid_wren = "wren5-oid"
    wren_phases_entree = [
        ("engine startup", 1592.990),
        ("takeoff", 2292.410),
        ("land", 4103.690),
        ("takeoff", 4173.430),
        ("land", 4627.001),
        ("engine shutdown", 4754.430),
    ]
    events_wren = _phases_events(oid_wren, wren_phases_entree)
    fl_wren = engine.ComputedFlight(
        object_id=oid_wren, acmi_track_id=None, aircraft_type="Mi-24P", coalition="2",
        pilote_profile_id=None, pilot_callsign="Wren5", identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    phases_wren = _phases_dict(fl_wren, events_wren, [])
    attendu_wren = [
        {"type": "engine startup", "t": 1592.990},
        {"type": "takeoff", "t": 2292.410},
        {"type": "saut", "t": 4103.690, "au_sol_s": 69.7},
        {"type": "land", "t": 4627.001},
        {"type": "engine shutdown", "t": 4754.430},
    ]
    assert phases_wren == attendu_wren, f"Wren5 : {phases_wren} (attendu {attendu_wren})"

    # --- DawN-FyX35 (Annexe A) -----------------------------------------------
    oid_dawn = "dawn-oid"
    dawn_phases_entree = [
        ("engine startup", 1385.433),
        ("takeoff", 1683.973),
        ("land", 1854.463),
        ("takeoff", 1887.793),
        ("land", 1973.773),
        ("takeoff", 2033.244),
        ("land", 2038.313),
        ("takeoff", 2114.853),
        ("land", 2145.797),
        ("takeoff", 2294.461),
        ("land", 3943.969),
        ("takeoff", 4037.593),
        ("land", 4111.074),
        ("takeoff", 4169.645),
        ("land", 4515.333),
        ("takeoff", 4576.633),
        ("land", 4615.973),
        ("engine shutdown", 4652.593),
    ]
    events_dawn = _phases_events(oid_dawn, dawn_phases_entree)
    fl_dawn = engine.ComputedFlight(
        object_id=oid_dawn, acmi_track_id=None, aircraft_type="Mi-24P", coalition="2",
        pilote_profile_id=None, pilot_callsign="DawN-FyX35", identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    phases_dawn = _phases_dict(fl_dawn, events_dawn, [])
    attendu_dawn = [
        {"type": "engine startup", "t": 1385.433},
        {"type": "takeoff", "t": 1683.973},
        {"type": "saut", "t": 1854.463, "au_sol_s": 33.3},
        {"type": "saut", "t": 1973.773, "au_sol_s": 59.5},
        {"type": "saut", "t": 2038.313, "au_sol_s": 76.5},
        {"type": "land", "t": 2145.797},
        {"type": "takeoff", "t": 2294.461},
        {"type": "saut", "t": 3943.969, "au_sol_s": 93.6},
        {"type": "saut", "t": 4111.074, "au_sol_s": 58.6},
        {"type": "saut", "t": 4515.333, "au_sol_s": 61.3},
        {"type": "land", "t": 4615.973},
        {"type": "engine shutdown", "t": 4652.593},
    ]
    assert phases_dawn == attendu_dawn, f"DawN-FyX35 : {phases_dawn} (attendu {attendu_dawn})"

    # Propriétés-clé (brief, Annexe A) : l'écart de 148,7 s (2145.797 ->
    # 2294.461) N'EST PAS replié -- il dépasse le seuil et sépare les tours
    # de piste de la vraie sortie. La micro-sortie de 5,1 s (2033.244 ->
    # 2038.313) disparaît d'elle-même, absorbée entre deux sauts. Les deux
    # propriétés sont déjà prouvées par l'égalité exacte ci-dessus ; les
    # deux assertions suivantes les rendent explicites.
    assert {"type": "land", "t": 2145.797} in phases_dawn and {"type": "takeoff", "t": 2294.461} in phases_dawn, (
        "l'écart de 148,7 s doit rester un atterrissage et un décollage francs"
    )
    assert not any(
        p["type"] == "saut" and abs(p["au_sol_s"] - 5.1) < 0.01 for p in phases_dawn
    ), "aucune micro-sortie de 5,1 s ne doit apparaître : elle doit s'absorber entre deux sauts"

    # --- Un land final sans takeoff derrière lui reste un land -------------
    oid_sans_land = "sans-land-oid"
    events_sans_land = _phases_events(
        oid_sans_land,
        [("engine startup", 100.0), ("takeoff", 200.0), ("land", 900.0)],
    )
    fl_sans_land = engine.ComputedFlight(
        object_id=oid_sans_land, acmi_track_id=None, aircraft_type="Mi-24P", coalition="2",
        pilote_profile_id=None, pilot_callsign=None, identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    phases_sans_land = _phases_dict(fl_sans_land, events_sans_land, [])
    assert phases_sans_land[-1] == {"type": "land", "t": 900.0}, (
        f"un land final sans takeoff derrière lui doit rester un land : {phases_sans_land[-1]!r}"
    )
    assert not any(p["type"] == "saut" for p in phases_sans_land), (
        "aucun saut ne doit être fabriqué : le land final n'a pas de takeoff derrière lui"
    )

    # --- Un vol encore en l'air à la fin (pas de land final) reste sans
    #     atterrissage : aucun land ne doit être fabriqué -----------------
    oid_encore_en_vol = "encore-en-vol-oid"
    events_encore_en_vol = _phases_events(
        oid_encore_en_vol, [("engine startup", 100.0), ("takeoff", 200.0)]
    )
    fl_encore_en_vol = engine.ComputedFlight(
        object_id=oid_encore_en_vol, acmi_track_id=None, aircraft_type="Mi-24P", coalition="2",
        pilote_profile_id=None, pilot_callsign=None, identity_state="anonyme",
        identity_source=None, t_start=None, t_end=None, slot_mission=None, mission_id_dcs=None,
    )
    phases_encore_en_vol = _phases_dict(fl_encore_en_vol, events_encore_en_vol, [])
    assert phases_encore_en_vol[-1] == {"type": "takeoff", "t": 200.0}, (
        f"vol sans atterrissage final : {phases_encore_en_vol!r} (aucun land ne doit être fabriqué)"
    )
    assert not any(p["type"] in ("land", "saut") for p in phases_encore_en_vol), (
        "aucun land ni saut ne doit apparaître pour un vol encore en l'air"
    )


if __name__ == "__main__":
    test_fusion_tirs_meme_arme_noms_divergents()
    print("OK -- test_fusion_tirs_meme_arme_noms_divergents")
    test_coalition_moins_un_cede_au_repli_acmi()
    print("OK -- test_coalition_moins_un_cede_au_repli_acmi")
    test_repli_sauts_annexe_a()
    print("OK -- test_repli_sauts_annexe_a")
