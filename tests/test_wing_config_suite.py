"""Lot « La config d'escadre de Mission Plan fabriquée par le Centre » (v1.0091) --
la config d'escadre de Mission Plan n'est plus un fichier déposé à la main :
`GET /outils/wing-config.json` la FABRIQUE (`app/wing_config.py`) depuis l'Escadre
et ses escadrilles ACTIVES qui ont un callsign, et la sert aux seuls membres
connectés. Le fichier `wing_config.json` du dossier des suites ne sert plus.

Neuf tests, sans base ni réseau : la route par le `TestClient` de FastAPI, la
garde remplacée par `dependency_overrides[get_current_user_optional]` (vidé après
chaque test) ; la fabrication par `fabriquer`, sur des objets minimaux
(`SimpleNamespace`) et des écussons PNG fabriqués ici.
"""
from __future__ import annotations

import base64
import io
import json
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# À son import, `starlette.testclient` émet un DeprecationWarning d'anyio : il
# fausserait la ligne de `pytest` (« 1 warning »). On n'ignore que celui-là.
with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from starlette.testclient import TestClient

from PIL import Image

import app.main as main_mod
from app import wing_config
from app.auth import get_current_user_optional
from app.main import app

_URL = "/outils/wing-config.json"
_RACINE = Path(__file__).resolve().parent.parent


def _png(cote: int, couleur=(200, 30, 30, 255)) -> bytes:
    sortie = io.BytesIO()
    Image.new("RGBA", (cote, cote), couleur).save(sortie, format="PNG")
    return sortie.getvalue()


def _decoder(data_url: str) -> bytes:
    assert data_url.startswith("data:image/png;base64,")
    return base64.b64decode(data_url.split(",", 1)[1])


def _escadre(**kw):
    base = dict(designation="1st EXAW", sigle=None, full_name="Example Air Wing", emblem_sha=None)
    return SimpleNamespace(**{**base, **kw})


def _esc(id, designation, callsign="Viper", status="actif", **kw):
    base = dict(
        id=id, designation=designation, callsign=callsign, full_name=None, nickname=None, status=status,
        crest_sha=None, aircraft=None, liveries=None, default_liveries=None,
    )
    return SimpleNamespace(**{**base, **kw})


def _sans_logo(cle):
    return None


def _config(escadre, escadrilles, lire_logo=_sans_logo) -> dict:
    return json.loads(wing_config.fabriquer(escadre, escadrilles, lire_logo))


def test_sans_session_401(monkeypatch):
    def _jamais(*a, **k):
        raise AssertionError("la base ne se lit pas sans session")

    monkeypatch.setattr(main_mod, "AsyncSessionLocal", _jamais)
    app.dependency_overrides[get_current_user_optional] = lambda: None
    try:
        client = TestClient(app, follow_redirects=False)
        r = client.get(_URL)
        # Un appel du front : 401, jamais de redirection ; rien ne part.
        assert r.status_code == 401
        assert "location" not in r.headers
        assert r.content == b""
    finally:
        app.dependency_overrides.clear()


def test_escadrilles_retenues():
    escadrilles = [
        _esc(5, "T-DEUX", "Deux"),
        _esc(2, "T-UN", "Un"),
        _esc(3, "T-SOMMEIL", "Dort", status="sommeil"),
        _esc(4, "T-VIDE", ""),
        _esc(6, "T-ESPACES", "   "),
        _esc(7, "T-NUL", None),
    ]
    config = _config(_escadre(), escadrilles)
    # Dans l'ordre des `id`, l'active à callsign seule : ni le sommeil, ni les callsigns vides.
    assert [s["id"] for s in config["squadrons"]] == ["T-UN", "T-DEUX"]


