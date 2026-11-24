"""Normalisation et stockage des écussons d'escadrille (Lot 3.2e, volet ②,
cf. BRIEF_SONNET_ReadyRoom_Lot_3_2e_Volet2.md §6). Fichier NEUF, hors
`app/command/` : la route de lecture (§7.2) vit hors du module Centre de
Commandement (`app/api.py`, aux côtés de `/api/me`) et s'en sert aussi --
loger ce module sous `app/command/` obligerait la route de lecture à
importer à travers la garde du module, pour rien.

Écrit et éprouvé SEUL, sur des fichiers du disque, avant que la moindre
route ne l'appelle (§0, ordre d'exécution imposé) -- c'est la seule pièce
de ce lot qui manipule des octets hostiles déposés par un utilisateur ;
l'éprouver à travers HTTP masquerait ses défauts derrière des codes de
statut.

Trois fonctions publiques, dans l'ordre où une route les appelle :
    1. `read_bounded(upload_file)`      -- lecture bornée du flux (§6.1)
    2. `normalize_crest(raw_bytes)`     -- reconnaissance, décodage,
                                           normalisation, ré-encodage (§6.2-§6.4)
    3. `write_temp` / `finalize_crest`  -- écriture atomique (§6.5), séparée
                                           en deux étapes pour respecter
                                           l'ordre imposé par la route
                                           d'écriture (§7.1) : le fichier
                                           temporaire est posé AVANT le
                                           commit en base, le remplacement
                                           atomique n'intervient qu'APRÈS.
"""
from __future__ import annotations

import io
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from app.config import settings

# --- §6.1 : bornes ------------------------------------------------------

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MiB, code de refus 413
STORED_SIDE = 512  # côté stocké AU MAXIMUM (§6.4, geste 3 -- jamais agrandi)

# Plafond EXPLICITE de pixels décodés (bombe de décompression traitée
# comme un refus, §6.1/P13). 4096×4096 = 16 777 216 px : très au-dessus de
# tout écusson légitime (stocké à 512 px max) mais borné -- une image
# déclarant des dimensions démesurées (des dizaines de milliers de pixels
# de côté, poids d'en-tête négligeable) doit être refusée AVANT toute
# tentative de décodage complet des pixels.
MAX_DECODED_PIXELS = 4096 * 4096

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_CHUNK_SIZE = 64 * 1024


class CrestTooLarge(Exception):
    """Dépassement de `MAX_UPLOAD_BYTES` (§6.1) -- l'appelant lève 413."""


class CrestInvalidFormat(Exception):
    """Format non reconnu sur les octets (§6.2), ou décodage impossible /
    bombe de décompression / fichier tronqué (§6.3) -- l'appelant lève
    422, jamais une trace de pile."""


@dataclass(frozen=True)
class CrestNormalizationReport:
    """Rendu par `normalize_crest()` en plus des octets PNG (§6.4, dernier
    paragraphe) : dimensions source, format source, poids source, côté
    stocké, poids stocké, et le drapeau « première image retenue » le cas
    échéant."""

    source_format: str
    source_width: int
    source_height: int
    source_bytes: int
    stored_side: int
    stored_bytes: int
    first_frame_retained: bool


# --- §6.1 : lecture bornée du flux --------------------------------------


