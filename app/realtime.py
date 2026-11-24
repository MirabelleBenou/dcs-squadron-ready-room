"""Temps réel — Lot 3a. Cf. BRIEF_SONNET_ReadyRoom_Lot3a_Realtime_API §1/§2/§3
et SPEC_TECHNIQUE_READY_ROOM_Planification_v1 §6.

Bus pub/sub **en mémoire, instance unique** (hypothèse documentée — cf.
VIGILANCE du brief) : une `asyncio.Queue` bornée par client connecté à
`GET /api/stream`. `publish_invalidate()` est appelé par `app/events.py`
APRÈS commit des mutations (jamais avant, sinon le re-fetch client peut lire
l'état d'avant écriture).

Un déploiement multi-instances nécessiterait un broker externe (Redis
pub/sub ou équivalent) pour diffuser entre processus — explicitement hors
périmètre de ce lot.
"""
from __future__ import annotations

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.auth import get_current_user

# Taille max de la file par client. Au-delà, on droppe le message le plus
# ancien (drop-oldest) plutôt que de laisser la mémoire croître sans borne
# si un client est lent ou ne lit plus son flux (cf. vigilance brief).
_MAX_QUEUE_SIZE = 50

# Intervalle du keep-alive (commentaire SSE `: ping`). Nécessaire derrière
# le Tailscale Funnel / tout proxy intermédiaire qui coupe les connexions
# HTTP inactives (cf. vigilance brief).
_KEEPALIVE_SECONDS = 20


class Broker:
    """Pub/sub en mémoire : une `asyncio.Queue` par client abonné."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        # `discard` : idempotent, pas d'erreur si déjà retiré.
        self._subscribers.discard(queue)

    def publish(self, message: dict) -> None:
        """Diffuse `message` à toutes les files abonnées. Ne bloque jamais
        la boucle asyncio : un abonné dont la file est pleine (client trop
        lent) se voit dropper son message le plus ancien plutôt que de
        bloquer l'émetteur ou croître indéfiniment."""
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()  # drop-oldest
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    pass  # abonné toujours saturé : message perdu, tant pis pour ce tour

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


broker = Broker()


def publish_invalidate(
    scope: str, event_id: str, occ_date: Optional[str] = None
) -> None:
    """Signal léger de mutation — cf. brief §3. Le client re-fetch la donnée
    concernée ; aucun diff n'est transmis ici."""
    broker.publish(
        {
            "type": "invalidate",
            "scope": scope,
            "event_id": event_id,
            "occ_date": occ_date,
        }
    )


router = APIRouter()


@router.get("/stream")
async def stream(request: Request, user: dict = Depends(get_current_user)):
    """`GET /api/stream` — SSE. Protégé par la session applicative (comme
    toutes les autres routes `/api/*`). La dépendance `get_current_user` lit la
    base à l'ouverture du flux ; ensuite le flux ne relit ni la base ni les
    droits tant qu'il reste ouvert."""
    queue = broker.subscribe()

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(
                        queue.get(), timeout=_KEEPALIVE_SECONDS
                    )
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive : commentaire SSE, ignoré par l'EventSource
                    # client mais empêche les proxies (Funnel) de couper la
                    # connexion pour inactivité.
                    yield ": ping\n\n"
        finally:
            # Exécuté que la boucle se termine normalement (disconnect
            # détecté), ou que la tâche soit annulée par le serveur ASGI à
            # la fermeture de la connexion (GeneratorExit/CancelledError) :
            # jamais de fuite de file abonnée.
            broker.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            # Désactive le buffering proxy (nginx-style directive, reprise
            # par certains proxys même hors nginx) — indispensable derrière
            # le Funnel pour un flux SSE qui ne se fige pas.
            "X-Accel-Buffering": "no",
        },
    )
