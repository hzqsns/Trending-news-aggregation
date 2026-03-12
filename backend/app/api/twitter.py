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


class CookiesImport(BaseModel):
    cookies: str  # JSON string from browser extension


@router.post("/import-cookies")
async def import_cookies(
    body: CookiesImport,
    _=Depends(get_current_user),
):
    """导入浏览器导出的 Cookie JSON，保存到 cookies 文件并验证"""
    from app.sources.twitter import COOKIES_FILE
    import json

    try:
        cookie_data = json.loads(body.cookies)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Cookie 格式无效，请粘贴合法的 JSON")

    # 兼容两种常见导出格式：
    # 1. Cookie-Editor 导出的数组格式 [{"name":..., "value":..., "domain":...}]
    # 2. twikit 自己保存的格式（直接存）
    if isinstance(cookie_data, list):
        # 转成 twikit 兼容的 dict 格式 {name: value}
        converted = {c["name"]: c["value"] for c in cookie_data if "name" in c and "value" in c}
    elif isinstance(cookie_data, dict):
        converted = cookie_data
    else:
        raise HTTPException(status_code=400, detail="不支持的 Cookie 格式")

    required = {"auth_token", "ct0"}
    missing = required - set(converted.keys())
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少必要的 Cookie 字段：{', '.join(missing)}（请确认已登录 x.com 后再导出）")

    COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIES_FILE.write_text(json.dumps(converted, ensure_ascii=False, indent=2))

    # 重置全局 client，下次采集时用新 cookies 重建
    from app.sources import twitter as tw_module
    tw_module._client = None

    # 快速验证：尝试加载 cookies 并获取当前用户
    try:
        from twikit import Client as TwikitClient
        client = TwikitClient("en-US")
        client.load_cookies(str(COOKIES_FILE))
        user = await client.user()
        tw_module._client = client
        return {"success": True, "message": f"Cookie 导入成功，已验证登录：@{user.screen_name}"}
    except Exception as e:
        COOKIES_FILE.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Cookie 验证失败（可能已过期）：{e}")


@router.post("/test-auth")
async def test_auth(
    _=Depends(get_current_user),
):
    """测试 twikit 账号认证是否可用"""
    from app.sources.twitter import _get_twitter_config, COOKIES_FILE
    import os

    config = await _get_twitter_config()
    if not config["username"] and not config["password"]:
        raise HTTPException(status_code=400, detail="未填写账号信息，请先保存 X 账号认证配置")

    # 强制重新登录（删除旧 cookies），确保用最新配置验证
    try:
        from twikit import Client as TwikitClient
    except ImportError:
        raise HTTPException(status_code=500, detail="twikit 未安装，请执行: pip install twikit")

    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink()

    from app.sources import twitter as tw_module
    tw_module._client = None  # 重置全局 client

    client = TwikitClient("en-US")
    try:
        COOKIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        await client.login(
            auth_info_1=config["username"],
            auth_info_2=config["email"],
            password=config["password"],
        )
        client.save_cookies(str(COOKIES_FILE))
        tw_module._client = client
        return {"success": True, "message": f"登录成功，已保存 cookies，后续采集无需重新登录"}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Twitter test-auth failed: {error_msg}")
        raise HTTPException(status_code=400, detail=f"登录失败：{error_msg}")


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
