"""Lot « rr-public-guide-2 » (v1.0125) -- l'annexe B du guide d'installation tient les volumes, les montages et les ports.

Les trois tables de l'annexe B (`docs/guide/{en,fr}/b-files-volumes-ports.md`, repérées par leur ancre `{ #volumes }`,
`{ #mounts }`, `{ #ports }`) sont comparées à `docker-compose.yml` et `compose.caddy.yml`. Un volume nommé, un montage ou
un port ajouté sans sa ligne fait échouer la livraison ; une ligne qui nomme ce que les deux fichiers ne portent plus
aussi. Les deux fichiers se lisent par expressions régulières, comme `_variables_compose()` de l'annexe A : aucune
dépendance neuve.

Le test lit `docs/` à la racine du dépôt. L'archive de déploiement n'en a pas (`docs/` est `export-ignore`) : il se saute.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_RACINE = Path(__file__).resolve().parent.parent
_GUIDE = _RACINE / "docs" / "guide"
_LANGUES = ("en", "fr")
_FICHIERS_COMPOSE = ("docker-compose.yml", "compose.caddy.yml")
# La première cellule d'une ligne de l'annexe B : tout ce qui est entre accents graves (`readyroom_pgdata`, `/backups`,
# `127.0.0.1:8000`, `443/udp`).
_NOM = re.compile(r"^`([^`]+)`")
_SEPARATEUR = re.compile(r"^\|[\s:|-]+\|\s*$")


def _annexe(langue: str) -> str:
    # Seule l'absence de `docs/` (l'archive de déploiement) saute le test ; `docs/` présent, une annexe manquante échoue.
    if not (_RACINE / "docs").is_dir():
        pytest.skip("docs/ absent : archive de déploiement, le guide n'y est pas")
    chemin = _GUIDE / langue / "b-files-volumes-ports.md"
    assert chemin.is_file(), f"annexe B introuvable : {chemin.relative_to(_RACINE)}"
    return chemin.read_text(encoding="utf-8")


def _noms(texte: str, ancre: str, langue: str) -> list[str]:
    """Les noms de la première colonne de la table qui suit le titre portant l'ancre."""
    lignes = texte.splitlines()
    debut = next((i for i, l in enumerate(lignes) if l.startswith("#") and "{ #" + ancre + " }" in l), None)
    assert debut is not None, f"[{langue}] ancre « {ancre} » introuvable dans l'annexe B"
    table: list[str] = []
    for ligne in lignes[debut + 1:]:
        if ligne.startswith("|"):
            table.append(ligne)
        elif table:
            break
    # L'en-tête et le séparateur passés, chaque ligne porte un nom entre accents graves en première cellule.
    assert len(table) > 2 and _SEPARATEUR.match(table[1]), f"[{langue}] la table de « {ancre} » n'a pas d'en-tête et de lignes"
    noms: list[str] = []
    for ligne in table[2:]:
        premiere = ligne.strip().strip("|").split("|")[0].strip()
        trouve = _NOM.match(premiere)
        assert trouve, f"[{langue}] « {ancre} » : ligne sans nom entre accents graves en première cellule : {ligne}"
        noms.append(trouve.group(1))
    return noms


def _compose(fichier: str) -> str:
    return (_RACINE / fichier).read_text(encoding="utf-8")


def _utiles(texte: str):
    """(indentation, texte sans l'indentation) de chaque ligne qui n'est ni vide ni un commentaire."""
    for brut in texte.splitlines():
        nu = brut.strip()
        if nu and not nu.startswith("#"):
            yield len(brut) - len(brut.lstrip(" ")), nu


def _decoupe(valeur: str) -> list[str]:
    """Coupe aux deux-points, hors d'un `${…}` (`${SUITES_HOST_DIR:-./data/suites}:/data/suites:ro`)."""
    morceaux, courant, profondeur = [], "", 0
    for c in valeur:
        if c == "{":
            profondeur += 1
        elif c == "}":
            profondeur -= 1
        if c == ":" and profondeur == 0:
            morceaux.append(courant)
            courant = ""
        else:
            courant += c
    morceaux.append(courant)
    return morceaux


def _elements(texte: str, cle: str) -> list[str]:
    """Les éléments (guillemets et commentaire ôtés) de la liste `<cle>:` de chaque service, forme courte `- …`."""
    elements: list[str] = []
    dans_services = en_liste = False
    for indent, nu in _utiles(texte):
        if indent == 0:
            dans_services, en_liste = nu == "services:", False
        elif not dans_services:
            continue
        elif indent <= 4:
            en_liste = indent == 4 and nu == cle + ":"
        elif en_liste:
            assert nu.startswith("- "), f"« {cle} » : forme non lue (seule la forme courte `- …` l'est) : {nu}"
            valeur = nu[2:].strip()
            valeur = re.sub(r"\s+#.*$", "", valeur) if valeur[:1] not in "\"'" else valeur
            elements.append(valeur.strip().strip("\"'"))
    return elements