async def read_bounded(upload_file, limit: int = MAX_UPLOAD_BYTES) -> bytes:
    """Lit `upload_file` (UploadFile Starlette/FastAPI) par morceaux, avec
    un compteur, et ABANDONNE dès le dépassement de `limit`. Ne fait
    JAMAIS `await file.read()` sans borne : un envoi de 5 Go serait lu en
    mémoire avant d'être refusé. La lecture s'arrête réellement avant la
    fin du flux -- aucun morceau supplémentaire n'est demandé une fois la
    borne dépassée (P12, prouvé par l'ordre des appels ci-dessous, pas
    seulement par le code de retour)."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload_file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise CrestTooLarge(
                f"Fichier de plus de {limit} octets ({limit // (1024 * 1024)} MiB au maximum)."
            )
        chunks.append(chunk)
    return b"".join(chunks)


# --- §6.2 : reconnaissance du format sur les octets ----------------------


def _sniff_format(raw: bytes) -> str:
    """Le format se lit dans les premiers octets, JAMAIS dans le nom ni
    l'en-tête -- `filename` et `content_type` viennent du client, ils ne
    prouvent rien. Signature PNG `\\x89PNG\\r\\n\\x1a\\n` ; WebP = conteneur
    RIFF portant WEBP. Tout le reste est refusé, y compris un fichier
    vectoriel renommé en `.png`."""
    if raw[:8] == _PNG_SIGNATURE:
        return "png"
    if len(raw) >= 12 and raw[0:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    raise CrestInvalidFormat(
        "Signature de fichier non reconnue (PNG ou WebP attendu)."
    )


# --- §6.3/§6.4 : décodage puis normalisation en quatre gestes ------------


def normalize_crest(raw: bytes) -> tuple[bytes, CrestNormalizationReport]:
    """Décode `raw`, normalise, ré-encode. Lève `CrestInvalidFormat` pour
    tout échec de reconnaissance, décodage, ou bombe de décompression --
    jamais une trace de pile (§6.2/§6.3).

    Geste 4 (dernier paragraphe §6.4) : le PNG écrit est reconstruit
    depuis les pixels décodés -- rien de ce que le client a envoyé
    n'atteint jamais un navigateur. C'est ce qui neutralise un fichier
    piégé et permet de servir le fichier sans crainte au §7.2.
    """
    source_format = _sniff_format(raw)
    source_bytes = len(raw)

    # Garde-fou bombe de décompression, gardé comme filet en plus du
    # contrôle explicite ci-dessous (jamais une mutation globale durable :
    # Image.MAX_IMAGE_PIXELS est un attribut de classe partagé par tout le
    # process, le fixer ici à la même constante à chaque appel reste sans
    # effet de bord d'un appel à l'autre).
    Image.MAX_IMAGE_PIXELS = MAX_DECODED_PIXELS

    try:
        im = Image.open(io.BytesIO(raw))
    except Exception as exc:  # décodage Pillow : jamais de trace de pile au-delà
        raise CrestInvalidFormat(f"Décodage impossible : {exc}") from exc

    # ⚠ Contrôle EXPLICITE du plafond, avant tout décodage complet des
    # pixels -- Pillow ne lève `DecompressionBombError` qu'au-delà de
    # DEUX FOIS `MAX_IMAGE_PIXELS` (en dessous, ce n'est qu'un
    # avertissement silencieux, jamais un refus). S'en remettre à ce seul
    # comportement laisserait passer une image entre le plafond annoncé et
    # son double. `im.size` est lisible dès l'en-tête pour PNG et WebP,
    # sans coût de décodage des pixels.
    width, height = im.size
    if width * height > MAX_DECODED_PIXELS:
        raise CrestInvalidFormat(
            f"Image refusée (dimensions démesurées) : {width}x{height} px "
            f"dépasse le plafond de {MAX_DECODED_PIXELS} px décodés."
        )

    try:
        # Force le chargement effectif des pixels -- une ouverture seule
        # ne lit que l'en-tête et ne détecte pas un fichier tronqué (§6.3).
        im.load()
    except Image.DecompressionBombError as exc:
        # Filet de sécurité si jamais le contrôle explicite ci-dessus était
        # un jour contourné (format exotique sans taille fiable en-tête).
        raise CrestInvalidFormat(
            f"Image refusée (dimensions démesurées) : {exc}"
        ) from exc
    except Exception as exc:
        raise CrestInvalidFormat(f"Décodage impossible : {exc}") from exc

    # Entrée animée (APNG, WebP animé) : retient la première image, le
    # signale dans le rapport (§6.3, dernier paragraphe).
    first_frame_retained = False
    if getattr(im, "is_animated", False):
        try:
            im.seek(0)
        except Exception:
            pass
        first_frame_retained = True

    source_width, source_height = im.size

    # Geste 1 -- conversion en RGBA : la transparence est une donnée, pas
    # un détail.
    im = im.convert("RGBA")

    # Geste 2 -- mise au carré par ajout de transparence (`contain`,
    # jamais `cover` : un écusson ne se recadre pas).
    side_before_resize = max(im.width, im.height)
    squared = Image.new("RGBA", (side_before_resize, side_before_resize), (0, 0, 0, 0))
    offset = (
        (side_before_resize - im.width) // 2,
        (side_before_resize - im.height) // 2,
    )
    squared.paste(im, offset)

    # Geste 3 -- réduction au côté cible : min(512, max(largeur, hauteur)).
    # N'AGRANDIS JAMAIS : une source de 64 px reste à 64 px.
    target_side = min(STORED_SIDE, side_before_resize)
    if target_side != side_before_resize:
        squared = squared.resize((target_side, target_side), Image.LANCZOS)

    # Geste 4 -- ré-encodage en PNG, optimisé, image neuve, sans reporter
    # aucune métadonnée de la source (aucun `pnginfo=` transmis : `save()`
    # sans cet argument n'écrit que les chunks obligatoires).
    out = io.BytesIO()
    squared.save(out, format="PNG", optimize=True)
    stored_bytes = out.getvalue()

    report = CrestNormalizationReport(
        source_format=source_format,
        source_width=source_width,
        source_height=source_height,
        source_bytes=source_bytes,
        stored_side=target_side,
        stored_bytes=len(stored_bytes),
        first_frame_retained=first_frame_retained,
    )
    return stored_bytes, report


# --- §6.5 : écriture, en deux temps (cf. docstring de tête) -------------


def _storage_dir() -> Path:
    """Patron exact de `app.debrief.engine._storage_dir()` -- crée le
    répertoire à la demande."""
    d = Path(settings.CREST_STORAGE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def crest_path(squadron_id: int) -> Path:
    """Chemin FIXE `{CREST_STORAGE_DIR}/{squadron_id}.png` (§6.5). Le nom
    fixe supprime la notion d'orphelin : le remplacement écrase, il n'y a
    jamais deux fichiers pour une escadrille. Utilisée aussi par la route
    de lecture (§7.2)."""
    return _storage_dir() / f"{squadron_id}.png"


def write_temp(squadron_id: int, png_bytes: bytes) -> Path:
    """Écrit le PNG normalisé dans un fichier temporaire du MÊME volume,
    sans encore le rendre visible aux lecteurs (§7.1, étape 4 -- posée
    AVANT le commit en base, étape 5). Nom du temporaire propre à cette
    écriture précise (suffixe aléatoire) : deux téléversements concurrents
    sur la même escadrille ne se marchent pas dessus avant le remplacement
    atomique."""
    tmp_dir = _storage_dir() / "_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"{squadron_id}.{uuid.uuid4().hex}.tmp"
    tmp_path.write_bytes(png_bytes)
    return tmp_path


def finalize_crest(tmp_path: Path, squadron_id: int) -> Path:
    """Remplacement atomique (§7.1, étape 6 -- APRÈS le commit en base) :
    le temporaire devient `{squadron_id}.png`. Idiome exact de
    `app.debrief.engine` (tmp puis `shutil.move`) -- une écriture directe
    sur le chemin final laisserait un PNG tronqué si le processus tombait
    au milieu."""
    final_path = crest_path(squadron_id)
    shutil.move(str(tmp_path), str(final_path))
    return final_path


# --- Lot « L'écran Escadre du Centre » : l'emblème de l'escadre ---------
#
# Même circuit que l'écusson d'une escadrille (lecture bornée, normalisation,
# temporaire puis remplacement atomique) ; seul le chemin change. Les trois
# fonctions ci-dessous s'ajoutent, aucune des précédentes n'est modifiée.


def wing_emblem_path() -> Path:
    """Chemin FIXE `{CREST_STORAGE_DIR}/wing.png`. Ne peut pas entrer en
    collision avec `crest_path(n)` (`{n}.png`, `n` entier) : « wing » n'est
    pas un identifiant d'escadrille."""
    return _storage_dir() / "wing.png"


def write_temp_wing(png_bytes: bytes) -> Path:
    """Équivalent de `write_temp` pour l'emblème : temporaire du MÊME volume,
    nom propre à cette écriture, posé AVANT le commit en base."""
    tmp_dir = _storage_dir() / "_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = tmp_dir / f"wing.{uuid.uuid4().hex}.tmp"
    tmp_path.write_bytes(png_bytes)
    return tmp_path


def finalize_wing_emblem(tmp_path: Path) -> Path:
    """Équivalent de `finalize_crest` pour l'emblème : remplacement atomique
    APRÈS le commit en base."""
    final_path = wing_emblem_path()
    shutil.move(str(tmp_path), str(final_path))
    return final_path


def discard_temp(tmp_path: Path) -> None:
    """Nettoyage du temporaire après un refus ou une erreur -- aucun
    fichier temporaire résiduel dans le volume après un téléversement
    réussi ET après un refus (P21). Idempotent : sans effet si le fichier
    a déjà été déplacé par `finalize_crest()`."""
    if tmp_path.exists():
        tmp_path.unlink(missing_ok=True)
