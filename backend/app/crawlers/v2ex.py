import logging
from datetime import datetime, timezone

import httpx

from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem

logger = logging.getLogger(__name__)

V2EX_HOT_URL = "https://www.v2ex.com/api/v2/topics/hot"
V2EX_LATEST_URL = "https://www.v2ex.com/api/v2/topics/latest"


class V2exCrawler(CrawlerPlugin):
    key = "v2ex"
    name = "V2EX"
    category = "tech"
    enabled_key = "source_v2ex_enabled"

    async def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    V2EX_HOT_URL,
                    headers={"User-Agent": "NewsAgent/2.0"},
                )
                if resp.status_code != 200:
                    logger.warning(f"V2EX API returned {resp.status_code}, trying latest")
                    resp = await client.get(
                        V2EX_LATEST_URL,
                        headers={"User-Agent": "NewsAgent/2.0"},
                    )
                    if resp.status_code != 200:
                        return items

                data = resp.json()
                topics = data.get("result", data) if isinstance(data, dict) else data
                if not isinstance(topics, list):
                    return items

                for topic in topics[:30]:
                    pub_date = None
                    if topic.get("created"):
                        try:
                            pub_date = datetime.fromtimestamp(topic["created"], tz=timezone.utc)
                        except (ValueError, TypeError):
                            pass

                    node_name = ""
                    if isinstance(topic.get("node"), dict):
                        node_name = topic["node"].get("title", "")

                    title = topic.get("title", "")
                    if node_name:
                        title = f"[{node_name}] {title}"

                    items.append(NewsItem(
                        title=title,
                        url=topic.get("url", f"https://www.v2ex.com/t/{topic.get('id', '')}"),
                        source="V2EX",
                        category="tech",
                        summary=topic.get("content", "")[:500] if topic.get("content") else None,
                        published_at=pub_date,
                    ))
        except Exception as e:
            logger.error(f"Error fetching V2EX: {e}")
        return items
