"""BUFF (网易 163) Cookie 爬虫 — 国内 CS2 饰品最大交易平台。

工作原理：
- 用户在浏览器登录 buff.163.com 后，通过插件导出 cookies
- 将 cookies JSON 放到 backend/data/buff_cookies.json
- 爬虫带 cookie 访问 /api/market/goods 公开端点

Cookie 获取方式：
1. Chrome 插件 "EditThisCookie" 导出 buff.163.com
2. 或 Firefox 插件 "Cookie-Editor"
3. JSON 格式：[{"name": "session", "value": "...", "domain": ".buff.163.com"}, ...]

Cookie 有效期：通常 1-3 个月，过期后后台日志会报 Login Required，需重新登录导出。
"""
import json
import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

COOKIES_FILE = Path(__file__).parent.parent.parent / "data" / "buff_cookies.json"
BUFF_API = "https://buff.163.com/api/market/goods"


def _load_cookies() -> dict[str, str]:
    """加载 BUFF cookies。返回 {name: value} 字典。"""
    if not COOKIES_FILE.exists():
        return {}
    try:
        with open(COOKIES_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        # 兼容两种格式：浏览器插件导出的 array 或简单 dict
        if isinstance(raw, list):
            return {item["name"]: item["value"] for item in raw if "name" in item and "value" in item}
        elif isinstance(raw, dict):
            return raw
        return {}
    except Exception as e:
        logger.error(f"BUFF cookies load error: {e}")
        return {}


class BuffCrawler:
    """BUFF 饰品市场爬虫。

    使用：
    1. 用户登录 buff.163.com 并导出 cookies 到 data/buff_cookies.json
    2. 调用 fetch_market(category, page_size) 批量拉取
    """

    name = "buff"

    async def fetch_market(
        self,
        category: Optional[str] = None,
        page_num: int = 1,
        page_size: int = 80,
        sort_by: str = "sell_num.desc",
    ) -> list[dict]:
        """批量拉取 BUFF 市场饰品列表。

        Args:
            category: 分类筛选，如 'knife' / 'rifle' / None(全部)
            page_num: 页码
            page_size: 每页数量（BUFF 最大 80）
            sort_by: 排序 sell_num.desc(成交量降序) / price.desc / price.asc / created.desc

        Returns:
            items 列表，每条包含：
            {
                "id": 33926,                       # BUFF 内部 goods_id
                "market_hash_name": "AK-47 | ...", # Steam 标准名
                "name": "AK-47 | 酷炫涂鸦皮革 (久经沙场)",  # 中文名
                "sell_min_price": "260.00",        # 在售最低价(BUFF 真实市场价)
                "sell_num": 25,                    # 在售数量
                "buy_max_price": "255.00",         # 求购最高价
                "buy_num": 12,                     # 求购数量
                "steam_market_url": "...",
                "quick_price": "258.00",           # BUFF 快速交易价
                ...
            }
        """
        cookies = _load_cookies()
        if not cookies:
            logger.debug("BUFF cookies not configured, skipping")
            return []

        params: dict = {
            "game": "csgo",
            "page_num": page_num,
            "page_size": min(page_size, 80),
            "sort_by": sort_by,
        }
        if category:
            params["category"] = category

        try:
            async with httpx.AsyncClient(timeout=20, cookies=cookies) as client:
                r = await client.get(
                    BUFF_API,
                    params=params,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Accept": "application/json",
                        "Referer": "https://buff.163.com/market/csgo",
                    },
                )
                if r.status_code != 200:
                    logger.warning(f"BUFF HTTP {r.status_code}")
                    return []

                # BUFF 未登录时返回 HTML 登录页（text/html）而不是 JSON
                ct = r.headers.get("content-type", "")
                if "json" not in ct:
                    logger.warning("BUFF returned non-JSON (cookies may be expired)")
                    return []

                body = r.json()
                if body.get("code") != "OK":
                    logger.warning(f"BUFF error: {body.get('code')} - {body.get('error')}")
                    return []

                return body.get("data", {}).get("items", []) or []
        except Exception as e:
            logger.error(f"BUFF fetch_market error: {e}")
            return []

    async def fetch_price_history(self, goods_id: int, days: int = 7) -> list[dict]:
        """获取单饰品历史价格曲线（无需登录状态，有 cookie 即可）。

        Returns: [{"timestamp": 1234567890, "price": 260.0}, ...]
        """
        cookies = _load_cookies()
        if not cookies:
            return []
        try:
            async with httpx.AsyncClient(timeout=15, cookies=cookies) as client:
                r = await client.get(
                    "https://buff.163.com/api/market/goods/price_history/buff",
                    params={"game": "csgo", "goods_id": goods_id, "currency": "CNY", "days": days},
                    headers={"User-Agent": "Mozilla/5.0", "Referer": f"https://buff.163.com/goods/{goods_id}"},
                )
                if r.status_code != 200 or "json" not in r.headers.get("content-type", ""):
                    return []
                body = r.json()
                if body.get("code") != "OK":
                    return []
                return body.get("data", {}).get("price_history", []) or []
        except Exception as e:
            logger.debug(f"BUFF price history error: {e}")
            return []
