"""Lot « rr-public-sans-escadre » (v1.0110) -- le code livré ne porte plus rien de l'escadre qui l'a vu naître.

Un seul test, `test_arbre_sans_escadre` : il parcourt les fichiers du dépôt et échoue, en nommant fichier et ligne,
pour chaque motif de `_MOTIFS` trouvé hors de `_HORS_LOT`. Le lot suivant
(`rr-public-guide-1`) raccourcira cette liste ; elle ne s'allonge jamais. Les noms réels sont cherchés par leur
empreinte, jamais écrits.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

_RACINE = Path(__file__).resolve().parent.parent

# Ce que ce test ne regarde pas -- chaque entrée avec le lot qui la reprendra. Un chemin de dossier finit par « / ».
_HORS_LOT = (
    "tests/test_sans_escadre.py",      # ses propres motifs
    "CHANGELOG.md",                    # l'historique des versions : jamais réécrit
    "app/static/dcs_types_livrees.json",  # des livrées du jeu, non de l'escadre
)

# Dossiers jamais parcourus : ceux-ci à toute profondeur (environnements et caches) ; `data` et `backups`
# (les dossiers de l'hôte, hors de git) sous la racine seulement -- `app/data/` est du code livré.
_DOSSIERS_SAUTES = {
    ".git", "__pycache__", ".pytest_cache", ".venv", "venv", ".mypy_cache", ".ruff_cache", "node_modules",
}
_DOSSIERS_SAUTES_RACINE = {"data", "backups"}
# Le `.env` de la racine (jamais suivi par git) n'est pas du code livré.
_FICHIERS_SAUTES_RACINE = {".env"}

_MOTIFS = (
    r"(?i:veaw)", r"Expeditionary", r"logo-veaw", r"/srv/dcs", r"tailnet", r"(?i:KHR-?26)", r"(?i:541-TFS)",
    r"(?i:160-SQN)", r"329 ?Mira",
    r"DCS-ReadyRoom-(App|Agent|Lots|Deploy)", r"\.ts\.net",
)
_RE = re.compile("|".join(f"(?:{m})" for m in _MOTIFS))

# Lot « rr-public-guide-1 » : l'option B du guide décrit Tailscale (`tailnet`, `*.ts.net`) ; ces deux motifs sont permis
# sous `docs/guide/` seulement, et nulle part ailleurs. Tous les autres motifs restent actifs partout, `docs/` compris.
_DOSSIER_GUIDE = "docs/guide/"
_MOTIFS_PERMIS_AU_GUIDE = (r"tailnet", r"\.ts\.net")
_RE_GUIDE = re.compile("|".join(f"(?:{m})" for m in _MOTIFS if m not in _MOTIFS_PERMIS_AU_GUIDE))

# Les noms réels (personnes, indicatifs, escadrilles) ne s'écrivent jamais ici : on en garde l'empreinte seule.
# Un jeton de ligne (en minuscules) ou une paire de jetons consécutifs, préfixé « rr-public: », se hache en SHA-256 ;
# les seize premiers caractères sont comparés à cette liste.
_EMPREINTES = frozenset({
    "043bb07dfab65093", "07efc440a4315f54", "0c67c7580a46cb3b", "0d37049b6152b1b6",
    "0db53ed3260de974", "0dc7b5f484c395a1", "14bfa2ecd7f7017c", "1da8bead434979d2",
    "22e70edfcf5938ee", "235f6cbd97389424", "24666ae555055f12", "28fd6c492831d8d5",
    "2b2bd37f5934d92d", "32c9e2b39f8b711f", "32ebbb59cc6f7309", "33a8d9789b30d27a",
    "35bc7a59eb3ac242", "38e2b152a7a1f553", "3a09e24cdba9fed5", "4094752f6ae2b693",
    "41851f16b8c3e910", "4777d38174095bc3", "4ce4805800a76546", "4ffa619f8e70def4",
    "53fd422e79ec498e", "54b89a5852c2ee8d", "6b9ebda05015f0fd", "6e4953f190d0a291",
    "6fbd59da6abdcceb", "6febe79eb8582701", "7392933f52591ca3", "774297cc190b0185",
    "7756591eb09e22b5", "7a491ce631a77e9b", "7d18225d342c98be", "7e4e0127876142c7",
    "8cfe8ef1fe4ce793", "8d480141e3602cdc", "9160977f339bda3f", "96aac0f24ceded88",
    "9961d8b1085b402c", "99658ed0c2510240", "99a79a8cf52f617e", "9ca3dbbd2c8a0695",
    "9ef1edef5dd3020f", "a0014b55130d60f3", "a243c9a0e9a0d278", "a6f5e2375c449b94",
    "a8bf3471d7ad886f", "a9d6786e70676129", "af2a284a4bc465d5", "afd4fdbd5e53e896",
    "b444d486f1df65c3", "b47a06103cda3c58", "b5cf2396a3aed8c3", "b658d0010cba2359",
    "b6e3ae0ac08b0659", "b78c7ad912f9801b", "ba54d7100044aaab", "bfa719a6043c411b",
    "c3863590a922bd73", "ca2b1ff5206f091d", "cb7c9cbe484a19cd", "d200f4b97f691375",
    "d22054e14497ba1a", "d3ec9db0d9e96bb6", "da1768e24d293169", "dbd92fcce958a8a6",
    "dd0d446e2e152483", "dd690414a9cbae09", "e1a231f2efecb62e", "e58032512c6a320e",
    "e7b222dad490b872", "e965db14fc71cc34", "ea374669e7330495", "ed3e65e26d9af50f",
    "f03683cc9567cf1a", "f1f4e1e52addfb01", "f31ef92e54588d77", "f34d93eac73f9014",
    "f512d9e45566e7d0", "f82a9c47307959ef", "fa33c3ef7827c3fc",
})
# Lot « rr-public-licence » : le terme additionnel de l'article 7(b) de la licence (R806, D2) impose cette ligne de
# crédit, qui nomme l'escadre ; c'est la seule exception permise, et elle ne vaut que pour cette phrase exacte.
_ATTRIBUTION = "MirabelleBenou and the 4th VEAW virtual wing"
_JETON = re.compile(r"[\w][\w.\-]*[\w]|\w")


def _empreinte(jeton: str) -> str:
    return hashlib.sha256(("rr-public:" + jeton).encode("utf-8")).hexdigest()[:16]


def _noms_reels(ligne: str) -> list[str]:
    """Les empreintes des noms réels présents dans la ligne (jamais le nom lui-même)."""
    # Une barre oblique inverse suivie de t, n ou r (séquence d'échappement écrite) vaut une espace.
    jetons = _JETON.findall(re.sub(r"\\[tnr]", " ", ligne).lower())
    candidats = jetons + [f"{a} {b}" for a, b in zip(jetons, jetons[1:])]
    # Chaque jeton se découpe aussi (points, soulignés, tirets, chiffres) : les morceaux de trois caractères ou plus.
    for jeton in jetons:
        candidats += [m for m in re.split(r"[._\-\d]+", jeton) if len(m) >= 3]
    return [e for e in (_empreinte(c) for c in candidats) if e in _EMPREINTES]


def _hors_lot(relatif: str) -> bool:
    return any(relatif == h or (h.endswith("/") and relatif.startswith(h)) for h in _HORS_LOT)


def test_arbre_sans_escadre():
    trouves: list[str] = []
    for chemin in sorted(_RACINE.rglob("*")):
        if not chemin.is_file():
            continue
        relatif = chemin.relative_to(_RACINE).as_posix()
        dossiers = relatif.split("/")[:-1]
        if _DOSSIERS_SAUTES & set(dossiers) or _DOSSIERS_SAUTES_RACINE & set(dossiers[:1]) or relatif in _FICHIERS_SAUTES_RACINE or _hors_lot(relatif):
            continue
        try:
            texte = chemin.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        motifs = _RE_GUIDE if relatif.startswith(_DOSSIER_GUIDE) else _RE
        for numero, ligne in enumerate(texte.splitlines(), 1):
            for trouve in motifs.finditer(ligne.replace(_ATTRIBUTION, "")):
                trouves.append(f"{relatif}:{numero} : {trouve.group(0)}")
            for empreinte in _noms_reels(ligne):
                trouves.append(f"{relatif}:{numero} : nom réel (empreinte {empreinte})")
    assert not trouves, "l'escadre dans le code livré :\n" + "\n".join(trouves)
