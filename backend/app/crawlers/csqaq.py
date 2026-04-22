"""CSQAQ API crawler — 国内主流市场（BUFF/悠悠有品）真实价格数据。

相比 Steam Market API：
- 数据源：BUFF + 悠悠有品（国内 CS 饰品 95% 交易量在此）
- 效率：1 次请求取 100 条 vs Steam 逐个请求（3s/个）
- 数据维度：实时价/成交量/库存/在售求购/价差/30 天 K 线
- 限流：1 req/sec（官方限制）

需要配置：settings.csqaq_api_token
文档：https://docs.csqaq.com/
"""
import asyncio
import logging
from typing import Optional

import httpx
from sqlalchemy import select

from app.database import async_session
from app.models.setting import SystemSetting

logger = logging.getLogger(__name__)

API_BASE = "https://api.csqaq.com/api/v1"
RATE_LIMIT_INTERVAL = 1.1  # 秒，略高于 1 避免 429


async def _get_api_token() -> str:
    async with async_session() as session:
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key == "csqaq_api_token")
        )
        s = result.scalar_one_or_none()
        return s.value if s and s.value else ""


class CSQAQCrawler:
    """CSQAQ API 爬虫。无 token 时安全降级返回 []。"""

    name = "csqaq"

    async def fetch_rank_list(
        self,
        page_size: int = 100,
        sort_field: str = "市值_降序(BUFF)",
    ) -> list[dict]:
        """批量拉取排行榜。一次拿 100 条 BUFF/悠悠双平台实时数据。

        返回示例 item：
        {
            "id": 7310, "name": "AK-47 | 红线", "exterior": "战痕累累",
            "buff_buy_price": 260.0, "buff_sell_price": 265.0, "buff_volume_day": 1892,
            "yyyp_buy_price": 258.0, "yyyp_sell_price": 264.0,
            "steam_buy_price": 310.0,
            "change_pct_1d": 2.3, "change_pct_7d": 5.1, "change_pct_30d": -1.5,
            "rarity": "classified", "quality": "normal",
        }
        """
        token = await _get_api_token()
        if not token:
            logger.debug("CSQAQ API token not configured")
            return []

        payload = {
            "page_index": 1,
            "page_size": min(max(page_size, 1), 500),
            "show_recently_price": False,
            "filter": {
                "排序": [sort_field],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{API_BASE}/info/get_rank_list",
                    headers={"ApiToken": token, "Content-Type": "application/json"},
                    json=payload,
                )
                if resp.status_code == 429:
                    logger.warning("CSQAQ 429 rate limit, backing off")
                    await asyncio.sleep(5)
                    return []
                if resp.status_code != 200:
                    logger.warning(f"CSQAQ {resp.status_code}: {resp.text[:200]}")
                    return []

                body = resp.json()
                if body.get("code") != 200:
                    logger.warning(f"CSQAQ API error: {body.get('msg')}")
                    return []

                return body.get("data", {}).get("data", []) or []
        except Exception as e:
            logger.error(f"CSQAQ fetch_rank_list error: {e}")
            return []

    async def fetch_item_detail(self, item_id: int) -> Optional[dict]:
        """获取单件饰品详情 — 含花纹/磨损/K 线。"""
        token = await _get_api_token()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{API_BASE}/info/good",
                    params={"id": item_id},
                    headers={"ApiToken": token},
                )
                if resp.status_code != 200:
                    return None
                body = resp.json()
                if body.get("code") != 200:
                    return None
                return body.get("data")
        except Exception as e:
            logger.error(f"CSQAQ fetch_item_detail({item_id}) error: {e}")
            return None
