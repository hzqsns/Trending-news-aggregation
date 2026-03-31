import logging

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.setting import SystemSetting

router = APIRouter()
logger = logging.getLogger(__name__)


async def _get_alice_config(session: AsyncSession) -> dict:
    config = {"enabled": False, "base_url": "http://localhost:3002"}
    for key in ("openalice_enabled", "openalice_base_url"):
        row = await session.scalar(select(SystemSetting).where(SystemSetting.key == key))
        if row and row.value:
            if key == "openalice_enabled":
                config["enabled"] = row.value == "true"
            else:
                config["base_url"] = row.value.rstrip("/")
    return config


@router.get("/status", dependencies=[Depends(get_current_user)])
async def alice_status(session: AsyncSession = Depends(get_session)):
    config = await _get_alice_config(session)
    if not config["enabled"]:
        return {"online": False, "enabled": False, "message": "OpenAlice 未启用，请在系统设置中开启"}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(config["base_url"])
            return {
                "online": resp.status_code == 200,
                "enabled": True,
                "base_url": config["base_url"],
                "status_code": resp.status_code,
            }
    except httpx.ConnectError:
        return {"online": False, "enabled": True, "message": f"无法连接 {config['base_url']}，请确认 OpenAlice 已启动"}
    except Exception as e:
        return {"online": False, "enabled": True, "message": str(e)}


class AskPayload(BaseModel):
    message: str


@router.post("/ask", dependencies=[Depends(get_current_user)])
async def alice_ask(payload: AskPayload, session: AsyncSession = Depends(get_session)):
    config = await _get_alice_config(session)
    if not config["enabled"]:
        return {"error": "OpenAlice 未启用"}

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{config['base_url']}/mcp/ask",
                json={"message": payload.message},
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"OpenAlice 返回 {resp.status_code}", "detail": resp.text[:500]}
    except httpx.ConnectError:
        return {"error": f"无法连接 OpenAlice ({config['base_url']})"}
    except Exception as e:
        logger.error(f"Alice ask failed: {e}")
        return {"error": str(e)}


@router.get("/market/{path:path}", dependencies=[Depends(get_current_user)])
async def alice_market_proxy(path: str, request: Request, session: AsyncSession = Depends(get_session)):
    config = await _get_alice_config(session)
    if not config["enabled"]:
        return {"error": "OpenAlice 未启用"}

    try:
        target_url = f"{config['base_url']}/api/{path}"
        params = dict(request.query_params)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(target_url, params=params)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"OpenAlice market API 返回 {resp.status_code}", "detail": resp.text[:500]}
    except httpx.ConnectError:
        return {"error": f"无法连接 OpenAlice ({config['base_url']})"}
    except Exception as e:
        logger.error(f"Alice market proxy failed: {e}")
        return {"error": str(e)}
