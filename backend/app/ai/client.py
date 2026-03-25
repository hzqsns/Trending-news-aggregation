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
        "api_format": "openai",
    },
    "openrouter": {
        "api_base": "https://openrouter.ai/api/v1",
        "default_model": "google/gemini-2.0-flash-exp:free",
        "api_format": "openai",
    },
    "dashscope": {
        "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "api_format": "openai",
    },
    "deepseek": {
        "api_base": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "api_format": "openai",
    },
    "openai": {
        "api_base": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "api_format": "openai",
    },
    "minimax": {
        "api_base": "https://api.minimax.io/anthropic",
        "default_model": "MiniMax-Text-01",
        "api_format": "anthropic",
    },
}


async def _get_ai_config() -> dict:
    async with async_session() as session:
        keys = ["ai_enabled", "ai_provider", "ai_api_key", "ai_api_base", "ai_model", "ai_api_format"]
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key.in_(keys))
        )
        settings = {s.key: s.value for s in result.scalars().all()}

    provider = settings.get("ai_provider", "custom")
    preset = PROVIDER_PRESETS.get(provider)

    # 用户填了就用用户的，没填就用预设的
    api_base = settings.get("ai_api_base", "")
    model = settings.get("ai_model", "")
    api_format = settings.get("ai_api_format", "")
    if preset:
        if not api_base:
            api_base = preset["api_base"]
        if not model:
            model = preset["default_model"]
        if not api_format:
            api_format = preset.get("api_format", "openai")

    return {
        "enabled": settings.get("ai_enabled", "true") == "true",
        "api_key": settings.get("ai_api_key", ""),
        "api_base": api_base or "https://api.openai.com/v1",
        "model": model or "gpt-4o-mini",
        "api_format": api_format or "openai",
    }


async def _call_openai_format(config: dict, messages: list[dict], temperature: float, max_tokens: int, response_format: Optional[dict]) -> Optional[str]:
    url = f"{config['api_base'].rstrip('/')}/chat/completions"
    payload: dict = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        logger.error(f"AI API error {resp.status_code}: {resp.text[:200]}")
        return None
    data = resp.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        logger.error(f"AI API returned empty content: {str(data)[:200]}")
    return content


async def _call_anthropic_format(config: dict, messages: list[dict], temperature: float, max_tokens: int) -> Optional[str]:
    """兼容 Anthropic Messages API 格式（MiniMax 等）。"""
    # 将 system 消息单独提取
    system_prompt: Optional[str] = None
    user_messages = []
    for m in messages:
        if m["role"] == "system":
            system_prompt = m["content"]
        else:
            user_messages.append({"role": m["role"], "content": m["content"]})

    url = f"{config['api_base'].rstrip('/')}/v1/messages"
    payload: dict = {
        "model": config["model"],
        "messages": user_messages,
        "max_tokens": max_tokens,
    }
    if system_prompt:
        payload["system"] = system_prompt

    headers = {
        "x-api-key": config["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        logger.error(f"AI API error {resp.status_code}: {resp.text[:200]}")
        return None
    data = resp.json()
    # Anthropic 格式：content 是列表，取第一个 text block
    content_blocks = data.get("content", [])
    for block in content_blocks:
        if block.get("type") == "text":
            return block.get("text")
    logger.error(f"AI API returned no text content: {str(data)[:200]}")
    return None


async def chat_completion(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 1000,
    response_format: Optional[dict] = None,
) -> Optional[str]:
    config = await _get_ai_config()
    if not config["enabled"] or not config["api_key"]:
        return None

    try:
        if config["api_format"] == "anthropic":
            return await _call_anthropic_format(config, messages, temperature, max_tokens)
        else:
            return await _call_openai_format(config, messages, temperature, max_tokens, response_format)
    except Exception as e:
        logger.error(f"AI API call failed: {e}")
        return None


def _extract_json_text(text: str) -> str:
    """Strip markdown code fences if the model wraps JSON in ```json ... ```."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # drop first line (``` or ```json) and last line (```)
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return text


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
            return json.loads(_extract_json_text(result))
        except json.JSONDecodeError:
            logger.error(f"Failed to parse AI JSON response: {result[:300]}")
    return None
