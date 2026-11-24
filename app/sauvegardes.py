"""Lot « L'écran Archives du Centre » -- les fichiers de sauvegarde.

Ce module porte la sauvegarde manuelle d'un administrateur (écran Archives du
Centre de Commandement) et la lecture du dossier des sauvegardes, où
`entrypoint.sh` écrit déjà celles qui précèdent une migration. Sept formes de
noms, et elles seules :

  - `readyroom_rev-<rév>_<AAAAMMJJ-HHMM>.dump`                 la migration
    (prise par `entrypoint.sh` avant `alembic upgrade`) ;
  - `readyroom_manuel-<rév>_<AAAAMMJJ-HHMMSS>.dump`            la base ;
  - `readyroom_manuel-<rév>_<AAAAMMJJ-HHMMSS>_ecussons.tar.gz`  les écussons ;
  - `readyroom_auto-<rév>_<AAAAMMJJ-HHMMSS>.dump`              la base ;
  - `readyroom_auto-<rév>_<AAAAMMJJ-HHMMSS>_ecussons.tar.gz`   les écussons ;
  - `readyroom_deploiement-<rév>_<AAAAMMJJ-HHMMSS>.dump`       la base ;
  - `readyroom_deploiement-<rév>_<AAAAMMJJ-HHMMSS>_ecussons.tar.gz`  les écussons.

Les deux de `auto` sont celles de la sauvegarde automatique (lot « Les
sauvegardes automatiques », `app/sauvegardes_auto.py`) ; les deux de
`deploiement` sont celles que prend le déployeur avant chaque déploiement
(lot « Le Centre côté serveur ») : LECTURE SEULE pour l'App -- elle les liste
et les fait télécharger, ne les écrit ni ne les purge jamais.

Les fonctions pures (`nom_valide`, `lister`, `purger_manuelles`,
`purger_automatiques`, `etiquette_revision`, `archiver_ecussons`,
`commande_pg_dump`) se testent hors ligne (tests/test_archives.py).
`sauvegarder` est la seule à lancer un sous-processus. Rien ici ne restaure :
la restauration reste en ligne de commande (guide, chapitre 11).
"""
from __future__ import annotations

import asyncio
import os
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.engine import make_url

# `<rév>` : une révision Alembic, ou le repli `vierge` de l'entrypoint.
_REV = r"[A-Za-z0-9]+"
NOM_FICHIER = re.compile(
    rf"^(?:"
    rf"readyroom_rev-(?P<rev_rev>{_REV})_(?P<rev_stamp>\d{{8}}-\d{{4}})\.dump"
    rf"|readyroom_manuel-(?P<man_rev>{_REV})_(?P<man_stamp>\d{{8}}-\d{{6}})(?P<man_suffixe>\.dump|_ecussons\.tar\.gz)"
    rf"|readyroom_auto-(?P<auto_rev>{_REV})_(?P<auto_stamp>\d{{8}}-\d{{6}})(?P<auto_suffixe>\.dump|_ecussons\.tar\.gz)"
    rf"|readyroom_deploiement-(?P<dep_rev>{_REV})_(?P<dep_stamp>\d{{8}}-\d{{6}})(?P<dep_suffixe>\.dump|_ecussons\.tar\.gz)"
    rf")\Z"
)

_SUFFIXE_ECUSSONS = "_ecussons.tar.gz"
_DELAI_PG_DUMP_S = 120

# Une seule sauvegarde à la fois : une seconde demande est refusée, pas mise
# en file (le bouton est désactivé pendant la première).
_verrou = asyncio.Lock()


class SauvegardeEnCours(Exception):
    """Une sauvegarde tourne déjà (verrou de module pris)."""


class SauvegardeEchec(Exception):
    """La sauvegarde a échoué ; le message est une raison courte."""


def nom_valide(fichier: str) -> bool:
    """Vrai pour l'une des sept formes, et pour elles seules : ni `/`, ni
    `..`, ni `.part`."""
    return isinstance(fichier, str) and NOM_FICHIER.match(fichier) is not None


def etiquette_revision(version_num) -> str:
    """Lot « Les sauvegardes automatiques » : la révision Alembic telle qu'elle
    entre dans un nom de fichier -- seulement des lettres et des chiffres ;
    `vierge` sans révision. Pure. Une seule règle, pour la route manuelle et
    pour la tâche automatique."""
    return re.sub(r"[^A-Za-z0-9]", "", version_num or "") or "vierge"


