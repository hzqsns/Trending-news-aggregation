"""CSGOSKINS.GG 多平台比价 crawler。

需配置 settings.source_csgoskins_api_key，未配置时安全降级返回 []。
"""
import logging

import httpx
from sqlalchemy import select

from app.database import async_session
from app.models.setting import SystemSetting

logger = logging.getLogger(__name__)

CSGOSKINS_API = "https://csgoskins.gg/api/v1/prices"


async def _get_api_key() -> str:
    async with async_session() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == "source_csgoskins_api_key")
        )
        s = result.scalar_one_or_none()
        return s.value if s and s.value else ""


class CSGOSkinsGGCrawler:
    name = "csgoskins_gg"

    async def fetch_multi_platform(self, market_hash_name: str) -> list[dict]:
        """返回给定饰品在多个平台的价格列表。无 key 或失败时返回 []。"""
        api_key = await _get_api_key()
        if not api_key:
            logger.debug("CSGOSKINS key not configured, skipping")
            return []

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    CSGOSKINS_API,
                    params={"name": market_hash_name},
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "User-Agent": "NewsAgent/2.0",
                    },
                )
                if resp.status_code == 429:
                    logger.warning("CSGOSKINS 429 rate limited")
                    return []
                if resp.status_code == 402 or resp.status_code == 403:
                    logger.warning(f"CSGOSKINS {resp.status_code}: quota exhausted")
                    return []
                if resp.status_code != 200:
                    return []
                data = resp.json()
                markets = data.get("markets", [])
                return [
                    {
                        "platform": m.get("name", "unknown"),
                        "price": m.get("price"),
                        "currency": m.get("currency", "USD"),
                        "url": m.get("url"),
                    }
                    for m in markets
                    if m.get("price") is not None
                ]
        except Exception as e:
            logger.error(f"CSGOSKINS fetch error: {e}")
            return []
