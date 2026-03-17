import json
import logging
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.setting import SystemSetting

logger = logging.getLogger(__name__)

# 预设服务商配置
PROVIDER_PRESETS = {
    "gemini": {
        "api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "default_model": "google/gemini-2.0-flash-exp:free",
    },
    "dashscope": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
    },
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
    },
}


async def _get_ai_config() -> dict:
    async with async_session() as session:
        keys = ["ai_enabled", "ai_provider", "ai_api_key", "ai_api_base", "ai_model"]
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key.in_(keys))
        )
        settings = {s.key: s.value for s in result.scalars().all()}

    provider = settings.get("ai_provider", "custom")
    preset = PROVIDER_PRESETS.get(provider)

    # 用户填了就用用户的，没填就用预设的
    api_base = settings.get("ai_api_base", "")
    model = settings.get("ai_model", "")
    if preset:
        if not api_base:
            api_base = preset["api_base"]
        if not model:
            model = preset["default_model"]

    return {
        "enabled": settings.get("ai_enabled", "true") == "true",
        "api_key": settings.get("ai_api_key", ""),
        "api_base": api_base or "https://api.openai.com/v1",
        "model": model or "gpt-4o-mini",
    }


async def chat_completion(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1000,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    config = await _get_ai_config()
    if not config["enabled"] or not config["api_key"]:
        return None

    url = f"{config['api_base'].rstrip('/')}/chat/completions"
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code != 200:
                logger.error(f"AI API error {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content")
            if not content:
                logger.error(f"AI API returned empty content: {str(data)[:200]}")
            return content
    except Exception as e:
        logger.error(f"AI API call failed: {e}")
        return None


async def chat_completion_json(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1000,
) -> Optional[dict]:
    result = await chat_completion(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    if result:
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI JSON response: {result[:200]}")
    return None
