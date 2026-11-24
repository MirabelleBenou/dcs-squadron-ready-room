"""Parser `debrief.log` — spec §2.2 / brief §2.2.

Format Lua-like, texte. Trois blocs : en-tête (`mission_file_path`,
`callsign` -- **NON FIABLE, jamais utilisé pour identifier**), `graveyard`,
`events`. Chaque event est délimité par un commentaire `-- end of [N]` ;
on extrait tous les champs `clé = "valeur"` / `clé = nombre` (approche
prescrite par le brief -- pas de parseur Lua complet, stdlib pure `re`).

Faits liants (spec §8) rappelés ici pour mémoire de contexte :
- `object_id` stable entre debriefs ; `event_id`/`linked_event_id` locaux
  au fichier (jamais une clé inter-fichiers -- cf. app/debrief/engine.py).
- `under control` énumère TOUTES les vies du déposant (exhaustif).
- `PLAYER` dans `*PilotName` = marqueur humain natif (≠ vrai callsign).
- `score` = mécanique de campagne, jamais un indicateur de hit/kill.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Union

# Capture générique `clé = "valeur"` / `["clé"] = "valeur"` / `clé = nombre`
# / `["clé"] = nombre` -- flat scan, ne suit pas la hiérarchie des
# sous-tables (suffisant : les noms de champs utiles sont uniques dans le
# format, y compris `x`/`y`/`alt`/`heading` nichés sous `pos` du graveyard).
_FIELD_RE = re.compile(
    r'\[?"?(?P<key>[A-Za-z_][A-Za-z0-9_]*)"?\]?\s*=\s*'
    r'(?:"(?P<str>[^"]*)"|(?P<num>-?\d+(?:\.\d+)?)|(?P<bool>true|false))'
)

# Découpe des entrées numérotées de premier niveau `[N] = { ... } -- end of
# [N]` (le \1 garantit qu'on referme sur le MÊME index, donc les
# sous-tables comme `["pos"] = { ... } -- end of ["pos"]` ne perturbent pas
# la coupe : leur marqueur de fin n'est jamais `-- end of [<même N>]`).
_ENTRY_RE = re.compile(
    r"\[(?P<idx>\d+)\]\s*=\s*\{(?P<body>.*?)\}\s*,?\s*--\s*end of \[(?P=idx)\]",
    re.DOTALL,
)

# Champs racine `mission_file_mark`/`mission_time` (brief HOTFIX ancre temps
# réel §Volet 1.b) -- constatés APRÈS le bloc graveyard sur les fichiers
# réels ; `_parse_header` ne scanne que la tranche AVANT graveyard, donc ces
# 2 champs sont lus séparément sur le texte COMPLET via ces regex dédiées.
_MISSION_FILE_MARK_RE = re.compile(r"^mission_file_mark\s*=\s*(\d+)", re.MULTILINE)
_MISSION_TIME_RE = re.compile(r"^mission_time\s*=\s*([\d.]+)", re.MULTILINE)


class DebrieferParseError(Exception):
    pass


@dataclass
class DebriefHeader:
    mission_file_path: str | None = None
    # NON FIABLE (spec §2.2, fait 1) -- conservé uniquement pour traçabilité/
    # debug, JAMAIS utilisé pour résoudre une identité.
    callsign_header_unreliable: str | None = None
    # Champs racine, écrits à la sortie de mission (brief HOTFIX ancre
    # temps réel §Volet 1.b) -- constatés APRÈS le bloc graveyard dans le
    # texte, d'où la regex racine dédiée dans _parse_header.
    mission_file_mark: int | None = None
    mission_time: float | None = None


@dataclass
class DebriefEvent:
    index: int
    t: float | None
    type: str | None
    initiator_object_id: str | None
    initiator_pilot_name: str | None
    initiator_unit_type: str | None
    initiator_mission_id: str | None
    initiator_coalition: str | None
    target_object_id: str | None
    target_pilot_name: str | None
    target_unit_type: str | None
    weapon: str | None
    event_id: str | None
    linked_event_id: str | None
    # `target` = slot mission (ex. "Spangdahlem_Mi-24P_513-1"), pertinent
    # uniquement sur les events `under control` (spec §3, brief §3.1).
    target_slot: str | None
    target_mission_id: str | None
    # Lot « Le passage moteur » : camp de la cible, lu tel quel -- même
    # encodage que `initiator_coalition` ("0" neutre, "1" rouge, "2" bleu,
    # "-1" quand DCS ne sait pas). Sa validité se juge dans le moteur
    # (`engine._coalition_valide`), jamais ici. Valeur par défaut : les
    # événements fabriqués par les tests ne le portent pas.
    target_coalition: str | None = None
    raw: dict = field(default_factory=dict, repr=False)


@dataclass
class DebriefGraveyardEntry:
    index: int
    unit_type: str | None
    coalition: str | None
    x: float | None
    y: float | None
    alt: float | None
    heading: float | None


@dataclass
class DebriefLogData:
    header: DebriefHeader
    events: list[DebriefEvent]
    graveyard: list[DebriefGraveyardEntry]

    def under_control_object_ids(self) -> set[str]:
        """Toutes les vies du déposant (spec §4.2) -- exhaustif par
        construction du fichier DCS."""
        return {
            e.initiator_object_id
            for e in self.events
            if e.type == "under control" and e.initiator_object_id
        }


def _extract_braced_section(text: str, section_name: str) -> str | None:
    """Isole le contenu `{ ... }` de la section `section_name = { ... }`
    (ou `["section_name"] = { ... }`) par comptage d'accolades (robuste à
    la présence/absence de commentaires `-- end of ...`)."""
    pattern = re.compile(
        r'\[?"?' + re.escape(section_name) + r'"?\]?\s*=\s*\{'
    )
    m = pattern.search(text)
    if m is None:
        return None
    start = m.end()  # juste après l'accolade ouvrante
    depth = 1
    i = start
    n = len(text)
    while i < n and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return text[start : i - 1]


def _parse_fields(entry_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for m in _FIELD_RE.finditer(entry_text):
        key = m.group("key")
        if m.group("str") is not None:
            fields[key] = m.group("str")
        elif m.group("num") is not None:
            fields[key] = m.group("num")
        elif m.group("bool") is not None:
            fields[key] = m.group("bool")
    return fields


def _parse_header(text: str, graveyard_start: int | None) -> DebriefHeader:
    header_text = text if graveyard_start is None else text[:graveyard_start]
    fields = _parse_fields(header_text)

    mark_m = _MISSION_FILE_MARK_RE.search(text)
    mission_file_mark: int | None = None
    if mark_m is not None:
        try:
            mission_file_mark = int(mark_m.group(1))
        except ValueError:
            mission_file_mark = None

    time_m = _MISSION_TIME_RE.search(text)
    mission_time = _to_float(time_m.group(1)) if time_m is not None else None

    return DebriefHeader(
        mission_file_path=fields.get("mission_file_path"),
        callsign_header_unreliable=fields.get("callsign"),
        mission_file_mark=mission_file_mark,
        mission_time=mission_time,
    )


def _to_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_events(events_section: str) -> list[DebriefEvent]:
    events: list[DebriefEvent] = []
    for m in _ENTRY_RE.finditer(events_section):
        idx = int(m.group("idx"))
        raw = _parse_fields(m.group("body"))
        events.append(
            DebriefEvent(
                index=idx,
                t=_to_float(raw.get("t")),
                type=raw.get("type"),
                initiator_object_id=raw.get("initiator_object_id"),
                initiator_pilot_name=raw.get("initiatorPilotName"),
                initiator_unit_type=raw.get("initiator_unit_type"),
                initiator_mission_id=raw.get("initiatorMissionID"),
                initiator_coalition=raw.get("initiator_coalition"),
                target_object_id=raw.get("target_object_id"),
                target_pilot_name=raw.get("targetPilotName"),
                target_unit_type=raw.get("target_unit_type"),
                weapon=raw.get("weapon"),
                event_id=raw.get("event_id"),
                linked_event_id=raw.get("linked_event_id"),
                target_slot=raw.get("target"),
                target_mission_id=raw.get("targetMissionID"),
                target_coalition=raw.get("target_coalition"),
                raw=raw,
            )
        )
    events.sort(key=lambda e: e.index)
    return events


def _parse_graveyard(graveyard_section: str) -> list[DebriefGraveyardEntry]:
    entries: list[DebriefGraveyardEntry] = []
    for m in _ENTRY_RE.finditer(graveyard_section):
        idx = int(m.group("idx"))
        raw = _parse_fields(m.group("body"))
        entries.append(
            DebriefGraveyardEntry(
                index=idx,
                unit_type=raw.get("type"),
                coalition=raw.get("coalition"),
                x=_to_float(raw.get("x")),
                y=_to_float(raw.get("y")),
                alt=_to_float(raw.get("alt")),
                heading=_to_float(raw.get("heading")),
            )
        )
    entries.sort(key=lambda e: e.index)
    return entries


def parse_debrief_log(source: Union[str, Path]) -> DebriefLogData:
    """Parse un fichier `debrief.log`. Lecture intégrale en texte (fichiers
    petits comparés à l'ACMI -- pas de contrainte de streaming ici, cf.
    volumétrie escadron notée spec §7)."""
    path = Path(source)
    text = path.read_text(encoding="utf-8", errors="replace")

    graveyard_match = re.search(r'\[?"?graveyard"?\]?\s*=\s*\{', text)
    graveyard_start = graveyard_match.start() if graveyard_match else None

    header = _parse_header(text, graveyard_start)

    graveyard_section = _extract_braced_section(text, "graveyard") or ""
    events_section = _extract_braced_section(text, "events") or ""

    if not events_section:
        raise DebrieferParseError(
            f"Section 'events' introuvable ou vide dans {path}"
        )

    graveyard = _parse_graveyard(graveyard_section)
    events = _parse_events(events_section)

    return DebriefLogData(header=header, events=events, graveyard=graveyard)
