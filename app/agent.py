"""Lot « La réception du .rrlog de l'agent » (`v1.0089`, `rr-agent-reception`) -- la route
que l'agent du serveur DCS (0.2.0) appelle pour envoyer un `.rrlog`.

`POST /api/agent/rrlog` vit hors de la session : seul l'authentifie l'en-tête
`Authorization: Bearer <jeton>` (R1, R2). Le jeton ne se garde que haché (sha256) ; l'App ne
fait que ranger le fichier reçu (`DEBRIEF_STORAGE_DIR/_agent/<sha256>.rrlog.gz`) et le noter
au registre `agent_rrlog` -- aucune session de Débrief n'en naît. La lecture du fichier est
l'affaire d'un autre lot. Le contrat d'envoi est celui du §3.4 de `ag-v0.2.0` : seul le code
de la réponse compte pour l'agent.

Ce module sert aussi les routes du Centre (`app.command.api`) : fabrication et empreinte
du jeton.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import unicodedata
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.defense import PLAFOND_AGENT
from app.models import AgentJeton, AgentRrlog

router = APIRouter(prefix="/api/agent")

PLAFOND_AGENT_DECOMPRESSE = 134_217_728  # 128 Mio

_PREFIXE_JETON = "rra_"
_FORME_AUTORISATION = re.compile("^Bearer (" + re.escape(_PREFIXE_JETON) + "[A-Za-z0-9_-]{1,128})$")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_ENTIER = re.compile(r"[0-9]{1,9}")
_POURCENT_MAL_FORME = re.compile(r"%(?![0-9A-Fa-f]{2})")
_TETE_MAX = 65_536  # la première ligne doit tenir dans ces octets
_PAS_DECOMPRESSION = 1_048_576  # `max_length` d'un appel de décompression
_DOSSIER = "_agent"


# --- Le jeton ------------------------------------------------------------------


def empreinte_jeton(jeton: str) -> str:
    """L'empreinte (sha256 hexadécimal) d'un jeton : la seule chose qui se garde."""
    return hashlib.sha256(jeton.encode("utf-8")).hexdigest()


def nouveau_jeton() -> tuple[str, str]:
    """`(jeton en clair, empreinte)` : 32 octets aléatoires, préfixés. Le clair n'est
    rendu qu'à la réponse de l'émission."""
    clair = _PREFIXE_JETON + secrets.token_urlsafe(32)
    return clair, empreinte_jeton(clair)


# Lot « La réception du .rrlog de l'agent », addendum 2 (A5) : le verrou de transaction qui sérialise les
# émissions de jeton -- un seul jeton actif, même si deux émissions partent ensemble.
VERROU_JETON = 5_240_177_103


async def verrouiller_emission(db: AsyncSession) -> None:
    """Prend le verrou de transaction des émissions (relâché au `commit` ou au `rollback`)."""
    await db.execute(text("SELECT pg_advisory_xact_lock(:cle)"), {"cle": VERROU_JETON})


def _refus_jeton() -> JSONResponse:
    return JSONResponse({"detail": "Jeton refusé."}, status_code=401)


def _refus(code: int, detail: str) -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=code)


async def _jetons_actifs(db: AsyncSession) -> list[AgentJeton]:
    """Les jetons non révoqués (un seul, par construction)."""
    return list(
        (await db.execute(select(AgentJeton).where(AgentJeton.revoque_le.is_(None)))).scalars().all()
    )


async def _jeton_accepte(db: AsyncSession, autorisation: str | None) -> int | None:
    """L'identifiant du jeton actif que porte l'en-tête, ou `None` : absent, d'une autre forme,
    inconnu ou révoqué. Comparé sur l'empreinte, à temps constant."""
    if not autorisation:
        return None
    forme = _FORME_AUTORISATION.match(autorisation)
    if forme is None:
        return None
    calculee = empreinte_jeton(forme.group(1)).encode("ascii")
    trouve = None
    for jeton in await _jetons_actifs(db):
        if hmac.compare_digest(str(jeton.empreinte).encode("ascii", "replace"), calculee):
            trouve = jeton.id
    return trouve


# --- Les en-têtes ----------------------------------------------------------------