def _noms_de_volumes() -> set[str]:
    """Les volumes du bloc `volumes:` de premier niveau des deux fichiers, sous le nom qu'ils y portent."""
    volumes: set[str] = set()
    for fichier in _FICHIERS_COMPOSE:
        dans_bloc = False
        for indent, nu in _utiles(_compose(fichier)):
            if indent == 0:
                dans_bloc = nu == "volumes:"
            elif dans_bloc and indent == 2:
                nom = re.match(r"([A-Za-z0-9_.-]+):", nu)
                assert nom, f"{fichier} : ligne de `volumes:` non lue : {nu}"
                volumes.add(nom.group(1))
    return volumes


def _volumes_nommes() -> set[str]:
    """Les mêmes, sous le nom que Compose leur donne : `<nom du projet>_<nom>`."""
    nom_projet = re.search(r"^name:\s*(\S+)\s*$", _compose("docker-compose.yml"), re.MULTILINE)
    assert nom_projet, "docker-compose.yml : ligne `name:` introuvable (le nom du projet préfixe les volumes)"
    return {f"{nom_projet.group(1)}_{v}" for v in _noms_de_volumes()}


def _montages() -> set[str]:
    """Le chemin dans le conteneur de chaque montage dont la source n'est pas un volume nommé (un chemin, une `${…}`)."""
    nommes = _noms_de_volumes()
    chemins: set[str] = set()
    for fichier in _FICHIERS_COMPOSE:
        for element in _elements(_compose(fichier), "volumes"):
            morceaux = _decoupe(element)
            assert len(morceaux) >= 2, f"{fichier} : montage non lu : {element}"
            if morceaux[0] not in nommes:
                chemins.add(morceaux[1])
    return chemins


def _ports() -> set[str]:
    """Le côté hôte de chaque port publié : `127.0.0.1:8000`, `80`, `443/udp`."""
    hotes: set[str] = set()
    for fichier in _FICHIERS_COMPOSE:
        for element in _elements(_compose(fichier), "ports"):
            corps, _, protocole = element.partition("/")
            morceaux = _decoupe(corps)
            assert len(morceaux) in (2, 3), f"{fichier} : port non lu : {element}"
            hote = ":".join(morceaux[:-1])  # tout sauf le port du conteneur : `ip:hôte` ou `hôte`
            hotes.add(hote + ("/" + protocole if protocole else ""))
    return hotes


def test_annexe_b_volumes():
    attendus = _volumes_nommes()
    assert attendus, "aucun volume nommé lu dans les fichiers Compose"
    for langue in _LANGUES:
        noms = _noms(_annexe(langue), "volumes", langue)
        manquants = sorted(attendus - set(noms))
        assert not manquants, f"[{langue}] §B.2 sans ligne pour : {manquants}"


def test_annexe_b_montages():
    attendus = _montages()
    assert attendus, "aucun montage lu dans les fichiers Compose"
    for langue in _LANGUES:
        noms = _noms(_annexe(langue), "mounts", langue)
        manquants = sorted(attendus - set(noms))
        assert not manquants, f"[{langue}] §B.3 sans ligne pour : {manquants}"


def test_annexe_b_ports():
    attendus = _ports()
    assert attendus, "aucun port lu dans les fichiers Compose"
    for langue in _LANGUES:
        noms = _noms(_annexe(langue), "ports", langue)
        manquants = sorted(attendus - set(noms))
        assert not manquants, f"[{langue}] §B.4 sans ligne pour : {manquants}"


def test_annexe_b_aucune_ligne_perimee():
    sources = {
        "volumes": _volumes_nommes(),
        "mounts": _montages(),
        "ports": _ports(),
    }
    for langue in _LANGUES:
        texte = _annexe(langue)
        for ancre, connus in sources.items():
            noms = _noms(texte, ancre, langue)
            inconnus = sorted(set(noms) - connus)
            assert not inconnus, f"[{langue}] « {ancre} » nomme ce que les fichiers Compose ne portent plus : {inconnus}"
            doublons = sorted({n for n in noms if noms.count(n) > 1})
            assert not doublons, f"[{langue}] « {ancre} » nomme deux fois : {doublons}"