def test_nom_et_surnom():
    escadrilles = [
        _esc(1, "BRAVO-22", " Viper ", full_name=" 22nd « Iron Hammer » Squadron ", nickname="  Iron Hammer \u00a0"),
        _esc(2, "ALPHA-11", "Wren", full_name="11 Squadron"),
        _esc(3, "CHARLIE-33", "Dragoon"),
        _esc(4, "T-NICK", "Nick", nickname="Faucon"),
    ]
    sq = {s["id"]: s for s in _config(_escadre(), escadrilles)["squadrons"]}
    # Le surnom vient de la colonne, bords retirés ; le nom est le nom complet tel quel, « » compris.
    assert sq["BRAVO-22"]["nickname"] == "Iron Hammer"
    assert sq["BRAVO-22"]["name"] == "22nd « Iron Hammer » Squadron"
    assert sq["BRAVO-22"]["callsign"] == "Viper"
    # Sans colonne, un surnom vide.
    assert sq["ALPHA-11"]["name"] == "11 Squadron" and sq["ALPHA-11"]["nickname"] == ""
    # Sans nom complet, la désignation.
    assert sq["CHARLIE-33"]["name"] == "CHARLIE-33" and sq["CHARLIE-33"]["nickname"] == ""
    assert sq["T-NICK"]["name"] == "T-NICK" and sq["T-NICK"]["nickname"] == "Faucon"
    # Le callsign garde la casse saisie.
    assert _config(_escadre(), [_esc(1, "X", "DrAgOoN")])["squadrons"][0]["callsign"] == "DrAgOoN"


def test_types_dcs():
    escadrilles = [
        _esc(1, "A", aircraft=["F-14A"]),
        _esc(2, "B", aircraft=["Combined Arms (JTAC)", "LotATC"]),
        _esc(3, "C", aircraft=["A-4E-C"]),
        _esc(4, "D", aircraft=["F-14A", "F-14B", "F-14A"]),
    ]
    sq = {s["id"]: s for s in _config(_escadre(), escadrilles)["squadrons"]}
    assert sq["A"]["aircraft"] == ["F-14A-135-GR", "F-14A-135-GR-Early", "F-14A-95-GR"]
    assert sq["B"]["aircraft"] == []
    assert sq["C"]["aircraft"] == ["A-4E-C"]            # hors de la table : tel quel
    # Types communs, sans doublon ; l'ordre de l'escadrille est gardé.
    assert sq["D"]["aircraft"] == ["F-14A-135-GR", "F-14A-135-GR-Early", "F-14A-95-GR", "F-14B", "F-14BU"]
    assert _config(_escadre(), [_esc(1, "E", aircraft=["Mi-24P", "mi-24p"])])["squadrons"][0]["aircraft"] == ["Mi-24P"]


def test_livrees_et_defauts():
    escadrilles = [
        _esc(
            1, "CHARLIE-33", aircraft=["Mi-24P", "Mi-8"],
            liveries=[
                {"name": "Grau", "aircraft": ["Mi-24P"], "jeu": False},
                {"name": "Germany", "aircraft": ["Mi-8"], "jeu": True},
            ],
            default_liveries={"Mi-24P": "Grau", "Mi-8": "Germany"},
        ),
        _esc(
            2, "BRAVO-22", aircraft=["Mi-24P", "F-4E"],
            liveries=[
                {"name": "GRAU", "aircraft": ["Mi-24P", "F-4E"], "jeu": False},
                {"name": "Jetons", "aircraft": ["LotATC"], "jeu": False},
            ],
            default_liveries={"Mi-24P": "Autre", "F-4E": "Euro"},
        ),
        # Une escadrille non retenue (sommeil) : ni ses livrées ni son défaut n'entrent.
        _esc(3, "DORT", status="sommeil", aircraft=["Mi-8"],
             liveries=[{"name": "Fantome", "aircraft": ["Mi-8"]}], default_liveries={"Mi-8": "Fantome"}),
        _esc(4, "SANS", callsign="", aircraft=["F-4E"],
             liveries=[{"name": "Fantome2", "aircraft": ["F-4E"]}], default_liveries={"F-4E": "Fantome2"}),
    ]
    config = _config(_escadre(), escadrilles)
    # Un même nom (casse différente) : une entrée, la première écriture, les types réunis.
    assert config["liveries"] == [
        {"name": "Grau", "aircraft": ["Mi-24P", "F-4E-45MC"]},
        {"name": "Germany", "aircraft": ["Mi-8MT"]},
    ]
    # Deux défauts pour un même type : la première escadrille l'emporte.
    assert config["defaultLiveries"] == {"Mi-24P": "Grau", "Mi-8MT": "Germany", "F-4E-45MC": "Euro"}
    # Une livrée du jeu ne part que vers les types dont la liste du jeu la contient (Germany : Mi-8MT seul) ;
    # une custom de même nom garde tous ses types ; sans type restant, la livrée du jeu n'entre pas.
    jeu = _config(_escadre(), [_esc(
        1, "CHARLIE-33", aircraft=["Mi-24P", "Mi-8"],
        liveries=[
            {"name": "Germany", "aircraft": ["Mi-24P", "Mi-8"], "jeu": True},
            {"name": "Egyptian Air Force", "aircraft": ["Mi-24P", "Mi-8"], "jeu": True},
            {"name": "Inconnue du jeu", "aircraft": ["Mi-24P"], "jeu": True},
            {"name": "Maison", "aircraft": ["Mi-24P", "Mi-8"], "jeu": False},
        ],
    )])
    assert jeu["liveries"] == [
        {"name": "Germany", "aircraft": ["Mi-8MT"]},
        {"name": "Egyptian Air Force", "aircraft": ["Mi-24P", "Mi-8MT"]},
        {"name": "Maison", "aircraft": ["Mi-24P", "Mi-8MT"]},
    ]
    assert wing_config.fabriquer(_escadre(), [], _sans_logo)
    vide = _config(_escadre(), [])
    assert vide["liveries"] == [] and vide["defaultLiveries"] == {}


