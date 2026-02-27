import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

connected_clients: Set[WebSocket] = set()


@router.websocket("/ws/news")
async def news_websocket(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    logger.info(f"WebSocket client connected. Total: {len(connected_clients)}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(connected_clients)}")
    except Exception:
        connected_clients.discard(websocket)


async def broadcast_news(event_type: str, data: dict):
    if not connected_clients:
        return
    message = json.dumps({"type": event_type, "data": data}, ensure_ascii=False, default=str)
    disconnected = set()
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    connected_clients.difference_update(disconnected)


async def broadcast_new_articles(articles: list[dict]):
    for article in articles:
        await broadcast_news("new_article", article)


async def broadcast_alert(alert: dict):
    await broadcast_news("new_alert", alert)
