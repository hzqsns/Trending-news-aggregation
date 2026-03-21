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


@router.post("/test-ai")
async def test_ai_connection(
    _=Depends(get_current_user),
):
    """测试 AI API 连接是否正常"""
    from app.ai.client import _get_ai_config
    import httpx

    config = await _get_ai_config()
    if not config["api_key"]:
        return {"success": False, "message": "未配置 API Key"}

    messages = [{"role": "user", "content": "Hi, reply with 'ok' only."}]

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if config["api_format"] == "anthropic":
                url = f"{config['api_base'].rstrip('/')}/v1/messages"
                payload = {
                    "model": config["model"],
                    "messages": messages,
                    "max_tokens": 100,
                }
                headers = {
                    "x-api-key": config["api_key"],
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                }
            else:
                url = f"{config['api_base'].rstrip('/')}/chat/completions"
                payload = {
                    "model": config["model"],
                    "messages": messages,
                    "temperature": 0,
                    "max_tokens": 100,
                }
                headers = {
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                }

            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                return {
                    "success": True,
                    "message": f"连接成功！模型: {config['model']}",
                    "model": config["model"],
                }
            else:
                error_text = resp.text[:200]
                return {
                    "success": False,
                    "message": f"API 返回错误 ({resp.status_code}): {error_text}",
                }
    except httpx.TimeoutException:
        return {"success": False, "message": "连接超时，请检查 API 地址是否正确"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


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


@router.get("/ai-providers")
async def ai_providers(_=Depends(get_current_user)):
    """返回 AI 服务商预设列表"""
    from app.ai.client import PROVIDER_PRESETS
    providers = [
        {"key": k, "api_base": v["api_base"], "default_model": v["default_model"], "api_format": v.get("api_format", "openai")}
        for k, v in PROVIDER_PRESETS.items()
    ]
    providers.append({"key": "custom", "api_base": "", "default_model": "", "api_format": "openai"})
    return {"providers": providers}


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
            {"key": "twitter", "label": "推特追踪"},
        ]
    }