def test_logos():
    def lire(cle):
        return {1: _png(512), 2: _png(180), "wing": _png(300)}.get(cle)

    escadrilles = [
        _esc(1, "GRAND", crest_sha="a"),
        _esc(2, "PETIT", crest_sha="b"),
        _esc(3, "SANS", crest_sha=None),
        _esc(4, "ABSENT", crest_sha="d"),          # écusson posé, fichier disparu
    ]
    config = _config(_escadre(emblem_sha="e"), escadrilles, lire)
    sq = {s["id"]: s for s in config["squadrons"]}
    grand = Image.open(io.BytesIO(_decoder(sq["GRAND"]["logo"])))
    assert grand.size == (256, 256) and grand.format == "PNG"
    # Un écusson de 180 px est gardé à l'octet.
    assert _decoder(sq["PETIT"]["logo"]) == _png(180)
    # Sans écusson, ou sans fichier : la clé est absente.
    assert "logo" not in sq["SANS"] and "logo" not in sq["ABSENT"]
    # L'emblème de l'escadre (300 px) est réduit aussi.
    assert Image.open(io.BytesIO(_decoder(config["wing"]["logo"]))).size == (256, 256)
    # Sans emblème : le logo de l'App (180 px), tel quel.
    sans = _config(_escadre(), escadrilles, lire)
    assert _decoder(sans["wing"]["logo"]) == (_RACINE / "app" / "static" / "assets" / "img" / "emblem-default.png").read_bytes()
    assert Image.open(io.BytesIO(_decoder(sans["wing"]["logo"]))).size == (180, 180)
    # Un fichier illisible vaut « pas de logo », jamais une erreur : l'emblème retombe sur le logo de l'App.
    illisible = _config(_escadre(emblem_sha="e"), [_esc(1, "X", crest_sha="a")], lambda cle: b"pas un png")
    assert "logo" not in illisible["squadrons"][0]
    assert illisible["wing"]["logo"] == sans["wing"]["logo"]


def test_valide_pour_hq():
    """Les contrôles de `validateWingConfig` (`dcs-mission-plan` 8efccee,
    `build_hq.py`), rejoués en Python."""
    escadrilles = [
        _esc(1, "CHARLIE-33", "Dragoon", aircraft=["Mi-24P", "Mi-8", "Combined Arms (JTAC)"], crest_sha="a",
             liveries=[{"name": "Grau", "aircraft": ["Mi-24P"], "jeu": False}], default_liveries={"Mi-24P": "Grau"}),
        _esc(2, "BRAVO-22", "Viper", aircraft=["F-4E"]),
        _esc(3, "ALPHA-11", "Wren", full_name="11 Squadron", nickname="Wren"),
    ]
    config = _config(_escadre(), escadrilles, lambda cle: _png(64) if cle == 1 else None)
    assert config["configSchemaVersion"] == 1
    assert config["wing"]["shortName"]
    assert config["wing"]["logo"].startswith("data:image/")
    assert isinstance(config["squadrons"], list) and len(config["squadrons"]) == 3
    for sq in config["squadrons"]:
        assert sq["id"] and sq["callsign"] and isinstance(sq["aircraft"], list)
    assert isinstance(config["liveries"], list)
    for livree in config["liveries"]:
        assert isinstance(livree["name"], str)
        assert isinstance(livree["aircraft"], list) and all(isinstance(a, str) for a in livree["aircraft"])
    defauts = config["defaultLiveries"]
    assert isinstance(defauts, dict) and all(isinstance(v, str) for v in defauts.values())
    # Ce que la Ready Room ajoute : sa marque, et la clé que les membres ont déjà.
    assert config["managedBy"] == "Ready Room"
    assert config["wing"]["id"] == "1st-EXAW"
    # Sans sigle ni désignation, jamais un nom vide.
    assert _config(_escadre(designation="", sigle=None), [])["wing"]["shortName"] == "Wing"
    assert _config(None, [])["wing"]["hqStamp"] == "HQ ░ Wing"
    assert _config(_escadre(sigle="EXAW"), [])["wing"]["hqStamp"] == "HQ ░ EXAW"


