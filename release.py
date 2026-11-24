#!/usr/bin/env python3
"""Bump de version du package Ready Room (exclusif à cet outil).

Trois usages, selon le format de `VERSION` :
    python release.py                → `VERSION` en `1.0xxx` : new = current + STEP (Decimal("0.0001")) ;
                                       `VERSION` en `RR-V<x.y.z>` ou `RR-V<x.y.z>+<n>` : `RR-V<x.y.z>+<n+1>`
                                       (`+1` juste après une release) ; `CHANGELOG.md` n'est pas écrit
    python release.py --set X.YY     → fixe explicitement la version (format `1.0xxx` seulement)
    python release.py --set X.YY --force  → autorise un downgrade (format `1.0xxx` seulement)
    python release.py --release RR-V<x.y.z>  → la release : `VERSION` vaut `RR-V<x.y.z>`, et la ligne
                                       `## RR-V<x.y.z> — <date>` se pose sous `## Unreleased` ; le tag doit être
                                       plus haut que la dernière release lue dans `VERSION` (`x.y.z` numérique ;
                                       une `VERSION` en `1.0xxx` n'a pas de release : tout tag passe)
`--set` et `--force` refusent (code 1) sur une `VERSION` en `RR-V` ; `--release` ne se combine pas avec eux.

`VERSION` (racine du dépôt) est l'unique source de vérité. Sans argument, comme avec `--set`, ce script ne met à jour
que `VERSION` : le CHANGELOG garde sa section, que chaque lot complète à la main (plus de section par mise à jour).
Seul `--release` écrit dans `CHANGELOG.md` : la ligne de la release, sous `## Unreleased`. Sans ligne `## Unreleased`,
le script s'arrête avant d'écrire quoi que ce soit (code de sortie 1). Aucun autre fichier ne doit contenir de numéro
de version codé en dur.
"""
import argparse
import datetime
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION_FILE = ROOT / "VERSION"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"

# `VERSION` sous le régime RR-V : `RR-V<x.y.z>` (la release) ou `RR-V<x.y.z>+<n>` (un numéro de dev après elle).
RR_VERSION_RE = re.compile(r"RR-V([0-9]+)\.([0-9]+)\.([0-9]+)(?:\+([0-9]+))?")
RR_TAG_RE = re.compile(r"RR-V([0-9]+)\.([0-9]+)\.([0-9]+)")

STEP = Decimal("0.0001")
CEILING = Decimal("2.0000")


def fmt(v: Decimal) -> str:
    return f"{v:.4f}"


def read_current_version() -> Decimal:
    raw = VERSION_FILE.read_text(encoding="utf-8").strip()
    return Decimal(raw)


def read_version_raw() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def write_version(new: Decimal) -> None:
    VERSION_FILE.write_text(fmt(new), encoding="utf-8")


UNRELEASED_RE = re.compile(r"^## Unreleased[ \t]*$")


def find_unreleased_index(lines: list[str]) -> int | None:
    """Indice de la ligne `## Unreleased`, ou None si elle manque."""
    for i, line in enumerate(lines):
        if UNRELEASED_RE.match(line.rstrip("\r\n")):
            return i
    return None


def read_changelog_lines() -> list[str] | None:
    """Lignes du CHANGELOG, ou None s'il n'a pas de `## Unreleased`."""
    if not CHANGELOG_FILE.exists():
        return None
    lines = CHANGELOG_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    return lines if find_unreleased_index(lines) is not None else None


def insert_release_heading(tag: str) -> None:
    # Lot « rr-release-auto » : la ligne de la release se pose sous `## Unreleased` et sa ligne vide ; les sections `###`
    # déjà là passent ainsi sous la release, `## Unreleased` reste, vide.
    today = datetime.date.today().isoformat()
    insert_under_unreleased(f"## {tag} — {today}\n\n")


def insert_under_unreleased(stub: str) -> None:
    lines = read_changelog_lines()
    if lines is None:
        raise ValueError("CHANGELOG.md sans ligne « ## Unreleased »")
    insert_at = find_unreleased_index(lines) + 1
    if insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1  # la ligne vide qui suit « ## Unreleased » reste au-dessus du stub
    else:
        stub = "\n" + stub
    new_content = "".join(lines[:insert_at]) + stub + "".join(lines[insert_at:])
    CHANGELOG_FILE.write_text(new_content, encoding="utf-8")


