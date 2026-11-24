"""Parser TacView ACMI — spec §2.1 / brief §2.1.

Entrée : chemin d'un `.acmi` (zip contenant un `.txt.acmi`) ou flux binaire
zip. Décompression **en streaming** (fichiers 50 Mo+ : lecture ligne à ligne
après décompression, jamais de chargement intégral en RAM). Stdlib pure
(`zipfile`, `re`) -- aucune dépendance tierce (brief §5).

Sortie : structure Python normalisée (dataclasses), aucune écriture DB (la
fusion s'en charge, cf. app/debrief/engine.py).

Pièges impératifs (spec §8 faits 11-12, brief §2.1) :
- U/V (champs 6-7 du `T=`) ne sont présents qu'à la déclaration ; les
  updates ne portent que lon/lat. Tout calcul de position = lon/lat
  forward-fillés (par index de sous-champ). **Jamais** de filtre sur l'axe y
  (rn4/ng5 -- non applicable ici, mais règle générale de prudence sur les
  index de champs conservée par cohérence de convention projet).
- Altitudes aberrantes possibles (ex. 38320 m observée) -> on stocke la
  valeur brute + un booléen de plausibilité grossier (`altmax_suspect`).
  L'écrêtage fin par catégorie d'appareil est un raffinement d'affichage,
  hors périmètre D1 (spec §2.1 : "l'écrêtage se fera à l'affichage").
"""
from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Union

# Seuil grossier de plausibilité d'altitude (mètres), toutes catégories
# confondues -- un raffinement par type d'appareil relève du lot UI (D2).
ALTMAX_SUSPECT_THRESHOLD_M = 15000.0

_AI_SUFFIX_RE = re.compile(r"-\d+(-\d+)?$")
_AI_PREFIXES = ("AWACS", "DYNH")

# Index des sous-champs de la propriété `T=` (pipe-separated). Seuls
# lon/lat/alt (0/1/2) sont utilisés pour la position -- U/V (6/7) ne sont
# jamais lus pour un calcul de position (piège documenté).
_T_LON, _T_LAT, _T_ALT = 0, 1, 2

# Coalition ABSOLUE (brief Révision ④.1 chgt 5) : `Color` (Blue/Red) est la
# coalition réelle de l'objet, fiable en toutes circonstances. Le champ
# `Coalition` (Enemies/Allies…) est RELATIF au point de vue de l'enregistreur
# -- un objet allié peut y sortir "Enemies" si l'enregistreur est dans le
# camp adverse (vérifié sur données réelles : Red Falcon/The Hawk/Golem,
# bleus, y sortaient "Enemies"). Neutre/valeur inattendue -> None (jamais
# une coalition inventée).
_ACMI_COLOR_TO_COALITION = {"Blue": "2", "Red": "1"}


@dataclass
class AcmiMeta:
    title: str | None = None
    reference_time: datetime | None = None
    recording_time: datetime | None = None
    duration_s: int | None = None


@dataclass
class AcmiObject:
    track_id: str
    type: str | None = None
    name: str | None = None
    pilot: str | None = None
    group: str | None = None
    coalition: str | None = None
    country: str | None = None
    t_spawn: float | None = None
    t_despawn: float | None = None
    alt_max: float | None = None
    altmax_suspect: bool = False
    is_human: bool = False
    # Lot « Le Débrief : la destruction probable » (v1.0056, R1) : vrai quand
    # l'objet a été retiré par une ligne `-<id>` -- son retrait marque
    # l'impact mortel. `t_despawn` ne change pas : l'heure du retrait, ou à
    # défaut la dernière heure du fichier.
    retire: bool = False


@dataclass
class AcmiData:
    meta: AcmiMeta = field(default_factory=AcmiMeta)
    objects: dict[str, AcmiObject] = field(default_factory=dict)


class AcmiParseError(Exception):
    pass