def test_memoire():
    escadrilles = [_esc(1, "CHARLIE-33", aircraft=["Mi-24P"], liveries=[{"name": "Grau", "aircraft": ["Mi-24P"]}])]
    # La fabrication est déterministe : mêmes données, mêmes octets.
    assert wing_config.fabriquer(_escadre(), escadrilles, _sans_logo) == wing_config.fabriquer(_escadre(), escadrilles, _sans_logo)
    # Une livrée changée : d'autres octets.
    autres = [_esc(1, "CHARLIE-33", aircraft=["Mi-24P"], liveries=[{"name": "Gris", "aircraft": ["Mi-24P"]}])]
    assert wing_config.fabriquer(_escadre(), autres, _sans_logo) != wing_config.fabriquer(_escadre(), escadrilles, _sans_logo)
    # La mémoire garde les octets tant que l'empreinte tient, et refabrique sinon.
    appels = []

    def lire(cle):
        appels.append(cle)
        return None

    presente = lambda cle: False  # noqa: E731
    wing_config._memoire.update(empreinte=None, octets=None)
    premiers = wing_config.en_memoire(_escadre(emblem_sha="e"), escadrilles, lire, presente)
    assert wing_config.en_memoire(_escadre(emblem_sha="e"), escadrilles, lire, presente) is premiers
    assert appels == ["wing"]                      # une seule fabrication
    refaits = wing_config.en_memoire(_escadre(emblem_sha="e"), autres, lire, presente)
    assert refaits != premiers and refaits == wing_config.fabriquer(_escadre(emblem_sha="e"), autres, _sans_logo)
    # La présence d'un fichier d'écusson fait partie de l'empreinte.
    wing_config.en_memoire(_escadre(emblem_sha="e"), autres, lire, lambda cle: True)
    assert appels.count("wing") == 3
    wing_config._memoire.update(empreinte=None, octets=None)


def test_cle_escadre():
    """Lot « rr-public-sans-escadre » : la clé de l'escadre des suites (`wing.id`) est le réglage `WING_ID`,
    et à défaut la désignation, chaque suite de blancs devenue un seul `-`."""
    cas = [
        ("", "1st EXAW", "1st-EXAW"),
        ("", "  Example   Air Wing ", "Example-Air-Wing"),
        ("", "", "Wing"),
        ("", None, "Wing"),
        (" X-1 ", "1st EXAW", "X-1"),
    ]
    for cle, designation, attendu in cas:
        assert wing_config.cle_escadre(cle, designation) == attendu, (cle, designation)
    # `fabriquer` : la clé posée l'emporte sur la désignation ; sans clé, la désignation.
    posee = json.loads(wing_config.fabriquer(_escadre(), [], _sans_logo, cle="X-1"))
    assert posee["wing"]["id"] == "X-1"
    assert _config(_escadre(), [])["wing"]["id"] == "1st-EXAW"
    # `en_memoire` refabrique quand seule la clé change.
    presente = lambda cle: False  # noqa: E731
    wing_config._memoire.update(empreinte=None, octets=None)
    premiers = wing_config.en_memoire(_escadre(), [], _sans_logo, presente, "A-1")
    assert wing_config.en_memoire(_escadre(), [], _sans_logo, presente, "A-1") is premiers
    refaits = wing_config.en_memoire(_escadre(), [], _sans_logo, presente, "B-2")
    assert refaits != premiers and json.loads(refaits)["wing"]["id"] == "B-2"
    wing_config._memoire.update(empreinte=None, octets=None)