def _refuse(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def _rr_tuple(m) -> tuple[int, int, int]:
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump de version Ready Room.")
    parser.add_argument("--set", dest="set_version", default=None, help="Fixe explicitement la version (ex: 1.0)")
    parser.add_argument("--force", action="store_true", help="Autorise un downgrade avec --set")
    parser.add_argument("--release", dest="release_tag", default=None,
                        help="Pose la release : un tag RR-V<x.y.z> (ex: RR-V1.0.0)")
    args = parser.parse_args()

    raw = read_version_raw()
    rr_courant = RR_VERSION_RE.fullmatch(raw)

    # Lot « rr-release-auto » : --release ne se combine pas avec --set ni --force.
    if args.release_tag is not None and (args.set_version is not None or args.force):
        return _refuse("Refus : --release ne se combine pas avec --set ni --force ; rien n'a été écrit.")

    if args.release_tag is not None:
        tag_m = RR_TAG_RE.fullmatch(args.release_tag)
        if not tag_m:
            return _refuse(
                f"Refus : --release attend un tag de la forme RR-V<x.y.z> (reçu {args.release_tag!r}) ; "
                f"rien n'a été écrit."
            )
        if rr_courant and _rr_tuple(tag_m) <= _rr_tuple(rr_courant):
            return _refuse(
                f"Refus : le tag {args.release_tag} n'est pas plus haut que la dernière release de VERSION "
                f"({raw}) ; rien n'a été écrit."
            )
        if rr_courant is None:
            try:
                Decimal(raw)
            except (InvalidOperation, ValueError):
                return _refuse(f"Refus : VERSION {raw!r} illisible ; rien n'a été écrit.")
        if read_changelog_lines() is None:
            return _refuse(
                "Refus : CHANGELOG.md n'a pas de ligne « ## Unreleased » "
                "(ou le fichier manque) ; rien n'a été écrit. "
                "Rétablir la section « ## Unreleased » avant de relancer."
            )
        VERSION_FILE.write_text(args.release_tag, encoding="utf-8")
        insert_release_heading(args.release_tag)
        print(f"Version : {raw} → {args.release_tag}")
        return 0

    if rr_courant is not None:
        # Régime RR-V : un numéro de dev `RR-V<x.y.z>+<n>` ; --set et --force n'y ont pas de sens.
        if args.set_version is not None or args.force:
            return _refuse(
                f"Refus : --set et --force ne valent que pour une VERSION en 1.0xxx (VERSION est {raw}) ; "
                f"rien n'a été écrit."
            )
        n = int(rr_courant.group(4) or 0) + 1
        label = f"RR-V{rr_courant.group(1)}.{rr_courant.group(2)}.{rr_courant.group(3)}+{n}"
        if read_changelog_lines() is None:
            return _refuse(
                "Refus : CHANGELOG.md n'a pas de ligne « ## Unreleased » "
                "(ou le fichier manque) ; rien n'a été écrit. "
                "Rétablir la section « ## Unreleased » avant de relancer."
            )
        VERSION_FILE.write_text(label, encoding="utf-8")
        print(f"Version : {raw} → {label}")
        return 0

    current = read_current_version()

    if args.set_version is not None:
        try:
            new = Decimal(args.set_version)
        except (InvalidOperation, ValueError):
            print(f"Valeur --set invalide : {args.set_version!r}", file=sys.stderr)
            return 1
        if new < current and not args.force:
            print(
                f"Refus : --set {args.set_version} ({fmt(new)}) est un downgrade "
                f"par rapport à la version courante ({fmt(current)}). "
                f"Utiliser --force pour l'autoriser explicitement.",
                file=sys.stderr,
            )
            return 1
    else:
        new = current + STEP

    if new >= CEILING and not args.force:
        print(
            f"Refus : {fmt(new)} atteint ou dépasse le plafond {fmt(CEILING)}. "
            f"Franchir ce plafond est une décision explicite : "
            f"utiliser --force pour l'autoriser.",
            file=sys.stderr,
        )
        return 1

    # Rien ne s'écrit sans la ligne « ## Unreleased » : le refus tient, même si le CHANGELOG n'est plus écrit ici.
    if read_changelog_lines() is None:
        print(
            "Refus : CHANGELOG.md n'a pas de ligne « ## Unreleased » "
            "(ou le fichier manque) ; rien n'a été écrit. "
            "Rétablir la section « ## Unreleased » avant de relancer.",
            file=sys.stderr,
        )
        return 1

    write_version(new)

    print(f"Version : {fmt(current)} → {fmt(new)}")
    print(f"Zip cible : readyroom_v{fmt(new).replace('.', '_')}.zip")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
