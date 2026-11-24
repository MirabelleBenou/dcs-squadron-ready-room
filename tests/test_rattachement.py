"""Lot « Le rattachement des dépôts » (v1.0052, R326) : dix invariants
déterministes, hors ligne -- ni base, ni réseau, aucun fichier lu.

1. `entete_exemple` : les cinq cas du cadrage (§3.2).
2. `faits_du_journal` : sur des évènements construits ici, ne garde que les
   faits datés, d'un type de `FAITS`, à l'initiateur ni vide ni `"0"`.
3. `taux_communs` d'un journal contre lui-même : `n = d`, taux 1.
4. Le même, décalé de +10 s : taux 0.
5. `choisir` : les deux seuils, le meilleur taux, puis le plus grand `n`.
6. La provenance au dépôt (`contenu` / `titre`) selon les deux clés de titre.
7. L'ACMI qui fait foi : le premier déposé, par `uploaded_at` puis `id`.
8. `overrides_a_recopier` : la cible l'emporte, par `object_id` comme par
   `acmi_track_id`.
9. Les deux corps de requête.
10. Les lignes de journal des deux gestes, passées à `journal.ecarts`.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.command import journal
from app.debrief import engine, rattachement
from app.debrief.debriefer import DebriefEvent
from app.debrief.schemas import DeplacerPayload, FusionnerPayload


def _ev(index: int, type_: str | None, oid: str | None, t: float | None) -> DebriefEvent:
    return DebriefEvent(
        index=index, t=t, type=type_, initiator_object_id=oid, initiator_pilot_name=None,
        initiator_unit_type=None, initiator_mission_id=None, initiator_coalition=None,
        target_object_id=None, target_pilot_name=None, target_unit_type=None, weapon=None,
        event_id=str(index), linked_event_id=None, target_slot=None, target_mission_id=None,
    )


def _journal(n: int = 30) -> list[DebriefEvent]:
    """Un journal synthétique : `n` faits, quatre objets, un fait toutes les
    7 s, les types de `FAITS` en rotation -- deux faits d'un même objet sont
    toujours à 28 s l'un de l'autre."""
    types = sorted(rattachement.FAITS)
    return [_ev(i, types[i % len(types)], str(100 + i % 4), 10.0 + 7.0 * i) for i in range(n)]


def test_entete_exemple_cinq_cas() -> None:
    assert rattachement.entete_exemple(
        ".\\\\Mods\\\\aircraft\\\\Mi-24P\\\\Missions\\\\quickStart/Mi-24P_Caucasus_cold.miz") is True
    assert rattachement.entete_exemple(
        "C:\\\\Program Files\\\\Eagle Dynamics\\\\DCS World OpenBeta\\\\Mods\\\\aircraft\\\\Mirage-F1"
        "\\\\Missions\\\\Instant_Action_Mirage_F1EE_ramp_start.miz") is True
    assert rattachement.entete_exemple(
        "C:\\\\Users\\\\pilot\\\\Saved Games\\\\DCS.openbeta\\\\Tracks\\\\Multiplayer\\\\"
        "Foothold_GCW_V5.2.5_Coldwar-Modern_radios_20260730-2219-20260817-213957.trk") is False
    assert rattachement.entete_exemple("C:\\\\Users\\\\x\\\\Saved Games\\\\DCS\\\\Missions\\\\Fulda_Gap.miz") is False
    assert rattachement.entete_exemple(None) is False


def test_faits_du_journal_evenements_construits() -> None:
    events = [
        _ev(0, "shot", "101", 12.0),          # retenu
        _ev(1, "under control", "101", 13.0), # type hors FAITS
        _ev(2, "kill", "102", None),          # t absent
        _ev(3, "hit", "0", 14.0),             # initiateur "0"
        _ev(4, "crash", "", 15.0),            # initiateur vide
        _ev(5, "takeoff", None, 16.0),        # initiateur absent
        _ev(6, "pilot dead", "103", 17.5),    # retenu
    ]
    assert rattachement.faits_du_journal(events) == [("shot", "101", 12.0), ("pilot dead", "103", 17.5)]


def test_taux_communs_contre_lui_meme() -> None:
    faits = rattachement.faits_du_journal(_journal())
    n, d = rattachement.taux_communs(faits, faits)
    assert n == d == 30
    assert rattachement.taux(n, d) == 1.0


def test_taux_communs_decale_de_dix_secondes() -> None:
    faits = rattachement.faits_du_journal(_journal())
    decales = [(typ, oid, t + 10.0) for typ, oid, t in faits]
    n, d = rattachement.taux_communs(faits, decales)
    assert n == 0 and d > 0
    assert rattachement.taux(n, d) == 0.0


def test_choisir_seuils_et_departage() -> None:
    t0 = datetime(2026, 10, 26, 20, 0, tzinfo=timezone.utc)
    a = SimpleNamespace(nom="a", created_at=t0)
    b = SimpleNamespace(nom="b", created_at=t0 + timedelta(hours=1))
    assert rattachement.choisir([(a, 19, 19)]) is None            # sous 20 faits
    assert rattachement.choisir([(a, 40, 100)]) is None           # sous 0,5
    assert rattachement.choisir([(a, 60, 100), (b, 30, 40)]) is b  # meilleur taux (0,75 contre 0,6)
    assert rattachement.choisir([(a, 40, 50), (b, 32, 40)]) is a  # égalité à 0,8 : le plus grand n


def test_provenance_selon_les_deux_cles() -> None:
    cle = engine._normalize_mission_key
    foothold = cle("C:\\Tracks\\Foothold_GCW_V5.2.5_Coldwar-Modern_radios_20260730-2219.trk")
    quickstart = cle(".\\Mods\\aircraft\\Mi-24P\\Missions\\quickStart/Mi-24P_Caucasus_cold.miz")
    assert rattachement.rattachement_du_depot(True, foothold, quickstart) == "contenu"
    assert rattachement.rattachement_du_depot(True, foothold, foothold) == "titre"
    assert rattachement.rattachement_du_depot(False, foothold, quickstart) == "titre"


def test_acmi_qui_fait_foi() -> None:
    t0 = datetime(2026, 10, 26, 21, 0, tzinfo=timezone.utc)
    premier = SimpleNamespace(kind="acmi", uploaded_at=t0, id=uuid.UUID(int=9))
    meme_instant = SimpleNamespace(kind="acmi", uploaded_at=t0, id=uuid.UUID(int=3))
    second = SimpleNamespace(kind="acmi", uploaded_at=t0 + timedelta(minutes=5), id=uuid.UUID(int=1))
    journal_ = SimpleNamespace(kind="debrief", uploaded_at=t0 - timedelta(hours=1), id=uuid.UUID(int=0))
    assert engine._acmi_qui_fait_foi([second, journal_, premier]) is premier
    assert engine._acmi_qui_fait_foi([second, premier, meme_instant]) is meme_instant
    assert engine._acmi_qui_fait_foi([journal_]) is None


def test_overrides_a_recopier_la_cible_l_emporte() -> None:
    def vol(oid, piste):
        return SimpleNamespace(object_id=oid, acmi_track_id=piste)
    s1, s2, s3, s4 = vol("16777300", None), vol("16777301", "a01"), vol(None, "a02"), vol("16777302", None)
    cible = [vol("16777300", None), vol(None, "a01"), vol("16777999", "a02")]
    assert rattachement.overrides_a_recopier([s1, s2, s3, s4], cible) == [s4]
    assert rattachement.overrides_a_recopier([s1, s2, s3, s4], []) == [s1, s2, s3, s4]


def test_corps_de_requete() -> None:
    sid = uuid.uuid4()
    assert DeplacerPayload(session_id=str(sid)).session_id == sid
    assert DeplacerPayload(session_id=None).session_id is None
    with pytest.raises(ValidationError):
        DeplacerPayload(session_id="pas-un-uuid")
    assert FusionnerPayload(source_id=str(sid)).source_id == sid
    with pytest.raises(ValidationError):
        FusionnerPayload()
    with pytest.raises(ValidationError):
        FusionnerPayload(source_id=None)


def test_lignes_de_journal_des_deux_gestes() -> None:
    fichier = rattachement.libelle_fichier("debrief", "Viper")
    assert fichier == "Débrief — Viper"
    assert rattachement.libelle_fichier("acmi", None) == "ACMI — —"
    lignes = journal.ecarts(*rattachement.etats_deplacer(fichier, "Mi-24P Caucasus cold", "Bataille de Francfort"))
    assert lignes == [
        {"champ": "fichier", "avant": None, "apres": "Débrief — Viper"},
        {"champ": "mission", "avant": "Mi-24P Caucasus cold", "apres": "Bataille de Francfort"},
    ]
    assert journal.ecarts(*rattachement.etats_fusionner("Fulda Gap Coldwar V1.0", 3)) == [
        {"champ": "absorbee", "avant": None, "apres": "Fulda Gap Coldwar V1.0 (3 fichiers)"},
    ]
    assert journal.ecarts(*rattachement.etats_fusionner("Mi-24P Caucasus cold", 1)) == [
        {"champ": "absorbee", "avant": None, "apres": "Mi-24P Caucasus cold (1 fichier)"},
    ]
