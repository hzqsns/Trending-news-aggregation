import logging
from datetime import datetime, timezone

import httpx

from app.crawlers.base import CrawlerPlugin
from app.sources.base import NewsItem

logger = logging.getLogger(__name__)

LINUX_DO_API = "https://linux.do/latest.json"


class LinuxDoCrawler(CrawlerPlugin):
    key = "linux_do"
    name = "Linux.do"
    category = "tech"
    enabled_key = "source_linux_do_enabled"

    async def fetch(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    LINUX_DO_API,
                    headers={"User-Agent": "NewsAgent/2.0"},
                )
                if resp.status_code != 200:
                    logger.warning(f"Linux.do returned {resp.status_code}")
                    return items

                data = resp.json()
                topic_list = data.get("topic_list", {})
                topics = topic_list.get("topics", [])

                for topic in topics[:30]:
                    pub_date = None
                    if topic.get("created_at"):
                        try:
                            pub_date = datetime.fromisoformat(
                                topic["created_at"].replace("Z", "+00:00")
                            )
                        except (ValueError, AttributeError):
                            pass

                    category_name = ""
                    if topic.get("category_id"):
                        category_name = f"[cat:{topic['category_id']}]"

                    slug = topic.get("slug", "")
                    tid = topic.get("id", "")
                    url = f"https://linux.do/t/{slug}/{tid}" if slug else f"https://linux.do/t/{tid}"

                    views = topic.get("views", 0)
                    reply_count = topic.get("posts_count", 0)
                    title = topic.get("title", "")
                    if views > 1000 or reply_count > 20:
                        title = f"{title} ({views} views, {reply_count} replies)"

                    items.append(NewsItem(
                        title=title,
                        url=url,
                        source="Linux.do",
                        category="tech",
                        summary=topic.get("excerpt", "")[:500] if topic.get("excerpt") else None,
                        published_at=pub_date,
                    ))
        except Exception as e:
            logger.error(f"Error fetching Linux.do: {e}")
        return items
