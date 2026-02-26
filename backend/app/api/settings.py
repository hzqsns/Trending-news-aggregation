from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.setting import SystemSetting, DEFAULT_SETTINGS

router = APIRouter()


class SettingUpdate(BaseModel):
    value: Optional[str] = None


class SettingsBatchUpdate(BaseModel):
    settings: dict[str, str]


@router.get("/")
async def list_settings(
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    query = select(SystemSetting).order_by(SystemSetting.category, SystemSetting.id)
    if category:
        query = query.where(SystemSetting.category == category)
    result = await session.execute(query)
    items = result.scalars().all()

    grouped: dict[str, list] = {}
    for item in items:
        d = item.to_dict()
        if item.field_type == "password" and item.value:
            d["value"] = "••••••••"
            d["has_value"] = True
        grouped.setdefault(item.category, []).append(d)
    return grouped


@router.get("/raw/{key}")
async def get_setting_raw(
    key: str,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        return {"error": "Setting not found"}
    return setting.to_dict()


@router.put("/{key}")
async def update_setting(
    key: str,
    body: SettingUpdate,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        return {"error": "Setting not found"}

    if body.value is not None and body.value != "••••••••":
        setting.value = body.value
        setting.updated_at = datetime.utcnow()
        await session.commit()
    return setting.to_dict()


@router.put("/")
async def batch_update_settings(
    body: SettingsBatchUpdate,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    updated = []
    for key, value in body.settings.items():
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        setting = result.scalar_one_or_none()
        if setting and value != "••••••••":
            setting.value = value
            setting.updated_at = datetime.utcnow()
            updated.append(key)
    await session.commit()
    return {"updated": updated}


@router.get("/categories")
async def setting_categories(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    return {
        "categories": [
            {"key": "system", "label": "系统配置"},
            {"key": "ai", "label": "AI 配置"},
            {"key": "sources", "label": "数据源配置"},
            {"key": "notifications", "label": "推送渠道"},
            {"key": "push_strategy", "label": "推送策略"},
        ]
    }