def _entree(dossier: Path, fichier_base: str, m: re.Match) -> dict:
    manuelle = m.group("man_rev") is not None
    automatique = m.group("auto_rev") is not None
    deploiement = m.group("dep_rev") is not None   # lot « Le Centre côté serveur »
    chemin = dossier / fichier_base
    st = chemin.stat()
    ecussons = None
    ecussons_octets = None
    if manuelle or automatique or deploiement:
        nom_ecussons = fichier_base[: -len(".dump")] + _SUFFIXE_ECUSSONS
        p = dossier / nom_ecussons
        if p.is_file():
            ecussons = nom_ecussons
            ecussons_octets = p.stat().st_size
    return {
        "fichier_base": fichier_base,
        "fichier_ecussons": ecussons,
        # `rev` (entrypoint.sh, avant une migration) -> « migration » ; la famille
        # du déployeur -> « deploiement ».
        "origine": (
            "manuelle" if manuelle
            else "automatique" if automatique
            else "deploiement" if deploiement
            else "migration"
        ),
        "revision": (
            m.group("man_rev") or m.group("auto_rev")
            or m.group("dep_rev") or m.group("rev_rev")
        ),
        # L'instant de modification, jamais déduit du nom : l'heure de
        # `entrypoint.sh` est celle du conteneur.
        "date": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
        "base_octets": st.st_size,
        "ecussons_octets": ecussons_octets,
    }


def lister(dossier) -> list[dict]:
    """Une entrée par fichier `.dump` reconnu, de la date la plus récente à la
    plus ancienne. Une archive d'écussons sans son `.dump`, un `.part` et tout
    autre fichier sont ignorés ; un dossier absent rend `[]`."""
    dossier = Path(dossier)
    if not dossier.is_dir():
        return []
    entrees = []
    for p in dossier.iterdir():
        m = NOM_FICHIER.match(p.name)
        if m is None or not p.is_file():
            continue
        suffixe = (
            m.group("man_suffixe") or m.group("auto_suffixe") or m.group("dep_suffixe")
        )
        if m.group("rev_rev") is None and suffixe != ".dump":
            continue  # archive d'écussons : rattachée à son .dump, jamais seule
        try:
            entrees.append(_entree(dossier, p.name, m))
        except OSError:
            continue  # disparu entre le listage et la lecture
    entrees.sort(key=lambda e: (e["date"], e["fichier_base"]), reverse=True)
    return entrees


def _purger(dossier, garder: int, prefixe: str) -> list[str]:
    """La règle commune des deux purges : garde les `garder` sauvegardes les
    plus récentes de l'origine `prefixe` (`man` ou `auto`), par l'horodatage de
    leur nom, et retire au-delà le `.dump` et son archive d'écussons. Ne touche
    jamais à une autre origine. Rend les noms retirés."""
    dossier = Path(dossier)
    if not dossier.is_dir():
        return []
    anciennes = []
    for p in dossier.iterdir():
        m = NOM_FICHIER.match(p.name)
        if m is not None and m.group(f"{prefixe}_suffixe") == ".dump" and p.is_file():
            anciennes.append((m.group(f"{prefixe}_stamp"), p.name))
    anciennes.sort(reverse=True)
    retires: list[str] = []
    for _stamp, nom in anciennes[garder:]:
        for cible in (nom, nom[: -len(".dump")] + _SUFFIXE_ECUSSONS):
            p = dossier / cible
            if p.is_file():
                p.unlink()
                retires.append(cible)
    return retires


def purger_manuelles(dossier, garder: int = 10) -> list[str]:
    """Garde les `garder` sauvegardes manuelles les plus récentes, par
    l'horodatage de leur nom, et retire au-delà le `.dump` et son archive
    d'écussons. Ne touche jamais à un `readyroom_rev-*`, ni à une automatique.
    Rend les noms retirés."""
    return _purger(dossier, garder, "man")


def purger_automatiques(dossier, garder: int) -> list[str]:
    """Lot « Les sauvegardes automatiques » : la même règle que
    `purger_manuelles`, appliquée aux seules sauvegardes automatiques
    (`readyroom_auto-*`). Ne touche jamais à une manuelle ni à un
    `readyroom_rev-*`. Rend les noms retirés."""
    return _purger(dossier, garder, "auto")


def archiver_ecussons(source, cible) -> None:
    """Écrit un `tar.gz` du CONTENU de `source` (`CREST_STORAGE_DIR`) : chaque
    fichier à la racine de l'archive (`wing.png`, `3.png`…), la forme que
    restaure la commande du guide, §11.5 (`tar xzf … -C /data`). Les sous-dossiers
    (`_tmp`, les temporaires d'écriture) n'y entrent pas. Un dossier absent ou
    vide donne une archive vide."""
    source = Path(source)
    with tarfile.open(cible, "w:gz") as tar:
        if source.is_dir():
            for p in sorted(source.iterdir()):
                if p.is_file():
                    tar.add(p, arcname=p.name, recursive=False)


