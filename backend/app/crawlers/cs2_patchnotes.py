"""CS2 patchnotes crawler — 为 LLM 预测提供外部因子。

抓取 steamdb.info/app/730/patchnotes 或 steamcommunity 更新公告。
"""
import logging
import re
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

# 优先使用 Steam News API（无需爬虫）
STEAM_NEWS_API = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/"


class CS2PatchNotesCrawler:
    name = "cs2_patchnotes"

    async def fetch_recent(self, count: int = 10) -> list[dict]:
        """返回最近的 CS2 更新公告列表。"""
        items: list[dict] = []
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(
                    STEAM_NEWS_API,
                    params={
                        "appid": 730,
                        "count": count,
                        "maxlength": 500,
                        "format": "json",
                    },
                    headers={"User-Agent": "NewsAgent/2.0"},
                )
                if resp.status_code != 200:
                    logger.warning(f"Steam news API returned {resp.status_code}")
                    return items

                data = resp.json()
                news_items = data.get("appnews", {}).get("newsitems", [])

                for entry in news_items:
                    pub_date = None
                    if entry.get("date"):
                        try:
                            pub_date = datetime.fromtimestamp(entry["date"])
                        except (ValueError, TypeError):
                            pass

                    # Strip BBCode/HTML
                    contents = entry.get("contents", "")
                    # 匹配所有 [xxx] 形式的 BBCode（包括 [*]、[/list]、[h1]）
                    contents = re.sub(r"\[[^\]]*\]", "", contents)
                    contents = re.sub(r"<[^>]+>", "", contents)

                    items.append({
                        "title": entry.get("title", ""),
                        "url": entry.get("url", ""),
                        "summary": contents[:500],
                        "published_at": pub_date.isoformat() if pub_date else None,
                        "author": entry.get("author", ""),
                    })
        except Exception as e:
            logger.error(f"CS2 patchnotes fetch error: {e}")
        return items
