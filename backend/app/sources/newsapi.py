import logging
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.setting import SystemSetting
from app.sources.base import NewsSource, NewsItem

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "business": "global",
    "technology": "tech",
    "general": "general",
    "science": "tech",
}


class NewsAPISource(NewsSource):
    name = "NewsAPI"
    enabled_key = "source_newsapi_enabled"

    async def _get_api_key(self) -> str:
        async with async_session() as session:
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == "source_newsapi_key")
            )
            s = result.scalar_one_or_none()
            return s.value if s and s.value else ""

    async def fetch(self) -> list[NewsItem]:
        api_key = await self._get_api_key()
        if not api_key:
            logger.debug("NewsAPI key not configured, skipping")
            return []

        items = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    "https://newsapi.org/v2/top-headlines",
                    params={
                        "category": "business",
                        "language": "en",
                        "pageSize": 30,
                        "apiKey": api_key,
                    },
                    headers={"User-Agent": "NewsAgent/2.0"},
                )
                if resp.status_code != 200:
                    logger.warning(f"NewsAPI returned {resp.status_code}")
                    return items

                data = resp.json()
                for article in data.get("articles", []):
                    pub_date = None
                    if article.get("publishedAt"):
                        try:
                            pub_date = datetime.fromisoformat(
                                article["publishedAt"].replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    source_name = "NewsAPI"
                    if article.get("source", {}).get("name"):
                        source_name = article["source"]["name"]

                    items.append(NewsItem(
                        title=article.get("title", "").strip(),
                        url=article.get("url", ""),
                        source=source_name,
                        category="global",
                        summary=article.get("description", "")[:500] if article.get("description") else None,
                        image_url=article.get("urlToImage"),
                        published_at=pub_date,
                    ))
        except Exception as e:
            logger.error(f"Error fetching NewsAPI: {e}")
        return items
