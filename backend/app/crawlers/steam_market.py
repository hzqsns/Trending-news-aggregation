"""Steam Market priceoverview API crawler.

注意：此 crawler 不继承自通用 CrawlerPlugin 的 fetch()->list[NewsItem] 签名，
因为 CS2 饰品价格不是新闻。提供独立的 fetch_prices(market_hash_names) 方法。
"""
import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

STEAM_PRICE_URL = "https://steamcommunity.com/market/priceoverview/"
CS2_APPID = 730
CURRENCY_CNY = 23
REQUEST_INTERVAL = 3.5  # 秒，避免 429


def _parse_price(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    # "¥ 3,240.00" → 3240.0
    cleaned = s.replace("¥", "").replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_volume(s: Optional[str]) -> int:
    if not s:
        return 0
    try:
        return int(s.replace(",", "").strip())
    except ValueError:
        return 0


class SteamMarketCrawler:
    """Steam 官方市场价格抓取器。

    返回每个饰品的 {price, volume, median_price} 字典。
    """

    name = "steam_market"

    async def fetch_one(
        self,
        client: httpx.AsyncClient,
        market_hash_name: str,
        currency: int = CURRENCY_CNY,
    ) -> dict | None:
        params = {
            "appid": CS2_APPID,
            "currency": currency,
            "market_hash_name": market_hash_name,
        }
        for attempt in range(3):
            try:
                resp = await client.get(STEAM_PRICE_URL, params=params, timeout=15)
                if resp.status_code == 429:
                    wait = 30 * (attempt + 1)
                    logger.warning(f"Steam 429 for {market_hash_name}, backoff {wait}s")
                    await asyncio.sleep(wait)
                    continue
                if resp.status_code != 200:
                    logger.warning(f"Steam {resp.status_code} for {market_hash_name}")
                    return None
                data = resp.json()
                if not data.get("success"):
                    return None
                return {
                    "market_hash_name": market_hash_name,
                    "price": _parse_price(data.get("lowest_price")),
                    "median_price": _parse_price(data.get("median_price")),
                    "volume": _parse_volume(data.get("volume")),
                }
            except httpx.TimeoutException:
                logger.debug(f"Timeout for {market_hash_name}, attempt {attempt + 1}")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Steam fetch error for {market_hash_name}: {e}")
                return None
        return None

    async def fetch_prices(
        self,
        market_hash_names: list[str],
        currency: int = CURRENCY_CNY,
        batch_size: int = 20,
    ) -> list[dict]:
        """按 market_hash_name 列表批量请求，错峰避限流。"""
        results: list[dict] = []
        async with httpx.AsyncClient(
            headers={"User-Agent": "NewsAgent/2.0 (CS2 market tracker)"},
        ) as client:
            for i, name in enumerate(market_hash_names[:batch_size * 10]):  # 上限保护
                result = await self.fetch_one(client, name, currency)
                if result and result.get("price") is not None:
                    results.append(result)
                if i < len(market_hash_names) - 1:
                    await asyncio.sleep(REQUEST_INTERVAL)
        return results