def _split_unescaped(s: str, sep: str) -> list[str]:
    """Découpe `s` sur `sep`, en respectant l'échappement `\\<sep>` (format
    ACMI : une valeur peut contenir une virgule échappée)."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n and s[i + 1] == sep:
            buf.append(sep)
            i += 2
            continue
        if c == sep:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def _is_human_pilot(pilot: str | None, name: str | None, type_: str | None) -> bool:
    """Détection humaine (brief D1.1 §1 -- correctif) : un humain pilote
    obligatoirement un objet AÉRIEN. DCS attribue aussi un `Pilot=` à
    l'infanterie IA (`Type=Ground+Light+Human+Infantry` -- le mot "Human"
    désigne un fantassin, jamais un joueur), avec des suffixes numériques à
    underscores (ex. `..._dismounted_1_1`) non captés par `_AI_SUFFIX_RE`
    (motif à tirets). Le test aérien est un filtre SUPPLÉMENTAIRE, appliqué
    en plus des filtres suffixe/préfixe IA existants (jamais un remplacement)."""
    if not (type_ or "").startswith("Air"):
        return False
    if not pilot or pilot == name:
        return False
    if _AI_SUFFIX_RE.search(pilot):
        return False
    if any(pilot.startswith(p) for p in _AI_PREFIXES):
        return False
    return True


class _ObjectState:
    """État interne de parsing d'un objet ACMI (forward-fill des sous-champs
    T= par index -- jamais persistée telle quelle, seulement projetée en
    `AcmiObject` en fin de parse)."""

    __slots__ = ("t_fields", "t_spawn", "t_despawn", "alt_max", "props")

    def __init__(self) -> None:
        self.t_fields: list[str] = []
        self.t_spawn: float | None = None
        self.t_despawn: float | None = None
        self.alt_max: float | None = None
        self.props: dict[str, str] = {}

    def apply_t(self, raw_t: str) -> None:
        subfields = raw_t.split("|")
        if len(subfields) > len(self.t_fields):
            self.t_fields.extend([""] * (len(subfields) - len(self.t_fields)))
        for idx, sub in enumerate(subfields):
            if sub != "":
                self.t_fields[idx] = sub
        if len(self.t_fields) > _T_ALT and self.t_fields[_T_ALT]:
            try:
                alt = float(self.t_fields[_T_ALT])
            except ValueError:
                return
            if self.alt_max is None or alt > self.alt_max:
                self.alt_max = alt


def _find_acmi_member(zf: zipfile.ZipFile) -> str:
    candidates = [n for n in zf.namelist() if n.lower().endswith((".acmi", ".txt.acmi", ".txt"))]
    if not candidates:
        # Repli : un seul membre dans l'archive -> on le prend tel quel.
        names = zf.namelist()
        if len(names) == 1:
            return names[0]
        raise AcmiParseError("Aucun membre .acmi/.txt.acmi trouvé dans l'archive")
    return candidates[0]


def _parse_lines(lines) -> AcmiData:
    meta = AcmiMeta()
    states: dict[str, _ObjectState] = {}
    current_time: float | None = None
    first_time: float | None = None
    last_time: float | None = None

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        if not line:
            continue

        if line.startswith("FileType=") or line.startswith("FileVersion="):
            continue

        if line.startswith("#"):
            try:
                current_time = float(line[1:])
            except ValueError:
                continue
            if first_time is None:
                first_time = current_time
            last_time = current_time
            continue

        if line.startswith("-"):
            despawn_id = line[1:].strip()
            state = states.get(despawn_id)
            if state is not None and current_time is not None:
                state.t_despawn = current_time
            continue

        if "," in line:
            obj_id, rest = line.split(",", 1)
        else:
            obj_id, rest = line, ""
        obj_id = obj_id.strip()
        if not obj_id or not rest:
            continue

        field_strs = _split_unescaped(rest, ",")
        parsed_fields: dict[str, str] = {}
        for f in field_strs:
            if "=" not in f:
                continue
            key, value = f.split("=", 1)
            parsed_fields[key.strip()] = value

        if obj_id == "0":
            if "Title" in parsed_fields:
                meta.title = parsed_fields["Title"]
            if "ReferenceTime" in parsed_fields:
                raw_rt = parsed_fields["ReferenceTime"]
                try:
                    meta.reference_time = datetime.fromisoformat(
                        raw_rt.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            if "RecordingTime" in parsed_fields:
                raw_rec = parsed_fields["RecordingTime"]
                try:
                    meta.recording_time = datetime.fromisoformat(
                        raw_rec.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass
            continue

        state = states.get(obj_id)
        if state is None:
            state = _ObjectState()
            states[obj_id] = state
            if current_time is not None:
                state.t_spawn = current_time

        if "T" in parsed_fields:
            state.apply_t(parsed_fields["T"])
        for key in ("Type", "Name", "Pilot", "Group", "Coalition", "Country", "Color"):
            if key in parsed_fields:
                state.props[key] = parsed_fields[key]

    if last_time is not None:
        meta.duration_s = int(round(last_time - (first_time or 0.0)))

    objects: dict[str, AcmiObject] = {}
    for obj_id, state in states.items():
        pilot = state.props.get("Pilot")
        name = state.props.get("Name")
        alt_max = state.alt_max
        # Coalition dérivée de `Color` (absolu), jamais de `Coalition` (relatif
        # au point de vue de l'enregistreur -- non fiable, brief chgt 5).
        color = state.props.get("Color")
        coalition = _ACMI_COLOR_TO_COALITION.get(color)
        objects[obj_id] = AcmiObject(
            track_id=obj_id,
            type=state.props.get("Type"),
            name=name,
            pilot=pilot,
            group=state.props.get("Group"),
            coalition=coalition,
            country=state.props.get("Country"),
            t_spawn=state.t_spawn,
            t_despawn=state.t_despawn if state.t_despawn is not None else last_time,
            alt_max=alt_max,
            altmax_suspect=bool(alt_max is not None and alt_max > ALTMAX_SUSPECT_THRESHOLD_M),
            is_human=_is_human_pilot(pilot, name, state.props.get("Type")),
            # Lot « Le Débrief : la destruction probable » (R1) : seule une
            # ligne `-<id>` pose `state.t_despawn`.
            retire=state.t_despawn is not None,
        )

    return AcmiData(meta=meta, objects=objects)


def parse_acmi(source: Union[str, Path, BinaryIO]) -> AcmiData:
    """Parse un fichier/flux ACMI (zip contenant un .txt.acmi). Streaming :
    lecture ligne à ligne du membre décompressé, aucun chargement intégral.
    """
    if isinstance(source, (str, Path)):
        zf = zipfile.ZipFile(source)
    else:
        zf = zipfile.ZipFile(source)

    with zf:
        member = _find_acmi_member(zf)
        with zf.open(member, "r") as raw:
            text_stream = io.TextIOWrapper(raw, encoding="utf-8", errors="replace")
            return _parse_lines(text_stream)