def commande_pg_dump(database_url: str, chemin) -> tuple[list[str], dict]:
    """La ligne de commande de `pg_dump`, lue sur `DATABASE_URL` (pilote
    `+asyncpg` ôté). Le mot de passe passe par `PGPASSWORD` dans `env`, jamais
    sur la ligne de commande. Rend `(argv, env)`."""
    url = make_url(database_url)
    argv = ["pg_dump", "-Fc"]
    if url.host:
        argv += ["-h", url.host]
    if url.port:
        argv += ["-p", str(url.port)]
    if url.username:
        argv += ["-U", url.username]
    argv += ["-d", url.database or "", "-f", str(chemin)]
    env = {}
    if url.password:
        env["PGPASSWORD"] = url.password
    return argv, env


def _horodatage(maintenant: datetime | None = None) -> str:
    return (maintenant or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S")


def _retirer(*chemins: Path) -> None:
    for p in chemins:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass


async def sauvegarder(
    dossier, database_url: str, ecussons, revision: str,
    *, origine: str = "manuel", garder: int = 10,
) -> dict:
    """La sauvegarde : la base (`pg_dump -Fc`) et les écussons (`tar.gz`), sous
    `readyroom_<origine>-<revision>_<AAAAMMJJ-HHMMSS UTC>`. `origine` vaut
    `"manuel"` (le bouton de l'écran Archives) ou `"auto"` (la tâche de
    `app/sauvegardes_auto.py`) ; toute autre valeur lève `ValueError`.

    Chaque fichier s'écrit sous un nom en `.part`, puis se renomme : la liste
    ne voit jamais un fichier à moitié écrit. Un échec -- code non nul, fichier
    vide, délai dépassé, erreur d'écriture -- retire tout ce qui a été écrit et
    lève `SauvegardeEchec` portant une raison courte. Une seconde sauvegarde
    pendant la première -- manuelle ou automatique : le verrou est unique --
    lève `SauvegardeEnCours`. En cas de réussite, purge : les manuelles au-delà
    de dix (`garder` est alors ignoré), ou les automatiques au-delà de
    `garder`. Rend l'entrée de `lister` de la neuve."""
    if origine not in ("manuel", "auto"):
        raise ValueError(f"origine de sauvegarde inconnue : {origine!r}")
    if _verrou.locked():
        raise SauvegardeEnCours("Une sauvegarde est déjà en cours.")
    async with _verrou:
        dossier = Path(dossier)
        base = f"readyroom_{origine}-{revision}_{_horodatage()}"
        # Deux sauvegardes dans la même seconde auraient le même nom : on attend
        # la seconde suivante plutôt que d'écraser -- ou, au nettoyage d'un
        # échec, de retirer -- celle qui existe.
        for _ in range(40):
            if not (dossier / f"{base}.dump").exists():
                break
            await asyncio.sleep(0.25)
            base = f"readyroom_{origine}-{revision}_{_horodatage()}"
        dump = dossier / f"{base}.dump"
        arch = dossier / f"{base}{_SUFFIXE_ECUSSONS}"
        dump_part = dossier / f"{base}.dump.part"
        arch_part = dossier / f"{base}{_SUFFIXE_ECUSSONS}.part"
        crees: list[Path] = []  # les fichiers définitifs écrits PAR cette sauvegarde
        try:
            try:
                dossier.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise SauvegardeEchec("le dossier des sauvegardes est inaccessible") from exc

            argv, env_pg = commande_pg_dump(database_url, dump_part)
            try:
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    env={**os.environ, **env_pg},
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.PIPE,
                )
            except OSError as exc:
                raise SauvegardeEchec("pg_dump est introuvable") from exc
            try:
                _out, err = await asyncio.wait_for(proc.communicate(), timeout=_DELAI_PG_DUMP_S)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise SauvegardeEchec("délai dépassé") from None
            if proc.returncode != 0:
                raison = (err or b"").decode("utf-8", "replace").strip().splitlines()
                court = raison[-1][:120] if raison else f"pg_dump a rendu le code {proc.returncode}"
                raise SauvegardeEchec(court)
            if not dump_part.is_file() or dump_part.stat().st_size == 0:
                raise SauvegardeEchec("le fichier de la base est vide")

            try:
                await asyncio.to_thread(archiver_ecussons, ecussons, arch_part)
            except OSError as exc:
                raise SauvegardeEchec("écriture des écussons impossible") from exc

            try:
                os.replace(dump_part, dump)
                crees.append(dump)
                os.replace(arch_part, arch)
                crees.append(arch)
            except OSError as exc:
                raise SauvegardeEchec("écriture impossible") from exc
        except BaseException:
            _retirer(dump_part, arch_part, *crees)
            raise

        if origine == "auto":
            purger_automatiques(dossier, garder)
        else:
            purger_manuelles(dossier)
        for e in lister(dossier):
            if e["fichier_base"] == dump.name:
                return e
        raise SauvegardeEchec("la sauvegarde n'est pas relue")