def nom_de_fichier(brut: str | None) -> str | None:
    """Le nom décodé de `X-RR-Fichier`, ou `None` s'il est refusé : absent ou vide, pourcent mal
    formé, UTF-8 invalide, plus de 255 caractères, ou contenant `/`, `\\` ou un caractère de
    contrôle."""
    if not brut or not brut.isascii():
        return None    # des octets bruts non encodés en pourcent : refusé
    if _POURCENT_MAL_FORME.search(brut):
        return None
    try:
        nom = unquote(brut, encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    if not nom or len(nom) > 255 or "/" in nom or "\\" in nom:
        return None
    if any(unicodedata.category(c) == "Cc" for c in nom):
        return None
    return nom


def champs_de_la_ligne_h(ligne: bytes) -> dict | None:
    """Les champs que dit la première ligne (`H` ⇥ `rrlog` ⇥ entier ⇥ version de l'agent ⇥ mission ⇥
    théâtre ⇥ date de mission ⇥ heure de départ ⇥ départ réel), ou `None` si ce n'est pas
    une ligne `H` de `rrlog`, ou si elle porte un caractère de contrôle autre que la tabulation. Un champ manquant ou vide reste `None`."""
    try:
        texte = ligne.rstrip(b"\r").decode("utf-8")
    except UnicodeDecodeError:
        return None
    # Aucun caractère de contrôle autre que la tabulation : un `\x00` ferait échouer l'écriture en base.
    if any(unicodedata.category(c) == "Cc" and c != "\t" for c in texte):
        return None
    champs = texte.split("\t")
    if len(champs) < 3 or champs[0] != "H" or champs[1] != "rrlog" or not _ENTIER.fullmatch(champs[2]):
        return None

    def lire(i: int) -> str | None:
        return (champs[i] or None) if i < len(champs) else None

    return {
        "format": int(champs[2]),
        "agent_version": lire(3),
        "mission": lire(4),
        "theatre": lire(5),
        "date_mission": lire(6),
        "depart_reel": lire(8),
    }


# --- Le registre ------------------------------------------------------------------


async def _recu_par_sha(db: AsyncSession, sha: str) -> AgentRrlog | None:
    return (await db.execute(select(AgentRrlog).where(AgentRrlog.sha256 == sha))).scalars().first()


async def _poser_dernier_envoi(db: AsyncSession, jeton_id: int, quand: datetime) -> None:
    """R6 : le dernier envoi du jeton, à l'heure du serveur (UTC)."""
    await db.execute(update(AgentJeton).where(AgentJeton.id == jeton_id).values(dernier_envoi_le=quand))


def _retirer(chemin: Path | None) -> None:
    if chemin is not None:
        try:
            chemin.unlink()
        except FileNotFoundError:
            pass


class _Refus(Exception):
    """Un refus de la lecture du corps : le code et le `detail`."""

    def __init__(self, code: int, detail: str):
        self.code = code
        self.detail = detail


async def _lire_le_corps(request: Request, temporaire: Path) -> tuple[str, int, int, bytes]:
    """Lit le corps par morceaux : range le gzip tel que reçu dans `temporaire`, le décompresse au fil de
    la lecture (`max_length` à chaque appel : jamais plus de 128 Mio, jamais tout en mémoire) et calcule le
    sha256 du flux décompressé. Rend `(sha256, taille_gz, taille, tête)` -- `tête` : les premiers
    octets décompressés. Lève `_Refus` : 413 au-delà d'un plafond, 422 pour un gzip invalide ou tronqué."""
    decomp = zlib.decompressobj(16 + zlib.MAX_WBITS)
    sha = hashlib.sha256()
    taille_gz = 0
    taille = 0
    tete = b""
    with open(temporaire, "wb") as sortie:
        async for morceau in request.stream():
            if not morceau:
                continue
            taille_gz += len(morceau)
            if taille_gz > PLAFOND_AGENT:
                raise _Refus(413, "Requête trop volumineuse.")
            sortie.write(morceau)
            restant = bytes(morceau)
            while restant:
                # `max_length` : au plus 1 Mio par appel, et jamais plus que ce que le plafond laisse
                # (plus un octet pour voir qu'il est dépassé) : une bombe ne tient jamais en mémoire.
                avant = len(restant)
                try:
                    sorti = decomp.decompress(
                        restant, min(PLAFOND_AGENT_DECOMPRESSE - taille + 1, _PAS_DECOMPRESSION)
                    )
                except zlib.error:
                    raise _Refus(422, "Fichier gzip invalide.") from None
                taille += len(sorti)
                if taille > PLAFOND_AGENT_DECOMPRESSE:
                    raise _Refus(413, "Fichier décompressé trop volumineux.")
                sha.update(sorti)
                if len(tete) < _TETE_MAX:
                    tete += sorti[: _TETE_MAX - len(tete)]
                restant = decomp.unconsumed_tail
                if decomp.eof:
                    break
                if not sorti and len(restant) >= avant:
                    raise _Refus(422, "Fichier gzip invalide.")  # aucun progrès : pas un gzip
            if decomp.eof and (decomp.unused_data or restant):
                raise _Refus(422, "Fichier gzip invalide.")
    if not decomp.eof:
        raise _Refus(422, "Fichier gzip tronqué.")
    if decomp.unused_data:
        raise _Refus(422, "Fichier gzip invalide.")
    return sha.hexdigest(), taille_gz, taille, tete


async def _retirer_si_orphelin(db: AsyncSession, sha: str, final: Path) -> None:
    """Retire le fichier rangé par cette requête, SEULEMENT si aucune ligne du registre ne porte ce sha256 (relu
    après le rollback). Si la relecture échoue, le fichier reste : mieux vaut un orphelin que le fichier d'un autre."""
    try:
        if await _recu_par_sha(db, sha) is None:
            _retirer(final)
    except Exception:
        pass


@router.post("/rrlog")
async def recevoir_rrlog(request: Request, db: AsyncSession = Depends(get_db)):
    """R1 à R6 : reçoit un `.rrlog` gzip de l'agent. 401 sans lire le corps ; puis les en-têtes (422) ; puis le
    corps (413 · 422) ; déjà reçu : 200 ; reçu : 201."""
    # R2 : le jeton d'abord, avant toute lecture du corps.
    jeton_id = await _jeton_accepte(db, request.headers.get("authorization"))
    if jeton_id is None:
        return _refus_jeton()
    # Addendum 2 (A3) : la transaction de lecture se clôt ; la connexion ne reste pas prise pendant l'envoi.
    await db.rollback()

    # R3 : les en-têtes.
    fichier = nom_de_fichier(request.headers.get("x-rr-fichier"))
    if fichier is None:
        return _refus(422, "En-tête X-RR-Fichier absent ou invalide.")
    sha_annonce = request.headers.get("x-rr-sha256")
    if sha_annonce is None or not _SHA256.fullmatch(sha_annonce):
        return _refus(422, "En-tête X-RR-Sha256 absent ou invalide.")

    dossier = Path(settings.DEBRIEF_STORAGE_DIR) / _DOSSIER
    dossier.mkdir(parents=True, exist_ok=True)
    temporaire = dossier / (".tmp-" + uuid.uuid4().hex)
    final: Path | None = None
    cree = False       # le fichier rangé l'a été par CETTE requête
    sha = ""
    try:
        try:
            sha, taille_gz, taille, tete = await _lire_le_corps(request, temporaire)
        except _Refus as refus:
            return _refus(refus.code, refus.detail)
        if sha != sha_annonce:
            return _refus(422, "Le sha256 ne correspond pas au fichier.")
        premiere = tete.split(b"\n", 1)[0]
        if b"\n" not in tete and taille > _TETE_MAX:
            return _refus(422, "Première ligne illisible.")
        champs = champs_de_la_ligne_h(premiere)
        if champs is None:
            return _refus(422, "Première ligne : ce n'est pas un rrlog.")

        # Addendum 2 (A3) : avant l'écriture, le jeton est relu et doit être encore actif.
        if jeton_id not in [j.id for j in await _jetons_actifs(db)]:
            await db.rollback()
            return _refus_jeton()

        maintenant = datetime.now(timezone.utc)
        final = dossier / (sha + ".rrlog.gz")
        try:
            # R4 : déjà reçu.
            if await _recu_par_sha(db, sha) is not None:
                await _poser_dernier_envoi(db, jeton_id, maintenant)
                await db.commit()
                final = None
                return JSONResponse({"statut": "deja_recu"}, status_code=200)

            # R5 : reçu. Le gzip tel que reçu -- jamais d'écrasement d'un fichier déjà rangé --, puis la ligne
            # au registre. Toute l'écriture en base est dans ce `try` : l'`INSERT` part au `flush`.
            try:
                os.link(temporaire, final)
                cree = True
            except FileExistsError:
                cree = False
            db.add(
                AgentRrlog(
                    sha256=sha, fichier=fichier, chemin=f"{_DOSSIER}/{sha}.rrlog.gz",
                    taille_gz=taille_gz, taille=taille, recu_le=maintenant, jeton_id=jeton_id,
                    etat="en_attente", **champs,
                )
            )
            await db.flush()
            await _poser_dernier_envoi(db, jeton_id, maintenant)
            await db.commit()
            return JSONResponse({"statut": "recu"}, status_code=201)
        except IntegrityError:
            # Deux envois du même fichier : la contrainte d'unicité tranche, le perdant rend 200. Le fichier rangé
            # reste : la ligne du gagnant le porte. Une autre violation d'intégrité n'est pas un doublon.
            await db.rollback()
            if await _recu_par_sha(db, sha) is None:
                raise
            await _poser_dernier_envoi(db, jeton_id, maintenant)
            await db.commit()
            return JSONResponse({"statut": "deja_recu"}, status_code=200)
    except BaseException:
        # L'écriture en base a échoué : le fichier rangé par cette requête n'est retiré que si aucune ligne du
        # registre ne le porte.
        if cree and final is not None:
            try:
                await db.rollback()
            except Exception:
                pass
            await _retirer_si_orphelin(db, sha, final)
        raise
    finally:
        _retirer(temporaire)
