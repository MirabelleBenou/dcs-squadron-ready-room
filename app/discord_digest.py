"""Route interne dédiée au déclenchement du digest Discord — Lot 7.

Routeur séparé de `app/api.py` (monté directement dans `main.py`) : surface
volontairement isolée, protégée par le seul token partagé
`DISCORD_DIGEST_TOKEN` — **hors auth Discord OAuth**, appel machine
(cron ou déclenchement manuel), cf. brief §4.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.config import settings
from app.db import get_db
from app.defense import jeton_valide
from app.discord_notify import post_digest

router = APIRouter(prefix="/api/internal")


@router.post("/digest", status_code=204)
async def trigger_digest(
    anchor: Optional[date] = Query(None),
    x_digest_token: Optional[str] = Header(None, alias="X-Digest-Token"),
    db: AsyncSession = Depends(get_db),
):
    # Lot « La défense de l'App exposée » (R5) : comparaison à temps constant.
    if not jeton_valide(settings.DISCORD_DIGEST_TOKEN, x_digest_token):
        raise HTTPException(status_code=403, detail="Token invalide ou absent")

    await post_digest(db, anchor)
    return None
