import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.setting import SystemSetting

router = APIRouter()
logger = logging.getLogger(__name__)


class HandleAdd(BaseModel):
    handle: str


class HandleRemove(BaseModel):
    handle: str


async def _get_handles(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "twitter_handles")
    )
    setting = result.scalar_one_or_none()
    if not setting or not setting.value:
        return []
    try:
        return json.loads(setting.value)
    except json.JSONDecodeError:
        return []


async def _save_handles(session: AsyncSession, handles: list[str]):
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "twitter_handles")
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = json.dumps(handles)
        await session.commit()


@router.get("/handles")
async def list_handles(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    handles = await _get_handles(session)
    return {"handles": handles}


@router.post("/handles")
async def add_handle(
    body: HandleAdd,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    handle = body.handle.strip().lstrip("@")
    if not handle:
        raise HTTPException(status_code=400, detail="Handle cannot be empty")

    handles = await _get_handles(session)
    if handle in handles:
        raise HTTPException(status_code=400, detail="Handle already exists")

    handles.append(handle)
    await _save_handles(session, handles)
    return {"handles": handles}


@router.delete("/handles/{handle}")
async def remove_handle(
    handle: str,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    handles = await _get_handles(session)
    handle = handle.strip().lstrip("@")
    if handle not in handles:
        raise HTTPException(status_code=404, detail="Handle not found")

    handles.remove(handle)
    await _save_handles(session, handles)
    return {"handles": handles}


@router.post("/fetch")
async def manual_fetch(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    """手动触发一次推特采集"""
    from app.sources.twitter import TwitterSource
    source = TwitterSource()
    try:
        items = await source.fetch()
        if items:
            from app.sources.manager import _save_items
            saved, new_articles = await _save_items(session, items)
            return {"fetched": len(items), "saved": saved}
        return {"fetched": 0, "saved": 0}
    except Exception as e:
        logger.error(f"Manual twitter fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
